"""Read a protected independent PRT in an isolated NX journal process.

Arguments must name an already byte-protected copy and a new evidence path. This reader never saves. Run only through the coordinated
physical lane and retain pre-load and post-exit byte-lock evidence separately.
"""
import ctypes as C
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import sys
import uuid

import NXOpen

NODE = "NX_SKETCH_MCP_V3_NODE"
STRING = NXOpen.NXObject.AttributeType.String


class DomainReject(ValueError):
    """A supported native read completed but the part is outside this family."""


def mass_volume_mm3(body):
    # Same UF API and units as the prior NX2506 independent inventory test.
    lib = C.CDLL(str(Path(os.environ['UGII_BASE_DIR']) / 'NXBIN/libufun.dll'))
    real = C.POINTER(C.c_double)
    fn = lib.UF_MODL_ask_mass_props_3d
    fn.argtypes = [C.POINTER(C.c_uint), C.c_int, C.c_int, C.c_int, C.c_double, C.c_int, real, real, real]
    fn.restype = C.c_int
    tags = (C.c_uint * 1)(int(body.Tag))
    props, stats = (C.c_double * 47)(), (C.c_double * 13)()
    accuracy = (C.c_double * 11)(1e-6, 1e-6)
    rc = fn(tags, 1, 1, 4, 1.0, 2, accuracy, props, stats)
    if rc or not all(math.isfinite(x) for x in (*props, *stats)):
        raise RuntimeError('UF mass-properties read failed')
    return props[1] * 1e9


def body_faults(body):
    lib = C.CDLL(str(Path(os.environ['UGII_BASE_DIR']) / 'NXBIN/libufun.dll'))
    tag = C.c_uint
    ints, tags = C.POINTER(C.c_int), C.POINTER(tag)
    ask = lib.UF_MODL_ask_body_consistency
    ask.argtypes = [tag, C.POINTER(C.c_int), C.POINTER(ints), C.POINTER(tags)]
    ask.restype = C.c_int
    release = lib.UF_free
    release.argtypes = [C.c_void_p]
    release.restype = None
    count, errors, entities = C.c_int(), ints(), tags()
    try:
        rc = ask(int(body.Tag), C.byref(count), C.byref(errors), C.byref(entities))
        if rc or count.value < 0: raise ValueError('body consistency call failed')
        return count.value
    finally:
        if errors: release(C.cast(errors, C.c_void_p))
        if entities: release(C.cast(entities, C.c_void_p))


def feature_key(feature):
    if feature.HasUserAttribute(NODE, STRING, 0):
        return 'node:' + feature.GetStringUserAttribute(NODE, 0)
    return 'jid:' + feature.JournalIdentifier


def snapshot(part):
    expressions = {}
    for expression in part.Expressions:
        if expression.Name in expressions or expression.OwningPart is None or expression.OwningPart.Tag != part.Tag:
            raise DomainReject('duplicate or foreign expression')
        if expression.IsInterpartExpression: raise DomainReject('interpart expression')
        expressions[expression.Name] = {'rhs': expression.RightHandSide, 'value': expression.Value,
                                        'interpart': False}
    features = {}
    slot = None
    for feature in part.Features:
        if feature.OwningPart is None or feature.OwningPart.Tag != part.Tag:
            raise DomainReject('foreign feature')
        parents = list(feature.GetParents())
        if any(p.OwningPart is None or p.OwningPart.Tag != part.Tag for p in parents):
            raise DomainReject('foreign feature parent')
        key = feature_key(feature)
        if key in features or 'WAVE' in feature.FeatureType.upper(): raise DomainReject('duplicate feature or WAVE')
        features[key] = {'type': feature.FeatureType, 'parents': sorted(feature_key(p) for p in parents),
                         'expressions': sorted(e.Name for e in feature.GetExpressions())}
        if key == 'node:rear_slot_tool': slot = feature
    if slot is None: raise DomainReject('slot feature missing')
    # These are feature-owned expression values, not independent proof of
    # NX's start/end limit association. The carrier witness provides a separate
    # check and full trim/consumer verification remains open.
    limits_by_rhs = {e.RightHandSide.replace(' ', ''): e.Value for e in slot.GetExpressions()}
    if set(limits_by_rhs) != {'-v3_slot_width/2', 'v3_slot_width/2'}:
        raise DomainReject('slot limit expression membership differs')
    limits = [limits_by_rhs['-v3_slot_width/2'], limits_by_rhs['v3_slot_width/2']]
    bodies = list(part.Bodies)
    if len(bodies) != 1 or not bodies[0].IsSolidBody: raise DomainReject('expected one solid')
    body = bodies[0]
    from collections import Counter
    volume = mass_volume_mm3(body)
    faces = list(body.GetFaces())
    shape = {'is_solid': True, 'body_consistency_fault_count': body_faults(body),
             'face_count': len(faces), 'edge_count': len(body.GetEdges()),
             'face_types': dict(Counter(str(f.SolidFaceType) for f in faces)), 'volume_mm3': volume}
    return {'expressions': expressions, 'features': features, 'slot_limits_mm': limits,
            'slot_limits_basis': 'feature-owned expression values; native limit binding not independently read',
            'body': shape}


