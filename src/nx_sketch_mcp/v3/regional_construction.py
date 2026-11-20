"""Evaluate evidence-bound P3 candidate constructions; no native execution.

Stock/slot are a conditional mathematical CSG proposal. Head carriers are
parameterized surfaces, not asserted trimmed solids. No P3 acceptance or
backend capability is inferred from evaluating these expressions.
"""
import ast
import json
import math
import operator
from fractions import Fraction
from pathlib import Path

STOCK = Path('workspace/v3/p3/P3-STOCK-DRIVERS-04/stock-drivers.json')
PROFILE = Path('workspace/v3/p3/P3-STOCK-01/meridian-plan-c2.json')
HEAD = Path('workspace/v3/p3/P3-HEAD-02/confirmed-head-drivers.json')
SLOT = Path('workspace/v3/p3/P3-REAR-SLOT-01/region-construction.json')
INTERFACE = Path('workspace/v3/p3/P3-INTEGRATION-03/shared-axial-interface-c1.json')


def _read(root, path):
    return json.loads((Path(root) / path).read_text(encoding='utf-8'))


def _expression(expression, values, *, sqrt=math.sqrt, tan=math.tan, power=operator.pow):
    """Evaluate the limited arithmetic grammar used by the stock chart."""
    def evaluate(node):
        if isinstance(node, ast.Expression): return evaluate(node.body)
        if isinstance(node, ast.Name): return values[node.id]
        if isinstance(node, ast.Constant) and type(node.value) in (int, float): return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp):
            a, b = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Add): return a+b
            if isinstance(node.op, ast.Sub): return a-b
            if isinstance(node.op, ast.Mult): return a*b
            if isinstance(node.op, ast.Div): return a/b
            if isinstance(node.op, ast.Pow): return power(a,b)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and len(node.args) == 1 and not node.keywords:
            arg = evaluate(node.args[0])
            if node.func.id == 'tan': return tan(arg)
            if node.func.id == 'sqrt': return sqrt(arg)
        raise ValueError('unsupported construction expression')
    return evaluate(ast.parse(expression.replace('^', '**'), mode='eval'))


