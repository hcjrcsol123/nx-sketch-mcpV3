"""Join reviewed P3 observations without treating local bounds as whole faces.

This planning ledger is specific to the current P1 snapshot and refers to
original evidence; it neither runs NX nor approves any construction.
"""
import json
import math
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

from .regions.common import normalize_snapshot
from .flank_construction import build_default_flank_candidate

BASE = Path('workspace/v3/p3')
PATHS = {
    'dag': BASE / 'P3-DAG-02/design-dag.json',
    'roots': BASE / 'P3-SHOULDERS-ANALYSIS-02/native-root-ledger.json',
    'exits': BASE / 'P3-ROOT-TRIM-04/22-root-mixed-index.json',
    'arcs': BASE / 'P3-ROOT-ARC-01/root-arc-proof.json',
    'shoulders': BASE / 'P3-SHOULDERS-ANALYSIS-03/visible-profile-comparison.json',
    'swept': BASE / 'P3-SWEPT-ANALYSIS-01/source-map.json',
    'parameters': BASE / 'P3-PARAMETERS-01/flank-parameter-expression-c5.json',
}
REVIEWS = {
    'roots': 'tests/v3/evidence/p3-root-exit-review.md#M2',
    'arcs_shoulders': 'tests/v3/evidence/p3-region-review-20261112.md',
    'dag': 'tests/v3/evidence/p3-region-plan-review.md',
}
DECISIONS = [
    'p3-shared-22-user-decision.json', 'p3-independent-flanks-user-decision.json',
    'p3-linear-geometry-target.json', 'p3-shared-flank-templates-user-decision.json',
    'p3-rear-slot-independent-user-decision.json',
    'p3-independent-flank-connection-angles-user-decision.json',
]
REGION_EVIDENCE = {
    'stock': [('workspace/v3/p3/P3-STOCK-02/stock-source-audit.json',
               'partial source containment; residual and full envelope remain open')],
    'lower_head': [('workspace/v3/p3/P3-REGION-PLAN-02/remaining-regions.json',
                    'source responsibility; complete cavity trim and occupancy remain open')],
    'upper_head': [('workspace/v3/p3/P3-HEAD-01/head-canonicalization-c5.json',
                    'H05 accepted canonical carrier and finite-curve bounds; not complete source trim')],
    'flanks': [('workspace/v3/p3/P3-SHAFT-FACES-01/combined-bound.json',
                'finite curves under independent review; complete surface remains open')],
}


def _read(root, path):
    return json.loads((root / path).read_text(encoding='utf-8'))


def _indexed(items, field):
    out = {item[field]: item for item in items}
    if len(out) != len(items):
        raise ValueError('duplicate identity: ' + field)
    return out


def _resolve_pointer(doc, pointer):
    if pointer:
        for key in pointer.lstrip('/').split('/'):
            doc = doc[int(key)] if isinstance(doc, list) else doc[key]
    return doc


