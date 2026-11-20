"""Bounded recognition/lowering of the reviewed parametric construction family.

Native observations describe a candidate family only. Carrier, graph, units,
and body checks do not prove trimmed-boundary equality or authorize execution.
"""
import ast
from copy import deepcopy
import json
import math
from pathlib import Path
from .project_root import project_root

from .regions.common import normalize_snapshot
from .regions.reference_slot import recognize as recognize_slot
from .ug11.compiler import lower_plan


class FamilyError(ValueError):
    pass


def _need(ok, message):
    if not ok:
        raise FamilyError(message)


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _near(a, b, tolerance=1e-7):
    return _finite(a) and _finite(b) and abs(a-b) <= tolerance * max(1, abs(a), abs(b))


def _unit(symbol):
    if symbol == 'mm': return 'mm'
    if symbol in ('radians', 'rad'): return 'rad'
    if symbol in ('degrees', 'deg'): return 'degree'
    if symbol in (None, '', '1'): return '1'
    raise FamilyError('unsupported native expression unit: ' + repr(symbol))


def _eval_formulas(expressions):
    """Evaluate the NX arithmetic subset in canonical mm/rad expression units."""
    visiting, done = set(), {}
    funcs = {'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
             'asin': math.asin, 'acos': math.acos, 'atan': math.atan, 'abs': abs}
    def evaluate(name):
        if name in done: return done[name]
        _need(name not in visiting and name in expressions, 'expression cycle or unknown dependency: ' + name)
        visiting.add(name)
        try:
            tree = ast.parse(expressions[name]['rhs'].replace('^', '**'), mode='eval')
            def node(n):
                if isinstance(n, ast.Expression): return node(n.body)
                if isinstance(n, ast.Constant) and _finite(n.value): return n.value
                if isinstance(n, ast.Name):
                    if n.id == 'pi': return math.pi
                    if n.id == 'e': return math.e
                    return evaluate(n.id)
                if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
                    value = node(n.operand); return value if isinstance(n.op, ast.UAdd) else -value
                if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
                    a, b = node(n.left), node(n.right)
                    return {ast.Add: lambda: a+b, ast.Sub: lambda: a-b, ast.Mult: lambda: a*b,
                            ast.Div: lambda: a/b, ast.Pow: lambda: a**b}[type(n.op)]()
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in funcs and len(n.args) == 1 and not n.keywords:
                    return funcs[n.func.id](node(n.args[0]))
                raise FamilyError('unsupported expression syntax: ' + name)
            value = node(tree)
            _need(_finite(value) and _near(value, expressions[name]['value_in_expression_units']),
                  'evaluated expression differs from native value: ' + name)
            done[name] = value
            return value
        except (SyntaxError, ArithmeticError, ValueError, OverflowError, TypeError) as exc:
            if isinstance(exc, FamilyError): raise
            raise FamilyError('cannot evaluate expression: ' + name) from exc
        finally:
            visiting.remove(name)
    for name in expressions: evaluate(name)
    return done


