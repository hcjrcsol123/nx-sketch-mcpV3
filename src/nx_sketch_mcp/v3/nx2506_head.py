"""Compile the accepted P3 head defaults to concrete, offline CSG operations.

This module does not execute NX, establish associativity, or approve execution.
All lengths are millimetres, angles are degrees, and frames are ABS.
"""
import math
from fractions import Fraction


def _line(a, b):
    return {"kind": "line", "start": list(a), "end": list(b)}


def _filled_arc(ident, y0, y1, center_y, radius, radial_offset=0.0):
    """Revolve a filled outer circular meridian on a finite station interval."""
    def point(y):
        q = radius * radius - (y - center_y) ** 2
        if q < 0:
            raise ValueError("head meridian outside circle: " + ident)
        return [radial_offset + math.sqrt(q), y]
    if not y0 < y1:
        raise ValueError("empty or reversed head station: " + ident)
    p0, pm, p1 = point(y0), point((y0 + y1) / 2), point(y1)
    edges = [{"kind": "arc", "start": p0, "mid": pm, "end": p1}]
    if p1[0] != 0:
        edges.append(_line(p1, [0, y1]))
    edges.append(_line([0, y1], [0, y0]))
    if p0[0] != 0:
        edges.append(_line([0, y0], p0))
    return _revolve(ident, [0, 0, 0], [1, 0, 0], [0, 1, 0], edges,
                    [0, 0, 0], [0, 1, 0])


def _revolve(ident, origin, x_axis, y_axis, edges, axis_point, axis_direction):
    return {"id": ident, "kind": "revolve",
            "frame": {"origin": origin, "x_axis": x_axis, "y_axis": y_axis},
            "edges": edges, "axis_point": axis_point, "axis_direction": axis_direction,
            "start_degrees": 0.0, "end_degrees": 360.0}


def _boolean(ident, operation, target, tools):
    return {"id": ident, "kind": "boolean", "operation": operation,
            "target": target, "tools": tools, "retain_tools": False}



def _base_expressions(params):
    """Candidate NX expressions and XYZ references for six axial meridians.

    The shared stock mouth expression is an external dependency, supplied by
    the stock compiler. Branch selection is for the recorded default domain.
    """
    expressions = []
    def add(short, formula, unit="mm"):
        name = "v3_head_" + short
        expressions.append({"id": "head.expression." + short, "kind": "expression",
                            "name": name, "formula": formula, "unit": unit})
        return name
    def literal(key):
        return format(float(params["head." + key]["value"]), ".17f").rstrip("0").rstrip(".") or "0"
    zero = add("zero", "0")
    r31, r32, r40 = (add(k, literal(k)) for k in ("R31", "R32", "R40"))
    y40, yl, yh = (add(k, literal(k)) for k in ("Y40", "Y_lower_step", "Y_head_step"))
    rl, ru = (add(k, literal(k)) for k in ("r_lower_fillet", "r_upper_fillet"))
    apex = add("cone_apex_Y", literal("cone_apex_Y"))
    angle = add("cone_half_angle", literal("cone_half_angle_initial_exact"), "rad")
    lower_y = add("lower_fillet_y", yl + "+" + rl)
    upper_y = add("upper_fillet_y", yh + "-" + ru)
    lower_major = add("lower_fillet_major", "sqrt((%s-%s)*(%s-%s)-(%s-%s)*(%s-%s))" %
                      (r40,rl,r40,rl,lower_y,y40,lower_y,y40))
    upper_major = add("upper_fillet_major", "sqrt((%s-%s)*(%s-%s)-(%s-%s)*(%s-%s))" %
                      (r40,ru,r40,ru,upper_y,y40,upper_y,y40))
    lc = add("lower_contact_y", "%s+%s*(%s-%s)/(%s-%s)" % (y40,r40,lower_y,y40,r40,rl))
    uc = add("upper_contact_y", "%s+%s*(%s-%s)/(%s-%s)" % (y40,r40,upper_y,y40,r40,ru))
    bottom = add("R31_bottom_y", "-" + r31)
    mouth = "v3_stock_Y_mouth"
    bindings = {}
    def profile(short, station0, station1, center, radius, offset=None, tangent_end=None):
        mid = add(short + "_mid_y", "(" + station0 + "+" + station1 + ")/2")
        ys = [station0, mid, station1]
        rs = []
        for label, y in zip(("start", "mid", "end"), ys):
            # R31 begins at the axis exactly; avoid a fragile zero-radicand
            # expression and preserve the planned axial pole.
            if short == "R31" and label == "start":
                rs.append(zero)
                continue
            if label == tangent_end:
                # At the axial step the circle's radial offset from the
                # center is exactly zero. Its direct expression remains
                # valid when the step and fillet radius move together.
                rs.append(add(short+"_"+label+"_r", offset))
                continue
            delta = "(" + y + "-" + center + ")"
            formula = "sqrt(%s*%s-%s*%s)" % (radius, radius, delta, delta)
            if offset:
                formula = offset + "+" + formula
            rs.append(add(short+"_"+label+"_r", formula))
        bindings["head." + {"R31":"R31_piece", "lower":"lower_fillet_piece",
                              "R40":"R40_piece", "upper":"upper_fillet_piece",
                              "R32":"R32_piece"}[short]] = (ys, rs)
    profile("R31", bottom, yl, zero, r31)
    profile("lower", yl, lc, lower_y, rl, lower_major, tangent_end="start")
    profile("R40", lc, uc, y40, r40)
    profile("upper", uc, yh, upper_y, ru, upper_major, tangent_end="end")
    profile("R32", yh, mouth, zero, r32)
    # On the recorded branch max(apex, head step, B lower) = head step,
    # and min(mouth, B upper) = mouth. Guard edits before regeneration.
    cone0 = add("cone_start_r", "tan(%s)*(%s-%s)" % (angle,yh,apex))
    cone1 = add("cone_end_r", "tan(%s)*(%s-%s)" % (angle,mouth,apex))
    bindings["head.cone_piece"] = ([yh, mouth], [cone0, cone1])
    return expressions, bindings, zero


