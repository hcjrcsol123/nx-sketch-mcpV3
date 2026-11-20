"""Evidence-limited ring-torus profile hypotheses from one guarded detail read.

No candidate confirms a design feature, a closed profile, a 360-degree sweep,
or the complete trim. All logical IDs and native tags are snapshot-local.
"""

from copy import deepcopy
import math


def _number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def _vec(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3 or not all(_number(x) for x in value):
        return None
    return tuple(float(x) for x in value)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _norm(v):
    return math.hypot(*v)


def _unit(v):
    if v is None:
        return None
    length = _norm(v)
    if not math.isfinite(length) or length == 0:
        return None
    return tuple(x / length for x in v)


def _limits(value):
    return (isinstance(value, (list, tuple)) and len(value) == 2 and
            all(_number(x) for x in value) and value[0] < value[1])


def _arc_match(arc, center, axis, major, minor, linear, angular):
    """Classify exact carrier circles with bounded numeric residuals.

    This checks underlying analytic circles, not their trim correspondence or
    the topology's orientation relative to evaluator parameter direction.
    """
    if not isinstance(arc, dict) or arc.get("type") != "circular_evaluator" or arc.get("coordinate_system") != "ABS":
        return None
    point, x, y = _vec(arc.get("center")), _vec(arc.get("x_axis")), _vec(arc.get("y_axis"))
    radius = arc.get("radius")
    if (point is None or x is None or y is None or not _number(radius) or radius <= 0 or
            not _limits(arc.get("evaluator_limits")) or not _limits(arc.get("arc_limits")) or
            type(arc.get("is_periodic")) is not bool or type(arc.get("arc_is_periodic")) is not bool or
            arc["is_periodic"] != arc["arc_is_periodic"]):
        return None
    xnorm, ynorm = _norm(x), _norm(y)
    if not (math.isfinite(xnorm) and math.isfinite(ynorm)) or abs(xnorm-1) > angular or abs(ynorm-1) > angular:
        return None
    ux, uy = _unit(x), _unit(y)
    if ux is None or uy is None or abs(_dot(ux, uy)) > math.sin(angular):
        return None
    normal = _unit(_cross(ux, uy))
    if normal is None:
        return None
    delta = tuple(a-b for a, b in zip(point, center))
    axial = _dot(delta, axis)
    radial = tuple(d - axial*a for d, a in zip(delta, axis))
    radial_length = _norm(radial)
    normal_axis = abs(_dot(normal, axis))
    # Meridian circle: its carrier plane contains the torus axis, its centre
    # is R from that axis in the central plane, and its radius is r.
    if (normal_axis <= math.sin(angular) and abs(_dot(normal, delta)) <= linear and
            abs(axial) <= linear and abs(radial_length-major) <= linear and abs(radius-minor) <= linear):
        return {"role": "meridian_carrier", "axis_plane_offset": abs(_dot(normal, delta)),
                "axis_plane_normal_component": normal_axis, "center_axial_offset": abs(axial),
                "major_radius_residual": abs(radial_length-major), "minor_radius_residual": abs(radius-minor)}
    # Parallel circle: its centre is on the torus axis and its plane is normal
    # to that axis; its radius/axial position satisfy the torus carrier equation.
    if (math.acos(min(1.0, normal_axis)) <= angular and radial_length <= linear and
            abs(math.hypot(radius-major, axial)-minor) <= linear):
        return {"role": "parallel_carrier", "center_axis_offset": radial_length,
                "plane_axis_angle": math.acos(min(1.0, normal_axis)),
                "section_radius_residual": abs(math.hypot(radius-major, axial)-minor)}
    return None


def _edge_occurrences(root):
    occurrences = []

    def walk(node, path, depth):
        if not isinstance(node, dict) or depth > 8 or not isinstance(node.get("children"), list):
            raise ValueError("invalid topology")
        kind = node.get("type")
        if kind == 8:
            occurrences.append((node, path))
        for child in node["children"]:
            if not isinstance(child, dict) or not isinstance(child.get("child"), dict):
                raise ValueError("invalid oriented child")
            child_kind, orientation = child["child"].get("type"), child.get("orientation")
            if orientation not in (-1, 0, 1) or type(orientation) is not int:
                raise ValueError("invalid orientation")
            if (kind, child_kind) in ((6, 7), (6, 8), (7, 8)) and orientation not in (-1, 1):
                raise ValueError("missing loop/fin direction")
            if kind == 7 and child_kind == 8 and path and path[-1]["orientation"] not in (0, orientation):
                raise ValueError("inconsistent fin and edge direction")
            walk(child["child"], path + [{"parent_type": kind, "child_type": child_kind, "orientation": orientation}], depth+1)

    walk(root, [], 0)
    return occurrences


def recognize(inventory):
    """Find supported ring-torus carrier/section candidates in guarded details."""
    linear, angular = inventory["tolerances"]["linear"], inventory["tolerances"]["angular"]
    if not (_number(linear) and linear > 0 and _number(angular) and 0 < angular < math.pi/2):
        raise ValueError("positive finite matching tolerances and angular < pi/2 required")
    if inventory.get("coordinate_system") != "absolute_part_coordinates":
        return []
    faces, edges = inventory["faces"], inventory["edges"]
    results = []
    for fid, detail in inventory.get("detail_faces", {}).items():
        face = faces.get(fid)
        if not isinstance(face, dict) or face.get("surface_type") != "SurfaceOfRevolution":
            continue
        diagnostic = detail.get("diagnostic", {})
        root = diagnostic.get("topology")
        if not isinstance(root, dict) or root.get("type") != 5:
            continue
        torus = root.get("geometry")
        if not isinstance(torus, dict) or torus.get("type") != 204:
            continue
        center, axis_raw, ref_raw = _vec(torus.get("center")), _vec(torus.get("axis")), _vec(torus.get("u0_ref_direction"))
        axis, ref = _unit(axis_raw), _unit(ref_raw)
        major, minor = torus.get("major_radius"), torus.get("minor_radius")
        if (center is None or axis is None or ref is None or _norm(_cross(axis, ref)) <= math.sin(angular) or
                not _number(major) or not _number(minor) or not (major > minor > 0)):
            continue
        edge_map = detail.get("source_edges_by_tag", {})
        declared = detail.get("source_edge_ids", [])
        if (not isinstance(edge_map, dict) or not isinstance(declared, list) or not declared or
                len(set(declared)) != len(declared) or set(edge_map.values()) != set(declared) or
                len(edge_map) != len(declared) or any(eid not in edges for eid in declared)):
            continue
        try:
            occurrences = _edge_occurrences(root)
        except (ValueError, TypeError):
            continue
        boundaries, seen = [], set()
        valid = True
        for edge, path in occurrences:
            tag = str(edge.get("tag"))
            eid = edge_map.get(tag)
            if (eid is None or edges[eid].get("edge_type") != "Circular" or fid not in edges[eid].get("face_ids", []) or
                    edge.get("geometry_class") != 10 or edge.get("edge_class_rc") != 0):
                valid = False; break
            match = _arc_match(edge.get("geometry"), center, axis, major, minor, linear, angular)
            if match is None:
                valid = False; break
            seen.add(eid)
            boundaries.append({"edge_id": eid, "topology_path": deepcopy(path), "geometry": deepcopy(edge["geometry"]),
                               "analytic_match": match,
                               "direction_relation": "evaluator parameter direction versus fin remains unverified"})
        meridians = [b for b in boundaries if b["analytic_match"]["role"] == "meridian_carrier"]
        if not valid or seen != set(declared) or not meridians:
            continue
        results.append({
            "id": "detail-torus-" + fid, "kind": "ring_torus_meridian_revolve_candidate",
            "snapshot_id": inventory["snapshot_id"], "coverage_role": "observation", "execution_approved": False,
            "source_faces": [fid], "source_edges": list(declared),
            "evidence": [{"type": "native_torus_carrier", "face_id": fid, "geometry": deepcopy(torus),
                          "coordinate_system": inventory["coordinate_system"], "unit": inventory["unit"],
                          "source": detail.get("evidence_path"), "summary": detail.get("summary_path")},
                         {"type": "circular_boundary_carriers", "face_id": fid, "occurrences": boundaries,
                          "linear_matching_threshold": linear, "angular_matching_threshold": angular,
                          "length_unit": inventory["unit"], "angle_unit": "rad",
                          "basis": "analytic carrier tests, not a proof of trim or parameter-direction equivalence"},
                         {"type": "candidate_section", "edge_id": meridians[0]["edge_id"],
                          "arc": deepcopy(meridians[0]["geometry"]), "topology_path": deepcopy(meridians[0]["topology_path"]),
                          "basis": "observed meridian carrier is a limited section candidate; sweep and closure remain unknown"}],
            "parameters": [{"id": fid + ":major_radius", "dimension": "length", "value": major,
                            "unit": inventory["unit"], "classification": "unclassified", "confirmation": "unconfirmed"},
                           {"id": fid + ":minor_radius", "dimension": "length", "value": minor,
                            "unit": inventory["unit"], "classification": "unclassified", "confirmation": "unconfirmed"}],
            "alternatives": ["F13 revolve of a verified editable circular section", "equivalent editable operations after boundary and boolean verification"],
            "open_items": [{"faces": [fid], "issue": "Complete trim, UV parameterization, inner/outer role, seam, and actual sweep extent remain unverified; periodicity does not establish a 360-degree face."},
                           {"faces": [fid], "issue": "Fin traversal versus evaluator parameter direction and tangency to neighboring faces remain unverified."},
                           {"faces": [fid], "issue": "Design intent, driving dimensions, operation order, and permitted edit range require confirmation."},
                           {"faces": [fid], "issue": "UF face axis point is not asserted to be the torus centre; resolve its native semantic branch separately."}],
            "capability_requirements": ["T04.b: compare complete trimmed surface and boundaries, including parameter mapping",
                                        "F13 or equivalent editable construction, target version and preservation verification"],
            "depends_on": [], "confirmed": False, "confirmation": {"status": "unconfirmed"},
        })
    return results
