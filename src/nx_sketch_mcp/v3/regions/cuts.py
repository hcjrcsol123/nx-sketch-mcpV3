"""Evidence-limited, snapshot-local recognition of a possible cut region.

This is a geometric hypothesis, not a feature, hole, or machining decision.
The restricted rule accepts only principal-axis cylinders whose two axial
bounding planes are directly attached through circular edges.
"""

from itertools import combinations
from math import asin, isfinite, sqrt


def _vector(value):
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        return None
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not isfinite(x) for x in value):
        return None
    return tuple(float(x) for x in value)


def _unit(value):
    vector = _vector(value)
    if vector is None:
        return None
    length = sqrt(sum(x * x for x in vector))
    return tuple(x / length for x in vector) if length and isfinite(length) else None


def _parameter(name, dimension, value, unit):
    return {"id": name, "dimension": dimension, "value": value, "unit": unit,
            "classification": "unclassified", "confirmation": "unconfirmed"}


def recognize(inventory):
    """Return possible cut regions using only normalized inventory v0.1.

    An empty list means this narrow rule found no candidate, not that no cuts
    exist. IDs and source tags are local to the supplied snapshot only.
    """
    faces, edges = inventory["faces"], inventory["edges"]
    linear, angular = inventory["tolerances"]["linear"], inventory["tolerances"]["angular"]
    unit = inventory["unit"]
    candidates = []
    for face_id, face in faces.items():
        data = face["native_face_data"]
        if face["surface_type"].lower() != "cylindrical" or data.get("normal_sense") != -1:
            continue
        direction = _unit(data.get("direction"))
        origin = _vector(data.get("origin"))
        radius = data.get("radius")
        box = data.get("bounding_box")
        if (direction is None or origin is None or isinstance(radius, bool)
                or not isinstance(radius, (int, float)) or not isfinite(radius) or radius <= 0
                or not isinstance(box, (tuple, list)) or len(box) != 6
                or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not isfinite(x) for x in box)
                or any(box[i] > box[i + 3] for i in range(3))):
            continue
        axis = max(range(3), key=lambda i: abs(direction[i]))
        off_axis = sqrt(sum(direction[i] ** 2 for i in range(3) if i != axis))
        if asin(min(1.0, off_axis)) > angular:
            continue
        # A tilted axis makes a world AABB's component span wider than its
        # actual axial extent. Do not equate those values even within tolerance.
        if off_axis > 1e-12:
            continue
        sides = []
        boundary_edges = []
        adjacent = set()
        for edge_id in face["edge_ids"]:
            edge = edges.get(edge_id)
            if edge is None or face_id not in edge["face_ids"]:
                continue
            boundary_edges.append(edge_id)
            for other_id in edge["face_ids"]:
                if other_id == face_id or other_id not in faces:
                    continue
                adjacent.add(other_id)
                other = faces[other_id]
                od = other["native_face_data"]
                normal, point = _unit(od.get("direction")), _vector(od.get("origin"))
                if (len(edge["face_ids"]) != 2 or edge["edge_type"].lower() != "circular" or other["surface_type"].lower() != "planar"
                        or edge_id not in other["edge_ids"] or normal is None or point is None):
                    continue
                cross = sqrt(sum((normal[i] - sum(normal[j] * direction[j] for j in range(3)) * direction[i]) ** 2 for i in range(3)))
                if asin(min(1.0, cross)) > angular or cross > 1e-12:
                    continue
                sides.append((other_id, edge_id, point[axis]))
        for a, b in combinations(sides, 2):
            if a[0] == b[0] or a[1] == b[1]:
                continue
            low, high = sorted((a[2], b[2]))
            if high - low <= linear or abs(low - box[axis]) > linear or abs(high - box[axis + 3]) > linear:
                continue
            candidate_id = "CUT-" + face_id + "-" + "-".join(sorted((a[0], b[0])))
            candidates.append({
                "id": candidate_id,
                "kind": "possible_bounded_cylindrical_cut_region",
                "source_faces": [face_id] + sorted(adjacent),
                "source_edges": sorted(set(boundary_edges)),
                "evidence": [
                    {"type": "native_face_data", "face": face_id, "fields": ["uf_type", "normal_sense", "origin", "direction", "radius", "bounding_box"],
                     "snapshot_id": inventory["snapshot_id"], "geometry_details_complete": inventory["geometry_details_complete"],
                     "origin": list(data["origin"]), "direction": list(data["direction"]), "radius": radius,
                     "normal_sense": data["normal_sense"], "uf_type": data["uf_type"], "bounding_box": list(box), "unit": unit,
                     "observation": "negative-sense cylindrical surface; local hypothesis only"},
                    {"type": "adjacency", "cylinder": face_id, "side_faces": [a[0], b[0]], "side_edges": [a[1], b[1]],
                     "side_native_data": {side[0]: faces[side[0]]["native_face_data"] for side in (a, b)},
                     "boundary_edges": {eid: {"edge_type": edges[eid]["edge_type"], "face_ids": edges[eid]["face_ids"]} for eid in boundary_edges},
                     "observation": "two planar faces parallel to each other, normal to cylinder axis, directly joined by circular edges"},
                    {"type": "matching", "linear_tolerance": linear, "linear_unit": unit, "angular_tolerance_rad": angular,
                     "observation": "side origins match cylinder axis-aligned bounding-box endpoints; cylinder and side normal restrictions of 1e-12 on normalized off-axis components"},
                ],
                "parameters": [
                    _parameter("cylinder_radius", "length", radius, unit),
                    _parameter("side_plane_separation", "length", high - low, unit),
                ],
                "alternatives": ["trimmed cylindrical boundary of an intersecting feature", "part of a compound cut or other surface construction"],
                "open_items": [
                    f"The full trimmed boundary and section of {face_id} and neighboring faces {sorted(adjacent)} are unavailable; establish a closed section and material side before choosing a cut.",
                    f"Determine actual cut depth, entry and termination around {face_id} from complete boundary and occupancy evidence; blind versus through and hole type are undetermined.",
                    "Review all listed boundary edges and adjacent faces, including any partial or missing geometry, and confirm design intent and dimensions.",
                ],
                "capability_requirements": ["complete_trimmed_boundary", "section_and_material_occupancy", "human_design_intent_confirmation"],
                "depends_on": [], "confirmed": False, "confirmation": {"status": "unconfirmed"},
            })
    return candidates
