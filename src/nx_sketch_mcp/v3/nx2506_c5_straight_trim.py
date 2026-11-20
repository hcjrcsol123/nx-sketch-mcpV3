"""Conditional finite straight C5 patch bounds from C14 BREP readback.

The finite-domain contract is explicit: each type-206 face is exactly the
extrusion between its complete generator endpoints, upper Y=-71 and the
positive stock.s6 cone intersection; loop interiors select that patch. A clean
trace, endpoint checks, converted splines and topology do not establish this
contract for tolerant kernel edges or the material side.
"""
from collections import defaultdict
from fractions import Fraction as Q
from itertools import permutations
import math
import re

from .nx2506_carrier_bound import (endpoints, read_generator, rev_curve,
                                    supports, sweep_candidates, tangent_range)
from .nx2506_tail_trim_bound import _loop_cycle, _sqrt
from .nx2506_trim_bound import _bernstein_matrix_inverse, _controls, _curve, bound_trim_pair


class C5StraightTrimError(ValueError):
    """The stated finite-patch calculation is not supported by the input."""


def _up(x):
    f = float(x)
    if not math.isfinite(f):
        raise C5StraightTrimError('nonfinite bound')
    return math.nextafter(f, math.inf) if Q(f) < x else f


def _out(x):
    return {'exact': [x.numerator, x.denominator], 'upper_mm': _up(x)}


def _walk(n):
    yield n
    for child in n.get('children', []):
        yield from _walk(child['child'])


def _edges(detail):
    result = {}
    for n in _walk(detail['topology']):
        if n.get('type') == 8:
            t = n['tag']
            if t in result:
                raise C5StraightTrimError('duplicate face edge')
            result[t] = n
    return result


def _l1(a, b):
    return sum((abs(x-y) for x, y in zip(a, b)), Q())


def _generator(reference, actual):
    # Vertical extrusion is unchanged when its generator is shifted to the
    # Y=-71 plane independently at each parameter; retain x,z and weights.
    native = read_generator(actual)
    for row in native['poles']:
        row[1] = -71*row[3]
    a = endpoints(native)
    choices = []
    for reverse in (False, True):
        ref = rev_curve(reference, reverse)
        ep = endpoints(ref)
        gap = max(_l1(x, y) for x, y in zip(a, ep))
        choices.append((gap, ref, reverse))
    gap, ref, reverse = min(choices, key=lambda x:x[0])
    if gap > Q('0.00025'):
        raise C5StraightTrimError('generator endpoint identity not supported')
    result = bound_trim_pair(native, ref)
    return native, ref, Q(*result['hausdorff_l1_upper_mm_exact']), reverse


def _bounds(native, ref, cone, reference_cone):
    if cone['type'] != 202 or cone['axis'] != [0,1,0] or cone['point_at_apex'][0] != 0 or cone['point_at_apex'][2] != 0:
        raise C5StraightTrimError('cone must be positive ABS Y nappe')
    apex = Q(cone['point_at_apex'][1])
    slo, shi = tangent_range(Q(cone['half_apex_angle']))
    if slo <= 0:
        raise C5StraightTrimError('native cone slope is not positive')
    _, _, p, axis, slope, _ = reference_cone
    if p[0] != 0 or p[2] != 0 or axis != (0,1,0) or slope <= 0:
        raise C5StraightTrimError('unsupported P3 cone')
    na, rf = _curve(native), _curve(ref)
    if any(row[3] != 1 for c in (na,rf) for row in c['poles']):
        raise C5StraightTrimError('non-unit generator weight unsupported')
    # The spline curve is in the convex hull of all poles. The L1 radius
    # is a conservative bound for Euclidean radius, including restrictions.
    radius = max(abs(row[0])+abs(row[2]) for c in (na,rf) for row in c['poles'])
    # Demonstrate each generator remains strictly off the cone axis.
    for c in (na,rf):
        if not any(all(row[d] > 0 for row in c['poles']) or all(row[d] < 0 for row in c['poles']) for d in (0,2)):
            raise C5StraightTrimError('generator could meet cone axis')
    # The cone intersection must stay below the common upper plane, including
    # the full generator hull, for a nonempty chart.
    if apex + radius/slo >= -71 or p[1] + radius/slope >= -71:
        raise C5StraightTrimError('lower graph could cross upper plane')
    slope_inverse_difference = max(abs(1/slo-1/slope), abs(1/shi-1/slope))
    return apex, slo, shi, p[1], slope, radius, slope_inverse_difference


