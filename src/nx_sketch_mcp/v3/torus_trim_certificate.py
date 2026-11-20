"""Source-scoped torus loop certificate; no model creation or P6 comparison.

The bounded verifier accepts a single 4/5-FIN loop with three normal circular
edges and one/two implicit-intersection edges. It verifies a closed simple
graph of the *returned FIN representations*, not an exact implicit trim.
"""
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path
import re

from .spline_restrict import restrict_bspline


class TrimCertificateError(ValueError):
    pass


P1_ID = "P1-REFERENCE-7812d302a165453badcd339473b5dba3"
LEDGER = "workspace/v3/p3/P3-SHOULDERS-ANALYSIS-02/native-root-ledger.json"
P1 = "workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json"
QUEUE = "workspace/v3/p3/P3-CARRIERS-01/read-queue.json"
PRIOR = "workspace/v3/p3/P3-SHOULDERS-ANALYSIS-01/remaining-detail-inventory.json"
DEFAULT_LINEAR_MATCH_MM = .001
DEFAULT_UV_JOIN_RAD = 1e-8


def _fail(message):
    raise TrimCertificateError(message)


def _read(path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out: _fail("duplicate JSON key")
            out[key] = value
        return out
    with path.open(encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=unique,
                         parse_constant=lambda _: _fail("non-finite JSON"))


def _path(root, relative):
    if not isinstance(relative, str) or not relative.strip(): _fail("missing source path")
    path = Path(relative.replace("\\", "/"))
    if path.is_absolute() or any(part in (".", "..") for part in path.parts): _fail("invalid source path")
    resolved = (root / path).resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file(): _fail("source outside repository")
    return resolved


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _vector(value, n):
    if not isinstance(value, list) or len(value) != n or any(not _number(x) for x in value):
        _fail("invalid finite vector")
    return value


def _require_mm(snapshot):
    inventory = snapshot.get("inventory") if isinstance(snapshot, dict) else None
    if (not isinstance(inventory, dict) or inventory.get("units") != "Millimeters"
            or inventory.get("coordinate_system") != "absolute_part_coordinates"):
        _fail("source must record millimeters and absolute part coordinates")


def _unit(vector):
    vector = _vector(vector, 3)
    scale = max(abs(x) for x in vector)
    if scale == 0: _fail("zero direction")
    v = [x / scale for x in vector]
    length = math.hypot(*v)
    return [x / length for x in v]


def _dot(a, b): return sum(x*y for x, y in zip(a, b))
def _cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def _frame(geometry):
    if (not isinstance(geometry, dict) or geometry.get("type") != 204
            or not _number(geometry.get("major_radius")) or not _number(geometry.get("minor_radius"))
            or not geometry["major_radius"] > geometry["minor_radius"] > 0):
        _fail("unsupported non-ring or invalid torus")
    center = _vector(geometry.get("center"), 3)
    axis = _unit(geometry.get("axis")); raw_ref = _unit(geometry.get("u0_ref_direction"))
    projection = [raw_ref[i] - _dot(axis, raw_ref)*axis[i] for i in range(3)]
    ref = _unit(projection); tangent = _unit(_cross(axis, ref))
    return center, axis, ref, tangent


def _point(geometry, u, v):
    center, axis, ref, tangent = _frame(geometry)
    radial = [math.cos(u)*ref[i] + math.sin(u)*tangent[i] for i in range(3)]
    return [center[i] + (geometry["major_radius"] + geometry["minor_radius"]*math.cos(v))*radial[i]
            + geometry["minor_radius"]*math.sin(v)*axis[i] for i in range(3)]


def _distance(a, b): return math.dist(a, b)


def _spans(spline, dimensions):
    """Return every nonzero knot span with exact binary64-derived controls."""
    if (not isinstance(spline, dict) or spline.get("type") != 102 or spline.get("rational") is not False
            or type(spline.get("order")) is not int or spline["order"] not in (2, 3, 4)
            or type(spline.get("num_poles")) is not int):
        _fail("unsupported spline representation")
    order, count = spline["order"], spline["num_poles"]
    knots, flat = spline.get("knots"), spline.get("weighted_poles_flat_xyzw")
    if (not isinstance(knots, list) or len(knots) != count + order or any(not _number(x) for x in knots)
            or not isinstance(flat, list) or len(flat) != count*4 or any(not _number(x) for x in flat)
            or any(w != 1 for w in flat[3::4]) or any(a > b for a,b in zip(knots, knots[1:]))):
        _fail("invalid spline basis or weights")
    lo, hi = spline.get("start"), spline.get("end")
    if not _number(lo) or not _number(hi) or lo != knots[order-1] or hi != knots[count] or not lo < hi:
        _fail("spline active interval differs from complete native domain")
    poles = [[float(flat[4*i+j]) for j in range(dimensions)] for i in range(count)]
    unique = sorted({k for k in knots if lo <= k <= hi})
    result = []
    for a,b in zip(unique, unique[1:]):
        if not a < b: continue
        restricted = restrict_bspline(order=order, knots=knots, poles=poles, a=a, b=b, rational=False)
        rows = restricted["dependency_rows_exact"]
        if len(rows) != order: _fail("non-Bezier restriction")
        exact = [[sum((Fraction(*rows[i][j]) * Fraction.from_float(float(poles[j][d]))
                       for j in range(count)), Fraction()) for d in range(dimensions)] for i in range(order)]
        result.append({"interval": [a,b], "controls": exact})
    if not result or result[0]["interval"][0] != lo or result[-1]["interval"][1] != hi:
        _fail("incomplete nonzero span coverage")
    return result


def _edge_direction(edge, match_mm):
    children = edge.get("children")
    if not isinstance(children, list) or len(children) != 2: _fail("edge does not have two vertices")
    vertices = []
    for ref in children:
        vertex = ref.get("child", {})
        ident = vertex.get("local_identifier")
        if vertex.get("type") != 9 or type(ident) is not int or ident <= 0:
            _fail("missing same-tree vertex identity")
        vertices.append((ident, _vector(vertex.get("geometry", {}).get("point"), 3)))
    if vertices[0][0] == vertices[1][0]: _fail("closed or degenerate edge unsupported")
    if edge.get("geometry_class") == 10:
        arc = edge.get("geometry", {})
        limits = arc.get("evaluator_limits")
        if (edge.get("geometry_rc") is not None or edge.get("geometry_sense") is not None
                or arc.get("type") != "circular_evaluator" or arc.get("coordinate_system") != "ABS"
                or not isinstance(limits, list) or len(limits) != 2 or any(not _number(x) for x in limits)
                or not limits[0] < limits[1] or limits[1]-limits[0] >= 2*math.pi
                or arc.get("arc_limits") != limits or arc.get("is_periodic") is not False
                or arc.get("arc_is_periodic") is not False or not _number(arc.get("radius")) or arc["radius"] <= 0):
            _fail("unsupported circular evaluator")
        center, raw_x, raw_y = _vector(arc.get("center"), 3), _vector(arc.get("x_axis"), 3), _vector(arc.get("y_axis"), 3)
        if abs(math.hypot(*raw_x)-1) > 1e-8 or abs(math.hypot(*raw_y)-1) > 1e-8:
            _fail("circular evaluator axes are not unit vectors")
        x, y = _unit(raw_x), _unit(raw_y)
        if abs(_dot(x,y)) > 1e-8: _fail("degenerate circular frame")
        points = [[center[j]+arc["radius"]*(math.cos(t)*x[j]+math.sin(t)*y[j]) for j in range(3)] for t in limits]
        direct = max(_distance(points[i], vertices[i][1]) for i in (0,1))
        reverse = max(_distance(points[i], vertices[1-i][1]) for i in (0,1))
        if (direct <= match_mm) == (reverse <= match_mm): _fail("ambiguous evaluator-to-vertex direction")
        return vertices, {"representation": "native_circular_evaluator", "evaluator_to_edge_vertex": "forward" if direct <= match_mm else "reverse",
                          "endpoint_match_mm": min(direct, reverse)}
    if edge.get("geometry_class") == 11:
        if (type(edge.get("geometry_rc")) is not int or edge["geometry_rc"] != 0
                or type(edge.get("geometry_free_rc")) is not int or edge["geometry_free_rc"] != 0 or edge.get("states") != []
                or type(edge.get("geometry_sense")) is not int or edge["geometry_sense"] not in (-1,1)):
            _fail("intersection conversion failed or has states")
        spans = _spans(edge.get("geometry"), 3)
        points = [[float(x) for x in spans[0]["controls"][0]], [float(x) for x in spans[-1]["controls"][-1]]]
        direct = max(_distance(points[i], vertices[i][1]) for i in (0,1))
        reverse = max(_distance(points[i], vertices[1-i][1]) for i in (0,1))
        if (direct <= match_mm) == (reverse <= match_mm): _fail("ambiguous converted 3D-to-vertex direction")
        if edge["geometry_sense"] != (1 if direct <= match_mm else -1):
            _fail("converted 3D geometry sense conflicts with vertex direction")
        return vertices, {"representation": "implicit_intersection_with_api_converted_3d_spline",
                          "converted_3d_nonzero_span_count": len(spans), "converted_3d_is_stored_source_curve": False,
                          "converted_3d_endpoint_match_mm": min(direct,reverse),
                          "converted_3d_to_edge_vertex": "forward" if direct <= match_mm else "reverse"}
    _fail("unsupported geometry class")


def _topology(snapshot, summary, *, match_mm, uv_join_rad):
    details = snapshot.get("detail")
    if not isinstance(details, list) or len(details) != 1: _fail("one selected source detail required")
    diagnostic = details[0].get("diagnostic", {})
    options = diagnostic.get("options", {})
    request = summary.get("detail_request", {})
    if (type(diagnostic.get("topology_rc")) is not int or diagnostic["topology_rc"] != 0
            or type(diagnostic.get("topology_release_rc")) is not int or diagnostic["topology_release_rc"] != 0
            or type(diagnostic.get("topology_state_count")) is not int or diagnostic["topology_state_count"] != 0
            or diagnostic.get("root_topology_states_omitted") is not True
            or diagnostic.get("topology_states") is not None or diagnostic.get("incomplete_observed") is not False
            or diagnostic.get("edge_coverage_complete") is not True or diagnostic.get("geometry_overflow") is not False
            or diagnostic.get("event_overflow") is not False or diagnostic.get("mapping") != ["BLEND_TO_BSURFACE", "INTERSECTION_TO_SPLINE"]
            or type(options.get("finsp")) is not int or options["finsp"] != 1
            or type(options.get("edge3d")) is not int or options["edge3d"] != 1 or options.get("flatten") is not False
            or options.get("tolerance_unit") != "part_length_unit"
            or options.get("curve_tolerance") != request.get("curve_tolerance")
            or options.get("surface_tolerance") != request.get("surface_tolerance")):
        _fail("source topology, states, mapping or options not supported")
    root = diagnostic.get("topology", {})
    geometry = root.get("geometry", {})
    _frame(geometry)
    if (root.get("type") != 5 or type(root.get("geometry_rc")) is not int or root["geometry_rc"] != 0
            or type(root.get("geometry_free_rc")) is not int or root["geometry_free_rc"] != 0
            or type(root.get("geometry_sense")) is not int or root["geometry_sense"] not in (-1, 1) or root.get("states") != []
            or not isinstance(root.get("children"), list) or len(root["children"]) != 1):
        _fail("unsupported torus face topology")
    loop = root["children"][0].get("child", {})
    fin_refs = loop.get("children")
    if loop.get("type") != 6 or not isinstance(fin_refs, list) or len(fin_refs) not in (4,5):
        _fail("only one four/five-FIN loop supported")
    body = snapshot["inventory"]["selected_body"]
    face_by_tag = {str(x["tag"]): x for x in body["faces"]}
    edge_by_tag = {str(x["tag"]): x for x in body["edges"]}
    source_face_tag = str(details[0]["observed_face"]["tag"])
    fins, vertex_points, used = [], {}, set()
    for position, ref in enumerate(fin_refs):
        fin = ref.get("child", {})
        children = fin.get("children")
        if (fin.get("type") != 7 or type(fin.get("geometry_rc")) is not int or fin["geometry_rc"] != 0
                or type(fin.get("geometry_free_rc")) is not int or fin["geometry_free_rc"] != 0
                or fin.get("states") != [] or type(fin.get("geometry_sense")) is not int or fin["geometry_sense"] not in (-1,1)
                or not isinstance(children,list) or len(children) != 1):
            _fail("invalid FIN or state")
        edge_ref, edge = children[0], children[0].get("child", {})
        direction = edge_ref.get("orientation")
        if (edge.get("type") != 8 or type(direction) is not int or direction not in (-1,1)
                or type(ref.get("orientation")) is not int or ref.get("orientation") != direction
                or type(edge.get("edge_class_rc")) is not int or edge["edge_class_rc"] != 0
                or type(edge.get("edge_class")) is not int or edge["edge_class"] != 1 or edge.get("states") != []
                or edge.get("geometry_class") not in (10,11)):
            _fail("invalid directed source edge")
        tag = str(edge.get("tag"))
        if tag in used or tag not in edge_by_tag: _fail("duplicate or unmapped same-tree edge")
        used.add(tag)
        original = edge_by_tag[tag]
        if source_face_tag not in original["face_tags"] or len(original["face_tags"]) != 2:
            _fail("intersection parent incidence is not unique")
        other_tag = next(t for t in original["face_tags"] if str(t) != source_face_tag)
        other = face_by_tag[str(other_tag)]
        vertices, representation = _edge_direction(edge, match_mm)
        for ident, point in vertices:
            if ident in vertex_points and vertex_points[ident] != point: _fail("same-tree vertex values differ")
            vertex_points[ident] = point
        spans = _spans(fin.get("geometry"), 2)
        if fin["geometry"]["order"] not in (2,3): _fail("unsupported FIN order")
        begin, end = spans[0]["controls"][0], spans[-1]["controls"][-1]
        world = [_point(geometry, float(p[0]), float(p[1])) for p in (begin,end)]
        direct = max(_distance(world[i], vertices[i][1]) for i in (0,1))
        reverse = max(_distance(world[i], vertices[1-i][1]) for i in (0,1))
        if (direct <= match_mm) == (reverse <= match_mm): _fail("ambiguous FIN-to-vertex endpoint mapping")
        sp_starts_at_vertex0 = direct <= match_mm
        traversal_is_forward = (direction == 1) == sp_starts_at_vertex0
        if fin["geometry_sense"] != (1 if traversal_is_forward else -1):
            _fail("FIN geometry sense conflicts with endpoint-mapped traversal")
        oriented = [deepcopy(x["controls"]) for x in spans]
        if not traversal_is_forward: oriented = [list(reversed(x)) for x in reversed(oriented)]
        start, finish = (vertices[0][0], vertices[1][0]) if direction == 1 else (vertices[1][0], vertices[0][0])
        fins.append({"position":position,"edge_tag":tag,"geometry_class":edge["geometry_class"],
                     "edge_orientation":direction,"loop_child_orientation":ref["orientation"],
                     "fin_geometry_sense":fin["geometry_sense"],"edge_geometry_sense":edge.get("geometry_sense"),
                     "source_interval":[fin["geometry"]["start"],fin["geometry"]["end"]],
                     "nonzero_spans":[x["interval"] for x in spans],"traversal_is_forward":traversal_is_forward,
                     "start_vertex":start,"end_vertex":finish,"uv_spans":oriented,
                     "fin_endpoint_match_mm":min(direct,reverse),"edge_representation":representation,
                     "other_parent_same_snapshot":{"local_tag":str(other_tag),"surface_type":other["surface_type"],
                                                    "native_face_data":deepcopy(other["native_face_data"]),"edge_count":len(other["edge_tags"])}})
    if used != {str(x) for x in details[0]["observed_face"]["edge_tags"]}: _fail("loop does not cover selected face edges")
    if any(fins[i]["end_vertex"] != fins[(i+1)%len(fins)]["start_vertex"] for i in range(len(fins))):
        _fail("directed vertex chain does not close")
    if len(vertex_points) != len(fins) or len({x["start_vertex"] for x in fins}) != len(fins):
        _fail("loop is not a single cycle")
    classes = [x["geometry_class"] for x in fins]
    if classes.count(10) != 3 or classes.count(11) not in (1,2): _fail("unsupported source class combination")
    return geometry, root["geometry_sense"], fins, vertex_points, diagnostic


def _adjacent_linear_only_join(a, b):
    """Exact sufficient test for two directed linear spans meeting at J."""
    if len(a)!=2 or len(b)!=2 or a[-1]!=b[0]: return False
    j=a[-1]
    x=[a[0][i]-j[i] for i in (0,1)]
    y=[b[-1][i]-j[i] for i in (0,1)]
    if x==[0,0] or y==[0,0]: return False
    cross=x[0]*y[1]-x[1]*y[0]
    dot=x[0]*y[0]+x[1]*y[1]
    return cross!=0 or dot<0


def _slanted_left_candidate(circular, right_spans):
    """Find one linear cross-v=0 side strictly left of all right controls."""
    if not right_spans: _fail('missing right intersection side')
    right_min=min(p[0] for span in right_spans for p in span)
    candidates=[]
    for fin in circular:
        spans=fin['uv_spans']
        if len(spans)!=1 or len(spans[0])!=2: continue
        a,b=spans[0]
        if min(a[1],b[1])<0<max(a[1],b[1]) and max(a[0],b[0])<right_min:
            candidates.append(fin)
    if len(candidates)!=1:
        _fail('no unique strictly separated linear cross-v=0 source side')
    return candidates[0]


def _graph(fins, *, uv_join_rad):
    """Prove simple closure of a bounded derived FIN graph by convex boxes."""
    # Conservative canonical chart: interior lies well inside one torus period.
    controls = [p for f in fins for span in f["uv_spans"] for p in span]
    if any(not (Fraction(0) < p[0] < Fraction(6) and Fraction(-3) < p[1] < Fraction(3)) for p in controls):
        _fail("periodic seam/lift not supported by this bounded verifier")
    joins, maximum = [], Fraction(0)
    for i in range(len(fins)):
        a, b = fins[i]["uv_spans"][-1][-1], fins[(i+1)%len(fins)]["uv_spans"][0][0]
        delta = max(abs(a[0]-b[0]), abs(a[1]-b[1]))
        if delta > Fraction.from_float(float(uv_join_rad)): _fail("UV endpoint association exceeds matching threshold")
        maximum = max(maximum, delta)
        joins.append([(a[j]+b[j])/2 for j in range(2)])
    # Explicitly labelled derived representation; no raw FIN is overwritten.
    for i, fin in enumerate(fins):
        fin["uv_spans"][0][0] = joins[(i-1)%len(fins)]
        fin["uv_spans"][-1][-1] = joins[i]
        for a,b in zip(fin["uv_spans"],fin["uv_spans"][1:]):
            if a[-1] != b[0]: _fail("non-contiguous internal nonzero spans")
    spans = [span for fin in fins for span in fin["uv_spans"]]
    if any(a[-1] != b[0] for a,b in zip(spans, spans[1:]+spans[:1])): _fail("derived graph is not closed")
    def monotone(span, axis):
        diffs = [b[axis]-a[axis] for a,b in zip(span,span[1:])]
        if all(d >= 0 for d in diffs) and any(d > 0 for d in diffs): return 1
        if all(d <= 0 for d in diffs) and any(d < 0 for d in diffs): return -1
        return 0
    if any(not (monotone(span,0) or monotone(span,1)) for span in spans):
        _fail("single FIN span injectivity is not certified")
    def bounds(span, axis): return min(p[axis] for p in span), max(p[axis] for p in span)
    def separated(a,b,adjacent):
        shared = a[-1] if adjacent else None
        for axis in (0,1):
            alo, ahi = bounds(a,axis); blo, bhi = bounds(b,axis)
            if ahi < blo or bhi < alo: return not adjacent
            if adjacent and (ahi == blo == shared[axis] or bhi == alo == shared[axis]):
                # At least one curve has every non-joint control strictly away
                # from the common separating line, so only the joint can meet.
                if all(p[axis] != shared[axis] for p in a[:-1]) or all(p[axis] != shared[axis] for p in b[1:]):
                    return True
        return adjacent and _adjacent_linear_only_join(a,b)
    for i,a in enumerate(spans):
        for j in range(i+1,len(spans)):
            b=spans[j]
            if j==i+1:
                ok=separated(a,b,True)
            elif i==0 and j==len(spans)-1:
                ok=separated(b,a,True)
            else:
                ok=separated(a,b,False)
            if not ok: _fail("simple non-self-intersecting graph not certified")
    # Exact polynomial line-integral establishes a nonzero oriented area.
    def coeff(values):
        if len(values)==2: return [values[0],values[1]-values[0]]
        if len(values)==3: return [values[0],2*(values[1]-values[0]),values[0]-2*values[1]+values[2]]
        _fail("unsupported FIN degree")
    area2=Fraction(0)
    for span in spans:
        x,y=coeff([p[0] for p in span]),coeff([p[1] for p in span])
        for i,a in enumerate(x):
            for j,b in enumerate(y[1:],1): area2 += a*j*b/Fraction(i+j)
        for i,a in enumerate(y):
            for j,b in enumerate(x[1:],1): area2 -= a*j*b/Fraction(i+j)
    if area2 == 0: _fail("zero-area graph")
    # Candidate interior point is justified by an empty vertical strip bounded
    # by the left edge, right-edge control hull, and the top/bottom hulls.
    circular = [f for f in fins if f["geometry_class"] == 10]
    left_candidates = [f for f in circular if len({p[0] for span in f["uv_spans"] for p in span}) == 1]
    fallback=False
    right_spans=[span for f in fins if f["geometry_class"]==11 for span in f["uv_spans"]]
    if len(left_candidates)==1:
        left=left_candidates[0]
    elif not left_candidates:
        left=_slanted_left_candidate(circular,right_spans)
        fallback=True
    else:
        _fail("no unique constant-U source side")
    uleft=max(p[0] for span in left['uv_spans'] for p in span) if fallback else left["uv_spans"][0][0][0]
    others=[f for f in circular if f is not left]
    if len(others)!=2: _fail("missing top/bottom source sides")
    top=max(others,key=lambda f: max(p[1] for span in f["uv_spans"] for p in span))
    bottom=next(f for f in others if f is not top)
    left_index=next(i for i,f in enumerate(fins) if f is left)
    adjacent={id(fins[(left_index-1)%len(fins)]),id(fins[(left_index+1)%len(fins)])}
    if adjacent != {id(top),id(bottom)}:
        _fail("constant-U side is not connected to the upper and lower boundaries")
    left_v=[left["uv_spans"][0][0][1],left["uv_spans"][-1][-1][1]]
    if not min(left_v) < 0 < max(left_v): _fail("constant-U side does not cross interior chart")
    if min(p[1] for span in top["uv_spans"] for p in span) <= 0 or max(p[1] for span in bottom["uv_spans"] for p in span) >= 0:
        _fail("interior strip is not bounded above and below")
    right_directions=[monotone(span,1) for span in right_spans]
    if not right_directions or 0 in right_directions or len(set(right_directions)) != 1:
        _fail("intersection-side FIN chain is not strictly monotone in V")
    if fallback and (any(a[-1]!=b[0] for a,b in zip(right_spans,right_spans[1:]))
                     or not min(right_spans[0][0][1],right_spans[-1][-1][1]) < 0 < max(right_spans[0][0][1],right_spans[-1][-1][1])):
        _fail('intersection-side FIN chain does not continuously cross V=0')
    right_min=min(p[0] for span in right_spans for p in span)
    if right_min <= uleft: _fail("interior strip has no positive width")
    interior_u=float((uleft+right_min)/2)
    if not uleft < Fraction.from_float(interior_u) < right_min:
        _fail('binary64 interior point is not strictly inside the proven interval')
    result={"status":"validated_derived_returned_FIN_graph", "loop_count":1, "hole_count_in_derived_graph":0,
            "nonzero_span_count":len(spans), "uv_join_max_linf_rad":float(maximum),
            "uv_join_threshold_rad":uv_join_rad, "periodic_lifts":[0]*len(fins),
            "period_scope":"all control hulls strictly within 0<U<6 and -3<V<3; no seam/lift in this supported chart",
            "simple_graph_proof":"exact binary64-rational monotone-projection injectivity per span, convex-box pair separation or exact adjacent linear-only join, and nonzero oriented area after explicit vertex identification",
            "oriented_area_twice_exact":[area2.numerator,area2.denominator],
            "interior_uv":[interior_u,0.0],
            "qualification":"UV joins are derived midpoint identifications bounded by the recorded matching threshold; not proof of exact native SP/implicit correspondence."}
    if fallback:
        result['interior_proof']='unique linear side strictly crosses v=0 and lies strictly left of the continuous monotone intersection chain; other two sides do not meet v=0'
    return result


def _load_detail(root, relative, queue):
    snapshot_path = _path(root, relative)
    if snapshot_path.name != "detail-snapshot.json": _fail("unexpected snapshot filename")
    evidence = snapshot_path.parent
    summary_path = evidence / "detail-summary.json"
    takeover_path = evidence / "detail-takeover.json"
    status_path = evidence / "detail-status.json"
    for path in (summary_path, takeover_path, status_path):
        if not queue.inside(path, evidence): _fail("missing or escaped saved proof")
    snapshot, summary, takeover = _read(snapshot_path), _read(summary_path), _read(takeover_path)
    _require_mm(snapshot)
    request = summary.get("detail_request", {})
    selectors = request.get("selectors")
    if not isinstance(selectors, list) or len(selectors) != 1: _fail("single requested source required")
    pid, epoch = summary.get("pid"), takeover.get("session_epoch")
    if (type(pid) is not int or pid <= 0 or not isinstance(epoch, str) or len(epoch)>40
            or re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", epoch, re.ASCII) is None
            or not epoch.startswith(str(pid)+":") or int(epoch.split(":")[1])>3155378975999999999):
        _fail("invalid saved source process identity")
    ctx = {"pid":pid,"session_epoch":epoch,"part":summary.get("part"),
           "match_linear":request.get("match_linear"),"curve_tolerance":request.get("curve_tolerance"),
           "surface_tolerance":request.get("surface_tolerance"),"angular_tolerance":.0001}
    queue.validate_evidence(evidence, selectors[0], ctx, 1)
    return snapshot, summary


def _p1_label(p1, source_face, threshold):
    data = source_face["native_face_data"]
    matches = [i for i, face in enumerate(p1["inventory"]["selected_body"]["faces"], 1)
               if face["surface_type"] == source_face["surface_type"]
               and face["native_face_data"]["uf_type"] == data["uf_type"]
               and len(face["edge_tags"]) == len(source_face["edge_tags"])
               and all(abs(a-b) <= threshold for a,b in zip(face["native_face_data"]["bounding_box"],data["bounding_box"]))]
    if len(matches) != 1: _fail("P1 semantic correspondence is missing or ambiguous")
    return f"F{matches[0]:04d}"


def _parent_path(root, label, queue_plan, prior):
    matches = [x for x in queue_plan.get("items", []) if x.get("source_face_id") == label]
    if len(matches) > 1: _fail("duplicate carrier source")
    if matches:
        path = Path(matches[0]["evidence_dir"]).resolve(strict=True) / "detail-snapshot.json"
        if not path.is_relative_to(root): _fail("carrier evidence outside workspace")
        return path.relative_to(root).as_posix()
    paths = prior.get("detailed_paths", {}).get(label)
    paths = paths if isinstance(paths, list) else [paths] if isinstance(paths, str) else []
    if len(paths) != 1: _fail("parent has no unique previously recorded detail")
    summary = _path(root, paths[0])
    if summary.name != "detail-summary.json": _fail("unexpected parent summary path")
    return (summary.parent / "detail-snapshot.json").relative_to(root).as_posix()


def _pair(point):
    return [[v.numerator,v.denominator] for v in point]


def build_certificate(repository_root, target_label, *, queue, match_mm=DEFAULT_LINEAR_MATCH_MM,
                      uv_join_rad=DEFAULT_UV_JOIN_RAD):
    """Verify one saved source record and its supported returned-FIN graph.

    ``queue`` must be the existing strict validator module supplied by the
    trusted offline entrypoint. Thresholds only disambiguate corresponding
    recorded endpoints; they are not a native or geometric error bound.
    """
    root = Path(repository_root).resolve(strict=True)
    if (not isinstance(target_label,str) or re.fullmatch(r"F[0-9]{4}",target_label,re.ASCII) is None
            or not _number(match_mm) or not 0 < match_mm <= .001
            or not _number(uv_join_rad) or not 0 < uv_join_rad <= 1e-8):
        _fail("invalid target or matching thresholds")
    p1, ledger, plan, prior = (_read(_path(root,p)) for p in (P1,LEDGER,QUEUE,PRIOR))
    _require_mm(p1)
    if (p1.get("snapshot_id") != P1_ID or p1.get("inventory_complete") is not True
            or ledger.get("schema") != "p3-22-member-native-root-construction-ledger/1.0"
            or plan.get("source_snapshot_id") != P1_ID or prior.get("source_snapshot_id") != P1_ID):
        _fail("source inventory or ledger identity mismatch")
    groups = [g for g in ledger.get("groups",[]) if g.get("root_shoulder_face") == target_label]
    if len(groups)!=1: _fail("root ledger does not contain exactly one target")
    group=groups[0]
    relative=group.get("root_native",{}).get("source_path")
    snapshot,summary=_load_detail(root,relative,queue)
    if (snapshot.get("snapshot_id") != group["root_native"].get("snapshot_id")
            or summary.get("p1_snapshot_id") != P1_ID or summary["detail_request"]["selectors"][0].get("label") != target_label
            or _p1_label(p1,snapshot["detail"][0]["observed_face"],match_mm) != target_label):
        _fail("target source binding differs from root ledger or P1")
    geometry,sense,fins,vertices,diagnostic=_topology(snapshot,summary,match_mm=match_mm,uv_join_rad=uv_join_rad)
    if (geometry != group["root_native"].get("geometry") or sense != group["root_native"].get("geometry_sense")
            or snapshot.get("geometry_details_complete") is not False):
        _fail("raw root differs from source ledger")
    bodies = snapshot["inventory"].get("bodies")
    selected_tag = snapshot["inventory"]["selected_body"]["tag"]
    selected = [body for body in bodies if body.get("tag") == selected_tag] if isinstance(bodies,list) else []
    if len(selected)!=1 or selected[0].get("is_solid") is not True:
        _fail("selected body is not recorded as one solid")
    parents = {}
    for fin in fins:
        if fin["geometry_class"] != 11: continue
        neighbor=fin["other_parent_same_snapshot"]
        probe={"surface_type":neighbor["surface_type"],"native_face_data":neighbor["native_face_data"],
               "edge_tags":[None]*neighbor["edge_count"]}
        label=_p1_label(p1,probe,match_mm)
        if label not in parents:
            parent_path=_parent_path(root,label,plan,prior)
            parent_snapshot,parent_summary=_load_detail(root,parent_path,queue)
            detail=parent_snapshot["detail"][0]
            parent_root=detail["diagnostic"]["topology"]
            if (_p1_label(p1,detail["observed_face"],match_mm) != label
                    or parent_summary["detail_request"]["selectors"][0].get("label") != label
                    or parent_root.get("geometry_rc") != 0 or parent_root.get("geometry_free_rc") != 0
                    or type(parent_root.get("geometry_sense")) is not int or parent_root["geometry_sense"] not in (-1,1)
                    or parent_root.get("states") != []
                    or parent_root["geometry"].get("type") != 204):
                _fail("implicit parent detail does not semantically bind")
            _frame(parent_root["geometry"])
            parents[label]={"source_snapshot_id":parent_snapshot["snapshot_id"],"source_path":parent_path,
                            "geometry":deepcopy(detail["diagnostic"]["topology"]["geometry"]),
                            "frame_correspondence":"semantic_candidate_not_independent_frame_proof"}
        fin["other_parent_same_snapshot"]["p1_semantic_label"]=label
        fin["other_parent_same_snapshot"]["parent_detail_snapshot_id"]=parents[label]["source_snapshot_id"]
    graph=_graph(fins,uv_join_rad=uv_join_rad)
    u,v=graph["interior_uv"]
    _,axis,ref,tangent=_frame(geometry)
    radial=[math.cos(u)*ref[i]+math.sin(u)*tangent[i] for i in range(3)]
    outward=[sense*(math.cos(v)*radial[i]+math.sin(v)*axis[i]) for i in range(3)]
    source_records=[]
    for f in fins:
        entry={k:deepcopy(v) for k,v in f.items() if k!="uv_spans"}
        entry["derived_joined_bezier_controls_exact"]=[[_pair(point) for point in span] for span in f["uv_spans"]]
        entry["source_role"] = "normal_edge_circle_and_api_returned_FIN" if f["geometry_class"]==10 else "implicit_two_parent_intersection_with_API_conversion"
        entry["stored_original_3d_spline"] = False if f["geometry_class"]==11 else None
        source_records.append(entry)
    return {"schema":"p3-torus-source-trim-certificate/0.1", "target":{"kind":"current_prt",
            "p1_snapshot_id":P1_ID,"source_snapshot_id":snapshot["snapshot_id"],"source_snapshot_path":relative,
            "unit":"mm","historical_STEP_accuracy":"not_required_for_current_prt"},
            "source_definition":{"status":"accepted_under_recorded_API_contract","root_geometry":deepcopy(geometry),
              "geometry_sense":sense,"source_FINs":source_records,"implicit_other_parents":parents,
              "options":deepcopy(diagnostic["options"]),"mapping":deepcopy(diagnostic["mapping"]),
              "root_topology_state_count":diagnostic["topology_state_count"],"reader_geometry_details_complete":False,
              "curve_conversion_tolerance":"recorded_API_request_not_a_global_error_bound"},
            "source_trim":{"topological_loop":"validated_same_tree_vertex_cycle",
              "returned_FIN_graph":graph,"actual_implicit_branch_and_source_domain":"conditional_not_yet_certified",
              "source_material_side":{"status":"conditional_local_orientation_under_UF_contract", "sample_uv":[u,v],
                 "source_outward_normal_unit":outward,"geometry_sense":sense,
                 "scope":"body is reported solid; outward/material interpretation assumes a valid solid under UF contract. Sample is on derived graph; exact native face membership and whole-body occupancy remain unproven"}},
            "candidate_region":{"status":"conditional","source":LEDGER,"member":group["member"],
              "limitations":["actual source/stock frame correspondence and unique implicit branch", "candidate stock material role and all interfaces"]},
            "candidate_source_relation":{"status":"conditional", "specific_open_items":[
              "prove each class11 two-parent implicit intersection has the selected unique branch over its complete span",
              "bound source FIN/3D representation correspondence without treating API request as a Hausdorff certificate",
              "verify candidate S0 and complete tool/source patch mapping, no overcut or missing boundary"]},
            "matching_thresholds":{"endpoint_disambiguation_mm":match_mm,"UV_join_identification_rad":uv_join_rad,
                                   "scope":"explicit matching thresholds, not source accuracy or engineering tolerance"},
            "execution_approved":False}