def evaluate_head_removal(plan, x, y, z):
    """Evaluate component membership of the head CSG in binary64, in mm.

    Boundary decisions are numerical previews, not interval or native proofs.
    """
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (x, y, z)):
        raise ValueError('head evaluation point must be finite')
    p = {entry['id']: entry['value'] for entry in plan['parameters']}
    r2 = x*x+z*z
    components = []
    lower, upper = p['head.lower_sphere_contact_y'], p['head.upper_sphere_contact_y']
    if -p['head.R31'] <= y <= p['head.Y_lower_step'] and r2+y*y <= p['head.R31']**2:
        components.append('head.R31_piece')
    def fillet_piece(label, lo, hi):
        if not lo <= y <= hi:
            return False
        radicand = p['head.r_'+label+'_fillet']**2-(y-p['head.'+label+'_fillet_y'])**2
        return radicand >= 0 and math.sqrt(r2) <= p['head.'+label+'_fillet_major']+math.sqrt(radicand)
    if fillet_piece('lower', p['head.Y_lower_step'], lower):
        components.append('head.lower_fillet_piece')
    if lower <= y <= upper and r2+(y-p['head.Y40'])**2 <= p['head.R40']**2:
        components.append('head.R40_piece')
    if fillet_piece('upper', upper, p['head.Y_head_step']):
        components.append('head.upper_fillet_piece')
    if p['head.Y_head_step'] <= y <= p['stock.Y_mouth']:
        if r2+y*y <= p['head.R32']**2:
            components.append('head.R32_piece')
        if y >= p['head.cone_apex_Y'] and math.sqrt(r2) <= math.tan(p['head.cone_half_angle_initial_exact'])*(y-p['head.cone_apex_Y']):
            components.append('head.cone_piece')
    for i in range(6):
        prefix = 'head.sector.%d.' % i
        theta = p[prefix+'theta']
        s = math.cos(theta)*x+math.sin(theta)*z
        t = math.sin(theta)*x-math.cos(theta)*z
        if t < 0:
            continue
        rho = math.hypot(t, y-p['head.Y40'])
        seams = [p[prefix+'branch.%d.contact_s' % j] for j in range(2)]
        if (upper <= y <= p['stock.Y_mouth'] and min(seams) <= s <= max(seams)
                and (rho-p[prefix+'RA'])**2+s*s <= p[prefix+'ra']**2):
            components.append(prefix+'A_piece')
        if p['head.Y_head_step'] <= y <= p['stock.Y_mouth']:
            for j, seam in enumerate(seams):
                b = prefix+'branch.%d.' % j
                if (((s >= seam) if j == 0 else (s <= seam))
                        and (rho-p[b+'major_radius'])**2+(s-p[b+'d'])**2 <= p[b+'rb']**2):
                    components.append(b+'B_piece')
    return {'inside': bool(components), 'components': components,
            'scope': 'binary64 candidate preview; boundary and edited-domain proofs not inferred'}