def _vertex_gap(detail, native, apex, slo, shi):
    # This is supporting endpoint evidence, not a tolerant edge guarantee.
    vertices = {}
    for n in _walk(detail['topology']):
        if n.get('type') == 9:
            ident = n['local_identifier']
            point = tuple(Q(x) for x in n['geometry']['point'])
            if len(point) != 3 or (ident in vertices and vertices[ident] != point):
                raise C5StraightTrimError('vertex identity inconsistent')
            vertices[ident] = point
    if len(vertices) != 4:
        raise C5StraightTrimError('face loop must have four vertices')
    targets = []
    for x, _, z in endpoints(native):
        rlo, rhi = _sqrt(x*x+z*z)
        lower = (apex+rlo/shi, apex+rhi/slo)
        targets.extend([((x,x),(Q(-71),Q(-71)),(z,z)), ((x,x),lower,(z,z))])
    def err(point, target):
        return sum((max(abs(x-a),abs(x-b)) for x,(a,b) in zip(point,target)),Q())
    points = list(vertices.values())
    gap = min(max(err(points[i], targets[p[i]]) for i in range(4)) for p in permutations(range(4)))
    if gap > Q('0.001'):
        raise C5StraightTrimError('reported vertices differ from expected four chart corners')
    return gap


def _upper_curve_gap(edge, native):
    g = edge['geometry']
    if g.get('type') != 102:
        raise C5StraightTrimError('upper edge must report a spline')
    curve = read_generator(g)
    bounds = []
    for reverse in (False, True):
        pair = bound_trim_pair(native, rev_curve(curve, reverse))
        bounds.append(Q(*pair['hausdorff_l1_upper_mm_exact']))
    error = min(bounds)
    if error > Q('0.001'):
        raise C5StraightTrimError('upper edge representation differs from generator')
    return error


def _side_line_gap(edge, native, apex, slo, shi):
    g = edge['geometry']
    if g.get('type') != 101:
        raise C5StraightTrimError('side edge must report a line')
    points = [tuple(Q(x) for x in g[k]) for k in ('start', 'end')]
    if any(len(p) != 3 for p in points):
        raise C5StraightTrimError('side line endpoints malformed')
    candidates = []
    for index, (x, _, z) in enumerate(endpoints(native)):
        lo, hi = _sqrt(x*x+z*z)
        targets = [((x,x),(Q(-71),Q(-71)),(z,z)),
                   ((x,x),(apex+lo/shi,apex+hi/slo),(z,z))]
        def error(p, target):
            return sum((max(abs(v-a),abs(v-b)) for v,(a,b) in zip(p,target)),Q())
        candidate = min(max(error(points[0], targets[i]), error(points[1],targets[1-i])) for i in (0,1))
        candidates.append((candidate,index))
    best, index = min(candidates)
    if best > Q('0.001'):
        raise C5StraightTrimError('side line endpoints do not match chart corners')
    return best, index


