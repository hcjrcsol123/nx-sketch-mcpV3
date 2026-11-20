"""Unconfirmed equal-radius hypotheses from one offline inventory.

The matching tolerance groups observations only; it is not a design tolerance
and the result does not establish a driving relationship or feature pattern.
"""

import math


def _positive(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and value > 0)


def recognize(inventory):
    """Group negative-sense cylindrical radii within a bounded total spread.

    Grouping is deterministic in radius/ID order and not transitive: the
    smallest and largest radius of each group must be within the linear
    matching threshold. It is not a complete inventory of possible relations.
    """
    tolerance, unit = inventory["tolerances"]["linear"], inventory["unit"]
    if not _positive(tolerance):
        raise ValueError("linear matching tolerance must be positive and finite")
    observations = []
    for face_id, face in inventory["faces"].items():
        data = face["native_face_data"]
        radius = data.get("radius")
        if (face["surface_type"].lower() == "cylindrical"
                and data.get("normal_sense") == -1 and _positive(radius)):
            observations.append((radius, face_id, face))
    observations.sort(key=lambda item: (item[0], item[1]))
    groups = []
    for item in observations:
        if not groups or item[0] - groups[-1][0][0] > tolerance:
            groups.append([item])
        else:
            groups[-1].append(item)
    candidates = []
    for group in groups:
        if len(group) < 2:
            continue
        ids = sorted(item[1] for item in group)
        edges = sorted({edge for _, _, face in group for edge in face["edge_ids"]})
        parameters = [{"id": "radius_" + face_id, "dimension": "length", "value": radius,
                       "unit": unit, "classification": "unclassified", "confirmation": "unconfirmed"}
                      for radius, face_id, _ in group]
        candidates.append({
            "id": "REL_equal_radius_" + "_".join(ids),
            "kind": "possible_equal_radius_relation",
            "source_faces": ids, "source_edges": edges,
            "evidence": [{"type": "native_radius_comparison", "snapshot_id": inventory["snapshot_id"],
                          "observations": [{"face_id": face_id, "radius": radius,
                                            "normal_sense": face["native_face_data"]["normal_sense"],
                                            "uf_type": face["native_face_data"]["uf_type"],
                                            "edge_ids": list(face["edge_ids"])}
                                           for radius, face_id, face in group],
                          "min_radius": group[0][0], "max_radius": group[-1][0],
                          "observed_spread": group[-1][0] - group[0][0], "linear_threshold": tolerance,
                          "unit": unit, "basis": "UF cylindrical radii and negative normal_sense; spread is a matching observation only"}],
            "parameters": parameters,
            "alternatives": ["independent radii may happen to match in this snapshot and may change independently",
                             "a shared driving radius could make the radii change together, if intent is confirmed"],
            "open_items": [f"For faces {ids}, confirm design intent and whether each radius is independent or a shared driving relation; matching values do not establish equality or edit behavior.",
                           "Complete trims, feature identity and editable parameters remain unverified; do not infer a pattern, hole type or operation from this group."],
            "capability_requirements": ["confirm design intent and parameter bindings", "evaluate and verify any approved relation on target models"],
            "depends_on": [], "confirmed": False, "confirmation": {"status": "unconfirmed"},
        })
    return candidates


def evaluate_hypothesis(radii, *, interpretation, edited_index, edited_value):
    """Simulate one edit under an explicitly chosen, still hypothetical model.

    For ``shared`` the edit sets every radius to the edited value. For
    ``independent`` only the selected radius changes. No IR plan is generated,
    no candidate is confirmed, and this function cannot approve execution.
    """
    if not isinstance(radii, (list, tuple)) or len(radii) < 2 or not all(_positive(r) for r in radii):
        raise ValueError("at least two positive finite radii required")
    if isinstance(edited_index, bool) or not isinstance(edited_index, int) or not 0 <= edited_index < len(radii):
        raise ValueError("edited_index out of range")
    if not _positive(edited_value):
        raise ValueError("edited radius must be positive and finite")
    if interpretation == "shared":
        return [edited_value] * len(radii)
    if interpretation == "independent":
        result = list(radii)
        result[edited_index] = edited_value
        return result
    raise ValueError("unknown hypothesis interpretation")
