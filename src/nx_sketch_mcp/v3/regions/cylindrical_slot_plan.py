"""Offline, evidence-limited finite-cylinder subtraction hypothesis.

IDs are local to the input P1 snapshot. This module does not create geometry.
"""

from dataclasses import dataclass
import math

from .common import InventoryError, normalize_snapshot


class SlotPlanError(ValueError):
    """The requested source binding cannot support this bounded hypothesis."""


@dataclass(frozen=True)
class SlotBinding:
    cylinder_face_id: str
    plane_face_ids: tuple[str, str]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _sub(a, b):
    return [x - y for x, y in zip(a, b)]


def _unit(v, label):
    length = math.hypot(*v)
    if not math.isfinite(length) or length == 0:
        raise SlotPlanError(f"{label}: invalid direction")
    return [x / length for x in v]


def _direction_data(face, label):
    data = face["native_face_data"]
    if data["normal_sense"] not in (-1, 1):
        raise SlotPlanError(f"{label}: unsupported normal_sense")
    return data, _unit(data["direction"], label)


def plan_slot(snapshot, binding: SlotBinding, *, tolerances):
    """Return a reviewable hypothesis from a validated raw P1 snapshot.

    Binding is explicit and snapshot-local. Thresholds are matching thresholds,
    not engineering tolerances. No material side or design intent is confirmed.
    """
    if not isinstance(binding, SlotBinding):
        raise SlotPlanError("binding: expected SlotBinding")
    ids = (binding.cylinder_face_id, *binding.plane_face_ids) if isinstance(binding.plane_face_ids, tuple) and len(binding.plane_face_ids) == 2 else ()
    if len(ids) != 3 or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != 3:
        raise SlotPlanError("binding: require three distinct explicit face IDs")
    try:
        inventory = normalize_snapshot(snapshot, tolerances=tolerances)
    except (InventoryError, OverflowError, TypeError) as exc:
        raise SlotPlanError(f"invalid snapshot: {exc}") from exc
    faces, edges = inventory["faces"], inventory["edges"]
    if any(i not in faces for i in ids):
        raise SlotPlanError("binding: face ID not present in snapshot")
    cylinder = faces[ids[0]]
    cd, axis = _direction_data(cylinder, ids[0])
    if cylinder["surface_type"].lower() != "cylindrical" or cd["normal_sense"] != -1:
        raise SlotPlanError("binding: expected negative-sense cylinder")
    radius = cd["radius"]
    if radius <= 0:
        raise SlotPlanError("cylinder: radius must be positive")
    # Canonical orientation is deterministic under reversal of the source axis.
    if next(x for x in axis if abs(x) > 1e-14) < 0:
        axis = [-x for x in axis]
    origin = cd["origin"]
    linear = inventory["tolerances"]["linear"]
    angular = inventory["tolerances"]["angular"]
    # A tilted plane does not define the requested axis-normal finite cylinder.
    # Use a roundoff bound as well as the user matching threshold.
    axis_bound = min(math.sin(min(angular, math.pi / 2)), 1e-12)
    sides = []
    for face_id in ids[1:]:
        face = faces[face_id]
        if face["surface_type"].lower() != "planar":
            raise SlotPlanError(f"{face_id}: expected planar face")
        data, direction = _direction_data(face, face_id)
        dot = _dot(direction, axis)
        residual = math.hypot(*(direction[i] - dot * axis[i] for i in range(3)))
        if residual > axis_bound:
            raise SlotPlanError(f"{face_id}: plane is not perpendicular to cylinder axis")
        shared = [edge_id for edge_id in cylinder["edge_ids"]
                  if edge_id in face["edge_ids"] and
                  set(edges[edge_id]["face_ids"]) == {ids[0], face_id} and
                  len(edges[edge_id]["face_ids"]) == 2 and
                  edges[edge_id]["edge_type"].lower() == "circular"]
        if len(shared) != 1:
            raise SlotPlanError(f"{face_id}: expected exactly one shared circular edge")
        t = _dot(_sub(data["origin"], origin), axis)
        if not math.isfinite(t):
            raise SlotPlanError(f"{face_id}: non-finite axial projection")
        sides.append({"face_id": face_id, "edge_id": shared[0], "t": t,
                      "source_origin": data["origin"], "source_direction": data["direction"],
                      "source_normal_sense": data["normal_sense"],
                      "direction_axis_dot": dot, "parallel_residual": residual})
    sides.sort(key=lambda side: side["t"])
    low, high = sides
    width = high["t"] - low["t"]
    if not math.isfinite(width) or width <= linear:
        raise SlotPlanError("planes: coincident or invalid separation")
    if low["direction_axis_dot"] <= 0 or high["direction_axis_dot"] >= 0:
        raise SlotPlanError("planes: source directions conflict with facing inward")
    if low["edge_id"] == high["edge_id"]:
        raise SlotPlanError("planes: shared edges must be distinct")
    midpoint = low["t"] + width / 2
    mid_axis_point = [origin[i] + midpoint * axis[i] for i in range(3)]
    if not all(math.isfinite(x) for x in mid_axis_point):
        raise SlotPlanError("planes: non-finite midpoint")
    for side in sides:
        side["axis_intersection"] = [origin[i] + side["t"] * axis[i] for i in range(3)]
        side["plane_residual"] = _dot(_sub(side["axis_intersection"], side["source_origin"]), _unit(side["source_direction"], side["face_id"]))
    edge_ids = sorted(set(e for face_id in ids for e in faces[face_id]["edge_ids"]))
    return {
        "schema": "cylindrical-slot-plan/1.0", "status": "reviewable_conditional_plan_not_executed",
        "snapshot_id": inventory["snapshot_id"], "id_scope": "input P1 snapshot only", "unit": inventory["unit"],
        "geometry_details_complete": inventory["geometry_details_complete"],
        "source": {"cylinder_face_id": ids[0], "plane_face_ids": list(ids[1:]),
                   "three_face_unique_edge_ids": edge_ids, "three_face_unique_edge_count": len(edge_ids),
                   "edges": [{"edge_id": e, "edge_type": edges[e]["edge_type"], "face_ids": edges[e]["face_ids"]} for e in edge_ids],
                   "cylinder_observation": {"origin": origin, "direction": cd["direction"], "normal_sense": cd["normal_sense"], "radius": radius},
                   "plane_observations_and_projections": sides},
        "derived": {"positive_axis": axis, "axis_origin": origin, "radius": radius,
                    "plane_axial_offsets": [low["t"], high["t"]], "width": width,
                    "midplane_axis_point": mid_axis_point, "midplane_normal": axis,
                    "matching_thresholds": {"linear": linear, "angular_rad": angular, "parallel_roundoff_bound": axis_bound}},
        "tool": {"kind": "finite_cylinder_intersection_of_two_axial_halfspaces", "closed_mathematical_set": True,
                 "definition": "For x, let t=dot(x-origin,axis), r=(x-origin)-t*axis. Tool={x: dot(r,r)<=radius^2 and low<=t<=high}.",
                 "operation_candidate": "subtract (stock intersection tool) from candidate stock",
                 "end_depth": "defined by stock intersection; no extra terminal plane or bounding-box inference"},
        "material_side": {"status": "conditional_unconfirmed", "evidence": "source plane directions face into the slab and the cylinder has negative UF sense; neither establishes occupancy"},
        "parameters_confirmation": "unconfirmed", "intent_confirmation": "unconfirmed", "geometry_proven": False, "execution_approved": False,
        "open_items": ["Explicit source binding does not establish that this candidate is globally unique.",
                       "Original directed FIN loops, trimmed boundary orientation and source section closure are not established by P1.",
                       "P1 edge journal_id strings provide at most finite sampled points, not a complete curve definition.",
                       "Candidate stock and material occupancy require independent confirmation; stock intersection defines the tool's actual engagement and depth.",
                       "Engineering parameter constraints and design intent require confirmation.",
                       "Backend capability and native geometry verification remain open."]}