def assess_c5_straight_trims(capture, support, plan):
    """Bound all 44 straight faces subject to the finite-domain contract.

    Input readbacks are in millimetres and the same ABS coordinate frame. The
    result proves a continuous two-sided Hausdorff upper bound for the two
    defined graph patches, not that tolerant BREP faces satisfy the contract.
    """
    try:
        if (capture.get('schema') != 'p4-native-tail-brep/1' or capture.get('status') != 'PROBES_RETURNED'
            or capture.get('scope') != 'all' or capture.get('stage') != 'complete'
            or capture.get('disk_copy_unchanged') is not True or capture.get('face_count') != 218
            or capture.get('returned_face_count') != 218 or capture.get('unvisited_roles')):
            raise C5StraightTrimError('expected complete unchanged all-face BREP capture')
        if support.get('schema') != 'p4-complete-untrimmed-carrier-bounds/1' or support.get('face_count') != 218:
            raise C5StraightTrimError('expected complete support assignments')
        if plan.get('schema') != 'p3-final-mathematical-plan/1' or plan.get('unit') != 'mm':
            raise C5StraightTrimError('expected P3 millimetre plan')
        assignments = {row['face_tag_session_only']: row for row in support['faces']}
        if len(assignments) != 218 or any(row['status'] != 'carrier_bound' for row in assignments.values()):
            raise C5StraightTrimError('support assignments incomplete')
        selection = {int(row['inventory']['tag_session_only']): row['inventory'] for row in capture['selection']}
        details = {row['detail']['face_tag']: row['detail'] for row in capture['results']}
        if len(selection) != 218 or len(details) != 218 or set(selection) != set(details) or set(details) != set(assignments):
            raise C5StraightTrimError('face identities do not agree')
        if any(d.get('outcome') != 'CLEAN_TRACE' or not d.get('edge_coverage_complete') for d in details.values()):
            raise C5StraightTrimError('face trace or edge coverage incomplete')
        adjacency = defaultdict(list)
        for tag, inv in selection.items():
            for e in inv['face_edge_tags_session_only']:
                adjacency[int(e)].append(tag)
        cone_ids = [t for t,a in assignments.items() if a['p3_support_id'] == 'stock.s6']
        if len(cone_ids) != 1:
            raise C5StraightTrimError('expected one s6 cone face')
        cone = details[cone_ids[0]]['topology']['geometry']
        p3_cones = [s for s in supports(plan) if s[0] == 'stock.s6']
        if len(p3_cones) != 1:
            raise C5StraightTrimError('expected one P3 s6 cone')
        refs = {s[0]:s[1] for s in sweep_candidates(plan)[206]}
        if len(refs) != 44:
            raise C5StraightTrimError('expected 44 distinct P3 generators')
        result, seen = [], set()
        for tag, d in details.items():
            g = d['topology']['geometry']
            if g['type'] != 206:
                continue
            entry = assignments[tag]
            ident = entry['p3_support_id']
            if g['generator'].get('rational') and ident.endswith('.straight_root'):
                continue
            m = re.fullmatch(r'(member_\d{2})\.(F0002|F0024)\.linear', ident)
            if not m or ident not in refs or ident in seen or g['direction'] not in ([0,1,0],[0,-1,0]):
                raise C5StraightTrimError('unexpected or duplicate straight generator')
            seen.add(ident)
            edges = _edges(d)
            cycle = _loop_cycle(d, selection[tag])
            if len(edges) != 4 or cycle['edge_count'] != 4:
                raise C5StraightTrimError('straight face loop must have four edges')
            expected = {'stock.s6':11, 'stock.s7':10,
                        m[1]+'.straight_root':10, m[1]+'.'+m[2]+'.roll':10}
            neighbor_edges = {}
            for edge_id, edge in edges.items():
                neighbors = adjacency[edge_id]
                if len(neighbors) != 2 or tag not in neighbors:
                    raise C5StraightTrimError('edge is not shared by exactly two faces')
                other = next(x for x in neighbors if x != tag)
                name = assignments[other]['p3_support_id']
                if name not in expected or name in neighbor_edges or edge['geometry_class'] != expected[name]:
                    raise C5StraightTrimError('unexpected straight face edge adjacency')
                neighbor_edges[name] = edge
            if set(neighbor_edges) != set(expected):
                raise C5StraightTrimError('missing expected edge family')
            native, ref, error, reverse = _generator(refs[ident], g['generator'])
            apex, slo, shi, p3_apex, p3_slope, radius, inverse_diff = _bounds(native, ref, cone, p3_cones[0])
            lower = abs(apex-p3_apex) + error/slo + radius*inverse_diff
            total = error+lower
            vertex_error = _vertex_gap(d, native, apex, slo, shi)
            upper_edge_error = _upper_curve_gap(neighbor_edges[m[1]+'.'+m[2]+'.roll'], native)
            side_errors = [_side_line_gap(neighbor_edges[name], native, apex, slo, shi)
                           for name in ('stock.s7', m[1]+'.straight_root')]
            if side_errors[0][1] == side_errors[1][1]:
                raise C5StraightTrimError('side lines do not terminate at opposite generator endpoints')
            result.append({'face_tag_session_only':tag, 'p3_support_id':ident,
                           'native_generator_reversed_relative_to_p3':reverse,
                           'generator_l1_upper_mm':_out(error),
                           'lower_height_upper_mm':_out(lower),
                           'conditional_patch_l1_upper_mm':_out(total),
                           'corner_vertex_l1_upper_mm':_out(vertex_error),
                           'upper_edge_vs_generator_l1_upper_mm':_out(upper_edge_error),
                           'side_line_endpoints_l1_upper_mm':_out(max(item[0] for item in side_errors)),
                           'edges':{name:edge['tag'] for name,edge in neighbor_edges.items()},
                           'loop':cycle})
        if len(result) != 44 or seen != set(refs):
            raise C5StraightTrimError('straight face or P3 generator coverage incomplete')
        return {'schema':'p4-c5-straight-conditional-finite-patches/1',
                'status':'conditional_patch_bounds_proved', 'face_count':len(result), 'faces':result,
                'max_conditional_patch_l1_upper_mm':_out(max(Q(*r['conditional_patch_l1_upper_mm']['exact']) for r in result)),
                'max_corner_vertex_l1_upper_mm':_out(max(Q(*r['corner_vertex_l1_upper_mm']['exact']) for r in result)),
                'max_upper_edge_vs_generator_l1_upper_mm':_out(max(Q(*r['upper_edge_vs_generator_l1_upper_mm']['exact']) for r in result)),
                'max_side_line_endpoints_l1_upper_mm':_out(max(Q(*r['side_line_endpoints_l1_upper_mm']['exact']) for r in result)),
                'method':'exact rational Bernstein generator bound; rational cone tangent enclosure; cone-radius Lipschitz bound; affine interpolation of corresponding lower/upper heights',
                'scope':'44 finite graph patches under the stated contract against P3 binary64 preview, in common ABS millimetres',
                'contract':['reported generator and analytic cone exactly describe the actual carriers in a common frame',
                            'every actual class-11 edge is exactly the complete positive cone/generator intersection, with no tolerant gap or unreported endpoint displacement',
                            'class-10 sides occur at the complete generator endpoints, and the upper edge is exactly at Y=-71',
                            'the directed loop and material side retain the entire patch between those four boundaries'],
                'limitations':['readback topology and corner proximity support but do not prove the finite-domain contract',
                               'mapped intersection splines and their requested 0.001 mm tolerance do not prove an edge error bound',
                               'no source/P3 error, whole-body coverage or normal-angle bound is included'],
                'execution_approved':False}
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        if isinstance(exc,C5StraightTrimError):
            raise
        raise C5StraightTrimError('incomplete or unsupported C5 input') from exc


