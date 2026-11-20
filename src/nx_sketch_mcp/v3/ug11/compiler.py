"""Fail-closed lowering of the reviewed P3 construction for UG11.

No NX session is started here. A generated journal is a candidate for controlled
native testing, not evidence of geometric or edit-domain acceptance.
"""
from copy import deepcopy
import importlib.util
import json
import math
import re
from pathlib import Path

from ..project_root import project_root
from ..nx2506_composition import compile_associative_preview
from ..nx2506_edit_domain import assess_joint_ideal_edit
from . import sketch, extrude, revolve
from .profile import OBSERVED, require_profile


class UnsupportedCompilation(ValueError):
    """A plan, operation or source lacks a proven lowering."""


_PLAN = Path('workspace/v3/p3/P3-FINAL-PLAN-01/final-plan.json')
_WINDOW = Path('workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/joint-ideal-edit-window.json')
_DRIVERS = Path('workspace/v3/p4/P4-ACCEPTANCE-20261119/per-driver-edit-domain.json')
_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*$')


def _load(path):
    with path.open(encoding='utf-8-sig') as stream:
        return json.load(stream, parse_constant=lambda s: (_ for _ in ()).throw(ValueError('non-finite JSON number')))


def lower_plan(plan, root, overrides=None, identity=OBSERVED):
    """Validate the entire reviewed source graph, then lower its P4 route.

    The P4 lowerer specializes structure and geometry. Until alternatives have
    explicit mappings, changed construction/parameter records are rejected;
    dimensional edits are supplied separately as native driver overrides.
    """
    require_profile(identity)
    root = Path(root).resolve()
    if root != project_root():
        raise UnsupportedCompilation('root must be the installed project evidence root')
    reference = _load(root / _PLAN)
    builder_path = root / 'workspace/v3/p3/P3-FINAL-PLAN-01/build_plan.py'
    spec = importlib.util.spec_from_file_location('ug11_p3_rebuild', builder_path)
    if spec is None or spec.loader is None:
        raise UnsupportedCompilation('P3 independent assembler unavailable')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    if builder.build(root) != reference:
        raise UnsupportedCompilation('reviewed plan differs from independent P3 assembly')
    if not isinstance(plan, dict):
        raise UnsupportedCompilation('plan must be an object')
    # The existing P4 code uses specialized constants and regional mappings.
    # Check their complete inputs, not just node names or nominal counts.
    if set(plan) != set(reference):
        raise UnsupportedCompilation('plan field set differs from reviewed source')
    for key in reference:
        if key not in plan or plan[key] != reference.get(key):
            raise UnsupportedCompilation('unmapped or changed P3 field: ' + key)
    edits = {} if overrides is None else dict(overrides)
    drivers = _load(root / _DRIVERS)['drivers']
    if any(key not in drivers for key in edits):
        raise UnsupportedCompilation('unknown independent driver')
    proof = _load(root / _WINDOW)
    try:
        admission = assess_joint_ideal_edit(edits, proof)
    except (ValueError, TypeError, KeyError) as exc:
        raise UnsupportedCompilation('invalid edit candidate') from exc
    if not admission['mathematically_admissible']:
        raise UnsupportedCompilation('driver outside proven ideal window')
    mapped = compile_associative_preview(plan)
    steps = [deepcopy(step) for group in mapped['groups'] for step in group]
    ids, live, expressions = set(), set(), set()
    for step in steps:
        ident, kind = step.get('id'), step.get('kind')
        if not isinstance(ident, str) or not ident or ident in ids:
            raise UnsupportedCompilation('missing or duplicate step id')
        ids.add(ident)
        try:
            if kind == 'expression':
                if set(step) - {'id', 'kind', 'name', 'formula', 'unit'} or not {'name', 'formula'} <= step.keys():
                    raise UnsupportedCompilation('unsupported expression fields: ' + ident)
                name = step['name']
                if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name) or name in expressions:
                    raise UnsupportedCompilation('duplicate or invalid expression: ' + ident)
                if step.get('unit', 'mm') not in ('mm', 'rad', '1') or not isinstance(step['formula'], str):
                    raise UnsupportedCompilation('invalid expression definition: ' + ident)
                refs = set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*', step['formula'])) - {'sqrt', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'abs', 'pi', 'e'}
                if not refs <= expressions:
                    raise UnsupportedCompilation('expression references unavailable names: ' + ident + ' ' + str(sorted(refs - expressions)))
                expressions.add(name)
            elif kind in ('revolve', 'extrude'):
                sketch.validate_step(step)
                (revolve if kind == 'revolve' else extrude).validate_step(step)
                if ident == 'rear_slot_tool':
                    sketch.validate_rear_slot(step)
                    by_name = {s['name']: s['formula'] for s in steps[:steps.index(step)] if s['kind'] == 'expression'}
                    for name, formula in {'v3_slot_high_y':'v3_slot_axis_y+v3_slot_radius',
                                          'v3_slot_low_y':'v3_slot_axis_y-v3_slot_radius',
                                          'v3_slot_high_z':'v3_slot_axis_z+v3_slot_radius',
                                          'v3_slot_low_z':'v3_slot_axis_z-v3_slot_radius'}.items():
                        if by_name.get(name) != formula:
                            raise UnsupportedCompilation('rear slot formula mismatch: ' + name)
                for edge in step['edges']:
                    for row in edge.get('point_expressions', edge.get('pole_expressions', [])):
                        if not set(row) <= expressions:
                            raise UnsupportedCompilation('profile references unavailable expressions: ' + ident)
                for row in step.get('axis_points_expressions', []):
                    if not set(row) <= expressions:
                        raise UnsupportedCompilation('axis references unavailable expressions: ' + ident)
                for field in ('start_formula', 'end_formula'):
                    if field in step:
                        refs = set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*', step[field])) - {'sqrt', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'abs', 'pi', 'e'}
                        if not refs <= expressions:
                            raise UnsupportedCompilation('limit references unavailable expressions: ' + ident)
                live.add(ident)
            elif kind == 'boolean':
                extrude.validate_step(step)
                if step['target'] not in live or not set(step['tools']) <= live:
                    raise UnsupportedCompilation('boolean input unavailable: ' + ident)
                live.remove(step['target'])
                if not step['retain_tools']:
                    live.difference_update(step['tools'])
                live.add(ident)
            else:
                raise UnsupportedCompilation('unknown native step: ' + str(kind))
        except (ValueError, KeyError, TypeError) as exc:
            if isinstance(exc, UnsupportedCompilation):
                raise
            raise UnsupportedCompilation('unsupported step ' + ident + ': ' + str(exc)) from exc
    if mapped['output_id'] not in live or live != {mapped['output_id']}:
        raise UnsupportedCompilation('output does not resolve to one live result')
    names = {drivers[k]['native_expression'] for k in edits}
    if len(names) != len(edits) or not names <= expressions:
        raise UnsupportedCompilation('driver mapping missing, duplicated or not consumed')
    from .operation_map import operation_map
    node_map = operation_map(plan, steps)
    from .driver_map import driver_map
    try:
        driver_trace = driver_map(steps, drivers)
    except (ValueError, KeyError, TypeError) as exc:
        raise UnsupportedCompilation('driver consumer mapping failed: ' + str(exc)) from exc
    if len(driver_trace) != len(drivers) or any(not row['consumers'] for row in driver_trace.values()):
        raise UnsupportedCompilation('incomplete driver consumer mapping')
    return {'steps': steps, 'output_id': mapped['output_id'],
            'driver_edits': {drivers[k]['native_expression']: v for k, v in edits.items()},
            'edit_checks': [(drivers[k]['native_expression'], [float(v) for v in proof['driver_windows'][k]])
                            for k in ('slot.width', 'slot.axis_y', 'slot.axis_z', 'slot.radius', 'shaft_outer_diameter_mm', 'F0002.P2.t_mm')],
            'source_snapshot': plan['p1_snapshot_id'], 'ideal_screen': admission,
            'operation_map': node_map, 'design_guidance': mapped['design_guidance'],
            'driver_map': driver_trace,
            'execution_approved': False}


