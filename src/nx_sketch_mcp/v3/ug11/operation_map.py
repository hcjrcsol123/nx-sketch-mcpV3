"""Trace P3 regions and construction nodes to the finite UG11 body operations."""
import math
import re


def operation_map(plan, steps):
    """Require every mathematical operation and every generated solid to correspond."""
    solids = {step["id"]: step for step in steps if step["kind"] != "expression"}
    result = {}

    def require(ident, kind):
        if ident not in solids or solids[ident]["kind"] != kind:
            raise ValueError(f"UG11 mapping requires {kind} step {ident}")
        return ident

    def boolean(ident, op, target, tools, retain=False):
        step = solids[require(ident, "boolean")]
        if (step["operation"], step["target"], step["tools"], step["retain_tools"]) != (
                op, target, tools, retain):
            raise ValueError(f"UG11 Boolean operands or retention differ for {ident}")
        return ident

    axial = {"head_cone_carrier": ("cone_carrier", "head.cone_piece"),
             "head_sphere_carrier": ("sphere_carrier", "head.R32_piece"),
             "head_lower_fillet": ("torus_carrier", "head.lower_fillet_piece"),
             "head_upper_fillet": ("torus_carrier", "head.upper_fillet_piece")}
    for node in plan["construction"]["nodes"]:
        ident, op = node["id"], node["operation"]
        if op in ("revolve_closed_meridian", "revolve_profile"):
            mapped = [require(ident, "revolve")]
            native = solids[ident]
            axis = node["axis"] if op == "revolve_closed_meridian" else node["axis_direction"]
            angle = node["sweep_rad"] if op == "revolve_closed_meridian" else node["angle_rad"]
            if native["axis_direction"] != axis or not math.isclose(
                    native["end_degrees"] - native["start_degrees"], math.degrees(angle),
                    abs_tol=1e-10, rel_tol=0):
                raise ValueError(f"UG11 axis or angular extent differs for {ident}")
        elif op in ("bounded_cylinder", "extrude_profile"):
            mapped = [require(ident, "extrude")]
        elif op in ("subtract", "regularized_difference"):
            mapped = [boolean(ident, "subtract", node["target"], [node["tool"]])]
        elif op in ("intersect", "union"):
            mapped = [boolean(ident, "intersect" if op == "intersect" else "unite",
                              node["left"], [node["right"]], retain=(op == "intersect"))]
        elif op == "regularized_union":
            inputs = node["depends_on"]
            mapped = [boolean(ident, "unite", inputs[0], inputs[1:])]
        elif op == "bounded_set":
            if node["carrier"] == "oriented_torus_and_halfspaces":
                torus = require(ident + ".torus", "revolve")
                clip = require(ident + ".clip", "extrude")
                mapped = [torus, clip, boolean(ident, "intersect", torus, [clip])]
            elif node["carrier"] in ("sphere_and_axial_clip", "revolved_disk_and_axial_clip",
                                    "positive_nappe_cone_and_axial_clip"):
                mapped = [require(ident, "revolve")]
            else:
                raise ValueError(f"unsupported bounded UG11 region {ident}")
        elif ident in axial and axial[ident][0] == op:
            mapped = [require(axial[ident][1], "revolve")]
        else:
            sector = re.fullmatch(r"head_sector_(\d+)(?:_branch_(\d+))?", ident)
            if not sector:
                raise ValueError(f"unmapped P3 operation {ident} ({op})")
            index, branch = sector.groups()
            if branch is None and op == "torus_carrier":
                piece = f"head.sector.{index}.A_piece"
            elif branch is not None and op == "tangent_torus_carrier":
                piece = f"head.sector.{index}.branch.{branch}.B_piece"
            else:
                raise ValueError(f"unmapped carrier type for {ident}")
            mapped = [require(piece + ".torus", "revolve")]
        if ident in result:
            raise ValueError(f"duplicate P3 node {ident}")
        result[ident] = mapped
    covered = {step_id for group in result.values() for step_id in group}
    if covered != set(solids):
        raise ValueError(f"UG11 steps without P3 operation: {sorted(set(solids) - covered)}")
    return result