def _linear_chart(generator, tangent):
    """Validate the complete monotone XZ generator as a graph in projected t."""
    c = _curve(generator)
    a,b = c['a'],c['b']
    cuts = sorted({Q(0),Q(1),*((k-a)/(b-a) for k in c['knots'] if min(a,b)<k<max(a,b))})
    inverse = _bernstein_matrix_inverse(c['degree'])
    spans = [_controls(c,l,r,inverse) for l,r in zip(cuts,cuts[1:])]
    def project(point):
        return sum(Q(point[k])*tangent[k] for k in (0,2))
    t0,t1 = project(spans[0][0]),project(spans[-1][-1])
    sign = 1 if t1>t0 else -1
    speed = Q(0)
    radius = Q(0)
    for poles in spans:
        if any(p[3]!=1 for p in poles):
            raise C5StraightTrimError('straight carrier must be polynomial')
        radius = max(radius,max(abs(p[0])+abs(p[2]) for p in poles))
        for p,q in zip(poles,poles[1:]):
            delta = sign*(project(q)-project(p))
            if delta<=0:
                raise C5StraightTrimError('straight carrier projection is not strictly monotone')
            speed = max(speed,(abs(p[0]-q[0])+abs(p[2]-q[2]))/delta)
    return project, *sorted((t0,t1)), speed, radius


