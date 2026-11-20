"""Bind the recorded P3 user decision to its exact offline observations.

The result describes intent, not proven region geometry or executable features.
Snapshot-local IDs must never be rebound implicitly to another inventory.
"""
from copy import deepcopy
import math


def _fail(message):
    raise ValueError("relation decision: " + message)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _unique(items, expected=None):
    if not isinstance(items, list) or any(not _text(x) for x in items) or len(items) != len(set(items)):
        _fail("invalid or duplicate identifiers")
    if expected is not None and len(items) != expected:
        _fail("wrong member count")
    return set(items)


def _only(records, ident):
    matches = [r for r in records if isinstance(r, dict) and r.get("id") == ident]
    if len(matches) != 1:
        _fail("missing or duplicate candidate " + ident)
    return matches[0]


def _parameter(candidate, ident, dimension, unit):
    parameter = _only(candidate.get("parameters", []), ident)
    value = parameter.get("value")
    if (parameter.get("dimension") != dimension or parameter.get("unit") != unit
            or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
        _fail("invalid observed parameter " + ident)
    return value


def bind(decision, *, decision_evidence, reference_analysis, reference_analysis_path, inventory, candidates):
    """Return one declarative intent after exact comparison to the linked draft.

    Equality is structural, not a hash or an assertion that IDs survive a new
    snapshot. The linked draft and the newly recognized candidates are both
    retained as evidence; a difference requires an explicit new decision.
    """
    if not isinstance(decision, dict) or decision.get("schema") != "v3-user-design-decision/1.0":
        _fail("unsupported decision schema")
    if (not _text(decision_evidence) or not _text(decision.get("decision_id"))
            or decision.get("authority") != "explicit user reply in this conversation"
            or decision.get("answer") != "确认共享尺寸和等角联动"):
        _fail("missing or unsupported user decision")
    if decision.get("scope") != {"shared_cylinder_radius": True, "shared_pitch_circle_radius": True,
                                 "shared_phase": True, "equal_angular_spacing": True, "fixed_count": 22}:
        _fail("unsupported decision scope")
    if any(decision["scope"][key] is not True for key in ("shared_cylinder_radius", "shared_pitch_circle_radius",
                                                           "shared_phase", "equal_angular_spacing")):
        _fail("invalid decision flags")
    # bool compares equal to int in Python; count must be an actual integer.
    if type(decision["scope"]["fixed_count"]) is not int:
        _fail("invalid fixed count")
    binding = decision.get("observation_binding")
    if not isinstance(binding, dict) or not _text(reference_analysis_path) or binding.get("analysis_path") != reference_analysis_path:
        _fail("linked analysis path mismatch")
    snapshot = binding.get("snapshot_id")
    if (not _text(snapshot) or not isinstance(reference_analysis, dict)
            or reference_analysis.get("schema") != "p3-analysis-plan/0.1"
            or reference_analysis.get("snapshot_id") != snapshot or inventory.get("snapshot_id") != snapshot):
        _fail("snapshot mismatch")
    face_ids = binding.get("source_face_ids")
    faces = _unique(face_ids, 22)
    if not faces <= set(inventory.get("faces", {})):
        _fail("source face missing from inventory")
    ids = binding.get("candidate_ids")
    _unique(ids, 2)
    baseline = reference_analysis.get("candidates")
    if not isinstance(baseline, list) or not isinstance(candidates, list):
        _fail("candidate lists required")
    selected = {}
    for ident in ids:
        old, current = _only(baseline, ident), _only(candidates, ident)
        if old != current:
            _fail("candidate differs from the linked analysis: " + ident)
        if current.get("snapshot_id") != snapshot or _unique(current.get("source_faces"), 22) != faces:
            _fail("candidate source mismatch")
        source_edges = _unique(current.get("source_edges"))
        if not source_edges or not source_edges <= set(inventory.get("edges", {})):
            _fail("candidate edge mismatch")
        kind = current.get("kind")
        if kind not in {"possible_equal_radius_relation", "possible_circular_axis_spacing"} or kind in selected:
            _fail("candidate kinds mismatch")
        selected[kind] = current
    if len(selected) != 2:
        _fail("both relation candidates required")
    equal = selected["possible_equal_radius_relation"]
    circular = selected["possible_circular_axis_spacing"]
    evidence = circular.get("evidence")
    if not isinstance(evidence, list) or len(evidence) != 1 or not isinstance(evidence[0], dict):
        _fail("circular fit evidence required")
    fit = evidence[0]
    if fit.get("type") != "circular_axis_fit" or fit.get("snapshot_id") != snapshot or fit.get("point_count") != 22:
        _fail("circular evidence scope mismatch")
    unit = inventory.get("unit")
    if unit != fit.get("length_unit") or not _text(unit):
        _fail("length unit mismatch")
    for field in ("axis_point", "axis_direction", "plane_basis_u", "plane_basis_v"):
        value = fit.get(field)
        if (not isinstance(value, list) or len(value) != 3 or any(isinstance(x, bool)
                or not isinstance(x, (int, float)) or not math.isfinite(x) for x in value)):
            _fail("invalid frame")
    ordered = fit.get("ordered_face_angles_rad")
    if not isinstance(ordered, list) or any(not isinstance(x, dict) or set(x) != {"face_id", "angle"} for x in ordered):
        _fail("invalid member angle records")
    if _unique([x["face_id"] for x in ordered], 22) != faces:
        _fail("ordered members mismatch")
    if any(isinstance(x["angle"], bool) or not isinstance(x["angle"], (int, float))
           or not math.isfinite(x["angle"]) for x in ordered):
        _fail("invalid member angle")
    radius = _parameter(equal, "radius_" + face_ids[0], "length", unit)
    observed_radii = [_parameter(equal, "radius_" + face, "length", unit) for face in face_ids]
    threshold = fit.get("linear_threshold")
    if (radius <= 0 or isinstance(threshold, bool) or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold) or threshold <= 0 or max(observed_radii)-min(observed_radii) > threshold):
        _fail("invalid shared-radius observations")
    pitch_radius = _parameter(circular, "pitch_circle_radius", "length", unit)
    phase = _parameter(circular, "phase", "angle", "rad")
    pitch = _parameter(circular, "pitch", "angle", "rad")
    count = _parameter(circular, "point_count", "scalar", "1")
    if pitch_radius <= 0 or count != 22 or not math.isclose(pitch, 2 * math.pi / 22, rel_tol=1e-14, abs_tol=0):
        _fail("invalid circular parameters")
    angular_threshold = fit.get("angular_threshold_rad")
    if (isinstance(angular_threshold, bool) or not isinstance(angular_threshold, (int, float))
            or not math.isfinite(angular_threshold) or angular_threshold <= 0):
        _fail("invalid angular threshold")
    for i, item in enumerate(ordered):
        if abs(math.remainder(item["angle"] - (phase + i * pitch), 2 * math.pi)) > angular_threshold:
            _fail("ordered angles do not follow the fitted phase and pitch")
    parameters = [
        {"id": "shared_cylinder_radius", "dimension": "length", "value": radius, "expression": None},
        {"id": "shared_pitch_circle_radius", "dimension": "length", "value": pitch_radius, "expression": None},
        {"id": "shared_phase", "dimension": "angle", "value": phase, "expression": None},
        {"id": "full_turn", "dimension": "angle", "value": 2 * math.pi, "expression": None},
        {"id": "fixed_count", "dimension": "scalar", "value": 22, "expression": None},
        {"id": "pitch", "dimension": "angle", "value": None, "expression": "full_turn / fixed_count"},
    ]
    members = []
    for i, item in enumerate(ordered):
        face = item["face_id"]
        radius_id, angle_id = "radius_" + face, "angle_" + face
        parameters.extend([{"id": radius_id, "dimension": "length", "value": None, "expression": "shared_cylinder_radius"},
                           {"id": angle_id, "dimension": "angle", "value": None, "expression": f"shared_phase + pitch * {i}"}])
        members.append({"face_id": face, "index": i, "observed_angle_rad": item["angle"],
                        "radius_parameter": radius_id, "angle_parameter": angle_id,
                        "pitch_circle_radius_parameter": "shared_pitch_circle_radius"})
    return {"schema": "p3-relation-intent/1.0", "decision_id": decision["decision_id"],
            "decision_evidence": decision_evidence, "reference_analysis_path": reference_analysis_path,
            "snapshot_id": snapshot, "candidate_ids": list(ids), "source_face_ids": list(face_ids),
            "status": "user_confirmed_relation_intent", "length_unit": unit, "angle_unit": "rad",
            "frame": {field: deepcopy(fit[field]) for field in ("axis_point", "axis_direction", "plane_basis_u", "plane_basis_v")},
            "angle_convention": "atan2(delta dot plane_basis_v, delta dot plane_basis_u)",
            "fixed_count": 22, "pitch_definition": "2*pi/fixed_count", "observed_pitch_rad": pitch,
            "parameter_roles": {"shared_cylinder_radius": "confirmed_shared_driving_intent",
                                "shared_pitch_circle_radius": "confirmed_shared_driving_intent",
                                "shared_phase": "confirmed_shared_driving_intent",
                                "full_turn": "fixed_constant", "fixed_count": "fixed_by_user_for_now",
                                "pitch": "derived"}, "parameters": parameters,
            "axis_position_definition": "axis_point + shared_pitch_circle_radius * (cos(angle) * plane_basis_u + sin(angle) * plane_basis_v)",
            "members": members, "edit_domains": "unconfirmed", "geometry_proven": False,
            "native_propagation_verified": False, "execution_approved": False}
