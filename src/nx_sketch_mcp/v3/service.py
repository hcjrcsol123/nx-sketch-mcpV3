"""MCP-facing V3 reference planning; no implicit native writes or file lookup."""
from .reference_recognition import analyze_reference
from .project_root import project_root
from .design_guidance import design_guidance_base


class ReferenceBindingError(ValueError):
    """The read cannot establish its session binding or consistency."""


def analyze_current_reference(snapshot, *, request, tolerances):
    """Analyze only a freshly returned bridge inventory bound to this read.

    Snapshot IDs and topology IDs are local to this observation. They are not
    native selectors and cannot authorize a later session or a generated model.
    """
    if not isinstance(snapshot, dict):
        raise ReferenceBindingError("reference read did not return an object")
    if (snapshot.get("snapshot_id") != request["snapshot_id"]
            or snapshot.get("binding_epoch") != request["binding_epoch"]
            or snapshot.get("revision_id") != request["revision_id"]
            or snapshot.get("ownership_state") != "AI_OWNED"
            or snapshot.get("writes_halted") is not False
            or snapshot.get("revision_matches_cached_before_and_after") is not True):
        raise ReferenceBindingError("reference read does not match the current ownership, epoch, revision and snapshot")
    if (not isinstance(snapshot.get("session_epoch"), str) or not snapshot["session_epoch"]
            or not isinstance(snapshot.get("load_instance_id"), str) or not snapshot["load_instance_id"]):
        raise ReferenceBindingError("reference session and load identity are required")
    effects = snapshot.get("read_effects")
    consistency = snapshot.get("snapshot_consistency")
    if (not isinstance(effects, dict) or effects.get("unchanged") is not True
            or effects.get("is_modified_before") is not False or effects.get("is_modified_after") is not False
            or not isinstance(consistency, dict) or consistency.get("two_native_samples_equal") is not True):
        raise ReferenceBindingError("reference read consistency is not established")
    inventory = snapshot.get("inventory")
    if not isinstance(inventory, dict) or inventory.get("load_state") != "FullyLoaded":
        raise ReferenceBindingError("reference must be fully loaded")
    part_path = inventory.get("part_path")
    body = inventory.get("selected_body")
    if (not isinstance(part_path, str) or not part_path or len(part_path) > 4096
            or not isinstance(body, dict) or not isinstance(body.get("journal_id"), str)
            or not body["journal_id"] or len(body["journal_id"]) > 4096
            or inventory.get("units") not in {"Millimeters", "Meters", "Inches"}):
        raise ReferenceBindingError("reference path, selected body and units are required")
    report = analyze_reference(snapshot, tolerances=tolerances, source_label="current bridge reference read")
    return {
        "schema": "v3-reference-analysis-response/1",
        "status": "planning_only",
        "execution_approved": False,
        "snapshot_id": request["snapshot_id"],
        "read_provenance": {"session_epoch": snapshot["session_epoch"],
                            "load_instance_id": snapshot["load_instance_id"],
                            "binding_epoch": snapshot["binding_epoch"], "revision_id": snapshot["revision_id"],
                            "snapshot_id": snapshot["snapshot_id"], "source_path": part_path,
                            "selected_body_id": body["journal_id"], "units": inventory["units"],
                            "load_state": inventory["load_state"], "inventory_complete": snapshot.get("inventory_complete"),
                            "read_effects": {"is_modified_before": False, "is_modified_after": False, "unchanged": True}},
        "analysis": report,
        "design_guidance": {
            **design_guidance_base(), "actions": [],
            "limitations": [
                "No construction profiles or source-to-construction bindings are established by this inventory, so no specific shared-profile or pattern action is asserted.",
                "Equal nominal values alone do not imply shared drivers; preserve independent features if independent edits are intended.",
                "A circular layout alone does not prove that complete features, trims and edit behavior can be patterned.",
            ],
        },
        "blockers": [
            "The inventory does not establish complete trimmed geometry, material occupancy, and source-to-construction correspondence.",
            "This analysis is not an executable P3 final plan; NX2506 preparation and UG11 bundle export require a separately validated current-source plan.",
        ],
    }


