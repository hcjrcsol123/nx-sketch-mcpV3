"""Bind two user decisions to accepted P3 evidence; no model execution.

The 22 shared flank generators are editable design intent, not proof that all
source trims or whole teeth are equal. Source IDs remain snapshot scoped.
"""
from copy import deepcopy
import json
import math
from pathlib import Path

from .regions.cylindrical_slot_plan import SlotBinding, plan_slot


class DecisionBindingError(ValueError):
    pass


P1_ID = "P1-REFERENCE-7812d302a165453badcd339473b5dba3"
P1 = "workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json"
SHARED = "docs/v3/decisions/p3-shared-flank-templates-user-decision.json"
SLOT_DECISION = "docs/v3/decisions/p3-rear-slot-independent-user-decision.json"
ORIGINAL_FLANK = "docs/v3/decisions/p3-independent-flanks-user-decision.json"
ORIGINAL_RELATION = "docs/v3/decisions/p3-shared-22-user-decision.json"
TARGET = "docs/v3/decisions/p3-linear-geometry-target.json"
SOURCE_MAP = "workspace/v3/p3/P3-SWEPT-ANALYSIS-01/source-map.json"
MECHANICAL = "workspace/v3/p3/P3-SWEPT-ANALYSIS-01/mechanical-observations.json"
RELATION_PLAN = "workspace/v3/p3/P3-ANALYSIS-04/model-plan.json"
RELATION_SOURCE = "workspace/v3/p3/P3-ANALYSIS-03/model-plan.json"
SLOT_PLAN = "workspace/v3/p3/P3-REGION-PLAN-02/slot-plan-c2.json"
_SIDE_TEMPLATES = {"F0002_like": "F0002", "F0024_like": "F0024"}


def _fail(message):
    raise DecisionBindingError(message)


