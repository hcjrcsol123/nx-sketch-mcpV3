"""Assemble an evidence-scoped P3 draft; this is not a V3 IR or executor."""
from collections import defaultdict
from collections.abc import Mapping
from copy import deepcopy
from .relation_decisions import bind as bind_relation_decision


def assemble_plan(inventory, candidates, *, source_path, capability_evidence=None, relation_decision=None):
    """Audit candidate sources, open requirements, and their dependency graph.

    A geometric explanation counts only with explicit confirmation and a
    separate proven-geometry evidence record. Candidate overlap is reported as
    evidence overlap; overlap between confirmed explanations blocks coverage.
    A consumed capability closure must have exactly status="closed" and a
    nonblank string evidence reference. Adopted closures and candidate/requirement
    uses are copied into the result for later review and serialization.
    This planning-only API never grants authority to execute a model.
    """
    if not isinstance(inventory, Mapping) or not isinstance(candidates, list):
        raise TypeError("expected normalized inventory and candidate list")
    if not isinstance(source_path, str) or not source_path.strip():
        raise ValueError("source_path must identify the inventory evidence")
    if capability_evidence is None:
        capability_evidence = {}
    if not isinstance(capability_evidence, Mapping):
        raise TypeError("capability_evidence must be a mapping")
    faces, edges = inventory["faces"], inventory["edges"]
    findings, by_id, invalid = [], {}, set()
    adopted_capabilities, capability_uses = {}, []
    mentions, unresolved, explained = defaultdict(list), defaultdict(list), defaultdict(list)

    def finding(code, target, detail):
        findings.append({"code": code, "target": target, "detail": detail})

    def invalid_finding(code, target, detail):
        invalid.add(target)
        finding(code, target, detail)

    def nonblank(value):
        return isinstance(value, str) and bool(value.strip())

    for position, item in enumerate(candidates):
        if not isinstance(item, Mapping):
            finding("invalid_candidate", str(position), "candidate must be a mapping")
            continue
        ident = item.get("id")
        if not isinstance(ident, str) or not ident.strip():
            finding("invalid_candidate_id", str(position), "candidate needs a non-empty ID")
            continue
        if ident in by_id:
            invalid_finding("duplicate_candidate_id", ident, "candidate IDs must be unique")
            continue
        by_id[ident] = item
        if item.get("snapshot_id") != inventory.get("snapshot_id"):
            invalid_finding("candidate_snapshot_mismatch", ident, "candidate must identify the same source snapshot")
        for field in ("source_faces", "source_edges", "depends_on", "parameters",
                      "alternatives", "open_items", "capability_requirements"):
            value = item.get(field)
            if not isinstance(value, list):
                invalid_finding("invalid_candidate_field", ident, field + " must be a list")
        if not nonblank(item.get("kind")):
            invalid_finding("invalid_candidate_field", ident, "kind is required")
        evidence = item.get("evidence")
        if (not isinstance(evidence, (list, Mapping)) or not evidence
                or isinstance(evidence, list) and any(not isinstance(e, Mapping) or not e for e in evidence)):
            invalid_finding("missing_candidate_evidence", ident, "non-empty source evidence required")
        source_faces = item.get("source_faces") if isinstance(item.get("source_faces"), list) else []
        source_edges = item.get("source_edges") if isinstance(item.get("source_edges"), list) else []
        if not source_faces:
            invalid_finding("missing_source_faces", ident, "candidate requires source faces")
        if not source_edges:
            invalid_finding("missing_source_edges", ident, "candidate requires source edges")
        for field, ids, known in (("source_faces", source_faces, faces), ("source_edges", source_edges, edges)):
            seen = set()
            for source_id in ids:
                if not isinstance(source_id, str) or source_id not in known:
                    invalid_finding("unknown_source", ident, f"{field}: {source_id!r}")
                elif source_id in seen:
                    invalid_finding("duplicate_source", ident, f"{field}: {source_id}")
                else:
                    seen.add(source_id)
                    if field == "source_faces":
                        target = unresolved if item.get("kind") == "unresolved_complex_surface" else mentions
                        target[source_id].append(ident)
        for parameter in item.get("parameters", []) if isinstance(item.get("parameters"), list) else []:
            if (not isinstance(parameter, Mapping) or not isinstance(parameter.get("dimension"), str)
                    or parameter.get("dimension") not in {"length", "angle", "scalar"}):
                invalid_finding("invalid_parameter", ident, "parameter dimension must be length, angle or scalar")
        confirmed = item.get("confirmed") is True
        confirmation = item.get("confirmation")
        if not confirmed or not isinstance(confirmation, Mapping) or confirmation.get("status") != "confirmed" or not nonblank(confirmation.get("by")) or not nonblank(confirmation.get("evidence")):
            finding("unconfirmed_candidate", ident, "candidate requires attributable confirmation")
            confirmed = False
        proof = item.get("geometry_proof")
        if (not isinstance(proof, Mapping) or proof.get("status") != "proven"
                or not nonblank(proof.get("evidence")) or proof.get("snapshot_id") != inventory.get("snapshot_id")):
            finding("missing_geometry_proof", ident, "full trimmed-region evidence is not established")
            confirmed = False
        if item.get("snapshot_id") != inventory.get("snapshot_id"):
            confirmed = False
        if item.get("coverage_role") != "geometry":
            confirmed = False
        for open_item in item.get("open_items", []) if isinstance(item.get("open_items"), list) else []:
            finding("open_item", ident, deepcopy(open_item))
        for requirement in item.get("capability_requirements", []) if isinstance(item.get("capability_requirements"), list) else []:
            if not isinstance(requirement, str) or not requirement.strip():
                invalid_finding("invalid_capability", ident, "capability must be a non-empty string")
                continue
            closure = capability_evidence.get(requirement)
            if (not isinstance(closure, Mapping) or set(closure) != {"status", "evidence"}
                    or closure.get("status") != "closed" or not nonblank(closure.get("evidence"))):
                finding("open_capability", ident, requirement)
            else:
                adopted_capabilities[requirement] = deepcopy(dict(closure))
                capability_uses.append({"candidate_id": ident, "requirement": requirement})

    graph = {}
    for ident, item in by_id.items():
        deps = item.get("depends_on") if isinstance(item.get("depends_on"), list) else []
        graph[ident] = []
        for dep in deps:
            if not isinstance(dep, str) or dep not in by_id:
                invalid_finding("unknown_dependency", ident, repr(dep))
            elif dep in graph[ident]:
                invalid_finding("duplicate_dependency", ident, dep)
            else:
                graph[ident].append(dep)
    state, order, stack = {}, [], []

    def visit(node):
        if state.get(node) == 1:
            finding("dependency_cycle", node, "cyclic candidate dependency")
            invalid.update(stack[stack.index(node):])
            return
        if state.get(node) == 2:
            return
        state[node] = 1
        stack.append(node)
        for dep in graph[node]:
            visit(dep)
        stack.pop()
        state[node] = 2
        order.append(node)

    for node in graph:
        visit(node)
    # A structurally invalid prerequisite cannot support a valid explanation.
    changed = True
    while changed:
        changed = False
        for ident, deps in graph.items():
            if ident not in invalid and any(dep in invalid for dep in deps):
                invalid_finding("invalid_dependency", ident, "dependency is structurally invalid")
                changed = True
    for ident, item in by_id.items():
        confirmation, proof = item.get("confirmation"), item.get("geometry_proof")
        eligible = (ident not in invalid and item.get("coverage_role") == "geometry"
                    and item.get("confirmed") is True and isinstance(confirmation, Mapping)
                    and confirmation.get("status") == "confirmed" and nonblank(confirmation.get("by"))
                    and nonblank(confirmation.get("evidence")) and isinstance(proof, Mapping)
                    and proof.get("status") == "proven" and nonblank(proof.get("evidence"))
                    and proof.get("snapshot_id") == inventory.get("snapshot_id"))
        if eligible:
            for face_id in item["source_faces"]:
                explained[face_id].append(ident)
    residual = sorted(set(faces) - (set(mentions) | set(unresolved)))
    unexplained = sorted(set(faces) - set(explained))
    overlaps = {face: ids for face, ids in sorted(mentions.items()) if len(ids) > 1}
    confirmed_overlaps = {face: ids for face, ids in sorted(explained.items()) if len(ids) > 1}
    for face in unexplained:
        finding("unexplained_face", face, "no confirmed, proven geometry explanation")
    for face, ids in confirmed_overlaps.items():
        finding("duplicate_explanation", face, ids)
    if inventory.get("geometry_details_complete") is not True:
        finding("incomplete_geometry", "inventory", "trimmed surfaces and full edge curves are not established")
    finding("construction_order_unresolved", "plan", "candidate adjacency is not proof of boolean or modifier order")
    finding("planning_only", "plan", "P3 draft is not an executable IR or model-operation authorization")
    report = {
        "schema": "p3-analysis-plan/0.1", "snapshot_id": inventory["snapshot_id"],
        "source_path": source_path, "unit": inventory["unit"],
        "tolerances": deepcopy(inventory["tolerances"]),
        "threshold_note": "Exploratory matching thresholds; not reference precision or manufacturing tolerance.",
        "candidates": deepcopy(candidates), "candidate_order": order,
        "capability_evidence": adopted_capabilities, "capability_uses": capability_uses,
        "construction_order": {"status": "unresolved", "operations": []},
        "coverage": {"total_faces": len(faces), "candidate_faces": len(mentions),
                     "explained_faces": len(explained), "candidate_face_ids": sorted(mentions),
                     "unresolved_face_ids": sorted(unresolved),
                     "explained_face_ids": sorted(explained), "residual_face_ids": residual,
                     "unexplained_face_ids": unexplained, "candidate_overlaps": overlaps,
                     "confirmed_overlaps": confirmed_overlaps},
        "findings": findings, "execution_approved": False,
    }
    if relation_decision is not None:
        if not isinstance(relation_decision, Mapping) or set(relation_decision) != {
                "decision", "decision_evidence", "reference_analysis", "reference_analysis_path"}:
            raise ValueError("invalid relation decision inputs")
        report["relation_intents"] = [bind_relation_decision(
            relation_decision["decision"], decision_evidence=relation_decision["decision_evidence"],
            reference_analysis=relation_decision["reference_analysis"],
            reference_analysis_path=relation_decision["reference_analysis_path"],
            inventory=inventory, candidates=candidates)]
    return report
