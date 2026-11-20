"""Resolve the project evidence bound to an installed application.

Source checkouts use their own root. An installed app must carry a binding
written by the installer, which must agree with its installation metadata. This
is a local dependency, not an assertion of evidence freshness or native support.
"""
import json
from pathlib import Path


def project_root():
    app = Path(__file__).resolve().parents[3]
    binding = app / 'v3-runtime-binding.json'
    if not binding.exists():
        return app
    try:
        from ..jsonutil import loads_unique
        spec = loads_unique(binding.read_text(encoding='utf-8-sig'))
        metadata = loads_unique((app.parent / 'installation.json').read_text(encoding='utf-8-sig'))
        if (not isinstance(spec, dict) or set(spec) != {'schema', 'source_root'}
                or spec['schema'] != 'v3-project-binding/1' or not isinstance(metadata, dict)):
            raise ValueError('invalid installation binding')
        source, declared = spec['source_root'], metadata.get('source_root')
        if not isinstance(source, str) or not source or not isinstance(declared, str):
            raise ValueError('missing installation source_root')
        a, b = Path(source), Path(declared)
        if not a.is_absolute() or not b.is_absolute():
            raise ValueError('source_root must be absolute')
        a, b = a.resolve(strict=True), b.resolve(strict=True)
        if a != b or not (a / 'src/nx_sketch_mcp/v3').is_dir():
            raise ValueError('installation source_root mismatch or unavailable')
        return a
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise RuntimeError('V3 project evidence binding is unavailable or invalid') from exc
