"""Compile the P3 mathematical construction into a non-executable P4 manifest.

This is a transport-independent planning artifact.  Native feature mappings,
parameter consumers and their preservation evidence are separate P4 gates; a
mathematical plan alone cannot authorize a model mutation.
"""
from copy import deepcopy


class CompositionError(ValueError):
    """The mathematical construction cannot be composed without ambiguity."""


_OPERATIONS = frozenset({
    "revolve_closed_meridian", "bounded_cylinder", "subtract", "extrude_profile",
    "revolve_profile", "intersect", "union", "cone_carrier", "sphere_carrier",
    "torus_carrier", "tangent_torus_carrier", "bounded_set", "regularized_union",
    "regularized_difference",
})
_BODY_INPUTS = {
    "subtract": ("target", "tool"), "regularized_difference": ("target", "tool"),
    "intersect": ("left", "right"), "union": ("left", "right"),
}


def compile_composition(plan):
    """Preserve the complete mathematical graph and its parameter context.

    Result is deliberately not an NX request and must not be submitted to a
    prepare or execute endpoint.  It records outstanding implementation gates,
    not claims of native coverage or permission to execute.
    """
    if not isinstance(plan, dict) or plan.get("schema") != "p3-final-mathematical-plan/1":
        raise CompositionError("expected a P3 final mathematical plan")
    if plan.get("p3_ready") is not True or plan.get("execution_approved") is not False:
        raise CompositionError("P3 readiness or execution boundary is invalid")
    try:
        construction = plan["construction"]
        nodes = construction["nodes"]
        profiles = construction["profiles"]
        parameters = plan["parameters"]
        bindings = plan["face_construction_bindings"]
        coverage = plan["coverage"]
        if not isinstance(nodes, list) or not nodes or not isinstance(profiles, dict):
            raise CompositionError("construction graph or profiles missing")
        records = {}
        for node in nodes:
            ident = node["id"]
            if not isinstance(ident, str) or not ident or ident in records:
                raise CompositionError("empty or duplicate node identity")
            if node["operation"] not in _OPERATIONS:
                raise CompositionError("unsupported mathematical operation: " + str(node["operation"]))
            records[ident] = node
        param_records = parameters["regional"] + parameters["c5"]
        parameter_ids = [p["id"] for p in param_records]
        if any(not isinstance(i, str) or not i for i in parameter_ids) or len(set(parameter_ids)) != len(parameter_ids):
            raise CompositionError("empty or duplicate parameter identity")
        known_parameters = set(parameter_ids)
        for node in nodes:
            deps = node["depends_on"]
            if not isinstance(deps, list) or len(set(deps)) != len(deps) or any(d not in records for d in deps):
                raise CompositionError("invalid node dependencies: " + node["id"])
            for field in _BODY_INPUTS.get(node["operation"], ()):
                if node[field] not in deps:
                    raise CompositionError("body input is not an explicit dependency: " + node["id"])
            if "profile" in node and node["profile"] not in profiles:
                raise CompositionError("unknown profile: " + node["id"])
            for field in ("parameter_dependencies", "depends_on_parameters"):
                if field in node and (not isinstance(node[field], list) or any(p not in known_parameters for p in node[field])):
                    raise CompositionError("unknown parameter dependency: " + node["id"])
        faces = [item["source_face"] for item in bindings]
        if len(faces) != len(set(faces)) or len(faces) != coverage["source_faces"] or len(faces) != coverage["unique_source_faces"]:
            raise CompositionError("source face coverage is incomplete or duplicated")
        if any(not item["construction_nodes"] or any(i not in records for i in item["construction_nodes"]) for item in bindings):
            raise CompositionError("source face references an unknown node")
        # Stable topological order retains plan order among available nodes.
        remaining = list(nodes)
        order, complete = [], set()
        while remaining:
            ready = [n for n in remaining if set(n["depends_on"]).issubset(complete)]
            if not ready:
                raise CompositionError("cyclic construction dependencies")
            for node in ready:
                order.append(node["id"])
                complete.add(node["id"])
                remaining.remove(node)
        return deepcopy({
            "schema": "nx2506-composition-manifest/1",
            "p1_snapshot_id": plan["p1_snapshot_id"], "unit": plan["unit"], "frame": plan["frame"],
            "node_order": order, "construction": construction, "parameters": parameters,
            "face_construction_bindings": bindings, "coverage": coverage,
            "shared_interfaces": plan["shared_interfaces"],
            "edit_domain_contract": plan["edit_domain_contract"], "guards_and_events": plan["guards_and_events"],
            "execution_approved": False,
            "native_gates": ["operation and bounded-set lowering", "native parameter and constraint consumers",
                             "boolean and non-target preservation", "fresh readback and permitted-edit regeneration"],
        })
    except (KeyError, TypeError) as exc:
        raise CompositionError("incomplete or malformed P3 construction") from exc


