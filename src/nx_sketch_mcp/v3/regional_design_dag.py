"""Evidence-scoped P3 design ledger, separate from model_plan and V3 IR.

Face responsibility is bookkeeping, not geometric explanation. The positive
planning path is limited to an explicitly checked simple polygon prism with
independently reviewed, snapshot-bound claims. Attestations are trusted project
records, not cryptographic authentication or P6 full-shape verification.
"""
from collections import Counter
from copy import deepcopy
import ast
from fractions import Fraction
import json
import math
from pathlib import Path
import re

from .regions.common import normalize_snapshot


class DesignDagError(ValueError):
    """Invalid or inconsistent planning inputs."""


_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_KINDS = {"stock", "subtract", "cavity", "root", "flank", "transition", "other"}
_CLAIMS = ("source_binding", "section", "trim", "closure", "material_side",
           "construction_order", "design_intent", "representation_error")
_DIMS = {"scalar": (0, 0), "length": (1, 0), "angle": (0, 1)}
_UNITS = {"scalar": "1", "length": "mm", "angle": "rad"}


def _fail(message):
    raise DesignDagError(message)


def _id(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        _fail("invalid logical ID")
    return value


def _unique(items, field):
    if not isinstance(items, list):
        _fail(field + " must be a list")
    result = {}
    for item in items:
        if not isinstance(item, dict):
            _fail(field + " item must be an object")
        ident = _id(item.get("id"))
        if ident in result:
            _fail("duplicate " + field + " ID")
        result[ident] = item
    return result


def _topological(graph):
    state, order = {}, []
    def visit(node):
        if state.get(node) == 1:
            _fail("dependency cycle")
        if state.get(node) == 2:
            return
        state[node] = 1
        for dep in graph[node]:
            if dep not in graph:
                _fail("unknown dependency")
            visit(dep)
        state[node] = 2
        order.append(node)
    for node in graph:
        visit(node)
    return order


def _path(root, text):
    if not isinstance(text, str) or not text.strip():
        _fail("source path is required")
    path = Path(text)
    if path.is_absolute() or any(p in (".", "..") for p in path.parts):
        _fail("source path must be repository-relative")
    try:
        target = (root / path).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise DesignDagError("source path missing") from exc
    if not target.is_relative_to(root) or not target.is_file():
        _fail("source path escapes repository or is not a file")
    return target


def _source(root, source, snapshot_id):
    if (not isinstance(source, dict) or set(source) != {"path", "snapshot_id", "scope"}
            or not isinstance(source["scope"], str) or not source["scope"].strip()
            or source["snapshot_id"] != snapshot_id):
        _fail("invalid or mismatched P1-scoped evidence reference")
    doc = _read(root, source["path"])
    if not isinstance(doc, dict): _fail("source evidence must be a JSON object")
    actual = doc.get("p1_snapshot_id", doc.get("snapshot_id"))
    if actual is None and isinstance(doc.get("source_evidence"), dict):
        actual = doc["source_evidence"].get("p1_source", {}).get("snapshot_id")
        if actual is None and isinstance(doc["source_evidence"].get("P1"), str):
            actual = _read(root, doc["source_evidence"]["P1"]).get("snapshot_id")
    if actual is None and isinstance(doc.get("sources"), dict) and isinstance(doc["sources"].get("P1"), str):
        actual = _read(root, doc["sources"]["P1"]).get("snapshot_id")
    if actual != snapshot_id:
        _fail("evidence document does not bind the P1 snapshot")


def _read(root, path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out: _fail("duplicate evidence JSON key")
            out[key] = value
        return out
    def bad(_):
        _fail("non-finite evidence JSON")
    with _path(root, path).open(encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=unique, parse_constant=bad)


def _attestation(root, reference, snapshot_id, region_id, claim):
    """Check the review chain; the reviewer and signed decision are trust inputs."""
    _source(root, reference, snapshot_id)
    evidence = _read(root, reference["path"])
    fields = {"schema", "snapshot_id", "region_id", "claim", "author", "evidence_kind", "sources", "review", "details"}
    if (not isinstance(evidence, dict) or set(evidence) != fields
            or evidence["schema"] != "p3-planning-evidence/1.0" or evidence["snapshot_id"] != snapshot_id
            or evidence["region_id"] != region_id or evidence["claim"] != claim
            or not isinstance(evidence["author"], str) or not evidence["author"].strip()
            or evidence["evidence_kind"] not in {"native", "analytic", "semantic_binding", "user_decision"}
            or not isinstance(evidence["sources"], list) or not evidence["sources"]
            or not isinstance(evidence["details"], dict)
            or not isinstance(evidence["details"].get("argument"), str) or not evidence["details"]["argument"].strip()):
        _fail("invalid planning evidence record")
    for source in evidence["sources"]:
        _source(root, source, snapshot_id)
    review = _read(root, evidence["review"])
    if (not isinstance(review, dict) or set(review) != {"schema", "snapshot_id", "region_id", "claim", "evidence_path", "evidence_witness", "source_witnesses", "reviewer", "conclusion"}
            or review["schema"] != "p3-planning-review/1.0" or review["snapshot_id"] != snapshot_id
            or review["region_id"] != region_id or review["claim"] != claim
            or review["evidence_path"] != reference["path"] or review["conclusion"] != "accepted"
            or json.dumps(review["evidence_witness"], sort_keys=True, allow_nan=False, separators=(",", ":"))
               != json.dumps(evidence, sort_keys=True, allow_nan=False, separators=(",", ":"))
            or not isinstance(review["reviewer"], str) or not review["reviewer"].strip()
            or review["reviewer"] == evidence["author"]):
        _fail("missing, mismatched or non-independent review record")
    source_witnesses = review["source_witnesses"]
    if not isinstance(source_witnesses, list) or len(source_witnesses) != len(evidence["sources"]):
        _fail("review does not bind all source contents")
    for source, witness in zip(evidence["sources"], source_witnesses):
        if (not isinstance(witness, dict) or set(witness) != {"path", "frozen_copy"}
                or witness["path"] != source["path"]):
            _fail("source witness mismatch")
        original, frozen = _path(root, witness["path"]), _path(root, witness["frozen_copy"])
        if original.samefile(frozen) or original.read_bytes() != frozen.read_bytes():
            _fail("source evidence differs from independent frozen copy")
    if claim == "design_intent" or claim.startswith("parameter:"):
        if evidence["evidence_kind"] != "user_decision":
            _fail("user decision evidence required")
        decision = _read(root, evidence["details"].get("decision_path"))
        if (not isinstance(decision, dict) or set(decision) != {"schema", "snapshot_id", "region_id", "claims", "claim_witnesses", "authority", "decision_id"}
                or decision["schema"] != "p3-region-user-decision/1.0" or decision["snapshot_id"] != snapshot_id
                or decision["region_id"] != region_id or not isinstance(decision["claims"], list)
                or any(not isinstance(x, str) for x in decision["claims"]) or len(set(decision["claims"])) != len(decision["claims"])
                or claim not in decision["claims"]
                or not isinstance(decision["claim_witnesses"], dict) or set(decision["claim_witnesses"]) != set(decision["claims"])
                or decision["authority"] != "explicit user reply" or not isinstance(decision["decision_id"], str)
                or not decision["decision_id"].strip()):
            _fail("missing or out-of-scope user decision")
        expected = ({"region_witness": evidence["details"].get("region_witness"), "node_witness": evidence["details"].get("node_witness")}
                    if claim == "design_intent" else {"parameter_witness": evidence["details"].get("parameter_witness")})
        if json.dumps(decision["claim_witnesses"][claim], sort_keys=True, allow_nan=False, separators=(",", ":")) != json.dumps(expected, sort_keys=True, allow_nan=False, separators=(",", ":")):
            _fail("user decision does not bind the proposed design or parameter")
        if evidence["details"]["decision_path"] not in {item["path"] for item in evidence["sources"]}:
            _fail("user decision must itself be a reviewed source")
    if claim == "representation_error":
        bound = evidence["details"].get("absolute_bound")
        if (type(bound) not in (int, float) or not math.isfinite(bound) or bound < 0
                or evidence["details"].get("unit") != "mm" or not evidence["details"].get("basis")):
            _fail("representation error bound missing or invalid")
    return evidence


def _polygon_prism(construction, node, parameters):
    """Validate a bounded native-independent planning representation only."""
    if not isinstance(construction, dict) or construction.get("kind") != "polygon_prism":
        return False
    if node["kind"] != "stock":
        return False
    if set(construction) != {"kind", "vertices", "height_parameter", "material_side", "frame"}:
        _fail("invalid polygon prism fields")
    verts, height = construction["vertices"], construction["height_parameter"]
    if (construction["frame"] != "P1_ABS_XY_Z0"
            or construction["material_side"] != "inside" or not isinstance(verts, list) or len(verts) < 3
            or any(not isinstance(p, list) or len(p) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in p) for p in verts)
            or len({tuple(p) for p in verts}) != len(verts) or node["parameters"] != [height]
            or parameters[height]["dimension"] != "length" or parameters[height]["classification"] == "derived"
            or type(parameters[height]["value"]) not in (int, float) or parameters[height]["value"] <= 0):
        _fail("invalid polygon section or prism height")
    # Binary64 input values are interpreted exactly; no multiplication-based
    # floating-point sign test can underflow and hide a self-intersection.
    verts = [[Fraction(v) for v in point] for point in verts]
    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    def intersects(a, b, c, d):
        def in_box(p, q, r):
            return min(p[0], q[0]) <= r[0] <= max(p[0], q[0]) and min(p[1], q[1]) <= r[1] <= max(p[1], q[1])
        x, y, z, w = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
        return ((x == 0 and in_box(a, b, c)) or (y == 0 and in_box(a, b, d))
                or (z == 0 and in_box(c, d, a)) or (w == 0 and in_box(c, d, b))
                or (x*y < 0 and z*w < 0))
    area2 = sum(verts[i][0]*verts[(i+1) % len(verts)][1] - verts[(i+1) % len(verts)][0]*verts[i][1] for i in range(len(verts)))
    if area2 == 0:
        _fail("degenerate polygon section")
    for i in range(len(verts)):
        for j in range(i+1, len(verts)):
            if j == i+1 or (i == 0 and j == len(verts)-1):
                continue
            if intersects(verts[i], verts[(i+1) % len(verts)], verts[j], verts[(j+1) % len(verts)]):
                _fail("self-intersecting polygon section")
    return True


def _parameter_dimension(node, parameters, graph, current):
    if isinstance(node, ast.Name):
        if node.id not in parameters:
            _fail("unknown formula parameter")
        graph[current].add(node.id)
        return _DIMS[parameters[node.id]["dimension"]]
    if isinstance(node, ast.Constant):
        if type(node.value) not in (int, float) or not math.isfinite(node.value):
            _fail("invalid formula constant")
        return _DIMS["scalar"]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _parameter_dimension(node.operand, parameters, graph, current)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        left = _parameter_dimension(node.left, parameters, graph, current)
        right = _parameter_dimension(node.right, parameters, graph, current)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if left != right:
                _fail("formula dimensions differ")
            return left
        sign = 1 if isinstance(node.op, ast.Mult) else -1
        return tuple(a + sign * b for a, b in zip(left, right))
    _fail("unsupported formula")


def build_design_dag(snapshot, *, repository_root, p1_source, regions, nodes, parameters, capabilities):
    """Validate inputs and compute a planning report; never grant execution.

    Unknown claims are recorded as blockers. Reviewed project attestations are
    trusted planning evidence, not proof of reconstructed native geometry.
    """
    root = Path(repository_root).resolve(strict=True)
    try:
        if json.dumps(snapshot, sort_keys=True, allow_nan=False, separators=(",", ":")) != json.dumps(
                _read(root, p1_source), sort_keys=True, allow_nan=False, separators=(",", ":")):
            _fail("input snapshot differs from the cited P1 source")
    except (TypeError, ValueError, OverflowError) as exc:
        raise DesignDagError("invalid snapshot comparison") from exc
    inventory = normalize_snapshot(snapshot, tolerances={"linear": .001, "angular": .0001})
    if inventory["unit"] != "mm" or snapshot.get("inventory", {}).get("coordinate_system") != "absolute_part_coordinates":
        _fail("only mm absolute part coordinates are supported")
    sid, faces, edges = inventory["snapshot_id"], inventory["faces"], inventory["edges"]
    regions_by_id, nodes_by_id = _unique(regions, "region"), _unique(nodes, "node")
    params = _unique(parameters, "parameter")
    requirements = _unique(capabilities, "capability")
    if not regions_by_id or not nodes_by_id:
        _fail("regions and nodes are required")
    responsible, region_findings, attestations = Counter(), [], {}
    for rid, region in regions_by_id.items():
        if set(region) != {"id", "kind", "responsible_faces", "sources", "directed_edges", "claims"}:
            _fail("invalid region fields")
        if region["kind"] not in _KINDS:
            _fail("unsupported region kind")
        owned = region["responsible_faces"]
        if (not isinstance(owned, list) or not owned or len(set(owned)) != len(owned)
                or any(fid not in faces for fid in owned)):
            _fail("invalid responsible P1 faces")
        responsible.update(owned)
        if not isinstance(region["sources"], list) or not region["sources"]:
            _fail("region sources are required")
        for source in region["sources"]:
            _source(root, source, sid)
        directed = region["directed_edges"]
        if not isinstance(directed, list):
            _fail("directed edges must be a list")
        seen_edges = set()
        for edge in directed:
            if (not isinstance(edge, dict) or set(edge) != {"edge_id", "orientation", "snapshot_id"}
                    or edge["snapshot_id"] != sid or edge["edge_id"] not in edges
                    or type(edge["orientation"]) is not int or edge["orientation"] not in (-1, 1)
                    or edge["edge_id"] in seen_edges
                    or not set(edges[edge["edge_id"]]["face_ids"]) & set(owned)):
                _fail("invalid directed edge or source scope")
            seen_edges.add(edge["edge_id"])
        claims = region["claims"]
        if not isinstance(claims, dict) or set(claims) != set(_CLAIMS):
            _fail("region claims must enumerate all required categories")
        for name in _CLAIMS:
            claim = claims[name]
            if (not isinstance(claim, dict) or set(claim) != {"state", "evidence"}
                    or claim["state"] not in {"unknown", "observed", "attested"} or not isinstance(claim["evidence"], list)):
                _fail("invalid planning claim state")
            if claim["state"] in {"observed", "attested"} and not claim["evidence"]:
                _fail("observation requires cited evidence")
            for source in claim["evidence"]:
                _source(root, source, sid)
            if claim["state"] == "attested":
                if len(claim["evidence"]) != 1: _fail("exactly one reviewed claim record required")
                attestations[(rid, name)] = _attestation(root, claim["evidence"][0], sid, rid, name)
            else:
                region_findings.append({"region_id": rid, "requirement": name, "status": "open"})
        if not directed:
            region_findings.append({"region_id": rid, "requirement": "directed_source_edges", "status": "open"})
    overlaps = sorted(fid for fid, count in responsible.items() if count > 1)
    if overlaps:
        _fail("duplicate responsibility for P1 face")
    missing_faces = sorted(set(faces) - set(responsible))
    graph = {}
    for nid, node in nodes_by_id.items():
        if set(node) != {"id", "kind", "region_id", "depends_on", "parameters", "operation_order", "sources", "construction"}:
            _fail("invalid node fields")
        if node["kind"] not in _KINDS or node["region_id"] not in regions_by_id:
            _fail("unsupported node kind or unknown region")
        deps, used = node["depends_on"], node["parameters"]
        if (not isinstance(deps, list) or len(set(deps)) != len(deps)
                or any(not isinstance(x, str) for x in deps)
                or not isinstance(used, list) or len(set(used)) != len(used)
                or any(x not in params for x in used)):
            _fail("invalid node dependencies or parameters")
        if node["operation_order"] not in {"unknown", "candidate", "fixed"}:
            _fail("unsupported operation order claim")
        if not isinstance(node["sources"], list) or not node["sources"]:
            _fail("node source missing")
        for source in node["sources"]:
            _source(root, source, sid)
        graph[nid] = deps
    order = _topological(graph)
    param_graph = {ident: set() for ident in params}
    for ident, param in params.items():
        if set(param) != {"id", "dimension", "unit", "classification", "value", "expression", "consumers", "confirmation", "confirmation_evidence", "sources"}:
            _fail("invalid parameter fields")
        dim = param["dimension"]
        if dim not in _DIMS or param["unit"] != _UNITS[dim] or param["classification"] not in {"fixed", "independent", "derived"}:
            _fail("invalid parameter dimension, unit or classification")
        if param["confirmation"] not in {"unknown", "observed", "confirmed"}:
            _fail("invalid parameter confirmation")
        if not isinstance(param["sources"], list) or not param["sources"]:
            _fail("parameter source missing")
        for source in param["sources"]:
            _source(root, source, sid)
        consumers = param["consumers"]
        if (not isinstance(consumers, list) or not consumers or len(set(consumers)) != len(consumers)
                or any(c not in nodes_by_id or ident not in nodes_by_id[c]["parameters"] for c in consumers)):
            _fail("parameter consumers are invalid or not reciprocal")
        refs = param["confirmation_evidence"]
        if not isinstance(refs, list): _fail("parameter confirmation evidence must be a list")
        if param["confirmation"] == "confirmed":
            region_ids = {nodes_by_id[c]["region_id"] for c in consumers}
            if len(refs) != 1 or len(region_ids) != 1:
                _fail("confirmed parameter needs one region-bound review chain")
            record = _attestation(root, refs[0], sid, next(iter(region_ids)), "parameter:" + ident)
            if record["details"].get("parameter_witness") != {k: v for k, v in param.items() if k != "confirmation_evidence"}:
                _fail("confirmed parameter differs from reviewed value or consumers")
            if not {s["path"] for s in param["sources"]} <= {s["path"] for s in record["sources"]}:
                _fail("parameter sources are not included in reviewed evidence")
        elif refs:
            _fail("unconfirmed parameter cannot cite confirmation evidence")
        if param["classification"] == "derived":
            if param["value"] is not None or not isinstance(param["expression"], str):
                _fail("derived parameter requires expression only")
            try:
                tree = ast.parse(param["expression"], mode="eval")
            except (SyntaxError, ValueError, RecursionError) as exc:
                raise DesignDagError("invalid parameter expression") from exc
            if _parameter_dimension(tree.body, params, param_graph, ident) != _DIMS[dim]:
                _fail("parameter expression dimension mismatch")
        elif (param["expression"] is not None or type(param["value"]) not in (int, float)
              or not math.isfinite(param["value"])):
            _fail("fixed or independent parameter requires finite value")
    param_order = _topological({k: sorted(v) for k, v in param_graph.items()})
    evaluated = {}
    def evaluate(expr):
        if isinstance(expr, ast.Name): return evaluated[expr.id]
        if isinstance(expr, ast.Constant): return expr.value
        if isinstance(expr, ast.UnaryOp):
            value = evaluate(expr.operand)
            return value if isinstance(expr.op, ast.UAdd) else -value
        a, b = evaluate(expr.left), evaluate(expr.right)
        if isinstance(expr.op, ast.Add): return a + b
        if isinstance(expr.op, ast.Sub): return a - b
        if isinstance(expr.op, ast.Mult): return a * b
        if b == 0: _fail("parameter expression divides by zero")
        return a / b
    try:
        for ident in param_order:
            value = params[ident]["value"] if params[ident]["classification"] != "derived" else evaluate(ast.parse(params[ident]["expression"], mode="eval").body)
            if not math.isfinite(value): _fail("non-finite parameter result")
            evaluated[ident] = value
    except (OverflowError, ZeroDivisionError) as exc:
        raise DesignDagError("invalid numeric parameter expression") from exc
    for nid, node in nodes_by_id.items():
        if any(nid not in params[p]["consumers"] for p in node["parameters"]):
            _fail("node parameter usage is not reciprocal")
    open_p3, deferred = [], []
    for cid, cap in requirements.items():
        if set(cap) != {"id", "stage", "status", "owner", "verification", "source", "region_id", "closure"}:
            _fail("invalid capability fields")
        if (cap["stage"] not in {"P3", "P4", "P5", "P6"} or cap["status"] not in {"open", "closed"}
                or not isinstance(cap["owner"], str) or not cap["owner"].strip()
                or not isinstance(cap["verification"], str) or not cap["verification"].strip()):
            _fail("invalid capability stage, state, owner or verification")
        _source(root, cap["source"], sid)
        if cap["region_id"] not in regions_by_id or not isinstance(cap["closure"], list):
            _fail("invalid capability region or closure evidence")
        if cap["status"] == "open":
            if cap["closure"]: _fail("open capability cannot have closure evidence")
            (open_p3 if cap["stage"] == "P3" else deferred).append(cid)
        else:
            if len(cap["closure"]) != 1: _fail("closed capability needs reviewed evidence")
            evidence = _attestation(root, cap["closure"][0], sid, cap["region_id"], "capability:" + cid)
            if evidence["details"].get("capability_witness") != {k: v for k, v in cap.items() if k != "closure"}:
                _fail("capability closure differs from reviewed record")
            if cap["source"]["path"] not in {s["path"] for s in evidence["sources"]}:
                _fail("capability source is not included in reviewed evidence")
    unsupported_nodes = []
    for nid, node in nodes_by_id.items():
        if node["construction"] != {"kind": "unresolved"} and (not isinstance(node["construction"], dict) or node["construction"].get("kind") != "polygon_prism"):
            _fail("unsupported construction schema")
        if node["construction"].get("kind") == "polygon_prism" and node["kind"] != regions_by_id[node["region_id"]]["kind"]:
            _fail("construction and region operation differ")
        if not _polygon_prism(node["construction"], node, params):
            unsupported_nodes.append(nid)
        else:
            region = regions_by_id[node["region_id"]]
            directed_ids = [item["edge_id"] for item in region["directed_edges"]]
            incident = {face for eid in directed_ids for face in edges[eid]["face_ids"]}
            if len(directed_ids) < len(node["construction"]["vertices"]) or not set(region["responsible_faces"]) <= incident:
                _fail("polygon boundary lacks source-scoped directed edge coverage")
    for (rid, name), evidence in attestations.items():
        witness = [{k: deepcopy(n[k]) for k in ("id", "kind", "region_id", "depends_on", "parameters", "operation_order", "construction", "sources")}
                   for n in nodes if n["region_id"] == rid]
        region_witness = {k: deepcopy(v) for k, v in regions_by_id[rid].items() if k != "claims"}
        if (not witness or evidence["details"].get("node_witness") != witness
                or evidence["details"].get("region_witness") != region_witness):
            _fail("claim record does not bind the reviewed construction and order")
        required = {s["path"] for s in regions_by_id[rid]["sources"]}
        required.update(s["path"] for node in nodes if node["region_id"] == rid for s in node["sources"])
        if not required <= {s["path"] for s in evidence["sources"]}:
            _fail("review does not cover every region and construction source")
    blockers = []
    if missing_faces: blockers.append("unassigned_source_faces")
    if region_findings: blockers.append("unresolved_region_requirements")
    if any(p["confirmation"] != "confirmed" for p in params.values()): blockers.append("unconfirmed_parameters")
    if any(not any(n["region_id"] == rid and n["parameters"] for n in nodes) for rid in regions_by_id):
        blockers.append("region_parameters_missing")
    if any(n["operation_order"] != "fixed" for n in nodes_by_id.values()): blockers.append("construction_order_unknown")
    if open_p3: blockers.append("open_p3_capabilities")
    if unsupported_nodes: blockers.append("unsupported_construction")
    if len(nodes_by_id) != 1 or next(iter(nodes_by_id.values()))["kind"] != "stock":
        blockers.append("unsupported_multi_operation_or_nonstock_plan")
    if set(n["region_id"] for n in nodes) != set(regions_by_id): blockers.append("region_without_node")
    design_faces = {face for rid, region in regions_by_id.items()
                    if all((rid, claim) in attestations for claim in _CLAIMS)
                    and any(n["region_id"] == rid for n in nodes)
                    and region["directed_edges"]
                    and all(n["id"] not in unsupported_nodes and n["operation_order"] == "fixed" for n in nodes if n["region_id"] == rid)
                    and all(params[p]["confirmation"] == "confirmed" for n in nodes if n["region_id"] == rid for p in n["parameters"])
                    for face in region["responsible_faces"]}
    return {"schema": "p3-regional-design-dag/0.1", "p1_snapshot_id": sid, "p1_source": p1_source, "unit": "mm",
            "frame": "absolute_part_coordinates", "status": "planning_only",
            "regions": deepcopy(regions), "nodes": deepcopy(nodes), "node_order": order,
            "parameters": deepcopy(parameters), "capabilities": deepcopy(capabilities),
            "coverage": {"p1_total_faces": len(faces), "responsibility_assigned": len(responsible),
                         "responsibility_unassigned_faces": missing_faces, "responsibility_duplicate_faces": overlaps,
                         "reviewed_design_face_count": len(design_faces),
                         "verified_geometric_explanation_count": 0,
                         "geometry_note": "Reviewed planning is not full native geometry proof; responsibility is not explanation."},
            "region_findings": region_findings, "open_p3_capabilities": open_p3,
            "deferred_backend_capabilities": deferred, "p3_blockers": blockers,
            "p3_ready": not blockers, "execution_approved": False,
            "trust_boundary": "Review and user-decision files are trusted project records, not authenticated signatures or native geometry proof.",
            "limitation": "The ready domain is one reviewed stock polygon prism; multi-operation and subtractive plans remain blocked. P3 readiness is planning only, not P6 geometry proof."}