def build_candidate(root, overrides=None):
    """Build concrete default/edit candidate, retaining all geometry gates."""
    stock, profile, head, slot, interface = (_read(root, p) for p in (STOCK, PROFILE, HEAD, SLOT, INTERFACE))
    if (stock['schema'] != 'p3-stock-engineering-drivers/1.0'
            or head['schema'] != 'p3-head02-confirmed-drivers/1'
            or head['shared_interface']['mouth_station'] != 'stock.Y_mouth'
            or interface['parameters'][0]['id'] != 'stock.Y_mouth'
            or stock['same_parameter_aliases']['head.Y_mouth'] != 'stock.Y_mouth'):
        raise ValueError('head/stock shared interface mismatch')
    overrides = {} if overrides is None else dict(overrides)
    values = {}
    stock_inputs = {n['id'] for n in stock['nodes'] if n['class'] in {'independent_local', 'external_independent_reference'}}
    head_inputs = {'head.'+name for name in head['global_independent']}
    sector_defaults = {}
    for index, sector in enumerate(head['sectors']):
        prefix = 'head.sector.%d.' % index
        sector_defaults.update({prefix+'theta': sector['theta_initial_display_rad'],
                                prefix+'RA': sector['RA_initial_source_binary64'],
                                prefix+'ra': sector['ra_initial_source_binary64']})
        for side, branch in enumerate(sector['branches']):
            lo, hi = (Fraction(x) for x in branch['d_initial_exact_enclosure'])
            sector_defaults[prefix+'branch.%d.rb' % side] = branch['rb_initial_source_binary64']
            sector_defaults[prefix+'branch.%d.d' % side] = float((lo+hi)/2)
    head_inputs |= set(sector_defaults)
    slot_inputs = {'slot.'+name for name in slot['confirmed_design']['four_independent_parameters_mm']}
    allowed = stock_inputs | head_inputs | slot_inputs
    if set(overrides) - allowed: raise ValueError('override is not an independent input')
    for node in stock['nodes']:
        ident = node['id']
        if node['class'] == 'derived':
            deps = {d[6:] if d.startswith('stock.') else d: values[d] for d in node['dependencies']}
            values[ident] = _expression(node['expression'], deps)
        else:
            initial = float(Fraction(*node['value_exact'])) if 'value_exact' in node else node['default']
            values[ident] = overrides.get(ident, initial)
        if type(values[ident]) not in (int, float) or not math.isfinite(values[ident]):
            raise ValueError('invalid stock parameter')
    for name, default in head['global_independent'].items():
        if name == 'cone_half_angle_initial_exact':
            ident, default = 'head.cone_half_angle_initial_exact', math.pi / 4
        else: ident = 'head.'+name
        values[ident] = overrides.get(ident, default)
    for name, default in sector_defaults.items(): values[name] = overrides.get(name, default)
    for name, default in slot['confirmed_design']['four_independent_parameters_mm'].items():
        values['slot.'+name] = overrides.get('slot.'+name, default)
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values.values()):
        raise ValueError('non-finite construction parameter')
    for node in stock['nodes']:
        if node['class'] in {'independent_local', 'external_independent_reference'}:
            if values[node['id']] <= 0: raise ValueError('stock driver must be positive')
            if node['unit'] == 'rad' and values[node['id']] >= math.pi/2:
                raise ValueError('stock cone angle outside local domain')
    if values['slot.width'] <= 0 or values['slot.radius'] <= 0:
        raise ValueError('slot width and radius must be positive')
    vertices = []
    for i in range(20):
        yid = 'stock.Y_mouth' if i == 19 else 'stock.Y%d' % i
        vertices.append({'id': 'v%d' % i, 'y_mm': values[yid], 'radius_mm': values['stock.R%d' % i],
                         'y_parameter': yid, 'radius_parameter': 'stock.R%d' % i})
    vertices.extend([{'id': 'v20', 'y_mm': values['stock.Y_mouth'], 'radius_mm': 0},
                     {'id': 'v21', 'y_mm': values['stock.Y0'], 'radius_mm': 0}])
    sequence = [0,1,2,3,4,5,6,7,8,9,10,12,13,15,16,17,18,19]
    if any(vertices[a]['y_mm'] >= vertices[b]['y_mm'] for a, b in zip(sequence, sequence[1:])):
        raise ValueError('stock station order invalid')
    if any(v['radius_mm'] <= 0 for v in vertices[:20]): raise ValueError('stock radius must be positive')
    arc_data = {'s5': ('stock.Y4', 'stock.M5', 'stock.tube_R5'),
                's8': ('stock.Y7', 'stock.M8', 'stock.tube_R8'),
                's10': ('stock.Y9', 'stock.M10', 'stock.tube_R10'),
                's19': ('stock.Ycenter19', 'stock.M19', 'stock.tube_R19')}
    by_id = {v['id']: v for v in vertices}
    curves = []
    for segment in profile['segments']:
        start, end = by_id[segment['start']], by_id[segment['end']]
        curve = {'id': segment['id'], 'kind': segment['kind'], 'start': start['id'], 'end': end['id']}
        if segment['kind'] == 'circular_arc':
            yi, ri, tube = arc_data[segment['id']]
            center = [values[yi], values[ri]]; radius = values[tube]
            def angle(point): return math.atan2(point['radius_mm']-center[1], point['y_mm']-center[0])
            for point in (start, end):
                if abs(math.hypot(point['y_mm']-center[0], point['radius_mm']-center[1])-radius) > 1e-7:
                    raise ValueError('candidate arc endpoint mismatch')
            a, b = angle(start), angle(end)
            sweep = (b-a) % (2*math.pi) if segment['arc']['sweep_rad'] > 0 else -((a-b) % (2*math.pi))
            curve.update({'center_y_r_mm': center, 'radius_mm': radius, 'start_rad': a, 'sweep_rad': sweep})
        curves.append(curve)
    h = {key[5:]: value for key, value in values.items() if key.startswith('head.')}
    half = h['cone_half_angle_initial_exact']
    if not 0 < half < math.pi/2: raise ValueError('head cone angle outside local domain')
    if h['R31'] <= 0 or h['R32'] <= 0 or h['R40'] <= 0: raise ValueError('head sphere radius must be positive')
    lower_y = h['Y_lower_step']+h['r_lower_fillet']
    upper_y = h['Y_head_step']-h['r_upper_fillet']
    def fillet(radius, center_y):
        if not 0 < radius < h['R40']: raise ValueError('head fillet radius outside local domain')
        return math.sqrt((h['R40']-radius)**2-(center_y-h['Y40'])**2)
    lower_major = fillet(h['r_lower_fillet'], lower_y)
    upper_major = fillet(h['r_upper_fillet'], upper_y)
    mouth_radius = math.tan(half)*(values['stock.Y_mouth']-h['cone_apex_Y'])
    if mouth_radius <= 0: raise ValueError('mouth outside positive cone nappe')
    sectors = []
    for index, sector in enumerate(head['sectors']):
        prefix = 'head.sector.%d.' % index
        theta = values[prefix+'theta']; axis = [math.cos(theta), 0, math.sin(theta)]
        major, minor = values[prefix+'RA'], values[prefix+'ra']
        if major <= 0 or minor <= 0: raise ValueError('head sector radii must be positive')
        branches = []
        for side, branch in enumerate(sector['branches']):
            rb = values[prefix+'branch.%d.rb' % side]
            distance = values[prefix+'branch.%d.d' % side]
            hdiff = rb-minor
            if hdiff <= abs(distance): raise ValueError('head canonical tangency invalid')
            radial = math.sqrt(hdiff*hdiff-distance*distance)
            if major <= radial: raise ValueError('head major radius must remain positive')
            branches.append({'face': branch['face'], 'axis': axis, 'minor_radius_mm': rb,
                             'major_radius_mm': major-radial,
                             'center_mm': [distance*axis[0], h['Y40'], distance*axis[2]],
                             'contact_s_mm': -minor*distance/hdiff,
                             'contact_rho_mm': major+minor*radial/hdiff,
                             'source_distance_enclosure_at_default': branch['d_initial_exact_enclosure'],
                             'side': branch['side']})
        if not branches[0]['contact_s_mm'] > 0 > branches[1]['contact_s_mm']:
            raise ValueError('head branch seam order event fails')
        sectors.append({'A_face': sector['A_face'], 'axis': axis, 'center_mm': [0,h['Y40'],0],
                        'major_radius_mm': major, 'minor_radius_mm': minor, 'branches': branches})
    slot_values = {key: values['slot.'+key] for key in ('width','radius','axis_y','axis_z')}
    graph = [{'id': n['id'], 'classification': n['class'], 'value': values[n['id']],
              'depends_on': n.get('dependencies', []), 'expression': n.get('expression')}
             for n in stock['nodes']]
    graph.extend({'id': name, 'classification': 'independent', 'value': values[name], 'depends_on': []}
                 for name in sorted(head_inputs | slot_inputs))
    graph.extend([
        {'id': 'head.mouth_radius', 'classification': 'derived', 'value': mouth_radius,
         'depends_on': ['stock.Y_mouth', 'head.cone_apex_Y', 'head.cone_half_angle_initial_exact'],
         'expression': 'tan(cone_half_angle)*(stock.Y_mouth-cone_apex_Y)'},
        {'id': 'head.lower_fillet_major', 'classification': 'derived', 'value': lower_major,
         'depends_on': ['head.R40', 'head.r_lower_fillet', 'head.Y_lower_step', 'head.Y40'],
         'expression': 'sqrt((R40-r_lower_fillet)^2-(Y_lower_step+r_lower_fillet-Y40)^2)'},
        {'id': 'head.upper_fillet_major', 'classification': 'derived', 'value': upper_major,
         'depends_on': ['head.R40', 'head.r_upper_fillet', 'head.Y_head_step', 'head.Y40'],
         'expression': 'sqrt((R40-r_upper_fillet)^2-(Y_head_step-r_upper_fillet-Y40)^2)'},
    ])
    for label, center_y, radius in (('lower', lower_y, h['r_lower_fillet']),
                                    ('upper', upper_y, h['r_upper_fillet'])):
        step = 'Y_lower_step' if label == 'lower' else 'Y_head_step'
        sign = '+' if label == 'lower' else '-'
        graph.append({'id': 'head.'+label+'_fillet_y', 'classification': 'derived', 'value': center_y,
                      'depends_on': ['head.'+step, 'head.r_'+label+'_fillet'],
                      'expression': step+sign+'r_'+label+'_fillet'})
        graph.append({'id': 'head.'+label+'_sphere_contact_y', 'classification': 'derived',
                      'value': h['Y40']+h['R40']*(center_y-h['Y40'])/(h['R40']-radius),
                      'depends_on': ['head.Y40', 'head.R40', 'head.'+label+'_fillet_y',
                                     'head.r_'+label+'_fillet'],
                      'expression': 'Y40+R40*(fillet_y-Y40)/(R40-fillet_radius)'})
    for index, sector in enumerate(sectors):
        prefix = 'head.sector.%d.' % index
        for coord, value in (('x', sector['axis'][0]), ('z', sector['axis'][2])):
            graph.append({'id': prefix+'axis_'+coord, 'classification': 'derived', 'value': value,
                          'depends_on': [prefix+'theta'], 'expression': ('cos' if coord == 'x' else 'sin')+'(theta)'})
        for side, branch in enumerate(sector['branches']):
            bp = prefix+'branch.%d.' % side
            common = [prefix+'RA', prefix+'ra', bp+'rb', bp+'d']
            graph.extend([
                {'id': bp+'major_radius', 'classification': 'derived', 'value': branch['major_radius_mm'],
                 'depends_on': common, 'expression': 'RA-sqrt((rb-ra)^2-d^2)'},
                {'id': bp+'contact_s', 'classification': 'derived', 'value': branch['contact_s_mm'],
                 'depends_on': [prefix+'ra', bp+'rb', bp+'d'], 'expression': '-ra*d/(rb-ra)'},
                {'id': bp+'contact_rho', 'classification': 'derived', 'value': branch['contact_rho_mm'],
                 'depends_on': common, 'expression': 'RA+ra*sqrt((rb-ra)^2-d^2)/(rb-ra)'},
            ])
    return {'schema': 'p3-regional-construction-candidate/0.1', 'unit': 'mm', 'frame': 'absolute_part_coordinates',
            'sources': [p.as_posix() for p in (STOCK, PROFILE, HEAD, SLOT, INTERFACE)],
            'parameters': values, 'parameter_graph': graph, 'stock_profile': {'vertices': vertices, 'curves': curves},
            'candidate_csg': [
                {'id': 'stock_revolve', 'operation': 'revolve_closed_meridian', 'axis': [0,1,0], 'sweep_rad': 2*math.pi,
                 'profile': 'stock_profile', 'depends_on': []},
                {'id': 'rear_slot_tool', 'operation': 'bounded_cylinder', 'axis': [1,0,0],
                 'axis_point_mm': [0,slot_values['axis_y'],slot_values['axis_z']],
                 'radius_mm': slot_values['radius'], 'x_limits_mm': [-slot_values['width']/2,slot_values['width']/2],
                 'parameter_dependencies': ['slot.width', 'slot.radius', 'slot.axis_y', 'slot.axis_z'],
                 'depends_on': []},
                {'id': 'stock_with_rear_slot', 'operation': 'subtract', 'target': 'stock_revolve', 'tool': 'rear_slot_tool',
                 'depends_on': ['stock_revolve','rear_slot_tool'], 'status': 'conditional_candidate'}],
            'head_carriers': {'mouth_y_mm': values['stock.Y_mouth'], 'mouth_radius_mm': mouth_radius,
                              'step_y_mm': h['Y_head_step'], 'sphere_center_mm': [0,0,0],
                              'sphere_radius_mm': h['R32'], 'cone_apex_y_mm': h['cone_apex_Y'],
                              'cone_half_angle_rad': half,
                              'lower_fillet': {'center_y_mm': lower_y, 'major_radius_mm': lower_major, 'minor_radius_mm': h['r_lower_fillet']},
                              'upper_fillet': {'center_y_mm': upper_y, 'major_radius_mm': upper_major, 'minor_radius_mm': h['r_upper_fillet']},
                              'sectors': sectors},
            'limitations': ['numeric preview only; all edit-domain and topology conditions are not yet established',
                            'stock source envelope, material occupancy and slot source trim remain open',
                            'head carriers are not complete finite solids or a closed CSG',
                            'no combined source-to-candidate budget or independent regional acceptance is claimed'],
            'execution_approved': False}