def execute_steps(executor, steps):
    """Run one explicitly selected, bounded native transaction on a live Executor.

    This low-level entry does not approve or execute the mathematical manifest.
    Every failure permanently stops this executor, including incomplete fresh reads.
    """
    from .nx2506_executor import ExecutionStopped
    try:
        if executor.stopped or not isinstance(steps, list) or not steps:
            raise ExecutionStopped("a live executor and explicit steps are required")
        result = executor._transaction("nx_prepare_v3_composition", {"steps": deepcopy(steps)})
        evidence = result.get("evidence")
        outputs = evidence.get("outputs") if isinstance(evidence, dict) else None
        ids = [step.get("id") for step in steps if isinstance(step, dict)]
        if (len(ids) != len(steps) or len(set(ids)) != len(ids) or not isinstance(outputs, dict)
                or set(outputs) != set(ids) or evidence.get("readback_verified") is not True
                or evidence.get("preservation_verified") is not True):
            raise ExecutionStopped("composition execution evidence is incomplete")
        for step in steps:
            item = outputs[step["id"]]
            if not isinstance(item, dict):
                raise ExecutionStopped("composition output evidence is malformed")
            if step.get("kind") == "expression":
                import math
                value = item.get("value")
                if item.get("name") != step.get("name") or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ExecutionStopped("composition expression output is missing")
            elif (not isinstance(item.get("feature_id"), str) or not item["feature_id"]
                  or not isinstance(item.get("body_ids"), list)
                  or any(not isinstance(i, str) or not i for i in item["body_ids"])):
                raise ExecutionStopped("composition native feature output is missing")
        checks = executor.last_verification.get("checks", {})
        for key in ("bindings", "geometry", "history", "non_target_preservation"):
            check = checks.get(key) if isinstance(checks, dict) else None
            proof = check.get("evidence") if isinstance(check, dict) else None
            if (not isinstance(check, dict) or check.get("status") != "VERIFIED" or not isinstance(proof, dict)
                    or proof.get("matches_execute") is not True or proof.get("logical_feature_ids_verified") is not True):
                raise ExecutionStopped("fresh composition verification is incomplete")
        return {"revision_id": executor.revision, "result": result,
                "verification": deepcopy(executor.last_verification)}
    except Exception as exc:
        executor.stopped = True
        if isinstance(exc, ExecutionStopped):
            raise
        raise ExecutionStopped("composition stopped; do not replay uncertain operations") from exc


