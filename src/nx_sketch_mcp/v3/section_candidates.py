"""Offline, evidence-scoped planning contract for the two selected flanks.

This is not V3 IR, a geometry proof, a constraint solver, or an executor. It
reads the user decision and the two recorded clean detail snapshots; no NX
session, model mutation, curve fitting, or implicit snapshot rebinding occurs.
"""
from copy import deepcopy
import json
import math
from pathlib import Path, PurePosixPath

from .regions.detail_common import normalize_detail_snapshot
from .regions.detail_extrusions import recognize


class SectionCandidateError(ValueError):
    """Decision or source evidence is outside this planning contract."""


_SOURCES = {
    "F0002": "P3-DETAIL-3444b40a6faa4210ad64c45f344b27be",
    "F0024": "P3-DETAIL-9c1ee4cf468e48b18b3ebe75d65df6b5",
}
_SCOPE_KEYS = ("independent_editable_flanks", "preserve_original_differences",
               "control_point_dimensions_and_endpoint_constraints", "fix_each_original_order_and_knot_vector")
_STOCK_PATH = "docs/v3/sample-regional-workbreakdown.json"


def _fail(message):
    raise SectionCandidateError("section candidate: " + message)


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            _fail("duplicate JSON key")
        out[key] = value
    return out


def _read(path):
    def reject_constant(value):
        _fail("non-finite JSON value: " + value)
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs,
                          parse_constant=reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SectionCandidateError("section candidate: unreadable evidence") from exc


def _source_path(root, relative):
    if (not isinstance(relative, str) or not relative.strip() or "\\" in relative or ":" in relative):
        _fail("invalid repository-relative source path")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in (".", "..") for part in path.parts):
        _fail("source path must remain in repository")
    try:
        result = root.joinpath(*path.parts).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SectionCandidateError("section candidate: missing source") from exc
    if not result.is_relative_to(root) or not result.is_file():
        _fail("source path must name a repository file")
    return result


def _node(ident, kind, depends_on, requirements):
    return {"id": ident, "kind": kind, "depends_on": depends_on,
            "status": "blocked", "requirements": [{"kind": item, "status": "open"} for item in requirements],
            "execution_approved": False}


def _stock_candidate(root):
    work = _read(_source_path(root, _STOCK_PATH))
    if (not isinstance(work, dict) or work.get("schema") != "v3-sample-regional-workbreakdown/1.0"
            or work.get("snapshot_id") != "P1-REFERENCE-7812d302a165453badcd339473b5dba3"):
        _fail("stock work breakdown source mismatch")
    stock = work.get("y_axis_outer_stock_candidate")
    if not isinstance(stock, dict) or stock.get("status") != "provisional":
        _fail("provisional stock candidate required")
    segments = stock.get("segments")
    evidence = stock.get("minimal_meridian_native_evidence")
    selectors = evidence.get("selectors") if isinstance(evidence, dict) else None
    if (not isinstance(segments, list) or len(segments) != 20 or any(not isinstance(s, dict) for s in segments)
            or not isinstance(selectors, list) or any(not isinstance(s, dict) for s in selectors)
            or {s.get("face_id") for s in selectors} != {"F0169", "F0167", "F0066"}
            or len(selectors) != 3 or not isinstance(stock.get("assumptions"), list)
            or not isinstance(stock.get("closure"), str) or not stock["closure"].strip()):
        _fail("incomplete stock planning source")
    return {"source_path": _STOCK_PATH, "source_snapshot_id": work["snapshot_id"],
            "status": "provisional", "frame_and_units": stock.get("frame_and_units"),
            "segments": deepcopy(segments), "assumptions": deepcopy(stock["assumptions"]),
            "proposed_closure": stock["closure"],
            "unresolved_carriers": ["F0169", "F0167", "F0066"],
            "section_closed_and_validated": False, "full_rotation_verified": False,
            "material_role_confirmed": False, "execution_approved": False}


