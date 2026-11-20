"""Supervise one authorized, isolated NX read of a saved parametric-family part.

The durable coordination record is owned by the product, not the caller's
observation directory. UNKNOWN retains the shared journal stop marker and is
never replayed or automatically recovered.
"""
from __future__ import annotations
from contextlib import ExitStack
import json
import os
from pathlib import Path
from .project_root import project_root
import shutil
import subprocess
import sys

from .. import journal
from .reference_evidence import _locked_read, _same_bytes


def _absolute(value, field):
    if not isinstance(value, str) or not value.strip() or not Path(value).is_absolute():
        raise ValueError(field + ' must be an absolute path')
    path = Path(value)
    if str(path).startswith('\\\\'):
        raise ValueError(field + ' must be a local path')
    if os.name == 'nt':
        import ctypes
        root = path.anchor
        if not root or ctypes.windll.kernel32.GetDriveTypeW(root) != 3:
            raise ValueError(field + ' must be on a fixed local drive')
    return path


def submit(request):
    journal._windows()
    if not isinstance(request, dict) or set(request) != {'operation_id', 'source_path', 'output_path', 'authorize'}:
        raise ValueError('operation_id, source_path, output_path and authorize are required')
    ident = journal._id(request['operation_id'])
    if request['authorize'] is not True:
        raise ValueError('explicit authorize=true is required')
    source = _absolute(str(_absolute(request['source_path'], 'source_path').resolve(strict=True)), 'source_path')
    requested_output = _absolute(request['output_path'], 'output_path')
    parent = _absolute(str(requested_output.parent.resolve(strict=True)), 'output_path')
    output = parent / requested_output.name
    if not source.is_file() or source.suffix.lower() != '.prt':
        raise ValueError('source must be an existing .prt file')
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise ValueError('output must be a new directory with an existing parent')
    root = journal._root()
    operations = root / 'operations'
    operations.mkdir(parents=True, exist_ok=True)
    directory = operations / ident
    try:
        directory.mkdir()
    except FileExistsError as exc:
        raise ValueError('operation_id already reserved; replay is prohibited') from exc
    record = {'schema': 'v3-parametric-file-operation/1', 'operation_id': ident, 'status': 'STARTING',
              'source_path': str(source), 'output_path': str(output), 'created_at': journal._now(),
              'dispatched': False}
    journal._json_write(directory / 'state.json', record)
    try:
        env = os.environ.copy()
        package_root = str(Path(__file__).resolve().parents[2])
        env['PYTHONPATH'] = package_root
        subprocess.Popen([sys.executable, '-m', 'nx_sketch_mcp.v3.family_supervisor', '--supervise', ident],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         env=env, close_fds=True,
                         creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
    except OSError as exc:
        record.update(status='FAILED', error='supervisor could not start: ' + str(exc), finished_at=journal._now())
        journal._json_write(directory / 'state.json', record)
    return record


def get(ident):
    directory = journal._root() / 'operations' / journal._id(ident)
    try:
        result = journal._read(directory / 'state.json')
    except FileNotFoundError as exc:
        if directory.is_dir():
            return {'schema': 'v3-parametric-file-operation/1', 'operation_id': ident, 'status': 'UNKNOWN',
                    'error': 'reserved operation has no state; do not replay'}
        raise ValueError('operation_id not found') from exc
    if result.get('schema') != 'v3-parametric-file-operation/1':
        raise ValueError('operation is not a parametric-file read')
    result['state_is_last_recorded'] = True
    result['supervisor_health'] = 'unknown'
    if result.get('status') == 'SUCCEEDED':
        try:
            plan = journal._read(directory / 'family-plan.json')
            if plan.get('schema') != 'p7-parametric-family-plan/1' or plan.get('execution_approved') is not False:
                raise ValueError('invalid saved family plan')
            result['family_plan'] = plan
        except (OSError, ValueError):
            result.update(status='UNKNOWN', error='product result unavailable; do not replay')
    return result


def _supervise(ident):
    root = journal._root()
    directory = root / 'operations' / journal._id(ident)
    state = directory / 'state.json'
    try:
        fd = os.open(directory / 'supervisor.claim', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return
    os.close(fd)
    record = journal._read(state)
    if record.get('schema') != 'v3-parametric-file-operation/1' or record.get('status') != 'STARTING':
        return
    marker = root / 'active.json'
    kernel = handle = proc = None
    marked = dispatched = False
    try:
        kernel, handle = journal._gate(root)
        if marker.exists():
            record.update(status='REJECTED', error='journal coordination marker already exists', finished_at=journal._now())
            journal._json_write(state, record)
            return
        with marker.open('x', encoding='utf8') as stream:
            json.dump({'operation_id': ident, 'created_at': journal._now()}, stream)
            stream.flush(); os.fsync(stream.fileno())
        marked = True
        busy = journal._processes()
        if busy:
            record.update(status='REJECTED', error='NX-related processes are present', processes=busy, finished_at=journal._now())
            journal._json_write(state, record)
            marker.unlink(); marked = False
            return
        source = _absolute(str(_absolute(record['source_path'], 'source_path').resolve(strict=True)), 'source_path')
        requested_output = _absolute(record['output_path'], 'output_path')
        parent = _absolute(str(requested_output.parent.resolve(strict=True)), 'output_path')
        output = parent / requested_output.name
        output.mkdir()
        local_copy = output / 'source-copy.prt'
        raw_path = directory / 'family-observation.json'
        with ExitStack() as stack:
            original = stack.enter_context(_locked_read(source))
            with local_copy.open('xb') as dest:
                original.seek(0); shutil.copyfileobj(original, dest, 1024 * 1024)
                dest.flush(); os.fsync(dest.fileno())
            copy = stack.enter_context(_locked_read(local_copy))
            if not _same_bytes(original, copy):
                raise ValueError('source and protected copy differ')
            project = project_root()
            network = project / 'tools/verify-m2-local-network.ps1'
            network_report = directory / 'network-prelaunch.json'
            if not network.is_file():
                raise ValueError('network verification script unavailable')
            preflight = subprocess.run(['pwsh.exe', '-NoProfile', '-NonInteractive', '-File', str(network),
                                        '-OutputPath', str(network_report)], stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            if preflight.returncode != 0 or journal._read(network_report).get('inbound_isolation_configured') is not True:
                raise ValueError('required NX inbound firewall configuration not established')
            for key in ('UGII_CUSTOM_DIRECTORY_FILE', 'UGII_USER_DIR', 'UGII_SITE_DIR', 'UGII_VENDOR_DIR'):
                if os.environ.get(key):
                    raise ValueError('inherited NX customization requires review: ' + key)
            nx_root = Path(journal.RUN_JOURNAL).resolve().parent.parent
            version_report = directory / 'nx-version-prelaunch.json'
            version_check = project / 'tools/verify-v3-nx2506.ps1'
            if not version_check.is_file():
                raise ValueError('NX version verification script unavailable')
            version = subprocess.run(['pwsh.exe', '-NoProfile', '-NonInteractive', '-File', str(version_check),
                                      '-NxRoot', str(nx_root), '-OutputPath', str(version_report)],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
            if version.returncode != 0 or journal._read(version_report).get('status') != 'PASS':
                raise ValueError('reviewed NX2506 version not established')
            for evidence_path in (network_report, version_report):
                with _locked_read(evidence_path) as verified, (output / evidence_path.name).open('xb') as published:
                    shutil.copyfileobj(verified, published)
                    published.flush(); os.fsync(published.fileno())
            image_kernel = journal._kernel()
            image_handle = image_kernel.CreateFileW(str(nx_root / 'NXBIN/ugraf.exe'), 0x80000000, 0, None, 3, 0x80, None)
            import ctypes
            if image_handle == ctypes.c_void_p(-1).value:
                raise OSError('cannot lock NX GUI executable against competing starts')
            stack.callback(image_kernel.CloseHandle, image_handle)
            capture = Path(__file__).with_name('parametric_family_capture.py')
            wrapper = Path(journal.__file__).with_name('journal_wrapper.py')
            if not capture.is_file() or not wrapper.is_file() or not Path(journal.RUN_JOURNAL).is_file():
                raise ValueError('fixed product journal or NX runner unavailable')
            frozen = directory / 'family-journal.py'
            with capture.open('rb') as src, frozen.open('xb') as dest:
                shutil.copyfileobj(src, dest)
            model_observation = directory / 'model-observation.json'
            command = [journal.RUN_JOURNAL, str(wrapper), '-args', str(frozen), str(model_observation), str(local_copy), str(raw_path)]
            child_env = os.environ.copy()
            child_env['UGII_BASE_DIR'] = str(nx_root)
            child_env['UGII_ROOT_DIR'] = str(nx_root / 'UGII')
            child_env['PATH'] = str(nx_root / 'NXBIN') + os.pathsep + child_env.get('PATH', '')
            if journal._processes():
                raise ValueError('NX-related processes appeared before batch dispatch')
            record.update(status='RUNNING', started_at=journal._now())
            journal._json_write(state, record)
            with (output / 'stdout.bin').open('xb') as out, (output / 'stderr.bin').open('xb') as err:
                proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                        cwd=str(output), env=child_env, close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW)
                dispatched = True
                # Run this callback before closing the source locks even if
                # logging, parsing, or wait itself raises unexpectedly.
                stack.callback(lambda child: child.wait() if child.poll() is None else None, proc)
                record.update(dispatched=True, runner_pid=proc.pid)
                journal._json_write(state, record)
                try:
                    code = proc.wait(timeout=1200)
                except subprocess.TimeoutExpired:
                    record.update(status='UNKNOWN', error='runner timeout; do not retry', finished_at=journal._now())
                    journal._json_write(state, record)
                    proc.wait()
                    return
            if code != 0 or journal._completed_model_observation(model_observation) != 'RETURNED':
                raise RuntimeError('runner or model observation did not complete successfully')
            if journal._processes():
                raise RuntimeError('NX-related processes remain or appeared after batch exit')
            if not _same_bytes(original, copy):
                raise RuntimeError('source or protected copy changed')
            from ..jsonutil import loads_unique
            with _locked_read(raw_path) as captured:
                raw_observation = captured.read(64 * 1024 * 1024 + 1)
            if len(raw_observation) > 64 * 1024 * 1024:
                raise RuntimeError('capture exceeds the observation limit')
            observation = loads_unique(raw_observation)
            if not isinstance(observation, dict):
                raise RuntimeError('capture is not an object')
            wrapper_record = journal._read(model_observation)
            changes = wrapper_record.get('changes', {})
            if (wrapper_record.get('before', {}).get('parts') != []
                    or wrapper_record.get('after', {}).get('parts') != []
                    or any(changes.get(key) != [] for key in ('added', 'removed', 'modified'))):
                raise RuntimeError('batch wrapper did not establish empty unchanged sessions before and after')
            with (output / 'observation.json').open('xb') as evidence:
                evidence.write(raw_observation)
                evidence.flush(); os.fsync(evidence.fileno())
            same_source = os.path.samefile(observation.get('source_path', ''), local_copy)
            if (observation.get('status') == 'SAFE_REJECTED' and observation.get('safe_rejection') is True
                    and observation.get('closed_without_save') is True
                    and observation.get('no_parts_remaining') is True and same_source):
                record.update(status='REJECTED', exit_code=code, finished_at=journal._now(),
                              error='saved part was safely rejected: ' + str(observation.get('error', 'unsupported part'))[:500])
                journal._json_write(state, record)
                marker.unlink(); marked = False
                return
            if (observation.get('status') != 'PASS' or observation.get('dirty_before') is not False
                    or observation.get('dirty_after') is not False or observation.get('closed_without_save') is not True
                    or observation.get('nx_build') != 'v2506.0.0.1700'
                    or observation.get('nx_build_source') != 'Session.GetEnvironmentVariableValue(NX_FULL_VERSION)'
                    or not same_source):
                raise RuntimeError('capture identity, runtime, clean state or close proof missing')
            from .parametric_family import recognize_parametric_family, FamilyError
            from .regions.common import InventoryError
            try:
                plan = recognize_parametric_family(observation)
            except (FamilyError, InventoryError) as exc:
                # NX has exited, the protected source/copy are unchanged and
                # capture proved clean close. An unsupported family is a known
                # rejection, not an uncertain native side effect.
                record.update(status='REJECTED', exit_code=code, finished_at=journal._now(),
                              error='source is outside the supported parametric family: ' + str(exc))
                journal._json_write(state, record)
                marker.unlink(); marked = False
                return
            journal._json_write(directory / 'family-plan.json', plan)
            journal._json_write(output / 'family-plan.json', plan)
            record.update(status='SUCCEEDED', exit_code=code, finished_at=journal._now(),
                          source_scope='saved file; protected copy in separate NX batch',
                          limitations=['Candidate does not establish complete trimmed geometry or native edit validity.'])
            journal._json_write(state, record)
            marker.unlink(); marked = False
    except Exception as exc:
        record.update(status='UNKNOWN' if dispatched else 'FAILED', error=f'{type(exc).__name__}: {exc}',
                      dispatched=dispatched, finished_at=journal._now())
        try:
            journal._json_write(state, record)
            if marked and not dispatched:
                marker.unlink(); marked = False
        finally:
            if proc is not None and proc.poll() is None:
                proc.wait()
    finally:
        if kernel is not None and handle is not None:
            kernel.CloseHandle(handle)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--supervise':
        _supervise(sys.argv[2])
    else:
        sys.exit(2)