def _same_feature_graph(reference, actual):
    """Compare semantic graph structure without retaining session-local JIDs.

    Named nodes are persistent family roles. Other feature keys are local graph
    vertices. Refine colors using both parent and child relations; only permit
    repeated colors when each class consists of interchangeable exact twins.
    """
    if not isinstance(reference, dict) or not isinstance(actual, dict) or len(reference) != len(actual):
        return False
    graphs = []
    for source in (reference, actual):
        children = {key: set() for key in source}
        for key, row in source.items():
            if (not isinstance(key, str) or not (key.startswith('node:') or key.startswith('jid:'))
                    or not isinstance(row, dict) or set(row) != {'type', 'parents', 'expressions'}
                    or not isinstance(row['type'], str) or not isinstance(row['parents'], list)
                    or not isinstance(row['expressions'], list)
                    or len(set(row['parents'])) != len(row['parents'])
                    or any(parent not in source for parent in row['parents'])):
                return False
            for parent in row['parents']: children[parent].add(key)
        graphs.append((source, children))
    def initial(key, row):
        return (key if key.startswith('node:') else '', row['type'], tuple(sorted(row['expressions'])))
    labels = [[initial(k, row) for k, row in graph[0].items()] for graph in graphs]
    palette = {v: i for i, v in enumerate(sorted(set(labels[0] + labels[1])))}
    colors = [{k: palette[initial(k, row)] for k, row in graph[0].items()} for graph in graphs]
    for _ in range(len(reference) + 1):
        descriptions = []
        for (source, children), color in zip(graphs, colors):
            descriptions.append({k: (color[k], tuple(sorted(color[x] for x in row['parents'])),
                                      tuple(sorted(color[x] for x in children[k]))) for k, row in source.items()})
        palette = {v: i for i, v in enumerate(sorted(set(descriptions[0].values()) | set(descriptions[1].values())))}
        new = [{k: palette[v] for k,v in d.items()} for d in descriptions]
        old_groups = [{frozenset(k for k,v in color.items() if v == c) for c in set(color.values())} for color in colors]
        new_groups = [{frozenset(k for k,v in color.items() if v == c) for c in set(color.values())} for color in new]
        colors = new
        if old_groups == new_groups: break
    else: return False
    from collections import Counter
    if Counter(colors[0].values()) != Counter(colors[1].values()): return False
    for (source, children), color in zip(graphs, colors):
        classes = {}
        for k,c in color.items(): classes.setdefault(c, []).append(k)
        for members in classes.values():
            if len(members) > 1:
                neighborhoods = {(frozenset(source[k]['parents']), frozenset(children[k])) for k in members}
                if len(neighborhoods) != 1: return False
    return True


