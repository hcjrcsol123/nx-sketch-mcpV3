"""P1-anchored, source-scoped Swept observations; never a geometry proof.

This sample-specific offline join preserves each detail snapshot and its local
identifiers. Candidate correspondence requires a unique bidirectional match;
matching thresholds are not an accuracy or reconstruction claim.
"""
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import re

from .regions.common import normalize_snapshot
from .regions.detail_common import normalize_detail_snapshot
from .regions.detail_extrusions import recognize


class SourceMapError(ValueError):
    pass


P1_ID = "P1-REFERENCE-7812d302a165453badcd339473b5dba3"
P1_PATH = "workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json"
DECISION_PATH = "docs/v3/decisions/p3-shared-22-user-decision.json"
FLANK_DECISION_PATH = "docs/v3/decisions/p3-independent-flanks-user-decision.json"
RELATION_PATH = "workspace/v3/p3/P3-ANALYSIS-04/model-plan.json"
OLD_RUN = "workspace/v3/p3/P3-SWEPT-01/controller"
NEW_RUN = "workspace/v3/p3/P3-SWEPT-02/controller"
LEGACY = {"F0002": "workspace/v3/p3/P3-CIRCLE-01/native-01",
          "F0024": "workspace/v3/p3/P3-REGIONS-01/native-01-F0024"}
THRESHOLDS = {"linear": 0.001, "angular": 0.0001}


def _fail(message):
    raise SourceMapError(message)


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _fail("duplicate JSON key")
            result[key] = value
        return result
    def nonfinite(_):
        _fail("non-finite JSON value")
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=unique, parse_constant=nonfinite)


def _file(root, relative):
    path = Path(relative)
    if path.is_absolute() or any(p in (".", "..") for p in path.parts):
        _fail("invalid repository evidence path")
    path = (root / path).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        _fail("source evidence missing or outside repository")
    return path


def _relative(root, path):
    path = Path(path).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        _fail("invalid source evidence path")
    return path.relative_to(root).as_posix()


def _signature(inv, face):
    result = []
    for edge_id in face["edge_ids"]:
        edge = inv["edges"][edge_id]
        neighbors = []
        for fid in edge["face_ids"]:
            if fid != face["id"]:
                neighbor = inv["faces"][fid]
                neighbors.append((neighbor["surface_type"], neighbor["native_face_data"]["uf_type"]))
        result.append((edge["edge_type"], tuple(sorted(neighbors))))
    return tuple(sorted(result))


def compatible(a, af, b, bf, *, linear, angular):
    """Semantic candidate match only; IDs and native tags are never compared."""
    if a["unit"] != b["unit"]:
        return False
    x, y = af["native_face_data"], bf["native_face_data"]
    if (af["surface_type"] != bf["surface_type"] or x["uf_type"] != y["uf_type"]
            or len(af["edge_ids"]) != len(bf["edge_ids"])
            or any(abs(p-q) > linear for p, q in zip(x["bounding_box"], y["bounding_box"]))
            or _signature(a, af) != _signature(b, bf)):
        return False
    if af["surface_type"] == "Cylindrical":
        if x["normal_sense"] != y["normal_sense"] or abs(x["radius"] - y["radius"]) > linear:
            return False
        u, v = x["direction"], y["direction"]
        lu, lv = math.hypot(*u), math.hypot(*v)
        if lu == 0 or lv == 0:
            return False
        u, v = [z/lu for z in u], [z/lv for z in v]
        cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        dot = sum(i*j for i, j in zip(u, v))
        if math.atan2(math.hypot(*cross), abs(dot)) > angular:
            return False
        d = [i-j for i, j in zip(x["origin"], y["origin"])]
        distance = math.hypot(*(d[i] - sum(d[j]*u[j] for j in range(3))*u[i] for i in range(3)))
        if distance > linear:
            return False
    return True


