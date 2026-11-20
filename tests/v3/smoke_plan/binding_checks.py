"""T12 assertions on the *fresh* T09 block verification payload."""
import math

from block_oracle import EXPECTED, LENGTH_ABS_MM, check_geometry

CHECKS = ("bindings", "geometry", "history", "non_target_preservation")
ROLES = ("x", "y", "width", "height", "depth")


def check_fresh(verification, stage, block, constraints):
    if not isinstance(verification, dict) or verification.get("verified") is not True:
        raise ValueError("fresh verification did not report success")
    checks = verification.get("checks")
    if not isinstance(checks, dict):
        raise ValueError("fresh checks missing")
    reads = []
    for key in CHECKS:
        item = checks.get(key)
        if not isinstance(item, dict) or item.get("status") != "VERIFIED":
            raise ValueError("fresh check unavailable or failed: " + key)
        evidence = item.get("evidence")
        if not isinstance(evidence, dict) or evidence.get("matches_execute") is not True:
            raise ValueError("fresh check does not match execute: " + key)
        read = evidence.get("fresh_native_readback")
        if not isinstance(read, dict):
            raise ValueError("fresh native readback missing: " + key)
        reads.append(read)
    if any(read != reads[0] for read in reads[1:]):
        raise ValueError("fresh checks refer to different native observations")
    return check_readback(reads[0], stage, block, constraints)


def check_readback(read, stage, block, constraints):
    """Check native evidence, including a read-only post-reopen prepare view."""
    if not isinstance(read, dict):
        raise ValueError("native readback missing")
    if not isinstance(block, dict) or any(read.get(key) != block.get(source) or not read.get(key)
                                          for key, source in (("sketch_id", "sketch_id"),
                                                              ("extrude_id", "extrude_feature_id"),
                                                              ("body_id", "body_id"))):
        raise ValueError("fresh native identities do not match this session's block")
    if not isinstance(constraints, dict) or set(constraints) != set(ROLES[:4]):
        raise ValueError("current session's four constraint identities are required")
    values = EXPECTED[stage]
    parameters = read.get("parameters")
    if not isinstance(parameters, list) or len(parameters) != 5:
        raise ValueError("five native parameter observations are required")
    expected_values = (values["x_mm"], 5, values["width_mm"], values["height_mm"], 15)
    for role, expected, parameter in zip(ROLES, expected_values, parameters):
        if not isinstance(parameter, dict) or parameter.get("name") != "v3_" + role or parameter.get("unit") != "mm":
            raise ValueError("native name or units mismatch: " + role)
        value = parameter.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value - expected) > LENGTH_ABS_MM:
            raise ValueError("native value mismatch: " + role)
        if role == "depth":
            if parameter.get("kind") != "extrude_end" or parameter.get("consumer_id") != block["extrude_feature_id"] or block["extrude_feature_id"] not in parameter.get("using_features", []):
                raise ValueError("native extrude depth consumer missing")
        else:
            if parameter.get("kind") != "driving_dimension" or parameter.get("consumer_id") != constraints[role] or not parameter.get("geometry"):
                raise ValueError("native driving geometry consumer missing: " + role)
    if "".join(str(parameters[3].get("formula", "")).split()) != "v3_width*2/3":
        raise ValueError("native height formula mismatch")
    if "v3_height" not in parameters[2].get("referencing_expressions", []):
        raise ValueError("width native expression does not report height as consumer")
    return check_geometry(stage, {"length_unit": "mm", "volume_unit": "mm3", "solid_count": 1,
                                  "bbox_mm": read.get("bbox_mm"), "volume_mm3": read.get("volume_mm3")})