def build_regional_construction(root, overrides=None):
    """Evaluate the actual candidate operation graph and its scoped error budget.

    The head carriers are explicit surfaces, not closed solids. The chart
    bound is conditional on the reviewed source assumptions and applies only
    to the default flank, not the complete native surface or resulting part.
    """
    candidate = build_default_flank_candidate(root, overrides)
    tail_path = Path('workspace/v3/p3/P3-TAIL-REGION-04/finite-regions.json')
    tail = _read(Path(root), tail_path)
    if tail['schema'] != 'p3-tail-finite-region/1.0':
        raise ValueError('tail finite-region evidence schema mismatch')
    head_path = Path('workspace/v3/p3/P3-HEAD-02/whole-head-csg-dag.json')
    head_dag = _read(Path(root), head_path)
    if head_dag['schema'] != 'p3-head02-whole-head-csg-dag/0.1':
        raise ValueError('head CSG candidate schema mismatch')
    root_graph_path = Path('workspace/v3/p3/P3-ROOT-CONE-06/cylinder-c5-cone.json')
    root_graph = _read(Path(root), root_graph_path)
    if root_graph['schema'] != 'p3-cylinder-c5-cone-graph/1.0':
        raise ValueError('root carrier graph evidence schema mismatch')
    stock_base = Path('workspace/v3/p3/P3-STOCK-REGION-05')
    stock_carriers, stock_events, stock_patches = (_read(Path(root), stock_base / name) for name in
        ('meridian-carriers.json', 'circular-events.json', 'ordinary-patches.json'))
    head_budgets_path = Path('workspace/v3/p3/P3-HEAD-02/whole-head-reviewed-face-budgets.json')
    head_budgets = _read(Path(root), head_budgets_path)
    shoulder_base = Path('workspace/v3/p3/P3-SHOULDER-STOCK-05')
    shoulder_names = ('all-shoulders-graph-transfer.json', 'all-shoulder-transition-events.json',
                      'all-s7-first-exit-guard.json', 'source-shoulder-regions.json')
    shoulder_graphs, shoulder_events, shoulder_exits, shoulder_regions = (
        _read(Path(root), shoulder_base / name) for name in shoulder_names)
    if (stock_carriers['schema'] != 'p3-stock-meridian-carrier-correspondence/1.0'
            or stock_events['schema'] != 'p3-stock-finite-circular-events/1.0'
            or stock_patches['schema'] != 'p3-stock-ordinary-patches/1.0'
            or head_budgets['schema'] != 'p3-head02-reviewed-face-budgets/1'):
        raise ValueError('regional budget evidence schema mismatch')
    if (len(stock_carriers['rows']) != 20 or len({x['segment'] for x in stock_carriers['rows']}) != 20
            or len(head_budgets['records']) != 45 or len({x['source_face'] for x in head_budgets['records']}) != 45):
        raise ValueError('regional evidence mapping coverage mismatch')
    member_map = {m['p1_cylinder_face']: m for m in candidate['members']}
    region_pairs = {(r['member'], r['shoulder']) for r in shoulder_regions['rows']}
    if (len(shoulder_regions['rows']) != 44 or len(region_pairs) != 44
            or len(shoulder_graphs['rows']) != 88
            or len({(r['member'], r['shoulder'], r['stock_kind']) for r in shoulder_graphs['rows']}) != 88
            or {(r['member'], r['shoulder']) for r in shoulder_graphs['rows']} != region_pairs
            or len(shoulder_events['rows']) != 44 or {(r['member'], r['shoulder']) for r in shoulder_events['rows']} != region_pairs
            or len(shoulder_exits['rows']) != 44 or {(r['member'], r['shoulder']) for r in shoulder_exits['rows']} != region_pairs):
        raise ValueError('shoulder graph and region mapping coverage mismatch')
    for row in shoulder_regions['rows']:
        if (row['member'] not in member_map or
                member_map[row['member']]['straight_faces'].get(row['side_template']) != row['boundary_parents']['straight_flank']):
            raise ValueError('shoulder graph and C5 flank association mismatch')
    head = candidate['stock_and_head']['head_carriers']
    profiles = {'stock_profile': candidate['stock_and_head']['stock_profile'],
                candidate['section']['id']: candidate['section']}
    nodes = list(candidate['csg_nodes'])
    nodes.append({'id': 'head_cone_carrier', 'operation': 'cone_carrier',
                  'apex_y_mm': head['cone_apex_y_mm'], 'half_angle_rad': head['cone_half_angle_rad'],
                  'mouth_y_mm': head['mouth_y_mm'], 'mouth_radius_mm': head['mouth_radius_mm'], 'depends_on': []})
    nodes.append({'id': 'head_sphere_carrier', 'operation': 'sphere_carrier',
                  'center_mm': head['sphere_center_mm'], 'radius_mm': head['sphere_radius_mm'], 'depends_on': []})
    for name in ('lower_fillet', 'upper_fillet'):
        nodes.append({'id': 'head_' + name, 'operation': 'torus_carrier',
                      'geometry': head[name], 'depends_on': []})
    for i, sector in enumerate(head['sectors']):
        a = 'head_sector_%d' % i
        nodes.append({'id': a, 'operation': 'torus_carrier',
                      'geometry': {k: v for k, v in sector.items() if k != 'branches'}, 'depends_on': []})
        for j, branch in enumerate(sector['branches']):
            nodes.append({'id': a + '_branch_%d' % j, 'operation': 'tangent_torus_carrier',
                          'geometry': branch, 'depends_on': [a]})
    parameter_ids = {p['id'] for p in candidate['stock_and_head']['parameter_graph']}
    for original in head_dag['nodes']:
        node = deepcopy(original)
        if set(node.get('depends_on_parameters', [])) - parameter_ids:
            raise ValueError('unresolved head construction parameter')
        if node['operation'] == 'bounded_set':
            node['depends_on'] = []
        if node['id'] == 'head.result':
            if node['target'] != 'stock_with_prior_cuts':
                raise ValueError('head target interface mismatch')
            node['target'] = 'member_21_result'
            node['depends_on'] = ['member_21_result', node['tool']]
        nodes.append(node)
    seen = set()
    for node in nodes:
        if node['id'] in seen or not set(node['depends_on']) <= seen:
            raise ValueError('invalid construction dependency order')
        if 'profile' in node and node['profile'] not in profiles:
            raise ValueError('unresolved construction profile')
        seen.add(node['id'])
    shift = candidate['default_section_guards']['C5_axis_to_candidate_stock_axis_translation_L1_mm']
    local_budgets = []
    for member in candidate['members']:
        for chart in member['shaft_source_charts']:
            bound = chart['chart_to_c5_bound_mm']
            total = None if bound is None else math.nextafter(bound + shift, math.inf)
            local_budgets.append({'face': chart['face'], 'source': chart['source_path'],
                                  'chart_to_default_C5_L1_mm_conditional': bound,
                                  'axis_translation_L1_mm': shift,
                                  'conditional_chart_to_candidate_upper_mm': total,
                                  'within_0_001_mm': None if total is None else total <= 0.001,
                                  'scope': 'reviewed carrier chart to ideal default C5 candidate; excludes native trim, source validity and numerical representation'})
    root_rows = {row['index']: row for row in root_graph['rows']}
    if len(root_graph['rows']) != 22 or len(root_rows) != 22 or set(root_rows) != set(range(22)):
        raise ValueError('root carrier graph member coverage mismatch')
    axis = candidate['c5_placement_contract']['frame']['axis_point']
    # The reviewed source graph is in the slightly displaced C5 frame. Its
    # cone has slope 1/sqrt(3)<1, so twice the exact binary64 XZ L1 translation
    # bounds the additional horizontal plus axial displacement to zero axis.
    root_axis = abs(Fraction(axis[0])) + abs(Fraction(axis[2]))
    root_budgets = []
    for member in candidate['members']:
        row = root_rows[member['member_index']]
        if row['member'] != member['p1_cylinder_face']:
            raise ValueError('root carrier graph member association mismatch')
        source_bound = Fraction(row['source_to_c5_canonical_cone_exit_upper_mm'])
        total = math.nextafter(float(source_bound + 2*root_axis), math.inf)
        root_budgets.append({'member': row['member'], 'index': row['index'],
                             'source_to_C5_axis_graph_upper_mm': str(source_bound),
                             'zero_axis_translation_plus_cone_slope_upper_mm_exact': [2*root_axis.numerator, root_axis.denominator],
                             'source_to_zero_axis_graph_upper_mm': total if not candidate['overrides'] else None,
                             'scope': 'default cylinder/cone carrier graphs at common global azimuth and reviewed radial interval; not finite native trim, material or converted spline error'})
    return {'schema': 'p3-regional-construction-integration/0.1', 'unit': 'mm',
            'frame': 'absolute_part_coordinates', 'overrides': candidate['overrides'],
            'parameters': candidate['stock_and_head']['parameter_graph'],
            'c5_parameters': candidate['c5_parameters'],
            'c5_circle_expressions': candidate['c5_circle_expressions'],
            'c5_placement_contract': candidate['c5_placement_contract'],
            'head_csg': {'source': str(head_path), 'definitions': head_dag['definitions'],
                         'derived_parameter_expressions': head_dag['derived_parameter_expressions'],
                         'edit_recomputation_requirements': head_dag['edits_require_recomputation'],
                         'status': 'conditional candidate; source finite-domain and material correspondence remain open',
                         'initial_candidate_review': 'tests/v3/evidence/p3-head-review-20261113.md#h208',
                         'initial_candidate_review_applies': not bool(candidate['overrides']),
                         'reviewed_initial_scope': 'continuous-domain radial single interval, specified artificial cap hiding and mouth nesting; not complete source face correspondence or whole-head budget'},
            'profiles': profiles, 'nodes': nodes, 'members': candidate['members'],
            'events': candidate['events'], 'domain_checks': candidate['candidate_domain_checks'],
            'c5_evaluation': candidate['c5_evaluation'],
            'tail_region': {'evidence': str(tail_path),
                            'review': 'tests/v3/evidence/p3-tail-region-review.md#tr401',
                            'default_source_correspondence_applies': not bool(candidate['overrides']),
                            'definitions_at_default': tail['definitions'],
                            'regions_at_default': tail['regions'], 'native_loops_at_default': tail['native_loops'],
                            'candidate_csg_at_default': tail['csg'],
                            'conditional_four_face_two_sided_upper_mm': 0.000004 if not candidate['overrides'] else None,
                            'conditions': ['native finite-trim, carrier and common ABS frame semantics',
                                           'source stock material occupancy',
                                           'default parameters only; not a whole-part error bound']},
            'budget': {'target_mm': 0.001, 'shaft_chart_budgets': local_budgets,
                       'root_carrier_graph_source': str(root_graph_path), 'root_carrier_graph_budgets': root_budgets,
                       'stock_regional_evidence': {'sources': [(stock_base / n).as_posix() for n in
                           ('meridian-carriers.json', 'circular-events.json', 'ordinary-patches.json')],
                           'review': 'tests/v3/evidence/p3-stock-region-review.md',
                           'default_bounds_apply': not bool(candidate['overrides']),
                           'source_records_scope': 'frozen default evidence; candidate fields describe the original default construction, not evaluated edited geometry',
                           'carriers': stock_carriers['rows'], 'algebraic_events': stock_carriers['algebraic_events'],
                           'finite_circular_events': stock_events['records'], 'ordinary_patch_candidates': stock_patches['rows'],
                           'scope': 'distinct carrier, event and candidate-patch scopes; not a full source trim or whole-stock bound'},
                       'head_regional_evidence': {'source': str(head_budgets_path),
                           'review': head_budgets['review_evidence'],
                           'default_bounds_apply': not bool(candidate['overrides']),
                           'source_records_scope': 'frozen default evidence; bounds are not applicable to edited construction',
                           'records': head_budgets['records'], 'composition': head_budgets['composition'],
                           'r40_union_source_ids': head_budgets['r40_union_source_ids'],
                           'scope': 'conditional reviewed face groups; R40 is a union and pending faces remain open'},
                       'shoulder_regional_evidence': {'sources': [(shoulder_base / n).as_posix() for n in shoulder_names],
                           'review': 'tests/v3/evidence/p3-shoulder-stock-review-20261113.md',
                           'default_bounds_apply': not bool(candidate['overrides']),
                           'source_records_scope': 'frozen default evidence; bounds and coordinates are not applicable to edited construction',
                           'carrier_graphs': shoulder_graphs['rows'], 'transition_events': shoulder_events['rows'],
                           'same_branch_s7_exits': shoulder_exits['rows'], 'source_loops': shoulder_regions['rows'],
                           's7_exit_common_upper_mm': shoulder_exits['same_branch_first_exit_displacement_upper_mm'],
                           'scope': 'conditional carrier graphs and same-branch events; native branch selection, finite filling, material and original edge errors remain open; do not sum dissimilar scopes'},
                       'whole_part_bound_mm': None,
                       'missing': ['native source validity and finite trim correspondence',
                                   'stock, slot, head, roots and shoulders material closure',
                                   'candidate numerical representation and boolean operation bounds',
                                   'edited source correspondence where parameters change']},
            'open': ['head finite trim and material', 'tail stock source occupancy and edited correspondence',
                     'root and shoulder individual trim and stock intersection',
                     'whole-part error budget and operation proof'],
            'execution_approved': False}