def _q(value):
    return json.dumps(value, ensure_ascii=True)


def _n(value):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise UnsupportedCompilation('non-finite C# number')
    out = repr(float(value))
    return out if any(c in out for c in '.eE') else out + '.0'


def _vec(value, cls):
    return 'new %s(%s)' % (cls, ','.join(_n(v) for v in value))


def _expr_rows(rows):
    return ','.join('E[' + _q(name) + ']' for name in rows)


def _profile_code(step):
    lines = ['var curves = new List<Curve>();']
    for index, edge in enumerate(step['edges']):
        if edge['kind'] == 'spline':
            rows = edge['pole_expressions']
            matrix = ','.join('{' + _expr_rows(row) + '}' for row in rows)
            knots = ','.join(_n(x) for x in edge['knots'])
            lines.extend(['double[] k%d=new double[]{%s};' % (index, knots),
                'var s%d=Ug11SketchBinding.CreateDrivenCubicSpline(P,new Expression[,] {%s},k%d);' % (index, matrix, index),
                's%d.Curve.SetUserAttribute("UG11_EDGE",0,%s,Update.Option.Now);' % (index,_q(step['id']+'/edge/'+str(index))),
                'curves.Add(s%d.Curve); splines.Add(s%d); splineKnots.Add(k%d);' % (index,index,index)])
        else:
            points = []
            for j, row in enumerate(edge['point_expressions']):
                ident = 'p%d_%d' % (index, j)
                lines.append('var %s=Ug11SketchBinding.CreateDrivenPoint(P,new Expression[]{%s});' % (ident, _expr_rows(row)))
                points.append(ident)
            method = 'CreateDrivenLine' if edge['kind'] == 'line' else 'CreateDrivenArc'
            lines.extend(['var c%d=Ug11SketchBinding.%s(P,%s);' % (index, method, ','.join(points)),
                          'c%d.Curve.SetUserAttribute("UG11_EDGE",0,%s,Update.Option.Now);' % (index,_q(step['id']+'/edge/'+str(index))),
                          'curves.Add(c%d.Curve); driven.Add(c%d);' % (index,index)])
    lines.append('Section section=Ug11SketchBinding.CreateSection(P,new Ug11SketchBinding.ProfileResult { Curves=curves.ToArray() },new Point3d(%s),0.0001,0.0001,0.01);' % ','.join(_n(x) for x in step['frame']['origin']))
    return lines


