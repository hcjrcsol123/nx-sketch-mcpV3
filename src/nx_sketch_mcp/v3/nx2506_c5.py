"""C5 endpoint elimination and exact FIN restriction for NX expression planning.

No NX calls are made.  Formula text uses symbolic NX-style sin/cos and rounded
binary64 constants. Angle typing/conventions, native consumers, and the
numerical effect of those roundings remain native verification gates.
"""
from decimal import Decimal
from fractions import Fraction
import math

from .spline_restrict import restrict_bspline


class C5Error(ValueError):
    pass


def _fraction(pair):
    if not isinstance(pair, list) or len(pair) != 2 or any(type(x) is not int for x in pair) or pair[1] == 0:
        raise C5Error("invalid exact rational")
    return Fraction(*pair)


def _pair(value):
    return [value.numerator, value.denominator]


def _literal(value):
    """Shortest binary64 decimal expanded without exponent for NX formulas."""
    number = float(value)
    if not math.isfinite(number):
        raise C5Error("non-finite expression coefficient")
    return format(Decimal(repr(number)), "f")


def compile_c5(c5, final_plan):
    """Return typed expression nodes, exact matrices and parameter consumers.

    Both accepted P3 documents are explicit inputs.  The result is a planning
    artifact, never an authorization to create features or an edited-domain
    proof.  Formula coefficients and input angles are rounded for NX; exact
    coefficients and accepted P3 definitions remain alongside them.
    """
    if not isinstance(c5, dict) or c5.get("schema") != "p3-flank-parameter-expression/0.1":
        raise C5Error("expected the accepted C5 expression document")
    if not isinstance(final_plan, dict) or final_plan.get("schema") != "p3-final-mathematical-plan/1":
        raise C5Error("expected the P3 final plan")
    if c5.get("execution_approved") is not False or final_plan.get("execution_approved") is not False:
        raise C5Error("P3 execution boundary is invalid")
    try:
        templates = c5["templates"]
        final_templates = final_plan["construction"]["profiles"]["section6"]["templates"]
        params = {p["id"]: p for p in c5["parameters"]}
        if len(params) != len(c5["parameters"]) or set(templates) != {"F0002", "F0024"}:
            raise C5Error("C5 parameter or template identities invalid")
        final_parameters = {p["id"]: p for p in final_plan["parameters"]["c5"]}
        expected = set(params) - {"shaft_outer_diameter_mm"}
        if set(final_parameters) != expected or any(
            final_parameters[key].get(field) != params[key].get(field)
            for key in expected for field in ("unit", "value_exact", "definition", "preview")
        ) or any(final_parameters[key].get("source_classification") != params[key].get("classification")
                 for key in expected):
            raise C5Error("C5 parameter values or definitions differ from final plan")
        shaft = next(p for p in final_plan["parameters"]["regional"] if p["id"] == "shaft_outer_diameter_mm")
        if Fraction.from_float(float(shaft["value"])) != _fraction(params["shaft_outer_diameter_mm"]["value_exact"]):
            raise C5Error("C5 shared shaft diameter differs from final plan")
        if (final_plan["parameters"]["c5_placement_contract"] != c5["placement_contract"] or
                final_plan["parameters"]["c5_circle_expressions"] != c5["circle_expressions"]):
            raise C5Error("C5 placement or circle contract differs from final plan")
        nodes, consumers, mappings, side_results = [], {}, {}, {}

        def add(name, unit, formula, dependencies, **extra):
            if any(n["name"] == name for n in nodes):
                raise C5Error("duplicate expression name")
            node = {"name": name, "unit": unit, "formula": formula, "dependencies": list(dependencies), **extra}
            nodes.append(node)
            for dep in dependencies:
                consumers.setdefault(dep, []).append(name)
            return name

        def input_param(ident):
            p = params[ident]
            name = "v3_c5_" + ident.replace(".", "_")
            if "value_exact" in p:
                value = _fraction(p["value_exact"])
                exact = _pair(value)
            else:
                value = p["preview"]["value"]
                exact = None
            add(name, p["unit"], _literal(value), [], parameter_id=ident,
                classification=p["classification"], canonical_exact=exact,
                definition=p.get("definition"), accepted_preview=p.get("preview"))
            mappings[ident] = name
            return name

        shared = {key: input_param(key) for key in ("pitch_radius_mm", "root_radius_mm", "phase_rad", "shaft_outer_diameter_mm")}
        def linear(name, terms):
            """Emit a short length expression per product, followed by sums."""
            products = []
            for index, (coefficient, reference) in enumerate(terms):
                if coefficient == 0:
                    continue
                term = name + "_t" + str(index)
                add(term, "mm", "(" + _literal(coefficient) + ") * " + reference, [reference],
                    coefficient_exact=_pair(coefficient))
                products.append(term)
            if not products:
                return add(name, "mm", "0.0", [])
            # Pairwise additions stay well under the current 200-character limit.
            current = products[0]
            for index, term in enumerate(products[1:]):
                target = name if index == len(products)-2 else name + "_s" + str(index)
                current = add(target, "mm", current + " + " + term, [current, term])
            if len(products) == 1:
                current = add(name, "mm", current, [current])
            return current

        for side in ("F0002", "F0024"):
            template = templates[side]
            if template["basis"] != final_templates[side]["basis"] or template["poles"] != final_templates[side]["poles"]:
                raise C5Error("final plan and C5 template differ: " + side)
            basis = template["basis"]
            if basis["order"] != 4 or basis["num_poles"] != 7 or basis["rational"] is not False:
                raise C5Error("unsupported C5 spline basis")
            knots_exact = [_fraction(x) for x in basis["knots_exact"]]
            lo, hi = [_fraction(x) for x in basis["fin_interval_exact"]]
            knot_floats = [float(x) for x in knots_exact]
            if any(Fraction.from_float(x) != y for x, y in zip(knot_floats, knots_exact)) or Fraction.from_float(float(lo)) != lo or Fraction.from_float(float(hi)) != hi:
                raise C5Error("basis cannot be passed exactly to binary64 restriction")
            source = [[_fraction(v) for v in row] for row in template["source"]["source_local_poles_exact"]]
            restricted = restrict_bspline(order=4, knots=knot_floats, poles=[[float(x) for x in row] for row in source],
                                          a=float(lo), b=float(hi), rational=False)
            rows = [[_fraction(x) for x in row] for row in restricted["dependency_rows_exact"]]
            weights = [[_fraction(x) for x in row] for row in template["endpoint_weights_exact"]]
            if rows[0] != weights[0] or rows[-1] != weights[1]:
                raise C5Error("restricted endpoints disagree with C5 weights")
            a, b = weights
            determinant = a[1]*b[5] - a[5]*b[1]
            if determinant == 0 or determinant != _fraction(template["matrix_determinant_exact"]):
                raise C5Error("C5 endpoint system is singular or inconsistent")
            alphas = {role: input_param(side + ".alpha_" + role + "_rad") for role in ("root", "outer")}
            endpoints = {}
            for role in ("root", "outer"):
                radius = shared["root_radius_mm"] if role == "root" else shared["shaft_outer_diameter_mm"]
                scale = radius if role == "root" else "(" + radius + " / 2.0)"
                center = shared["pitch_radius_mm"] + " + " if role == "root" else ""
                for axis, trig in (("t", "sin"), ("r", "cos")):
                    name = "v3_c5_" + side + "_" + role + "_" + axis
                    formula = (center if axis == "r" else "") + scale + " * " + trig + "(" + alphas[role] + ")"
                    deps = [radius, alphas[role]] + ([shared["pitch_radius_mm"]] if role == "root" and axis == "r" else [])
                    endpoints[(role, axis)] = add(name, "mm", formula, deps, semantic="C5 circle endpoint")
            poles = {}
            for i in (0, 2, 3, 4, 6):
                for axis, column in (("t", 0), ("r", 1)):
                    if i in (0, 6):
                        name = "v3_c5_" + side + "_P" + str(i) + "_" + axis
                        poles[(i, axis)] = add(name, "mm", _literal(source[i][column]), [], classification="fixed_not_counted", canonical_exact=_pair(source[i][column]))
                    else:
                        poles[(i, axis)] = input_param(side + ".P" + str(i) + "." + axis + "_mm")
            # F0002 runs outer→root; F0024 runs root→outer.
            roles = ("outer", "root") if side == "F0002" else ("root", "outer")
            solve_rows = {}
            for index in (1, 5):
                ca, cb = (b[5]/determinant, -a[5]/determinant) if index == 1 else (-b[1]/determinant, a[1]/determinant)
                coeff = {j: -(ca*a[j] + cb*b[j]) for j in (0, 2, 3, 4, 6)}
                solve_rows[str(index)] = {"endpoint_a": _pair(ca), "endpoint_b": _pair(cb),
                                          "rhs_poles": {str(j): _pair(coeff[j]) for j in coeff}}
                for axis in ("t", "r"):
                    terms = [(ca, endpoints[(roles[0], axis)]), (cb, endpoints[(roles[1], axis)])]
                    terms += [(coeff[j], poles[(j, axis)]) for j in coeff]
                    poles[(index, axis)] = linear("v3_c5_" + side + "_P" + str(index) + "_" + axis, terms)
            restricted_names = []
            for i, row in enumerate(rows):
                restricted_names.append({axis: linear("v3_c5_" + side + "_R" + str(i) + "_" + axis,
                                                      [(coefficient, poles[(j, axis)]) for j, coefficient in enumerate(row)])
                                         for axis in ("t", "r")})
            normalized = [(Fraction.from_float(k) - lo)/(hi-lo) for k in restricted["knots"]]
            side_results[side] = {"order": 4, "interval_exact": [_pair(lo), _pair(hi)],
                                  "normalized_knots_exact": [_pair(k) for k in normalized],
                                  "normalized_knots_binary64": [float(k) for k in normalized],
                                  "restriction_matrix_exact": [[_pair(x) for x in row] for row in rows],
                                  "endpoint_weights_exact": template["endpoint_weights_exact"],
                                  "determinant_exact": _pair(determinant), "solve_coefficients_exact": solve_rows,
                                  "original_poles": [{axis: poles[(i, axis)] for axis in ("t", "r")} for i in range(7)],
                                  "endpoints": {role: {axis: endpoints[(role, axis)] for axis in ("t", "r")}
                                                for role in ("root", "outer")},
                                  "restricted_poles": restricted_names}
        # The final-plan member frame is ABS=(0,-71,0)+t*e_t+r*e_r.
        # Keep phase and pi symbolically meaningful in the contract; the decimal
        # angle offsets and trig formulas are only a candidate NX realization.
        graph_nodes = {node["id"]: node for node in final_plan["construction"]["nodes"]}
        phase_exact = _fraction(params["phase_rad"]["value_exact"])
        world_points = {}
        y_ref = add("v3_c5_section_y", "mm", "-71.0", [], classification="fixed_auxiliary")
        for member in range(22):
            frame = graph_nodes["member_%02d_straight_tool" % member]["frame"]
            theta = float(phase_exact) + member * (2 * math.pi / 22)
            expected_t = [math.cos(theta), 0.0, -math.sin(theta)]
            expected_r = [math.sin(theta), 0.0, math.cos(theta)]
            if (frame["origin_mm"] != [0, -71, 0] or len(frame["e_t"]) != 3 or len(frame["e_r"]) != 3 or
                    any(abs(a-b) > 1e-12 for a, b in zip(frame["e_t"], expected_t)) or
                    any(abs(a-b) > 1e-12 for a, b in zip(frame["e_r"], expected_r))):
                raise C5Error("member frame differs from C5 placement contract")
            theta_name = "v3_c5_m%02d_theta" % member
            add(theta_name, "rad", shared["phase_rad"] + " + " + _literal(member * (2 * math.pi / 22)),
                [shared["phase_rad"]], exact_semantic="phase_rad + member_index * 2*pi/22")
            side_points = {}
            for side in ("F0002", "F0024"):
                points = []
                for i, pole in enumerate(side_results[side]["restricted_poles"]):
                    base = "v3_c5_m%02d_%s_R%d" % (member, side, i)
                    x = add(base + "_x", "mm", pole["t"] + " * cos(" + theta_name + ") + " + pole["r"] + " * sin(" + theta_name + ")",
                            [pole["t"], pole["r"], theta_name])
                    z = add(base + "_z", "mm", "-" + pole["t"] + " * sin(" + theta_name + ") + " + pole["r"] + " * cos(" + theta_name + ")",
                            [pole["t"], pole["r"], theta_name])
                    points.append({"x": x, "y": y_ref, "z": z})
                side_points[side] = points
            world_points[str(member)] = side_points
        return {"schema": "nx2506-c5-expression-graph/1", "nodes": nodes, "parameter_expressions": mappings,
                "consumers": consumers, "templates": side_results, "world_points": world_points,
                "placement_contract": c5["placement_contract"], "member_placements": c5["member_placements"],
                "execution_approved": False, "native_binding_verified": False,
                "limitations": ["NX angle units, sin/cos semantics and world-point consumers are not yet verified",
                                "expression constants and normalized knots are rounded for NX; native error remains unbounded",
                                "default source correspondence and P3 guards do not automatically apply to edits"]}
    except (KeyError, TypeError, ValueError, ZeroDivisionError, StopIteration) as exc:
        if isinstance(exc, C5Error):
            raise
        raise C5Error("incomplete or inconsistent C5 input") from exc


