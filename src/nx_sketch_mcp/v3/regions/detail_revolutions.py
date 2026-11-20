"""Bounded UF205 spline-generatrix revolution carrier observations.

A carrier is not a solid feature, a trimmed face proof, or an editable design.
All identifiers and evidence are local to the supplied detail inventory.
"""
from collections.abc import Mapping
from copy import deepcopy
import math

from .detail_extrusions import _spline


def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _vec(x):
    return list(x) if isinstance(x, list) and len(x) == 3 and all(_finite(v) for v in x) else None


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def _unit(v):
    length = math.hypot(*v)
    return [x/length for x in v] if _finite(length) and length > 0 else None


def _control_points(curve):
    if not _spline(curve):
        return None
    knots, order = curve['knots'], curve['order']
    # An over-multiple knot is not a valid order-k spline representation.
    run = 1
    for a, b in zip(knots, knots[1:]):
        run = run + 1 if a == b else 1
        if run > order:
            return None
    raw = curve['weighted_poles_flat_xyzw']
    weights = raw[3::4]
    # A non-rational representation cannot encode varying rational weights.
    if not curve['rational'] and any(w != weights[0] for w in weights):
        return None
    points = [[raw[i+j] / raw[i+3] for j in range(3)] for i in range(0, len(raw), 4)]
    return points if all(all(_finite(v) for v in p) for p in points) else None


def _occurrences(root, mapping, declared, edges, fid):
    """Require one directed, uniquely sourced edge for each recorded fin."""
    if not isinstance(root, Mapping) or root.get('type') != 5:
        return None
    loops = root.get('children')
    if not isinstance(loops, list) or not loops:
        return None
    found = []
    for li, lr in enumerate(loops):
        if not isinstance(lr, Mapping) or type(lr.get('orientation')) is not int or lr['orientation'] not in (-1, 0, 1):
            return None
        loop = lr.get('child')
        if not isinstance(loop, Mapping) or loop.get('type') != 6 or not isinstance(loop.get('children'), list) or not loop['children']:
            return None
        for fi, fr in enumerate(loop['children']):
            if not isinstance(fr, Mapping) or type(fr.get('orientation')) is not int or fr['orientation'] not in (-1, 1):
                return None
            fin = fr.get('child')
            if (not isinstance(fin, Mapping) or fin.get('type') != 7 or fin.get('geometry_rc') != 0
                    or fin.get('geometry_free_rc') != 0 or not _spline(fin.get('geometry'))):
                return None
            refs = fin.get('children')
            if not isinstance(refs, list) or len(refs) != 1 or not isinstance(refs[0], Mapping):
                return None
            er = refs[0]
            if (type(er.get('orientation')) is not int or er['orientation'] not in (-1, 1)
                    or er['orientation'] != fr['orientation']):
                return None
            edge = er.get('child')
            if not isinstance(edge, Mapping) or edge.get('type') != 8 or edge.get('edge_class_rc') != 0:
                return None
            tag = str(edge.get('tag'))
            eid = mapping.get(tag)
            if eid not in edges or str(edges[eid].get('source_tag')) != tag or fid not in edges[eid].get('face_ids', []):
                return None
            geom = edge.get('geometry')
            if not isinstance(geom, Mapping):
                return None
            if geom.get('type') == 'circular_evaluator':
                if edges[eid].get('edge_type') != 'Circular':
                    return None
            elif edge.get('geometry_rc') != 0 or edge.get('geometry_free_rc') != 0:
                return None
            found.append({'edge_id': eid, 'source_tag': tag, 'loop_index': li, 'fin_index': fi,
                          'loop_orientation': lr['orientation'], 'fin_orientation': fr['orientation'],
                          'edge_orientation': er['orientation'], 'fin_geometry': deepcopy(fin['geometry']),
                          'edge_geometry': deepcopy(geom), 'direction_relation': 'unverified'})
    ids = [x['edge_id'] for x in found]
    return found if len(ids) == len(set(ids)) and set(ids) == set(declared) else None


