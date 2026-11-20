"""UG11 native revolve mapping for P4 associative-preview steps.

Generation/validation is offline. Native execution and permitted-edit evidence are
separate gates. Lengths are mm, limits degrees, and coordinates are absolute.
"""
import ast
from copy import deepcopy
import math
from pathlib import Path
import re


class UnsupportedRevolve(ValueError):
    """The requested step is outside the explicit UG11 revolve mapping."""


_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_FIELDS = {"id", "kind", "frame", "edges", "axis_point", "axis_direction",
           "start_degrees", "end_degrees", "axis_points_expressions",
           "start_formula", "end_formula"}


def source():
    """Return the standalone NX11 C# helper, requiring NXOpen and NXOpen.UF."""
    return Path(__file__).with_name("revolve_template.cs").read_text(encoding="utf-8")


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise UnsupportedRevolve(label + " must be finite")
    return float(value)


def _vector(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise UnsupportedRevolve(label + " must contain three finite numbers")
    return [_number(v, label) for v in value]


def _unit(value, label):
    v = _vector(value, label)
    magnitude = math.hypot(*v)
    if not math.isfinite(magnitude) or magnitude <= 0:
        raise UnsupportedRevolve(label + " must be nonzero")
    return [x / magnitude for x in v]


def _formula(value, label):
    if not isinstance(value, str) or not value or len(value) > 512:
        raise UnsupportedRevolve(label + " must be a bounded expression")
    try:
        tree = ast.parse(value.replace("^", "**"), mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise UnsupportedRevolve(label + " is invalid") from exc
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult,
               ast.Div, ast.Pow, ast.UAdd, ast.USub, ast.Name, ast.Load, ast.Constant)
    for n in ast.walk(tree):
        if not isinstance(n, allowed):
            raise UnsupportedRevolve(label + " uses unsupported expression syntax")
        if isinstance(n, ast.Name) and not _NAME.fullmatch(n.id):
            raise UnsupportedRevolve(label + " has an invalid expression name")
        if isinstance(n, ast.Constant):
            _number(n.value, label)
    return value


def validate_step(step):
    """Validate a P4 revolve step, retaining all fields for the integrator.

    Curve geometry/closure and expression existence are owned by sketch and
    expression consumers; no claim that generated code ran or propagated edits.
    The caller must verify those consumers before making a journal executable.
    """
    if not isinstance(step, dict) or step.get("kind") != "revolve":
        raise UnsupportedRevolve("expected a revolve step")
    if set(step) - _FIELDS:
        raise UnsupportedRevolve("unsupported revolve fields: " + ", ".join(sorted(set(step) - _FIELDS)))
    if not isinstance(step.get("id"), str) or not step["id"]:
        raise UnsupportedRevolve("missing step identity")
    frame = step.get("frame")
    if not isinstance(frame, dict) or set(frame) != {"origin", "x_axis", "y_axis"}:
        raise UnsupportedRevolve("expected explicit origin and frame axes")
    origin = _vector(frame["origin"], "frame origin")
    x = _unit(frame["x_axis"], "frame x axis")
    y = _unit(frame["y_axis"], "frame y axis")
    if abs(sum(a*b for a, b in zip(x, y))) > 1e-10:
        raise UnsupportedRevolve("frame axes are not orthogonal")
    normal = [x[1]*y[2]-x[2]*y[1], x[2]*y[0]-x[0]*y[2], x[0]*y[1]-x[1]*y[0]]
    axis = _unit(step.get("axis_direction"), "axis direction")
    point = _vector(step.get("axis_point"), "axis point")
    if abs(sum(a*b for a,b in zip(axis, normal))) > 1e-9 or abs(sum((a-b)*c for a,b,c in zip(point, origin, normal))) > 1e-7:
        raise UnsupportedRevolve("axis must lie in the profile plane")
    start = _number(step.get("start_degrees"), "start angle")
    end = _number(step.get("end_degrees"), "end angle")
    if start < -360 or end > 360 or not 0 < end-start <= 360:
        raise UnsupportedRevolve("expected a positive sweep of at most 360 degrees")
    if not isinstance(step.get("edges"), list) or not step["edges"]:
        raise UnsupportedRevolve("profile edges are required")
    if "axis_points_expressions" in step:
        rows = step["axis_points_expressions"]
        if not isinstance(rows, list) or len(rows) != 2 or any(not isinstance(r, list) or len(r) != 3 for r in rows):
            raise UnsupportedRevolve("axis requires two three-coordinate expression points")
        if any(not isinstance(name, str) or not _NAME.fullmatch(name) for row in rows for name in row):
            raise UnsupportedRevolve("axis coordinates must reference named expressions")
    for key in ("start_formula", "end_formula"):
        if key in step:
            _formula(step[key], key)
    return deepcopy(step)
