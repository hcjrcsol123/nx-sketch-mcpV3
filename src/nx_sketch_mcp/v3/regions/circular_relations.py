"""Unconfirmed circular spacing of cylindrical *axes*, not a feature pattern.

This deliberately narrow offline rule considers negative-sense cylinders of
matching radius and parallel axes.  It fits their intersections with a common
plane to a circle and requires the observed points to form an evenly spaced
ring. A missing regular subset may itself form a smaller ring and cannot be
detected from these points alone. IDs and evidence are snapshot-local.
"""

import math
from collections import Counter


def _number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _vector(x):
    if not isinstance(x, (list, tuple)) or len(x) != 3 or not all(_number(v) for v in x):
        return None
    return tuple(float(v) for v in x)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _unit(v):
    length = math.hypot(*v)
    return tuple(x / length for x in v) if length > 0 and math.isfinite(length) else None


def _canonical(v):
    # Fix the arbitrary sign of an unoriented native axis deterministically.
    major = max(range(3), key=lambda i: abs(v[i]))
    return tuple(-x for x in v) if v[major] < 0 else v


def _angle(a, b):
    return math.atan2(math.hypot(*_cross(a, b)), abs(_dot(a, b)))


def _parameter(ident, dimension, value, unit):
    return {"id": ident, "dimension": dimension, "value": value, "unit": unit,
            "classification": "unclassified", "confirmation": "unconfirmed"}


def _fit(group, linear, angular):
    n = len(group)
    if n < 3:
        return None
    axis = group[0][3]
    # Radius and direction are checked against the whole group, avoiding a
    # chain of individually close observations with an unbounded total spread.
    axis_spread = max(_angle(a[3], b[3]) for i, a in enumerate(group) for b in group[i+1:])
    if axis_spread > angular:
        return None
    reference = tuple(sum(item[2][j] for item in group) / n for j in range(3))
    reference_axis = min(range(3), key=lambda i: abs(axis[i]))
    ref = tuple(1.0 if i == reference_axis else 0.0 for i in range(3))
    u = _unit(_cross(ref, axis))
    v = _cross(axis, u)
    points = []
    for _, _, origin, direction, _ in group:
        denominator = _dot(direction, axis)
        if abs(denominator) < 1e-12:
            return None
        distance = _dot(tuple(reference[i] - origin[i] for i in range(3)), axis) / denominator
        point = tuple(origin[i] + distance * direction[i] - reference[i] for i in range(3))
        points.append((_dot(point, u), _dot(point, v)))
    if any(math.hypot(p[0]-q[0], p[1]-q[1]) <= linear
           for i, p in enumerate(points) for q in points[i+1:]):
        return None
    # Translate before solving the algebraic circle fit to reduce cancellation.
    xbar = sum(p[0] for p in points) / n
    ybar = sum(p[1] for p in points) / n
    centered = [(x-xbar, y-ybar) for x, y in points]
    xx = sum(x*x for x, y in centered)
    xy = sum(x*y for x, y in centered)
    yy = sum(y*y for x, y in centered)
    det = xx*yy - xy*xy
    # Scale-independent collinearity/ill-conditioning rejection.
    if not math.isfinite(det) or det <= 1e-12 * (xx + yy)**2:
        return None
    bx = sum(x*(x*x+y*y) for x, y in centered) / 2
    by = sum(y*(x*x+y*y) for x, y in centered) / 2
    cx = xbar + (bx*yy-by*xy)/det
    cy = ybar + (by*xx-bx*xy)/det
    radii = [math.hypot(x-cx, y-cy) for x, y in points]
    radius = sum(radii)/n
    radial_error = max(abs(r-radius) for r in radii)
    if not math.isfinite(radius) or radius <= linear or radial_error > linear:
        return None
    ordered = sorted((math.atan2(y-cy, x-cx) % (2*math.pi), item[1])
                     for (x, y), item in zip(points, group))
    pitch = 2*math.pi/n
    gaps = [(ordered[(i+1) % n][0] - ordered[i][0]) % (2*math.pi) for i in range(n)]
    gap_error = max(abs(gap-pitch) for gap in gaps)
    phase = sum(angle-i*pitch for i, (angle, _) in enumerate(ordered))/n
    phase_error = max(abs(angle-(phase+i*pitch)) for i, (angle, _) in enumerate(ordered))
    if gap_error > angular or phase_error > angular:
        return None
    center = tuple(reference[i] + cx*u[i] + cy*v[i] for i in range(3))
    return {"axis_point": list(center), "axis_direction": list(axis), "basis_u": list(u), "basis_v": list(v),
            "pitch_radius": radius, "phase": phase, "pitch": pitch,
            "ordered": ordered, "gaps": gaps, "max_radial_residual": radial_error,
            "max_gap_residual": gap_error, "max_phase_residual": phase_error,
            "max_axis_angle": axis_spread}