def load_section_candidate(decision_path, *, repository_root):
    """Bind the user decision to its two on-disk source snapshots and summaries.

    The source records are read directly using their decision paths. Their
    normalizer validates the recorded returned-ownership clean evidence and
    snapshot-local face/edge links. The historical selection labels are not NX
    tags and do not establish a shared frame or an equality across sessions.
    """
    try:
        root = Path(repository_root).resolve(strict=True)
        decision_file = Path(decision_path).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SectionCandidateError("section candidate: missing root or decision") from exc
    if not root.is_dir() or not decision_file.is_relative_to(root) or not decision_file.is_file():
        _fail("decision must be a file inside the repository")
    decision = _read(decision_file)
    if (not isinstance(decision, dict) or decision.get("schema") != "v3-user-design-decision/1.0"
            or decision.get("decision_id") != "P3-USER-INDEPENDENT-FLANK-SPLINES-01"
            or decision.get("authority") != "explicit user reply in this conversation"
            or decision.get("answer") != "接受两条独立可编辑样条"):
        _fail("unsupported user decision")
    scope = decision.get("scope")
    if not isinstance(scope, dict) or set(scope) != set(_SCOPE_KEYS) or any(scope[k] is not True for k in _SCOPE_KEYS):
        _fail("unsupported or incomplete user decision scope")
    sources = decision.get("observation_sources")
    if not isinstance(sources, list) or len(sources) != 2 or any(not isinstance(x, dict) for x in sources):
        _fail("exactly two source observations required")
    stock_candidate = _stock_candidate(root)
    by_label = {}
    for source in sources:
        label = source.get("label")
        if label not in _SOURCES or label in by_label or source.get("snapshot_id") != _SOURCES[label]:
            _fail("source label or snapshot mismatch")
        if any(not isinstance(source.get(k), str) or not source[k].strip()
               for k in ("selection_evidence", "source_locator_scope")):
            _fail("selection evidence required")
        by_label[label] = source
    curves = []
    for label in ("F0002", "F0024"):
        source = by_label[label]
        detail_path = _source_path(root, source.get("detail_path"))
        summary_path = _source_path(root, source.get("summary_path"))
        snapshot, summary = _read(detail_path), _read(summary_path)
        if not isinstance(snapshot, dict) or snapshot.get("snapshot_id") != source["snapshot_id"]:
            _fail("detail snapshot mismatch")
        try:
            inventory = normalize_detail_snapshot(snapshot, summary=summary, evidence_path=str(detail_path),
                                                  summary_path=str(summary_path),
                                                  tolerances={"linear": 0.001, "angular": 0.0001})
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise SectionCandidateError("section candidate: invalid detail evidence") from exc
        if inventory.get("snapshot_id") != source["snapshot_id"]:
            _fail("normalized snapshot mismatch")
        matching = [(fid, item) for fid, item in inventory["detail_faces"].items() if item.get("label") == label]
        if len(matching) != 1:
            _fail("selected face label is missing or ambiguous")
        fid, detail = matching[0]
        candidates = [x for x in recognize(inventory) if x.get("source_faces") == [fid]]
        if len(candidates) != 1 or candidates[0].get("kind") != "possible_extruded_spline_surface":
            _fail("valid extruded spline observation required")
        candidate = candidates[0]
        evidence = candidate["evidence"][0]
        generator = evidence["generator"]
        observed = {"order": generator["order"], "knots": generator["knots"],
                    "full_domain": [generator["start"], generator["end"]],
                    "num_poles": generator["num_poles"], "rational": generator["rational"]}
        basis = source.get("observed_basis")
        if (not isinstance(basis, dict) or basis != observed or type(basis.get("order")) is not int
                or type(basis.get("num_poles")) is not int or basis.get("rational") is not False
                or not isinstance(basis.get("knots"), list) or not isinstance(basis.get("full_domain"), list)
                or any(type(value) not in (int, float) or not math.isfinite(value)
                       for value in basis["knots"] + basis["full_domain"])
                or type(generator["order"]) is not int
                or generator["order"] != 4 or generator["num_poles"] != 7 or generator["rational"] is not False
                or any(weight != 1 for weight in generator["weighted_poles_flat_xyzw"][3::4])):
            _fail("observed basis differs from decision or unsupported source basis")
        curves.append({
            "id": "flank_" + label, "kind": "sketch_bspline_segment_candidate",
            "source": {"selection_label": label, "snapshot_id": inventory["snapshot_id"],
                       "snapshot_face_id": fid, "source_edge_ids": deepcopy(candidate["source_edges"]),
                       "detail_path": source["detail_path"], "summary_path": source["summary_path"],
                       "selection_evidence": source["selection_evidence"],
                       "locator_scope": source["source_locator_scope"]},
            "native_frame": {"inventory_coordinate_system": inventory["coordinate_system"],
                             "generator_to_inventory_mapping": "unverified"},
            "length_unit": inventory["unit"], "extrusion_direction_observed": deepcopy(evidence["direction"]),
            "original_generator": deepcopy(generator),
            "original_basis_policy": "fixed original order and knot vector for this source only",
            "face_uv_box": {"values": deepcopy(evidence["uv_box"]), "unit": "unknown",
                            "generator_parameter_mapping": "unverified"},
            "actual_generator_trim": {"interval": None, "status": "unverified"},
            "endpoint_constraints": [
                {"id": "start_" + label, "endpoint": "C(a)", "parameter": None,
                 "kind": "point_on_carrier_proposed", "carrier": None, "status": "unresolved"},
                {"id": "end_" + label, "endpoint": "C(b)", "parameter": None,
                 "kind": "point_on_carrier_proposed", "carrier": None, "status": "unresolved"}],
            "driving_parameters": [], "control_point_usage": "unknown_until_actual_trim_and_consumers_verified",
            "edit_domain": "unconfirmed", "confirmed_geometry": False,
            "requirements": [{"kind": name, "status": "open"} for name in (
                "native_to_common_frame", "uv_to_generator_mapping", "actual_trim_and_direction",
                "endpoint_carrier_correspondence", "control_point_active_support_and_consumers",
                "constraint_solvability_and_edit_domains", "complete_trimmed_geometry")],
            "execution_approved": False,
        })
    return {
        "schema": "p3-section-candidate/0.1", "status": "planning_only",
        "decision": {"id": decision["decision_id"], "evidence_path": decision_file.relative_to(root).as_posix(),
                     "status": "user_confirmed_expression_intent", "scope": deepcopy(scope)},
        "curves": curves,
        "stock_candidate": stock_candidate,
        "pair_relationship": {"independent_shapes": True, "reflection_or_equal_shape": "not_assumed",
                              "shared_22_complete_shape": "unconfirmed", "common_section_frame": "unverified"},
        "nodes": [
            _node("flank_F0002", "sketch_bspline_segment", [], ["verified_trim", "active_support_and_consumers", "endpoint_mapping"]),
            _node("flank_F0024", "sketch_bspline_segment", [], ["verified_trim", "active_support_and_consumers", "endpoint_mapping"]),
            _node("local_flank_loop", "sketch_loop", ["flank_F0002", "flank_F0024"],
                  ["common_frame", "all_oriented_boundary_segments", "closed_loop_evidence"]),
            _node("stock_meridian", "stock_section_candidate", [],
                  ["meridian_carriers_and_trims", "closed_section_evidence", "stock_construction_assumptions"]),
            _node("stock_revolve", "revolve_candidate", ["stock_meridian"],
                  ["sweep_extent_and_axis", "material_role", "target_backend_capability"]),
            _node("local_modification", "cut_or_add_candidate", ["stock_revolve", "local_flank_loop"],
                  ["material_side_and_operation_kind", "depth_or_termination", "boolean_order", "target_backend_capability"]),
        ],
        "open_items": ["source-frame correspondence and complete trims", "endpoint carrier and direction evidence",
                       "active control-point support, consumers and edit ranges", "stock carrier and closure evidence",
                       "material side, boolean operation and construction order", "full 22-member geometry equivalence"],
        "geometry_proven": False, "edit_domains_confirmed": False, "execution_approved": False,
    }