def compile_c5_member(c5, final_plan, member_index=0, existing_expressions=()):
    """Lower one C5 section to candidate associative native expression steps.

    Numeric profile previews accompany world-coordinate expression references.
    Existing C5 expressions must be supplied as name-to-definition mappings
    with matching formula and unit, except the coordinated shaft input may be
    named alone. The caller must establish those definitions in the live part.
    The result does not authorize execution or establish native propagation.
    """
    import json
    from copy import deepcopy
    from .nx2506_composition import compile_stock_and_members_preview

    if type(member_index) is not int or not 0 <= member_index < 22:
        raise C5Error("member index must be from 0 to 21")
    definitions = existing_expressions if isinstance(existing_expressions, dict) else None
    existing = set(existing_expressions)
    shaft_name = "v3_c5_shaft_outer_diameter_mm"
    if definitions is None and not existing.issubset({shaft_name}):
        raise C5Error("reused C5 expressions require their canonical formula and unit")
    graph = compile_c5(c5, final_plan)
    all_nodes = {node["name"]: deepcopy(node) for node in graph["nodes"]}
    added = []

    def add(name, formula, deps, unit="mm"):
        if name in all_nodes:
            raise C5Error("duplicate C5 closure expression")
        node = {"name": name, "formula": formula, "unit": unit, "dependencies": list(deps)}
        all_nodes[name] = node
        added.append(node)
        return name

    section = final_plan["construction"]["profiles"]["section6"]
    fixed = {p["id"]: p for p in final_plan["parameters"]["fixed_auxiliaries"]}
    cap_value = fixed["auxiliary_cap_radius"]["value"]
    if section["edges"][2]["radius_mm"] != cap_value or fixed["auxiliary_cap_radius"]["unit"] != "mm":
        raise C5Error("cap radius differs from the accepted auxiliary")
    cap_radius = add("v3_c5_cap_radius", _literal(cap_value), [])
    pitch = graph["parameter_expressions"]["pitch_radius_mm"]
    rho = graph["parameter_expressions"]["root_radius_mm"]
    shaft = graph["parameter_expressions"]["shaft_outer_diameter_mm"]
    theta = "v3_c5_m%02d_theta" % member_index
    y_ref = "v3_c5_section_y"
    e = {side: graph["templates"][side]["endpoints"] for side in ("F0002", "F0024")}
    local = {}
    for side in ("F0002", "F0024"):
        outer = e[side]["outer"]
        local[side + "_cap"] = {axis: add("v3_c5_" + side + "_cap_" + axis,
            outer[axis] + " * " + cap_radius + " / (" + shaft + " / 2.0)",
            [outer[axis], cap_radius, shaft]) for axis in ("t", "r")}
        local[side + "_root"] = e[side]["root"]
        local[side + "_outer"] = outer

    def midpoint(prefix, left, right, center_r, radius):
        sum_t = add(prefix + "_sum_t", left["t"] + " + " + right["t"], [left["t"], right["t"]])
        if center_r:
            sum_r = add(prefix + "_sum_r", left["r"] + " + " + right["r"] + " - 2.0 * " + center_r,
                        [left["r"], right["r"], center_r])
        else:
            sum_r = add(prefix + "_sum_r", left["r"] + " + " + right["r"], [left["r"], right["r"]])
        norm = add(prefix + "_norm", "sqrt(" + sum_t + " * " + sum_t + " + " + sum_r + " * " + sum_r + ")",
                   [sum_t, sum_r])
        t = add(prefix + "_t", radius + " * " + sum_t + " / " + norm, [radius, sum_t, norm])
        r_formula = (center_r + " + " if center_r else "") + radius + " * " + sum_r + " / " + norm
        r = add(prefix + "_r", r_formula, ([center_r] if center_r else []) + [radius, sum_r, norm])
        return {"t": t, "r": r}

    local["cap_mid"] = midpoint("v3_c5_cap_mid", local["F0024_cap"], local["F0002_cap"], None, cap_radius)
    local["root_mid"] = midpoint("v3_c5_root_mid", local["F0002_root"], local["F0024_root"], pitch, rho)

    def world(label, point):
        base = "v3_c5_m%02d_%s" % (member_index, label)
        t, r = point["t"], point["r"]
        x = add(base + "_x", t + " * cos(" + theta + ") + " + r + " * sin(" + theta + ")", [t, r, theta])
        z = add(base + "_z", "-" + t + " * sin(" + theta + ") + " + r + " * cos(" + theta + ")", [t, r, theta])
        return [x, y_ref, z]
    world_closure = {label: world(label, point) for label, point in local.items()}
    member_prefix = "v3_c5_m%02d" % member_index
    roll_radius = add("v3_c5_roll_radius", _literal(fixed["roll_axis_radius"]["value"]), [])
    unit_length = add("v3_c5_axis_unit_length", "1", [])
    roll_x = add(member_prefix + "_roll_axis_x", roll_radius + "*sin(" + theta + ")", [roll_radius, theta])
    roll_z = add(member_prefix + "_roll_axis_z", roll_radius + "*cos(" + theta + ")", [roll_radius, theta])
    axis_end_x = add(member_prefix + "_roll_axis_end_x", roll_x + "+" + unit_length + "*cos(" + theta + ")",
                     [roll_x, unit_length, theta])
    axis_end_z = add(member_prefix + "_roll_axis_end_z", roll_z + "-" + unit_length + "*sin(" + theta + ")",
                     [roll_z, unit_length, theta])
    has_stock_y4 = "v3_stock_Y4" in existing
    if definitions is not None:
        existing.intersection_update(all_nodes)
        for name in existing:
            definition = definitions[name]
            expected = all_nodes[name]
            if (not isinstance(definition, dict) or definition.get("formula") != expected["formula"]
                    or definition.get("unit") != expected["unit"]):
                raise C5Error("reused C5 expression definition differs: " + str(name))
    spline_points = graph["world_points"][str(member_index)]
    preview = compile_stock_and_members_preview(final_plan)
    profile_steps = deepcopy(preview["groups"][member_index + 1][:2])
    for step in profile_steps:
        edges = step["edges"]
        edges[0]["pole_expressions"] = [[p["x"], p["y"], p["z"]] for p in spline_points["F0024"]]
        edges[1]["point_expressions"] = [world_closure["F0024_outer"], world_closure["F0024_cap"]]
        edges[2]["point_expressions"] = [world_closure["F0024_cap"], world_closure["cap_mid"], world_closure["F0002_cap"]]
        edges[3]["point_expressions"] = [world_closure["F0002_cap"], world_closure["F0002_outer"]]
        edges[4]["pole_expressions"] = [[p["x"], p["y"], p["z"]] for p in spline_points["F0002"]]
        edges[5]["point_expressions"] = [world_closure["F0002_root"], world_closure["root_mid"], world_closure["F0024_root"]]

    profile_steps[1]["axis_points_expressions"] = [[roll_x, y_ref, roll_z], [axis_end_x, y_ref, axis_end_z]]
    if has_stock_y4:
        profile_steps[0]["start_formula"] = "v3_stock_Y4 - " + y_ref

    # Emit only this member's transitive expressions. Dependencies on the
    # explicitly supplied shared stock expression are resolved by the caller.
    targets = [name for step in profile_steps[:1] for edge in step["edges"]
               for points in (edge.get("point_expressions", []), edge.get("pole_expressions", []))
               for point in points for name in point]
    targets.extend(name for point in profile_steps[1]["axis_points_expressions"] for name in point)
    needed = set()
    def visit(name):
        if name in existing or name in needed:
            return
        if name not in all_nodes:
            raise C5Error("unknown C5 expression dependency")
        for dep in all_nodes[name]["dependencies"]:
            visit(dep)
        needed.add(name)
    for target in targets:
        visit(target)
    ordered = [node for node in graph["nodes"] + added if node["name"] in needed]
    steps = [{"id": node["name"], "kind": "expression", "name": node["name"],
              "unit": node["unit"], "formula": node["formula"]} for node in ordered]
    groups, group = [], []
    for step in steps:
        trial = group + [step]
        if len(json.dumps(trial, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf8")) > 12000:
            if not group:
                raise C5Error("C5 expression exceeds request size")
            groups.append(group)
            group = [step]
        else:
            group = trial
    if group:
        groups.append(group)
    return {"schema": "nx2506-c5-member-preview/1", "member_index": member_index,
            "expression_groups": groups, "profile_steps": profile_steps,
            "expression_graph": ordered, "existing_expressions": sorted(existing),
            "canonical_matrices": graph["templates"], "execution_approved": False,
            "limitations": graph["limitations"] + [
                "centered-circle midpoint normalization and branch validity must be checked for each edit",
                "native roll axis association and stock start formula require regeneration verification",
                "native closed profile, parameter propagation, solver, regeneration and persistence remain unverified"]}