def compile_stock_and_members_preview(plan):
    """Lower stock, slot and 22 member tools to default-value native steps.

    These steps are a geometry preview only.  In particular, their coordinates
    are not native Driving bindings, and this function does not authorize use.
    All roll intersections precede consumption of the original stock.
    """
    import math
    from .spline_restrict import restrict_bspline

    manifest = compile_composition(plan)
    profiles = manifest["construction"]["profiles"]
    nodes = {n["id"]: n for n in manifest["construction"]["nodes"]}
    stock = profiles["stock_profile"]
    vertices = {v["id"]: [v["y_mm"], v["radius_mm"]] for v in stock["vertices"]}
    edges = []
    for curve in stock["curves"]:
        a, b = vertices[curve["start"]], vertices[curve["end"]]
        if curve["kind"] == "line":
            edges.append({"kind": "line", "start": a, "end": b})
        elif curve["kind"] == "circular_arc":
            theta = curve["start_rad"] + curve["sweep_rad"] / 2
            cy, cr = curve["center_y_r_mm"]
            mid = [cy + curve["radius_mm"] * math.cos(theta), cr + curve["radius_mm"] * math.sin(theta)]
            edges.append({"kind": "arc", "start": a, "mid": mid, "end": b})
        else:
            raise CompositionError("unsupported stock curve")
    frame = {"origin": [0, 0, 0], "x_axis": [0, 1, 0], "y_axis": [1, 0, 0]}
    stock_step = {"id": "stock_revolve", "kind": "revolve", "frame": frame, "edges": edges,
                  "axis_point": [0, 0, 0], "axis_direction": [0, 1, 0], "start_degrees": 0, "end_degrees": 360}

    section = profiles["section6"]
    splines, endpoints = {}, {}
    for name, template in section["templates"].items():
        basis = template["basis"]
        knot_values = [a / b for a, b in basis["knots_exact"]]
        lo, hi = [a / b for a, b in basis["fin_interval_exact"]]
        poles = [[p["t_mm"]["value"], p["r_mm"]["value"]] for p in template["poles"]]
        restricted = restrict_bspline(order=basis["order"], knots=knot_values, poles=poles,
                                      a=lo, b=hi, rational=basis["rational"])
        # Studio Spline retained the clamped FIN basis in NX2506, including
        # the very short end span that UF curve creation rejected.
        knots = [(k - lo) / (hi - lo) for k in restricted["knots"]]
        splines[name] = {"kind": "spline", "method": "studio", "order": basis["order"], "knots": knots,
                         "poles": [[*p, 1.0] for p in restricted["poles"]]}
        endpoints[name] = restricted["poles"][0], restricted["poles"][-1]
    root24, outer24 = endpoints["F0024"]
    outer2, root2 = endpoints["F0002"]
    cap_radius = section["edges"][2]["radius_mm"]
    def cap(point):
        radius = math.hypot(*point)
        return [x * cap_radius / radius for x in point]
    cap24, cap2 = cap(outer24), cap(outer2)
    def arc_mid(a, b, center, lower=False):
        a0 = math.atan2(a[1] - center[1], a[0] - center[0])
        a1 = math.atan2(b[1] - center[1], b[0] - center[0])
        delta = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        radius = math.hypot(a[0] - center[0], a[1] - center[1])
        def point(angle): return [center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle)]
        mid = point(a0 + delta / 2)
        other = point(a0 + (delta - math.copysign(2 * math.pi, delta)) / 2)
        return other if lower and other[1] < mid[1] else mid
    root_center = section["edges"][5]["center_t_r_mm"]
    profile_edges = [splines["F0024"], {"kind": "line", "start": outer24, "end": cap24},
                     {"kind": "arc", "start": cap24, "mid": arc_mid(cap24, cap2, [0, 0]), "end": cap2},
                     {"kind": "line", "start": cap2, "end": outer2}, splines["F0002"],
                     {"kind": "arc", "start": root2, "mid": arc_mid(root2, root24, root_center, lower=True), "end": root24}]
    groups = [[stock_step]]
    for i in range(22):
        prefix = "member_%02d" % i
        straight = nodes[prefix + "_straight_tool"]
        roll = nodes[prefix + "_roll_tool"]
        placement = straight["frame"]
        member_frame = {"origin": placement["origin_mm"], "x_axis": placement["e_t"], "y_axis": placement["e_r"]}
        groups.append([
            {"id": straight["id"], "kind": "extrude", "frame": member_frame, "edges": profile_edges,
             "direction": [0, 1, 0], "start": straight["y_limits_mm"][0] - member_frame["origin"][1],
             "end": straight["y_limits_mm"][1] - member_frame["origin"][1]},
            {"id": roll["id"], "kind": "revolve", "frame": member_frame, "edges": profile_edges,
             "axis_point": roll["axis_point_mm"], "axis_direction": roll["axis_direction"],
             "start_degrees": 0, "end_degrees": math.degrees(roll["angle_rad"])},
            {"id": prefix + "_roll_stock_intersection", "kind": "boolean", "operation": "intersect",
             "target": roll["id"], "tools": ["stock_revolve"], "retain_tools": True},
            {"id": prefix + "_combined_tool", "kind": "boolean", "operation": "unite",
             "target": straight["id"], "tools": [prefix + "_roll_stock_intersection"], "retain_tools": False},
        ])
    slot = nodes["rear_slot_tool"]
    regional = {p["id"]: p for p in manifest["parameters"]["regional"]}
    width, radius = regional["slot.width"]["value"], regional["slot.radius"]["value"]
    if width <= 0 or radius <= 0 or slot["x_limits_mm"] != [-width / 2, width / 2] or slot["radius_mm"] != radius:
        raise CompositionError("slot defaults differ from their width/radius parameters")
    groups.append([
        {"id": "slot.width.expression", "kind": "expression", "name": "v3_slot_width", "formula": str(width)},
        {"id": "slot.radius.expression", "kind": "expression", "name": "v3_slot_radius", "formula": str(radius)},
        {"id": "rear_slot_tool", "kind": "extrude",
         "frame": {"origin": slot["axis_point_mm"], "x_axis": [0, 1, 0], "y_axis": [0, 0, 1]},
         "edges": [{"kind": "circle", "center": [0, 0], "radius": radius, "radius_expression": "v3_slot_radius"}],
         "direction": slot["axis"], "start": slot["x_limits_mm"][0], "end": slot["x_limits_mm"][1],
         "start_formula": "-v3_slot_width / 2", "end_formula": "v3_slot_width / 2"},
        {"id": "stock_with_rear_slot", "kind": "boolean", "operation": "subtract", "target": "stock_revolve",
         "tools": ["rear_slot_tool"], "retain_tools": False},
    ])
    for i in range(22):
        prefix = "member_%02d" % i
        target = "stock_with_rear_slot" if i == 0 else "member_%02d_result" % (i - 1)
        groups.append([{"id": prefix + "_result", "kind": "boolean", "operation": "subtract", "target": target,
                        "tools": [prefix + "_combined_tool"], "retain_tools": False}])
    return deepcopy({"groups": groups, "output_id": "member_21_result", "execution_approved": False,
                     "limitations": ["default geometry preview only; Driving parameter propagation unbound",
                                     "spline normalization, feature topology and native representation error require verification",
                                     "whole-plan execution and edits remain gated"]})