def _source_path(value):
    from pathlib import Path
    if not isinstance(value, str) or not value.strip() or not Path(value).is_absolute():
        raise ValueError("source_path must be an absolute path to a reviewed disk source")
    return Path(value)


def review_disk_source(source_path, *, group_index=None):
    """Rebuild a reviewed exact-file plan under its evidence lease.

    This is not fresh geometric reconstruction or proof of any live NX state.
    Each call obtains a new lease. A native target still requires the normal
    takeover, revision, prepare, execute and verify lifecycle.
    """
    from .reference_evidence import bound_reference_plan
    from .nx2506_composition import compile_associative_preview
    path = _source_path(source_path)
    if group_index is not None and (type(group_index) is not int or group_index < 0):
        raise ValueError("group_index must be a nonnegative integer")
    with bound_reference_plan(path) as plan:
        preview = compile_associative_preview(plan)
        groups = preview["groups"]
        if group_index is not None:
            if group_index >= len(groups):
                raise ValueError("group_index is outside the preview")
            return {"schema": "v3-reviewed-source-group/1", "group_index": group_index,
                    "group_count": len(groups), "steps": groups[group_index],
                    "execution_approved": False, "source_scope": "reviewed identical disk file only"}
        return {"schema": "v3-reviewed-source-preview/1", "status": "reviewed_disk_source_only",
                "execution_approved": False, "group_count": len(groups),
                "output_id": preview["output_id"], "design_guidance": preview["design_guidance"],
                "limitations": ["Exact disk-source evidence reuse is not a general recognizer and does not prove the identity or clean state of a live NX part.",
                                "The plan is advisory; target ownership, prepare, execute, fresh verification and save/reopen use the existing gates.",
                                "Recognition of changed sizes or poses is not established by this route."]}


def export_reviewed_disk_source(source_path, output_path):
    """Export UG11 artifacts while the exact reviewed disk source is locked."""
    from pathlib import Path
    from .reference_evidence import bound_reference_plan
    from .export_bundle import export
    path = _source_path(source_path)
    if not isinstance(output_path, str) or not output_path.strip() or not Path(output_path).is_absolute():
        raise ValueError("output_path must be an absolute path to a new directory")
    root = project_root()
    with bound_reference_plan(path) as plan:
        target = export(plan, root, output_path)
    return {"schema": "v3-reviewed-source-export/1", "output_path": str(target),
            "status": "generated_only", "execution_approved": False,
            "source_scope": "reviewed identical disk file only",
            "limitations": ["This does not establish live NX source identity; target native execution and verification are separate."]}



def compare_design_options(plan, groups):
    """Evaluate client-provided profile definitions as advisory guidance."""
    import json
    from .design_guidance import build_design_guidance
    if not isinstance(plan, dict) or not isinstance(plan.get("construction"), dict):
        raise ValueError("plan must contain construction")
    construction = plan["construction"]
    if not isinstance(construction.get("profiles"), dict) or not isinstance(construction.get("nodes"), list):
        raise ValueError("construction requires profiles and nodes")
    if not isinstance(groups, list) or len(groups) > 128 or any(not isinstance(g, list) or len(g) > 512 or any(not isinstance(step, dict) for step in g) for g in groups):
        raise ValueError("groups must contain bounded arrays of step objects")
    try:
        encoded = json.dumps({"plan": plan, "groups": groups}, allow_nan=False, ensure_ascii=False).encode("utf8")
        if len(encoded) > 500000:
            raise ValueError("design comparison input exceeds 500000 bytes")
        result = build_design_guidance(plan, groups)
    except (KeyError, TypeError, AttributeError, UnicodeError, OverflowError) as exc:
        raise ValueError("malformed design comparison") from exc
    return {"schema": "v3-design-comparison/1", "input_scope": "client_supplied",
            "execution_approved": False, "design_guidance": result}
