"""Analyze one current P1 inventory without asserting executable reconstruction.

The observations are snapshot-local hypotheses, not persistent NX selectors.
A complete editable plan requires trimmed geometry, source correspondence,
construction order and attributable design decisions that this API does not infer.
"""
from .model_plan import assemble_plan
from .regions import additions, circular_relations, cuts, profiles, reference_slot, relations, transitions
from .regions.common import normalize_snapshot


def analyze_reference(snapshot, *, tolerances, source_label):
    """Return a P3 candidate report for the supplied inventory, without file lookup.

    ``source_label`` is informational and is never used to establish geometry or
    source identity. Thresholds are caller-selected matching limits in inventory
    units and radians, not engineering tolerances. This report is always planning
    only and cannot be passed to an executor as a generated model plan.
    """
    if not isinstance(source_label, str) or not source_label.strip():
        raise ValueError("source_label must be a non-empty diagnostic label")
    inventory = normalize_snapshot(snapshot, tolerances=tolerances)
    candidates = []
    for module in (profiles, additions, cuts, reference_slot, relations, circular_relations, transitions):
        for candidate in module.recognize(inventory):
            if "snapshot_id" in candidate and candidate["snapshot_id"] != inventory["snapshot_id"]:
                raise ValueError("candidate snapshot differs from current inventory")
            candidate["snapshot_id"] = inventory["snapshot_id"]
            candidates.append(candidate)
    return assemble_plan(inventory, candidates, source_path=source_label)

