"""Snapshot-local hypotheses from a detailed UF extruded spline surface.

These are observations of a generating surface and its recorded face topology,
not proofs of a complete trimmed face or editable engineering design intent.
"""

from collections.abc import Mapping
from copy import deepcopy
import math


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _spline(curve):
    if not isinstance(curve, Mapping) or curve.get("type") != 102:
        return False
    order, count = curve.get("order"), curve.get("num_poles")
    knots, poles = curve.get("knots"), curve.get("weighted_poles_flat_xyzw")
    start, end = curve.get("start"), curve.get("end")
    if (type(order) is not int or type(count) is not int or not 2 <= order <= count
            or not isinstance(knots, list) or len(knots) != count + order
            or not isinstance(poles, list) or len(poles) != 4 * count
            or not all(_finite(v) for v in knots + poles)
            or any(a > b for a, b in zip(knots, knots[1:]))
            or any(poles[i] <= 0 for i in range(3, len(poles), 4))
            or type(curve.get("rational")) is not bool
            or not _finite(start) or not _finite(end)
            or not knots[order-1] <= start < end <= knots[count]):
        return False
    return True


def _topology_error(root, source_edge_ids, edge_mapping):
    """Check each recorded oriented fin has its own uniquely mapped edge."""
    if not isinstance(root, Mapping) or root.get("type") != 5:
        return "missing face topology root"
    children = root.get("children")
    if not isinstance(children, list) or not children:
        return "missing loops"
    found = []
    for loop_ref in children:
        if not isinstance(loop_ref, Mapping) or loop_ref.get("orientation") not in (-1, 0, 1):
            return "invalid loop orientation"
        loop = loop_ref.get("child")
        if not isinstance(loop, Mapping) or loop.get("type") != 6:
            return "missing loop"
        fins = loop.get("children")
        if not isinstance(fins, list) or not fins:
            return "missing fins"
        for fin_ref in fins:
            if not isinstance(fin_ref, Mapping) or fin_ref.get("orientation") not in (-1, 1):
                return "missing directed fin"
            fin = fin_ref.get("child")
            if (not isinstance(fin, Mapping) or fin.get("type") != 7
                    or fin.get("geometry_rc") != 0 or fin.get("geometry_free_rc") != 0
                    or not _spline(fin.get("geometry"))):
                return "missing or invalid fin geometry"
            edge_refs = fin.get("children")
            if not isinstance(edge_refs, list) or len(edge_refs) != 1:
                return "fin edge is not unique"
            edge_ref = edge_refs[0]
            if not isinstance(edge_ref, Mapping) or edge_ref.get("orientation") not in (-1, 1):
                return "missing directed edge"
            edge = edge_ref.get("child")
            if (not isinstance(edge, Mapping) or edge.get("type") != 8
                    or edge.get("geometry_rc") != 0 or edge.get("geometry_free_rc") != 0
                    or not isinstance(edge.get("geometry"), Mapping)):
                return "missing 3D edge geometry"
            tag = str(edge.get("tag"))
            if tag not in edge_mapping:
                return "edge not uniquely mapped in current snapshot"
            found.append(edge_mapping[tag])
    if len(found) != len(set(found)) or set(found) != set(source_edge_ids):
        return "source edges and topology fins differ or repeat"
    return None


