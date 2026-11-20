"""Bounded Y/r stock profile planning from typed, evidence-scoped proposals.

Only monotone-y exterior chains with explicit radial and axis closures are
supported. Source matching tolerances do not prove source trim or shape. This
module does not create an IR, run NX, or approve a revolved solid.
"""
from copy import deepcopy
import json
import math
from pathlib import Path, PurePosixPath

from .regions.common import normalize_snapshot
from .regions.detail_common import normalize_detail_snapshot


class StockProfileError(ValueError):
    """The bounded profile or its source evidence cannot be established."""


def _fail(message):
    raise StockProfileError("stock profile: " + message)


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail("finite numeric value required")
    try:
        if not math.isfinite(value):
            _fail("finite numeric value required")
    except OverflowError:
        _fail("finite numeric value required")
    return float(value)


def _vector(value, size):
    if not isinstance(value, list) or len(value) != size:
        _fail("invalid vector")
    return [_num(x) for x in value]


def _axis(origin, direction, linear, angular):
    x, _, z = _vector(origin, 3)
    dx, dy, dz = _vector(direction, 3)
    norm = math.hypot(dx, dy, dz)
    if not math.isfinite(norm) or norm == 0 or math.hypot(x, z) > linear or math.atan2(math.hypot(dx, dz), abs(dy)) > angular:
        _fail("source axis is not the proposed Y axis")


