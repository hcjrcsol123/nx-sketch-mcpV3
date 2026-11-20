"""Offline parameter entry point for a portable UG11 generated bundle.

Run with --overrides FILE --output NEW_DIRECTORY. No NX session is started.
"""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent
PROFILE = {'release': 'NX V11.0', 'assembly_version': '11.0.0.33',
           'file_version': '11.0.0.33', 'product_version': '11.0.0.33',
           'journal_language': 'C#', 'ui_language_environment': 'simpl_chinese'}
MARKER = '@UG11_BUNDLE_DRIVER_EDITS@'


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def load(path):
    with Path(path).open(encoding='utf-8-sig') as stream:
        return json.load(stream, object_pairs_hook=_pairs,
                         parse_constant=lambda s: (_ for _ in ()).throw(ValueError('non-finite JSON number')))


def _number(value):
    if type(value) not in (int, float):
        raise ValueError('driver values must be finite numbers')
    try:
        val = float(value)
    except (OverflowError, ValueError):
        raise ValueError('driver values must be finite numbers') from None
    if not math.isfinite(val):
        raise ValueError('driver values must be finite numbers')
    out = repr(val)
    return out if any(c in out for c in '.eE') else out + '.0'


def _q(value):
    return json.dumps(value, ensure_ascii=True)


def _validate():
    profile = load(ROOT / 'profile.json')
    if profile != PROFILE:
        raise ValueError('unsupported or changed bundle profile')
    schema = load(ROOT / 'parameter-schema.json')
    ir = load(ROOT / 'logic-ir.json')
    manifest = load(ROOT / 'manifest.json')
    if (schema.get('schema') != 'ug11-bundle-parameters/1' or
        ir.get('schema') != 'ug11-bundle-ir/1' or
        manifest.get('schema') != 'ug11-compiler/1' or
        manifest.get('execution_approved') is not False or
        manifest.get('verify_edits') is not False or
        manifest.get('profile') != PROFILE):
        raise ValueError('invalid bundle metadata')
    drivers = schema.get('drivers')
    trace = ir.get('driver_map')
    windows = ir.get('driver_windows')
    steps = ir.get('steps')
    if (not isinstance(drivers, dict) or len(drivers) != 104 or
        not isinstance(trace, dict) or set(drivers) != set(trace) or
        not isinstance(windows, dict) or set(windows) != set(drivers) or
        not isinstance(steps, list) or not steps):
        raise ValueError('incomplete parameter or logic IR')
    expressions = {}
    ids = []
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get('id'), str):
            raise ValueError('invalid IR step')
        ids.append(step['id'])
        if step.get('kind') == 'expression':
            name = step.get('name')
            if not isinstance(name, str) or name in expressions:
                raise ValueError('invalid IR expression')
            expressions[name] = (step.get('unit', 'mm'), step.get('formula'))
    if len(set(ids)) != len(ids) or manifest.get('checkpoints') != ids:
        raise ValueError('inconsistent operation checkpoints')
    if (manifest.get('output_id') != ir.get('output_id') or
        manifest.get('operation_map') != ir.get('operation_map') or
        manifest.get('driver_map') != trace or
        manifest.get('design_guidance') != ir.get('design_guidance')):
        raise ValueError('inconsistent IR and manifest')
    seen = set()
    for key, row in drivers.items():
        if not isinstance(row, dict) or set(row) != {'expression', 'unit', 'default', 'minimum', 'maximum'}:
            raise ValueError('invalid driver schema')
        name = row['expression']
        record = trace[key]
        if (not isinstance(record, dict) or name in seen or name not in expressions or
            record.get('expression') != name or row['unit'] != expressions[name][0] or
            row['unit'] != record.get('unit') or not record.get('consumers')):
            raise ValueError('invalid driver mapping')
        seen.add(name)
        _number(row['minimum']); _number(row['maximum']); _number(row['default'])
        try:
            actual_default = float(expressions[name][1])
        except (TypeError, ValueError, OverflowError):
            raise ValueError('invalid IR driver default') from None
        if not math.isfinite(actual_default) or actual_default != row['default'] or not row['minimum'] <= actual_default <= row['maximum']:
            raise ValueError('parameter default does not match fixed IR')
        if windows[key] != [row['minimum'], row['maximum']]:
            raise ValueError('parameter window does not match fixed IR')
        if row['minimum'] > row['maximum']:
            raise ValueError('invalid driver window')
    template = (ROOT / 'journal.template.cs').read_text(encoding='utf-8')
    journal = (ROOT / 'journal.cs').read_text(encoding='utf-8')
    if template.count(MARKER) != 1 or template.replace(MARKER, '\n') != journal:
        raise ValueError('inconsistent journal template and default journal')
    # Bundle files are explicit inputs, even where their contents are documentation.
    for name in ('parameters.json', 'README.md', 'Run-Bundle.ps1'):
        if not (ROOT / name).is_file():
            raise ValueError('missing bundle file: ' + name)
    return drivers, manifest, template