def unique_binding(left, left_id, right, *, linear, angular):
    """Require reciprocal single candidates, even if a global pairing exists."""
    source = left["faces"][left_id]
    matches = [ident for ident, face in right["faces"].items()
               if compatible(left, source, right, face, linear=linear, angular=angular)]
    if len(matches) != 1:
        _fail("semantic correspondence missing or ambiguous")
    target = right["faces"][matches[0]]
    reverse = [ident for ident, face in left["faces"].items()
               if compatible(right, target, left, face, linear=linear, angular=angular)]
    if reverse != [left_id]:
        _fail("semantic correspondence is not reciprocal and unique")
    return matches[0]


def adjacency_members(p1, relation_ids, swept_ids):
    """Partition all Swept observations by direct reciprocal P1 incidence."""
    if len(relation_ids) != 22 or len(set(relation_ids)) != 22 or len(swept_ids) != 44:
        _fail("wrong decision member or Swept count")
    remaining, result = Counter(), {}
    for cylinder in relation_ids:
        face = p1["faces"][cylinder]
        if face["surface_type"] != "Cylindrical":
            _fail("decision member is not a cylinder")
        for eid in face["edge_ids"]:
            edge = p1["edges"][eid]
            if cylinder not in edge["face_ids"] or any(eid not in p1["faces"][fid]["edge_ids"] for fid in edge["face_ids"]):
                _fail("non-reciprocal P1 adjacency")
        neighbors = {other for eid in face["edge_ids"] for other in p1["edges"][eid]["face_ids"]
                     if other != cylinder and other in swept_ids}
        if len(neighbors) != 2:
            _fail("member does not have exactly two adjacent Swept faces")
        result[cylinder] = sorted(neighbors)
        remaining.update(neighbors)
    if set(remaining) != set(swept_ids) or any(v != 1 for v in remaining.values()):
        _fail("Swept faces do not form a unique 22 by 2 partition")
    return result


def _relation(root, decision, inventory):
    """Read the accepted decision and its accepted plan without re-running recognition."""
    plan = read_json(_file(root, RELATION_PATH))
    intents = plan.get("relation_intents")
    binding = decision.get("observation_binding", {})
    if (decision.get("schema") != "v3-user-design-decision/1.0"
            or decision.get("decision_id") != "P3-USER-22-SHARED-01"
            or decision.get("authority") != "explicit user reply in this conversation"
            or decision.get("scope") != {"shared_cylinder_radius": True, "shared_pitch_circle_radius": True,
                                         "shared_phase": True, "equal_angular_spacing": True, "fixed_count": 22}
            or type(decision["scope"]["fixed_count"]) is not int
            or not isinstance(intents, list) or len(intents) != 1):
        _fail("invalid accepted relation decision")
    intent = intents[0]
    reference_path = binding.get("analysis_path")
    reference = read_json(_file(root, reference_path))
    candidates = [c for c in reference.get("candidates", []) if c.get("id") in binding.get("candidate_ids", [])]
    circular = [c for c in candidates if c.get("kind") == "possible_circular_axis_spacing"]
    accepted = [c for c in plan.get("candidates", []) if c.get("id") in binding.get("candidate_ids", [])]
    if (len(candidates) != 2 or len(accepted) != 2 or len(circular) != 1
            or len(circular[0].get("evidence", [])) != 1
            or {c.get("id") for c in candidates} != set(binding.get("candidate_ids", []))
            or any(c not in accepted for c in candidates)
            or any(c.get("snapshot_id") != binding.get("snapshot_id") for c in candidates)
            or any(set(c.get("source_faces", [])) != set(binding.get("source_face_ids", [])) for c in candidates)):
        _fail("decision candidate evidence missing")
    fit = circular[0]["evidence"][0]
    expected_ids = binding.get("source_face_ids")
    members = intent.get("members")
    frame_keys = ("axis_point", "axis_direction", "plane_basis_u", "plane_basis_v")
    if (reference.get("snapshot_id") != binding.get("snapshot_id")
            or inventory["snapshot_id"] != binding.get("snapshot_id")
            or intent.get("snapshot_id") != binding.get("snapshot_id")
            or intent.get("decision_id") != decision["decision_id"]
            or intent.get("reference_analysis_path") != reference_path
            or intent.get("schema") != "p3-relation-intent/1.0" or intent.get("status") != "user_confirmed_relation_intent"
            or intent.get("fixed_count") != 22 or intent.get("length_unit") != inventory["unit"]
            or intent.get("angle_convention") != "atan2(delta dot plane_basis_v, delta dot plane_basis_u)"
            or intent.get("frame") != {k: fit.get(k) for k in frame_keys}
            or not isinstance(expected_ids, list) or len(expected_ids) != 22 or len(set(expected_ids)) != 22
            or not isinstance(members, list) or len(members) != 22
            or [m.get("index") for m in members] != list(range(22))
            or len({m.get("face_id") for m in members}) != 22
            or {m.get("face_id") for m in members} != set(expected_ids)
            or [(m.get("face_id"), m.get("observed_angle_rad")) for m in members]
               != [(m.get("face_id"), m.get("angle")) for m in fit.get("ordered_face_angles_rad", [])]):
        _fail("accepted relation does not match its original observation/frame/order")
    return intent