def _bind_axial_points(step, bindings, zero):
    ys, rs = bindings[step["id"]]
    def xyz(r, y):
        return [r, y, zero]
    if step["id"] == "head.cone_piece":
        points = [[xyz(rs[0],ys[0]), xyz(rs[1],ys[1])],
                  [xyz(rs[1],ys[1]), xyz(zero,ys[1])],
                  [xyz(zero,ys[1]), xyz(zero,ys[0])],
                  [xyz(zero,ys[0]), xyz(rs[0],ys[0])]]
    else:
        points = [[xyz(rs[0],ys[0]), xyz(rs[1],ys[1]), xyz(rs[2],ys[2])],
                  [xyz(rs[2],ys[2]), xyz(zero,ys[2])],
                  [xyz(zero,ys[2]), xyz(zero,ys[0])]]
        if rs[0] != zero:
            points.append([xyz(zero,ys[0]), xyz(rs[0],ys[0])])
    if len(points) != len(step["edges"]):
        raise ValueError("unexpected axial profile topology: " + step["id"])
    for edge, point_expressions in zip(step["edges"], points):
        edge["point_expressions"] = point_expressions


def _a_torus_expressions(index, theta, major, minor):
    """Expression-backed two-semicircle torus profile and associated axis.

    Coordinates are in the ABS frame. The two axis points are separated by
    one millimetre in the axis direction; their separation is not a product
    dimension. Fixed prism clips still require a complete dependency binding.
    """
    steps = []
    prefix = "sector_%d_" % index
    def add(short, formula, unit="mm"):
        name = "v3_head_" + prefix + short
        steps.append({"id": "head.expression." + prefix + short,
                      "kind": "expression", "name": name,
                      "formula": formula, "unit": unit})
        return name
    def literal(number):
        return format(number, ".17f").rstrip("0").rstrip(".") or "0"
    th = add("theta", literal(theta), "rad")
    ra = add("A_major_radius", literal(major))
    tube = add("A_minor_radius", literal(minor))
    unit_length = add("axis_reference_length", "1")
    ux = add("axis_point_x", unit_length + "*cos(" + th + ")")
    uz = add("axis_point_z", unit_length + "*sin(" + th + ")")
    px = add("profile_plus_x", tube + "*cos(" + th + ")")
    pz = add("profile_plus_z", tube + "*sin(" + th + ")")
    nx = add("profile_minus_x", "-" + px)
    nz = add("profile_minus_z", "-" + pz)
    cy = add("profile_center_y", "v3_head_Y40+" + ra)
    high = add("profile_upper_y", cy + "+" + tube)
    low = add("profile_lower_y", cy + "-" + tube)
    zero = "v3_head_zero"
    axis_points = [[zero, "v3_head_Y40", zero], [ux, "v3_head_Y40", uz]]
    minus = [nx, cy, nz]
    plus = [px, cy, pz]
    upper = [zero, high, zero]
    lower = [zero, low, zero]
    return steps, axis_points, [[minus, upper, plus], [plus, lower, minus]]