def read(part, ident):
    data = snapshot(part)
    for expression in part.Expressions:
        row = data['expressions'][expression.Name]
        symbol = expression.Units.Symbol if expression.Units is not None else None
        value = float(expression.Value)
        if symbol in ('rad', 'radians'):
            value = math.radians(value)  # NX base angular Value is degrees.
        row.update(unit_symbol=symbol, value_in_expression_units=value)
    bodies = list(part.Bodies)
    if len(bodies) != 1 or not bodies[0].IsSolidBody:
        raise DomainReject('expected one solid body')
    body = bodies[0]
    lib = C.CDLL(str(Path(os.environ['UGII_BASE_DIR']) / 'NXBIN/libufun.dll'))
    real = C.POINTER(C.c_double)
    ask = lib.UF_MODL_ask_face_data
    ask.argtypes = [C.c_uint, C.POINTER(C.c_int), real, real, real,
                    C.POINTER(C.c_double), C.POINTER(C.c_double), C.POINTER(C.c_int)]
    ask.restype = C.c_int
    faces, edges = [], []
    for face in body.GetFaces():
        typ, sense = C.c_int(), C.c_int()
        radius, rd = C.c_double(), C.c_double()
        origin, direction, box = (C.c_double * 3)(), (C.c_double * 3)(), (C.c_double * 6)()
        rc = ask(int(face.Tag), C.byref(typ), origin, direction, box, C.byref(radius), C.byref(rd), C.byref(sense))
        if rc: raise ValueError('UF_MODL_ask_face_data failed: %d' % rc)
        faces.append({'tag': str(face.Tag), 'surface_type': {16: 'Cylindrical', 17: 'Conical', 18: 'Spherical', 19: 'SurfaceOfRevolution', 20: 'Swept', 22: 'Planar'}.get(typ.value, 'UFType%d' % typ.value),
                      'edge_tags': [str(e.Tag) for e in face.GetEdges()],
                      'native_face_data': {'origin': list(origin), 'direction': list(direction),
                          'bounding_box': list(box), 'radius': radius.value, 'radius_data': rd.value,
                          'normal_sense': sense.value, 'uf_type': typ.value}})
    for edge in body.GetEdges():
        edge_kind = str(edge.SolidEdgeType).split('.')[-1]
        edge_kind = {'1': 'Linear', '2': 'Circular', '4': 'Intersection', '5': 'Spline'}.get(edge_kind, edge_kind)
        edges.append({'tag': str(edge.Tag), 'edge_type': edge_kind,
                      'face_tags': [str(f.Tag) for f in edge.GetFaces()]})
    data['inventory_snapshot'] = {'ok': True, 'complete': True, 'inventory_complete': True,
        'read_consistency_fault': False, 'guard_errors': [], 'verification_sample_errors': [],
        'geometry_details_complete': False, 'snapshot_id': ident,
        'inventory': {'errors': [], 'selection_resolved': True, 'units': 'Millimeters',
                      'selected_body': {'faces': faces, 'edges': edges}}}
    return data


def canonicalize_sample(sample):
    """Sort only unordered P1 inventory collections using same-session tags.

    Face and edge collections are inventory sets; their adjacency tag lists
    are membership sets, as in ReferenceSnapshot.V3CheckAdjacency. Tags are
    local to this capture and never become cross-session selectors. Scalar
    values, vectors, limits, formulas and all other arrays stay untouched.
    """
    result = deepcopy(sample)
    body = result['inventory_snapshot']['inventory']['selected_body']
    for collection, adjacency in (('faces', 'edge_tags'), ('edges', 'face_tags')):
        rows = body[collection]
        if not isinstance(rows, list): raise ValueError('inventory collection is not a list: ' + collection)
        tags = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('tag'), str) or not row['tag']:
                raise ValueError('invalid inventory identity: ' + collection)
            tags.append(row['tag'])
            links = row.get(adjacency)
            if (not isinstance(links, list) or any(not isinstance(x, str) or not x for x in links)
                    or len(set(links)) != len(links)):
                raise ValueError('invalid or repeated inventory adjacency: ' + collection)
            row[adjacency] = sorted(links)
        if len(tags) != len(set(tags)): raise ValueError('duplicate inventory identity: ' + collection)
        body[collection] = sorted(rows, key=lambda row: row['tag'])
    return result


