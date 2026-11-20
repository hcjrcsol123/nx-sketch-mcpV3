"""Propose a restricted cylinder/shoulder candidate from inventory evidence.

This does not decide whether the region is a separate added feature. UF face
sense is used as a restricted search filter, not as proof of the material side.
"""
import math


def _unit(vector):
    norm = math.sqrt(sum(value * value for value in vector))
    return None if norm == 0 else [value / norm for value in vector]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _parallel_residual(a, b):
    return math.acos(min(1.0, max(0.0, abs(_dot(a, b)))))


def _axis_distance(origin, other, axis):
    delta = [a - b for a, b in zip(origin, other)]
    axial = _dot(delta, axis)
    return math.sqrt(sum((v - axial * d) ** 2 for v, d in zip(delta, axis)))


def recognize(inventory):
    """Return unconfirmed cylinder/plane/cone alternatives from one inventory.

    The cylinder must be parallel to a principal part axis, touch a plane at an
    axial end of its bounding box, and touch a coaxial cone on circular edges.
    Finite boxes and partial surface data are evidence for a candidate only.
    """
    faces, edges = inventory["faces"], inventory["edges"]
    linear, angular = inventory["tolerances"]["linear"], inventory["tolerances"]["angular"]
    candidates = []
    for fid, face in faces.items():
        data = face["native_face_data"]
        if face["surface_type"] != "Cylindrical" or data["normal_sense"] != 1 or data["radius"] <= 0:
            continue
        axis = _unit(data["direction"])
        if axis is None:
            continue
        principal = max(range(3), key=lambda i: abs(axis[i]))
        basis = [float(i == principal) for i in range(3)]
        principal_error = _parallel_residual(axis, basis)
        if principal_error > angular:
            continue
        plane_matches, cone_matches = [], []
        for eid in face["edge_ids"]:
            edge = edges[eid]
            if edge["edge_type"] != "Circular":
                continue
            for neighbor_id in edge["face_ids"]:
                if neighbor_id == fid:
                    continue
                other = faces[neighbor_id]
                od = other["native_face_data"]
                direction = _unit(od["direction"])
                if direction is None:
                    continue
                angle_error = _parallel_residual(axis, direction)
                if angle_error > angular:
                    continue
                if other["surface_type"] == "Planar":
                    coordinate = od["origin"][principal]
                    box = data["bounding_box"]
                    end_error = min(abs(coordinate - box[principal]), abs(coordinate - box[principal + 3]))
                    if end_error <= linear:
                        plane_matches.append((neighbor_id, eid, angle_error, end_error))
                elif other["surface_type"] == "Conical":
                    distance = _axis_distance(data["origin"], od["origin"], axis)
                    if distance <= linear:
                        cone_matches.append((neighbor_id, eid, angle_error, distance))
        for plane_id, plane_edge, plane_angle, end_error in plane_matches:
            for cone_id, cone_edge, cone_angle, axis_error in cone_matches:
                if cone_edge == plane_edge:
                    continue
                candidates.append({
                    "id": f"addition_{fid}_{plane_id}_{cone_id}",
                    "kind": "cylinder_shoulder_addition_candidate",
                    "source_faces": [fid, plane_id, cone_id],
                    "source_edges": [plane_edge, cone_edge],
                    "evidence": {
                        "snapshot_id": inventory["snapshot_id"],
                        "description": "Cylinder shares circular edges with an axial-end plane and coaxial cone; UF sense is a search filter only.",
                        "source_fields": ["surface_type", "native_face_data", "edge_type", "face_ids"],
                        "cylinder_data": data.copy(),
                        "plane_data": faces[plane_id]["native_face_data"].copy(),
                        "cone_data": faces[cone_id]["native_face_data"].copy(),
                        "matching_tolerances": inventory["tolerances"].copy(),
                        "length_unit": inventory["unit"], "angular_unit": "rad",
                        "residuals": {"principal_axis_angle_rad": principal_error,
                                      "plane_axis_angle_rad": plane_angle,
                                      "cone_axis_angle_rad": cone_angle,
                                      "plane_bbox_end_distance": end_error,
                                      "cone_axis_distance": axis_error},
                        "bbox_axis_span": data["bounding_box"][principal + 3] - data["bounding_box"][principal],
                        "bbox_span_is_thickness": False,
                    },
                    "parameters": [{"id": f"radius_{fid}", "dimension": "length",
                                    "value": data["radius"], "unit": inventory["unit"],
                                    "classification": "unclassified", "confirmation": "unconfirmed"}],
                    "alternatives": ["separate added cylindrical shoulder", "integral turned profile", "other construction consistent with the incomplete boundary"],
                    "open_items": [{"source_faces": [fid, plane_id, cone_id],
                                    "reason": "Material side, closed section, trimmed curves, connection, axial thickness and construction intent are not established."}],
                    "capability_requirements": ["closed_section_and_trim_evidence", "confirmed_construction_and_parameters"],
                    "depends_on": [], "confirmed": False,
                    "confirmation": {"status": "unconfirmed"},
                })
    return candidates
