"""Match two P1 inventories, without replaying NX session identifiers.

Carrier records and incidence are observations, not a finite-geometry proof.
Source-file binding and live NX state are separate caller-owned gates.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import json
import math
from pathlib import Path
from .project_root import project_root

from .regions.common import normalize_snapshot


class CorrespondenceError(ValueError):
    """The inventory does not uniquely establish P1 face correspondence."""


_ROOT = project_root()
_P1_SNAPSHOT = Path('workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json')


def _value(value):
    """Make all raw non-identity data hashable while rejecting malformed numbers."""
    if value is None or isinstance(value, str):
        return ('literal', value)
    if isinstance(value, bool):
        return ('bool', value)
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise CorrespondenceError('non-finite observation')
        return ('number', value)
    if isinstance(value, list):
        return ('list', tuple(_value(v) for v in value))
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return ('object', tuple((k, _value(v)) for k, v in sorted(value.items())))
    raise CorrespondenceError('unsupported observation type')


def _build(snapshot):
    normalized = normalize_snapshot(snapshot, tolerances={'linear': 1e-6, 'angular': 1e-6})
    body = snapshot['inventory']['selected_body']
    if body.get('unknown_surface_tags') not in (None, []):
        raise CorrespondenceError('unknown surfaces cannot be mapped')
    # Every raw field is included apart from ephemeral identities and adjacency;
    # adjacency is verified independently below. JID strings are not geometry.
    face_raw = body['faces']
    edge_raw = body['edges']
    faces = normalized['faces']
    edges = normalized['edges']
    face_keys = {ident: _value({k: v for k, v in raw.items()
                 if k not in {'tag', 'journal_id', 'edge_tags'}})
                 for ident, raw in zip(faces, face_raw)}
    edge_keys = {ident: _value({k: v for k, v in raw.items()
                 if k not in {'tag', 'journal_id', 'face_tags'}})
                 for ident, raw in zip(edges, edge_raw)}
    return normalized, face_keys, edge_keys


def _unique_faces(current, old):
    """Refine bipartite observation/adjacency colors; reject unresolved faces."""
    a, af, ae = current
    b, bf, be = old
    if a['unit'] != b['unit'] or len(af) != len(bf) or len(ae) != len(be):
        raise CorrespondenceError('inventory unit or entity counts differ')
    items = [(side, kind, ident) for side, fs, es in ((0, af, ae), (1, bf, be))
             for kind, ids in (('f', fs), ('e', es)) for ident in ids]
    initial = {(side, kind, ident): (kind, (af if side == 0 else bf)[ident] if kind == 'f'
                      else (ae if side == 0 else be)[ident]) for side, kind, ident in items}

    def colorize(signatures):
        palette = {}
        out = {}
        for item, sig in signatures.items():
            if sig not in palette:
                palette[sig] = len(palette)
            out[item] = palette[sig]
        return out

    colors = colorize(initial)
    while True:
        signatures = {}
        for side, kind, ident in items:
            inv = a if side == 0 else b
            if kind == 'f':
                neighbors = inv['faces'][ident]['edge_ids']
                other = 'e'
            else:
                neighbors = inv['edges'][ident]['face_ids']
                other = 'f'
            signatures[(side, kind, ident)] = (colors[(side, kind, ident)],
                tuple(sorted(colors[(side, other, n)] for n in neighbors)))
        refined = colorize(signatures)
        if len(set(refined.values())) == len(set(colors.values())):
            colors = refined
            break
        colors = refined
    groups = [defaultdict(list), defaultdict(list)]
    for side, kind, ident in items:
        if kind == 'f':
            groups[side][colors[(side, kind, ident)]].append(ident)
    if set(groups[0]) != set(groups[1]) or any(len(v) != 1 for group in groups for v in group.values()):
        raise CorrespondenceError('face observations and topology do not yield a unique mapping')
    return {ids[0]: groups[1][color][0] for color, ids in groups[0].items()}


def _edge_classes(current, old, face_map):
    a, _, ae = current
    b, _, be = old
    current_groups, old_groups = defaultdict(list), defaultdict(list)
    for ident, edge in a['edges'].items():
        current_groups[(ae[ident], tuple(sorted(face_map[f] for f in edge['face_ids'])))].append(ident)
    for ident, edge in b['edges'].items():
        old_groups[(be[ident], tuple(sorted(edge['face_ids'])))].append(ident)
    if set(current_groups) != set(old_groups) or any(
            len(current_groups[key]) != len(old_groups[key]) for key in current_groups):
        raise CorrespondenceError('edge observations or incidence multiplicity differ')
    return [{'current_edge_ids': sorted(current_groups[key]), 'p1_edge_ids': sorted(old_groups[key]),
             'individual_mapping_unique': len(current_groups[key]) == 1}
            for key in current_groups]


def correspond_reference(snapshot, plan):
    """Map current inventory faces and edge classes to the accepted P1/P3 record.

    Call only within the source evidence lease, after the caller has checked
    the live part and read consistency. Logical IDs are local array positions;
    they are diagnostic observations, not selectors or persistent NX tags.
    Exact raw observations and all face-edge incidence must match. The returned
    correspondence does not itself prove trimmed geometry or a clean NX part.
    """
    try:
        p1 = json.loads((_ROOT / _P1_SNAPSHOT).read_text(encoding='utf-8-sig'),
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite JSON')))
        current, old = _build(snapshot), _build(p1)
        if snapshot['inventory'].get('coordinate_system') != p1['inventory'].get('coordinate_system'):
            raise CorrespondenceError('inventory coordinate frame differs')
        mapping = _unique_faces(current, old)
        edge_classes = _edge_classes(current, old, mapping)
        if (not isinstance(plan, dict) or plan.get('p1_snapshot_id') != old[0]['snapshot_id']
                or plan.get('unit') != old[0]['unit'] or plan.get('p3_ready') is not True
                or plan.get('execution_approved') is not False):
            raise CorrespondenceError('plan does not identify the accepted P1 inventory')
        bindings = plan['face_construction_bindings']
        by_face = {entry['source_face']: entry for entry in bindings}
        if len(by_face) != len(bindings) or set(by_face) != set(old[0]['faces']):
            raise CorrespondenceError('plan does not have exactly one binding per P1 face')
        responsibility = {}
        for group in plan['source_responsibility']:
            for face in group['faces']:
                if face in responsibility:
                    raise CorrespondenceError('duplicate P3 face responsibility')
                responsibility[face] = group['region']
        if set(responsibility) != set(by_face) or any(
                by_face[f]['responsible_region'] != responsibility[f] for f in by_face):
            raise CorrespondenceError('P3 face responsibility differs from bindings')
        face_rows = [{'current_face_id': current_id, 'p1_face_id': p1_id,
                      'p3_binding': deepcopy(by_face[p1_id])}
                     for current_id, p1_id in sorted(mapping.items())]
        return {'schema': 'p1-inventory-correspondence/1.0',
                'current_snapshot_id': current[0]['snapshot_id'],
                'p1_snapshot_id': old[0]['snapshot_id'], 'unit': old[0]['unit'],
                'faces': face_rows, 'edge_equivalence_classes': edge_classes,
                'scope': 'exact observed carriers, edge properties and complete incidence; no trimmed geometry proof',
                'source_binding_checked_here': False, 'live_nx_state_checked_here': False}
    except CorrespondenceError:
        raise
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError) as exc:
        raise CorrespondenceError('invalid or unavailable P1 correspondence inputs') from exc
