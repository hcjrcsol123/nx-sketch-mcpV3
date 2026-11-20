"""Restricted, session-scoped P2 block orchestration over an injected MCP transport.

The transport returns the structuredContent object of each MCP tool response.
This module does not take ownership, resolve native constraint identities, or
claim that the actual reference part has been reconstructed.
"""
import ast
import math
import re
import time
import uuid

from .ir import Plan


class ExecutionStopped(RuntimeError):
    """Stop the chain; a caller must investigate before any further writes."""


def _values(parameters):
    items = {p["id"]: p for p in parameters}
    cache = {}
    def resolve(name):
        if name in cache:
            return cache[name]
        p = items[name]
        def evaluate(node):
            if isinstance(node, ast.Name):
                return resolve(node.id)
            if isinstance(node, ast.Constant):
                return float(node.value)
            if isinstance(node, ast.UnaryOp):
                value = evaluate(node.operand)
                return -value if isinstance(node.op, ast.USub) else value
            a, b = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            return a / b
        value = float(p["value"]) if p["value"] is not None else evaluate(ast.parse(p["expression"], mode="eval").body)
        if not math.isfinite(value):
            raise ValueError("non-finite parameter")
        cache[name] = value
        return value
    return {name: resolve(name) for name in items}


class Executor:
    def __init__(self, transport, ownership_id, binding_epoch, revision_id, id_factory=None, max_polls=600, poll_interval=0.25, timeout_seconds=120, clock=None, sleeper=None):
        if not isinstance(ownership_id, str) or not ownership_id or isinstance(binding_epoch, bool) or not isinstance(binding_epoch, int) or binding_epoch < 1 or not isinstance(revision_id, str) or not revision_id:
            raise ValueError("current ownership, epoch and revision are required")
        if not isinstance(max_polls, int) or isinstance(max_polls, bool) or max_polls < 1:
            raise ValueError("max_polls must be positive")
        if isinstance(poll_interval, bool) or not isinstance(poll_interval, (int, float)) or not math.isfinite(poll_interval) or not 0 <= poll_interval <= 5:
            raise ValueError("poll_interval must be between 0 and 5 seconds")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.transport = transport
        self.owner = ownership_id
        self.epoch = binding_epoch
        self.revision = revision_id
        self.id_factory = id_factory or (lambda: "v3-" + uuid.uuid4().hex)
        self.max_polls = max_polls
        self.poll_interval = poll_interval
        self.timeout_seconds = timeout_seconds
        self.clock = clock or time.monotonic
        self.sleeper = sleeper or time.sleep
        self.stopped = False
        self._used_ids = set()
        self._block = None
        self._block_dims = None
        self._bound = False
        self._constraints = None
        self.last_verification = None

    def _id(self):
        value = self.id_factory()
        if not isinstance(value, str) or not value or value in self._used_ids:
            raise ExecutionStopped("invalid or reused operation id")
        self._used_ids.add(value)
        return value

    def _call(self, tool, args):
        if self.stopped:
            raise ExecutionStopped("executor is stopped")
        try:
            result = self.transport.call(tool, args)
            if not isinstance(result, dict) or result.get("ok") is not True or result.get("writes_halted") is not False:
                raise ExecutionStopped("invalid result or bridge writes halted")
            return result
        except Exception as exc:
            self.stopped = True
            raise ExecutionStopped(f"{tool}: stopped; do not replay uncertain operations") from exc

    def _operation(self, tool, args):
        operation_id = args["operation_id"]
        result = self._call(tool, args)
        deadline = self.clock() + self.timeout_seconds
        for _ in range(self.max_polls + 1):
            if result.get("operation_id") != operation_id:
                raise ExecutionStopped("operation identity mismatch")
            state = result.get("state")
            if state == "SUCCEEDED":
                payload = result.get("result")
                if not isinstance(payload, dict):
                    raise ExecutionStopped("missing operation result")
                return payload
            if state not in ("QUEUED", "RUNNING"):
                raise ExecutionStopped(f"operation did not succeed: {state!r}")
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise ExecutionStopped("operation deadline exceeded; outcome requires investigation")
            if self.poll_interval:
                self.sleeper(min(self.poll_interval, remaining))
            if self.clock() >= deadline:
                raise ExecutionStopped("operation deadline exceeded; outcome requires investigation")
            result = self._call("nx_get_operation", {"operation_id": operation_id})
        raise ExecutionStopped("operation did not complete; outcome requires investigation")

    def _transaction(self, tool, fields):
        common = {"ownership_id": self.owner, "binding_epoch": self.epoch}
        prepared = self._operation(tool, {**common, "operation_id": self._id(), "revision_id": self.revision, **fields})
        plan = prepared.get("plan")
        if not isinstance(plan, dict) or not isinstance(plan.get("plan_id"), str) or not plan["plan_id"]:
            raise ExecutionStopped("prepare did not return a plan")
        execute_id = self._id()
        executed = self._operation("nx_execute_plan", {**common, "operation_id": execute_id, "plan_id": plan["plan_id"]})
        if executed.get("mutation_state") != "APPLIED" or executed.get("plan_id") != plan["plan_id"]:
            raise ExecutionStopped("execute did not prove an applied plan")
        verified = self._operation("nx_verify_part", {**common, "operation_id": self._id(), "execute_operation_id": execute_id})
        if verified.get("verified") is not True or verified.get("execute_operation_id") != execute_id or verified.get("plan_id") != plan["plan_id"]:
            raise ExecutionStopped("fresh verification failed or is not linked to execution")
        revision = verified.get("revision_id")
        if not isinstance(revision, str) or not revision:
            raise ExecutionStopped("fresh revision missing")
        self.revision = revision
        self.last_verification = verified
        return executed

    def create_block(self, plan):
        try:
            if self.stopped or self._block is not None:
                raise ExecutionStopped("executor is stopped or already created a block")
            doc = Plan.from_dict(plan.to_dict() if isinstance(plan, Plan) else plan).to_dict()
            frame = {"origin": [0, 0, 0], "x_axis": [1, 0, 0], "y_axis": [0, 1, 0]}
            if doc["reference"]["length_unit"] != "mm" or doc["reference"]["rigid_transform"] != frame or doc["open_items"] or doc["constraints"] or any(not x["confirmed"] for x in doc["regions"] + doc["operations"]):
                raise ExecutionStopped("block plan is outside the P2 supported domain")
            ops = doc["operations"]
            if (not set(doc["capability_requirements"]).issubset({"rectangle_driving_dimensions", "extrude_create"}) or
                    len(doc["regions"]) != 1 or any(op["region_id"] != doc["regions"][0]["id"] for op in ops)):
                raise ExecutionStopped("unsupported capability or uncovered region")
            if len(ops) != 3 or [o["kind"] for o in ops] != ["datum_plane", "sketch_rectangle", "extrude"] or ops[0]["data"] != frame:
                raise ExecutionStopped("only the fixed XY block plan is supported")
            p = {item["id"]: item for item in doc["parameters"]}
            if (set(p) != {"x", "y", "width", "height", "depth"} or
                    ops[1]["parameters"] != {"x": "x", "y": "y", "width": "width", "height": "height"} or
                    ops[2]["parameters"] != {"distance": "depth"} or
                    any(p[k]["value"] is None for k in ("x", "y", "width", "depth")) or
                    p["height"]["expression"] != "width * 2 / 3"):
                raise ExecutionStopped("only the confirmed P2 width-to-height relationship is supported")
            params = _values(doc["parameters"])
            sketch, extrude = ops[1:]
            dims = {role: params[key] for role, key in sketch["parameters"].items()}
            depth = params[extrude["parameters"]["distance"]]
            if any(v <= 0 for v in (*dims.values(), depth)):
                raise ExecutionStopped("block dimensions and coordinates must be positive")
            datum = self._transaction("nx_prepare_datum_plane", {"origin_mm": frame["origin"], "normal": [0, 0, 1], "x_axis": frame["x_axis"]})
            datum_id = datum.get("datum_plane_id")
            if not isinstance(datum_id, str) or not datum_id:
                raise ExecutionStopped("created datum identity missing")
            created = self._transaction("nx_prepare_sketch", {"support_datum_plane_id": datum_id, "x_axis": [1, 0, 0], "constraint_mode": "legacy_driving", "geometries": [{"id": sketch["id"], "type": "rectangle", "corner_mm": [dims["x"], dims["y"]], "width_mm": dims["width"], "height_mm": dims["height"]}]})
            sketch_id = created.get("sketch_id")
            if not isinstance(sketch_id, str) or not sketch_id:
                raise ExecutionStopped("created sketch identity missing")
            body = self._transaction("nx_prepare_extrude", {"sketch_id": sketch_id, "mode": "create", "direction": "positive", "extent": "finite", "depth_mm": depth})
            body_ids = body.get("body_ids")
            if not isinstance(body_ids, list) or len(body_ids) != 1 or not isinstance(body_ids[0], str) or not body_ids[0] or not isinstance(body.get("feature_id"), str) or not body["feature_id"]:
                raise ExecutionStopped("created body or extrude identity ambiguous")
            self._block = {"sketch_id": sketch_id, "extrude_feature_id": body["feature_id"], "body_id": body_ids[0]}
            self._block_dims = dims
            constraint_ids = self.resolve_constraints()
            return {**self._block, "constraint_ids": constraint_ids, "revision_id": self.revision, "binding_required": True}
        except Exception as exc:
            self.stopped = True
            if isinstance(exc, ExecutionStopped): raise
            raise ExecutionStopped("invalid block plan or transport failure") from exc

    def resolve_constraints(self):
        """Read current sketch; match unique native geometry associations by role."""
        try:
            if self.stopped or self._block is None or self._bound:
                raise ExecutionStopped("unbound live block required")
            result = self.transport.call("nx_inspect_sketch", {"ownership_id": self.owner, "binding_epoch": self.epoch, "sketch_id": self._block["sketch_id"]})
            if (not isinstance(result, dict) or result.get("ok") is not True or result.get("ownership_state") != "AI_OWNED" or
                    result.get("ownership_id") != self.owner or result.get("binding_epoch") != self.epoch or
                    result.get("revision_id") != self.revision or result.get("semantic_changed_since_previous_read") is True):
                raise ExecutionStopped("sketch identity or revision changed")
            sketch = result.get("sketch")
            if not isinstance(sketch, dict) or sketch.get("journal_id") != self._block["sketch_id"]:
                raise ExecutionStopped("sketch result identity mismatch")
            geometry, constraints = sketch.get("geometry"), sketch.get("constraints")
            if not isinstance(geometry, list) or not isinstance(constraints, list):
                raise ExecutionStopped("missing sketch geometry or constraints")
            lines = [g for g in geometry if isinstance(g, dict) and g.get("kind") == "LINE"]
            if len(lines) != 4 or any(not isinstance(g.get("journal_id"), str) or not g["journal_id"] for g in lines) or len({g["journal_id"] for g in lines}) != 4:
                raise ExecutionStopped("expected exactly four unique rectangle lines")
            dims = self._block_dims
            x, y, w, h = dims["x"], dims["y"], dims["width"], dims["height"]
            def at(actual, expected):
                return isinstance(actual, list) and len(actual) == 3 and all(math.isfinite(float(a)) and abs(float(a)-b) <= 1e-7 for a, b in zip(actual, expected))
            def line(start, end):
                matches = [g for g in lines if at(g.get("start"), start) and at(g.get("end"), end)]
                if len(matches) != 1:
                    raise ExecutionStopped("rectangle line is missing or ambiguous")
                return matches[0]["journal_id"]
            bottom = line([x, y, 0], [x+w, y, 0])
            left = line([x, y+h, 0], [x, y, 0])
            line([x+w, y, 0], [x+w, y+h, 0])
            line([x+w, y+h, 0], [x, y+h, 0])
            def choose(kind, required, coordinate=False):
                found = []
                for c in constraints:
                    if not isinstance(c, dict) or c.get("class") != "DIMENSIONAL" or c.get("is_driving") is not True or c.get("constraint_type") != kind:
                        continue
                    refs = c.get("geometry_refs")
                    if not isinstance(refs, list) or len(refs) != 2 or not all(isinstance(r, str) for r in refs):
                        continue
                    if coordinate:
                        valid = required in refs and sum(r.endswith(":None") and r != required for r in refs) == 1
                    else:
                        valid = sorted(refs) == sorted(required)
                    if valid and isinstance(c.get("journal_id"), str) and c["journal_id"]:
                        found.append(c["journal_id"])
                if len(found) != 1:
                    raise ExecutionStopped("constraint mapping is missing or ambiguous")
                return found[0]
            mapping = {
                "x": choose("HorizontalDim", bottom + ":StartPoint", True),
                "y": choose("VerticalDim", bottom + ":StartPoint", True),
                "width": choose("HorizontalDim", [bottom + ":StartPoint", bottom + ":EndPoint"]),
                "height": choose("VerticalDim", [left + ":StartPoint", left + ":EndPoint"]),
            }
            if len(set(mapping.values())) != 4:
                raise ExecutionStopped("constraint mapping is not unique")
            return mapping
        except Exception as exc:
            self.stopped = True
            if isinstance(exc, ExecutionStopped): raise
            raise ExecutionStopped("constraint inspection failed") from exc

    def resolve_reopened_constraints(self, sketch_id, extrude_feature_id, body_id, dimensions):
        """Attach freshly reidentified session objects for read-only preview.

        The caller must locate the identities from this session's part inventory;
        the native prepare independently checks all object relationships.
        """
        try:
            if self.stopped or self._block is not None:
                raise ExecutionStopped("fresh executor required")
            if any(not isinstance(v, str) or not v for v in (sketch_id, extrude_feature_id, body_id)):
                raise ExecutionStopped("current object identities required")
            if not isinstance(dimensions, dict) or set(dimensions) != {"x", "y", "width", "height"}:
                raise ExecutionStopped("current block dimensions required")
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in dimensions.values()):
                raise ExecutionStopped("positive finite block dimensions required")
            self._block = {"sketch_id": sketch_id, "extrude_feature_id": extrude_feature_id, "body_id": body_id}
            self._block_dims = dict(dimensions)
            return self.resolve_constraints()
        except Exception as exc:
            self.stopped = True
            if isinstance(exc, ExecutionStopped): raise
            raise ExecutionStopped("reopened block mapping failed") from exc

    def preview_block_binding(self, constraint_ids, value):
        """Prepare an edit and return its public view; never execute the plan."""
        try:
            if self.stopped or self._block is None or self._bound:
                raise ExecutionStopped("unbound current block required")
            if not isinstance(constraint_ids, dict) or set(constraint_ids) != {"x", "y", "width", "height"} or any(not isinstance(v, str) or not v for v in constraint_ids.values()) or len(set(constraint_ids.values())) != 4:
                raise ExecutionStopped("four unique constraint IDs required")
            if not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) or not math.isfinite(float(value)) or float(value) <= 0:
                raise ExecutionStopped("positive finite decimal required")
            fields = {**self._block, "action": "edit_width", "value": value}
            for role in ("x", "y", "width", "height"):
                fields[role + "_constraint_id"] = constraint_ids[role]
            result = self._operation("nx_prepare_block_binding", {"ownership_id": self.owner, "binding_epoch": self.epoch, "revision_id": self.revision, "operation_id": self._id(), **fields})
            plan = result.get("plan")
            if not isinstance(plan, dict) or not isinstance(plan.get("before"), dict) or not isinstance(plan.get("plan_id"), str) or not plan["plan_id"]:
                raise ExecutionStopped("native binding preview missing")
            return plan
        except Exception as exc:
            self.stopped = True
            if isinstance(exc, ExecutionStopped): raise
            raise ExecutionStopped("binding preview failed") from exc

    def bind_or_edit(self, constraint_ids, action, value=None):
        """Bind or edit this session's block; constraint IDs must be explicit.

        The native adapter independently revalidates each ID and consumer.
        """
        try:
            if self.stopped or self._block is None:
                raise ExecutionStopped("a live created block is required")
            if not isinstance(constraint_ids, dict) or set(constraint_ids) != {"x", "y", "width", "height"}:
                raise ExecutionStopped("four explicit constraint IDs are required")
            ids = list(constraint_ids.values())
            if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != 4:
                raise ExecutionStopped("constraint IDs must be nonempty and distinct")
            if action == "bind":
                if self._bound or value is not None:
                    raise ExecutionStopped("bind is allowed once without a value")
            elif action in ("edit_width", "edit_x"):
                if not self._bound or constraint_ids != self._constraints or not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) or not math.isfinite(float(value)) or float(value) <= 0:
                    raise ExecutionStopped("edit requires a positive finite decimal after binding")
            else:
                raise ExecutionStopped("unsupported binding action")
            fields = {**self._block, "action": action}
            for role in ("x", "y", "width", "height"):
                fields[role + "_constraint_id"] = constraint_ids[role]
            if value is not None:
                fields["value"] = value
            result = self._transaction("nx_prepare_block_binding", fields)
            if action == "bind":
                self._bound = True
                self._constraints = dict(constraint_ids)
            return {"revision_id": self.revision, "action": action, "result": result}
        except Exception as exc:
            self.stopped = True
            if isinstance(exc, ExecutionStopped): raise
            raise ExecutionStopped("binding failed; do not replay") from exc