def _validate_legacy(queue, evidence, label):
    names = queue.once.FILES
    if any(not queue.inside(evidence / n, evidence) for n in names):
        _fail("legacy evidence missing or escaped")
    summary, takeover, snapshot, status = (read_json(evidence / n) for n in names)
    request = summary.get("detail_request", {})
    selectors = request.get("selectors", [])
    pid, epoch = summary.get("pid"), takeover.get("session_epoch")
    if (type(pid) is not int or pid <= 0 or type(status.get("pid")) is not int
            or status["pid"] != pid or not isinstance(epoch, str) or len(epoch) > 40
            or re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", epoch, re.ASCII) is None
            or not epoch.startswith(str(pid) + ":")
            or int(epoch.split(":")[1]) > 3155378975999999999):
        _fail("legacy process or canonical session epoch invalid")
    if (summary.get("status") != "RETURNED" or summary.get("return") != "HUMAN_OWNED"
            or summary.get("inspection") != "response_recorded" or summary.get("geometry") != "INCONCLUSIVE"
            or summary.get("takeover") != "AI_OWNED" or summary.get("p1_snapshot_id") != P1_ID
            or not isinstance(selectors, list) or sum(s.get("label") == label for s in selectors) != 1
            or takeover.get("ok") is not True or takeover.get("ownership_state") != "AI_OWNED"
            or takeover.get("artifact_scope") != "saved_independent_copy" or takeover.get("part_path") != summary.get("part")
            or status.get("ok") is not True or status.get("ownership_state") != "AI_OWNED"
            or status.get("pid") != summary.get("pid") or status.get("writes_halted") is not False
            or snapshot.get("writes_halted") is not False
            or takeover.get("session_epoch") != status.get("session_epoch")
            or takeover.get("session_epoch") != snapshot.get("session_epoch")
            or type(takeover.get("binding_epoch")) is not int or takeover["binding_epoch"] <= 0
            or takeover.get("binding_epoch") != status.get("binding_epoch")
            or takeover.get("binding_epoch") != snapshot.get("binding_epoch")
            or not isinstance(takeover.get("load_instance_id"), str) or not takeover["load_instance_id"]
            or takeover.get("load_instance_id") != status.get("load_instance_id")
            or takeover.get("load_instance_id") != snapshot.get("load_instance_id")
            or not isinstance(takeover.get("revision_id"), str) or not takeover["revision_id"]
            or takeover.get("revision_id") != snapshot.get("revision_id")
            or not queue.once.clean_diagnostic_response(snapshot, summary.get("evidence_id"), selectors)):
        _fail("legacy evidence does not establish clean returned ownership")
    return summary, snapshot


