"""Bound reuse of the reviewed P3 construction for an identical disk source.

This is an offline evidence path, not a live NX identity, dirty-state or write
permission check. The returned plan is valid for use only inside the lease.
Evidence artifacts are inherited as trusted project records, not authenticated.
"""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
from .project_root import project_root


class ReferenceEvidenceError(ValueError):
    """The input cannot be associated with the reviewed evidence."""


_ROOT = project_root()
_P1 = Path('workspace/v3/p1/P1-20261108-01/source-before.prt')
_P3 = Path('workspace/v3/p3/P3-CARRIERS-01/source-before.prt')
_P1_SNAPSHOT = Path('workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json')
_BASE = Path('workspace/v3/p3/P3-FINAL-PLAN-01')
_BUILDER = _BASE / 'build_plan.py'
_ARCHIVE = _BASE / 'final-plan.json'
_FROZEN_SOURCE = _BASE / 'source'
_CODE = (_BUILDER, Path('src/nx_sketch_mcp/v3/p3_integration.py'),
         Path('src/nx_sketch_mcp/v3/flank_construction.py'),
         Path('src/nx_sketch_mcp/v3/regions/common.py'))


def _locked_read(path):
    """Open a Windows file denying concurrent write/delete for handle lifetime."""
    if os.name != 'nt':
        raise ReferenceEvidenceError('source read locking requires Windows')
    import ctypes
    import msvcrt
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    handle = create(str(path), 0x80000000, 1, None, 3, 0x80, None)
    if handle == wintypes.HANDLE(-1).value:
        raise OSError(ctypes.get_last_error(), 'cannot open read-locked evidence file', str(path))
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        kernel.CloseHandle(handle)
        raise
    return os.fdopen(fd, 'rb')


def _same_bytes(left, right):
    left.seek(0)
    right.seek(0)
    while True:
        a, b = left.read(1024 * 1024), right.read(1024 * 1024)
        if a != b:
            return False
        if not a:
            return True


def _identity(stream):
    stat = os.fstat(stream.fileno())
    return stat.st_dev, stat.st_ino


@contextmanager
def bound_reference_plan(source_path):
    """Yield a freshly assembled plan while an identical disk source is locked.

    Reject aliases to either independent baseline. Each invocation compares
    content anew; neither paths nor IDs are cache keys. This does not prove
    an NX in-memory part equals the file, or certify changed dimensions/pose.
    Consumers must complete their offline use before the context exits.
    """
    root = _ROOT
    with ExitStack() as stack:
        try:
            candidate = stack.enter_context(_locked_read(Path(source_path).resolve(strict=True)))
            p1 = stack.enter_context(_locked_read(root / _P1))
            p3 = stack.enter_context(_locked_read(root / _P3))
            if len({_identity(candidate), _identity(p1), _identity(p3)}) != 3:
                raise ReferenceEvidenceError('source and independent baselines must be distinct files')
            if not _same_bytes(candidate, p1) or not _same_bytes(p1, p3):
                raise ReferenceEvidenceError('source content differs from the reviewed reference')
            for path in _CODE:
                current = stack.enter_context(_locked_read(root / path))
                frozen = stack.enter_context(_locked_read(root / _FROZEN_SOURCE / path))
                if _identity(current) == _identity(frozen) or not _same_bytes(current, frozen):
                    raise ReferenceEvidenceError('P3 assembler source differs from its frozen copy: ' + str(path))
                installed_path = Path(__file__).resolve().parents[3] / path
                if installed_path != root / path and path.parts[0] == 'src':
                    installed = stack.enter_context(_locked_read(installed_path))
                    if not _same_bytes(installed, frozen):
                        raise ReferenceEvidenceError('installed P3 source differs from its frozen copy: ' + str(path))
            # Keep the accepted P1 inventory stable during both assembly and
            # current-snapshot correspondence in this same source lease.
            stack.enter_context(_locked_read(root / _P1_SNAPSHOT))
            archive = stack.enter_context(_locked_read(root / _ARCHIVE))
            archive.seek(0)
            reference = json.load(archive)
            spec = importlib.util.spec_from_file_location('_bound_p3_assembler', root / _BUILDER)
            if spec is None or spec.loader is None:
                raise ReferenceEvidenceError('P3 assembler unavailable')
            builder = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(builder)
            plan = builder.build(root)
            if plan != reference or plan.get('p3_ready') is not True or plan.get('execution_approved') is not False:
                raise ReferenceEvidenceError('P3 rebuild differs from accepted planning evidence')
        except ReferenceEvidenceError:
            raise
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ReferenceEvidenceError('reference evidence unavailable or invalid') from exc
        yield deepcopy(plan)
