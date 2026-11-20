"""Export a reviewed UG11 compiler result as a portable, offline bundle."""
import argparse
from copy import deepcopy
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

from .ug11.compiler import _load, lower_plan, render_journal, _WINDOW
from .ug11.profile import OBSERVED

MARKER = '@UG11_BUNDLE_DRIVER_EDITS@'
README = r'''# UG11 可搬移建模包

本包是离线生成的候选建模脚本；生成本包不代表 NX 已运行或模型已验收。
复制整个文件夹到目标电脑。编译参数需要 Python 3.10 或更高版本的标准库（当前离线实测 3.14.7），不需要源码仓库、
源 PRT、MCP 或 NX。运行模型需要匹配 profile.json 的 UG11 安装环境。

## 参数和限制

parameters.json 是默认可编辑参数文件，空对象 `{}` 表示使用默认模型。
也可另建 JSON 覆写文件。键为 parameter-schema.json 中的逻辑驱动 ID，
值为有限数字；每项默认值、单位及含端点的最小、最大值见该文件，slot.axis_z 的
单位是 mm。允许同时设置多个参数，未知键、重复键、非数字、非有限值及
越界值均会拒绝。104 项区间是联合数学窗口，窗口内任意组合并不等于原生
验收。P6 曾对 104 项分别编辑及 5 个组合做原生验证；首次交付包链
的实际原生验证属于后续 T31，本包生成成功不代表该验证已完成。logic-ir.json 是固定只读建模逻辑，含有序操作、表达式、坐标、
逻辑来源 ID、驱动消费映射和仅供参考的设计建议，不能作为参数入口修改。
Journal 中的 Tag 查询只用于当前原生会话，包不携带历史会话 Tag。

## 默认预检

以下命令在 Windows PowerShell 中从包目录运行，请将 UG11 安装目录改成
实际位置；`C:\ug11-result` 的父目录需存在且结果目录不能已存在。预检
不会创建模型；需要 Python 可通过 -PythonExe 指定其完整路径。

    $env:UGII_LANG = 'simpl_chinese'
    .\Run-Bundle.ps1 -NxInstallDir 'C:\Siemens\NX11' -OutputDir 'C:\ug11-result'

如当前会话、环境或预检不通过，按终端报错处理；预检通过不等于原生验证。
明确选择运行时，在上述命令末尾加 `-Execute`。执行会检查当前参数与
Journal 和清单一致，并复制输入到新结果目录；请先协调独占运行环境。

## 非默认参数

在包目录建立 `custom.json`（可用任何路径），例如内容为：

    {"slot.width": 5.01}

父目录必须存在，下列 generated 和 result 目录都必须尚不存在。下面两条
命令以同一份参数文件生成并预检；修改参数后必须重新生成，启动器会拒绝
不匹配的文件：

    python .\bundle_runtime.py --overrides .\custom.json --output C:\ug11-generated
    .\Run-Bundle.ps1 -NxInstallDir 'C:\Siemens\NX11' -OutputDir 'C:\ug11-result' -InputDir 'C:\ug11-generated' -Overrides .\custom.json

在第二条命令末尾加 `-Execute` 才会启动 NX。默认参数无需生成目录，直接
使用包内 journal.cs；默认参数已更改后也需先生成并指定 -InputDir。

成功运行的结果目录包含 blank.prt、native-evidence.tsv、journal.cs、
manifest.json、runner-stdout.txt 和 runner-stderr.txt。查看终端运行状态及
native-evidence.tsv 末尾的 `result` 记录；运行失败、缺少 PASS 或状态未知
时不能视为成功，也不要直接重放同一目录，应保留日志并排查。几何和编辑
行为仍需按实际用途独立验证；design_guidance 需人工确认后采用。
'''


def _clean(value):
    if isinstance(value, dict):
        for key in value:
            if any(word in key.lower() for word in ('source_path', 'session_tag', 'ownership', 'credential')):
                raise ValueError('private field in portable IR: ' + key)
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    if isinstance(value, str):
        if value == 'Analysis: workspace/v3/p3/P3-ANALYSIS-03/model-plan.json':
            return 'Analysis: logical model plan'
        if value.startswith('Explicit decision confirms equal angular spacing in observation snapshot '):
            return 'Explicit decision confirms equal angular spacing; the applicable members are mapped to the current plan.'
        if value == 'Decision: docs/v3/decisions/p3-shared-22-user-decision.json':
            return 'Decision: P3-USER-22-SHARED-01'
        if value.startswith('Current member identities are scoped to P1 snapshot '):
            return 'Current member identities are scoped to the reviewed source face set.'
        if 'workspace/' in value or '\\\\' in value or __import__('re').search(r'(?i)(?:^|\s)[a-z]:[\\/]', value):
            raise ValueError('environment path in portable IR')
    return value


def _portable_domain(value):
    if isinstance(value, dict):
        return {k: _portable_domain(v) for k, v in value.items()
                if 'evidence' not in k.lower() and 'path' not in k.lower() and 'tag' not in k.lower()}
    if isinstance(value, list):
        return [_portable_domain(v) for v in value]
    return value


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8', newline='\n')


