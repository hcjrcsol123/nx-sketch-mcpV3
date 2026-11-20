"""Lower the P3 stock driver graph to NX2506 expression and revolve steps.

This is a default-plan lowering, not evidence of NX associativity or geometric
acceptance. Lengths are mm; expression angles are radians. The caller must create
steps in order and validate the complete native result before treating it as a
parametric model.
"""
import math
import re
from fractions import Fraction

from .regional_construction import _expression

_SHAFT = 'shaft_outer_diameter_mm'
_ARCS = {
    's5': ('stock.Y4', 'stock.M5', 'stock.tube_R5'),
    's8': ('stock.Y7', 'stock.M8', 'stock.tube_R8'),
    's10': ('stock.Y9', 'stock.M10', 'stock.tube_R10'),
    's19': ('stock.Ycenter19', 'stock.M19', 'stock.tube_R19'),
}


def _name(ident):
    if ident == _SHAFT:
        return 'v3_c5_shaft_outer_diameter_mm'
    if not re.fullmatch(r'stock\.[A-Za-z][A-Za-z0-9_]*', ident):
        raise ValueError('unsupported stock parameter identifier: ' + ident)
    return 'v3_' + ident.replace('.', '_')


def _close(actual, expected, label):
    if not (math.isfinite(actual) and math.isfinite(expected)
            and math.isclose(actual, expected, rel_tol=1e-13, abs_tol=1e-10)):
        raise ValueError('stock default mismatch: ' + label)


def _lower_formula(node, known):
    deps = node['dependencies']
    aliases = {d[6:] if d.startswith('stock.') else d: d for d in deps}
    if len(aliases) != len(deps) or any(d not in known for d in deps):
        raise ValueError('stock expression dependencies are not unique and ordered')
    tokens = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', node['expression']))
    if tokens - set(aliases) - {'tan', 'sqrt'} or not set(aliases) <= tokens:
        raise ValueError('stock formula references do not match dependencies: ' + node['id'])
    return re.sub(r'[A-Za-z_][A-Za-z0-9_]*',
                  lambda m: _name(aliases[m.group()]) if m.group() in aliases else m.group(),
                  node['expression'])


