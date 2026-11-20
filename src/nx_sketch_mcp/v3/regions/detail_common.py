"""Normalize a guarded P3 detail snapshot without promoting geometry claims.

The supplied paths are provenance labels for already loaded evidence; this
module never opens PRTs or other files. Callers must load those exact records.
All source tags and logical IDs are limited to this snapshot and cannot select
entities in another NX session.
"""
from collections.abc import Mapping
from copy import deepcopy
import json

from .common import InventoryError, _index, _links, _list, _mapping, _number, _text, _vector


def _same(a, b):
    try:
        return json.dumps(a, sort_keys=True, allow_nan=False, separators=(",", ":")) == json.dumps(
            b, sort_keys=True, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError, OverflowError) as exc:
        raise InventoryError("evidence: values cannot be compared as finite JSON") from exc


def _tag(value, where):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InventoryError(f"{where}: expected positive native tag")
    return str(value)


def _clean_trace(probe, face_tag, part_tag, edge_types):
    if (probe.get("schema") != "v3-reference-geometry-probe-v3" or probe.get("outcome") != "CLEAN_TRACE"
            or probe.get("first_dirty_sequence") is not None or probe.get("event_overflow") is not False
            or probe.get("geometry_overflow") is not False or probe.get("edge_coverage_complete") is not True
            or probe.get("incomplete_observed") is not False):
        raise InventoryError("detail: native trace or geometry is incomplete")
    if _tag(probe.get("face_tag"), "detail.face_tag") != face_tag or _tag(probe.get("part_tag"), "detail.part_tag") != part_tag:
        raise InventoryError("detail: native identity differs from inventory")
    events = _list(probe.get("events"), "detail.events")
    if not events:
        raise InventoryError("detail: missing native events")
    cleanup_stages = {"UF_BREP_free_geometry_data", "UF_BREP_release_topology", "UF_free_states", "UF_EVAL_free"}
    void_stages = {"UF_BREP_ask_identifier", "UF_free_states"}
    known_stages = cleanup_stages | void_stages | {
        "UF_MODL_ask_face_uv_minmax", "UF_BREP_ask_topology", "UF_BREP_ask_edge_class",
        "UF_BREP_ask_geometry", "UF_CSYS_ask_matrix_values", "UF_EVAL_initialize_2", "UF_EVAL_is_arc",
        "UF_EVAL_ask_limits", "UF_EVAL_is_periodic", "UF_EVAL_ask_arc"}
    eval_stages = ("UF_EVAL_initialize_2", "UF_EVAL_is_arc", "UF_EVAL_ask_limits",
                   "UF_EVAL_is_periodic", "UF_EVAL_ask_arc", "UF_EVAL_free")
    pending, eval_state, visited = {}, {}, set()
    release_count = uv_count = topology_count = geometry_count = 0
    for index, event in enumerate(events, 1):
        if (not isinstance(event, Mapping) or type(event.get("sequence")) is not int or event["sequence"] != index or event.get("called") is not True
                or event.get("dirty_before") is not False or event.get("dirty_after") is not False):
            raise InventoryError("detail: native event ordering or dirty state invalid")
        stage = event.get("stage")
        if (not isinstance(stage, str) or stage not in known_stages
                or event.get("cleanup") is not (stage in cleanup_stages) or "uf_rc" not in event):
            raise InventoryError("detail: native event stage/return code missing")
        rc = event["uf_rc"]
        if stage in void_stages:
            if rc is not None:
                raise InventoryError("detail: void native call has unexpected return code")
        elif isinstance(rc, bool) or not isinstance(rc, (int, float)) or rc != 0:
            raise InventoryError("detail: native call did not report success")
        tag, kind = event.get("tag"), event.get("topology_type")
        if type(tag) is not int or tag < 0 or type(kind) is not int or kind < 0:
            raise InventoryError("detail: invalid native event identity")
        if index == 1 and (stage != "UF_MODL_ask_face_uv_minmax" or str(tag) != face_tag):
            raise InventoryError("detail: trace missing initial face UV query")
        if index == 2 and (stage != "UF_BREP_ask_topology" or str(tag) != face_tag):
            raise InventoryError("detail: trace missing initial face topology query")
        if release_count and stage != "UF_free_states":
            raise InventoryError("detail: native query follows topology release")
        if stage == "UF_MODL_ask_face_uv_minmax": uv_count += 1
        if stage == "UF_BREP_ask_topology": topology_count += 1
        if stage == "UF_BREP_release_topology":
            if str(tag) != face_tag: raise InventoryError("detail: released topology identity mismatch")
            release_count += 1
        if stage in eval_stages:
            edge = str(tag)
            if edge_types.get(edge) != "Circular": raise InventoryError("detail: evaluator edge is not a circular source edge")
            step = eval_stages.index(stage)
            if eval_state.get(edge, 0) != step: raise InventoryError("detail: evaluator sequence invalid")
            eval_state[edge] = 0 if step == len(eval_stages) - 1 else step + 1
            if step == 0: visited.add(edge)
        if stage == "UF_BREP_ask_geometry":
            geometry_count += 1
            if kind == 8:
                edge = str(tag)
                if edge not in edge_types or edge_types[edge] == "Circular":
                    raise InventoryError("detail: edge geometry bypasses source type gate")
                visited.add(edge)
            key = (tag, kind); pending[key] = pending.get(key, 0) + 1
        if stage == "UF_BREP_free_geometry_data":
            key = (tag, kind)
            if not pending.get(key): raise InventoryError("detail: native geometry release is unmatched")
            pending[key] -= 1
    if (uv_count != 1 or topology_count != 1 or release_count != 1 or not geometry_count
            or any(pending.values()) or any(eval_state.values()) or visited != set(edge_types)):
        raise InventoryError("detail: native event trace or edge coverage incomplete")


