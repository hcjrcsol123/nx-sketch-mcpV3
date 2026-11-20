"""Snapshot-local sphere carrier observations, conditional on an unverified frame.

Circular carrier compatibility does not establish a trimmed face or feature.
"""
from collections.abc import Mapping
from copy import deepcopy
import math

from .detail_tori import _cross, _dot, _limits, _norm, _number, _unit, _vec


def _finite_tree(value):
    if isinstance(value, Mapping):
        return all(_finite_tree(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite_tree(item) for item in value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return math.isfinite(value)
        except OverflowError:
            return False
    return True


def _arc_match(arc, center, sphere_radius, linear, angular):
    if not isinstance(arc, Mapping) or arc.get("type") != "circular_evaluator" or arc.get("coordinate_system") != "ABS":
        return None
    point, x, y = _vec(arc.get("center")), _vec(arc.get("x_axis")), _vec(arc.get("y_axis"))
    radius = arc.get("radius")
    if (point is None or x is None or y is None or not _number(radius) or radius <= 0
            or not _limits(arc.get("evaluator_limits")) or not _limits(arc.get("arc_limits"))
            or type(arc.get("is_periodic")) is not bool or type(arc.get("arc_is_periodic")) is not bool
            or arc["is_periodic"] != arc["arc_is_periodic"]):
        return None
    if abs(_norm(x) - 1) > angular or abs(_norm(y) - 1) > angular:
        return None
    ux, uy = _unit(x), _unit(y)
    if ux is None or uy is None or abs(_dot(ux, uy)) > math.sin(angular):
        return None
    normal = _unit(_cross(ux, uy))
    if normal is None:
        return None
    delta = tuple(q - c for q, c in zip(point, center))
    axial = _dot(delta, normal)
    off_axis = _norm(tuple(d - axial * n for d, n in zip(delta, normal)))
    residual = abs(math.hypot(_norm(delta), radius) - sphere_radius)
    if not math.isfinite(off_axis) or not math.isfinite(residual) or off_axis > linear or residual > linear:
        return None
    return {"center_normal_offset": off_axis, "sphere_radius_residual": residual}


def _topology(root, edge_map, edge_ids, edges, fid, center, radius, linear, angular):
    if not isinstance(root, Mapping) or root.get("type") != 5 or not isinstance(root.get("children"), list) or not root["children"]:
        raise ValueError("missing face topology or loops")
    found, occurrences = set(), []
    for loop_ref in root["children"]:
        if not isinstance(loop_ref, Mapping) or type(loop_ref.get("orientation")) is not int or loop_ref["orientation"] not in (-1, 0, 1):
            raise ValueError("invalid loop direction")
        loop = loop_ref.get("child")
        if not isinstance(loop, Mapping) or loop.get("type") != 6 or not isinstance(loop.get("children"), list) or not loop["children"]:
            raise ValueError("missing loop or fins")
        for fin_ref in loop["children"]:
            if not isinstance(fin_ref, Mapping) or type(fin_ref.get("orientation")) is not int or fin_ref["orientation"] not in (-1, 1):
                raise ValueError("missing fin direction")
            fin = fin_ref.get("child")
            if not isinstance(fin, Mapping) or fin.get("type") != 7 or not isinstance(fin.get("children"), list) or len(fin["children"]) != 1:
                raise ValueError("invalid fin or edge occurrence")
            if fin.get("geometry_rc") != 0 or fin.get("geometry_free_rc") != 0 or not isinstance(fin.get("geometry"), Mapping):
                raise ValueError("missing native fin geometry")
            edge_ref = fin["children"][0]
            if not isinstance(edge_ref, Mapping) or type(edge_ref.get("orientation")) is not int or edge_ref["orientation"] != fin_ref["orientation"]:
                raise ValueError("missing or inconsistent edge direction")
            edge = edge_ref.get("child")
            if not isinstance(edge, Mapping) or edge.get("type") != 8:
                raise ValueError("missing edge")
            eid = edge_map.get(str(edge.get("tag")))
            source = edges.get(eid, {})
            if (eid is None or source.get("edge_type") != "Circular" or fid not in source.get("face_ids", [])
                    or edge.get("geometry_class") != 10 or edge.get("edge_class_rc") != 0):
                raise ValueError("edge type, adjacency or native class invalid")
            match = _arc_match(edge.get("geometry"), center, radius, linear, angular)
            if match is None:
                raise ValueError("circular edge carrier is invalid or incompatible")
            found.add(eid)
            occurrences.append({"edge_id": eid, "loop_orientation": loop_ref["orientation"],
                                "fin_orientation": fin_ref["orientation"], "edge_orientation": edge_ref["orientation"],
                                "geometry": deepcopy(edge["geometry"]), "analytic_match": match,
                                "direction_relation": "evaluator parameter direction versus fin remains unverified"})
    if found != set(edge_ids):
        raise ValueError("topology does not cover all source edges")
    return occurrences


def recognize(inventory):
    """Return one conditional carrier candidate or unresolved observation per spherical detail face."""
    if inventory.get("contract_version") != "detail-inventory/1.0":
        raise ValueError("detail-inventory/1.0 required")
    tolerances = inventory.get("tolerances", {})
    linear, angular = tolerances.get("linear"), tolerances.get("angular")
    if not (_number(linear) and linear > 0 and _number(angular) and 0 < angular < math.pi / 2):
        raise ValueError("positive finite matching tolerances and angular < pi/2 required")
    results = []
    faces, edges = inventory["faces"], inventory["edges"]
    for fid, detail in inventory["detail_faces"].items():
        face = faces.get(fid, {})
        native = face.get("native_face_data", {})
        if face.get("surface_type") != "Spherical" and native.get("uf_type") != 18:
            continue
        diagnostic = detail.get("diagnostic", {})
        root = diagnostic.get("topology") if isinstance(diagnostic, Mapping) else None
        geometry = root.get("geometry", {}) if isinstance(root, Mapping) else {}
        geometry = geometry if isinstance(geometry, Mapping) else {}
        source_edges, edge_map = detail.get("source_edge_ids"), detail.get("source_edges_by_tag")
        reasons, occurrences = [], []
        if inventory.get("coordinate_system") != "absolute_part_coordinates":
            reasons.append("absolute part frame for evaluator edges is not established")
        if face.get("surface_type") != "Spherical" or native.get("uf_type") != 18 or geometry.get("type") != 203:
            reasons.append("UF18 spherical face and UF BREP type 203 are required")
        if geometry.get("source_frame") != "UF_BREP_native_unverified":
            reasons.append("sphere source frame is missing or unexpected")
        center = _vec(geometry.get("center"))
        axis, ref = _unit(_vec(geometry.get("axis"))), _unit(_vec(geometry.get("u0_ref_direction")))
        radius = geometry.get("radius")
        valid_sphere = (center is not None and axis is not None and ref is not None
                        and _norm(_cross(axis, ref)) > math.sin(angular) and _number(radius) and radius > 0)
        if not valid_sphere:
            reasons.append("invalid sphere center, radius or degenerate axis/reference")
        uv = diagnostic.get("uv_box") if isinstance(diagnostic, Mapping) else None
        if not isinstance(uv, (list, tuple)) or len(uv) != 4 or not _limits(uv[:2]) or not _limits(uv[2:]):
            reasons.append("invalid or missing face UV bounds")
        if not _finite_tree(root):
            reasons.append("native topology contains non-finite numerical data")
        if (not isinstance(root, Mapping) or str(root.get("tag")) != str(face.get("source_tag"))
                or root.get("geometry_rc") != 0 or root.get("geometry_free_rc") != 0
                or not isinstance(diagnostic, Mapping) or diagnostic.get("edge_coverage_complete") is not True):
            reasons.append("face identity, native geometry or edge coverage is incomplete")
        valid_links = (detail.get("source_face_id") == fid and isinstance(source_edges, list) and bool(source_edges)
                       and all(isinstance(eid, str) for eid in source_edges) and len(set(source_edges)) == len(source_edges)
                       and set(source_edges) == set(face.get("edge_ids", [])) and isinstance(edge_map, Mapping)
                       and len(edge_map) == len(source_edges) and set(edge_map.values()) == set(source_edges)
                       and all(eid in edges and str(edges[eid].get("source_tag")) == tag for tag, eid in edge_map.items()))
        if not valid_links:
            reasons.append("source face or edge linkage is incomplete or nonunique")
        if valid_links and valid_sphere:
            try:
                occurrences = _topology(root, edge_map, source_edges, edges, fid, center, radius, linear, angular)
            except (ValueError, TypeError, OverflowError) as exc:
                reasons.append(str(exc))
        result = {
            "id": "detail_sphere_" + fid, "snapshot_id": inventory["snapshot_id"],
            "kind": "unresolved_detail_sphere" if reasons else "possible_spherical_carrier",
            "coverage_role": "observation", "source_faces": [fid],
            "source_edges": list(source_edges) if isinstance(source_edges, list) else [],
            "evidence": [{"type": "native_sphere_detail", "snapshot_id": inventory["snapshot_id"],
                          "source_face_id": fid, "source_edge_ids": deepcopy(source_edges),
                          "source_edges_by_tag": deepcopy(edge_map), "evidence_path": detail.get("evidence_path"),
                          "summary_path": detail.get("summary_path"), "coordinate_system": inventory.get("coordinate_system"),
                          "source_frame": geometry.get("source_frame"), "length_unit": inventory["unit"],
                          "geometry": deepcopy(geometry), "uv_box": deepcopy(uv), "uv_unit": "unknown",
                          "topology": deepcopy(root), "edge_coverage_complete": diagnostic.get("edge_coverage_complete") if isinstance(diagnostic, Mapping) else False,
                          "occurrences": occurrences, "linear_matching_threshold": linear, "angular_matching_threshold": angular,
                          "angle_unit": "rad", "frame_assumption": "UF_BREP sphere center frame and ABS evaluator edges are the same; unverified",
                          "basis": "conditional analytic carrier compatibility only; thresholds are matching thresholds, not manufacturing or global tolerances"}],
            "parameters": [] if reasons else [{"id": fid + ":radius", "dimension": "length", "value": radius,
                                                "unit": inventory["unit"], "classification": "unclassified", "confirmation": "unconfirmed"}],
            "alternatives": ["editable construction after independent boundary and geometric equivalence verification"],
            "open_items": ["Verify the UF_BREP sphere frame against ABS before relying on carrier compatibility.",
                           "Trimmed surface, spherical cap closure, complete boundary, material role and global geometry remain unverified.",
                           "Fin traversal versus evaluator direction, construction history and engineering intent remain unverified."] + reasons,
            "capability_requirements": ["verify complete trimmed geometry and boundary", "confirm engineering intent and editable construction"],
            "depends_on": [], "confirmed": False, "confirmation": {"status": "unconfirmed"}, "execution_approved": False,
        }
        results.append(result)
    return results