def export(plan, root, output):
    root = Path(root)
    lowered = lower_plan(plan, root)
    journal = render_journal(lowered)
    if MARKER in journal:
        raise ValueError('journal marker already exists')
    template = render_journal(lowered, _bundle_marker=MARKER)
    if template.count(MARKER) != 1 or template.replace(MARKER, '\n') != journal:
        raise ValueError('journal template does not reproduce default')
    proof = _load(root / _WINDOW)
    if proof.get('schema') != 'p4-joint-ideal-edit-window/1' or proof.get('status') != 'mathematical_window_proved':
        raise ValueError('missing proven joint window')
    windows = proof['driver_windows']
    trace = deepcopy(lowered['driver_map'])
    if len(trace) != 104 or set(trace) != set(windows):
        raise ValueError('incomplete joint window')
    expressions = {s['name']: s for s in lowered['steps'] if s['kind'] == 'expression'}
    drivers = {}
    for key, row in trace.items():
        name = row['expression']
        if name not in expressions or row['unit'] != expressions[name].get('unit', 'mm') or len(windows[key]) != 2:
            raise ValueError('driver unit or window mismatch: ' + key)
        low, high = map(float, windows[key])
        if not math.isfinite(low) or not math.isfinite(high) or low > high:
            raise ValueError('invalid ideal window: ' + key)
        default = float(expressions[name]['formula'])
        if not math.isfinite(default) or not low <= default <= high:
            raise ValueError('invalid driver default: ' + key)
        drivers[key] = {'expression': name, 'unit': row['unit'], 'default': default, 'minimum': low, 'maximum': high}
    if drivers['slot.axis_z']['unit'] != 'mm':
        raise ValueError('slot.axis_z unit mismatch')
    fieldset = {'id', 'classification', 'value', 'depends_on', 'expression', 'unit', 'consumers', 'definition'}
    parameters = {group: [{k: v for k, v in row.items() if k in fieldset}
                          for row in plan['parameters'][group]]
                  for group in ('regional', 'c5', 'fixed_auxiliaries')}
    # Correct the historical P3 record to the P6 native expression unit contract.
    for rows in parameters.values():
        for row in rows:
            if row.get('id') == 'slot.axis_z': row['unit'] = 'mm'
    reviewed = {'schema': plan['schema'], 'source_face_set_id': 'P1-source-face-set-235',
                'unit': plan['unit'], 'frame': plan['frame'],
                'source_responsibility': plan['source_responsibility'],
                'face_construction_bindings': [
                    {k: _portable_domain(row[k]) for k in ('source_face', 'responsible_region', 'construction_nodes', 'finite_domain', 'material_role') if k in row}
                    for row in plan['face_construction_bindings']],
                'construction_nodes': [
                    {k: v for k, v in row.items() if k in ('id', 'operation', 'depends_on', 'parameter_dependencies', 'target', 'tools')}
                    for row in plan['construction']['nodes']],
                'parameters': parameters,
                'design_decision_ids': [row['record']['decision_id'] for row in plan['user_decisions']]}
    if len(reviewed['face_construction_bindings']) != 235:
        raise ValueError('incomplete source face mapping')
    ir = _clean({'schema': 'ug11-bundle-ir/1', 'reviewed_plan': reviewed, 'steps': lowered['steps'],
                 'output_id': lowered['output_id'], 'operation_map': lowered['operation_map'],
                 'driver_map': trace, 'driver_windows': {key: [row['minimum'], row['maximum']] for key, row in drivers.items()},
                 'design_guidance': lowered['design_guidance']})
    steps = ir['steps']; mapping = ir['operation_map']
    reverse = {step['id']: [] for step in steps}
    for node, mapped in mapping.items():
        for ident in mapped:
            reverse[ident].append(node)
    metadata = [{'id': s['id'], 'kind': s['kind'], 'source_nodes': reverse[s['id']]} for s in steps]
    profile = asdict(OBSERVED)
    manifest = {'schema': 'ug11-compiler/1', 'checkpoints': [s['id'] for s in steps],
                'steps': metadata, 'operation_map': mapping, 'output_id': ir['output_id'],
                'driver_map': ir['driver_map'], 'design_guidance': ir['design_guidance'],
                'driver_edits': {}, 'execution_approved': False, 'verify_edits': False,
                'status': 'generated_only; native verification is required', 'profile': profile}
    runtime_dir = Path(__file__).with_name('ug11')
    files = {'journal.cs': journal, 'journal.template.cs': template,
             'bundle_runtime.py': (runtime_dir / 'bundle_runtime.py').read_text(encoding='utf8'),
             'Run-Bundle.ps1': (runtime_dir / 'Run-Bundle.ps1').read_text(encoding='utf8'),
             'README.md': README}
    target = Path(output).absolute()
    if target.exists() or target.is_symlink():
        raise FileExistsError('output already exists')
    if not target.parent.is_dir():
        raise ValueError('output parent must exist')
    stage = Path(tempfile.mkdtemp(prefix='.ug11-export-', dir=target.parent))
    try:
        for name, content in files.items():
            (stage / name).write_bytes(content.replace('\n', '\r\n').encode('utf8')) if name == 'journal.cs' else (stage / name).write_text(content, encoding='utf8', newline='\n')
        for name, content in [('manifest.json', manifest), ('profile.json', profile),
                              ('parameters.json', {}), ('parameter-schema.json', {'schema': 'ug11-bundle-parameters/1', 'drivers': drivers}),
                              ('logic-ir.json', ir)]:
            _write_json(stage / name, content)
        if os.name == 'nt':
            os.rename(stage, target)
        else:
            target.mkdir()
            published = []
            try:
                for item in sorted(stage.iterdir(), key=lambda p: p.name == 'manifest.json'):
                    os.link(item, target / item.name)
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
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        target = export(_load(args.plan), args.root, args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, 'bundle export failed: %s\n' % exc)
    print('Generated only; NX has not run:', target)


if __name__ == '__main__':
    main()