def _pack_steps(steps):
    import json

    groups, group = [], []
    for step in steps:
        trial = group + [step]
        if len(json.dumps(trial, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf8")) > 12000:
            if not group:
                raise CompositionError("native step exceeds request size")
            groups.append(group)
            group = [step]
        else:
            group = trial
    if group:
        groups.append(group)
    return groups


def _head_fixed_steps(steps):
    for original in steps:
        if original["kind"] == "expression":
            continue
        step = deepcopy(original)
        for key in ("axis_points_expressions", "start_formula", "end_formula"):
            step.pop(key, None)
        for edge in step.get("edges", ()):
            edge.pop("point_expressions", None)
        yield step


def compile_native_preview(plan):
    """Compile the default construction independently of native edit bindings."""
    from .nx2506_head import compile_head

    manifest = compile_composition(plan)
    body = compile_stock_and_members_preview(plan)
    head = compile_head(plan)
    groups = body["groups"] + _pack_steps(_head_fixed_steps(head["steps"]))
    return _preview_result(manifest, body, head, groups, "nx2506-native-preview/1")


def _slot_with_axis_expressions(group):
    width, radius, extrude, subtract = deepcopy(group)
    center_y, center_z = extrude["frame"]["origin"][1:]
    r = extrude["edges"][0]["radius"]
    formulas = {
        "axis_y": repr(center_y), "axis_z": repr(center_z),
        "high_y": "v3_slot_axis_y+v3_slot_radius", "low_y": "v3_slot_axis_y-v3_slot_radius",
        "high_z": "v3_slot_axis_z+v3_slot_radius", "low_z": "v3_slot_axis_z-v3_slot_radius",
    }
    expressions = [
        {"id": "slot.expression." + name, "kind": "expression", "name": "v3_slot_" + name,
         "formula": rhs, "unit": "mm"}
        for name, rhs in formulas.items()
    ]
    zero = "v3_stock_zero"
    positive_y = [zero, "v3_slot_high_y", "v3_slot_axis_z"]
    negative_y = [zero, "v3_slot_low_y", "v3_slot_axis_z"]
    positive_z = [zero, "v3_slot_axis_y", "v3_slot_high_z"]
    negative_z = [zero, "v3_slot_axis_y", "v3_slot_low_z"]
    extrude["edges"] = [
        {"kind": "arc", "start": [r, 0], "mid": [0, r], "end": [-r, 0],
         "point_expressions": [positive_y, positive_z, negative_y]},
        {"kind": "arc", "start": [-r, 0], "mid": [0, -r], "end": [r, 0],
         "point_expressions": [negative_y, negative_z, positive_y]},
    ]
    return [width, radius, *expressions, extrude, subtract]


def compile_associative_preview(plan):
    """Lower the real P3 graph and shared expressions into candidate NX transactions.

    The caller can inspect every native body dependency and coordinate formula.
    The manifest remains gated on native composition, admissible edits and
    representation/Boolean evidence.
    """
    from .nx2506_c5 import compile_c5_member
    from .nx2506_head import compile_head
    from .nx2506_stock import build_stock_steps

    manifest = compile_composition(plan)
    body = compile_stock_and_members_preview(plan)
    head = compile_head(plan)
    stock = build_stock_steps(plan)
    groups = _pack_steps(stock["steps"][:-1]) + [stock["steps"][-1:]]
    existing = {step["name"]: {"formula": step["formula"], "unit": step["unit"]} for step in stock["steps"][:-1]}
    c5 = plan["parameters"]["canonical_definitions"]["c5"]
    for index, group in enumerate(body["groups"][1:23]):
        bound = compile_c5_member(c5, plan, index, existing)
        groups.extend(bound["expression_groups"])
        for expression in bound["expression_graph"]:
            existing[expression["name"]] = {"formula": expression["formula"], "unit": expression["unit"]}
        groups.append(bound["profile_steps"] + group[2:])
    groups.append(_slot_with_axis_expressions(body["groups"][23]))
    groups.extend(body["groups"][24:])
    groups.extend(_pack_steps(head["steps"]))
    result = _preview_result(manifest, body, head, groups, "nx2506-associative-preview/1")
    from .design_guidance import build_design_guidance, reviewed_layout_evidence
    result["design_guidance"] = build_design_guidance(plan, groups, layout_evidence=reviewed_layout_evidence())
    result["stock_expression_trace"] = stock["trace"]
    result["limitations"] = [
        "The full native construction and edited-domain validity are unverified.",
        "Native representation and Boolean error must fit the P3 residual budget.",
    ]
    return result


def _preview_parameter_units(manifest):
    """Correct the documented historical slot label in a preview copy only."""
    import math
    import re

    if manifest["unit"] != "mm":
        raise CompositionError("preview requires millimetre part coordinates")
    regional = manifest["parameters"]["regional"]
    by_id = {item["id"]: item for item in regional}
    for ident in ("slot.axis_y", "slot.axis_z"):
        if ident not in by_id:
            raise CompositionError("missing rear slot position: " + ident)
    slot = next((node for node in manifest["construction"]["nodes"] if node["id"] == "rear_slot_tool"), None)
    if (not isinstance(slot, dict) or slot.get("operation") != "bounded_cylinder"
            or slot.get("axis") != [1, 0, 0] or any(isinstance(v, bool) for v in slot.get("axis", []))
            or not {"slot.axis_y", "slot.axis_z"}.issubset(slot.get("parameter_dependencies", []))):
        raise CompositionError("rear slot position role is not established")
    point = slot.get("axis_point_mm")
    def finite_number(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return math.isfinite(value)
        except OverflowError:
            return False
    if (not isinstance(point, list) or len(point) != 3 or not all(finite_number(v) for v in point)
            or any(not finite_number(by_id[ident].get("value")) or by_id[ident]["value"] != point[index]
                   for ident, index in (("slot.axis_y", 1), ("slot.axis_z", 2)))):
        raise CompositionError("rear slot position differs from its parameter")
    if by_id["slot.axis_y"].get("unit") != "mm":
        raise CompositionError("conflicting unit for slot.axis_y")
    for item in regional:
        if re.fullmatch(r"head\.sector\.\d+\.axis_[xz]", item["id"]) and item.get("unit") != "1":
            raise CompositionError("conflicting unit for head sector direction: " + item["id"])
    slot_z = by_id["slot.axis_z"]
    source_unit = slot_z.get("unit")
    if source_unit not in ("1", "mm"):
        raise CompositionError("conflicting unit for slot.axis_z")
    if source_unit == "1":
        slot_z["unit"] = "mm"
        manifest["parameter_unit_corrections"] = [{
            "parameter_id": "slot.axis_z", "source_unit": "1", "preview_unit": "mm",
            "basis": "rear_slot_tool.axis_point_mm[2] is a position in part coordinates",
        }]
    return manifest


def _preview_result(manifest, body, head, groups, schema):
    ids = [step["id"] for group in groups for step in group]
    if len(ids) != len(set(ids)):
        raise CompositionError("duplicate lowered step identity")
    return {"schema": schema, "manifest": _preview_parameter_units(manifest), "groups": groups,
            "output_id": head["output_id"], "head_trace": head["trace"],
            "limitations": body["limitations"] + head["limitations"], "execution_approved": False}