def build_decision_overlays(root, parameter_doc, members):
    """Bind newly confirmed intent without rewriting the accepted C5 expression."""
    diameter_path = 'docs/v3/decisions/p3-shaft-diameter-editable-user-decision.json'
    shoulder_path = 'docs/v3/decisions/p3-shoulder-flank-link-user-decision.json'
    diameter = _read(root, diameter_path)
    shoulder = _read(root, shoulder_path)
    if (diameter.get('schema') != 'v3-user-design-decision/1.0'
            or diameter.get('authority') != 'explicit user reply in this conversation'
            or diameter.get('decision_id') != 'P3-USER-SHAFT-DIAMETER-EDITABLE-01'
            or diameter.get('answer') != '轴外径独立可编辑，外端半径随动（推荐）'
            or diameter.get('scope') != {'shaft_outer_diameter': 'independent editable dimension',
                                         'outer_endpoint_radius': 'derived as shaft outer diameter / 2',
                                         'consumers': ['stock shaft outer radius', 'F0002.outer.circle_point', 'F0024.outer.circle_point']}
            or diameter.get('source_binding', {}).get('parameter_expression') != PATHS['parameters'].as_posix()
            or diameter.get('source_binding', {}).get('prior_flank_angles_decision') != 'docs/v3/decisions/p3-independent-flank-connection-angles-user-decision.json'
            or shoulder.get('schema') != 'v3-user-design-decision/1.0'
            or shoulder.get('authority') != 'explicit user reply in this conversation'
            or shoulder.get('decision_id') != 'P3-USER-SHOULDER-FLANK-LINK-01'
            or shoulder.get('answer') != '肩部随对应直翼母形联动（推荐）'
            or shoulder.get('scope') != {'link': 'each shoulder follows its corresponding straight-flank template',
                                         'generation': 'each shoulder revolves about its own transverse axis',
                                         'trim': 'each shoulder is trimmed at its own intersection with stock',
                                         'shared_trim_across_shoulders': False, 'additional_tangency_constraint': False}
            or shoulder.get('source_binding', {}).get('parameter_expression') != PATHS['parameters'].as_posix()
            or shoulder.get('source_binding', {}).get('shoulder_comparison') != PATHS['shoulders'].as_posix()
            or shoulder.get('source_binding', {}).get('shared_templates_decision') != 'docs/v3/decisions/p3-shared-flank-templates-user-decision.json'):
        raise ValueError('decision binding mismatch')
    param = next(p for p in parameter_doc['parameters'] if p['id'] == 'shaft_outer_diameter_mm')
    circles = [c for c in parameter_doc['circle_expressions'] if '.outer.circle_point' in c['id']]
    if (len(circles) != 2 or any(c['radius_expression'] != 'shaft_outer_diameter_mm/2' for c in circles)):
        raise ValueError('C5 outer-radius dependency mismatch')
    default = Fraction(*param['value_exact'])
    default_radius = default / 2
    return {
        'shaft_diameter': {'decision': diameter_path,
                           'parameter': 'shaft_outer_diameter_mm', 'classification': 'independent',
                           'default_exact_mm': param['value_exact'],
                           'source_classification': param['classification'],
                           'derived_radius': {'expression': 'shaft_outer_diameter_mm/2',
                                              'default_exact_mm': [default_radius.numerator, default_radius.denominator],
                                              'consumers': ['stock shaft outer radius'] + [c['id'] for c in circles]},
                           'scope': 'planning intent; native propagation and edit domain remain unverified'},
        'shoulder_flank_link': {'decision': shoulder_path,
                                'members': [{'root_cylinder': m['root_cylinder'],
                                             'shoulders': [{'shoulder': s['shoulder'],
                                                            'flank': s['straight_flank'],
                                                            'side': s['side']}
                                                           for s in m['shoulder_seams']]}
                                            for m in members],
                                'scope': shoulder['scope'],
                                'qualification': 'intent only; source trim, edit domain and native propagation remain open'},
    }


