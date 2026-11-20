"""Audit supplied parameter and source-region records, without inferring geometry.

The input is a separate mapping with lists ``parameters``, ``regions`` and
``relations`` and a ``source_inventory`` mapping. IDs are scoped to the
supplied plan and inventory. The result is a bookkeeping review, not a model,
constraint-evaluation, identity-rebinding, or geometry-verification gate.
"""

from collections.abc import Mapping
import math


_UNITS = {"length": {"m", "mm", "inch"}, "angle": {"rad"}, "scalar": {"1"}}
_POLICIES = {"reject", "stop"}


def _number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def audit_ledger(plan, ledger):
    """Return explicit gaps and scoped coverage for a T07 Plan and ledger.

    A confirmation is ``{status: 'confirmed', by: ..., evidence: ...}``.
    Parameter ``edit_domain`` is a range with numeric lower/upper and boolean
    lower_inclusive/upper_inclusive, or ``{kind: 'not_editable'}``. Relation
    expressions are retained for review, not interpreted here; every relation
    therefore remains in ``requires_evaluation`` even for a complete ledger.
    """
    if not isinstance(ledger, Mapping):
        raise TypeError("ledger must be a mapping")
    document = plan.to_dict()
    findings = []

    def gap(code, target, detail):
        findings.append({"code": code, "target": target, "detail": detail})

    def records(container, key):
        values = container.get(key)
        if not isinstance(values, list):
            gap("invalid_records", key, "expected a list")
            return {}
        result = {}
        for index, item in enumerate(values):
            if not isinstance(item, Mapping) or not _text(item.get("id")):
                gap("invalid_record", f"{key}[{index}]", "record requires a non-empty id")
                continue
            ident = item["id"]
            if ident in result:
                gap("duplicate_id", ident, f"duplicate {key} record")
            else:
                result[ident] = item
        return result

    def confirmation(item, target):
        record = item.get("confirmation")
        if (not isinstance(record, Mapping) or record.get("status") != "confirmed"
                or not _text(record.get("by")) or not _text(record.get("evidence"))):
            gap("unconfirmed", target, "confirmation requires confirmed status, by, and evidence")

    def ids(value, target):
        if not isinstance(value, list) or any(not _text(i) for i in value):
            gap("invalid_ids", target, "expected a list of non-empty IDs")
            return []
        if len(set(value)) != len(value):
            gap("duplicate_id", target, "duplicate ID in list")
        return value

    plan_parameters = records(document, "parameters")
    plan_regions = records(document, "regions")
    plan_constraints = records(document, "constraints")
    parameters = records(ledger, "parameters")
    regions = records(ledger, "regions")
    relations = records(ledger, "relations")

    for key, expected, actual in (("parameter", plan_parameters, parameters),
                                  ("region", plan_regions, regions)):
        for ident in expected.keys() - actual.keys():
            gap(f"missing_{key}", ident, f"plan {key} has no ledger record")
        for ident in actual.keys() - expected.keys():
            gap(f"unknown_{key}", ident, f"ledger {key} is not in the plan")
    for ident in plan_constraints.keys() - relations.keys():
        gap("missing_relation", ident, "plan constraint has no relation record")

    for ident, item in parameters.items():
        source = plan_parameters.get(ident, {})
        category = item.get("classification")
        if category not in {"independent", "derived", "fixed"}:
            gap("unclassified_parameter", ident, "classification must be independent, derived, or fixed")
        if not _text(item.get("reason")):
            gap("missing_reason", ident, "classification reason required")
        if item.get("unit") not in _UNITS.get(source.get("dimension"), set()):
            gap("invalid_unit", ident, "unit must match the plan dimension")
        if source.get("dimension") == "length" and item.get("unit") != document["reference"]["length_unit"]:
            gap("plan_unit_mismatch", ident, "ledger length unit must equal the plan length unit")
        initial = item.get("initial_value")
        if not _number(initial):
            gap("invalid_initial_value", ident, "finite numeric initial value required")
        elif source.get("value") is not None and initial != source["value"]:
            gap("initial_value_mismatch", ident, "initial value differs from the plan")
        domain = item.get("edit_domain")
        if not isinstance(domain, Mapping):
            gap("invalid_edit_domain", ident, "edit domain required")
        elif category == "independent":
            lower, upper = domain.get("lower"), domain.get("upper")
            lo_inc, hi_inc = domain.get("lower_inclusive"), domain.get("upper_inclusive")
            if (domain.get("kind") != "range" or not _number(lower) or not _number(upper)
                    or type(lo_inc) is not bool or type(hi_inc) is not bool
                    or lower > upper or (lower == upper and not (lo_inc and hi_inc))):
                gap("invalid_edit_domain", ident, "independent parameter needs a non-empty bounded range")
            elif _number(initial) and (initial < lower or initial > upper
                    or (initial == lower and not lo_inc) or (initial == upper and not hi_inc)):
                gap("initial_out_of_range", ident, "initial value falls outside the edit domain")
        elif domain.get("kind") != "not_editable":
            gap("invalid_edit_domain", ident, "fixed and derived parameters must be non-editable")
        if item.get("out_of_bounds") not in _POLICIES:
            gap("invalid_out_of_bounds_policy", ident, "reject or stop policy required")
        if category == "derived" and not _text(source.get("expression")):
            gap("missing_expression", ident, "derived parameter needs a plan expression")
        if category in {"independent", "fixed"} and source.get("expression") is not None:
            gap("classification_conflict", ident, "an expression parameter must be derived")
        for relation_id in ids(item.get("relation_ids"), ident):
            if relation_id not in relations:
                gap("unknown_relation", ident, f"relation {relation_id} is absent")
            elif not isinstance(relations[relation_id].get("parameter_ids"), list) or ident not in relations[relation_id]["parameter_ids"]:
                gap("unlinked_parameter", ident, f"relation {relation_id} does not link back")
        confirmation(item, ident)

    for ident, item in relations.items():
        source = plan_constraints.get(ident)
        if source is not None and source.get("confirmed") is not True:
            gap("unconfirmed_plan_relation", ident, "plan constraint is not confirmed")
        if not _text(item.get("expression")):
            gap("missing_relation_expression", ident, "relation expression required")
        members = ids(item.get("parameter_ids"), ident)
        if source is not None and set(members) != set(source.get("parameters", [])):
            gap("relation_members_mismatch", ident, "relation parameters differ from plan constraint")
        if not members:
            gap("missing_relation_parameters", ident, "relation must name its parameters")
        for parameter_id in members:
            if parameter_id not in plan_parameters:
                gap("unknown_relation_parameter", ident, f"parameter {parameter_id} is absent")
            elif (not isinstance(parameters.get(parameter_id, {}).get("relation_ids"), list)
                  or ident not in parameters[parameter_id]["relation_ids"]):
                gap("unlinked_relation", ident, f"parameter {parameter_id} does not link back")
        if item.get("out_of_bounds") not in _POLICIES:
            gap("invalid_out_of_bounds_policy", ident, "reject or stop policy required")
        confirmation(item, ident)

    inventory = ledger.get("source_inventory")
    if not isinstance(inventory, Mapping):
        gap("missing_inventory", "source_inventory", "scoped source inventory required")
        inventory = {}
    scope = inventory.get("scope")
    if not _text(scope) or not _text(inventory.get("reference_id")) or not _text(inventory.get("evidence")):
        gap("invalid_inventory_identity", "source_inventory", "reference, scope and evidence required")
    if inventory.get("reference_id") != document["reference"]["snapshot_id"]:
        gap("inventory_reference_mismatch", "source_inventory", "inventory and plan snapshot IDs must match")
    if inventory.get("complete") is not True:
        gap("incomplete_inventory", "source_inventory", "explicit inventory completeness required")
    faces = ids(inventory.get("face_ids"), "source_inventory")
    if not faces:
        gap("empty_inventory", "source_inventory", "at least one source face required")
    covered = set()
    for ident, item in regions.items():
        source = plan_regions.get(ident)
        if source is not None and source.get("confirmed") is not True:
            gap("unconfirmed_plan_region", ident, "plan region is not confirmed")
        if not _text(item.get("explanation")):
            gap("unexplained_region", ident, "region explanation required")
        confirmation(item, ident)
        face_ids = ids(item.get("source_face_ids"), ident)
        if source is not None:
            plan_face_ids = {entry["logical_id"] for entry in source.get("source_geometry", [])
                             if entry.get("geometry_kind") == "face"}
            if set(face_ids) != plan_face_ids:
                gap("region_sources_mismatch", ident, "region source faces differ from plan logical sources")
        if not face_ids:
            gap("missing_region_source", ident, "region needs at least one source face")
        if item.get("source_scope") != scope or not _text(scope):
            gap("source_scope_mismatch", ident, "region and inventory scopes must match")
            continue
        for face in face_ids:
            if face not in faces:
                gap("unknown_source_face", ident, f"face {face} absent from inventory")
            elif ident in plan_regions and _text(item.get("explanation")):
                covered.add(face)
    for face in set(faces) - covered:
        gap("unexplained_source_face", face, "source face has no explained plan region")
    for open_item in document.get("open_items", []):
        gap("plan_open_item", "plan", open_item)

    return {
        "ready_for_review": not findings,
        "findings": findings,
        "coverage": {"plan_parameters": len(plan_parameters), "ledger_parameters": len(parameters),
                     "plan_regions": len(plan_regions), "ledger_regions": len(regions),
                     "source_faces": len(set(faces)), "explained_source_faces": len(covered)},
        "requires_evaluation": ([{"kind": "relation", "id": ident} for ident in sorted(relations)]
                                + [{"kind": "derived_parameter", "id": ident}
                                   for ident, item in sorted(parameters.items())
                                   if item.get("classification") == "derived"]),
        "execution_approved": False,
        "scope_note": "Bookkeeping only; inventory identity, geometry, constraint evaluation and native editing are not verified.",
    }
