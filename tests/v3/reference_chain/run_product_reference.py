"""ROOT ONLY: observe one already-open independent reference via the product MCP.

This does not launch NX, open/close a part, create a plan, or write a model.
The process/file locks start here, after the operator opened the part; they do
not establish what bytes NX loaded. Record pre-load protection separately.
Uncertain or failed calls stop without retry, automatic return, or shutdown.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests/v3/smoke_plan')]
from nx_sketch_mcp.config import load_config
from nx_sketch_mcp.server import McpServer
from run_block_once import find_secrets, same_path, scrub, write_new


class KnownBusyBeforeRead(RuntimeError):
    """The bridge explicitly rejected takeover before any model read."""


@contextmanager
def deny_writes(path):
    """Windows read handle shared only for reads; denies writes and deletion."""
    if os.name != 'nt':
        raise RuntimeError('Windows file-sharing protection is required')
    import msvcrt
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    handle = create(str(path), 0x80000000, 1, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        kernel.CloseHandle(handle)
        raise
    with os.fdopen(fd, 'rb') as stream:
        yield stream


def bytes_equal(a, b):
    a.seek(0); b.seek(0)
    while True:
        left, right = a.read(1024 * 1024), b.read(1024 * 1024)
        if left != right:
            return False
        if not left:
            return True


def validate_takeover(result, path, session_epoch):
    if (result.get('ok') is not True or result.get('ownership_state') != 'AI_OWNED'
            or result.get('artifact_scope') != 'saved_independent_copy'
            or result.get('session_epoch') != session_epoch
            or result.get('part_load_state') != 'FullyLoaded'
            or result.get('part_units') != 'Millimeters'
            or result.get('is_modified_before_read') is not False
            or not same_path(result.get('part_path', ''), path)
            or not isinstance(result.get('ownership_id'), str) or not result['ownership_id']
            or type(result.get('binding_epoch')) is not int or result['binding_epoch'] < 1
            or not isinstance(result.get('revision_id'), str) or not result['revision_id']
            or not isinstance(result.get('load_instance_id'), str) or not result['load_instance_id']):
        raise RuntimeError('takeover source identity, clean-before-read, or load state unresolved')


def validate_snapshot(snapshot, taken, path, snapshot_id):
    inventory = snapshot.get('inventory')
    effects = snapshot.get('read_effects')
    if (snapshot.get('ok') is not True or snapshot.get('complete') is not True
            or snapshot.get('inventory_complete') is not True
            or snapshot.get('snapshot_id') != snapshot_id
            or snapshot.get('ownership_state') != 'AI_OWNED'
            or snapshot.get('writes_halted') is not False
            or snapshot.get('read_consistency_fault') is not False
            or snapshot.get('session_epoch') != taken['session_epoch']
            or snapshot.get('load_instance_id') != taken['load_instance_id']
            or snapshot.get('binding_epoch') != taken['binding_epoch']
            or snapshot.get('revision_id') != taken['revision_id']
            or not isinstance(inventory, dict) or not same_path(inventory.get('part_path', ''), path)
            or inventory.get('load_state') != 'FullyLoaded' or inventory.get('units') != 'Millimeters'
            or not isinstance(effects, dict) or effects.get('unchanged') is not True):
        raise RuntimeError('source inventory identity or consistency unresolved')


def wait_ready(call, session_epoch):
    """Poll cached ownership and main-thread dispatch; this cannot read the part.

    The subsequent single takeover establishes work-part path, load and dirty
    state. Failed or ambiguous probes are not retried.
    """
    for index in range(3):
        status = call('nx_bridge_status', {})
        if (status.get('ownership_state') != 'HUMAN_OWNED' or status.get('writes_halted') is not False
                or status.get('session_epoch') != session_epoch or status.get('active_operations') != 0):
            raise RuntimeError('pre-takeover bridge identity, ownership or activity unresolved')
        nonce = 'T31-READY-' + uuid.uuid4().hex
        ping = call('nx_bridge_ping', {'nonce': nonce})
        if (ping.get('ok') is not True or ping.get('nonce') != nonce or ping.get('on_main_thread') is not True
                or ping.get('nx_api_calls') != 0):
            raise RuntimeError('pre-takeover NX main-thread dispatch unresolved')
        if index < 2:
            time.sleep(0.5)


def takeover_when_ready(call, arguments, session_epoch):
    """Retry only the explicit NX_BUSY no-model-read rejection, never UNKNOWN."""
    deadline = time.monotonic() + 30
    while True:
        try:
            return call('nx_takeover', arguments)
        except KnownBusyBeforeRead:
            status = call('nx_bridge_status', {})
            if (status.get('ownership_state') != 'HUMAN_OWNED' or status.get('writes_halted') is not False
                    or status.get('session_epoch') != session_epoch or status.get('active_operations') != 0):
                raise RuntimeError('known busy rejection did not restore idle human ownership')
            if time.monotonic() >= deadline:
                raise RuntimeError('NX remained busy; manual investigation required')
            time.sleep(1)


def run(args, server):
    secrets = set()
    serial = 0
    report = {'status': 'STOP_MANUAL_CHECK', 'stage': 'initialize',
              'source': str(args.source), 'independent_copy': str(args.part),
              'preload_byte_binding': 'NOT_ESTABLISHED_BY_THIS_RUNNER',
              'target_creation': 'BLOCKED: product analysis is planning only'}
    returned = False

    def call(name, arguments, *, require_ok=True):
        nonlocal serial
        serial += 1
        prefix = f'{serial:04d}'
        find_secrets(arguments, secrets)
        write_new(args.evidence_dir / f'{prefix}-request.json', scrub({'tool': name, 'arguments': arguments}, secrets))
        response = server.handle_message({'jsonrpc': '2.0', 'id': serial + 10, 'method': 'tools/call',
                                          'params': {'name': name, 'arguments': arguments}})
        find_secrets(response, secrets)
        write_new(args.evidence_dir / f'{prefix}-response.json', scrub(response, secrets))
        outer = response.get('result', {}) if isinstance(response, dict) else {}
        content = outer.get('structuredContent') if isinstance(outer, dict) else None
        error = content.get('error') if isinstance(content, dict) else None
        if (name == 'nx_takeover' and outer.get('isError') is True and isinstance(error, dict)
                and error.get('code') == 'NX_BUSY'
                and error.get('message') == 'NX UI is busy; no model read was started'):
            raise KnownBusyBeforeRead('NX UI is busy; no model read was started')
        if (outer.get('isError') is True or not isinstance(content, dict)
                or content.get('writes_halted') is True or content.get('state') == 'UNKNOWN'
                or (require_ok and content.get('ok') is not True)):
            raise RuntimeError(f'{name}: failed, missing or uncertain response')
        return content

    try:
        with deny_writes(args.source) as source, deny_writes(args.part) as part:
            if not bytes_equal(source, part):
                raise RuntimeError('independent copy does not match reference bytes')
            report['disk_bytes_before'] = 'equal while both paths deny writes and deletion'
            response = server.handle_message({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                'params': {'protocolVersion': '2025-11-25', 'capabilities': {},
                           'clientInfo': {'name': 't31-product-reference', 'version': '1'}}})
            if not isinstance(response, dict) or 'result' not in response:
                raise RuntimeError('MCP initialization failed')
            server.handle_message({'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {}})
            session_epoch = f'{args.pid}:{args.start_ticks}'
            report['stage'] = 'readiness'
            wait_ready(lambda name, value: call(name, value, require_ok=False), session_epoch)
            report['stage'] = 'takeover'
            taken = takeover_when_ready(call, {'expected_pid': args.pid, 'expected_part_path': str(args.part),
                'expected_session_epoch': session_epoch, 'artifact_scope': 'saved_independent_copy', 'authorize': True}, session_epoch)
            validate_takeover(taken, args.part, session_epoch)
            report['source_session_epoch'] = taken['session_epoch']
            report['source_load_instance_id'] = taken['load_instance_id']
            creds = {key: taken[key] for key in ('ownership_id', 'binding_epoch')}
            if args.include_inventory:
                report['stage'] = 'source_inventory'
                snapshot_id = 'T31-INVENTORY-' + uuid.uuid4().hex
                snapshot = call('nx_inspect_reference', {**creds, 'revision_id': taken['revision_id'], 'snapshot_id': snapshot_id})
                validate_snapshot(snapshot, taken, args.part, snapshot_id)
            report['stage'] = 'product_analysis'
            analysis_id = 'T31-ANALYSIS-' + uuid.uuid4().hex
            analysis_args = {**creds, 'revision_id': taken['revision_id'],
                             'snapshot_id': analysis_id, 'linear': args.linear, 'angular': args.angular}
            if args.reviewed_source:
                analysis_args['source_path'] = str(args.part)
            analysis = call('nx_analyze_v3_reference', analysis_args, require_ok=False)
            if (analysis.get('schema') != 'v3-reference-analysis-response/1'
                    or analysis.get('status') != 'planning_only' or analysis.get('execution_approved') is not False
                    or analysis.get('snapshot_id') != analysis_id or not isinstance(analysis.get('blockers'), list)):
                raise RuntimeError('product analysis contract missing or changed')
            provenance = analysis.get('read_provenance')
            if (not isinstance(provenance, dict) or provenance.get('session_epoch') != taken['session_epoch']
                    or provenance.get('load_instance_id') != taken['load_instance_id']
                    or provenance.get('binding_epoch') != taken['binding_epoch']
                    or provenance.get('revision_id') != taken['revision_id']
                    or provenance.get('snapshot_id') != analysis_id
                    or not same_path(provenance.get('source_path', ''), args.part)
                    or provenance.get('load_state') != 'FullyLoaded' or provenance.get('units') != 'Millimeters'
                    or provenance.get('inventory_complete') is not True
                    or not isinstance(provenance.get('selected_body_id'), str) or not provenance['selected_body_id']
                    or provenance.get('read_effects', {}).get('is_modified_before') is not False
                    or provenance.get('read_effects', {}).get('is_modified_after') is not False):
                raise RuntimeError('product read provenance does not match the clean loaded source')
            if args.reviewed_source:
                reviewed = analysis.get('reviewed_source')
                correspondence = reviewed.get('correspondence') if isinstance(reviewed, dict) else None
                if (not isinstance(reviewed, dict)
                        or reviewed.get('status') != 'current_inventory_matches_reviewed_disk_source'
                        or reviewed.get('execution_approved') is not False
                        or type(reviewed.get('group_count')) is not int or reviewed['group_count'] < 1
                        or not isinstance(reviewed.get('output_id'), str) or not reviewed['output_id']
                        or not isinstance(correspondence, dict)
                        or correspondence.get('schema') != 'p1-inventory-correspondence/1.0'
                        or correspondence.get('current_snapshot_id') != analysis_id
                        or not isinstance(correspondence.get('faces'), list) or not correspondence['faces']):
                    raise RuntimeError('same-read reviewed source correspondence missing or invalid')
                report['reviewed_source'] = {'group_count': reviewed['group_count'],
                                             'output_id': reviewed['output_id'], 'snapshot_id': analysis_id}
            status = call('nx_bridge_status', {}, require_ok=False)
            if (status.get('ownership_state') != 'AI_OWNED' or status.get('writes_halted') is not False
                    or status.get('ownership_id') != creds['ownership_id'] or status.get('binding_epoch') != creds['binding_epoch']):
                raise RuntimeError('post-analysis bridge identity or write halt unresolved')
            if not bytes_equal(source, part):
                raise RuntimeError('reference or copy changed during analysis')
            report['disk_bytes_after'] = 'equal while both paths deny writes and deletion'
            report['stage'] = 'return'
            result = call('nx_return', creds)
            if result.get('ownership_state') != 'HUMAN_OWNED' or result.get('safe_for_human') is not True:
                raise RuntimeError('safe return unresolved')
            returned = True
            report.update(status='SOURCE_ANALYZED_TARGET_BLOCKED', stage='complete', blockers=analysis['blockers'])
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
    finally:
        write_new(args.evidence_dir / 'summary.json', scrub(report, secrets))
        if returned:
            server.close()
    print(json.dumps(scrub(report, secrets), ensure_ascii=False))
    return 0 if returned else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--start-ticks', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--part', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--linear', type=float, default=0.001)
    parser.add_argument('--angular', type=float, default=0.0001)
    parser.add_argument('--include-inventory', action='store_true', help='separate full inventory only when required by a variant oracle')
    parser.add_argument('--reviewed-source', action='store_true', help='request exact reviewed-source linkage on the same live read')
    args = parser.parse_args()
    import math
    if (args.pid <= 0 or not args.start_ticks.isdecimal() or int(args.start_ticks) <= 0
            or not all(p.is_absolute() and p.is_file() for p in (args.source, args.part, args.config))
            or not args.evidence_dir.is_absolute() or not args.evidence_dir.is_dir() or any(args.evidence_dir.iterdir())
            or os.path.samefile(args.source, args.part)
            or not all(math.isfinite(v) and v > 0 for v in (args.linear, args.angular))):
        parser.error('provide separate existing absolute source/copy/config, empty evidence directory, positive identity and tolerances')
    return run(args, McpServer(load_config(args.config)))


if __name__ == '__main__':
    sys.exit(main())
