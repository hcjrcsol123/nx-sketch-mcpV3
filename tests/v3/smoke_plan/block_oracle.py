"""Independent numeric checks for the single, manually specified P2 block.

Inputs must be fresh native readbacks of the selected solid in absolute part
coordinates. These checks are only a small architecture-smoke oracle, not a
general shape comparator or a manufacturing tolerance.
"""
import math

LENGTH_ABS_MM = 1.0e-5
VOLUME_ABS_MM3 = 1.0e-5
VOLUME_REL = 1.0e-8

# x=10, y=5, width=30, height=width*2/3, depth=15; then
# width=36, and finally x=14. Values were calculated independently of NX.
EXPECTED = {
    "initial": {"bbox_mm": (10, 5, 0, 40, 25, 15), "volume_mm3": 9000, "width_mm": 30, "height_mm": 20, "x_mm": 10},
    "width_edited": {"bbox_mm": (10, 5, 0, 46, 29, 15), "volume_mm3": 12960, "width_mm": 36, "height_mm": 24, "x_mm": 10},
    "position_edited": {"bbox_mm": (14, 5, 0, 50, 29, 15), "volume_mm3": 12960, "width_mm": 36, "height_mm": 24, "x_mm": 14},
}


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(field + " must be a finite number")
    return float(value)


def check_geometry(stage, observation):
    """Reject missing/invalid data or mismatch; return a record on success.

    Required observation keys: `length_unit` (mm), `volume_unit` (mm3),
    `solid_count` (exactly one), `bbox_mm` (xmin,ymin,zmin,xmax,ymax,zmax),
    `volume_mm3`. The caller is responsible for establishing freshness and
    identity, and for native expression/consumer/history verification.
    """
    if stage not in EXPECTED:
        raise ValueError("unknown smoke stage")
    if not isinstance(observation, dict):
        raise ValueError("observation must be an object")
    if observation.get("length_unit") != "mm" or observation.get("volume_unit") != "mm3":
        raise ValueError("native observations must explicitly be in mm and mm3")
    if type(observation.get("solid_count")) is not int or observation["solid_count"] != 1:
        raise ValueError("exactly one selected solid is required")
    bbox = observation.get("bbox_mm")
    if not isinstance(bbox, (tuple, list)) or len(bbox) != 6:
        raise ValueError("bbox_mm must contain six coordinates")
    bbox = [_number(item, "bbox_mm") for item in bbox]
    volume = _number(observation.get("volume_mm3"), "volume_mm3")
    expected = EXPECTED[stage]
    errors = [abs(actual - target) for actual, target in zip(bbox, expected["bbox_mm"])]
    volume_error = abs(volume - expected["volume_mm3"])
    volume_limit = max(VOLUME_ABS_MM3, VOLUME_REL * abs(expected["volume_mm3"]))
    if any(error > LENGTH_ABS_MM for error in errors) or volume_error > volume_limit:
        raise ValueError("native geometry differs from the independent " + stage + " oracle")
    return {"stage": stage, "bbox_error_mm": errors, "volume_error_mm3": volume_error,
            "length_limit_mm": LENGTH_ABS_MM, "volume_limit_mm3": volume_limit}