def recognize_parametric_family(observation, *, root=None):
    """Infer and lower current family drivers from one guarded native capture.

    Returns all compiler-validated steps and inferred edits. This is a family
    construction candidate, not proof that those steps reproduce every trim.
    The caller is responsible for binding a clean capture to its NX source.
    """
    root = Path(root or project_root()).resolve()
    _need(root == project_root(), 'unexpected project evidence root')
    def read(path):
        return json.loads((root / path).read_text(encoding='utf-8-sig'))
    template = read('workspace/v3/p3/P3-FINAL-PLAN-01/final-plan.json')
    baseline = read('workspace/v3/p6/T28-NX-01/reopen.json')
    _need(baseline.get('status') == 'PASS' and baseline.get('phase') == 'reopen', 'family reference graph unavailable')
    _need(isinstance(observation, dict) and observation.get('schema') == 'p7-parametric-family-observation/1'
          and observation.get('status') == 'PASS' and observation.get('samples_equal') is True
          and observation.get('units') == 'mm' and observation.get('interpart') == {'parents': 0, 'children': 0}
          and observation.get('dirty_before') is False and observation.get('dirty_after') is False
          and observation.get('closed_without_save') is True, 'native observation not complete and clean across read')
    actual, reference = observation['readback'], baseline['readback']
    _need(_same_feature_graph(reference['features'], actual['features']), 'complete native feature-parent graph differs or is ambiguous')
    exp, ref = actual['expressions'], reference['expressions']
    _need(set(exp) == set(ref), 'native expression set differs')
    default = lower_plan(template, root)
    steps_by_name = {s['name']: s for s in default['steps'] if s['kind'] == 'expression'}
    drivers = default['driver_map']
    _need(len(drivers) == 104, 'reviewed driver map incomplete')
    native_drivers = {row['expression']: ident for ident, row in drivers.items()}
    _need(len(native_drivers) == len(drivers), 'driver map is ambiguous')
    for name, item in exp.items():
        _need(isinstance(item, dict) and item.get('interpart') is False
              and isinstance(item.get('rhs'), str) and _finite(item.get('value_in_expression_units')),
              'bad native expression: ' + name)
        _unit(item.get('unit_symbol'))
        if name in native_drivers:
            try: value = float(item['rhs'])
            except ValueError as exc: raise FamilyError('independent expression is not numeric: ' + name) from exc
            _need(_near(value, item['value_in_expression_units']), 'independent expression value differs: ' + name)
        else:
            _need(item['rhs'] == ref[name]['rhs'], 'dependent or fixed formula differs: ' + name)
        if name in steps_by_name:
            _need(_unit(item.get('unit_symbol')) == steps_by_name[name].get('unit', 'mm'),
                  'compiled expression unit differs: ' + name)
    values = _eval_formulas(exp)
    changes = {}
    for ident, row in drivers.items():
        name = row['expression']
        _need(_unit(exp[name].get('unit_symbol')) == row['unit'], 'driver unit differs: ' + ident)
        expected_default = float(steps_by_name[name]['formula'])
        if not _near(values[name], expected_default, 1e-12): changes[ident] = values[name]
    # The compiler checks every step, input graph, driver map, and ideal window.
    lowered = lower_plan(template, root, overrides=changes)
    body, refbody = actual['body'], reference['body']
    # P4 documents the alternative analytic/rotated-carrier representation
    # after a fully finite edited-body comparison. This admits only its coarse
    # type-count class; it does not transfer that geometry proof to this input.
    edited_case = read('workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/corrected-native-mixed-brep/result.json')
    edited_proof = read('workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/corrected-native-mixed-brep/complete-edited-boolean-evidence.json')
    _need(edited_case.get('status') == 'NATIVE_EDIT_POINT_PASS'
          and edited_proof.get('status') == 'within_limit'
          and edited_proof.get('face_count') == refbody['face_count']
          and edited_case.get('after', {}).get('body_consistency_fault_count') == 0,
          'reviewed edited representation evidence unavailable')
    representations = [refbody['face_types'], edited_case['after']['face_types']]
    _need(body.get('is_solid') is True and body.get('body_consistency_fault_count') == 0
          and _finite(body.get('volume_mm3')) and body['volume_mm3'] > 0
          and body.get('face_count') == refbody['face_count'] and body.get('edge_count') == refbody['edge_count']
          and body.get('face_types') in representations, 'solid consistency or unsupported coarse representation')
    snapshot = observation['inventory_snapshot']
    inv = normalize_snapshot(snapshot, tolerances={'linear': 0.001, 'angular': 0.0001})
    _need(inv['unit'] == 'mm' and len(inv['faces']) == body['face_count']
          and len(inv['edges']) == body['edge_count'], 'carrier inventory and body counts differ')
    slots = recognize_slot(inv)
    _need(len(slots) == 1, 'current cylindrical slot carrier is missing or ambiguous')
    geometry = slots[0]['measured_geometry']
    for key in ('width', 'radius'):
        _need(_near(geometry[key], values[drivers['slot.'+key]['expression']]), 'slot carrier value differs: ' + key)
    point, axis = geometry['midplane_axis_point'], geometry['axis_direction']
    _need(all(_near(a,b) for a,b in zip(axis, (1,0,0))) and
          all(_near(a,b) for a,b in zip(point, (0,values[drivers['slot.axis_y']['expression']],
                                                   values[drivers['slot.axis_z']['expression']]))),
          'slot carrier pose differs from family construction')
    _need(_near(actual['slot_limits_mm'][1] - actual['slot_limits_mm'][0], geometry['width']),
          'native slot limits and carrier width differ')
    lowered = deepcopy(lowered)
    lowered['source_snapshot_role'] = 'reviewed_template_not_current_source'
    lowered['current_observation_snapshot_id'] = inv['snapshot_id']
    return {'schema': 'p7-parametric-family-plan/1', 'status': 'recognized_candidate',
            'current_snapshot_id': inv['snapshot_id'], 'driver_values': {ident: values[row['expression']] for ident,row in drivers.items()},
            'inferred_edits': changes, 'lowered_plan': lowered, 'execution_approved': False,
            'geometry_witness': geometry, 'geometry_closure': 'not_established',
            'limitations': ['Current carrier and coarse solid checks do not establish all trims or full-body equivalence.',
                            'Observed graph and expression relationships identify a candidate family, not independently proven native consumers.',
                            'The compiler screen proves an ideal mathematical window, not native edit validity.']}