def _normalize_source(root, summary, snapshot, evidence):
    detail_path = _relative(root, evidence / "detail-snapshot.json")
    summary_path = _relative(root, evidence / "detail-summary.json")
    inv = normalize_detail_snapshot(snapshot, summary=summary, evidence_path=detail_path,
                                    summary_path=summary_path, tolerances=THRESHOLDS)
    if inv["unit"] != "mm" or inv["coordinate_system"] != "absolute_part_coordinates":
        _fail("unsupported evidence frame or units")
    return inv, detail_path, summary_path


def _closed_queue(root, queue):
    """Revalidate the completed chain without exposing its private context."""
    run = (root / NEW_RUN).resolve(strict=True)
    if (run / "LOCK.json").exists() or (run / "STOP.json").exists():
        _fail("completed run has a lock or STOP")
    context = read_json(run / "context.json")
    queue.check_context(context, run)
    plan = read_json(run / "plan.json")
    if Path(plan.get("inherit_run", "")).resolve(strict=True) != (root / OLD_RUN).resolve(strict=True):
        _fail("unexpected inherited run")
    if plan != queue.expected_plan(context, run, plan.get("inherit_run")):
        _fail("completed queue plan differs from validated chain")
    if len(plan["selectors"]) != 33 or queue.completed_prefix(run, context, plan["selectors"], queue.validate_evidence) != 33:
        _fail("completed queue is not fully validated")
    experiment = run.parent
    completion = read_json(experiment / "completion-manifest.json")
    entries = completion.get("items")
    if (completion.get("schema") != "p3-swept-completion-manifest/1" or completion.get("new_count") != 33
            or type(completion.get("new_count")) is not int or not isinstance(entries, list) or len(entries) != 33
            or completion.get("previous_pause_manifest") != "workspace/v3/p3/P3-SWEPT-01/pause-manifest.json"):
        _fail("completed queue manifest invalid")
    for index, (entry, selector) in enumerate(zip(entries, plan["selectors"]), 1):
        item = run / f"item-{index:02d}-{selector['label']}"
        summary = read_json(item / "evidence/detail-summary.json")
        expected_paths = {"summary": item / "evidence/detail-summary.json", "snapshot": item / "evidence/detail-snapshot.json",
                          "dispatch": item / "DISPATCHED.json", "clean": item / "CLEAN.json"}
        if (not isinstance(entry, dict) or type(entry.get("index")) is not int or entry["index"] != index
                or entry.get("label") != selector["label"] or entry.get("snapshot_id") != summary.get("evidence_id")
                or entry.get("return") != "HUMAN_OWNED" or entry.get("geometry") != "INCONCLUSIVE"
                or any(_file(root, entry.get(key)) != path.resolve(strict=True) for key, path in expected_paths.items())):
            _fail("completed queue manifest differs from original evidence")
    preservation = read_json(experiment / "shutdown-preservation.json")
    processes = read_json(experiment / "shutdown-processes.json")
    copy = read_json(experiment / "source-copy-record.json")
    source = Path(queue.once.SOURCE).resolve(strict=True)
    before = (experiment / "source-before.prt").resolve(strict=True)
    part = Path(context["part"]).resolve(strict=True)
    if (preservation.get("nx_pid") != context["pid"] or preservation.get("normal_exit") is not True
            or preservation.get("saved") is not False or preservation.get("source_bytes_unchanged") is not True
            or preservation.get("work_bytes_unchanged") is not True or preservation.get("source_mtime_ns_unchanged") is not True
            or preservation.get("force_kill") is not False or preservation.get("dll_hot_replaced") is not False
            or processes.get("observed") != [] or processes.get("controlled_pid") != context["pid"]
            or processes.get("controlled_pid_absent") is not True
            or not part.is_relative_to(experiment) or Path(copy.get("source_path", "")).resolve() != source
            or Path(copy.get("working_copy_path", "")).resolve() != part
            or Path(copy.get("before_path", "")).resolve() != before
            or type(copy.get("source_mtime_ns")) is not int or copy["source_mtime_ns"] != source.stat().st_mtime_ns
            or source.read_bytes() != before.read_bytes() or part.read_bytes() != before.read_bytes()):
        _fail("completed queue shutdown or source preservation not established")
    old = (root / OLD_RUN).resolve(strict=True)
    old_plan = read_json(old / "plan.json")
    return [(old / f"item-{i + 1:02d}-{s['label']}" / "evidence", s)
            for i, s in enumerate(old_plan["selectors"][:9])] + [
            (run / f"item-{i + 1:02d}-{s['label']}" / "evidence", s)
            for i, s in enumerate(plan["selectors"])]


