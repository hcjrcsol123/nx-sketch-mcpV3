"""V3 IR 1.0: validated, lossless JSON plans for the P2 block smoke test.

Values are expressed in the plan's length unit and radians for angles. Formula
numeric literals are dimensionless; unitful constants are separate parameters.
Semantic geometry IDs are not NX tags or journal identifiers. This contract
does not assert coverage, execution readiness, or native feature support.
"""

import ast
import copy
import json
import math
import re


class IRValidationError(ValueError):
    """The input cannot be represented by this version of the IR."""


_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DIMS = {"scalar": (0, 0), "length": (1, 0), "angle": (0, 1)}


def _fail(message):
    raise IRValidationError(message)


def _object(value, fields, where):
    if not isinstance(value, dict) or set(value) != set(fields):
        _fail(f"{where}: expected fields {', '.join(fields)}")
    return value


def _id(value, where):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        _fail(f"{where}: expected logical identifier")
    return value


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        _fail(f"{where}: expected nonempty text")


def _number(value, where):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        _fail(f"{where}: expected finite number")


def _array(value, where):
    if not isinstance(value, list):
        _fail(f"{where}: expected array")
    return value


def _boolean(value, where):
    if not isinstance(value, bool):
        _fail(f"{where}: expected boolean")


def _unique(items, where):
    result = {}
    for item in _array(items, where):
        if not isinstance(item, dict):
            _fail(f"{where}: expected objects")
        ident = _id(item.get("id"), where)
        if ident in result:
            _fail(f"{where}: duplicate id {ident}")
        result[ident] = item
    return result


def _sources(value, where):
    for source in _array(value, where):
        _object(source, ("logical_id", "parent_feature_id", "geometry_kind"), where)
        _id(source["logical_id"], where)
        if source["parent_feature_id"] is not None:
            _id(source["parent_feature_id"], where)
        _text(source["geometry_kind"], where)


def _vector(value, where):
    if not isinstance(value, list) or len(value) != 3:
        _fail(f"{where}: expected 3-vector")
    for n in value:
        _number(n, where)


def _frame(origin, x, y, where):
    for v in (origin, x, y):
        _vector(v, where)
    dot = sum(a * b for a, b in zip(x, y))
    if abs(sum(a*a for a in x) - 1) > 1e-8 or abs(sum(a*a for a in y) - 1) > 1e-8 or abs(dot) > 1e-8:
        _fail(f"{where}: axes must be orthonormal")


def _dag(graph, where):
    state = {}
    def visit(node):
        if state.get(node) == 1:
            _fail(f"{where}: cyclic dependency at {node}")
        if state.get(node) == 2:
            return
        state[node] = 1
        for dependency in graph[node]:
            if dependency not in graph:
                _fail(f"{where}: unknown dependency {dependency}")
            visit(dependency)
        state[node] = 2
    for node in graph:
        visit(node)


