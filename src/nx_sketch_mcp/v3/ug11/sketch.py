"""UG11 mapping of the P4 expression-driven profile; does not execute NX.

The caller validates the operation and expression graph, owns transactions and
native verification, and must retain the ordered edge-to-curve mapping.
"""
from pathlib import Path
import math
import re

class UnsupportedSketch(ValueError):
    """The profile cannot be represented without dropping its associations."""

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def source():
    """Return the standalone NX11 C# binding. Compile only, no NX launch."""
    return (Path(__file__).parent / "templates" / "SketchBinding.cs").read_text(encoding="utf-8-sig")


def _vector(value, count, label):
    if not isinstance(value, (tuple, list)) or len(value) != count:
        raise UnsupportedSketch(label + " must contain %d values" % count)
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in value):
        raise UnsupportedSketch(label + " must contain finite numbers")
    return value


def _refs(value, count):
    if not isinstance(value, list) or len(value) != count:
        raise UnsupportedSketch("missing expression-backed point rows")
    for row in value:
        if not isinstance(row, list) or len(row) != 3 or any(not isinstance(x, str) or not _NAME.fullmatch(x) for x in row):
            raise UnsupportedSketch("each point must reference three named XYZ expressions")


def validate_step(step):
    """Validate profile fields of a P4 extrude/revolve step, without mutation.

    Other step fields and formula definitions belong to the composition compiler.
    On success return the input step; this is not solver or native evidence.
    """
    if not isinstance(step, dict) or step.get("kind") not in ("extrude", "revolve"):
        raise UnsupportedSketch("expected an extrude or revolve profile")
    frame = step.get("frame")
    if not isinstance(frame, dict) or set(frame) != {"origin", "x_axis", "y_axis"}:
        raise UnsupportedSketch("expected explicit origin and two frame axes")
    _vector(frame["origin"], 3, "frame origin")
    x = _vector(frame["x_axis"], 3, "frame x axis")
    y = _vector(frame["y_axis"], 3, "frame y axis")
    if abs(sum(a*a for a in x)-1) > 1e-8 or abs(sum(a*a for a in y)-1) > 1e-8 or abs(sum(a*b for a,b in zip(x,y))) > 1e-8:
        raise UnsupportedSketch("frame axes must be orthonormal")
    edges = step.get("edges")
    if not isinstance(edges, list) or not edges:
        raise UnsupportedSketch("empty profile")
    for edge in edges:
        if not isinstance(edge, dict):
            raise UnsupportedSketch("invalid edge")
        kind = edge.get("kind")
        if kind in ("line", "arc"):
            keys = {"kind", "start", "end", "point_expressions"} | ({"mid"} if kind == "arc" else set())
            if set(edge) != keys:
                raise UnsupportedSketch("line/arc requires exactly its coordinates and associative point references")
            points = [_vector(edge[k], 2, k) for k in (("start", "end") if kind == "line" else ("start", "mid", "end"))]
            _refs(edge["point_expressions"], len(points))
            if points[0] == points[-1]:
                raise UnsupportedSketch("degenerate edge")
            if kind == "arc":
                a,b,c=points
                if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])) <= 1e-14:
                    raise UnsupportedSketch("degenerate arc")
        elif kind == "spline":
            if set(edge) != {"kind", "method", "order", "knots", "poles", "pole_expressions"} or edge["method"] != "studio" or edge["order"] != 4:
                raise UnsupportedSketch("expected expression-driven cubic Studio Spline")
            poles = edge["poles"]
            if not isinstance(poles, list) or len(poles) < 4:
                raise UnsupportedSketch("cubic spline needs four or more poles")
            for p in poles:
                _vector(p, 3, "pole")
                if p[2] != 1:
                    raise UnsupportedSketch("rational poles are unsupported")
            _refs(edge["pole_expressions"], len(poles))
            knots = _vector(edge["knots"], len(poles)+4, "knots")
            if list(knots[:4]) != [0]*4 or list(knots[-4:]) != [1]*4 or knots[4] <= 0 or knots[-5] >= 1 or any(a > b for a,b in zip(knots, knots[1:])):
                raise UnsupportedSketch("spline knots must be normalized, clamped and nondecreasing")
            if any(knots[i] == knots[i+3] and 0 < knots[i] < 1 for i in range(len(knots)-3)):
                raise UnsupportedSketch("interior knot multiplicity exceeds three")
        else:
            raise UnsupportedSketch("unsupported profile geometry: " + str(kind))
    return step

def validate_rear_slot(step):
    """Only replace the exact P4 rear-slot two semicircles by the native circle.

    The caller must also compare native initial expression values against the
    frame center and radius before constructing, and verify all edits/readback.
    """
    validate_step(step)
    if step.get("id") != "rear_slot_tool" or step.get("kind") != "extrude":
        raise UnsupportedSketch("not the rear-slot tool")
    frame = step["frame"]
    if frame["origin"][0] != 0 or frame["x_axis"] != [0,1,0] or frame["y_axis"] != [0,0,1] or frame["origin"][1] >= 0 or frame["origin"][2] <= 0:
        raise UnsupportedSketch("rear-slot frame outside supported domain")
    e = step["edges"]
    if len(e) != 2 or any(edge["kind"] != "arc" for edge in e):
        raise UnsupportedSketch("rear-slot requires two semicircles")
    radius = e[0]["start"][0]
    if radius <= 0 or [e[0][k] for k in ("start","mid","end")] != [[radius,0],[0,radius],[-radius,0]] or [e[1][k] for k in ("start","mid","end")] != [[-radius,0],[0,-radius],[radius,0]]:
        raise UnsupportedSketch("rear-slot arcs do not describe the same circle")
    expected = [
        [["v3_stock_zero","v3_slot_high_y","v3_slot_axis_z"], ["v3_stock_zero","v3_slot_axis_y","v3_slot_high_z"], ["v3_stock_zero","v3_slot_low_y","v3_slot_axis_z"]],
        [["v3_stock_zero","v3_slot_low_y","v3_slot_axis_z"], ["v3_stock_zero","v3_slot_axis_y","v3_slot_low_z"], ["v3_stock_zero","v3_slot_high_y","v3_slot_axis_z"]],
    ]
    if [edge["point_expressions"] for edge in e] != expected:
        raise UnsupportedSketch("rear-slot expression bindings differ")
    return {"center_y": frame["origin"][1], "center_z": frame["origin"][2], "radius": radius}