def build_source_map(repository_root, *, queue):
    """Build one complete offline observation map; no raw context is returned."""
    root = Path(repository_root).resolve(strict=True)
    p1_snapshot = read_json(_file(root, P1_PATH))
    p1 = normalize_snapshot(p1_snapshot, tolerances=THRESHOLDS)
    if (p1["snapshot_id"] != P1_ID or p1["unit"] != "mm"
            or p1_snapshot.get("inventory", {}).get("coordinate_system") != "absolute_part_coordinates"):
        _fail("unexpected P1 source")
    flank_decision = read_json(_file(root, FLANK_DECISION_PATH))
    if (flank_decision.get("decision_id") != "P3-USER-INDEPENDENT-FLANK-SPLINES-01"
            or flank_decision.get("scope") != {"independent_editable_flanks": True, "preserve_original_differences": True,
                                               "control_point_dimensions_and_endpoint_constraints": True,
                                               "fix_each_original_order_and_knot_vector": True}):
        _fail("independent flank decision mismatch")
    records = _closed_queue(root, queue)
    all_sources = [(root / path, label, None) for label, path in LEGACY.items()]
    all_sources += [(path, selector["label"], selector) for path, selector in records]
    if len(all_sources) != 44 or len({label for _, label, _ in all_sources}) != 44:
        _fail("source count or label uniqueness mismatch")
    raw, inventories, snapshot_ids = {}, {}, set()
    for evidence, label, selector in all_sources:
        evidence = evidence.resolve(strict=True)
        if not evidence.is_relative_to(root):
            _fail("evidence outside repository")
        if selector is None:
            summary, snapshot = _validate_legacy(queue, evidence, label)
        else:
            summary = read_json(evidence / "detail-summary.json")
            snapshot = read_json(evidence / "detail-snapshot.json")
            if summary.get("detail_request", {}).get("selectors") != [selector]:
                _fail("source selector differs from dispatched plan")
        inv, detail_path, summary_path = _normalize_source(root, summary, snapshot, evidence)
        if inv["snapshot_id"] in snapshot_ids:
            _fail("duplicate detail snapshot across source records")
        snapshot_ids.add(inv["snapshot_id"])
        matches = [fid for fid, detail in inv["detail_faces"].items() if detail["label"] == label]
        if len(matches) != 1:
            _fail("detail label is missing or ambiguous")
        fid = matches[0]
        p1_face = unique_binding(inv, fid, p1, **THRESHOLDS)
        if p1_face != label:
            _fail("selector label does not agree with independent semantic binding")
        candidates = [c for c in recognize(inv) if c["source_faces"] == [fid]]
        if len(candidates) != 1 or candidates[0]["kind"] != "possible_extruded_spline_surface":
            _fail("unsupported or incomplete Swept generator observation")
        observed = candidates[0]["evidence"][0]
        raw[p1_face] = {"p1_face_id": p1_face, "selection_label": label,
                        "detail_snapshot_id": inv["snapshot_id"], "detail_face_id": fid,
                        "detail_edge_ids": deepcopy(candidates[0]["source_edges"]),
                        "detail_path": detail_path, "summary_path": summary_path,
                        "selector": deepcopy(next(s for s in summary["detail_request"]["selectors"] if s["label"] == label)),
                        "unit": inv["unit"], "coordinate_system": inv["coordinate_system"],
                        "original_generator": deepcopy(observed["generator"]),
                        "extrusion_direction_observed": deepcopy(observed["direction"]),
                        "uv_box": deepcopy(observed["uv_box"]), "uv_unit": "unknown",
                        "trim_status": "unverified", "geometry_proven": False,
                        "id_scope": "detail face and edge IDs are local to detail_snapshot_id"}
        inventories[label] = inv
    if len(raw) != 44:
        _fail("multiple detail records map to the same P1 face")
    decision_sources = flank_decision.get("observation_sources")
    if not isinstance(decision_sources, list) or len(decision_sources) != 2:
        _fail("independent flank decision sources missing")
    for source in decision_sources:
        label = source.get("label")
        if label not in LEGACY or label not in raw:
            _fail("unsupported independent flank source")
        record = raw[label]; generator = record["original_generator"]
        basis = {"order": generator["order"], "knots": generator["knots"],
                 "full_domain": [generator["start"], generator["end"]],
                 "num_poles": generator["num_poles"], "rational": generator["rational"]}
        if (source.get("snapshot_id") != record["detail_snapshot_id"] or source.get("detail_path") != record["detail_path"]
                or source.get("summary_path") != record["summary_path"] or source.get("observed_basis") != basis):
            _fail("independent flank source or original basis mismatch")
    if {s.get("label") for s in decision_sources} != set(LEGACY):
        _fail("independent flank source labels are duplicated or missing")
    decision = read_json(_file(root, DECISION_PATH))
    anchor = inventories["F0002"]
    intent = _relation(root, decision, anchor)
    relation_ids = [m["face_id"] for m in intent["members"]]
    mapped = [unique_binding(anchor, fid, p1, **THRESHOLDS) for fid in relation_ids]
    if len(set(mapped)) != 22:
        _fail("decision members do not map bijectively to P1")
    groups = adjacency_members(p1, mapped, set(raw))
    members = []
    for item, p1_id in zip(intent["members"], mapped):
        members.append({"member_index": item["index"], "observed_angle_rad": item["observed_angle_rad"],
                        "decision_snapshot_face_id": item["face_id"], "p1_cylinder_face_id": p1_id,
                        "p1_swept_face_ids": groups[p1_id], "status": "observation_mapping_only",
                        "flank_order": "unassigned", "shared_shape": "not_assumed"})
    return {"schema": "p3-swept-source-map/0.1", "status": "planning_observations_only",
            "p1_snapshot_id": P1_ID, "p1_path": P1_PATH, "unit": "mm",
            "matching_thresholds": {**THRESHOLDS, "linear_unit": "mm", "angular_unit": "rad"},
            "matching_scope": "absolute-part-coordinate semantic candidate association; thresholds are not shape or accuracy proof",
            "decision": {"path": DECISION_PATH, "decision_id": decision["decision_id"],
                         "decision_snapshot_id": intent["snapshot_id"], "relation_plan": RELATION_PATH,
                         "reference_analysis_path": intent["reference_analysis_path"],
                         "frame": deepcopy(intent["frame"]), "angle_convention": intent["angle_convention"],
                         "scope": deepcopy(decision["scope"]), "flank_decision_path": FLANK_DECISION_PATH},
            "members": members, "swept_sources": [raw[x] for x in sorted(raw)],
            "coverage": {"member_count": 22, "swept_source_count": 44, "geometry_explanations_conferred_by_this_map": 0},
            "open_items": ["cross-session frame correspondence and candidate association need independent validation",
                           "edge-to-generator parameter mapping and complete trim", "closed section and material side",
                           "flank constraints, edit domains and target capability", "whole-part regional DAG and geometry proof"],
            "geometry_proven": False, "execution_approved": False}
