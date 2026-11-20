"""Resolve independent engineering dimensions to native feature consumers."""
import math
import re


_REFERENCE = re.compile(r"\bv3_\w+\b")


def driver_map(steps, drivers):
    records = {}
    independent = {}
    for ident, item in drivers.items():
        name = item["native_expression"]
        if name in independent:
            raise ValueError(f"duplicate independent driver expression {name}")
        independent[name] = ident
        records[ident] = {"expression": name, "unit": item["unit"], "consumers": []}

    ancestors = {}
    for step in steps:
        kind = step["kind"]
        if kind == "expression":
            name = step["name"]
            sources = set()
            for ref in _REFERENCE.findall(step["formula"]):
                if ref not in ancestors:
                    raise ValueError(f"unresolved expression {ref} in {name}")
                sources.update(ancestors[ref])
            if name in independent:
                ident = independent[name]
                if records[ident]["unit"] != step.get("unit", "mm") or sources:
                    raise ValueError(f"driver unit or independence mismatch for {ident}")
                if not math.isfinite(float(step["formula"])):
                    raise ValueError(f"driver {ident} requires a finite independent value")
                sources.add(ident)
            ancestors[name] = sources
            continue
        if kind not in ("revolve", "extrude"):
            continue
        refs = set()
        if step["id"] == "rear_slot_tool":
            # UG11 consumes the three native Driving dimensions of one circle.
            refs.update(("v3_slot_axis_y", "v3_slot_axis_z", "v3_slot_radius"))
        else:
            for edge in step["edges"]:
                for row in edge.get("point_expressions", edge.get("pole_expressions", [])):
                    refs.update(row)
        for row in step.get("axis_points_expressions", []):
            refs.update(row)
        for key in ("start_formula", "end_formula"):
            refs.update(_REFERENCE.findall(step.get(key, "")))
        reached = set()
        for ref in refs:
            if ref not in ancestors:
                raise ValueError(f"unresolved {ref} at native feature {step['id']}")
            reached.update(ancestors[ref])
        for ident in reached:
            records[ident]["consumers"].append(step["id"])
    for ident, row in records.items():
        if not row["consumers"]:
            raise ValueError(f"independent driver has no native geometry consumer: {ident}")
    return records