def _path(root, name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        _fail("invalid evidence path")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        _fail("evidence path must be repository relative")
    try:
        result = root.joinpath(*path.parts).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise StockProfileError("stock profile: missing evidence") from exc
    if not result.is_relative_to(root) or not result.is_file():
        _fail("evidence must be a repository file")
    return result


def _read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail("duplicate JSON key")
            result[key] = value
        return result
    def constant(value):
        _fail("non-finite JSON: " + value)
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StockProfileError("stock profile: unreadable evidence") from exc


def _torus(inventory, label, linear, angular):
    if not isinstance(inventory, dict) or inventory.get("unit") != "mm":
        _fail("torus detail requires explicit millimeter units")
    matches = [(fid, detail) for fid, detail in inventory["detail_faces"].items() if detail.get("label") == label]
    if len(matches) != 1:
        _fail("torus selection missing or ambiguous")
    fid, detail = matches[0]
    face = inventory["faces"][fid]
    diagnostic = detail["diagnostic"]
    topology = diagnostic.get("topology")
    if (face.get("surface_type") != "SurfaceOfRevolution" or face.get("native_face_data", {}).get("uf_type") != 19
            or diagnostic.get("edge_coverage_complete") is not True or not isinstance(topology, dict)
            or topology.get("geometry_rc") != 0 or topology.get("geometry_free_rc") != 0):
        _fail("torus detail does not establish the requested carrier")
    g = topology.get("geometry")
    if not isinstance(g, dict) or g.get("type") != 204:
        _fail("requested detail is not a torus")
    center, axis = _vector(g.get("center"), 3), _vector(g.get("axis"), 3)
    _axis(center, axis, linear, angular)
    major, minor = _num(g.get("major_radius")), _num(g.get("minor_radius"))
    if minor <= 0 or major <= minor or not all(math.isfinite(x) for x in (major + minor, center[1] + minor, center[1] - minor)):
        _fail("unsupported spindle or degenerate torus")
    return {"snapshot_id": inventory["snapshot_id"], "snapshot_face_id": fid,
            "center_y": center[1], "major_radius": major, "minor_radius": minor,
            "native_center": center, "native_axis": axis,
            "frame_assumption": "UF_BREP native frame coincides with ABS Y/r; unverified"}


def _arc_at(y, carrier, linear):
    cy, major, minor, branch = carrier["center_y"], carrier["major_radius"], carrier["minor_radius"], carrier["branch"]
    excess = abs(y - cy) - minor
    if excess > linear:
        _fail("arc endpoint outside carrier")
    adjusted_y = min(max(y, cy - minor), cy + minor)
    ratio = (adjusted_y - cy) / minor
    return [adjusted_y, major + branch * minor * math.sqrt(max(0.0, 1.0 - ratio * ratio))]


def _arc_segment(start, end, carrier, epsilon):
    cy, major, minor, branch = carrier["center_y"], carrier["major_radius"], carrier["minor_radius"], carrier["branch"]
    for point in (start, end):
        expected = _arc_at(point[0], carrier, epsilon)
        if math.dist(expected, point) > epsilon:
            _fail("arc endpoint is not on its carrier")
    t0 = math.atan2(start[1] - major, start[0] - cy)
    t1 = math.atan2(end[1] - major, end[0] - cy)
    if branch == -1:
        if t0 > 0: t0 -= 2 * math.pi
        if t1 > 0: t1 -= 2 * math.pi
        if t0 < -math.pi - epsilon or t1 < -math.pi - epsilon:
            _fail("unsupported arc branch")
    elif t0 < -epsilon or t1 < -epsilon or t0 > math.pi + epsilon or t1 > math.pi + epsilon:
        _fail("unsupported arc branch")
    sweep = t1 - t0
    if abs(sweep) <= 1e-15 or abs(sweep) > math.pi + 1e-12:
        _fail("degenerate or unsupported arc sweep")
    radii = [start[1], end[1]]
    if min(start[0], end[0]) <= cy <= max(start[0], end[0]):
        radii.append(major + branch * minor)
    return {"center": [cy, major], "radius": minor, "branch": branch,
            "start_angle_rad": t0, "sweep_rad": sweep,
            "radial_range": [min(radii), max(radii)]}


def _line_carrier(carrier, start, end, p1, linear, angular):
    kind = carrier.get("kind")
    if kind in ("constructed_axis", "constructed_bottom"):
        if kind == "constructed_axis" and (start[1] != 0 or end[1] != 0):
            _fail("axis closure is not on axis")
        if kind == "constructed_bottom" and start[0] != end[0]:
            _fail("bottom closure is not radial")
        return {"max_residual_mm": 0.0, "basis": "explicit construction assumption"}
    face_id = carrier.get("p1_face")
    face = p1["faces"].get(face_id)
    if not isinstance(face, dict):
        _fail("unknown P1 carrier face")
    data = face["native_face_data"]
    origin, direction = _vector(data["origin"], 3), _vector(data["direction"], 3)
    if kind == "plane":
        if face.get("surface_type") != "Planar" or data.get("uf_type") != 22:
            _fail("P1 plane mismatch")
        _axis([0, origin[1], 0], direction, linear, angular)
        residual = max(abs(p[0] - origin[1]) for p in (start, end))
    else:
        _axis(origin, direction, linear, angular)
        radius = _num(data["radius"])
        if radius <= 0:
            _fail("invalid carrier radius")
        if kind == "cylinder":
            if face.get("surface_type") != "Cylindrical" or data.get("uf_type") != 16:
                _fail("P1 cylinder mismatch")
            residual = max(abs(p[1] - radius) for p in (start, end))
        elif kind == "cone":
            if (face.get("surface_type") != "Conical" or data.get("uf_type") != 17
                    or type(carrier.get("slope_sign")) is not int or carrier["slope_sign"] not in (-1, 1)):
                _fail("P1 cone mismatch")
            angle = _num(data["radius_data"])
            if not 0 < angle < math.pi / 2:
                _fail("invalid cone angle")
            slope = carrier["slope_sign"] * math.tan(angle)
            residual = max(abs(p[1] - (radius + slope * (p[0] - origin[1]))) for p in (start, end))
        else:
            _fail("unsupported line carrier")
    if residual > linear:
        _fail("line does not match its proposed carrier")
    return {"max_residual_mm": residual, "p1_face": face_id,
            "basis": "carrier consistency only; source face trim and material side unverified"}


def calculate_profile(proposal, p1, details):
    """Compute the restricted monotone profile; supplied inventories are untrusted.

    Call ``load_stock_profile`` to validate actual on-disk evidence first. This
    computational API by itself does not attest to provenance.
    """
    if (not isinstance(proposal, dict) or proposal.get("schema") != "p3-meridian-proposal/1.0"
            or proposal.get("unit") != "mm" or proposal.get("frame") != "Y_r_positive"):
        _fail("unsupported proposal schema or frame")
    tolerances = proposal.get("matching_thresholds")
    if not isinstance(tolerances, dict): _fail("matching thresholds required")
    linear, angular = _num(tolerances.get("linear_mm")), _num(tolerances.get("angular_rad"))
    epsilon = _num(proposal.get("numerical_epsilon_mm"))
    if not (0 < epsilon < linear and 0 < angular < math.pi / 2):
        _fail("invalid numeric policy")
    revolution = proposal.get("revolution")
    if (not isinstance(revolution, dict) or revolution.get("status") != "construction_assumption"
            or not isinstance(revolution.get("basis"), str) or not revolution["basis"].strip()):
        _fail("explicit revolution construction assumption required")
    angle = _num(revolution.get("angle_rad"))
    if not 0 < angle <= 2 * math.pi:
        _fail("unsupported revolution angle")
    target = proposal.get("geometry_target")
    if (not isinstance(target, dict) or not isinstance(target.get("decision_path"), str)
            or not target["decision_path"].strip() or not isinstance(target.get("decision_id"), str)
            or not target["decision_id"].strip() or target.get("unit") != "mm" or _num(target.get("value")) <= 0):
        _fail("linear geometry target reference required")
    p1_source = proposal.get("p1_source")
    if not isinstance(p1_source, dict) or not isinstance(p1, dict) or p1.get("unit") != "mm" or p1.get("snapshot_id") != p1_source.get("snapshot_id"):
        _fail("P1 source mismatch")
    source_specs = proposal.get("detail_sources")
    if not isinstance(details, dict) or not isinstance(source_specs, dict) or set(details) != set(source_specs):
        _fail("detail sources mismatch")
    torus = {}
    for key, spec in source_specs.items():
        if not isinstance(spec, dict) or spec.get("label") != key or details[key].get("snapshot_id") != spec.get("snapshot_id"):
            _fail("detail identity mismatch")
        torus[key] = _torus(details[key], key, linear, angular)
    raw_vertices, raw_segments = proposal.get("vertices"), proposal.get("segments")
    if not isinstance(raw_vertices, list) or not isinstance(raw_segments, list) or len(raw_segments) < 4:
        _fail("vertices and a closed chain are required")
    vertices = {}
    for item in raw_vertices:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"] or item["id"] in vertices:
            _fail("invalid vertex IDs")
        vertices[item["id"]] = [_num(item.get("y")), _num(item.get("r"))]
    segments = []
    seen = set()
    for item in raw_segments:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"] or item["id"] in seen:
            _fail("invalid segment IDs")
        seen.add(item["id"])
        if item.get("start") not in vertices or item.get("end") not in vertices or item["start"] == item["end"]:
            _fail("invalid segment vertices")
        if item.get("kind") not in ("line", "circular_arc") or not isinstance(item.get("carrier"), dict):
            _fail("invalid segment kind or carrier")
        contexts = item.get("p1_context_faces")
        if not isinstance(contexts, list) or len(contexts) != len(set(contexts)) or any(x not in p1["faces"] for x in contexts):
            _fail("invalid P1 context")
        segments.append(deepcopy(item))
    if len(vertices) != len(segments) or len({s["start"] for s in segments}) != len(segments):
        _fail("loop must use each vertex exactly once")
    if any(segments[i]["end"] != segments[(i + 1) % len(segments)]["start"] for i in range(len(segments))):
        _fail("segments do not form one directed loop")
    if segments[-2]["carrier"].get("kind") != "constructed_axis" or segments[-1]["carrier"].get("kind") != "constructed_bottom":
        _fail("explicit axis and bottom closures required")
    original = deepcopy(vertices)
    assigned = {}
    for item in segments:
        carrier = item["carrier"]
        if item["kind"] == "circular_arc":
            key, branch = carrier.get("detail_source"), carrier.get("radial_branch")
            if carrier.get("kind") != "torus_meridian" or key not in torus or type(branch) is not int or branch not in (-1, 1):
                _fail("invalid torus branch or source")
            if key not in item["p1_context_faces"]:
                _fail("torus source missing from P1 context")
            arc_carrier = {**torus[key], "branch": branch}
            item["_resolved_torus"] = arc_carrier
            for vid in (item["start"], item["end"]):
                point = _arc_at(original[vid][0], arc_carrier, linear)
                if math.dist(point, original[vid]) > linear:
                    _fail("proposed vertex does not match torus")
                if vid in assigned and point != assigned[vid]:
                    _fail("intersecting torus junction requires explicit resolution")
                assigned[vid] = point
    vertices.update(assigned)
    area2, result_segments = 0.0, []
    for item in segments:
        start, end = vertices[item["start"]], vertices[item["end"]]
        if math.dist(start, end) <= epsilon:
            _fail("degenerate segment")
        result = {"id": item["id"], "kind": item["kind"], "start": item["start"], "end": item["end"],
                  "construction_role": item.get("construction_role"), "p1_context_faces": item["p1_context_faces"],
                  "carrier": deepcopy(item["carrier"]), "source_description": item.get("source_description")}
        if item["kind"] == "circular_arc":
            arc = _arc_segment(start, end, item["_resolved_torus"], epsilon)
            result["arc"] = arc
            result["source_evidence"] = {k: v for k, v in item["_resolved_torus"].items() if k != "branch"}
            cy, major = arc["center"]
            rho, t0, dt = arc["radius"], arc["start_angle_rad"], arc["sweep_rad"]
            t1 = t0 + dt
            area2 += rho * cy * (math.sin(t1) - math.sin(t0)) - rho * major * (math.cos(t1) - math.cos(t0)) + rho * rho * dt
        else:
            if item["carrier"].get("kind") == "torus_meridian": _fail("torus must be an arc")
            if (item["carrier"].get("kind") not in ("constructed_axis", "constructed_bottom")
                    and item["carrier"].get("p1_face") not in item["p1_context_faces"]):
                _fail("line carrier missing from P1 context")
            result["source_residual"] = _line_carrier(item["carrier"], start, end, p1, linear, angular)
            area2 += start[0] * end[1] - end[0] * start[1]
        result_segments.append(result)
    # Restricted y-monotone exterior + radial end and axis closures is simple
    # if all interior radii are positive and same-y runs do not reverse.
    outer = segments[:-2]
    if vertices[outer[-1]["end"]][1] != 0 or vertices[outer[0]["start"]][1] <= 0:
        _fail("outer chain must end on axis and start at positive radius")
    # The closing bottom edge runs from the axis out to the first outer
    # vertex. Include it in the cyclic same-y run so an initial inward
    # segment cannot overlap that closure. The last outer segment ends at
    # the axis, so the same direction check also covers the top closure run.
    direction = 1
    for i, item in enumerate(outer):
        start, end = vertices[item["start"]], vertices[item["end"]]
        if start[1] <= 0 or end[1] < 0 or (end[1] == 0 and i != len(outer)-1):
            _fail("outer chain crosses or touches the axis")
        dy, dr = end[0] - start[0], end[1] - start[1]
        if dy < 0: _fail("outer chain must be y-monotone")
        if dy == 0:
            if item["kind"] != "line" or dr == 0: _fail("invalid same-y segment")
            step = 1 if dr > 0 else -1
            if direction and direction != step: _fail("overlapping same-y chain")
            direction = step
        else:
            direction = 0
        if item["kind"] == "circular_arc" and result_segments[i]["arc"]["radial_range"][0] <= 0:
            _fail("arc reaches the axis")
    axis, bottom = segments[-2:]
    if (vertices[axis["start"]][0] != vertices[outer[-1]["end"]][0]
            or vertices[axis["end"]][0] != vertices[outer[0]["start"]][0]
            or vertices[axis["start"]][0] <= vertices[axis["end"]][0]):
        _fail("axis closure does not span the exterior chain")
    if not math.isfinite(area2) or abs(area2) <= epsilon * epsilon:
        _fail("degenerate profile area")
    adjustments = [{"vertex_id": key, "proposal": original[key], "computed": vertices[key],
                    "distance_mm": math.dist(original[key], vertices[key]),
                    "basis": "torus carrier endpoint; original source values are unchanged"}
                   for key in assigned]
    return {"schema": "p3-stock-profile-plan/0.1", "status": "planning_only", "unit": "mm", "frame": "Y_r_positive",
            "matching_thresholds": deepcopy(tolerances), "numerical_epsilon_mm": epsilon,
            "threshold_note": "candidate consistency only; not source precision or manufacturing tolerance",
            "vertices": [{"id": key, "y": value[0], "r": value[1]} for key, value in vertices.items()],
            "segments": result_segments, "vertex_adjustments": adjustments,
            "loop": {"segment_ids": [s["id"] for s in segments], "closed_by_shared_vertices": True,
                     "simple_by_monotone_chain": True, "signed_area_mm2": area2 / 2},
            "nodes": [{"id": "stock_section", "kind": "closed_meridian_candidate", "depends_on": [],
                       "status": "computed_under_assumptions"},
                      {"id": "stock_revolve", "kind": "revolve_candidate", "depends_on": ["stock_section"],
                       "angle_rad": angle, "angle_status": "construction_assumption",
                       "angle_basis": revolution["basis"], "status": "blocked"}],
            "assumptions": deepcopy(proposal.get("assumptions")),
            "geometry_target": {**deepcopy(target), "status": "not_evaluated",
                                "basis": "later geometry comparison; not a source matching tolerance or proof of achievement"},
            "open_items": ["native source frame and common ABS frame correspondence",
                           "source face trim and opposite-side evidence", "whole-stock envelope and material role",
                           "reference full-rotation and trimmed-face equivalence", "native backend and P6 shape comparison"],
            "source_records_verified": False, "source_geometry_proven": False,
            "whole_stock_envelope_proven": False, "execution_approved": False}


def load_stock_profile(proposal_path, *, repository_root):
    """Load and normalize the proposal's recorded source evidence without NX."""
    try:
        root = Path(repository_root).resolve(strict=True)
        source = Path(proposal_path).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise StockProfileError("stock profile: missing proposal or repository") from exc
    if not root.is_dir() or not source.is_relative_to(root) or not source.is_file():
        _fail("proposal must be a repository file")
    proposal = _read(source)
    if not isinstance(proposal, dict) or not isinstance(proposal.get("p1_source"), dict):
        _fail("P1 source is required")
    target = proposal.get("geometry_target")
    if not isinstance(target, dict): _fail("geometry target reference required")
    target_record = _read(_path(root, target.get("decision_path")))
    if (not isinstance(target_record, dict) or target_record.get("schema") != "v3-user-acceptance-target/1.0"
            or target_record.get("decision_id") != target.get("decision_id")
            or target_record.get("status") != "user_confirmed_target_pending_native_validation"
            or target_record.get("linear_absolute_target") != {"value": target.get("value"), "unit": target.get("unit")}):
        _fail("geometry target evidence mismatch")
    p1_spec = proposal["p1_source"]
    p1_file = _path(root, p1_spec.get("path"))
    source_work = _read(_path(root, proposal.get("source_proposal")))
    if (not isinstance(source_work, dict) or source_work.get("schema") != "v3-sample-regional-workbreakdown/1.0"
            or source_work.get("snapshot_id") != p1_spec.get("snapshot_id")):
        _fail("planning proposal source mismatch")
    stock = source_work.get("y_axis_outer_stock_candidate")
    original_segments = stock.get("segments") if isinstance(stock, dict) else None
    proposed_segments, proposed_vertices = proposal.get("segments"), proposal.get("vertices")
    if not isinstance(original_segments, list) or not isinstance(proposed_segments, list) or not isinstance(proposed_vertices, list):
        _fail("planning proposal segments are missing")
    if len(proposed_segments) != len(original_segments) + 2:
        _fail("typed proposal does not represent the source segment count")
    lookup = {v.get("id"): v for v in proposed_vertices if isinstance(v, dict)}
    if len(lookup) != len(proposed_vertices): _fail("duplicate proposal vertices")
    for item, original in zip(proposed_segments[:-2], original_segments):
        if not isinstance(item, dict) or not isinstance(original, dict): _fail("invalid proposal segment")
        a, b = lookup.get(item.get("start")), lookup.get(item.get("end"))
        if (not isinstance(a, dict) or not isinstance(b, dict)
                or [a.get("y"), a.get("r")] != [original.get("y_start_mm"), original.get("r_start_mm")]
                or [b.get("y"), b.get("r")] != [original.get("y_end_mm"), original.get("r_end_mm")]
                or item.get("p1_context_faces") != original.get("source_faces")):
            _fail("typed segment differs from the recorded source proposal")
    tolerances = proposal.get("matching_thresholds", {})
    numeric = {"linear": _num(tolerances.get("linear_mm")), "angular": _num(tolerances.get("angular_rad"))}
    if numeric != {"linear": 0.001, "angular": 0.0001}:
        _fail("recorded evidence requires the approved exploratory matching thresholds")
    try:
        p1 = normalize_snapshot(_read(p1_file), tolerances=numeric)
        details = {}
        source_specs = proposal.get("detail_sources")
        if not isinstance(source_specs, dict): _fail("detail source list required")
        for label, spec in source_specs.items():
            if not isinstance(spec, dict): _fail("invalid detail source")
            snap = _path(root, spec.get("snapshot_path")); summary = _path(root, spec.get("summary_path"))
            details[label] = normalize_detail_snapshot(_read(snap), summary=_read(summary), evidence_path=str(snap),
                                                       summary_path=str(summary), tolerances=numeric)
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        if isinstance(exc, StockProfileError): raise
        raise StockProfileError("stock profile: invalid source evidence") from exc
    result = calculate_profile(proposal, p1, details)
    result["source_records_verified"] = True
    result["source_evidence"] = {"proposal": source.relative_to(root).as_posix(),
                                 "p1_source": deepcopy(p1_spec), "detail_sources": deepcopy(source_specs)}
    return result