def recognize(inventory):
    """Return unconfirmed UF205 carrier candidates or explicit unresolved records."""
    tol = inventory.get('tolerances', {}).get('linear')
    if not _finite(tol) or tol <= 0:
        raise ValueError('positive finite linear tolerance required in part units')
    if inventory.get('contract_version') != 'detail-inventory/1.0':
        raise ValueError('detail-inventory/1.0 required')
    results = []
    for fid, detail in inventory['detail_faces'].items():
        face = inventory['faces'].get(fid, {})
        if face.get('surface_type') != 'SurfaceOfRevolution':
            continue
        diagnostic = detail.get('diagnostic', {})
        root = diagnostic.get('topology') if isinstance(diagnostic, Mapping) else None
        geometry = root.get('geometry') if isinstance(root, Mapping) else None
        # The distinct UF204 torus mode is owned by detail_tori.
        if isinstance(geometry, Mapping) and geometry.get('type') == 204:
            continue
        geometry = geometry if isinstance(geometry, Mapping) else {}
        gen, axis, origin = geometry.get('generator'), _vec(geometry.get('axis')), _vec(geometry.get('point_on_axis'))
        source, mapping = detail.get('source_edge_ids'), detail.get('source_edges_by_tag')
        reasons, boundary, plane = [], None, None
        if inventory.get('coordinate_system') != 'absolute_part_coordinates':
            reasons.append('absolute part coordinate frame is not established')
        if face.get('native_face_data', {}).get('uf_type') != 19 or geometry.get('type') != 205:
            reasons.append('surface is not the supported UF19 / UF205 revolution carrier')
        points = _control_points(gen)
        if points is None:
            reasons.append('generating spline is missing, invalid, or has inconsistent weights')
        axis_unit = _unit(axis) if axis is not None else None
        if origin is None or axis_unit is None:
            reasons.append('axis point or axis direction is absent or degenerate')
        if (not isinstance(source, list) or not source or len(source) != len(set(source))
                or not isinstance(mapping, Mapping) or len(mapping) != len(source)
                or set(mapping.values()) != set(source) or set(source) != set(face.get('edge_ids', []))
                or detail.get('source_face_id') != fid):
            reasons.append('source face or edge linkage is incomplete or nonunique')
        elif isinstance(root, Mapping):
            boundary = _occurrences(root, mapping, source, inventory['edges'], fid)
            if boundary is None:
                reasons.append('directed loop, fin, and edge sources are incomplete or nonunique')
        if (not isinstance(root, Mapping) or str(root.get('tag')) != str(face.get('source_tag'))
                or root.get('geometry_rc') != 0 or root.get('geometry_free_rc') != 0
                or not isinstance(diagnostic, Mapping) or diagnostic.get('edge_coverage_complete') is not True):
            reasons.append('native face topology, geometry, or edge coverage is incomplete')
        uv = diagnostic.get('uv_box') if isinstance(diagnostic, Mapping) else None
        if not isinstance(uv, list) or len(uv) != 4 or not all(_finite(x) for x in uv):
            reasons.append('face UV observation is missing or invalid')
        if points is not None and axis_unit is not None and origin is not None:
            offsets = [[p[i]-origin[i] for i in range(3)] for p in points]
            radial = [[v[i]-_dot(v, axis_unit)*axis_unit[i] for i in range(3)] for v in offsets]
            lengths = [math.hypot(*v) for v in radial]
            largest = max(range(len(lengths)), key=lengths.__getitem__)
            if not _finite(lengths[largest]) or lengths[largest] <= tol:
                reasons.append('generator control polygon is parallel to or degenerate at the axis; section plane is not determined')
            else:
                radial_unit = _unit(radial[largest])
                normal = _unit(_cross(axis_unit, radial_unit))
                distances = [abs(_dot(v, normal)) for v in offsets]
                signed = [_dot(v, radial_unit) for v in offsets]
                if not all(_finite(x) for x in distances + signed) or max(distances) > tol:
                    reasons.append('generator control points do not lie in one axis-containing plane within tolerance')
                elif min(signed) <= tol:
                    reasons.append('control polygon cannot prove separation from the axis within tolerance; actual crossing is not established')
                else:
                    plane = {'point_on_axis': deepcopy(geometry['point_on_axis']), 'normal': normal,
                             'axis_unit': axis_unit, 'radial_unit': radial_unit,
                             'max_control_point_distance': max(distances), 'linear_tolerance': tol,
                             'minimum_signed_control_radius': min(signed), 'length_unit': inventory['unit'],
                             'basis': 'positive-weight B-spline affine control-point hull; tolerance-bounded plane, no finite sampling proof'}
        evidence = {'type': 'native_revolution_carrier', 'snapshot_id': inventory['snapshot_id'],
                    'source_face_id': fid, 'source_edge_ids': deepcopy(source), 'source_edges_by_tag': deepcopy(mapping),
                    'evidence_path': detail.get('evidence_path'), 'summary_path': detail.get('summary_path'),
                    'coordinate_system': inventory.get('coordinate_system'), 'native_geometry_frame': 'UF_BREP native frame; equivalence to inventory ABS unverified',
                    'length_unit': inventory['unit'],
                    'point_on_axis': deepcopy(geometry.get('point_on_axis')), 'axis': deepcopy(geometry.get('axis')),
                    'generator': deepcopy(gen), 'uv_box': deepcopy(uv), 'uv_unit': 'unknown',
                    'topology': deepcopy(root), 'edge_occurrences': boundary, 'candidate_section_plane': plane,
                    'root_complete': False, 'basis': 'native underlying surface and source topology; trim equivalence unverified'}
        results.append({'id': 'detail_revolution_' + fid, 'snapshot_id': inventory['snapshot_id'],
                        'kind': 'unresolved_detail_revolution' if reasons else 'possible_spline_revolution_surface',
                        'coverage_role': 'observation', 'source_faces': [fid],
                        'source_edges': deepcopy(source) if isinstance(source, list) else [], 'evidence': [evidence],
                        'parameters': [], 'alternatives': ['native revolve route using a verified editable section', 'another verified equivalent construction'],
                        'open_items': ['The generator is only an underlying carrier: closed section, sweep extent, trim domain, material direction, and solid feature are not established; do not infer 360 degrees.',
                                       'UF_BREP generator and axis are treated as sharing a native frame; their equivalence to the inventory ABS frame is unverified.',
                                       'UV units and direction, fin traversal and full boundary equivalence require verification; finite sampling does not prove complete geometry.',
                                       'Engineering dimensions, relationships, edit ranges and design intent remain open; fixed spline poles do not constitute a full engineering parameterization.'] + reasons,
                        'capability_requirements': ['T04.b: verify complete trimmed surface, topology and editable revolution on the target version', 'confirm engineering dimensions and relationships'],
                        'depends_on': [], 'confirmed': False, 'confirmation': {'status': 'unconfirmed'}, 'execution_approved': False})
    return results