def _render(overrides_path):
    drivers, manifest, template = _validate()
    edits = load(overrides_path)
    if not isinstance(edits, dict):
        raise ValueError('overrides must be a JSON object')
    native = {}
    for key, value in edits.items():
        if key not in drivers:
            raise ValueError('unknown independent driver: ' + key)
        _number(value)
        row = drivers[key]
        if not row['minimum'] <= value <= row['maximum']:
            raise ValueError('driver outside proven ideal window: ' + key)
        native[row['expression']] = value
    lines = ['P.Expressions.EditWithUnits(E[%s],E[%s].Units,%s);' % (_q(k), _q(k), _q(_number(v)))
             for k, v in native.items()]
    edit_text = '\n'.join(lines)
    if native:
        edit_text += '\nUpdateModel();\n' + '\n'.join(
            'Need(Math.Abs(E[%s].GetValueUsingUnits(Expression.UnitsOption.Expression)-(%s))<1e-8,"requested driver value mismatch");' % (_q(k), _number(v))
            for k, v in native.items())
    edit_text += '\n'
    rendered = template.replace(MARKER, edit_text)
    manifest['driver_edits'] = native
    return rendered, manifest


def check_input(overrides_path, input_dir):
    rendered, manifest = _render(overrides_path)
    folder = Path(input_dir)
    if (folder / 'journal.cs').read_bytes() != rendered.replace('\n', '\r\n').encode('utf-8'):
        raise ValueError('journal does not match current parameters and bundle')
    if load(folder / 'manifest.json') != manifest:
        raise ValueError('manifest does not match current parameters and bundle')
    return folder


def generate(overrides_path, output):
    rendered, manifest = _render(overrides_path)
    target = Path(output).absolute()
    if target.exists() or target.is_symlink():
        raise FileExistsError('output already exists')
    if not target.parent.is_dir():
        raise ValueError('output parent must exist')
    stage = Path(tempfile.mkdtemp(prefix='.ug11-bundle-', dir=target.parent))
    try:
        (stage / 'journal.cs').write_bytes(rendered.replace('\n', '\r\n').encode('utf-8'))
        (stage / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')
        if os.name == 'nt':
            os.rename(stage, target)
        else:
            target.mkdir()
            published = []
            try:
                for name in ('journal.cs', 'manifest.json'):
                    item = stage / name
                    os.link(item, target / name)
                    published.append(item)
            except BaseException:
                for item in published:
                    dest = target / item.name
                    try:
                        if os.path.samefile(item, dest): dest.unlink()
                    except OSError:
                        pass
                try: target.rmdir()
                except OSError: pass
                raise
    finally:
        if stage.exists(): shutil.rmtree(stage)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overrides', required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--check-input', type=Path)
    args = parser.parse_args(argv)
    try:
        target = (generate(args.overrides, args.output) if args.output is not None
                  else check_input(args.overrides, args.check_input))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, 'bundle generation failed: %s\n' % exc)
    print(('Generated only; NX has not run:' if args.output is not None else 'Input matches current parameters; NX has not run:'), target)


if __name__ == '__main__':
    main()