def _read(root, rel):
    if not isinstance(rel, str) or not rel or "\\" in rel or ":" in rel:
        _fail("invalid repository-relative path")
    path = Path(rel)
    if path.is_absolute() or any(p in (".", "..") for p in path.parts):
        _fail("invalid repository-relative path")
    try:
        file = (root / path).resolve(strict=True)
        if not file.is_relative_to(root) or not file.is_file(): _fail("source escapes repository")
        def unique(pairs):
            out = {}
            for key, value in pairs:
                if key in out: _fail("duplicate JSON key")
                out[key] = value
            return out
        with file.open(encoding="utf-8") as stream:
            return json.load(stream, object_pairs_hook=unique,
                             parse_constant=lambda _: _fail("non-finite JSON"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DecisionBindingError("source evidence unreadable") from exc


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _positive(value, name):
    if not _finite(value) or value <= 0: _fail(name + " must be finite and positive")
    return value


def load_inputs(repository_root):
    """Read accepted artifacts and source definitions without loading context."""
    root = Path(repository_root).resolve(strict=True)
    paths = (P1, SHARED, SLOT_DECISION, ORIGINAL_FLANK, ORIGINAL_RELATION, TARGET,
             SOURCE_MAP, MECHANICAL, RELATION_PLAN, RELATION_SOURCE, SLOT_PLAN)
    data = {path: _read(root, path) for path in paths}
    sources = data[SOURCE_MAP].get("swept_sources")
    if not isinstance(sources, list): _fail("source map lacks observations")
    raw = {}
    for source in sources:
        if not isinstance(source, dict): _fail("invalid source observation")
        label, detail_path, summary_path = source.get("selection_label"), source.get("detail_path"), source.get("summary_path")
        if not isinstance(label, str) or label in raw: _fail("duplicate or invalid source label")
        snapshot, summary = _read(root, detail_path), _read(root, summary_path)
        details = [d for d in snapshot.get("detail", []) if d.get("label") == label]
        if (snapshot.get("snapshot_id") != source.get("detail_snapshot_id") or len(details) != 1
                or details[0].get("status") != "MATCHED" or details[0].get("matching_count") != 1
                or summary.get("evidence_id") != source.get("detail_snapshot_id")
                or summary.get("status") != "RETURNED" or summary.get("return") != "HUMAN_OWNED"
                or summary.get("p1_snapshot_id") != P1_ID
                or sum(s == source.get("selector") for s in summary.get("detail_request", {}).get("selectors", [])) != 1):
            _fail("source snapshot or returned summary mismatch")
        raw[label] = {"snapshot_id": snapshot["snapshot_id"], "detail_path": detail_path,
                      "summary_path": summary_path, "generator": details[0]["diagnostic"]["topology"]["geometry"]["generator"]}
    data["raw_sources"] = raw
    return data


def _basis(generator):
    if (not isinstance(generator, dict) or generator.get("type") != 102
            or type(generator.get("order")) is not int or generator["order"] != 4
            or type(generator.get("num_poles")) is not int or generator["num_poles"] != 7
            or generator.get("rational") is not False or generator.get("start") != 0 or generator.get("end") != 1):
        _fail("unsupported original generator basis")
    knots, poles = generator.get("knots"), generator.get("weighted_poles_flat_xyzw")
    if (not isinstance(knots, list) or len(knots) != 11 or any(not _finite(x) for x in knots)
            or any(a > b for a, b in zip(knots, knots[1:]))
            or not isinstance(poles, list) or len(poles) != 28 or any(not _finite(x) for x in poles)
            or any(x != 1 for x in poles[3::4])):
        _fail("malformed original generator knots or poles")
    return {"order": 4, "knots": deepcopy(knots), "full_domain": [0, 1], "num_poles": 7, "rational": False}


def _decision(doc, ident, scope):
    if (not isinstance(doc, dict) or doc.get("schema") != "v3-user-design-decision/1.0"
            or doc.get("decision_id") != ident or doc.get("authority") != "explicit user reply in this conversation"
            or doc.get("answer") != "均为前者" or doc.get("scope") != scope):
        _fail("missing, wrong or altered user decision")


def bind_flanks(data):
    shared, original, previous = data[SHARED], data[ORIGINAL_FLANK], data[ORIGINAL_RELATION]
    mapping, mechanical, plan = data[SOURCE_MAP], data[MECHANICAL], data[RELATION_PLAN]
    scope = {"two_independent_original_generators": True, "same_side_shared_across_members": True,
             "fixed_count": 22, "preserve_each_template_original_order_and_knots": True,
             "position_by_confirmed_equal_angular_relation": True, "per_member_trim_and_connection_evidence_retained": True}
    _decision(shared, "P3-USER-SHARED-FLANK-TEMPLATES-01", scope)
    if type(shared["scope"]["fixed_count"]) is not int: _fail("invalid fixed member count")
    binding = shared.get("source_binding", {})
    relation_scope = {"shared_cylinder_radius": True, "shared_pitch_circle_radius": True,
                      "shared_phase": True, "equal_angular_spacing": True, "fixed_count": 22}
    flank_scope = {"independent_editable_flanks": True, "preserve_original_differences": True,
                   "control_point_dimensions_and_endpoint_constraints": True, "fix_each_original_order_and_knot_vector": True}
    if (mapping.get("schema") != "p3-swept-source-map/0.1" or mapping.get("p1_snapshot_id") != P1_ID
            or binding.get("source_map_path") != SOURCE_MAP or binding.get("p1_snapshot_id") != P1_ID
            or binding.get("members") != mapping.get("members")
            or binding.get("relation_decision_path") != ORIGINAL_RELATION
            or binding.get("original_flank_decision_path") != ORIGINAL_FLANK
            or binding.get("template_observation_sources") != original.get("observation_sources")
            or original.get("decision_id") != "P3-USER-INDEPENDENT-FLANK-SPLINES-01"
            or original.get("schema") != "v3-user-design-decision/1.0" or original.get("scope") != flank_scope
            or previous.get("decision_id") != "P3-USER-22-SHARED-01"
            or previous.get("schema") != "v3-user-design-decision/1.0" or previous.get("scope") != relation_scope
            or type(previous["scope"]["fixed_count"]) is not int
            or mapping.get("decision", {}).get("scope") != previous.get("scope")
            or mechanical.get("schema") != "p3-swept-mechanical-observations/1.0"
            or mechanical.get("sources", {}).get("confirmed_relation") != ORIGINAL_RELATION):
        _fail("decision and accepted source identities differ")
    intents = plan.get("relation_intents")
    if not isinstance(intents, list) or len(intents) != 1: _fail("accepted relation intent missing")
    intent = intents[0]
    relation_binding = previous.get("observation_binding", {})
    baseline = data[RELATION_SOURCE]
    candidate_ids = relation_binding.get("candidate_ids")
    if (relation_binding.get("analysis_path") != RELATION_SOURCE or not isinstance(candidate_ids, list) or len(candidate_ids) != 2
            or len(set(candidate_ids)) != 2 or baseline.get("snapshot_id") != relation_binding.get("snapshot_id")
            or intent.get("reference_analysis_path") != RELATION_SOURCE):
        _fail("original relation observation binding mismatch")
    old_candidates = [c for c in baseline.get("candidates", []) if c.get("id") in candidate_ids]
    current_candidates = [c for c in plan.get("candidates", []) if c.get("id") in candidate_ids]
    if len(old_candidates) != 2 or len(current_candidates) != 2 or any(c not in current_candidates for c in old_candidates):
        _fail("accepted relation candidates differ from original observation")
    circular = [c for c in old_candidates if c.get("kind") == "possible_circular_axis_spacing"]
    if len(circular) != 1 or len(circular[0].get("evidence", [])) != 1:
        _fail("original circular relation evidence missing")
    fit = circular[0]["evidence"][0]
    frame = intent.get("frame", {})
    if (intent.get("decision_id") != previous["decision_id"] or intent.get("status") != "user_confirmed_relation_intent"
            or intent.get("snapshot_id") != mapping["decision"].get("decision_snapshot_id")
            or intent.get("snapshot_id") != relation_binding.get("snapshot_id")
            or intent.get("frame") != mapping["decision"].get("frame")
            or frame != {k: fit.get(k) for k in ("axis_point", "axis_direction", "plane_basis_u", "plane_basis_v")}
            or frame.get("axis_direction") != [0, 1, 0] or frame.get("plane_basis_u") != [0, 0, 1]
            or frame.get("plane_basis_v") != [1, 0, 0] or intent.get("angle_convention") != "atan2(delta dot plane_basis_v, delta dot plane_basis_u)"
            or intent.get("fixed_count") != 22 or intent.get("length_unit") != "mm"):
        _fail("relation frame, count or provenance differs")
    origin = frame.get("axis_point")
    if not isinstance(origin, list) or len(origin) != 3 or any(not _finite(x) for x in origin): _fail("invalid relation origin")
    pars = intent.get("parameters", [])
    def one(ident):
        found = [p for p in pars if p.get("id") == ident]
        if len(found) != 1: _fail("missing relation parameter")
        return found[0]
    phase, turn, count, pitch, cylinder_radius, pitch_radius = (one(x) for x in
        ("shared_phase", "full_turn", "fixed_count", "pitch", "shared_cylinder_radius", "shared_pitch_circle_radius"))
    if (phase.get("dimension") != "angle" or not _finite(phase.get("value")) or phase.get("expression") is not None
            or turn.get("dimension") != "angle" or turn.get("value") != 2*math.pi or turn.get("expression") is not None
            or count.get("dimension") != "scalar" or type(count.get("value")) is not int or count["value"] != 22
            or count.get("expression") is not None or pitch.get("dimension") != "angle"
            or pitch.get("value") is not None or pitch.get("expression") != "full_turn / fixed_count"
            or cylinder_radius.get("dimension") != "length" or not _finite(cylinder_radius.get("value"))
            or cylinder_radius["value"] <= 0 or cylinder_radius.get("expression") is not None
            or pitch_radius.get("dimension") != "length" or not _finite(pitch_radius.get("value"))
            or pitch_radius["value"] <= 0 or pitch_radius.get("expression") is not None):
        _fail("accepted phase, count or derived pitch mismatch")
    def candidate_value(candidate, ident, dimension, unit):
        found = [p for p in candidate.get("parameters", []) if p.get("id") == ident]
        if (len(found) != 1 or found[0].get("dimension") != dimension or found[0].get("unit") != unit
                or not _finite(found[0].get("value"))):
            _fail("original relation parameter missing or invalid")
        return found[0]["value"]
    equal = [c for c in old_candidates if c.get("kind") == "possible_equal_radius_relation"]
    source_faces = relation_binding.get("source_face_ids")
    if len(equal) != 1 or not isinstance(source_faces, list) or len(source_faces) != 22:
        _fail("original shared radius observations missing")
    if (phase["value"] != candidate_value(circular[0], "phase", "angle", "rad")
            or pitch_radius["value"] != candidate_value(circular[0], "pitch_circle_radius", "length", "mm")
            or cylinder_radius["value"] != candidate_value(equal[0], "radius_" + source_faces[0], "length", "mm")
            or candidate_value(circular[0], "pitch", "angle", "rad") != 2*math.pi/22
            or candidate_value(circular[0], "point_count", "scalar", "1") != 22):
        _fail("confirmed relation differs from original fitted parameters")
    members, observed = mapping.get("members"), mechanical.get("members")
    if (not isinstance(members, list) or len(members) != 22 or [m.get("member_index") for m in members] != list(range(22))
            or not isinstance(observed, list) or len(observed) != 22): _fail("missing or duplicate member order")
    by_member = {}
    for member in observed:
        key = member.get("member")
        if not isinstance(key, str) or key in by_member: _fail("duplicate mechanical member")
        by_member[key] = member
    sources = mapping.get("swept_sources")
    if not isinstance(sources, list) or len(sources) != 44: _fail("44 source observations required")
    by_face = {}
    for source in sources:
        face = source.get("p1_face_id")
        if not isinstance(face, str) or face in by_face or source.get("selection_label") != face:
            _fail("duplicate or mismatched semantic source")
        raw = data["raw_sources"].get(face, {})
        if (raw.get("snapshot_id") != source.get("detail_snapshot_id") or raw.get("detail_path") != source.get("detail_path")
                or raw.get("summary_path") != source.get("summary_path") or raw.get("generator") != source.get("original_generator")):
            _fail("original source generator differs from source map")
        _basis(source["original_generator"])
        by_face[face] = source
    references = {}
    for source in binding["template_observation_sources"]:
        label = source.get("label")
        if label not in _SIDE_TEMPLATES.values() or label in references or label not in by_face:
            _fail("invalid original template observation")
        record = by_face[label]
        if (source.get("snapshot_id") != record["detail_snapshot_id"] or source.get("detail_path") != record["detail_path"]
                or source.get("summary_path") != record["summary_path"] or source.get("observed_basis") != _basis(record["original_generator"])):
            _fail("template basis or source differs from original decision")
        references[label] = record
    if set(references) != set(_SIDE_TEMPLATES.values()): _fail("two original templates required")
    relation_members = intent.get("members")
    if (not isinstance(relation_members, list) or len(relation_members) != 22
            or [(m.get("face_id"), m.get("observed_angle_rad")) for m in relation_members]
               != [(m.get("face_id"), m.get("angle")) for m in fit.get("ordered_face_angles_rad", [])]
            or {m.get("face_id") for m in relation_members} != set(relation_binding.get("source_face_ids", []))):
        _fail("relation members differ from original observations")
    all_used, out, anchor = set(), [], None
    for index, member in enumerate(members):
        key = member.get("p1_cylinder_face_id")
        item, relation = by_member.get(key), relation_members[index]
        if (not isinstance(item, dict) or relation.get("index") != index
                or relation.get("face_id") != member.get("decision_snapshot_face_id")
                or relation.get("observed_angle_rad") != member.get("observed_angle_rad")
                or item.get("angle_rad") != member.get("observed_angle_rad")
                or not _finite(member.get("observed_angle_rad"))
                or abs(math.remainder(member["observed_angle_rad"] - (phase["value"] + index*2*math.pi/22), 2*math.pi)) > .0001):
            _fail("member index, observed angle or confirmed relation mismatch")
        faces = member.get("p1_swept_face_ids")
        sides = item.get("sides")
        topology = item.get("source_topology", {})
        if (not isinstance(faces, list) or len(faces) != 2 or len(set(faces)) != 2
                or topology.get("confirmed_relation_cylinder") != key or set(topology.get("direct_swept_neighbors", [])) != set(faces)
                or not isinstance(sides, list) or len(sides) != 2):
            _fail("member source topology mismatch")
        labelled = {}
        for side in sides:
            kind, label = side.get("side"), side.get("label")
            if kind not in _SIDE_TEMPLATES or kind in labelled or label not in faces or label in all_used or label not in by_face:
                _fail("missing, duplicate or ambiguous side mapping")
            source = by_face[label]
            generator, native = side.get("generator", {}), source["original_generator"]
            expected_poles = [native["weighted_poles_flat_xyzw"][i:i+3] for i in range(0, 28, 4)]
            if (side.get("snapshot_id") != source["detail_snapshot_id"] or side.get("source_path") != source["detail_path"]
                    or side.get("source_summary_path") != source["summary_path"] or side.get("direction") != source["extrusion_direction_observed"]
                    or generator.get("order") != native["order"] or generator.get("knots") != native["knots"]
                    or generator.get("poles_world_mm") != expected_poles or generator.get("domain") != [native["start"], native["end"]]):
                _fail("mechanical side and original source differ")
            template_knots = {name: references[template]["original_generator"]["knots"] for name, template in _SIDE_TEMPLATES.items()}
            similar = [name for name, knots in template_knots.items() if all(abs(a-b) <= 1e-8 for a, b in zip(native["knots"], knots))]
            if similar != [kind]: _fail("side classification is ambiguous or mismatched")
            labelled[kind] = {"template": _SIDE_TEMPLATES[kind], "p1_face_id": label,
                              "detail_snapshot_id": source["detail_snapshot_id"], "detail_path": source["detail_path"],
                              "summary_path": source["summary_path"], "original_basis": _basis(native),
                              "trim": "individual_unverified", "active_pole_support": "unverified",
                              "source_geometry_equivalence": "not_proven"}
            all_used.add(label)
        if set(labelled) != set(_SIDE_TEMPLATES): _fail("both independent sides required")
        if labelled["F0002_like"]["p1_face_id"] == "F0002" and labelled["F0024_like"]["p1_face_id"] == "F0024":
            if anchor is not None: _fail("duplicate template anchor")
            anchor = index
        out.append({"member_index": index, "p1_cylinder_face_id": key,
                    "decision_snapshot_face_id": member["decision_snapshot_face_id"],
                    "observed_angle_rad": member["observed_angle_rad"], "angle_expression": f"shared_phase + {index} * pitch",
                    "sides": labelled})
    if set(by_member) != {m["p1_cylinder_face_id"] for m in members} or all_used != set(by_face) or anchor is None:
        _fail("incomplete or duplicated 22 by 2 mapping")
    return {"status": "user_confirmed_relation_intent", "decision_path": SHARED,
            "prior_decisions": [ORIGINAL_RELATION, ORIGINAL_FLANK], "source_map": SOURCE_MAP, "mechanical_observations": MECHANICAL,
            "frame": deepcopy(frame), "angle_convention": intent["angle_convention"], "fixed_count": 22,
            "reference_phase_rad": phase["value"], "shared_phase_rad": phase["value"],
            "shared_cylinder_radius_mm": cylinder_radius["value"], "shared_pitch_circle_radius_mm": pitch_radius["value"],
            "pitch_expression": "2*pi / 22", "anchor_member_index": anchor,
            "axis_position_expression": "axis_point + shared_pitch_circle_radius * (cos(angle) * plane_basis_u + sin(angle) * plane_basis_v)",
            "rotation_expression": "shared_phase + member_index * pitch - (reference_phase + anchor_index * pitch)",
            "templates": {label: {"source": references[label]["detail_path"], "snapshot_id": references[label]["detail_snapshot_id"],
                                  "original_generator": deepcopy(references[label]["original_generator"])} for label in sorted(references)},
            "members": out, "same_side_shared": True, "opposite_sides_independent": True,
            "trim_and_connections": "per_member_unverified", "pole_activity": "unverified",
            "radius_to_flank_endpoint_coupling": "unverified_constraint_requirement",
            "geometry_proven": False, "native_binding_verified": False, "execution_approved": False}


def evaluate_flank_poles(intent, template_label, member_index, *, phase=None, poles=None):
    """Evaluate the intent's original seven poles under the shared Y rotation."""
    if type(member_index) is not int or not 0 <= member_index < 22 or template_label not in intent["templates"]:
        _fail("unknown member or template")
    reference_phase = intent["reference_phase_rad"]
    phase = intent["shared_phase_rad"] if phase is None else phase
    if not _finite(phase) or not _finite(reference_phase): _fail("phase must be finite")
    original = intent["templates"][template_label]["original_generator"]["weighted_poles_flat_xyzw"]
    poles = [original[i:i+3] for i in range(0, 28, 4)] if poles is None else poles
    if (not isinstance(poles, list) or len(poles) != 7 or any(not isinstance(p, list) or len(p) != 3
            or any(not _finite(x) for x in p) for p in poles)):
        _fail("seven finite 3D poles required")
    angle = phase + member_index*2*math.pi/22 - (reference_phase + intent["anchor_member_index"]*2*math.pi/22)
    s, c = math.sin(angle), math.cos(angle)
    x0, _, z0 = intent["frame"]["axis_point"]
    return [[x0 + c*(x-x0) + s*(z-z0), y, z0 - s*(x-x0) + c*(z-z0)] for x, y, z in poles]


def evaluate_member_axis(intent, member_index, *, phase=None, pitch_circle_radius=None):
    """Evaluate the previously confirmed axis placement, not flank coupling."""
    if type(member_index) is not int or not 0 <= member_index < 22:
        _fail("unknown member")
    phase = intent["shared_phase_rad"] if phase is None else phase
    radius = intent["shared_pitch_circle_radius_mm"] if pitch_circle_radius is None else pitch_circle_radius
    if not _finite(phase): _fail("phase must be finite")
    _positive(radius, "pitch circle radius")
    frame = intent["frame"]
    angle = phase + member_index*2*math.pi/22
    return [frame["axis_point"][i] + radius*(math.cos(angle)*frame["plane_basis_u"][i]
            + math.sin(angle)*frame["plane_basis_v"][i]) for i in range(3)]


def bind_slot(data):
    decision, plan = data[SLOT_DECISION], data[SLOT_PLAN]
    if (not isinstance(decision, dict) or decision.get("schema") != "v3-user-design-decision/1.0"
            or decision.get("decision_id") != "P3-USER-REAR-SLOT-INDEPENDENT-01"
            or decision.get("authority") != "explicit user reply in this conversation" or decision.get("answer") != "均为前者"):
        _fail("missing or wrong slot decision")
    scope, source = decision.get("scope", {}), decision.get("source_binding", {})
    items = scope.get("independent_parameters")
    if not isinstance(items, list) or len(items) != 4: _fail("four independent slot dimensions required")
    pars = {}
    for item in items:
        if (not isinstance(item, dict) or set(item) != {"id", "value", "unit"}
                or item["id"] not in {"width", "radius", "axis_y", "axis_z"} or item["id"] in pars
                or item["unit"] != "mm" or not _finite(item["value"])): _fail("invalid independent slot dimension")
        pars[item["id"]] = item["value"]
    _positive(pars["width"], "width"); _positive(pars["radius"], "radius")
    fixed = scope.get("fixed_center_x")
    direction = scope.get("fixed_axis_line_direction")
    if (set(scope) != {"independent_parameters", "fixed_center_x", "fixed_axis_line_direction", "centering_rule", "cross_parameter_linkage"}
            or scope.get("fixed_center_x") != {"value": 0.0, "unit": "mm"} or scope.get("fixed_axis_line_direction") != [1, 0, 0]
            or type(fixed.get("value")) not in (int, float) or not isinstance(direction, list)
            or any(type(v) not in (int, float) for v in direction)
            or scope.get("centering_rule") != "side planes x=-width/2 and x=+width/2 in the source part absolute frame"
            or scope.get("cross_parameter_linkage") is not False or source.get("plan_path") != SLOT_PLAN
            or source.get("snapshot_id") != P1_ID or source.get("unit") != "mm" or source.get("source") != plan.get("source")
            or source.get("tool") != plan.get("tool") or plan.get("schema") != "cylindrical-slot-plan/1.0"
            or plan.get("snapshot_id") != P1_ID or plan.get("unit") != "mm"):
        _fail("slot decision, source or centering rule mismatch")
    selected = source["source"]
    if (selected.get("cylinder_face_id") != "F0116" or set(selected.get("plane_face_ids", [])) != {"F0059", "F0119"}
            or len(selected.get("plane_face_ids", [])) != 2): _fail("slot source face binding mismatch")
    derived = plan["derived"]
    if (pars["width"] != derived.get("width") or pars["radius"] != derived.get("radius")
            or derived.get("positive_axis") != [1, 0, 0]
            or derived.get("midplane_axis_point") != [0, pars["axis_y"], pars["axis_z"]]
            or derived.get("plane_axial_offsets") != [-pars["width"]/2, pars["width"]/2]):
        _fail("slot parameters differ from measured source plan")
    recomputed = plan_slot(data[P1], SlotBinding(selected["cylinder_face_id"], tuple(selected["plane_face_ids"])),
                           tolerances={"linear": .001, "angular": .0001})
    if (recomputed["snapshot_id"] != P1_ID or recomputed["source"] != plan["source"]
            or recomputed["derived"] != plan["derived"] or recomputed["tool"] != plan["tool"]):
        _fail("slot plan no longer matches source inventory")
    return {"status": "user_confirmed_parameter_intent", "decision_path": SLOT_DECISION, "source_plan": SLOT_PLAN,
            "p1_snapshot_id": P1_ID, "source_face_ids": [selected["cylinder_face_id"], *selected["plane_face_ids"]],
            "parameters": [{"id": key, "value": pars[key], "unit": "mm", "classification": "independent"}
                           for key in ("width", "radius", "axis_y", "axis_z")],
            "fixed": {"center_x": 0.0, "axis_direction": [1, 0, 0]},
            "derived": {"side_x_negative": "-width / 2", "side_x_positive": "width / 2"},
            "cross_parameter_linkage": False, "edit_domains": "unverified", "material_side": "unverified",
            "geometry_proven": False, "native_binding_verified": False, "execution_approved": False}


def evaluate_slot(intent, *, width=None, radius=None, axis_y=None, axis_z=None):
    values = {p["id"]: p["value"] for p in intent["parameters"]}
    for key, value in (("width", width), ("radius", radius), ("axis_y", axis_y), ("axis_z", axis_z)):
        if value is not None: values[key] = value
    _positive(values["width"], "width"); _positive(values["radius"], "radius")
    if not _finite(values["axis_y"]) or not _finite(values["axis_z"]): _fail("axis position must be finite")
    return {"width": values["width"], "radius": values["radius"], "axis_point": [0, values["axis_y"], values["axis_z"]],
            "axis_direction": [1, 0, 0], "side_planes_x": [-values["width"]/2, values["width"]/2]}


def build_intents(data):
    if (data[TARGET].get("decision_id") != "P3-USER-LINEAR-GEOMETRY-001MM-01"
            or data[TARGET].get("linear_absolute_target") != {"value": .001, "unit": "mm"}):
        _fail("prior geometry target decision mismatch")
    return {"schema": "p3-decision-bindings/1.0", "status": "design_intent_only", "p1_snapshot_id": P1_ID,
            "flanks": bind_flanks(data), "rear_slot": bind_slot(data),
            "retained_geometry_target": {"decision_path": TARGET, "value": .001, "unit": "mm", "achievement": "unverified"},
            "geometry_proven": False, "native_binding_verified": False, "execution_approved": False}
