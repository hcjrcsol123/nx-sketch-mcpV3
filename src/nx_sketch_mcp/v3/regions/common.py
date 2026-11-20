"""Normalize a P1 reference snapshot for offline candidate recognition.

Logical IDs refer only to the supplied snapshot and its original array order.
They are not a way to locate entities in a later NX session. This inventory
does not supply the trimmed geometry missing from the P1 reader.
"""

from collections.abc import Mapping
from copy import deepcopy
import math


class InventoryError(ValueError):
    """Reference inventory cannot safely be used for recognition."""


def _mapping(value, where):
    if not isinstance(value, Mapping):
        raise InventoryError(f"{where}: expected mapping")
    return value


def _list(value, where):
    if not isinstance(value, list):
        raise InventoryError(f"{where}: expected list")
    return value


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise InventoryError(f"{where}: expected non-empty string")
    return value


def _number(value, where):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InventoryError(f"{where}: expected finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise InventoryError(f"{where}: expected finite number")
    return value


def _vector(value, size, where):
    if not isinstance(value, list) or len(value) != size:
        raise InventoryError(f"{where}: expected {size} numbers")
    return [_number(item, where) for item in value]


def _index(records, prefix, where):
    result = {}
    for n, record in enumerate(_list(records, where), 1):
        _mapping(record, f"{where}[{n - 1}]")
        tag = _text(record.get("tag"), f"{where}[{n - 1}].tag")
        if tag in result:
            raise InventoryError(f"{where}: duplicate tag {tag}")
        result[tag] = f"{prefix}{n:04d}"
    if not result:
        raise InventoryError(f"{where}: empty inventory")
    return result


def _links(record, field, index, where):
    tags = _list(record.get(field), f"{where}.{field}")
    if any(not isinstance(tag, str) or not tag.strip() for tag in tags):
        raise InventoryError(f"{where}.{field}: invalid tag")
    if len(tags) != len(set(tags)):
        raise InventoryError(f"{where}.{field}: duplicate tag")
    if any(tag not in index for tag in tags):
        raise InventoryError(f"{where}.{field}: unknown tag")
    return [index[tag] for tag in tags]


def normalize_snapshot(snapshot, *, tolerances):
    """Validate and copy a complete P1 inventory into the v0.1 analysis form.

    ``linear`` is in the inventory's length unit and ``angular`` is in radians.
    These are caller-chosen candidate matching thresholds, not engineering
    tolerances or evidence of native model precision. Geometric completeness is
    copied separately from inventory completeness and never inferred from it.
    """
    snapshot = _mapping(snapshot, "snapshot")
    tolerance = _mapping(tolerances, "tolerances")
    if set(tolerance) != {"linear", "angular"}:
        raise InventoryError("tolerances: require exactly linear and angular")
    tolerance = {name: _number(tolerance[name], f"tolerances.{name}")
                 for name in ("linear", "angular")}
    if any(value <= 0 for value in tolerance.values()):
        raise InventoryError("tolerances: values must be positive")
    if any(snapshot.get(key) is not True for key in ("ok", "complete", "inventory_complete")):
        raise InventoryError("snapshot: inventory is not complete")
    if snapshot.get("read_consistency_fault") is not False:
        raise InventoryError("snapshot: read consistency is not established")
    if snapshot.get("guard_errors") != [] or snapshot.get("verification_sample_errors") != []:
        raise InventoryError("snapshot: read or verification errors")
    details = snapshot.get("geometry_details_complete")
    if type(details) is not bool:
        raise InventoryError("snapshot: geometry completeness must be explicit")
    snapshot_id = _text(snapshot.get("snapshot_id"), "snapshot_id")
    inventory = _mapping(snapshot.get("inventory"), "inventory")
    if inventory.get("errors") != [] or inventory.get("selection_resolved") is not True:
        raise InventoryError("inventory: errors or unresolved selection")
    units = {"Millimeters": "mm", "Meters": "m", "Inches": "inch"}
    unit = units.get(inventory.get("units"))
    if unit is None:
        raise InventoryError("inventory: unsupported or missing unit")
    body = _mapping(inventory.get("selected_body"), "selected_body")
    raw_faces = _list(body.get("faces"), "faces")
    raw_edges = _list(body.get("edges"), "edges")
    face_ids = _index(raw_faces, "F", "faces")
    edge_ids = _index(raw_edges, "E", "edges")

    faces = {}
    for face in raw_faces:
        ident = face_ids[face["tag"]]
        data = _mapping(face.get("native_face_data"), f"{ident}.native_face_data")
        values = {
            "origin": _vector(data.get("origin"), 3, f"{ident}.origin"),
            "direction": _vector(data.get("direction"), 3, f"{ident}.direction"),
            "bounding_box": _vector(data.get("bounding_box"), 6, f"{ident}.bounding_box"),
            "radius": _number(data.get("radius"), f"{ident}.radius"),
            "radius_data": _number(data.get("radius_data"), f"{ident}.radius_data"),
            "normal_sense": _number(data.get("normal_sense"), f"{ident}.normal_sense"),
            "uf_type": _number(data.get("uf_type"), f"{ident}.uf_type"),
        }
        box = values["bounding_box"]
        if any(box[i] > box[i + 3] for i in range(3)):
            raise InventoryError(f"{ident}: invalid bounding box")
        faces[ident] = {"id": ident, "source_tag": face["tag"],
                        "surface_type": _text(face.get("surface_type"), f"{ident}.surface_type"),
                        "native_face_data": values,
                        "edge_ids": _links(face, "edge_tags", edge_ids, ident)}
    edges = {}
    for edge in raw_edges:
        ident = edge_ids[edge["tag"]]
        edges[ident] = {"id": ident, "source_tag": edge["tag"],
                        "edge_type": _text(edge.get("edge_type"), f"{ident}.edge_type"),
                        "face_ids": _links(edge, "face_tags", face_ids, ident)}
    for face_id, face in faces.items():
        for edge_id in face["edge_ids"]:
            if face_id not in edges[edge_id]["face_ids"]:
                raise InventoryError(f"{face_id}/{edge_id}: asymmetric adjacency")
    for edge_id, edge in edges.items():
        for face_id in edge["face_ids"]:
            if edge_id not in faces[face_id]["edge_ids"]:
                raise InventoryError(f"{edge_id}/{face_id}: asymmetric adjacency")
    return {"contract_version": "0.1", "snapshot_id": snapshot_id, "unit": unit,
            "tolerances": deepcopy(tolerance), "geometry_details_complete": details,
            "faces": faces, "edges": edges}