def _method(index, step):
    ident, kind = step['id'], step['kind']
    lines = ['static void S%d() {' % index, 'Begin(%s);' % _q(ident)]
    if kind == 'expression':
        # NX11's observed Unit.Name is singular; native expression.Value uses
        # base degrees while formula evaluation respects the Radian unit.
        unit = {'mm':'MilliMeter','rad':'Radian','1':None}[step.get('unit','mm')]
        unit_cs = 'null' if unit is None else 'P.UnitCollection.FindObject(%s)' % _q(unit)
        lines.append('E.Add(%s,P.Expressions.CreateWithUnits(%s,%s));' % (_q(step['name']), _q(step['name']+'='+step['formula']), unit_cs))
    elif kind in ('extrude', 'revolve'):
        lines.append('int firstDriven=driven.Count, firstSplines=splines.Count, firstSlots=slots.Count;')
        if ident == 'rear_slot_tool':
            dimensions = sketch.validate_rear_slot(step)
            for name, value in [('v3_slot_axis_y', dimensions['center_y']),
                                ('v3_slot_axis_z', dimensions['center_z']),
                                ('v3_slot_radius', dimensions['radius'])]:
                lines.append('Need(Math.Abs(E[%s].Value-(%s))<1e-8,"rear slot initial mismatch");' % (_q(name), _n(value)))
            lines.append('var slot=Ug11SketchBinding.CreateRearSlot(P,E["v3_slot_axis_y"],E["v3_slot_axis_z"],E["v3_slot_radius"]); slot.Sketch.Feature.SetUserAttribute("UG11_SLOT",0,"rear_slot",Update.Option.Now); slot.Circle.SetUserAttribute("UG11_EDGE",0,"rear_slot_tool/edge/circle",Update.Option.Now); slots.Add(slot); Section section=slot.Section;')
        else:
            lines.extend(_profile_code(step))
        if kind == 'extrude':
            lines.append('Feature f=UG11ExtrudeSolids.CreateExtrude(P,section,%s,%s,%s,%s,%s);' % (_vec(step['direction'],'Vector3d'), _n(step['start']),_n(step['end']), _q(step.get('start_formula')), _q(step.get('end_formula'))))
        else:
            axes = step.get('axis_points_expressions')
            if axes:
                for i,row in enumerate(axes):
                    lines.append('var axis%d=Ug11SketchBinding.CreateDrivenPoint(P,new Expression[]{%s});' % (i,_expr_rows(row)))
            lines.append('Feature f=Ug11Revolve.CreateRevolve(P,section,%s,%s,%s,%s,%s,%s,%s,%s);' % (_vec(step['axis_point'],'Point3d'),_vec(step['axis_direction'],'Vector3d'),_n(step['start_degrees']),_n(step['end_degrees']),_q(step.get('start_formula')),_q(step.get('end_formula')),'axis0.Point' if axes else 'null','axis1.Point' if axes else 'null'))
        lines.append('Register(%s,f); UpdateModel(); VerifyNewProfiles(firstDriven,firstSplines,firstSlots);' % _q(ident))
        if ident == 'rear_slot_tool':
            lines.append('Ug11SketchBinding.VerifyRearSlotConsumer(P,(Extrude)f,slot);')
    else:
        tools = ','.join('Live(%s)' % _q(x) for x in step['tools'])
        lines.append('Feature f=UG11ExtrudeSolids.Boolean(P,%s,Live(%s),new Body[]{%s},false,%s);' % (_q(step['operation']), _q(step['target']), tools, str(step['retain_tools']).lower()))
        lines.append('Register(%s,f); UpdateModel();' % _q(ident))
    lines.extend(['End(%s);' % _q(ident), '}'])
    return '\n'.join(lines)


