"""Conditional analytic intersection graph bounds for a C14 tail BREP read.

The UF read maps class-11 intersections to splines without a proven error.
Consequently no claim is made about exact BREP edges, finite trims or faces.
The bounds compare intersections of the reported analytic parent carriers
against the accepted P3 ideal tail chart, in the common ABS frame hypothesis.
"""
from fractions import Fraction as Q
from math import factorial, isfinite, isqrt, nextafter, inf

from .nx2506_slot_interval import assess_tail_width_interval


class TailTrimBoundError(ValueError):
    """Reported data cannot support this conditional carrier comparison."""


def _q(x):
    if type(x) not in (int, float):
        raise TailTrimBoundError('expected binary64')
    try:
        f = float(x)
    except OverflowError as exc:
        raise TailTrimBoundError('nonfinite number') from exc
    if not isfinite(f) or (type(x) is int and int(f) != x):
        raise TailTrimBoundError('nonfinite or inexact binary64')
    return Q(f)


def _sqrt(q):
    if q < 0:
        raise TailTrimBoundError('negative square root')
    scale = 10**30
    n = isqrt(q.numerator*scale*scale//q.denominator)
    return Q(n, scale), Q(n+1, scale)


def _tan(x):
    """Rational Taylor enclosures for 0 < x < 1.2 radians."""
    if not 0 < x < Q('1.2'):
        raise TailTrimBoundError('unsupported cone angle')
    def series(offset):
        # Alternating terms decrease on this interval; next term bounds error.
        s = sum(((-1)**j*x**(2*j+offset)/factorial(2*j+offset)
                 for j in range(15)), Q())
        rem = x**(30+offset)/factorial(30+offset)
        return s-rem, s+rem
    sl, sh = series(1)
    cl, ch = series(0)
    if cl <= 0:
        raise TailTrimBoundError('cosine sign not proved')
    return sl/ch, sh/cl


def _up(q):
    f = float(q)
    if not isfinite(f):
        raise TailTrimBoundError('bound overflow')
    return nextafter(f, inf) if Q(f) < q else f


def _fmt(q):
    return {'exact': [q.numerator, q.denominator], 'upper_mm': _up(q)}


def _axis(g, kind, axis, point_key):
    if g.get('type') != kind or list(map(_q, g.get('axis', []))) != list(map(Q, axis)):
        raise TailTrimBoundError('unexpected analytic carrier or axis')
    point = list(map(_q, g.get(point_key, [])))
    if len(point) != 3:
        raise TailTrimBoundError('missing carrier axis point')
    return point


def _walk(node):
    yield node
    for child in node.get('children', []):
        yield from _walk(child['child'])


def _edge_nodes(d):
    found = {}
    for n in _walk(d['topology']):
        if n.get('type') == 8:
            tag = n.get('tag')
            if tag in found:
                raise TailTrimBoundError('duplicate edge in one face topology')
            found[tag] = n
    return found


def _vertices(edge):
    nodes = [n for n in _walk(edge) if n.get('type') == 9]
    if len(nodes) != 2:
        raise TailTrimBoundError('edge requires exactly two vertices')
    points = [tuple(map(_q, n['geometry']['point'])) for n in nodes]
    if any(len(p) != 3 for p in points):
        raise TailTrimBoundError('invalid vertex')
    return points


def _loop_cycle(detail, inventory):
    """Check combinatorial closure only; do not assert oriented winding."""
    loops = inventory.get('loops')
    if not isinstance(loops, list) or len(loops) != 1:
        raise TailTrimBoundError('expected one tool-face loop')
    edges = _edge_nodes(detail)
    recorded = [int(x) for x in loops[0]['edge_tags_session_only']]
    if len(set(recorded)) != len(recorded) or set(recorded) != set(edges):
        raise TailTrimBoundError('loop inventory differs from topology')
    adj = {}
    for edge in edges.values():
        verts = [n.get('local_identifier') for n in _walk(edge) if n.get('type') == 9]
        if len(verts) != 2 or verts[0] == verts[1] or any(type(v) is not int for v in verts):
            raise TailTrimBoundError('loop has invalid vertices')
        adj.setdefault(verts[0], []).append(verts[1])
        adj.setdefault(verts[1], []).append(verts[0])
    if any(len(v) != 2 for v in adj.values()):
        raise TailTrimBoundError('loop vertex degree is not two')
    seen, todo = set(), [next(iter(adj))]
    while todo:
        v = todo.pop()
        if v not in seen:
            seen.add(v)
            todo.extend(adj[v])
    if len(seen) != len(adj):
        raise TailTrimBoundError('loop is disconnected')
    return {'edge_count': len(edges), 'vertex_count': len(adj),
            'status': 'undirected_single_cycle',
            'limitation': 'directed winding, edge-to-FIN coincidence and material side not proved'}


def _shared_class11(d1, d2):
    a, b = _edge_nodes(d1), _edge_nodes(d2)
    shared = set(a) & set(b)
    matches = [a[t] for t in shared if a[t].get('geometry_class') == 11
               and b[t].get('geometry_class') == 11]
    if len(matches) != 1:
        raise TailTrimBoundError('expected one shared class-11 edge')
    edge = matches[0]
    if edge.get('geometry', {}).get('type') != 102:
        raise TailTrimBoundError('expected mapped intersection representation')
    _vertices(edge)
    return edge


def _shared_line(d1, d2):
    a, b = _edge_nodes(d1), _edge_nodes(d2)
    shared = set(a) & set(b)
    matches = [a[t] for t in shared if a[t].get('geometry_class') == 10
               and b[t].get('geometry_class') == 10
               and a[t].get('geometry', {}).get('type') == 101]
    if len(matches) != 1:
        raise TailTrimBoundError('expected one shared analytic line')
    return matches[0]


def _point_error(point, target):
    return sum((max(abs(value-lo), abs(value-hi))
                for value, (lo, hi) in zip(point, target)), Q())


def _endpoint_error(points, targets):
    if len(points) != 2 or len(targets) != 2 or any(len(p) != 3 for p in points):
        raise TailTrimBoundError('expected two three-dimensional endpoints')
    return min(max(_point_error(points[0], targets[i]),
                   _point_error(points[1], targets[1-i])) for i in (0, 1))


def _const(q):
    return (q, q)


def _ideal_targets():
    """Outward-rational endpoint intervals for the fixed P3 tail chart."""
    s3lo, s3hi = _sqrt(Q(3))
    y3 = (Q('-151.1')+Q('1.1')/s3hi, Q('-151.1')+Q('1.1')/s3lo)
    z0 = _sqrt(Q('6.9')**2-Q('2.5')**2)
    z7 = _sqrt(Q('7.9')**2-Q('2.5')**2)
    z9 = _sqrt(Q(81)-Q('2.5')**2)
    ztool_sqrt = _sqrt(Q('37.5')**2-Q(4)**2)
    ztool = (Q(42)-ztool_sqrt[1], Q(42)-ztool_sqrt[0])
    # y=-162.6+sqrt(37.5^2-(42-z9)^2); monotone in z9.
    yexit = (_sqrt(Q('37.5')**2-(Q(42)-z9[0])**2)[0]+Q('-162.6'),
             _sqrt(Q('37.5')**2-(Q(42)-z9[1])**2)[1]+Q('-162.6'))
    return {'y3': y3, 'z0': z0, 'z7': z7, 'z9': z9,
            'ztool': ztool, 'yexit': yexit}


def _line_bound(d1, d2, targets, label):
    edge = _shared_line(d1, d2)
    geom = edge['geometry']
    points = [tuple(map(_q, geom[key])) for key in ('start', 'end')]
    bound = _endpoint_error(points, targets)
    if bound > Q('0.01'):
        raise TailTrimBoundError('line endpoints do not identify expected P3 feature')
    return {'kind': label, 'edge_tag_session_only': edge['tag'],
            'position_l1_upper_mm': _fmt(bound),
            'scope': 'reported finite type-101 line segment to ideal P3 line segment'}


def _sincos(t):
    if not -10 < t < 10:
        raise TailTrimBoundError('unsupported arc angle')
    def series(offset):
        value = sum(((-1)**j*t**(2*j+offset)/factorial(2*j+offset)
                     for j in range(30)), Q())
        error = abs(t)**(60+offset)/factorial(60+offset)
        return value-error, value+error
    return series(1), series(0)


def _iscale(a, c):
    v = [a[0]*c, a[1]*c]
    return min(v), max(v)


def _iadd(a, b):
    return a[0]+b[0], a[1]+b[1]


def _arc_bound(cutter, face, x, targets):
    a, b = _edge_nodes(cutter), _edge_nodes(face)
    matches = [a[t] for t in set(a)&set(b)
               if a[t].get('geometry_class') == 10
               and a[t].get('geometry', {}).get('type') == 'circular_evaluator']
    if len(matches) != 1:
        raise TailTrimBoundError('expected one tool-side circular evaluator')
    edge = matches[0]
    g = edge['geometry']
    if g.get('coordinate_system') != 'ABS' or g.get('is_periodic') is not False or g.get('arc_is_periodic') is not False or g['arc_limits'] != g['evaluator_limits']:
        raise TailTrimBoundError('unexpected circle evaluator domain')
    lo, hi = map(_q, g['arc_limits'])
    if x < 0:
        signs = ((1, -1), (-1, -1))
        if not Q('0.3') < lo < hi < Q('0.7'):
            raise TailTrimBoundError('negative side arc branch guard failed')
    else:
        signs = ((-1, 1), (1, 1))
        if not Q('3.4') < lo < hi < Q('3.9'):
            raise TailTrimBoundError('positive side arc branch guard failed')
    # Both intervals lie strictly in the claimed quadrant: pi in (3.14159,
    # 3.14160), pi/4 in (0.78539, 0.78540).
    c_lo, c_hi = _sqrt(Q(1, 2))
    center = tuple(map(_q, g['center']))
    u, v = (tuple(map(_q, g[k])) for k in ('x_axis', 'y_axis'))
    radius = _q(g['radius'])
    if len(center) != 3 or len(u) != 3 or len(v) != 3 or u[0] or v[0] or radius <= 0:
        raise TailTrimBoundError('invalid circular evaluator')
    def vector_error(actual, sign):
        bounds = (sign*c_lo, sign*c_hi)
        return max(abs(actual-min(bounds)), abs(actual-max(bounds)))
    axis_error = sum((vector_error(axis[d+1], signs[i][d])
                      for i, axis in enumerate((u, v)) for d in (0, 1)), Q())
    if axis_error > Q('0.001'):
        raise TailTrimBoundError('circular evaluator basis differs from expected')
    # Compare every point at the same angle to an ideal circle with exact
    # unit diagonal axes. |sin|,|cos|<=1; each axis L1 norm <=2.
    same_parameter = (abs(center[0]-x) + abs(center[1]-Q('-162.6'))
                      + abs(center[2]-Q(42)) + Q(4)*abs(radius-Q('37.5'))
                      + Q('37.5')*axis_error)
    # Enclose the corresponding ideal y values at the two angular limits.
    y_ends = []
    for angle in (lo, hi):
        si, co = _sincos(angle)
        # y = center_y + 37.5*c*(sign_u*cos + sign_v*sin).
        term = _iadd(_iscale(co, signs[0][0]), _iscale(si, signs[1][0]))
        products = [a*b for a in term for b in (c_lo, c_hi)]
        y_ends.append((Q('-162.6')+Q('37.5')*min(products),
                       Q('-162.6')+Q('37.5')*max(products)))
    ytargets = [_const(Q('-158.6')), targets['yexit']]
    endpoint_y = min(max(max(abs(a-b) for a in y_ends[0] for b in ytargets[i]),
                         max(abs(a-b) for a in y_ends[1] for b in ytargets[1-i]))
                     for i in (0, 1))
    if endpoint_y > Q('0.01'):
        raise TailTrimBoundError('arc endpoints do not match expected P3 limits')
    # On -158.61<=y<=-145.45 the ideal lower graph satisfies |dz/dy|<1.
    # Ideal and reference arc images are therefore within 2*endpoint_y in L1.
    bound = same_parameter + 2*endpoint_y
    return {'kind': 'tool_side_arc', 'edge_tag_session_only': edge['tag'],
            'position_l1_upper_mm': _fmt(bound),
            'scope': 'reported circular evaluator segment to ideal P3 circular side arc',
            'condition': 'evaluator center, axes and parameter limits describe the returned finite curve'}


def _end_ring_arc(plane, cone, targets):
    a,b=_edge_nodes(plane),_edge_nodes(cone)
    edge,=[a[key] for key in set(a)&set(b) if a[key]["geometry_class"]==10 and
           a[key]["geometry"]["type"]=="circular_evaluator"]
    g=edge["geometry"]
    start,end=map(_q,g["evaluator_limits"])
    anchor=tuple(map(_q,g["center"]))
    radius=_q(g["radius"])
    if (g["is_periodic"] or not Q(5)<end-start<Q(6) or anchor[0]!=0 or anchor[2]!=0 or
            g["x_axis"]!=[0,0,-1] or g["y_axis"]!=[1,0,0]):
        raise TailTrimBoundError("expected the retained major arc of the end disk")
    error=Q()
    for angle,x in ((start,Q('-2.5')),(end,Q('2.5'))):
        si,co=_sincos(angle)
        x_interval=_iscale(si,Q('6.9'))
        z_interval=_iscale(co,-Q('6.9'))
        error=max(error,max(abs(t-x) for t in x_interval)+
                  max(abs(a-b) for a in z_interval for b in targets['z0']))
    if error>Q('0.000001'):
        raise TailTrimBoundError("end ring arc endpoint pairing failed")
    bound=abs(anchor[1]-Q('-158.6'))+2*abs(radius-Q('6.9'))+4*error
    return {'kind':'tail_end_major_arc','edge_tag_session_only':edge['tag'],
            'position_l1_upper_mm':_fmt(bound),
            'scope':'reported major-circle evaluator to the ideal finite end ring arc'}


def _directed_tail_cycle(detail):
    loop,=detail["topology"]["children"]
    corners=[]
    for member in loop["child"]["children"]:
        link,=member["child"]["children"]
        direction=link["orientation"]
        a,b=[r["child"]["local_identifier"] for r in link["child"]["children"]]
        if direction not in (-1,1) or member["orientation"] not in (0,direction):
            raise TailTrimBoundError("tail fin orientation is inconsistent")
        corners.append((a,b) if direction>0 else (b,a))
    if any(b!=corners[(i+1)%len(corners)][0] for i,(_,b) in enumerate(corners)):
        raise TailTrimBoundError("ordered native tail vertices do not close")
    return True


def _cone_bound(g, x, kind):
    p = _axis(g, 202, [0, 1, 0], 'point_at_apex')
    if p[0] != 0 or p[2] != 0:
        raise TailTrimBoundError('cone apex must be on the Y axis')
    lo, hi = _tan(_q(g['half_apex_angle']))
    if kind == 'end':
        y0, radius, span = Q('-158.6'), Q('6.9'), Q('1.001')
        slo = shi = Q(1)
        y_window = [Q('-158.601'), Q('-157.599')]
    elif kind == 'shoulder':
        y0, radius, span = Q('-151.1'), Q('7.9'), Q('0.637')
        slo, shi = _sqrt(Q(3))
        y_window = [Q('-151.101'), Q('-150.464')]
    else:
        raise TailTrimBoundError('unexpected cone')
    delta = y0-p[1]
    if delta <= 0:
        raise TailTrimBoundError('cone branch not positive')
    anchor_error = max(abs(lo*delta-radius), abs(hi*delta-radius))
    slope_error = max(abs(lo-shi), abs(hi-slo))
    radial_error = anchor_error + span*slope_error
    # Every chart radius is >= 6.899, x=2.5. Hence both positive
    # z=sqrt(r^2-x^2) branches have z>6.4 and r<9.01.
    if abs(x) != Q('2.5') or radial_error >= Q('0.001'):
        raise TailTrimBoundError('radial graph guard failed')
    z_error = Q('18.02')*radial_error/Q('12.8')
    return z_error, y_window


def assess_tail_parent_intersections(data):
    """Derive carrier graph bounds from the captured eight-face BREP object.

    Output deliberately excludes finite BREP edge/face equivalence. In
    particular the class-11 spline conversion tolerance is not a proven bound.
    """
    try:
        if data.get('schema') != 'p4-native-tail-brep/1' or data.get('stage') != 'complete':
            raise TailTrimBoundError('unsupported or incomplete BREP capture')
        if not data.get('disk_copy_unchanged') or data.get('face_count') != 218 or data.get('edge_count') != 562:
            raise TailTrimBoundError('capture context mismatch')
        if assess_tail_width_interval(5, 5)['status'] != 'proved':
            raise TailTrimBoundError('P3 ideal tail certificate failed')
        records = data['results']
        if len(records) != 8 or len({r['role'] for r in records}) != 8:
            raise TailTrimBoundError('expected eight distinct face details')
        details = {r['role']: r['detail'] for r in records}
        if any(d.get('outcome') != 'CLEAN_TRACE' or d.get('edge_coverage_complete') is not True
               or d.get('topology_rc') != 0 or d.get('geometry_overflow') is not False
               for d in details.values()):
            raise TailTrimBoundError('unclean topology read')
        selection = {r['role']: r['inventory'] for r in data['selection']}
        if set(details) != set(selection) or any(int(selection[k]['tag_session_only']) != details[k]['face_tag'] for k in details):
            raise TailTrimBoundError('inventory and detail identity mismatch')
        if any(not selection[k]['loop_edge_set_matches_face_edges'] for k in details):
            raise TailTrimBoundError('incomplete face inventory')
        for name in ('tool_cylinder_axis_x', 'tool_plane_negative_x', 'tool_plane_positive_x'):
            if name not in details:
                raise TailTrimBoundError('missing tool face')
        cycles = {name: _loop_cycle(details[name], selection[name]) for name in
                  ('tool_cylinder_axis_x', 'tool_plane_negative_x', 'tool_plane_positive_x')}
        stock = [d for name, d in details.items() if name.startswith('adjacent_stock_')]
        by_kind = {}
        for d in stock:
            g = d['topology']['geometry']
            if g.get('type') == 201 and _q(g['radius']) == 9:
                by_kind['r9'] = d
            elif g.get('type') == 201 and _q(g['radius']) == Q(7.9):
                by_kind['r7'] = d
            elif g.get('type') == 202:
                apex = _q(g['point_at_apex'][1])
                if Q('-166') < apex < Q('-165'):
                    by_kind['end'] = d
                elif Q('-156') < apex < Q('-155'):
                    by_kind['shoulder'] = d
            elif g.get('type') == 209 and _q(g['point_on_plane'][1]) == Q(-158.6):
                by_kind['end_plane'] = d
        if set(by_kind) != {'r9', 'r7', 'end', 'shoulder', 'end_plane'}:
            raise TailTrimBoundError('could not uniquely identify stock carriers')
        end_plane_role = next(name for name, detail in details.items() if detail is by_kind['end_plane'])
        cycles[end_plane_role] = _loop_cycle(by_kind['end_plane'], selection[end_plane_role])
        g9 = by_kind['r9']['topology']['geometry']
        origin9 = _axis(g9, 201, [0, -1, 0], 'point_on_axis')
        if origin9[0] != 0 or origin9[2] != 0:
            raise TailTrimBoundError('R9 axis is not the ABS Y axis')
        cutter = details['tool_cylinder_axis_x']
        gc = cutter['topology']['geometry']
        pc = _axis(gc, 201, [-1, 0, 0], 'point_on_axis')
        radius = _q(gc['radius'])
        # The lower tool branch and positive R9 branch over |x|<=2.5.
        # z>=8.64 and both square-root denominators exceed 17 mm each.
        if not Q('37') < radius < Q('38') or not Q('-163') < pc[1] < Q('-162') or not Q(41) < pc[2] < Q(43):
            raise TailTrimBoundError('cutter carrier outside branch guard')
        zlo, _ = _sqrt(Q(81)-Q('2.5')**2)
        if zlo < Q('8.64'):
            raise TailTrimBoundError('R9 positive branch guard failed')
        dn = radius**2 - max((pc[2]-zlo)**2, (pc[2]-Q(9))**2)
        di = Q('37.5')**2 - max((Q(42)-zlo)**2, Q(33)**2)
        if min(dn, di) <= Q(17)**2:
            raise TailTrimBoundError('cutter root denominator guard failed')
        dy = abs(pc[1]-Q('-162.6')) + (abs(radius-Q('37.5'))*(radius+Q('37.5'))
              + abs(pc[2]-Q(42))*(abs(pc[2]-zlo)+Q(42)-zlo))/Q(34)
        e9 = _shared_class11(cutter, by_kind['r9'])
        v9 = _vertices(e9)
        if sorted(v[0] for v in v9) != [Q('-2.5'), Q('2.5')]:
            raise TailTrimBoundError('R9 edge endpoint X values inconsistent')
        if any(not Q('-146') < v[1] < Q('-145') or not Q('8.6') < v[2] < Q('8.7') for v in v9):
            raise TailTrimBoundError('R9 edge endpoint branch guard failed')
        graphs = [{'kind': 'lower_cutter_positive_R9', 'edge_tag_session_only': e9['tag'],
                   'chart_parameter': 'x', 'chart_interval_mm': [-2.5, 2.5],
                   'position_l1_upper_mm': _fmt(dy)}]
        targets = _ideal_targets()
        pminus = (_const(Q('-2.5')), targets['yexit'], targets['z9'])
        pplus = (_const(Q('2.5')), targets['yexit'], targets['z9'])
        graphs[0]['reported_vertex_l1_to_ideal_endpoints_upper_mm'] = _fmt(_endpoint_error(v9, [pminus, pplus]))
        lines, arcs = [], []
        arcs.append(_end_ring_arc(by_kind['end_plane'],by_kind['end'],targets))
        def point(x, y, z):
            return (_const(x), y, z)
        y0, y1, y2 = map(lambda v: _const(Q(v)), ('-158.6', '-157.6', '-151.1'))
        lines.append(_line_bound(cutter, by_kind['end_plane'],
                     [point(Q('-2.5'), y0, targets['ztool']), point(Q('2.5'), y0, targets['ztool'])],
                     'tool_end_cross_line'))
        for name, expected_x in [('tool_plane_negative_x', Q('-2.5')), ('tool_plane_positive_x', Q('2.5'))]:
            face = details[name]
            g = face['topology']['geometry']
            if g.get('type') != 209 or list(map(_q,g['normal'])) != [Q(1), Q(0), Q(0)] or _q(g['point_on_plane'][0]) != expected_x:
                raise TailTrimBoundError('side plane does not match P3')
            box = selection[name]['uf_face_data']['bounding_box_mm']
            if _q(box[2]) <= 0:
                raise TailTrimBoundError('positive side branch not selected')
            arcs.append(_arc_bound(cutter, face, expected_x, targets))
            for kind in ('end', 'shoulder'):
                edge = _shared_class11(face, by_kind[kind])
                upper, window = _cone_bound(by_kind[kind]['topology']['geometry'], expected_x, kind)
                if any(v[0] != expected_x or not window[0] <= v[1] <= window[1] or v[2] <= 0 for v in _vertices(edge)):
                    raise TailTrimBoundError('cone edge vertex/branch guard failed')
                ideal_ends = ([point(expected_x, y0, targets['z0']), point(expected_x, y1, targets['z7'])]
                              if kind == 'end' else
                              [point(expected_x, y2, targets['z7']), point(expected_x, targets['y3'], targets['z9'])])
                graphs.append({'kind': kind+'_cone_side', 'edge_tag_session_only': edge['tag'],
                               'chart_parameter': 'y', 'chart_interval_mm': [float(x) for x in window],
                               'chart_interval_mm_exact': [[x.numerator, x.denominator] for x in window],
                               'position_l1_upper_mm': _fmt(upper),
                               'reported_vertex_l1_to_ideal_endpoints_upper_mm': _fmt(_endpoint_error(_vertices(edge), ideal_ends))})
            lines.append(_line_bound(face, by_kind['end_plane'],
                         [point(expected_x, y0, targets['ztool']), point(expected_x, y0, targets['z0'])],
                         name+'_end_line'))
            lines.append(_line_bound(face, by_kind['r7'],
                         [point(expected_x, y1, targets['z7']), point(expected_x, y2, targets['z7'])],
                         name+'_r7_line'))
            lines.append(_line_bound(face, by_kind['r9'],
                         [point(expected_x, targets['y3'], targets['z9']), point(expected_x, targets['yexit'], targets['z9'])],
                         name+'_r9_line'))
        maximum = max(Q(*g['position_l1_upper_mm']['exact']) for g in graphs)
        line_maximum = max(Q(*g['position_l1_upper_mm']['exact']) for g in lines)
        arc_maximum = max(Q(*g['position_l1_upper_mm']['exact']) for g in arcs)
        vertex_bound=max(Q(*g['reported_vertex_l1_to_ideal_endpoints_upper_mm']['exact']) for g in graphs)
        closed={name:_directed_tail_cycle(details[name]) for name in cycles}
        senses={name:details[name]['topology']['geometry_sense'] for name in cycles}
        if senses!={'tool_cylinder_axis_x':-1,'tool_plane_negative_x':1,
                    'tool_plane_positive_x':-1,end_plane_role:-1}:
            raise TailTrimBoundError('native tail tool-facing orientation differs from P3')
        # Include finite-end correspondence in each implicit graph. The cone
        # side graph has L1 speed <= 5 per unit y; the R9 graph has <= 3 per x.
        # Project matching loops to the x/y or plane chart. Away from the
        # boundary strip, winding is invariant under the paired homotopy.
        # Lift the strip by a <=2 Lipschitz chart and include a native carrier
        # shift for the lower tool cylinder (the other chart planes are fixed).
        loop_bound=max(maximum+5*vertex_bound,line_maximum,arc_maximum)
        carrier_shift=abs(pc[1]-Q('-162.6'))+abs(pc[2]-42)+2*abs(radius-Q('37.5'))
        conditional_face_bound=4*loop_bound+carrier_shift
        return {'schema': 'p4-tail-parent-intersection-bound/1', 'status': 'conditional_graphs_proved',
                'graphs': graphs, 'max_position_l1_upper_mm': _fmt(maximum),
                'reported_lines': lines, 'max_reported_line_position_l1_upper_mm': _fmt(line_maximum),
                'reported_arcs': arcs, 'max_reported_arc_position_l1_upper_mm': _fmt(arc_maximum),
                'face_loop_connectivity': cycles,
                'directed_face_loops': closed,'material_senses':senses,
                'conditional_tail_face_upper_mm':_fmt(conditional_face_bound),
                'method': 'exact binary64 rational parent parameters; rational square-root and Taylor-series tangent enclosures; positive-branch Lipschitz bounds',
                'scope': 'Four finite tail faces if the captured original curves and selected actual-parent intersection graphs define their complete trim. Five implicit edges, seven lines and three arcs.',
                'not_proved': ['class-11 BREP edge equality to parent intersections or to mapped spline',
                               'unconditional finite native trim equivalence, complete body and angle',
                               'mapping request 0.001 mm is not a Hausdorff bound',
                               'frame and actual native kernel representation uncertainty'],
                'execution_approved': False}
    except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        if isinstance(exc, TailTrimBoundError):
            raise
        raise TailTrimBoundError('invalid or unsupported tail input') from exc


def verify_tail_facet_patches(facets, carrier_proof, plan):
    """Verify four complete finite tail patches using original facet-edge chains."""
    from .nx2506_stock_bands import _exact_stock_parameters

    if (facets.get('schema')!='p4-native-tail-facets/1' or facets.get('disk_copy_unchanged') is not True
            or carrier_proof.get('status')!='conditional_graphs_proved'
            or not all(carrier_proof['directed_face_loops'].values())):
        raise TailTrimBoundError('ordered original tail facets and BREP loops required')
    roles = ('tool_plane_positive_x','tool_plane_negative_x')
    required = {('r9_exit','tool_cylinder_axis_x'),
                *((kind,role) for role in roles for kind in ('end_cone','shoulder_cone'))}
    anchors = facets['material_anchors']
    if (set(anchors)!={'end_plane','tool_cylinder_axis_x',*roles}
            or not all([r['containment_status'] for r in pair]==[1,2] for pair in anchors.values())):
        raise TailTrimBoundError('original finite tail material-side witnesses differ')
    targets = _ideal_targets()
    sqrt3_lo,sqrt3_hi = _sqrt(Q(3))
    graphs = {
        'end_cone': (Q('-158.6'),Q('6.9'), (Q(1),Q(1)),
                     _const(Q('-158.6')),_const(Q('-157.6')),Q('-158.601'),Q('-157.599')),
        'shoulder_cone': (Q('-151.1'),Q('7.9'), (sqrt3_lo,sqrt3_hi),
                          _const(Q('-151.1')),targets['y3'],Q('-151.101'),Q('-150.464')),
    }
    results=[]
    for row in facets['edges']:
        kind,role = row['kind'],row['face_role']
        required.remove((kind,role))
        points = [tuple(map(Q,p)) for p in row['points_mm']]
        parameter_axis = 0 if kind=='r9_exit' else 1
        chord_lengths = [sum((x-y)**2 for x,y in zip(a,b)) for a,b in zip(points,points[1:])]
        e = Q(row['max_vertex_deviation_mm'])
        tau = Q(row['chord_tolerance_mm'])
        if min(chord_lengths)<=(2*e)**2 or Q(row['max_midpoint_deviation_mm'])>tau:
            raise TailTrimBoundError('original tail facet tolerance or ordered endpoints disagree')
        reversed_order = points[0][parameter_axis]>points[-1][parameter_axis]
        if reversed_order:
            points.reverse()
        coordinates = [p[parameter_axis] for p in points]
        steps = [b-a for a,b in zip(coordinates,coordinates[1:])]
        if min(steps)<=0:
            raise TailTrimBoundError('tail facet chain is not a graph of the chart coordinate')
        samples = []
        if kind=='r9_exit':
            flat = Q('2.50000001')
            if max(map(abs,coordinates))>flat:
                raise TailTrimBoundError('R9 exit coordinate window exceeded')
            z_min,_ = _sqrt(81-flat**2)
            root_min,_ = _sqrt(Q('37.5')**2-(42-z_min)**2)
            if z_min<=Q('8.64') or root_min<=17:
                raise TailTrimBoundError('R9 exit derivative denominators too small')
            for point in points:
                zlo,zhi=_sqrt(81-point[0]**2)
                ylo=_sqrt(Q('37.5')**2-(42-zlo)**2)[0]-Q('162.6')
                yhi=_sqrt(Q('37.5')**2-(42-zhi)**2)[1]-Q('162.6')
                samples.append(_point_error(point, (_const(point[0]),(ylo,yhi),(zlo,zhi))))
            ends = (_const(Q('-2.5')),_const(Q('2.5')))
            # z''=-81/z^3. Y_z=(42-z)/D, |Y_zz|=37.5^2/D^3.
            z_first=flat/z_min
            z_second=Q(81)/z_min**3
            gradient=(42-z_min)/root_min
            curvature=z_second*(1+gradient)+Q('37.5')**2/root_min**3*z_first**2
        else:
            center,r0,slopes,start,end,lo,hi = graphs[kind]
            if coordinates[0]<lo or coordinates[-1]>hi:
                raise TailTrimBoundError('cone facet chain lies outside its analytic branch')
            x = Q('2.5') if role.endswith('positive_x') else Q('-2.5')
            extent = [r0+(t-center)*s for t in (lo,hi) for s in slopes]
            z_min,_ = _sqrt(min(extent)**2-x**2)
            if z_min<=Q('6.4'):
                raise TailTrimBoundError('side cone derivative denominator too small')
            for point in points:
                radii=[r0+(point[1]-center)*m for m in slopes]
                zlo=_sqrt(min(radii)**2-x**2)[0]
                zhi=_sqrt(max(radii)**2-x**2)[1]
                samples.append(_point_error(point, (_const(x),_const(point[1]),(zlo,zhi))))
            ends=(start,end)
            # For z=sqrt(r(Y)^2-x^2) with affine r, |z''|=x²*slope²/z³.
            curvature=x**2*max(slopes)**2/z_min**3
        endpoint_error=max(abs(t-k) for t,span in zip((coordinates[0],coordinates[-1]),ends) for k in span)
        # Linear interpolation error is bounded by max |g''| h²/8;
        # rescaling the finite chart endpoints adds at most 5 times their shift.
        analytic_error=max(samples)+curvature*max(steps)**2/8+5*endpoint_error
        results.append({'kind':kind,'face_role':role,
                        'continuous_pointwise_boundary_upper_mm':_up(analytic_error+tau+e)})
    if required:
        raise TailTrimBoundError('incomplete five-edge tail facet coverage')
    if max(Q(row['chord_tolerance_mm']) for row in facets['edges'])>Q('0.00002'):
        raise TailTrimBoundError('tail facet distance outside the evaluated chart limits')
    p = _exact_stock_parameters(plan)
    nominal = {'Y0':_const(Q('-158.6')),'Y1':_const(Q('-157.6')),'Y2':_const(Q('-151.1')),
               'Y3':targets['y3'],'R0':_const(Q('6.9')),'R1':_const(Q('7.9')),'R3':_const(Q(9))}
    shift=max(abs(Q(endpoint)-target) for name,interval in nominal.items()
              for endpoint in (p[name].lo,p[name].hi) for target in interval)
    # All stable tail construction inputs and joins stay in the stated
    # derivative windows: cone slope graph <=5, z-to-cutter-exit <=2,
    # and axis-point/slot-radius perturbations have amplification <3.
    # Use 32 times the largest input shift for all joined boundary terms.
    slot = {row['id']:Q(row['value']) for row in plan['parameters']['regional']}
    for name,nom in {'width':'5','radius':'37.5','axis_y':'-162.6','axis_z':'42'}.items():
        shift=max(shift,abs(slot['slot.'+name]-Q(nom)))
    if shift>=Q('0.00000001'):
        raise TailTrimBoundError('nominal tail chart differs from the canonical driver certificate')
    transfer=32*shift
    limit=max(*(Q(r['continuous_pointwise_boundary_upper_mm']) for r in results),
              *(Q(*carrier_proof[key]['exact']) for key in ('max_reported_line_position_l1_upper_mm',
                                                            'max_reported_arc_position_l1_upper_mm')))
    # Retain the existing finite chart deformation bound: planar loop
    # winding, lower cutter graph lift <2 and a carrier displacement term.
    total=4*(limit+transfer)+Q(*carrier_proof['conditional_tail_face_upper_mm']['exact'])
    return {'schema':'p4-native-tail-four-finite-patches/1',
            'status':'within_limit' if total<=Q('0.000141') else 'bound_exceeds_limit',
            'face_count':4,'continuous_bidirectional_patch_upper_mm':_up(total),
            'implicit_edge_count':len(results),'canonical_transfer_upper_mm':_up(transfer),
            'edge_bounds':results,
            'scope':'Two cutter side planes, the lower cylinder face and the retained tail closure face.',
            'proof':('Original facet-segment tolerance and analytic interpolation bound the five '
                     'implicit edges pointwise. Original line and circle evaluators cover the '
                     'other trim edges. Ordered loops, native inside/outside anchors and bounded '
                     'lower-cylinder chart lift give both complete finite-face directions.'),
            'execution_approved':False}
