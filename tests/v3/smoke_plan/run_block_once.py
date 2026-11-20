"""ROOT ONLY: one authorized P2 smoke on an already-running isolated NX.

Never starts, opens or closes NX. Any exception or uncertain result stops the
chain without retry, return or server shutdown; preserve the live session for
manual investigation. This single-use runner does not perform UG11 acceptance.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from nx_sketch_mcp.config import load_config
from nx_sketch_mcp.server import McpServer
from nx_sketch_mcp.v3.nx2506_executor import Executor
from binding_checks import check_fresh, check_readback


def write_new(path, value):
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write("\n")


def scrub(value, secrets):
    if isinstance(value, dict):
        return {k: scrub(v, secrets) for k, v in value.items()
                if not any(s in str(k).lower() for s in ("ownership_id", "token", "secret", "password", "credential"))}
    if isinstance(value, list):
        return [scrub(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[redacted]")
    return value


def find_secrets(value, secrets):
    if isinstance(value, dict):
        for key, child in value.items():
            if any(s in str(key).lower() for s in ("ownership_id", "token", "secret", "password", "credential")):
                if isinstance(child, str) and child:
                    secrets.add(child)
            else:
                find_secrets(child, secrets)
    elif isinstance(value, list):
        for child in value:
            find_secrets(child, secrets)


class RecordingTransport:
    def __init__(self, server, directory):
        self.server, self.directory = server, directory
        self.serial, self.secrets = 0, set()
        self.stopped = False

    def call(self, name, args):
        if self.stopped:
            raise RuntimeError("transport stopped")
        self.serial += 1
        prefix = "%04d" % self.serial
        find_secrets(args, self.secrets)
        write_new(self.directory / (prefix + "-request.json"), scrub({"tool": name, "arguments": args}, self.secrets))
        try:
            message = {"jsonrpc": "2.0", "id": self.serial + 10, "method": "tools/call",
                       "params": {"name": name, "arguments": args}}
            response = self.server.handle_message(message)
            find_secrets(response, self.secrets)
            write_new(self.directory / (prefix + "-response.json"), scrub(response, self.secrets))
            result = response.get("result", {}) if isinstance(response, dict) else {}
            content = result.get("structuredContent") if isinstance(result, dict) else None
            if (not isinstance(content, dict) or result.get("isError") is True or
                    content.get("ok") is not True or content.get("writes_halted") is True or
                    content.get("state") == "UNKNOWN"):
                raise RuntimeError("missing, failed or uncertain response")
            return content
        except Exception:
            self.stopped = True
            raise


def same_path(a, b):
    return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


def select_reopened(part):
    if not isinstance(part, dict):
        raise ValueError("reopened inventory missing")
    sketches, bodies, features = part.get("sketches"), part.get("bodies"), part.get("features")
    if (not all(isinstance(x, list) for x in (sketches, bodies, features)) or
            len(sketches) != 1 or len(bodies) != 1 or len(features) not in (3, 4) or
            not isinstance(sketches[0], dict) or not isinstance(bodies[0], dict) or
            not all(isinstance(f, dict) for f in features)):
        raise ValueError("reopened block inventory is ambiguous")
    feature_ids = [f.get("journal_id") for f in features]
    if any(not isinstance(v, str) or not v for v in feature_ids) or len(set(feature_ids)) != len(feature_ids):
        raise ValueError("reopened feature identities missing or ambiguous")
    by_type = {}
    for feature in features:
        kind = feature.get("feature_type")
        if not isinstance(kind, str):
            raise ValueError("reopened feature type missing")
        by_type.setdefault(kind.upper(), []).append(feature)
    required = {"ABSOLUTE_DATUM_PLANE", "SKETCH", "EXTRUDE"}
    if (set(by_type) not in (required, required | {"DATUM_CSYS"}) or
            any(len(items) != 1 for items in by_type.values()) or bodies[0].get("is_solid") is not True):
        raise ValueError("reopened history has unknown, repeated or missing features")
    datum, sketch_feature, extrude = (by_type[k][0] for k in ("ABSOLUTE_DATUM_PLANE", "SKETCH", "EXTRUDE"))
    datum_id, sketch_feature_id, extrude_id = (x["journal_id"] for x in (datum, sketch_feature, extrude))
    sketch_id, body_id = sketches[0].get("journal_id"), bodies[0].get("journal_id")
    ids = {"sketch_id": sketch_id, "body_id": body_id, "extrude_feature_id": extrude_id}
    if any(not isinstance(v, str) or not v for v in ids.values()):
        raise ValueError("reopened object identity missing")
    support = sketches[0].get("support_association")
    if (sketches[0].get("feature_journal_id") != sketch_feature_id or not isinstance(datum.get("datum_plane"), dict) or
            not isinstance(support, dict) or support.get("support_kind") != "DATUM_PLANE" or
            support.get("native") is not True or support.get("native_feature_parent") is not True or
            support.get("datum_plane_id") != datum_id):
        raise ValueError("reopened sketch has no unique native datum support")
    def only_list(item, key, expected):
        actual = item.get(key)
        return isinstance(actual, list) and len(actual) == len(expected) and set(actual) == set(expected)
    parents = sketch_feature.get("parent_ids")
    if not isinstance(parents, list) or len(parents) != 1 or not isinstance(parents[0], str) or not parents[0]:
        raise ValueError("reopened sketch parent missing or ambiguous")
    internal_id = parents[0]
    if (internal_id in (datum_id, sketch_feature_id, extrude_id) or
            not only_list(sketches[0], "parent_feature_ids", [internal_id]) or
            not only_list(support, "ancestor_feature_ids", [datum_id, internal_id]) or
            not only_list(datum, "parent_ids", []) or not only_list(datum, "child_ids", [internal_id]) or
            not only_list(sketch_feature, "child_ids", [extrude_id]) or
            not only_list(extrude, "parent_ids", [sketch_feature_id]) or
            not only_list(extrude, "child_ids", []) or not only_list(extrude, "body_ids", [body_id])):
        raise ValueError("reopened feature graph is not closed")
    if "DATUM_CSYS" in by_type:
        internal = by_type["DATUM_CSYS"][0]
        if (internal["journal_id"] != internal_id or not only_list(internal, "parent_ids", [datum_id]) or
                not only_list(internal, "child_ids", [sketch_feature_id])):
            raise ValueError("reopened internal datum is not the unique support")
    elif internal_id in feature_ids:
        raise ValueError("hidden internal datum aliases another visible feature")
    return ids


def operation(transport, name, arguments, max_polls=900):
    oid = arguments["operation_id"]
    value = transport.call(name, arguments)
    for _ in range(max_polls + 1):
        if value.get("operation_id") != oid:
            raise RuntimeError("operation identity mismatch")
        if value.get("state") == "SUCCEEDED":
            if not isinstance(value.get("result"), dict):
                raise RuntimeError("operation result missing")
            return value["result"]
        if value.get("state") not in ("QUEUED", "RUNNING"):
            raise RuntimeError("operation not successful")
        time.sleep(0.2)
        value = transport.call("nx_get_operation", {"operation_id": oid})
    raise RuntimeError("operation unresolved; manual check required")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--part", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    source = ROOT / "tests" / "外球叉.prt"
    if (args.pid <= 0 or not args.part.is_absolute() or not args.part.is_file() or
            not args.config.is_absolute() or not args.config.is_file() or
            not args.target.is_absolute() or args.target.suffix.lower() != ".prt" or
            not args.target.parent.is_dir() or args.target.exists() or
            not args.evidence_dir.is_absolute() or not args.evidence_dir.is_dir() or
            any(args.evidence_dir.iterdir()) or same_path(args.part, args.target) or
            (source.exists() and os.path.samefile(args.part, source))):
        parser.error("new evidence directory, new target and existing independent work part/config are required")
    document = json.loads((Path(__file__).with_name("block-plan.json")).read_text(encoding="utf-8"))
    report = {"status": "INCONCLUSIVE", "stage": "initialize", "part": str(args.part), "target": str(args.target)}
    server = McpServer(load_config(args.config))
    transport = RecordingTransport(server, args.evidence_dir)
    returned = False
    try:
        response = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "p2-block-smoke", "version": "1"}}})
        if not isinstance(response, dict) or "result" not in response:
            raise RuntimeError("initialization failed")
        server.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        report["stage"] = "takeover"
        taken = transport.call("nx_takeover", {"expected_pid": args.pid, "expected_part_path": str(args.part.resolve()),
                                               "artifact_scope": "saved_independent_copy", "authorize": True})
        owner, epoch = taken.get("ownership_id"), taken.get("binding_epoch")
        if taken.get("ownership_state") != "AI_OWNED" or not isinstance(owner, str) or not owner or type(epoch) is not int:
            raise RuntimeError("takeover identity unresolved")
        creds = {"ownership_id": owner, "binding_epoch": epoch}
        report["stage"] = "blank_preflight"
        session = transport.call("nx_get_session", creds)
        if not same_path(session.get("part_path", ""), args.part) or session.get("part_units") != "Millimeters":
            raise RuntimeError("work part path or units mismatch")
        before = transport.call("nx_inspect_part", creds)
        if any(not isinstance(before.get(k), list) or before[k] for k in ("features", "sketches", "bodies")):
            raise RuntimeError("fixture is not empty")
        revision = before.get("revision_id")
        executor = Executor(transport, owner, epoch, revision)
        report["stage"] = "create"
        block = executor.create_block(document)
        ids = block["constraint_ids"]
        for action, value, stage in (("bind", None, "initial"), ("edit_width", "36", "width_edited"),
                                     ("edit_x", "14", "position_edited")):
            report["stage"] = action
            applied = executor.bind_or_edit(ids, action, value)
            if applied.get("result", {}).get("evidence", {}).get("readback_verified") is not True:
                raise RuntimeError("binding execute readback missing")
            check_fresh(executor.last_verification, stage, block, ids)
        report["stage"] = "save_reopen"
        saved = operation(transport, "nx_save_copy", {**creds, "operation_id": "p2-save-" + uuid.uuid4().hex,
                                                       "target_path": str(args.target), "reopen": True})
        new_owner, new_epoch = saved.get("new_ownership_id"), saved.get("new_binding_epoch")
        if (saved.get("saved") is not True or saved.get("reopened") is not True or
                not isinstance(new_owner, str) or not new_owner or new_owner == owner or
                type(new_epoch) is not int or new_epoch == epoch or not same_path(saved.get("saved_path", ""), args.target) or
                not args.target.is_file()):
            raise RuntimeError("save/reopen identity unresolved")
        save_checks = saved.get("checks")
        if not isinstance(save_checks, dict) or any(
                not isinstance(save_checks.get(key), dict) or save_checks[key].get("status") != "VERIFIED"
                for key in ("expression", "geometry", "history", "associations")):
            raise RuntimeError("save/reopen checks incomplete")
        creds = {"ownership_id": new_owner, "binding_epoch": new_epoch}
        report["stage"] = "reopen_readback"
        session = transport.call("nx_get_session", creds)
        if not same_path(session.get("part_path", ""), args.target) or session.get("part_units") != "Millimeters":
            raise RuntimeError("reopened path or units mismatch")
        reopened = transport.call("nx_inspect_part", creds)
        current = select_reopened(reopened)
        fresh = Executor(transport, new_owner, new_epoch, reopened.get("revision_id"))
        current_ids = fresh.resolve_reopened_constraints(**current, dimensions={"x": 14, "y": 5, "width": 36, "height": 24})
        dirty_before = transport.call("nx_get_session", creds)
        if (dirty_before.get("ownership_state") != "AI_OWNED" or
                dirty_before.get("ownership_id") != new_owner or dirty_before.get("binding_epoch") != new_epoch or
                dirty_before.get("revision_id") != fresh.revision or
                dirty_before.get("semantic_changed_since_previous_read") is not False or
                type(dirty_before.get("is_modified_after_read")) is not bool):
            raise RuntimeError("reopened identity, revision, or dirty state unresolved")
        plan = fresh.preview_block_binding(current_ids, "37")
        check_readback(plan.get("before"), "position_edited", current, current_ids)
        dirty_after = transport.call("nx_get_session", creds)
        if (dirty_after.get("ownership_state") != "AI_OWNED" or dirty_after.get("ownership_id") != new_owner or
                dirty_after.get("binding_epoch") != new_epoch or
                dirty_after.get("revision_id") != fresh.revision or
                dirty_after.get("semantic_changed_since_previous_read") is not False or
                type(dirty_after.get("is_modified_after_read")) is not bool):
            raise RuntimeError("post-prepare identity, revision, semantics, or dirty state unresolved")
        report["reopen_dirty"] = {"before": dirty_before.get("is_modified_after_read"),
                                  "after": dirty_after.get("is_modified_after_read")}
        report["stage"] = "return"
        result = transport.call("nx_return", creds)
        if result.get("ownership_state") != "HUMAN_OWNED" or result.get("safe_for_human") is not True:
            raise RuntimeError("safe return not established")
        returned = True
        report.update(status="NX2506_PASS", stage="complete")
    except Exception as exc:
        transport.stopped = True
        report.update(status="STOP_MANUAL_CHECK", failure_type=type(exc).__name__, failure_message=str(exc),
                      next_action="preserve session and inspect; no automatic retry or return")
    finally:
        write_new(args.evidence_dir / "summary.json", scrub(report, transport.secrets))
        if returned:
            server.close()
        print(json.dumps(scrub(report, transport.secrets), ensure_ascii=False))
    return 0 if returned else 2


if __name__ == "__main__":
    sys.exit(main())