def sample_comparison(first, second, limit=100):
    """Keep differences exact; do not apply tolerance, float rounding or ID remapping."""
    a, b = canonicalize_sample(first), canonicalize_sample(second)
    raw_equal = json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(second, sort_keys=True, allow_nan=False)
    differences = []
    count = 0
    def visit(x, y, path):
        nonlocal count
        if isinstance(x, dict) and isinstance(y, dict):
            for key in sorted(x.keys() | y.keys()):
                p = path + '/' + str(key).replace('~', '~0').replace('/', '~1')
                if key not in x or key not in y:
                    count += 1
                    if len(differences) < limit: differences.append({'path': p, 'kind': 'missing_key'})
                else: visit(x[key], y[key], p)
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                count += 1
                if len(differences) < limit: differences.append({'path': path, 'kind': 'length', 'first': len(x), 'second': len(y)})
            for i, (left, right) in enumerate(zip(x, y)): visit(left, right, path + '/' + str(i))
        elif type(x) is not type(y) or x != y:
            count += 1
            if len(differences) < limit:
                differences.append({'path': path, 'kind': 'value', 'first': repr(x)[:200], 'second': repr(y)[:200]})
    visit(a, b, '')
    return {'raw_equal': raw_equal, 'canonical_equal': count == 0, 'difference_count': count,
            'differences': differences, 'differences_truncated': count > len(differences),
            'canonicalization': 'same-session face/edge inventory and adjacency membership ordering only'}


def main():
    import argparse
    import traceback
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('output')
    args = parser.parse_args()
    model = Path(args.source).resolve(strict=True)
    output = Path(args.output).resolve()
    result = {'schema': 'p7-parametric-family-observation/1', 'status': 'UNKNOWN',
              'safe_rejection': False}
    with output.open('x', encoding='utf-8') as stream:
        session = part = None
        source_bytes = None
        try:
            source_bytes = model.read_bytes()
            if model == output or model.suffix.lower() != '.prt':
                raise DomainReject('invalid input path')
            session = NXOpen.Session.GetSession()
            if list(session.Parts): raise RuntimeError('expected empty dedicated session')
            version = session.GetEnvironmentVariableValue('NX_FULL_VERSION')
            result['nx_build'] = version
            result['nx_build_source'] = 'Session.GetEnvironmentVariableValue(NX_FULL_VERSION)'
            if version != 'v2506.0.0.1700': raise DomainReject('unsupported NX build')
            # Bind to the NX-owned UF session before invoking direct UF reads.
            from NXOpen.UF import UFSession
            if UFSession.GetUFSession() is None: raise RuntimeError('NX UF session unavailable')
            part, load = session.Parts.OpenBaseDisplay(str(model))
            try:
                if load.NumberUnloadedParts or not part.IsFullyLoaded or Path(part.FullPath).resolve() != model:
                    raise RuntimeError('part load incomplete')
            finally:
                load.Dispose()
            if bool(part.IsModified): raise RuntimeError('input dirty before read')
            if part.PartUnits != NXOpen.BasePart.Units.Millimeters: raise DomainReject('expected millimeters')
            parents, children = part.GetInterpartParents(), part.GetInterpartChildren()
            if parents or children or len(list(session.Parts)) != 1: raise DomainReject('interpart or extra part loaded')
            ident = 'family-' + uuid.uuid4().hex
            result['samples'] = []
            first = read(part, ident)
            result['samples'].append(first)
            second = read(part, ident)
            result['samples'].append(second)
            comparison = sample_comparison(first, second)
            result['sample_comparison'] = comparison
            if not comparison['canonical_equal']: raise RuntimeError('native observations differ')
            inv = first['inventory_snapshot']
            readback = {key: value for key, value in first.items() if key != 'inventory_snapshot'}
            dirty_after = bool(part.IsModified)
            result.update(units='mm', dirty_before=False, samples_equal=True,
                          samples_equal_basis='exact after same-session unordered inventory canonicalization',
                          interpart={'parents': 0, 'children': 0}, readback=readback,
                          inventory_snapshot=inv, dirty_after=dirty_after, source_path=str(model))
            if dirty_after: raise RuntimeError('native read left part dirty')
            part.Close(NXOpen.BasePart.CloseWholeTree.FalseValue,
                       NXOpen.BasePart.CloseModified.CloseModified, None)
            part = None
            if list(session.Parts): raise RuntimeError('part remains open')
            result['closed_without_save'] = model.read_bytes() == source_bytes
            if not result['closed_without_save']: raise RuntimeError('source bytes changed')
            result['status'] = 'PASS'
        except DomainReject as exc:
            # Only a known domain miss can take this recovery path. A dirty
            # part, failed close, extra part or changed bytes leaves UNKNOWN.
            try:
                if part is not None:
                    if bool(part.IsModified): raise RuntimeError('part became dirty before rejection')
                    part.Close(NXOpen.BasePart.CloseWholeTree.FalseValue,
                               NXOpen.BasePart.CloseModified.CloseModified, None)
                    part = None
                if session is None or list(session.Parts): raise RuntimeError('empty session not established')
                if source_bytes is None or model.read_bytes() != source_bytes: raise RuntimeError('source bytes changed')
                result.update(status='SAFE_REJECTED', safe_rejection=True,
                              closed_without_save=True, no_parts_remaining=True,
                              source_path=str(model), error=str(exc))
            except Exception as cleanup:
                result.update(status='UNKNOWN', error_type=type(cleanup).__name__,
                              error=str(cleanup), rejection_reason=str(exc), traceback=traceback.format_exc())
        except Exception as exc:
            result.update(status='UNKNOWN', error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        json.dump(result, stream, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