def _lower_chord_height(facet, apex, slopes):
    points = [tuple(map(Q,p)) for p in facet['points_mm']]
    intervals = facet['original_edge_parameters']
    tau, endpoint = Q(facet['chord_tolerance_mm']),Q(facet['max_vertex_deviation_mm'])
    first,last = facet['original_edge_parameter_limits']
    sense = 1 if last>first else -1
    if (len(intervals)!=len(points) or (intervals[0],intervals[-1])!=(first,last)
            or any(sense*(b-a)<=0 for a,b in zip(intervals,intervals[1:]))
            or Q(facet['max_midpoint_deviation_mm'])>tau):
        raise C5StraightTrimError('native facet chain does not bind all of the original lower edge')
    slo,shi = slopes
    slope = (slo+shi)/2
    max_error, rmax = Q(0),Q(0)
    for a,b in zip(points,points[1:]):
        if sum((x-y)**2 for x,y in zip(a,b))<=(2*endpoint)**2:
            raise C5StraightTrimError('chord endpoint adjustment exceeds segment length')
        squared_r = [p[0]*q[0]+p[2]*q[2] for p,q in ((a,a),(a,b),(b,b))]
        ra,rb = (slope*(p[1]-apex) for p in (a,b))
        if min(squared_r)<=100 or min(ra,rb)<=10:
            raise C5StraightTrimError('lower trim leaves positive cone graph')
        residual = max(abs(u-v) for u,v in zip(squared_r,(ra*ra,ra*rb,rb*rb)))
        max_error = max(max_error,residual/(20*slope))
        rmax = max(rmax,abs(a[0])+abs(a[2]),abs(b[0])+abs(b[2]))
    parameter_shift = rmax*max(abs(1/slope-1/slo),abs(1/slope-1/shi))
    # Bernstein residual covers the whole chord. Original curve tolerance
    # plus ordered endpoint adjustment bounds the Y/radius graph functional.
    return max_error+parameter_shift+(tau+endpoint)*(1+1/slo)


def _canonical_straight_transfer(plan, template, frame, member, p3_cone, exact_stock, reach):
    from decimal import Decimal

    from .flank_parameters import _pi
    from .root_exit_certificate import I, _trig

    phase, = [r for r in plan['parameters']['c5'] if r['id']=='phase_rad']
    theta = I.of(Q(*phase['value_exact']))+member*_pi()/11
    sine,cosine = _trig(theta-_pi()) if theta.hi>4 else _trig(theta)
    if theta.hi>4:
        sine,cosine = -sine,-cosine
    generator_shift = Q(0)
    for pole in template['poles']:
        t0,r0 = pole['t_mm'],pole['r_mm']
        t,r = (I(Decimal(p['lower']),Decimal(p['upper'])) for p in (t0,r0))
        ideal = (t*cosine+r*sine,-t*sine+r*cosine)
        nominal = [Q(t0['value'])*Q(frame['e_t'][k])+Q(r0['value'])*Q(frame['e_r'][k]) for k in (0,2)]
        generator_shift = max(generator_shift,sum(
            max(abs(Q(val.lo)-q),abs(Q(val.hi)-q)) for val,q in zip(ideal,nominal)))
    p = exact_stock
    slope = (p['R6']-p['R5'])/(p['Y6']-p['Y5'])
    apex = p['Y5']-p['R5']/slope
    old_apex, old_slope = p3_cone[2][1],p3_cone[4]
    apex_shift = max(abs(Q(val)-old_apex) for val in (apex.lo,apex.hi))
    inverse = I.of(1)/slope
    inverse_shift = max(abs(Q(val)-1/old_slope) for val in (inverse.lo,inverse.hi))
    # The common coordinate origin is the accepted stock axis. The tiny
    # reference-source axis offset is already in P3 source correspondence.
    return generator_shift*(1+Q(inverse.hi))+apex_shift+reach*inverse_shift


def _original_strip_bound(facet, project, tlo, thi, speed, reach, apex, slope, side_uncertainty):
    graph_speed = speed/slope[0]
    t_pad = 2*side_uncertainty
    lower_pad = _lower_chord_height(facet,apex,slope)
    height_pad = max(lower_pad,side_uncertainty+graph_speed*t_pad)
    inside,outside = facet['material_anchors']
    if [r['containment_status'] for r in (inside,outside)]!=[1,2]:
        raise C5StraightTrimError('NX trim-side witnesses disagree')
    x,y,z = map(Q,inside['carrier_point_mm'])
    if (not tlo+t_pad<project((x,y,z))<thi-t_pad
            or not apex+reach/slope[0]+height_pad<y<-71-height_pad
            or outside['carrier_point_mm'][1]<=-71+height_pad):
        raise C5StraightTrimError('material anchors outside the corresponding unambiguous core/exterior')
    # The inner strip excludes all original boundaries and connects to
    # the inside anchor; the bounded outer strip contains every boundary.
    # Clamping in t and Y bounds both directions on the common carrier.
    return height_pad+t_pad*(graph_speed+speed)


