"""Limited conical transition hypotheses, based on local profile evidence.

These hypotheses do not classify a face as a chamfer, draft or blend, and
do not establish tangency, full trim, feature history or tool eligibility.
"""

from copy import deepcopy
import math

from .profiles import recognize as recognize_profiles


def recognize(inventory):
    """Return unconfirmed adjacent cylinder/cone transitions for one snapshot."""
    result = []
    for profile in recognize_profiles(inventory):
        if profile["kind"] != "coaxial_cylinder_cone_chain":
            continue
        angle = next((p for p in profile["parameters"]
                      if p["id"].endswith(":cone_half_angle")), None)
        if angle is None or not (0 < angle["value"] < math.pi / 2):
            continue
        shared = next(e for e in profile["evidence"] if e["type"] == "shared_edge")
        face_ids = list(profile["source_faces"])
        edge_types = {eid: inventory["edges"][eid]["edge_type"] for eid in profile["source_edges"]}
        complex_edges = [eid for eid, kind in edge_types.items() if kind in ("Spline", "Intersection")]
        result.append({
            "id": "transition-" + shared["edge_id"],
            "kind": "conical_transition_candidate",
            "source_faces": face_ids,
            "source_edges": list(profile["source_edges"]),
            "evidence": deepcopy(profile["evidence"]) + [
                {"type": "shared_profile_evidence", "profile_candidate_id": profile["id"],
                 "basis": "shared observation only; construction dependency is not established"},
                {"type": "boundary_edge_types", "edges": edge_types,
                 "complex_edge_ids": complex_edges,
                 "basis": "native edge type and incidence only; no edge curve or trim definition"}],
            "parameters": deepcopy(profile["parameters"]),
            "alternatives": ["conical portion of a verified revolved profile (F13)",
                             "separately built analytic geometry and a verified boolean (F12/F15)",
                             "another editable construction after intent and full geometry are established"],
            "open_items": [
                {"faces": face_ids, "issue": "Shared incidence and an angle do not prove tangent continuity; obtain boundary curve, surface normals and tangency evidence."},
                {"faces": face_ids, "issue": "Trim, complete profile, transition extent, and whether the feature is chamfer, draft or another operation remain unknown."},
                {"faces": face_ids, "issue": "Other boundary regions, including possible blends or round transitions, remain unresolved; classify only from additional local geometry evidence."},
                {"faces": face_ids, "issue": "The supporting body, boolean target, construction dependencies and operation order are not established."},
                {"faces": face_ids, "issue": "F16/F17 currently support restricted box straight edges; this circular non-box boundary is not eligible for direct use. T04.c remains open for complex edges."}],
            "capability_requirements": [
                "verify complete trimmed geometry, transition dimensions and editable construction on target versions",
                "T04.c: verify non-box and spline/intersection edge support or establish an equivalent editable construction; do not release F16/F17 directly"],
            "depends_on": [],
            "confirmed": False,
            "confirmation": {"status": "unconfirmed"},
        })
    return result