def _b_torus_expressions(index, branch, d, rb):
    """Compile the recorded tangent-root branch, section and axis points."""
    steps = []
    sector = "v3_head_sector_%d_" % index
    prefix = "sector_%d_branch_%d_" % (index, branch)
    def add(short, formula):
        name = "v3_head_" + prefix + short
        steps.append({"id":"head.expression." + prefix + short, "kind":"expression",
                      "name":name, "formula":formula, "unit":"mm"})
        return name
    def literal(number):
        return format(number, ".17f").rstrip("0").rstrip(".") or "0"
    dd = add("d", literal(d))
    tube = add("rb", literal(rb))
    ra, R, theta = sector+"A_minor_radius", sector+"A_major_radius", sector+"theta"
    gap = add("radius_gap", tube+"-"+ra)
    major = add("major", R+"-sqrt("+gap+"*"+gap+"-"+dd+"*"+dd+")")
    contact = add("contact_s", "-"+ra+"*"+dd+"/"+gap)
    end_d = add("axis_end_s", dd+"+"+sector+"axis_reference_length")
    plus_d = add("profile_plus_s", dd+"+"+tube)
    minus_d = add("profile_minus_s", dd+"-"+tube)
    def xz(name, station):
        return (add(name+"_x", station+"*cos("+theta+")"),
                add(name+"_z", station+"*sin("+theta+")"))
    cx, cz = xz("center", dd)
    ex, ez = xz("axis_end", end_d)
    px, pz = xz("profile_plus", plus_d)
    nx, nz = xz("profile_minus", minus_d)
    cy = add("profile_center_y", "v3_head_Y40+"+major)
    high = add("profile_upper_y", cy+"+"+tube)
    low = add("profile_lower_y", cy+"-"+tube)
    axis = [[cx,"v3_head_Y40",cz], [ex,"v3_head_Y40",ez]]
    minus, plus = [nx,cy,nz], [px,cy,pz]
    upper, lower = [cx,high,cz], [cx,low,cz]
    return steps, axis, [[minus,upper,plus], [plus,lower,minus]], contact


def _clip_rectangle_expressions(index, label, s0, s1, extent):
    """World XZ corners of the finite local (s,t) rectangle."""
    steps = []
    prefix = "sector_%d_%s_clip_" % (index, label)
    theta = "v3_head_sector_%d_theta" % index
    def add(short, formula):
        name = "v3_head_" + prefix + short
        steps.append({"id":"head.expression."+prefix+short, "kind":"expression",
                      "name":name, "formula":formula, "unit":"mm"})
        return name
    zero = "v3_head_zero"
    points = []
    for i, (s, t) in enumerate(((s0,zero),(s1,zero),(s1,extent),(s0,extent))):
        x = add("p%d_x" % i, s+"*cos("+theta+")+"+t+"*sin("+theta+")")
        z = add("p%d_z" % i, s+"*sin("+theta+")-"+t+"*cos("+theta+")")
        points.append([x,zero,z])
    return steps, points