def verify_c5_straight_patches(capture, supports_index, plan, conditional, facets, limit=Q('0.000141')):
    """Verify each original C14 straight finite C5 face against the canonical patch."""
    from .nx2506_stock_bands import _exact_stock_parameters

    if (facets.get('schema')!='p4-native-c5-straight-facets/1'
            or facets.get('status')!='complete' or facets.get('disk_copy_unchanged') is not True):
        raise C5StraightTrimError('complete original straight-edge and anchor capture required')
    finite = {r['p3_support_id']:r for r in conditional['faces']}
    if len(finite)!=44 or set(finite)!=set(facets['faces']):
        raise C5StraightTrimError('straight finite face coverage differs')
    originals = {r['detail']['face_tag']:r['detail'] for r in capture['results']}
    cone_id, = [r['face_tag_session_only'] for r in supports_index['faces'] if r['p3_support_id']=='stock.s6']
    cone = originals[cone_id]['topology']['geometry']
    slope = tangent_range(Q(cone['half_apex_angle']))
    apex = Q(cone['point_at_apex'][1])
    p3_cone, = [r for r in supports(plan) if r[0]=='stock.s6']
    templates = plan['construction']['profiles']['section6']['templates']
    frames = {r['id']:r['frame'] for r in plan['construction']['nodes'] if r['id'].endswith('_straight_tool')}
    exact_stock = _exact_stock_parameters(plan)
    role_results = []
    for name, row in sorted(finite.items()):
        member,side,_ = name.split('.')
        frame = frames[member+'_straight_tool']
        detail = originals[row['face_tag_session_only']]
        facet = facets['faces'][name]
        top_edge = _edges(detail)[row['edges'][name.removesuffix('.linear')+'.roll']]
        old_points = sorted(r['child']['geometry']['point'] for r in top_edge['children'])
        new_points = facet['upper_endpoints_mm']
        if any(_l1(tuple(map(Q,a)),tuple(map(Q,b)))>Q('0.00000001')
               for a,b in zip(old_points,new_points,strict=True)):
            raise C5StraightTrimError('physical original upper edge locator changed')
        generator = read_generator(detail['topology']['geometry']['generator'])
        project,tlo,thi,speed,reach = _linear_chart(generator,tuple(map(Q,frame['e_t'])))
        def bound(key):
            return Q(*row[key]['exact'])
        side_uncertainty = max(bound('corner_vertex_l1_upper_mm'),bound('side_line_endpoints_l1_upper_mm'),
                               bound('upper_edge_vs_generator_l1_upper_mm'))
        trim = _original_strip_bound(facet,project,tlo,thi,speed,reach,apex,slope,side_uncertainty)
        transfer = _canonical_straight_transfer(plan,templates[side],frame,
                                               int(member.rsplit('_',1)[1]),p3_cone,exact_stock,reach+1)
        total = trim+bound('conditional_patch_l1_upper_mm')+transfer
        role_results.append({'p3_support_id':name, 'facet_count':facet['facet_count'],
                             'native_trim_upper_mm':_up(trim), 'preview_transfer_upper_mm':_up(transfer),
                             'continuous_bidirectional_patch_upper_mm':_up(total),
                             'status':'within_limit' if total<=limit else 'bound_exceeds_limit'})
    maximum = max(r['continuous_bidirectional_patch_upper_mm'] for r in role_results)
    return {'schema':'p4-native-c5-straight-finite-patches/1','face_count':len(role_results),
            'status':'within_limit' if all(r['status']=='within_limit' for r in role_results) else 'bound_exceeds_limit',
            'continuous_bidirectional_patch_upper_mm':maximum,
            'scope':'44 original straight BREP faces, on their finite NX trim charts under the documented facet-edge contract.',
            'execution_approved':False,'faces':role_results}