def _validate(doc):
    _object(doc, ("schema_version", "reference", "parameters", "regions", "operations", "constraints", "capability_requirements", "open_items"), "plan")
    if doc["schema_version"] != "1.0":
        _fail("unsupported schema_version")
    ref = _object(doc["reference"], ("snapshot_id", "path", "version", "selected_body", "length_unit", "rigid_transform"), "reference")
    for key in ("snapshot_id", "path", "version"):
        _text(ref[key], "reference." + key)
    _id(ref["selected_body"], "reference.selected_body")
    if ref["length_unit"] not in ("mm", "m", "inch"):
        _fail("reference.length_unit: unsupported unit")
    frame = _object(ref["rigid_transform"], ("origin", "x_axis", "y_axis"), "rigid_transform")
    _frame(frame["origin"], frame["x_axis"], frame["y_axis"], "rigid_transform")
    params = _unique(doc["parameters"], "parameters")
    expressions = {}
    graph = {}
    for ident, param in params.items():
        _object(param, ("id", "dimension", "value", "expression"), f"parameter {ident}")
        if param["dimension"] not in _DIMS:
            _fail(f"parameter {ident}: unknown dimension")
        if (param["value"] is None) == (param["expression"] is None):
            _fail(f"parameter {ident}: require exactly one value or expression")
        graph[ident] = []
        if param["value"] is not None:
            _number(param["value"], ident)
        else:
            _text(param["expression"], ident)
            try:
                tree = ast.parse(param["expression"], mode="eval")
            except (SyntaxError, ValueError, RecursionError) as exc:
                raise IRValidationError(f"parameter {ident}: invalid expression") from exc
            expressions[ident] = tree.body
            graph[ident] = [node.id for node in ast.walk(tree) if isinstance(node, ast.Name)]
    _dag(graph, "parameter expressions")
    def dimension(node):
        if isinstance(node, ast.Name):
            return _DIMS[params[node.id]["dimension"]]
        if isinstance(node, ast.Constant):
            _number(node.value, "expression literal")
            return _DIMS["scalar"]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return dimension(node.operand)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = dimension(node.left), dimension(node.right)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                if left != right:
                    _fail("expression: incompatible dimensions")
                return left
            sign = 1 if isinstance(node.op, ast.Mult) else -1
            return tuple(a + sign*b for a, b in zip(left, right))
        _fail("expression: unsupported syntax")
    for ident, expr in expressions.items():
        if dimension(expr) != _DIMS[params[ident]["dimension"]]:
            _fail(f"parameter {ident}: expression dimension mismatch")
    regions = _unique(doc["regions"], "regions")
    for ident, region in regions.items():
        _object(region, ("id", "source_geometry", "confirmed"), f"region {ident}")
        _sources(region["source_geometry"], ident)
        _boolean(region["confirmed"], ident)
    ops = _unique(doc["operations"], "operations")
    graph = {}
    for ident, op in ops.items():
        _object(op, ("id", "kind", "depends_on", "region_id", "parameters", "data", "source_geometry", "confirmed"), f"operation {ident}")
        if op["region_id"] not in regions:
            _fail(f"operation {ident}: unknown region")
        _sources(op["source_geometry"], ident)
        _boolean(op["confirmed"], ident)
        deps = _array(op["depends_on"], ident)
        for dep in deps:
            _id(dep, ident)
        if len(deps) != len(set(deps)):
            _fail(f"operation {ident}: duplicate dependency")
        graph[ident] = deps
        kind = op["kind"]
        if kind == "datum_plane":
            roles = ()
            data = _object(op["data"], ("origin", "x_axis", "y_axis"), ident)
            _frame(data["origin"], data["x_axis"], data["y_axis"], ident)
        elif kind == "sketch_rectangle":
            roles = ("x", "y", "width", "height")
            data = _object(op["data"], ("datum_id",), ident)
            if data["datum_id"] not in ops or ops[data["datum_id"]].get("kind") != "datum_plane" or data["datum_id"] not in deps:
                _fail(f"operation {ident}: datum must be a dependency")
        elif kind == "extrude":
            roles = ("distance",)
            data = _object(op["data"], ("sketch_id", "boolean"), ident)
            if data["sketch_id"] not in ops or ops[data["sketch_id"]].get("kind") != "sketch_rectangle" or data["sketch_id"] not in deps:
                _fail(f"operation {ident}: sketch must be a dependency")
            if data["boolean"] != "create":
                _fail(f"operation {ident}: unsupported boolean")
        else:
            _fail(f"operation {ident}: unknown kind {kind!r}")
        _object(op["parameters"], roles, ident)
        for param_id in op["parameters"].values():
            if param_id not in params or params[param_id]["dimension"] != "length":
                _fail(f"operation {ident}: expected length parameter")
    _dag(graph, "operations")
    constraints = _unique(doc["constraints"], "constraints")
    for ident, constraint in constraints.items():
        _object(constraint, ("id", "kind", "parameters", "source_geometry", "confirmed"), ident)
        if constraint["kind"] != "equal":
            _fail(f"constraint {ident}: unknown kind")
        ids = _array(constraint["parameters"], ident)
        if len(ids) < 2 or any(i not in params for i in ids) or len({params[i]["dimension"] for i in ids}) != 1:
            _fail(f"constraint {ident}: expected matching parameter dimensions")
        _sources(constraint["source_geometry"], ident)
        _boolean(constraint["confirmed"], ident)
    for field in ("capability_requirements", "open_items"):
        for item in _array(doc[field], field):
            _text(item, field)


class Plan:
    """Immutable-by-interface plan; serialization always returns a copy."""
    def __init__(self, data):
        data = copy.deepcopy(data)
        try:
            _validate(data)
        except (TypeError, RecursionError, OverflowError) as exc:
            raise IRValidationError("invalid plan value") from exc
        self._data = data

    @classmethod
    def from_dict(cls, data):
        return cls(data)

    @classmethod
    def from_json(cls, value):
        def pairs(items):
            result = {}
            for key, val in items:
                if key in result:
                    _fail(f"duplicate JSON key {key}")
                result[key] = val
            return result
        try:
            return cls(json.loads(value, object_pairs_hook=pairs, parse_constant=lambda x: _fail(f"invalid JSON constant {x}")))
        except (json.JSONDecodeError, TypeError) as exc:
            raise IRValidationError("invalid JSON") from exc

    def to_dict(self):
        return copy.deepcopy(self._data)

    def to_json(self):
        return json.dumps(self._data, ensure_ascii=False, allow_nan=False, indent=2)
