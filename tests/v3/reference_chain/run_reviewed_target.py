"""ROOT ONLY: build an exact-reviewed-disk-source model in an owned blank NX.

This is the scoped reviewed-source route, not general geometric recognition.
No NX process is launched or closed here. Any failure stops without replay,
return or helper shutdown; the operator preserves the session for inspection.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests/v3/smoke_plan'), str(Path(__file__).parent)]
from nx_sketch_mcp.config import load_config
from nx_sketch_mcp.server import McpServer
from nx_sketch_mcp.v3.nx2506_composition import execute_steps
from nx_sketch_mcp.v3.nx2506_executor import Executor
from run_block_once import RecordingTransport, find_secrets, operation, same_path, scrub, write_new
from run_product_reference import bytes_equal, deny_writes, KnownBusyBeforeRead, takeover_when_ready, validate_takeover, wait_ready


class ProductTransport(RecordingTransport):
    def call(self, name, args):
        if name not in ('nx_v3_review_disk_source', 'nx_takeover'):
            return super().call(name, args)
        if self.stopped:
            raise RuntimeError('transport stopped')
        self.serial += 1
        prefix = f'{self.serial:04d}'
        find_secrets(args, self.secrets)
        write_new(self.directory / (prefix + '-request.json'), scrub({'tool': name, 'arguments': args}, self.secrets))
        try:
            response = self.server.handle_message({'jsonrpc': '2.0', 'id': self.serial + 10,
                'method': 'tools/call', 'params': {'name': name, 'arguments': args}})
            find_secrets(response, self.secrets)
            write_new(self.directory / (prefix + '-response.json'), scrub(response, self.secrets))
            outer = response.get('result', {}) if isinstance(response, dict) else {}
            result = outer.get('structuredContent') if isinstance(outer, dict) else None
            error = result.get('error') if isinstance(result, dict) else None
            if (name == 'nx_takeover' and outer.get('isError') is True and isinstance(error, dict)
                    and error.get('code') == 'NX_BUSY'
                    and error.get('message') == 'NX UI is busy; no model read was started'):
                raise KnownBusyBeforeRead(error['message'])
            if outer.get('isError') is True or not isinstance(result, dict):
                raise RuntimeError('reviewed source result missing or rejected')
            if name == 'nx_takeover' and (result.get('ok') is not True or result.get('writes_halted') is True):
                raise RuntimeError('takeover rejected or uncertain')
            return result
        except KnownBusyBeforeRead:
            raise
        except Exception:
            self.stopped = True
            raise


def run(args, server):
    transport = ProductTransport(server, args.evidence_dir)
    report = {'status': 'STOP_MANUAL_CHECK', 'stage': 'initialize', 'source_run': str(args.source_run),
              'scope': 'reviewed exact disk source; not a general recognition result',
              'target': str(args.target)}
    returned = False
    try:
        source_summary = json.loads((args.source_run / 'product-source/summary.json').read_text(encoding='utf8'))
        shutdown = json.loads((args.source_run / 'shutdown.json').read_text(encoding='utf8'))
        launch = json.loads((args.source_run / 'launch.json').read_text(encoding='utf8'))
        claim = (args.source_run / 'preload-claim.txt').read_text(encoding='utf8')
        normal_close_evidence = 'source locks held continuously from before launch through exit' in claim
        if not normal_close_evidence:
            reconciliation = json.loads((args.source_run / 'source-reconciliation.json').read_text(encoding='utf8'))
            target_launch = json.loads((args.fixture.parent.parent / 'launch.json').read_text(encoding='utf8'))
            def instant(value):
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            normal_close_evidence = (
                reconciliation.get('schema') == 't31-source-close-reconciliation/1'
                and reconciliation.get('source_pid') == launch.get('pid')
                and reconciliation.get('target_pid') == args.pid == target_launch.get('pid')
                and str(target_launch.get('start_ticks')) == str(args.start_ticks)
                and reconciliation.get('source_exit_utc') == shutdown.get('captured_utc')
                and reconciliation.get('target_start_utc') == target_launch.get('process_start_utc')
                and instant(reconciliation['source_exit_utc']) < instant(reconciliation['target_start_utc'])
                and all(reconciliation.get(k) is True for k in ('source_normal_exit', 'held_through_source_exit',
                    'post_exit_bytes_equal', 'unidentified_postclose_process', 'later_queue_empty_before_target')))
            report['source_close_scope'] = 'explicit post-close process reconciliation; unidentified process remains unidentified'
        source = Path(source_summary['source'])
        copy = Path(source_summary['independent_copy'])
        if (source_summary.get('status') != 'SOURCE_ANALYZED_TARGET_BLOCKED'
                or not isinstance(source_summary.get('reviewed_source'), dict)
                or shutdown.get('normal_exit') is not True or shutdown.get('force_terminated') is not False
                or source_summary.get('source_session_epoch') != f"{launch.get('pid')}:{launch.get('start_ticks')}"
                or source_summary.get('source_session_epoch') == f'{args.pid}:{args.start_ticks}'
                or shutdown.get('pid') != launch.get('pid')
                or not isinstance(source_summary.get('source_load_instance_id'), str)
                or not source_summary['source_load_instance_id']
                or not normal_close_evidence
                or not same_path(copy, args.source_run / 'reference-copy.prt')
                or not source.is_file() or not copy.is_file() or os.path.samefile(source, copy)
                or os.path.samefile(copy, args.fixture)):
            raise RuntimeError('source run preload, analysis or shutdown evidence incomplete')
        with deny_writes(source) as ref, deny_writes(copy) as independent:
            if not bytes_equal(ref, independent):
                raise RuntimeError('reviewed source copy differs from reference')
            init = server.handle_message({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                'params': {'protocolVersion': '2025-11-25', 'capabilities': {},
                           'clientInfo': {'name': 't31-reviewed-target', 'version': '1'}}})
            if not isinstance(init, dict) or 'result' not in init:
                raise RuntimeError('MCP initialization failed')
            server.handle_message({'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {}})
            report['stage'] = 'reviewed_disk_preview'
            preview = transport.call('nx_v3_review_disk_source', {'source_path': str(copy)})
            count = preview.get('group_count')
            if (preview.get('schema') != 'v3-reviewed-source-preview/1'
                    or preview.get('status') != 'reviewed_disk_source_only'
                    or preview.get('execution_approved') is not False
                    or type(count) is not int or count < 1 or count > 10000
                    or count != source_summary['reviewed_source'].get('group_count')
                    or preview.get('output_id') != source_summary['reviewed_source'].get('output_id')):
                raise RuntimeError('reviewed source preview not supported')
            report['group_count'] = count
            report['stage'] = 'readiness'
            wait_ready(transport.call, f'{args.pid}:{args.start_ticks}')
            report['stage'] = 'takeover'
            taken = takeover_when_ready(transport.call, {'expected_pid': args.pid, 'expected_part_path': str(args.fixture),
                'expected_session_epoch': f'{args.pid}:{args.start_ticks}',
                'artifact_scope': 'saved_independent_copy', 'authorize': True}, f'{args.pid}:{args.start_ticks}')
            validate_takeover(taken, args.fixture, f'{args.pid}:{args.start_ticks}')
            creds = {key: taken[key] for key in ('ownership_id', 'binding_epoch')}
            part = transport.call('nx_inspect_part', creds)
            if (not isinstance(part.get('part'), dict) or not same_path(part['part'].get('path', ''), args.fixture)
                    or any(part.get(k) != [] for k in ('features', 'sketches', 'bodies'))
                    or part.get('revision_id') != taken['revision_id']):
                raise RuntimeError('current target is not an identified blank work part')
            executor = Executor(transport, creds['ownership_id'], creds['binding_epoch'], part['revision_id'])
            for index in range(count):
                report['stage'] = f'group_{index}'
                group = transport.call('nx_v3_review_disk_source', {'source_path': str(copy), 'group_index': index})
                if (group.get('schema') != 'v3-reviewed-source-group/1' or group.get('group_index') != index
                        or group.get('group_count') != count or group.get('execution_approved') is not False
                        or group.get('source_scope') != 'reviewed identical disk file only'
                        or not isinstance(group.get('steps'), list) or not group['steps']):
                    raise RuntimeError('reviewed group identity, scope or steps invalid')
                execute_steps(executor, group['steps'])
            report['stage'] = 'target_inventory'
            observed = transport.call('nx_inspect_part', creds)
            bodies = observed.get('bodies')
            if (not isinstance(bodies, list) or len(bodies) != 1
                    or not isinstance(bodies[0], dict) or bodies[0].get('is_solid') is not True):
                raise RuntimeError('target must have exactly one solid body')
            if not bytes_equal(ref, independent):
                raise RuntimeError('source or independent copy changed during target build')
            report['stage'] = 'save_reopen'
            saved = operation(transport, 'nx_save_copy', {**creds, 'operation_id': 't31-save-' + uuid.uuid4().hex,
                'target_path': str(args.target), 'reopen': True})
            if (saved.get('saved') is not True or saved.get('reopened') is not True or not args.target.is_file()
                    or any(saved.get('checks', {}).get(k, {}).get('status') != 'VERIFIED'
                           for k in ('expression', 'geometry', 'history', 'associations'))):
                raise RuntimeError('target save/reopen checks incomplete')
            creds = {'ownership_id': saved['new_ownership_id'], 'binding_epoch': saved['new_binding_epoch']}
            report['stage'] = 'return'
            result = transport.call('nx_return', creds)
            if result.get('ownership_state') != 'HUMAN_OWNED' or result.get('safe_for_human') is not True:
                raise RuntimeError('safe return unresolved')
            returned = True
            report.update(status='REVIEWED_TARGET_CREATED', stage='complete',
                          limitations=['No general current-source plan recognition is established.',
                                       'New part G, P and independent persistence remain separate gates.'])
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
    finally:
        write_new(args.evidence_dir / 'summary.json', scrub(report, transport.secrets))
        if returned:
            server.close()
    print(json.dumps(scrub(report, transport.secrets), ensure_ascii=False))
    return 0 if returned else 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pid', type=int, required=True); p.add_argument('--start-ticks', required=True)
    p.add_argument('--source-run', type=Path, required=True); p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--target', type=Path, required=True); p.add_argument('--config', type=Path, required=True)
    p.add_argument('--evidence-dir', type=Path, required=True)
    a = p.parse_args()
    if (a.pid <= 0 or not a.start_ticks.isdecimal() or int(a.start_ticks) <= 0
            or not a.source_run.is_absolute() or not a.source_run.is_dir()
            or not all(x.is_absolute() and x.is_file() for x in (a.fixture, a.config))
            or not a.target.is_absolute() or a.target.suffix.lower() != '.prt' or a.target.exists()
            or not a.target.parent.is_dir() or a.target.parent != a.fixture.parent
            or not a.evidence_dir.is_absolute() or not a.evidence_dir.is_dir() or any(a.evidence_dir.iterdir())):
        p.error('new target in fixture directory, separate source run, config, PID and empty evidence directory required')
    return run(a, McpServer(load_config(a.config)))


if __name__ == '__main__':
    sys.exit(main())
