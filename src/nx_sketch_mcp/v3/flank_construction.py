"""Build default P3 straight and rolled cutter candidates from accepted C5.

This consumes stored C5 expressions, not re-running their certificate. All
cuts and rotational transfers are planning candidates pending independent
integration review, source trim/material proof and a combined error budget.
"""
import json
import math
from fractions import Fraction
from pathlib import Path
from .regional_construction import build_candidate
from .construction_domain import assess_candidate_domain
from .flank_parameters import build_parameters

C5 = Path('workspace/v3/p3/P3-PARAMETERS-01/flank-parameter-expression-c5.json')
SHAFT = Path('workspace/v3/p3/P3-SHAFT-FACES-03/carrier-chart-evidence.json')
ROLL = Path('workspace/v3/p3/P3-SWEPT-ANALYSIS-01/shoulder-construction-c4.json')


def _read(root, path):
    return json.loads((Path(root) / path).read_text(encoding='utf8'))


def build_default_flank_candidate(root, overrides=None):
    overrides = dict(overrides or {})
    original_c5, charts, roll = (_read(root, path) for path in (C5, SHAFT, ROLL))
    flank_inputs = {p['id'] for p in original_c5['parameters']
                    if p['classification'] in {'independent', 'independent_shared',
                                               'external_stock_dependency_editability_unresolved'}}
    c5_edits = {k: v for k, v in overrides.items() if k in flank_inputs}
    stock_edits = {k: v for k, v in overrides.items() if k not in flank_inputs or k == 'shaft_outer_diameter_mm'}
    base = build_candidate(root, stock_edits)
    domain = assess_candidate_domain(root, stock_edits)
    if not domain['all_listed_checks_passed']:
        raise ValueError('stock or slot necessary event guard fails')
    c5 = build_parameters(root, c5_edits) if c5_edits else original_c5
    if (c5['schema'] != 'p3-flank-parameter-expression/0.1'
            or charts['schema'] != 'p3-shaft-physical-carrier-charts/1.0'
            or roll['schema'] != 'p3-shoulder-construction-c4/1.0'):
        raise ValueError('wrong candidate evidence')
    parameters = {item['id']: item for item in c5['parameters']}
    rational = lambda name: Fraction(*parameters[name]['value_exact'])
    pitch, root_radius, phase, diameter = (rational(name) for name in
        ('pitch_radius_mm','root_radius_mm','phase_rad','shaft_outer_diameter_mm'))
    shaft_radius, cap_radius, roll_radius = diameter/2, Fraction(131,10), Fraction(15)
    if not 0 < shaft_radius < cap_radius < roll_radius or not 0 < root_radius < pitch:
        raise ValueError('six-edge profile or roll-radius guard fails')
    templates = c5['templates']
    def component(side, name): return templates[side]['endpoints'][name]
    def bound_abs(coord):
        return max(abs(Fraction(coord['lower'])), abs(Fraction(coord['upper'])))
    max_pole_t = max(bound_abs(p['t_mm']) for side in templates.values() for p in side['poles'])
    min_pole_r = min(Fraction(p['r_mm']['lower']) for side in templates.values() for p in side['poles'])
    cap_t = max(bound_abs(component(side,'outer')['t_mm'])*cap_radius/shaft_radius for side in ('F0002','F0024'))
    if c5['validation'].get('simple_four_segment_loop') != 'sufficient strict interval guards passed' or c5['validation'].get('six_segment_auxiliary_roll_clearance') != 'sufficient strict interval guards passed with cap=13.1 mm, roll=15 mm':
        raise ValueError('C5 default loop guard was not established')
    if any(bound_abs(p['t_mm'])**2 + bound_abs(p['r_mm'])**2 >= cap_radius**2
           for side in templates.values() for p in side['poles']):
        raise ValueError('C5 control hull leaves auxiliary cap')
    # Positive short cap arc has |t| bounded by its endpoint magnitudes. The
    # root arc is the lower half of its circle; pole bounds cover the splines.
    t_upper = max(max_pole_t, cap_t, root_radius)
    r_lower = min(min_pole_r, pitch-root_radius,
                  min(Fraction(component(side,'outer')['r_mm']['lower']) for side in ('F0002','F0024')))
    guards = roll['rotation_tool_and_clipping']['domain_guards']
    if not t_upper < Fraction(str(guards['analytic_t_guard_mm'])) or not r_lower > Fraction(str(guards['s_lower_guard_mm'])):
        raise ValueError('reference roll section leaves reviewed conservative strip')
    if not 0 < pitch+root_radius < cap_radius:
        raise ValueError('root circle lies outside auxiliary cap')
    stock = base['parameters']
    expected = {'stock.Rshaft':float(shaft_radius), 'stock.Y7':-69.76410523497,
                'stock.Y8':-67.0, 'stock.R9':13.0, 'stock.M8':17.1665, 'stock.tube_R8':5.0}
    if not overrides and any(abs(stock[k]-v)>1e-9 for k,v in expected.items()):
        raise ValueError('reviewed ideal stock strip does not match default candidate')
    if not 0 < stock['stock.M8']-stock['stock.R9'] < stock['stock.tube_R8']:
        raise ValueError('stock s8 inner branch event guard fails')
    if abs(stock['stock.Rshaft']-float(shaft_radius)) > 1e-12:
        raise ValueError('stock and C5 shaft diameter disagree')
    if not stock['stock.Y6'] < -71 < stock['stock.Y7'] or not stock['stock.Y4'] < -71:
        raise ValueError('straight and shoulder junction leaves the stock interval')
    if max(stock['stock.R0'],stock['stock.R1'],stock['stock.R3']) >= float(r_lower):
        raise ValueError('tail stock does not clear the cutter section')
    source_frame = c5['placement_contract']['frame']['axis_point']
    axis_shift = math.hypot(source_frame[0], source_frame[2])
    if axis_shift >= 1e-12:
        raise ValueError('C5/stock axis shift requires separate analysis')
    # Canonical axis is the stock axis; the tiny source C5 axis shift remains
    # an explicit uncombined budget item rather than being silently discarded.
    section = {'id':'section6', 'kind':'closed_profile_t_r', 'basis':'two C5 original order/knots and their own FIN intervals',
        'templates': {name: {'basis': templates[name]['basis'], 'poles': templates[name]['poles'],
                             'endpoints': templates[name]['endpoints']} for name in ('F0002','F0024')},
        'edges': [
            {'kind':'bspline', 'template':'F0024', 'from':'F0024.root', 'to':'F0024.outer', 'parameter_direction':'increasing'},
            {'kind':'radial_line', 'from':'F0024.outer', 'to':'F0024.cap', 'end_expression':'outer*(Rcap/Rshaft)'},
            {'kind':'circle_arc', 'from':'F0024.cap', 'to':'F0002.cap', 'center_t_r_mm':[0,0], 'radius_mm':float(cap_radius), 'branch':'positive_r_short'},
            {'kind':'radial_line', 'from':'F0002.cap', 'to':'F0002.outer', 'start_expression':'outer*(Rcap/Rshaft)'},
            {'kind':'bspline', 'template':'F0002', 'from':'F0002.outer', 'to':'F0002.root', 'parameter_direction':'increasing'},
            {'kind':'circle_arc', 'from':'F0002.root', 'to':'F0024.root', 'center_t_r_mm':[0,float(pitch)], 'radius_mm':float(root_radius), 'branch':'lower_r'},
        ], 'endpoint_contract':'shared C5 circle expressions; stored pole and endpoint decimal previews are not exact equality certificates'}
    records = charts['records']
    if len(records) != 44 or len({x['face'] for x in records}) != 44:
        raise ValueError('shaft chart coverage mismatch')
    by_face = {x['face']:x for x in records}
    nodes = list(base['candidate_csg'])
    member_nodes = []
    previous = 'stock_with_rear_slot'
    for member in c5['member_placements']:
        index = member['member_index']; theta = float(phase) + index*2*math.pi/22
        er, et = [math.sin(theta),0,math.cos(theta)], [math.cos(theta),0,-math.sin(theta)]
        faces = member['side_face_ids']
        if (set(faces) != {'F0002_like','F0024_like'}
                or any(face not in by_face or by_face[face]['member'] != member['p1_cylinder_face_id'] for face in faces.values())):
            raise ValueError('shaft chart/member association mismatch')
        prefix = 'member_%02d_' % index
        frame = {'origin_mm':[0,-71,0], 'e_t':et, 'e_r':er,
                 'mapping':'point=origin+t*e_t+r*e_r'}
        straight, rolled = prefix+'straight_tool', prefix+'roll_tool'
        clip, both, cut = prefix+'roll_stock_intersection', prefix+'combined_tool', prefix+'result'
        nodes.extend([
            {'id':straight,'operation':'extrude_profile','profile':'section6','frame':frame,
             'y_limits_mm':[stock['stock.Y4'],-71], 'depends_on':[]},
            {'id':rolled,'operation':'revolve_profile','profile':'section6','frame':frame,
             'axis_point_mm':[15*er[0],-71,15*er[2]],'axis_direction':et,
             'angle_rad':math.pi/2,'depends_on':[]},
            {'id':clip,'operation':'intersect','left':rolled,'right':'stock_revolve',
             'depends_on':[rolled,'stock_revolve'],'status':'candidate_only'},
            {'id':both,'operation':'union','left':straight,'right':clip,'depends_on':[straight,clip],
             'status':'candidate_only'},
            {'id':cut,'operation':'subtract','target':previous,'tool':both,'depends_on':[previous,both],
             'status':'candidate_only'},
        ])
        member_nodes.append({'member_index':index,'p1_cylinder_face':member['p1_cylinder_face_id'],
            'straight_faces':faces,'shared_roll_axis':rolled,'root_and_two_shoulders_use_same_axis':True,
            'shaft_source_charts':[{'face':face,'source_path':by_face[face]['source_path'],
                                    'chart_to_c5_bound_mm':by_face[face]['carrier_chart_to_C5_candidate_L1_upper_mm_conditional_on_01'] if not overrides else None,
                                    'bound_scope':'default C5 only; edited construction requires new correspondence'}
                                   for face in faces.values()],
            'individual_source_trim_and_stock_exit':'open'})
        previous = cut
    if (len(member_nodes) != 22 or len({m['p1_cylinder_face'] for m in member_nodes}) != 22
            or sorted(m['member_index'] for m in member_nodes) != list(range(22))):
        raise ValueError('member placement coverage mismatch')
    return {'schema':'p3-default-flank-csg-candidate/0.1','unit':'mm','frame':'absolute_part_coordinates',
            'sources':[C5.as_posix(),SHAFT.as_posix(),ROLL.as_posix()], 'stock_and_head':base,
            'c5_evaluation': 'recomputed_for_edited_flank_inputs' if c5_edits else 'stored_default',
            'c5_parameters': c5['parameters'], 'c5_circle_expressions': c5['circle_expressions'],
            'c5_placement_contract': c5['placement_contract'],
            'overrides': overrides, 'candidate_domain_checks': domain,
            'events': [{'id':'s8_inner_branch', 'value_mm':stock['stock.M8']-stock['stock.R9'],
                        'required':'0 < value < stock.tube_R8'},
                       {'id':'roll_station_in_stock_s7', 'value_mm':-71,
                        'required':'stock.Y6 < value < stock.Y7'},
                       {'id':'head_mouth_on_positive_cone', 'value_mm':base['head_carriers']['mouth_radius_mm'],
                        'required':'value > 0'}],
            'section':section,'csg_nodes':nodes,'members':member_nodes,
            'default_section_guards':{'max_abs_t_upper_mm':float(t_upper),'min_r_lower_mm':float(r_lower),
                't_limit_mm':guards['analytic_t_guard_mm'],'r_lower_limit_mm':guards['s_lower_guard_mm'],
                'Rshaft_mm':float(shaft_radius),'Rcap_mm':float(cap_radius),'roll_radius_mm':float(roll_radius),
                'stock_strip_matches_reference_within_mm':1e-9 if not overrides else None,
                'C5_axis_to_candidate_stock_axis_translation_mm':axis_shift,
                'C5_axis_to_candidate_stock_axis_translation_L1_mm':abs(source_frame[0])+abs(source_frame[2]),
                'interpretation':'same ideal section and common-axis placement for all members; transfer of the F0047 reference stock proof is conditional on its stated approximations and independent integration review'},
            'limitations':['edits are evaluated candidates; listed checks are necessary, not a complete valid edit domain',
                           'sweep/clip and boolean order are proposals, not demonstrated native capability',
                           'actual source FIN/stock exit, material occupancy, and global error budget remain open',
                           'axis shift and C5 preview rounding are not included in any complete source-to-result bound'],
            'execution_approved':False}