def render_journal(lowered, verify_edits=False, *, _bundle_marker=None):
    """Render an unexecuted journal from a validated lowering."""
    if type(verify_edits) is not bool:
        raise ValueError('verify_edits must be boolean')
    steps = lowered['steps']
    methods = '\n'.join(_method(i, step) for i, step in enumerate(steps))
    shaft = next(item for item in lowered['edit_checks'] if item[0] == 'v3_c5_shaft_outer_diameter_mm')
    c5 = next(item for item in lowered['edit_checks'] if item[0] == 'v3_c5_F0002_P2_t_mm')
    calls = '\n'.join('S%d();%s%s' % (i, (' TestDriver(%s,%s,%s);' % (_q(shaft[0]),_n(shaft[1][0]),_n(shaft[1][1]))) if verify_edits and step['id'] == 'stock_revolve' else '', (' TestC5(%s,%s);' % (_n(c5[1][0]),_n(c5[1][1]))) if verify_edits and step['id'] == 'member_00_roll_tool' else '') for i,step in enumerate(steps))
    edits = '\n'.join('P.Expressions.EditWithUnits(E[%s],E[%s].Units,%s);' % (_q(k),_q(k),_q(_n(v))) for k,v in lowered['driver_edits'].items())
    if lowered['driver_edits']:
        edits += '\nUpdateModel();\n' + '\n'.join('Need(Math.Abs(E[%s].GetValueUsingUnits(Expression.UnitsOption.Expression)-(%s))<1e-8,"requested driver value mismatch");' % (_q(k),_n(v)) for k,v in lowered['driver_edits'].items())
    edits += '\n' + '\n'.join(
        'TestDriver(%s,%s,%s);' % (_q(name), _n(window[0]), _n(window[1]))
        for name,window in lowered['edit_checks'] if verify_edits and name not in (shaft[0],c5[0]))
    if _bundle_marker is not None:
        if not isinstance(_bundle_marker, str) or not _bundle_marker:
            raise ValueError('invalid bundle marker')
        edits = _bundle_marker
    main = Path(__file__).with_name('journal_template.cs').read_text(encoding='utf8')
    for marker, replacement in (('@METHODS@',methods),('@CALLS@',calls),('@EDITS@',edits)):
        if main.count(marker)!=1:
            raise RuntimeError('invalid journal template marker')
        main=main.replace(marker,replacement)
    sources=[]
    for module in (sketch,extrude,revolve):
        # A C# compilation unit requires all using directives before all classes.
        sources.append('\n'.join(line for line in module.source().splitlines() if not line.startswith('using ')))
    sources.append('\n'.join(line for line in Path(__file__).with_name('safe_close.cs').read_text(encoding='utf8').splitlines() if not line.startswith('using ')))
    return main+'\n'+'\n'.join(sources)+'\n'