def build_stock_steps(plan, *, declare_shared_shaft=True):
    """Return ordered expression steps followed by one stock revolve step.

    Setting ``declare_shared_shaft=False`` requires the caller to have already
    created ``v3_c5_shaft_outer_diameter_mm`` at the matching value and unit.
    Each point expression is a 3-D ABS [X,Y,Z] list; numeric edge points remain
    in the stock frame's local [Y,r] coordinates for existing preview consumers.
    The canonical graph and profile must agree with the recorded defaults.
    """
    if not isinstance(declare_shared_shaft, bool):
        raise ValueError('declare_shared_shaft must be boolean')
    if plan.get('schema') != 'p3-final-mathematical-plan/1':
        raise ValueError('expected P3 final mathematical plan')
    stock = plan['parameters']['canonical_definitions']['stock']
    if stock.get('schema') != 'p3-stock-engineering-drivers/1.0':
        raise ValueError('unsupported canonical stock graph')
    nodes = stock['nodes']
    regional = {p['id']: p for p in plan['parameters']['regional']}
    if len(regional) != len(plan['parameters']['regional']):
        raise ValueError('duplicate regional parameter')
    steps, values, trace = [], {}, {}
    names = set()
    for node in nodes:
        ident = node['id']
        name = _name(ident)
        if ident in values or name in names:
            raise ValueError('duplicate stock parameter or native expression name')
        names.add(name)
        if node['unit'] not in ('mm', 'rad'):
            raise ValueError('unsupported stock expression unit')
        if node['class'] == 'derived':
            local = {d[6:] if d.startswith('stock.') else d: values[d]
                     for d in node['dependencies']}
            val = float(_expression(node['expression'], local))
            formula = _lower_formula(node, values)
        elif node['class'] in ('fixed_reference', 'independent_local', 'external_independent_reference'):
            val = float(Fraction(*node['value_exact'])) if 'value_exact' in node else float(node['default'])
            formula = repr(val)
        else:
            raise ValueError('unsupported stock parameter class')
        if not math.isfinite(val) or regional[ident]['unit'] != node['unit']:
            raise ValueError('invalid stock value or unit: ' + ident)
        _close(val, float(regional[ident]['value']), ident)
        values[ident] = val
        trace[ident] = {'name': name, 'value': val, 'unit': node['unit'],
                        'dependencies': list(node.get('dependencies') or []), 'formula': formula}
        if ident != _SHAFT or declare_shared_shaft:
            steps.append({'id': 'stock.expression.' + ident, 'kind': 'expression',
                          'name': name, 'formula': formula, 'unit': node['unit']})

    if trace['stock.R6']['dependencies'] != ['stock.Rshaft'] or trace['stock.R7']['dependencies'] != ['stock.Rshaft'] or trace['stock.Rshaft']['dependencies'] != [_SHAFT]:
        raise ValueError('stock shaft must use the shared diameter')
    if 'stock.Y_mouth' not in trace or 'stock.Y19' in trace:
        raise ValueError('stock and head must use the unique mouth station')

    # P3 B encloses the supporting stock circles as well as every vertex.
    # Keep this derived from the live stock graph rather than adding a margin.
    radial_candidates = [(_name('stock.R%d' % i), values['stock.R%d' % i]) for i in range(20)]
    radial_dependencies = ['stock.R%d' % i for i in range(20)]
    for segment, (_, center_id, radius_id) in _ARCS.items():
        center, radius = _name(center_id), _name(radius_id)
        candidate = 'v3_stock_B_%s_circle' % segment
        formula = 'sqrt(%s*%s)+%s' % (center, center, radius)
        steps.append({'id': 'stock.expression.' + candidate, 'kind': 'expression',
                      'name': candidate, 'formula': formula, 'unit': 'mm'})
        radial_candidates.append((candidate, abs(values[center_id]) + values[radius_id]))
        radial_dependencies.extend([center_id, radius_id])
    maximum_name, maximum = radial_candidates[0]
    for index, (candidate, candidate_value) in enumerate(radial_candidates[1:], 1):
        reduced = 'v3_stock_B_max_%02d' % index
        formula = '(%s+%s+sqrt((%s-%s)*(%s-%s)))/2' % (
            maximum_name, candidate, maximum_name, candidate, maximum_name, candidate)
        steps.append({'id': 'stock.expression.' + reduced, 'kind': 'expression',
                      'name': reduced, 'formula': formula, 'unit': 'mm'})
        maximum_name, maximum = reduced, max(maximum, candidate_value)
    radial_name = 'v3_stock_B_radial'
    steps.append({'id': 'stock.expression.' + radial_name, 'kind': 'expression',
                  'name': radial_name, 'formula': maximum_name, 'unit': 'mm'})
    preview = plan['construction']['implementation_route']['solid_enclosure']['default_binary64_outward_preview']['radial_upper_mm']
    _close(maximum, float(preview), 'B.radial')
    trace['stock.B_radial'] = {'name': radial_name, 'value': maximum, 'unit': 'mm',
                               'dependencies': radial_dependencies, 'formula': maximum_name}
    zero = 'v3_stock_zero'
    steps.append({'id': 'stock.expression.zero', 'kind': 'expression', 'name': zero, 'formula': '0', 'unit': 'mm'})
    profile = plan['construction']['profiles']['stock_profile']
    vertices = {v['id']: v for v in profile['vertices']}
    if set(vertices) != {'v%d' % i for i in range(22)} or len(profile['curves']) != 22:
        raise ValueError('expected the complete 22-vertex stock profile')
    points = {}
    for i in range(22):
        yid = 'stock.Y_mouth' if i in (19, 20) else 'stock.Y0' if i == 21 else 'stock.Y%d' % i
        rid = 'stock.R%d' % i if i < 20 else None
        point = vertices['v%d' % i]
        _close(float(point['y_mm']), values[yid], 'v%d.y' % i)
        _close(float(point['radius_mm']), values[rid] if rid else 0.0, 'v%d.r' % i)
        points['v%d' % i] = [_name(rid) if rid else zero, _name(yid), zero]
    expected_pairs = [('s%d' % (i + 1), 'v%d' % i, 'v%d' % (i + 1)) for i in range(20)]
    expected_pairs += [('axis_closure', 'v20', 'v21'), ('bottom_closure', 'v21', 'v0')]
    if [(c['id'], c['start'], c['end']) for c in profile['curves']] != expected_pairs:
        raise ValueError('stock profile sequence differs from the canonical closed meridian')
    edges, seen = [], set()
    for curve in profile['curves']:
        ident, a, b = curve['id'], curve['start'], curve['end']
        if ident in seen or a not in vertices or b not in vertices:
            raise ValueError('duplicate or invalid stock segment')
        seen.add(ident)
        pa, pb = vertices[a], vertices[b]
        start, end = [pa['y_mm'], pa['radius_mm']], [pb['y_mm'], pb['radius_mm']]
        if curve['kind'] == 'line':
            edge = {'kind': 'line', 'start': start, 'end': end,
                    'point_expressions': [points[a], points[b]]}
        elif curve['kind'] == 'circular_arc' and ident in _ARCS:
            yi, ri, tube = _ARCS[ident]
            cy, cr, radius = values[yi], values[ri], values[tube]
            _close(float(curve['center_y_r_mm'][0]), cy, ident + '.center_y')
            _close(float(curve['center_y_r_mm'][1]), cr, ident + '.center_r')
            _close(float(curve['radius_mm']), radius, ident + '.radius')
            sweep = float(curve['sweep_rad'])
            if not 0 < abs(sweep) < math.pi:
                raise ValueError('stock arc midpoint formula requires a minor arc')
            for p in (pa, pb):
                _close(math.hypot(p['y_mm'] - cy, p['radius_mm'] - cr), radius, ident + '.endpoint')
            dr = (pa['radius_mm'] - cr) + (pb['radius_mm'] - cr)
            dy = (pa['y_mm'] - cy) + (pb['y_mm'] - cy)
            denom = math.hypot(dr, dy)
            if denom <= 0:
                raise ValueError('stock arc midpoint is degenerate')
            mid = [cy + radius*dy/denom, cr + radius*dr/denom]
            theta = float(curve['start_rad']) + sweep / 2
            _close(mid[0], cy + radius*math.cos(theta), ident + '.mid_y')
            _close(mid[1], cr + radius*math.sin(theta), ident + '.mid_r')
            ncy, ncr, nr = _name(yi), _name(ri), _name(tube)
            ry = '(%s+%s-2*%s)' % (points[a][1], points[b][1], ncy)
            rr = '(%s+%s-2*%s)' % (points[a][0], points[b][0], ncr)
            dn, my, mr = ('v3_stock_%s_%s' % (ident, suffix) for suffix in ('mid_den', 'mid_y', 'mid_r'))
            for name, formula in ((dn, 'sqrt(%s^2+%s^2)' % (ry, rr)),
                                  (my, '%s+%s*%s/%s' % (ncy, nr, ry, dn)),
                                  (mr, '%s+%s*%s/%s' % (ncr, nr, rr, dn))):
                steps.append({'id': 'stock.expression.' + name, 'kind': 'expression',
                              'name': name, 'formula': formula, 'unit': 'mm'})
            edge = {'kind': 'arc', 'start': start, 'mid': mid, 'end': end,
                    'point_expressions': [points[a], [mr, my, zero], points[b]]}
        else:
            raise ValueError('unsupported stock segment: ' + ident)
        edges.append(edge)
    if seen != ({'s%d' % i for i in range(1, 21)} | {'axis_closure', 'bottom_closure'}):
        raise ValueError('stock segment inventory differs from P3')
    steps.append({'id': 'stock_revolve', 'kind': 'revolve',
                  'frame': {'origin': [0, 0, 0], 'x_axis': [0, 1, 0], 'y_axis': [1, 0, 0]},
                  'edges': edges, 'axis_point': [0, 0, 0], 'axis_direction': [0, 1, 0],
                  'start_degrees': 0, 'end_degrees': 360})
    return {'steps': steps, 'trace': trace,
            'limitations': ['Default values and minor arc branches only; edited geometry requires domain validation.',
                            'Native expression evaluation, associativity, geometric equivalence and feature persistence require NX verification.']}