def recognize(inventory):
    """Return complete-ring position hypotheses only; absence is not proof."""
    linear, angular = inventory["tolerances"]["linear"], inventory["tolerances"]["angular"]
    if not (_number(linear) and linear > 0 and _number(angular) and angular > 0):
        raise ValueError("matching thresholds must be positive and finite")
    faces, edges, unit = inventory["faces"], inventory["edges"], inventory["unit"]
    items = []
    for ident, face in faces.items():
        data = face["native_face_data"]
        origin, direction, radius = _vector(data.get("origin")), _vector(data.get("direction")), data.get("radius")
        if (face.get("surface_type") != "Cylindrical" or data.get("normal_sense") != -1
                or origin is None or direction is None or not _number(radius) or radius <= 0):
            continue
        direction = _unit(direction)
        if direction is not None:
            items.append((radius, ident, origin, _canonical(direction), face))
    items.sort(key=lambda x: (x[0], x[1]))
    groups = []
    for item in items:
        for group in groups:
            if item[0] - group[0][0] <= linear and all(_angle(item[3], other[3]) <= angular for other in group):
                group.append(item)
                break
        else:
            groups.append([item])
    result = []
    for group in groups:
        fit = _fit(group, linear, angular)
        if fit is None:
            continue
        sources = sorted(item[1] for item in group)
        source_edges = sorted({e for item in group for e in item[4]["edge_ids"]})
        observations = []
        signatures = {}
        for radius, ident, origin, direction, face in group:
            links = []
            for eid in face["edge_ids"]:
                edge = edges.get(eid)
                if not edge:
                    links.append({"edge_id": eid, "missing": True})
                    continue
                neighbors = [{"face_id": fid, "surface_type": faces[fid].get("surface_type") if fid in faces else None}
                             for fid in edge["face_ids"] if fid != ident]
                links.append({"edge_id": eid, "edge_type": edge.get("edge_type"), "neighbors": neighbors})
            signature = tuple(sorted((link.get("edge_type", "missing"), neighbor.get("surface_type") or "unknown")
                                     for link in links for neighbor in link.get("neighbors", [{"surface_type": "unknown"}])))
            signatures[ident] = signature
            data = face["native_face_data"]
            observations.append({"face_id": ident, "origin": list(data["origin"]), "direction": list(data["direction"]),
                                 "radius": radius, "normal_sense": data["normal_sense"], "uf_type": data["uf_type"], "adjacency": links})
        counts = Counter(signatures.values())
        # All signatures are retained; a modal comparison only highlights an
        # observed difference and does not assert which topology is correct.
        modal = max(counts, key=lambda signature: (counts[signature], signature))
        anomalies = [ident for ident in sources if signatures[ident] != modal]
        result.append({
            "id": "REL_circular_axes_" + "_".join(sources), "kind": "possible_circular_axis_spacing",
            "snapshot_id": inventory["snapshot_id"], "coverage_role": "observation",
            "source_faces": sources, "source_edges": source_edges,
            "evidence": [{"type": "circular_axis_fit", "snapshot_id": inventory["snapshot_id"],
                          "geometry_details_complete": inventory["geometry_details_complete"],
                          "axis_point": fit["axis_point"], "axis_direction": fit["axis_direction"],
                          "plane_basis_u": fit["basis_u"], "plane_basis_v": fit["basis_v"],
                          "ordered_face_angles_rad": [{"face_id": ident, "angle": angle} for angle, ident in fit["ordered"]],
                          "adjacent_angular_gaps_rad": fit["gaps"], "point_count": len(group),
                          "max_radial_residual": fit["max_radial_residual"], "length_unit": unit,
                          "max_gap_residual_rad": fit["max_gap_residual"], "max_phase_residual_rad": fit["max_phase_residual"],
                          "max_axis_angle_rad": fit["max_axis_angle"], "linear_threshold": linear,
                          "angular_threshold_rad": angular, "observations": observations,
                          "adjacency_signature_outliers": anomalies,
                          "basis": "UF origins and unoriented directions projected to a common plane; algebraic circle center and mean radial distance; full cyclic gaps"}],
            "parameters": [_parameter("pitch_circle_radius", "length", fit["pitch_radius"], unit),
                           _parameter("phase", "angle", fit["phase"], "rad"),
                           _parameter("pitch", "angle", fit["pitch"], "rad"),
                           _parameter("point_count", "scalar", len(group), "1")],
            "alternatives": ["independent axes happen to have regular positions", "one shared circular pattern", "multiple interleaved patterns or individually constructed features"],
            "open_items": [f"For faces {sources}, confirm whether angular spacing, radius and count are intended driving relationships or independent observations.",
                           "Fixed topology, valid edit ranges, seed, phase reference, pattern history and operation order are unknown; missing points that themselves leave a regular smaller ring cannot be detected from these observations.",
                           "Full trims, generatrices, boundary curves and material occupancy are missing; compare transformed regions before asserting repeating geometry; adjacency signature differences may be face splits."],
            "capability_requirements": ["confirm design intent and edit domains", "obtain trimmed curves and compare transformed regions", "verify any editable relation on each target model"],
            "depends_on": [], "confirmed": False, "confirmation": {"status": "unconfirmed"},
        })
    return result