def compile_head(plan):
    """Return ordered native-operation dictionaries for the recorded default head.

    The six axial meridians and A-torus profiles and axes include candidate
    native point expressions; B tori and seam/axial clips also have expression
    bindings using the shared stock enclosure radius. No actual NX dependency
    propagation, precision or boolean result is asserted. Input consistency
    checks are necessary checks, not edited-domain proofs.
    """
    if plan.get("schema") is None:
        raise ValueError("missing plan schema")
    construction = plan["construction"]
    nodes = {n["id"]: n for n in construction["nodes"]}
    params = {p["id"]: p for p in plan["parameters"]["regional"]}
    def value(name):
        x = float(params[name]["value"])
        if not math.isfinite(x):
            raise ValueError("non-finite parameter: " + name)
        return x
    def close(name, calculated):
        if not math.isclose(value(name), calculated, rel_tol=1e-13, abs_tol=1e-12):
            raise ValueError("inconsistent pre-evaluated parameter: " + name)

    h = plan["parameters"]["canonical_definitions"]["head"]
    for name, default in h["global_independent"].items():
        if isinstance(default, (int, float)) and value("head." + name) != default:
            raise ValueError("head compilation supports recorded defaults only: " + name)
    close("head.cone_half_angle_initial_exact", math.pi / 4)
    if value("stock.Y_mouth") != float(h["shared_interface"]["initial_mm"]):
        raise ValueError("head compilation supports the recorded mouth default only")
    r31, r32, r40 = (value("head." + k) for k in ("R31", "R32", "R40"))
    y40, yl, yh, mouth = (value(k) for k in
        ("head.Y40", "head.Y_lower_step", "head.Y_head_step", "stock.Y_mouth"))
    rl, ru = value("head.r_lower_fillet"), value("head.r_upper_fillet")
    for prefix, cy, rad in (("lower", yl + rl, rl), ("upper", yh - ru, ru)):
        if not (r40 > rad > 0 and (r40-rad)**2 > (cy-y40)**2):
            raise ValueError("invalid fillet domain: " + prefix)
        close("head." + prefix + "_fillet_y", cy)
        close("head." + prefix + "_fillet_major", math.sqrt((r40-rad)**2-(cy-y40)**2))
        close("head." + prefix + "_sphere_contact_y", y40+r40*(cy-y40)/(r40-rad))
    lc, uc = value("head.lower_sphere_contact_y"), value("head.upper_sphere_contact_y")
    if not (-r31 < yl < lc < uc < yh < mouth < r32):
        raise ValueError("head station ordering is invalid")
    box = construction["implementation_route"]["solid_enclosure"]["default_binary64_outward_preview"]
    rb, blo, bhi = (float(box[k]) for k in ("radial_upper_mm", "y_lower_mm", "y_upper_mm"))
    if not (math.isfinite(rb) and math.isfinite(blo) and math.isfinite(bhi)
            and rb > max(r31, r32, r40) and blo < -r31 and bhi > mouth):
        raise ValueError("default B does not enclose the head meridians")
    if max(value("head.lower_fillet_major") + rl, value("head.upper_fillet_major") + ru) > rb:
        raise ValueError("filled fillet meridian exceeds default B")
    steps = [
        _filled_arc("head.R31_piece", -r31, yl, 0, r31),
        _filled_arc("head.lower_fillet_piece", yl, lc, value("head.lower_fillet_y"), rl, value("head.lower_fillet_major")),
        _filled_arc("head.R40_piece", lc, uc, y40, r40),
        _filled_arc("head.upper_fillet_piece", uc, yh, value("head.upper_fillet_y"), ru, value("head.upper_fillet_major")),
        _filled_arc("head.R32_piece", yh, mouth, 0, r32),
    ]
    apex, angle = value("head.cone_apex_Y"), value("head.cone_half_angle_initial_exact")
    lo, hi = max(apex, yh, blo), min(mouth, bhi)
    if not lo < hi or not (0 < angle < math.pi / 2):
        raise ValueError("empty or invalid positive cone")
    a, b = math.tan(angle)*(lo-apex), math.tan(angle)*(hi-apex)
    close("head.mouth_radius", math.tan(angle)*(mouth-apex))
    if max(a, b) > rb:
        raise ValueError("cone exceeds default B")
    cone_edges = [_line([a, lo], [b, hi]), _line([b, hi], [0, hi]), _line([0, hi], [0, lo])]
    if a:
        cone_edges.append(_line([0, lo], [a, lo]))
    steps.append(_revolve("head.cone_piece", [0,0,0], [1,0,0], [0,1,0], cone_edges, [0,0,0], [0,1,0]))

    expression_steps, axial_bindings, zero_name = _base_expressions(params)
    for step in steps:
        _bind_axial_points(step, axial_bindings, zero_name)
    steps = expression_steps + steps

    for i, sector in enumerate(h["sectors"]):
        prefix = "head.sector.%d." % i
        theta, major, minor = (value(prefix+k) for k in ("theta", "RA", "ra"))
        if (theta != sector["theta_initial_display_rad"] or major != sector["RA_initial_source_binary64"]
                or minor != sector["ra_initial_source_binary64"]):
            raise ValueError("sector inputs differ from recorded defaults: " + prefix)
        c, s = math.cos(theta), math.sin(theta)
        close(prefix+"axis_x", c)
        close(prefix+"axis_z", s)
        es, et = [c, 0.0, s], [s, 0.0, -c]
        # Bounds of the projection of the eight B corners; round outward.
        extent = math.nextafter(math.nextafter(rb * (abs(c) + abs(s)), math.inf), math.inf)
        seams = []
        for j, branch in enumerate(sector["branches"]):
            bp = prefix+"branch.%d." % j
            d, r = value(bp+"d"), value(bp+"rb")
            dlo, dhi = (float(Fraction(v)) for v in branch["d_initial_exact_enclosure"])
            if (r != branch["rb_initial_source_binary64"] or not (r > minor > 0 and abs(d) < r-minor)
                    or not (math.nextafter(dlo, -math.inf) <= d <= math.nextafter(dhi, math.inf))):
                raise ValueError("invalid or edited torus branch: " + bp)
            maj = major-math.sqrt((r-minor)**2-d*d)
            close(bp+"major_radius", maj)
            close(bp+"contact_s", -minor*d/(r-minor))
            seams.append(value(bp+"contact_s"))
        if not (seams[1] < seams[0]):
            raise ValueError("branch seam order changed: " + prefix)
        # Default preview uses outward-rounded projected B. The NX expression
        # follows the exact stock B radius and theta; native rounding remains to
        # be measured. Edited seam and slab order still require explicit guards.
        if not (-extent < seams[1] < seams[0] < extent and blo < uc < yh < mouth < bhi):
            raise ValueError("sector seams or stations outside B: " + prefix)
        a_steps, a_axis, a_arcs = _a_torus_expressions(i, theta, major, minor)
        steps.extend(a_steps)
        b_data = []
        for j in range(2):
            bp = prefix+"branch.%d." % j
            data = _b_torus_expressions(i, j, value(bp+"d"), value(bp+"rb"))
            steps.extend(data[0])
            b_data.append(data)
        ext_name = "v3_head_sector_%d_clip_extent" % i
        minus_ext_name = "v3_head_sector_%d_clip_minus_extent" % i
        steps.extend([
            {"id":"head.expression.sector_%d_clip_extent" % i, "kind":"expression",
             "name":ext_name,
             "formula":"v3_stock_B_radial*(sqrt(cos(v3_head_sector_%d_theta)*cos(v3_head_sector_%d_theta))+sqrt(sin(v3_head_sector_%d_theta)*sin(v3_head_sector_%d_theta)))" % (i,i,i,i),
             "unit":"mm"},
            {"id":"head.expression.sector_%d_clip_minus_extent" % i, "kind":"expression",
             "name":minus_ext_name, "formula":"-"+ext_name, "unit":"mm"},
        ])
        pieces = [(prefix+"A_piece", 0.0, major, minor, seams[1], seams[0], uc,
                   "A", b_data[1][3], b_data[0][3], "v3_head_upper_contact_y", a_axis, a_arcs)]
        for j in range(2):
            bp = prefix+"branch.%d." % j
            low, high = (seams[j], extent) if j == 0 else (-extent, seams[j])
            s0ref, s1ref = (b_data[j][3], ext_name) if j == 0 else (minus_ext_name, b_data[j][3])
            pieces.append((bp+"B_piece", value(bp+"d"), value(bp+"major_radius"), value(bp+"rb"),
                           low, high, yh, "B%d" % j, s0ref, s1ref, "v3_head_Y_head_step",
                           b_data[j][1], b_data[j][2]))
        for ident, d, R, r, s0, s1, y0, label, s0ref, s1ref, y0ref, axis_refs, arc_refs in pieces:
            y1 = mouth
            if not (R > r > 0 and s0 < s1 and y0 < y1 and extent > 0):
                raise ValueError("empty or invalid sector clip: " + ident)
            torus_id, clip_id = ident+".torus", ident+".clip"
            axis_point = [d*c, y40, d*s]
            arcs = [{"kind":"arc", "start":[-r,R], "mid":[0,R+r], "end":[r,R],
                     "point_expressions":arc_refs[0]},
                    {"kind":"arc", "start":[r,R], "mid":[0,R-r], "end":[-r,R],
                     "point_expressions":arc_refs[1]}]
            torus = _revolve(torus_id, axis_point, es, [0,1,0], arcs, axis_point, es)
            torus["axis_points_expressions"] = axis_refs
            steps.append(torus)
            expr, refs = _clip_rectangle_expressions(i, label, s0ref, s1ref, ext_name)
            steps.extend(expr)
            corners = [[s0,0], [s1,0], [s1,extent], [s0,extent]]
            edges = []
            for k in range(4):
                edge = _line(corners[k], corners[(k+1)%4])
                edge["point_expressions"] = [refs[k],refs[(k+1)%4]]
                edges.append(edge)
            steps.append({"id":clip_id, "kind":"extrude",
                          "frame":{"origin":[0,0,0], "x_axis":es, "y_axis":et},
                          "edges":edges, "direction":[0,1,0], "start":y0, "end":y1,
                          "start_formula":y0ref, "end_formula":"v3_stock_Y_mouth"})
            steps.append(_boolean(ident, "intersect", torus_id, [clip_id]))
    ids = nodes["head.removal_tool"]["depends_on"]
    if len(ids) != 24 or {step["id"] for step in steps}.intersection(ids) != set(ids):
        raise ValueError("head union membership differs from plan")
    steps.append(_boolean("head.removal_tool", "unite", ids[0], ids[1:]))
    steps.append(_boolean("head.result", "subtract", "member_21_result", ["head.removal_tool"]))
    return {"steps":steps, "output_id":"head.result", "trace":{
        "plan_schema":plan["schema"], "parameter_defaults":{k:v["value"] for k,v in params.items() if k.startswith("head.") or k == "stock.Y_mouth"},
        "piece_dependencies":{k:nodes[k].get("depends_on_parameters", []) for k in ids},
        "piece_predicates":{k:nodes[k].get("predicate") for k in ids},
        "head_expression_external_dependencies":["v3_stock_Y_mouth", "v3_stock_B_radial"],
        "head_expression_scope":"axial meridians, A/B torus curves and axes, seam clip corners, projected B extents and axial limits have candidate expressions",
        "unbound_head_dependencies":{
            "sector_tori":"A and B sections/axes reference theta, RA, ra, Y40 and each branch d/rb; B major and seam use the selected tangent root",
            "sector_clips":"seams, theta, upper sphere contact, head step, stock mouth and stock enclosure radius bind to clip geometry; native numerical enclosure and edited seam/station order remain unverified",
            "edited_domains":"tangent root branch, real radicands, station and seam order, occupancy, stock interfaces and exposure require independent proof before editing"},
        "bounding_box":box, "skipped_carriers":[n["id"] for n in construction["nodes"] if n.get("operation") in ("cone_carrier", "sphere_carrier", "torus_carrier", "tangent_torus_carrier") and n["id"].startswith("head")],
        "shared_mouth_face":"F0196", "shared_mouth_owner":"stock"},
        "limitations":["Axial meridians, A/B torus curves/axes and seam clips have candidate expressions. Projected B extents follow the stock enclosure radius and sector angle; edited-domain, branch and native numerical enclosure proofs are absent.",
                       "An isolated NX probe exercised sqrt and radian trigonometry; propagation and precision of these actual head curves and associated axes remain unverified.",
                       "Regularized union includes touching pieces; NX tolerance and topology may reject or alter it. Check the native union and final retained solid on an authorized separate target.",
                       "No NX execution, preservation, persistent-ID, regeneration, parameter-edit or precision evidence is supplied; P3 bounds do not include native creation and measurement error."]}