def _edge_tree(topology, expected_face, edge_ids):
    if not isinstance(topology, Mapping) or topology.get("type") != 5 or _tag(topology.get("tag"), "topology.face") != expected_face:
        raise InventoryError("detail: root topology does not identify the matched face")
    seen = set()

    def visit(node, depth):
        if depth > 16 or not isinstance(node, Mapping):
            raise InventoryError("detail: invalid topology tree")
        if node.get("type") == 8:
            tag = _tag(node.get("tag"), "topology.edge")
            if tag not in edge_ids:
                raise InventoryError("detail: topology edge is not in this face inventory")
            seen.add(tag)
        children = _list(node.get("children"), "topology.children")
        for child in children:
            if not isinstance(child, Mapping) or "orientation" not in child or "child" not in child:
                raise InventoryError("detail: missing oriented topology child")
            _number(child["orientation"], "topology.orientation")
            visit(child["child"], depth + 1)

    visit(topology, 0)
    if seen != set(edge_ids):
        raise InventoryError("detail: topology does not cover the face edge inventory")


def normalize_detail_snapshot(snapshot, *, summary, evidence_path, summary_path, tolerances):
    """Return a clean v2/v3 detail inventory with raw topology and provenance.

    ``complete=False`` from the original root is preserved as ``root_complete``;
    a clean inventory and local native definitions do not prove full geometry,
    feature intent, or editable reconstruction.
    """
    doc = _mapping(snapshot, "snapshot")
    summary = _mapping(summary, "summary")
    evidence_path = _text(evidence_path, "evidence_path")
    summary_path = _text(summary_path, "summary_path")
    threshold = _mapping(tolerances, "tolerances")
    if set(threshold) != {"linear", "angular"}:
        raise InventoryError("tolerances: require exactly linear and angular")
    threshold = {key: _number(threshold[key], f"tolerances.{key}") for key in ("linear", "angular")}
    if any(value <= 0 for value in threshold.values()):
        raise InventoryError("tolerances: must be positive")
    if (doc.get("schema") != "v3-reference-detail-v2" or doc.get("ok") is not True
            or doc.get("complete") is not False or doc.get("geometry_details_complete") is not False
            or doc.get("inventory_complete") is not True or doc.get("read_consistency_fault") is not False
            or doc.get("writes_halted") is not False or doc.get("ownership_state") != "AI_OWNED"):
        raise InventoryError("snapshot: detail read is not a clean bounded v2 result")
    snapshot_id = _text(doc.get("snapshot_id"), "snapshot_id")
    if (summary.get("evidence_id") != snapshot_id or summary.get("status") != "RETURNED"
            or summary.get("return") != "HUMAN_OWNED" or summary.get("inspection") != "response_recorded"):
        raise InventoryError("summary: snapshot identity or ownership return is not established")
    if doc.get("first_change") is not None:
        raise InventoryError("snapshot: observed dirty change or diagnostic error")
    comparison = _mapping(doc.get("snapshot_consistency"), "snapshot_consistency")
    diff = _mapping(doc.get("inventory_diff"), "inventory_diff")
    if comparison.get("two_native_samples_equal") is not True or diff.get("status") != "complete" or diff.get("changes") != []:
        raise InventoryError("snapshot: native inventory comparison is not clean and complete")
    before = _mapping(doc.get("inventory_before"), "inventory_before")
    after = _mapping(doc.get("inventory_after"), "inventory_after")
    if not _same(before, after) or not _same(before, doc.get("inventory")):
        raise InventoryError("snapshot: actual inventories differ")
    if before.get("errors") != [] or before.get("selection_resolved") is not True:
        raise InventoryError("snapshot: inventory has errors or unresolved selection")
    if before.get("coordinate_system") != "absolute_part_coordinates":
        raise InventoryError("snapshot: absolute part coordinate system is required")
    if not isinstance(summary.get("part"), str) or summary.get("part") != before.get("part_path"):
        raise InventoryError("summary: part path does not match the inventory")
    unit = {"Millimeters": "mm", "Meters": "m", "Inches": "inch"}.get(before.get("units"))
    if unit is None:
        raise InventoryError("snapshot: unsupported part unit")
    options = _mapping(doc.get("detail_options"), "detail_options")
    if options.get("unit") != before.get("units"):
        raise InventoryError("snapshot: detail and inventory units differ")
    request = _mapping(summary.get("detail_request"), "summary.detail_request")
    for key in ("match_linear", "curve_tolerance", "surface_tolerance"):
        if _number(request.get(key), key) <= 0 or request[key] != options.get(key):
            raise InventoryError("summary: native read options do not match")
    details = _list(doc.get("detail"), "detail")
    selectors = _list(request.get("selectors"), "summary.selectors")
    if len(selectors) not in (1, 2) or len(details) != len(selectors):
        raise InventoryError("detail: one or two requested faces and matching returned faces required")
    if (any(not isinstance(s, Mapping) or not isinstance(s.get("label"), str) or not s["label"].strip() for s in selectors)
            or (len(selectors) == 2 and selectors[0]["label"] == selectors[1]["label"])):
        raise InventoryError("detail: selector labels must be distinct and non-empty")
    if len(selectors) == 2 and all(selectors[0].get(k) == selectors[1].get(k)
                                    for k in ("uf_type", "surface_type", "bounding_box", "edge_count")):
        raise InventoryError("detail: duplicate semantic selectors")
    events = _list(doc.get("diagnostic_events"), "diagnostic_events")
    stages = ["capture_before:pre", "capture_before:post", "selector:pre", "selector:post"]
    for i in range(len(selectors)):
        stages += [f"native:{i}:pre", f"native:{i}", f"native:{i}:post"]
    stages += ["capture_after:pre", "capture_after:post"]
    if len(events) != len(stages):
        raise InventoryError("snapshot: managed diagnostic events missing")
    for index, (event, stage) in enumerate(zip(events, stages), 1):
        if not isinstance(event, Mapping) or type(event.get("sequence")) is not int or event["sequence"] != index or event.get("stage") != stage:
            raise InventoryError("snapshot: managed diagnostic event ordering invalid")
        if stage in {f"native:{i}" for i in range(len(selectors))}:
            if event.get("outcome") != "CLEAN_TRACE" or event.get("native_first_dirty_sequence") is not None:
                raise InventoryError("snapshot: native stage was not clean")
        elif event.get("dirty") is not False:
            raise InventoryError("snapshot: managed dirty observation is not clean")

    body = _mapping(before.get("selected_body"), "selected_body")
    raw_faces, raw_edges = _list(body.get("faces"), "faces"), _list(body.get("edges"), "edges")
    face_ids, edge_ids = _index(raw_faces, "F", "faces"), _index(raw_edges, "E", "edges")
    faces, edges = {}, {}
    face_by_tag = {face["tag"]: face for face in raw_faces}
    for raw in raw_faces:
        fid = face_ids[raw["tag"]]
        native = _mapping(raw.get("native_face_data"), f"{fid}.native_face_data")
        values = {"origin": _vector(native.get("origin"), 3, fid), "direction": _vector(native.get("direction"), 3, fid),
                  "bounding_box": _vector(native.get("bounding_box"), 6, fid),
                  "radius": _number(native.get("radius"), fid), "radius_data": _number(native.get("radius_data"), fid),
                  "normal_sense": _number(native.get("normal_sense"), fid), "uf_type": _number(native.get("uf_type"), fid)}
        if any(values["bounding_box"][i] > values["bounding_box"][i + 3] for i in range(3)):
            raise InventoryError(f"{fid}: invalid bounding box")
        faces[fid] = {"id": fid, "source_tag": raw["tag"], "surface_type": _text(raw.get("surface_type"), fid),
                      "native_face_data": values, "edge_ids": _links(raw, "edge_tags", edge_ids, fid)}
    for raw in raw_edges:
        eid = edge_ids[raw["tag"]]
        edges[eid] = {"id": eid, "source_tag": raw["tag"], "edge_type": _text(raw.get("edge_type"), eid),
                      "face_ids": _links(raw, "face_tags", face_ids, eid)}
    for fid, face in faces.items():
        for eid in face["edge_ids"]:
            if fid not in edges[eid]["face_ids"]:
                raise InventoryError(f"{fid}/{eid}: asymmetric adjacency")
    for eid, edge in edges.items():
        for fid in edge["face_ids"]:
            if eid not in faces[fid]["edge_ids"]:
                raise InventoryError(f"{eid}/{fid}: asymmetric adjacency")

    scoped = {}
    part_tag = _text(before.get("part_tag"), "inventory.part_tag")
    for item, selector in zip(details, selectors):
        item, selector = _mapping(item, "detail item"), _mapping(selector, "selector")
        if (item.get("label") != selector.get("label") or item.get("status") != "MATCHED"
                or type(item.get("matching_count")) is not int or item["matching_count"] != 1):
            raise InventoryError("detail: requested face was not uniquely matched in order")
        observed = _mapping(item.get("observed_face"), "observed_face")
        face_tag = _text(observed.get("tag"), "observed_face.tag")
        if face_tag not in face_ids or not _same(observed, face_by_tag[face_tag]):
            raise InventoryError("detail: matched face is absent or differs from the inventory")
        fid = face_ids[face_tag]
        if fid in scoped:
            raise InventoryError("detail: duplicate selected face")
        face = faces[fid]
        if type(selector.get("uf_type")) is not int or (selector.get("uf_type"), selector.get("surface_type")) not in (
                (16, "Cylindrical"), (17, "Conical"), (18, "Spherical"), (19, "SurfaceOfRevolution"), (20, "Swept"), (22, "Planar")):
            raise InventoryError("detail: unsupported UF surface selector")
        box = _vector(selector.get("bounding_box"), 6, "selector.bounding_box")
        if (selector.get("surface_type") != face["surface_type"] or selector.get("uf_type") != face["native_face_data"]["uf_type"]
                or type(selector.get("edge_count")) is not int or selector["edge_count"] != len(face["edge_ids"])
                or any(abs(box[i] - face["native_face_data"]["bounding_box"][i]) > request["match_linear"] for i in range(6))):
            raise InventoryError("detail: selector does not match the observed face")
        diag = _mapping(item.get("diagnostic"), "detail.diagnostic")
        face_edge_map = {edges[eid]["source_tag"]: eid for eid in face["edge_ids"]}
        face_edge_types = {tag: edges[eid]["edge_type"] for tag, eid in face_edge_map.items()}
        _clean_trace(diag, face_tag, part_tag, face_edge_types)
        _edge_tree(diag.get("topology"), face_tag, face_edge_map)
        _vector(diag.get("uv_box"), 4, "detail.uv_box")
        scoped[fid] = {"source_face_id": fid, "source_edge_ids": list(face["edge_ids"]),
                       "source_edges_by_tag": face_edge_map, "label": item["label"],
                       "evidence_path": evidence_path, "summary_path": summary_path, "diagnostic": deepcopy(diag)}
    return {"contract_version": "detail-inventory/1.0", "snapshot_id": snapshot_id,
            "unit": unit, "coordinate_system": before["coordinate_system"], "tolerances": deepcopy(threshold),
            "geometry_details_complete": False, "root_complete": doc["complete"],
            "faces": faces, "edges": edges, "detail_faces": scoped}
