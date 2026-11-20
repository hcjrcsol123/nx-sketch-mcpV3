"""UG11 finite extrude and bounded Boolean implementation for P4 composition.

Generated C# is a candidate until the NX11 session has validated native behavior.
The caller owns section generation, expression lookup, transactions, body liveness,
model updates and failure handling. All lengths are millimetres.
"""
import math
from pathlib import Path


class UnsupportedSolidStep(ValueError):
    """The step cannot be represented by these bounded native operations."""


def source():
    """Return the complete NX11 C# helper source; this never starts NX."""
    return Path(__file__).with_name("ExtrudeSolids.cs").read_text(encoding="utf-8")


def _fail(message):
    raise UnsupportedSolidStep(message)


def _ident(value, label):
    if not isinstance(value, str) or not value or not value.strip() or value != value.strip():
        _fail(label + " must be a nonempty identifier")


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(label + " must be a finite number")
    try:
        if not math.isfinite(value):
            _fail(label + " must be a finite number")
    except OverflowError:
        _fail(label + " must be a finite number")


def _vector(value, label, nonzero=False):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        _fail(label + " must have three components")
    for v in value:
        _number(v, label)
    if nonzero and not any(value):
        _fail(label + " must be nonzero")


def validate_step(step):
    """Reject unsupported fields or malformed local inputs.

    This does not resolve expression names, validate profile geometry, guarantee
    live body identity, or authorize/execute a mutation; the caller must do so.
    Returns the input step unchanged after validation.
    """
    if not isinstance(step, dict):
        _fail("step must be an object")
    kind = step.get("kind")
    _ident(step.get("id"), "id")
    if kind == "extrude":
        required = {"id", "kind", "frame", "edges", "direction", "start", "end"}
        allowed = required | {"start_formula", "end_formula"}
        if not required <= step.keys() or step.keys() - allowed:
            _fail("unsupported or missing extrude fields")
        frame = step["frame"]
        if not isinstance(frame, dict) or set(frame) != {"origin", "x_axis", "y_axis"}:
            _fail("invalid profile frame")
        _vector(frame["origin"], "frame origin")
        _vector(frame["x_axis"], "frame x axis", True)
        _vector(frame["y_axis"], "frame y axis", True)
        if not isinstance(step["edges"], list) or not step["edges"]:
            _fail("profile must have edges")
        _vector(step["direction"], "direction", True)
        _number(step["start"], "start")
        _number(step["end"], "end")
        if step["end"] <= step["start"]:
            _fail("extrude end must exceed start")
        for key in ("start_formula", "end_formula"):
            if key in step and (not isinstance(step[key], str) or not step[key].strip()):
                _fail(key + " must be a nonempty native expression")
    elif kind == "boolean":
        if set(step) != {"id", "kind", "operation", "target", "tools", "retain_tools"}:
            _fail("unsupported or missing Boolean fields")
        if step["operation"] not in ("unite", "subtract", "intersect"):
            _fail("unsupported Boolean operation")
        _ident(step["target"], "target")
        tools = step["tools"]
        if not isinstance(tools, list) or not tools:
            _fail("at least one Boolean tool is required")
        for item in tools:
            _ident(item, "tool")
        if len(set(tools)) != len(tools) or step["target"] in tools:
            _fail("target and tools must be distinct")
        if type(step["retain_tools"]) is not bool:
            _fail("retain_tools must be boolean")
    elif kind == "prism":
        if set(step) != {"id", "kind", "frame", "lengths"}:
            _fail("unsupported or missing prism fields")
        frame = step["frame"]
        if not isinstance(frame, dict) or set(frame) != {"origin", "x_axis", "y_axis"}:
            _fail("invalid prism frame")
        _vector(frame["origin"], "frame origin")
        _vector(frame["x_axis"], "frame x axis", True)
        _vector(frame["y_axis"], "frame y axis", True)
        _vector(step["lengths"], "lengths")
        if any(value <= 0 for value in step["lengths"]):
            _fail("prism lengths must be positive")
    else:
        _fail("unsupported solid operation")
    return step