def recognize(inventory):
    """Return one unconfirmed candidate or an unresolved record per swept face."""
    output = []
    for fid, detail in inventory["detail_faces"].items():
        face = inventory["faces"].get(fid, {})
        if face.get("surface_type") != "Swept":
            continue
        diagnostic = detail.get("diagnostic", {})
        root = diagnostic.get("topology") if isinstance(diagnostic, Mapping) else None
        geometry = root.get("geometry", {}) if isinstance(root, Mapping) else {}
        generator = geometry.get("generator") if isinstance(geometry, Mapping) else None
        direction = geometry.get("direction") if isinstance(geometry, Mapping) else None
        source_edges = detail.get("source_edge_ids")
        edge_map = detail.get("source_edges_by_tag")
        reasons = []
        if inventory.get("coordinate_system") != "absolute_part_coordinates":
            reasons.append("absolute part coordinate frame is not established")
        if (detail.get("source_face_id") != fid or not isinstance(source_edges, list)
                or not source_edges or len(source_edges) != len(set(source_edges))
                or set(source_edges) != set(face.get("edge_ids", []))
                or not isinstance(edge_map, Mapping) or set(edge_map.values()) != set(source_edges)
                or len(edge_map) != len(source_edges)
                or any(eid not in inventory["edges"] or str(inventory["edges"][eid]["source_tag"]) != tag
                       for tag, eid in edge_map.items())):
            reasons.append("source face or edge linkage is incomplete or nonunique")
        if face.get("native_face_data", {}).get("uf_type") != 20 or not isinstance(geometry, Mapping) or geometry.get("type") != 206:
            reasons.append("surface is not the supported UF20 extruded surface")
        if not _spline(generator):
            reasons.append("generating spline definition is absent or invalid")
        if (not isinstance(direction, list) or len(direction) != 3 or not all(_finite(v) for v in direction)
                or math.hypot(*direction) <= 0):
            reasons.append("linear generating direction is absent or invalid")
        if not isinstance(root, Mapping) or str(root.get("tag")) != str(face.get("source_tag")):
            reasons.append("topology root does not uniquely identify this snapshot face")
        if (not isinstance(diagnostic, Mapping) or diagnostic.get("edge_coverage_complete") is not True
                or not isinstance(root, Mapping) or root.get("geometry_rc") != 0 or root.get("geometry_free_rc") != 0):
            reasons.append("native face geometry or edge coverage is incomplete")
        if isinstance(source_edges, list) and isinstance(edge_map, Mapping):
            topology_error = _topology_error(root, source_edges, edge_map)
            if topology_error:
                reasons.append(topology_error)
        else:
            reasons.append("directed topology cannot be checked")
        candidate = {
            "id": "detail_extrusion_" + fid, "snapshot_id": inventory["snapshot_id"],
            "kind": "unresolved_detail_extrusion" if reasons else "possible_extruded_spline_surface",
            "coverage_role": "observation", "source_faces": [fid],
            "source_edges": list(source_edges) if isinstance(source_edges, list) else [],
            "evidence": [{"type": "native_detail", "snapshot_id": inventory["snapshot_id"],
                          "source_face_id": fid, "source_edge_ids": deepcopy(source_edges),
                          "evidence_path": detail.get("evidence_path"), "summary_path": detail.get("summary_path"),
                          "coordinate_system": inventory.get("coordinate_system"), "length_unit": inventory["unit"],
                          "generator": deepcopy(generator), "direction": deepcopy(direction),
                          "uv_box": deepcopy(diagnostic.get("uv_box")) if isinstance(diagnostic, Mapping) else None,
                          "uv_unit": "unknown", "topology": deepcopy(root),
                          "source_edges_by_tag": deepcopy(edge_map),
                          "native_status": diagnostic.get("status") if isinstance(diagnostic, Mapping) else None,
                          "edge_coverage_complete": diagnostic.get("edge_coverage_complete") if isinstance(diagnostic, Mapping) else False,
                          "root_complete": False,
                          "basis": "native generatrix and oriented face topology; no complete trim or surface equivalence proof"}],
            "parameters": [],
            "alternatives": ["editable spline generator with separately determined trim and translation", "different construction with equivalent verified geometry"],
            "open_items": ["The exact UV scale and domain mapping to part length are unknown; UV differences are not lengths and the bounding box is not cut or extrusion depth.",
                           "Complete trimmed surface, face-loop semantics and geometric equivalence require independent verification; finite edge samples would not establish a whole-surface proof.",
                           "Determine and confirm engineering driving dimensions, allowable edit ranges, geometric relationships and construction history; fixed spline control points alone are not a complete engineering parameterization."] + reasons,
            "capability_requirements": ["T04.a: verify trimmed spline-extrusion surface and target-version editable construction", "confirm engineering parameters and relationships", "establish UV-to-geometry mapping and compare complete boundary"],
            "depends_on": [], "confirmed": False, "confirmation": {"status": "unconfirmed"}, "execution_approved": False,
        }
        if not reasons:
            candidate["parameters"] = [
                {"id": "generator_order", "dimension": "scalar", "value": generator["order"], "unit": "1", "classification": "unclassified", "confirmation": "unconfirmed"},
                {"id": "generator_pole_count", "dimension": "scalar", "value": generator["num_poles"], "unit": "1", "classification": "unclassified", "confirmation": "unconfirmed"},
            ]
        output.append(candidate)
    return output