def build_integration(root):
    root = Path(root)
    data = {key: _read(root, path) for key, path in PATHS.items()}
    dag, ledger, index = data['dag'], data['roots'], data['exits']
    sid = dag['p1_snapshot_id']
    review = (root / 'tests/v3/evidence/p3-root-exit-review.md').read_text(encoding='utf-8')
    if 'M2 ACCEPTED WITH SCOPE LIMITS' not in review or '混合索引覆盖全部 22 根' not in review:
        raise ValueError('local root review not accepted')
    if data['swept']['p1_snapshot_id'] != sid:
        raise ValueError('snapshot mismatch')
    groups = _indexed(ledger['groups'], 'member')
    placements = _indexed(data['parameters']['member_placements'], 'p1_cylinder_face_id')
    source_members = _indexed(data['swept']['members'], 'p1_cylinder_face_id')
    exits = _indexed(index['results'], 'label')
    if set(groups) != set(placements) or set(groups) != set(source_members):
        raise ValueError('member mapping mismatch')
    if {g['root_shoulder_face'] for g in groups.values()} != set(exits):
        raise ValueError('root certificate mapping mismatch')
    shoulders = data['shoulders']['records']
    arcs = data['arcs']['records']
    result = []
    for member, group in sorted(groups.items(), key=lambda item: item[1]['member_index']):
        placement, source_member = placements[member], source_members[member]
        if placement['member_index'] != group['member_index'] or source_member['member_index'] != group['member_index']:
            raise ValueError('member order mismatch')
        sides = placement['side_face_ids']
        if set(sides.values()) != set(source_member['p1_swept_face_ids']):
            raise ValueError('flank mapping mismatch')
        face = group['root_shoulder_face']
        ref = exits[face]
        cert = _resolve_pointer(_read(root, ref['certificate_path']), ref['json_pointer'])
        cert_source = cert.get('target', cert.get('source', {}))
        cert_sid = cert_source.get('source_snapshot_id')
        if cert_sid != ref['source_snapshot_id'] or cert_sid != group['root_native']['snapshot_id']:
            raise ValueError('root detail snapshot mismatch')
        if (cert.get('schema') not in {'p3-four-fin-multispan-exit/0.1', 'p3-f0123-root-exit-tube/0.1', 'p3-double-fin-root-exit-tube/0.2'}
                or cert.get('status') != 'validated_tube_graph_API_source_association_conditional'
                or cert_source.get('p1_snapshot_id') != sid
                or cert_source.get('source_snapshot_path') != group['root_native']['source_path']
                or cert.get('execution_approved') is not False):
            raise ValueError('root certificate does not match accepted local scope')
        face_arcs = [x for x in arcs if x['root'] == face]
        face_shoulders = [x for x in shoulders if x['member'] == member]
        if {x['straight_flank'] for x in face_shoulders} != set(sides.values()):
            raise ValueError('shoulder to flank mapping mismatch')
        fin_arcs = {x['P1_shared_edge']: x['P1_neighbor_candidate'] for x in group['root_FINs_in_source_loop_order']
                    if x['edge_geometry'].get('type') == 'circular_evaluator'}
        arc_pairs = [(x['P1_shared_edge'], x['P1_neighbor_candidate']) for x in face_arcs]
        if len(fin_arcs) != 3 or len(face_arcs) != 3 or len(set(arc_pairs)) != 3 or dict(arc_pairs) != fin_arcs:
            raise ValueError('root arc association mismatch')
        result.append({
            'member_index': group['member_index'], 'root_cylinder': member,
            'root_shoulder_face': face, 'source_snapshot_id': cert_sid,
            'source_detail_path': group['root_native']['source_path'],
            'source_trim': {'directed_fins_in_source_order': [
                {k: fin[k] for k in ('P1_shared_edge', 'P1_neighbor_candidate',
                                    'fin_geometry', 'fin_geometry_sense',
                                    'loop_child_orientation', 'edge_child_orientation')}
                for fin in group['root_FINs_in_source_loop_order']],
                'full_candidate_trim_status': 'conditional_not_proven'},
            'implicit_exit': {'certificate_path': ref['certificate_path'],
                              'json_pointer': ref['json_pointer'],
                              'review': REVIEWS['roots'], 'status': cert['status'],
                              'graph_window': cert['graph_window'],
                              'finite_branch_evidence': cert.get('termination', cert.get('edges')),
                              'evidence_acceptance': 'accepted_local_scope_M2',
                              'scope': 'local FIN-to-implicit branch; not full trim or material membership'},
            'class10_arcs': [{'p1_edge': a['P1_shared_edge'],
                              'neighbor_candidate': a['P1_neighbor_candidate'],
                              'FIN_parameter_range': a['finite_FIN_parameter_range'],
                              'eval_limits': a['finite_EVAL_limits'],
                              'topology_directions': a['topology_directions'],
                              'bound_mm_exact': a['full_curve_same_normalized_parameter_upper_mm'],
                              'evidence_acceptance': 'accepted_local_scope_RARC01',
                              'evidence': str(PATHS['arcs'])} for a in face_arcs],
            'flank_placement': placement,
            'shoulder_seams': [{'shoulder': s['shoulder'], 'straight_flank': s['straight_flank'],
                                'side': s['side'], 'source_snapshot_id': s['snapshot_id'],
                                'source_path': s['shoulder_source_path'],
                                'FIN_U_endpoints': s['own_start_FIN_U_endpoints'],
                                'bound_mm': s['restricted_shoulder_vs_restricted_template']['total_L1_upper_mm'],
                                'scope': 'restricted shoulder expression to shared template, same-t candidate',
                                'evidence_acceptance': 'accepted_local_scope_S03',
                                'evidence': str(PATHS['shoulders'])} for s in face_shoulders],
        })
    ownership = [f for region in dag['regions'] for f in region['responsible_faces']]
    if len(ownership) != len(set(ownership)):
        raise ValueError('overlapping face responsibility')
    snapshot = _read(root, dag['p1_source'])
    inventory = normalize_snapshot(snapshot, tolerances={'linear': .001, 'angular': .0001})
    if inventory['snapshot_id'] != sid or set(ownership) != set(inventory['faces']):
        raise ValueError('face responsibility does not cover the bound P1 inventory')
    for path in DECISIONS:
        _read(root, Path('docs/v3/decisions') / path)
    for evidence in REGION_EVIDENCE.values():
        for path, _ in evidence:
            _read(root, path)
    parameter_doc = data['parameters']
    parameters = [{'id': p['id'], 'classification': p['classification'],
                   'source_pointer': '/parameters/' + str(i),
                   'consumers': p.get('consumers', [])}
                  for i, p in enumerate(parameter_doc['parameters'])]
    requirements = [
        {'id': ident, 'state': 'open', 'evidence': [], 'next': description}
        for ident, description in [
            ('stock', 'prove source containment, envelope and material occupancy'),
            ('rear_slot', 'close source trim and actual stock/material occupancy'),
            ('lower_head', 'close finite cavity trim and material occupancy'),
            ('roots', 'combine local class10 and implicit certificates into full source/candidate trim'),
            ('shoulders', 'combine source FIN, shared template, exit and occupancy'),
            ('upper_head', 'bind class11 finite branches, events and directed material closure'),
            ('flanks', 'establish finite surface correspondence and resolve FIN parameter contract'),
            ('construction', 'establish regional construction and dependency order'),
            ('budget', 'combine compatible full-domain error contributions to the 0.001 mm target'),
            ('transitions', 'resolve T04.c actual modification requirements'),
            ('sphere_trim', 'resolve T04.d sphere trims and adjacency'),
        ]
    ]
    return {
        'schema': 'p3-integrated-regional-ledger/0.1', 'p1_snapshot_id': sid,
        'unit': 'mm', 'frame': 'absolute_part_coordinates',
        'sources': {key: str(value) for key, value in PATHS.items()},
        'reviews': REVIEWS,
        'decisions': ['docs/v3/decisions/' + name for name in DECISIONS],
        'regions': [{'id': r['id'], 'responsible_faces': r['responsible_faces'],
                     'responsibility_only': True,
                     'additional_evidence': [{'path': path, 'scope': scope}
                                             for path, scope in REGION_EVIDENCE.get(r['id'], [])],
                     'previous_reviewed_local_evidence': [e for e in dag['reviewed_local_evidence']
                                                          if e['region_id'] == r['id']]}
                    for r in dag['regions']],
        'root_members': result,
        'parameter_graph': {'source': str(PATHS['parameters']), 'parameters': parameters,
                            'placement_contract': parameter_doc['placement_contract'],
                            'circle_expressions': parameter_doc['circle_expressions'],
                            'templates': parameter_doc['templates'],
                            'qualification': 'C5 offline expression; edit ranges and native propagation remain open'},
        'decision_overlays': build_decision_overlays(root, parameter_doc, result),
        'construction_graph': {'nodes': dag['nodes'], 'order_status': 'candidate_order_unresolved',
                               'qualification': 'old DAG dependencies do not prove physical operation order'},
        'budget_policy': {'target_mm': 0.001, 'target_source': 'docs/v3/decisions/p3-linear-geometry-target.json',
                          'total_bound_mm': None,
                          'status': 'incomplete',
                          'reason': 'local bounds have different domains and missing source/API, placement, trim, and material contributions; do not sum as a total'},
        'p3_requirements': requirements,
        'p3_open': [r['id'] for r in requirements if r['state'] != 'accepted'],
        'later_gates': ['P4 NX2506 native binding and operation composition',
                        'P5 UG11 capability and native propagation', 'P6 whole-part geometric verification'],
        'coverage': {'responsible_faces': len(ownership),
                     'local_root_exit_certificates': len(result),
                     'local_class10_arcs': sum(len(m['class10_arcs']) for m in result),
                     'local_shoulder_seams': sum(len(m['shoulder_seams']) for m in result),
                     'fully_explained_faces': 'not_established'},
        'readiness_assessment': 'not_assessed_by_evidence_index', 'execution_approved': False,
    }