def prepare(plan, root, output, overrides=None, identity=OBSERVED, verify_edits=False):
    """Create an unused output directory and write candidate journal and map."""
    lowered=lower_plan(plan,root,overrides,identity)
    mapping=lowered['operation_map']
    journal=render_journal(lowered,verify_edits)
    steps=lowered['steps']
    reverse={s['id']:[] for s in steps}
    for node, mapped in mapping.items():
        for step_id in mapped:
            reverse[step_id].append(node)
    shaft_name='v3_c5_shaft_outer_diameter_mm'
    checkpoints=[]
    for step in steps:
        checkpoints.append(step['id'])
        if verify_edits and step['id']=='stock_revolve': checkpoints.append('edit.'+shaft_name)
        if verify_edits and step['id']=='member_00_roll_tool': checkpoints.append('edit.v3_c5_F0002_P2_t_mm')
    checkpoints += ['edit.' + n for n,_ in lowered['edit_checks'] if verify_edits and n not in (shaft_name,'v3_c5_F0002_P2_t_mm')]
    metadata={s['id']:{'id':s['id'],'kind':s['kind'],'source_nodes':reverse[s['id']]} for s in steps}
    metadata.update({'edit.'+n:{'id':'edit.'+n,'kind':'edit_readback_restore','source_nodes':[], 'ideal_window':window}
                     for n,window in lowered['edit_checks']})
    manifest={'schema':'ug11-compiler/1','source_snapshot':lowered['source_snapshot'],
              'checkpoints':checkpoints,
              'steps':[metadata[ident] for ident in checkpoints],
              'operation_map':mapping,'output_id':lowered['output_id'],
              'driver_map':lowered['driver_map'], 'design_guidance':lowered['design_guidance'],
              'driver_edits':lowered['driver_edits'], 'execution_approved':False,
              'verify_edits':verify_edits,
              'status':'generated_only; native verification is required'}
    target=Path(output).absolute()
    target.mkdir(parents=False,exist_ok=False)
    (target/'journal.cs').write_text(journal,encoding='utf8')
    (target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    return target


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--overrides',type=Path)
    parser.add_argument('--verify-edits',action='store_true')
    args=parser.parse_args(argv)
    target=prepare(_load(args.plan),args.root,args.output,_load(args.overrides) if args.overrides else None,verify_edits=args.verify_edits)
    print('Generated only; NX has not run:',target)
    guidance = _load(target / 'manifest.json')['design_guidance']
    print('Advisory design guidance:', target / 'manifest.json', 'field design_guidance;',
          len(guidance['actions']), 'review candidates; confirm intent and validate before adoption.')


if __name__ == '__main__':
    main()

