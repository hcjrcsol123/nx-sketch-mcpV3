"""Conservative profile evidence from one normalized reference snapshot.

IDs and topology refer only to that snapshot.  These results are hypotheses,
not complete profiles, persistent NX references, or executable operations.
"""

import math


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _vector(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3 or not all(map(_number, value)):
        return None
    return tuple(float(x) for x in value)


def _axis(face):
    data = face.get("native_face_data") or {}
    origin, direction = _vector(data.get("origin")), _vector(data.get("direction"))
    radius = data.get("radius")
    if origin is None or direction is None or not _number(radius) or radius <= 0:
        return None
    length = math.hypot(*direction)
    if not math.isfinite(length) or length == 0:
        return None
    return origin, tuple(x / length for x in direction)


def _axis_difference(first, second):
    p, a = first
    q, b = second
    cross_axes = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    dot = sum(x*y for x, y in zip(a, b))
    angle = math.atan2(math.hypot(*cross_axes), abs(dot))
    delta = tuple(x-y for x, y in zip(q, p))
    def offset(direction):
        cross = (delta[1]*direction[2]-delta[2]*direction[1],
                 delta[2]*direction[0]-delta[0]*direction[2],
                 delta[0]*direction[1]-delta[1]*direction[0])
        return math.hypot(*cross)
    # Check both native origins against the opposite axis.  Near-parallel axes
    # can otherwise pass depending on face order and an arbitrary axis origin.
    return max(offset(a), offset(b)), angle


def _parameter(identifier, dimension, value, unit):
    return {"id": identifier, "dimension": dimension, "value": value, "unit": unit,
            "classification": "unclassified", "confirmation": "unconfirmed"}


def _base(identifier, kind, face_ids, edge_ids):
    return {"id": identifier, "kind": kind, "source_faces": face_ids,
            "source_edges": edge_ids, "evidence": [], "parameters": [],
            "alternatives": [], "open_items": [], "capability_requirements": [],
            "depends_on": [], "confirmed": False, "confirmation": {"status": "unconfirmed"}}


def recognize(inventory):
    """Return limited adjacent cylinder/cone hypotheses and unresolved surfaces.

    A circular shared edge, two-sided incidence and coaxial analytic axes are
    required for every two-face chain.  A chain is deliberately local: no
    equivalence or complete trimming is implied by common underlying surfaces.
    Tolerances are matching thresholds, not manufacturing tolerances.
    """
    faces, edges = inventory["faces"], inventory["edges"]
    tol, unit = inventory["tolerances"], inventory["unit"]
    linear, angular = tol["linear"], tol["angular"]
    if not all(_number(x) and x > 0 for x in (linear, angular)):
        raise ValueError("matching tolerances must be positive finite numbers")
    candidates = []
    for edge_id, edge in edges.items():
        face_ids = edge.get("face_ids", [])
        if edge.get("edge_type") != "Circular" or len(face_ids) != 2 or face_ids[0] == face_ids[1]:
            continue
        if any(fid not in faces or edge_id not in faces[fid].get("edge_ids", []) for fid in face_ids):
            continue
        left, right = (faces[fid] for fid in face_ids)
        if {left.get("surface_type"), right.get("surface_type")} != {"Cylindrical", "Conical"}:
            continue
        axis_left, axis_right = _axis(left), _axis(right)
        if axis_left is None or axis_right is None:
            continue
        distance, angle = _axis_difference(axis_left, axis_right)
        if not (math.isfinite(distance) and distance <= linear and angle <= angular):
            continue
        ids = sorted(face_ids)
        boundary_edges = sorted(set(left.get("edge_ids", [])) | set(right.get("edge_ids", [])))
        candidate = _base("profile-" + edge_id, "coaxial_cylinder_cone_chain", ids, boundary_edges)
        candidate["evidence"] = [{"type": "shared_edge", "edge_id": edge_id,
                                  "edge_type": "Circular", "face_ids": ids,
                                  "basis": "reciprocal snapshot incidence; edge curve and trim not supplied"},
                                 {"type": "coaxial_axes", "face_ids": list(face_ids),
                                  "axes": [{"face_id": f["id"], "origin": list(a[0]),
                                            "direction": list(a[1])} for f, a in ((left, axis_left), (right, axis_right))],
                                  "origin_line_distance": distance, "axis_angle": angle,
                                  "linear_threshold": linear, "angular_threshold": angular,
                                  "length_unit": unit, "angle_unit": "rad",
                                  "basis": "UF origin and direction; unoriented axes; maximum of the two origin-to-opposite-axis distances"},
                                 {"type": "native_face_data", "faces": [
                                     {"face_id": f["id"], "surface_type": f["surface_type"],
                                      "data": f.get("native_face_data")} for f in (left, right)]}]
        for f in (left, right):
            data = f["native_face_data"]
            candidate["parameters"].append(_parameter(f["id"] + ":radius", "length", data["radius"], unit))
            raw_angle = data.get("radius_data")
            if f["surface_type"] == "Conical" and _number(raw_angle):
                candidate["parameters"].append(_parameter(f["id"] + ":cone_half_angle", "angle", raw_angle, "rad"))
        candidate["alternatives"] = ["revolve a verified editable section (F13)",
                                     "combine separately constructed analytic features (F12/F15)"]
        candidate["open_items"] = [
            {"faces": ids, "issue": "Complete profile, trim domains, edge curves and axial extents are unknown; shared edge type alone cannot establish a full circle or a closed section."},
            {"faces": ids, "issue": "Feature intent, additive/subtractive role, operation order, dimensions and editable constraints require confirmation."},
            {"faces": ids, "issue": "Common underlying axes or radii do not establish equivalent trimmed regions or a complete body."}]
        candidate["capability_requirements"] = ["F13 verified section and axis, or equivalent editable construction",
                                                  "compare trimmed geometry and validate operation and preservation on target versions"]
        candidates.append(candidate)

    gaps = {"Swept": ("T04.a", "sweep section, path, trim and editable definition"),
            "SurfaceOfRevolution": ("T04.b", "generatrix, axis, trim and editable revolution definition"),
            "Spherical": ("T04.d", "trim boundaries and sphere-to-neighbor parameter relationships")}
    for face_id, face in faces.items():
        surface = face.get("surface_type")
        if surface not in gaps:
            continue
        gap, missing = gaps[surface]
        incident = list(face.get("edge_ids", []))
        candidate = _base("profile-unresolved-" + face_id, "unresolved_complex_surface", [face_id], incident)
        candidate["evidence"] = [{"type": "per_face_native_evidence", "face_id": face_id,
                                  "surface_type": surface, "native_face_data": face.get("native_face_data"),
                                  "edge_incidence": [{"edge_id": eid, "edge_type": edges[eid].get("edge_type"),
                                                      "face_ids": edges[eid].get("face_ids", [])}
                                                     for eid in incident if eid in edges],
                                  "basis": "partial UF face data and snapshot incidence; no complete trim or edge curves"}]
        candidate["alternatives"] = ["investigate an editable equivalent using " + ("F21" if surface == "Swept" else "F13/F15"),
                                     "retain as unresolved until evidence supports an equivalent"]
        candidate["open_items"] = [{"faces": [face_id], "issue": "Missing " + missing + "; surface type and partial UF fields do not establish equivalence or feature history."}]
        candidate["capability_requirements"] = [gap + ": obtain and verify " + missing,
                                                  "compare complete trimmed region and validate editable construction on target versions"]
        candidates.append(candidate)
    return candidates
