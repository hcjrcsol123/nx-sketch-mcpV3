"""Discover a bounded cylindrical region from the current P1 carriers.

This recognizes carrier geometry, not a complete trimmed cut or design intent.
An empty result includes ambiguous inputs. Source IDs are snapshot-local only.
"""
from itertools import combinations
import math


def _unit(vector):
    length = math.hypot(*vector)
    if not math.isfinite(length) or length == 0:
        return None
    return [x / length for x in vector]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _region(inventory, face_id, plane_ids):
    faces, edges = inventory['faces'], inventory['edges']
    cylinder = faces[face_id]
    data = cylinder['native_face_data']
    if cylinder['surface_type'].lower() != 'cylindrical' or data['normal_sense'] != -1:
        return None
    axis = _unit(data['direction'])
    radius = data['radius']
    if axis is None or radius <= 0:
        return None
    # Reversing the source cylinder's direction must not change the result.
    if next(x for x in axis if abs(x) > 1e-14) < 0:
        axis = [-x for x in axis]
    origin = data['origin']
    threshold = min(math.sin(min(inventory['tolerances']['angular'], math.pi / 2)), 1e-12)
    sides = []
    for plane_id in plane_ids:
        plane = faces[plane_id]
        if plane['surface_type'].lower() != 'planar':
            return None
        pd = plane['native_face_data']
        if pd['normal_sense'] not in (-1, 1):
            return None
        normal = _unit(pd['direction'])
        if normal is None:
            return None
        dot = _dot(normal, axis)
        if math.hypot(*(normal[i] - dot * axis[i] for i in range(3))) > threshold:
            return None
        shared = [eid for eid in cylinder['edge_ids'] if eid in plane['edge_ids']
                  and edges[eid]['edge_type'].lower() == 'circular'
                  and len(edges[eid]['face_ids']) == 2
                  and set(edges[eid]['face_ids']) == {face_id, plane_id}]
        if len(shared) != 1:
            return None
        t = _dot([pd['origin'][i] - origin[i] for i in range(3)], axis)
        if not math.isfinite(t):
            return None
        sides.append((t, dot, plane_id, shared[0]))
    sides.sort()
    low, high = sides
    width = high[0] - low[0]
    if (not math.isfinite(width) or width <= inventory['tolerances']['linear']
            or low[1] <= 0 or high[1] >= 0 or low[3] == high[3]):
        return None
    midpoint = low[0] + width / 2
    center = [origin[i] + midpoint * axis[i] for i in range(3)]
    if not all(math.isfinite(x) for x in center):
        return None
    return {'width': width, 'radius': radius, 'axis': axis, 'midplane_axis_point': center,
            'sides': sides}


def recognize(inventory):
    """Return the unique bounded carrier candidate, or [] if none/ambiguous.

    Input is a validated normalized P1 inventory. Values are measured in its
    length units and absolute frame. The two planar directions must face toward
    the slab; the cylinder must have negative sense and share one circular edge
    with each side. Nearly parallel matching is limited to roundoff (1e-12).
    Uniqueness is only within this rule, not among all possible constructions.
    """
    faces, edges = inventory['faces'], inventory['edges']
    matches = []
    for fid, face in faces.items():
        if face['surface_type'].lower() != 'cylindrical':
            continue
        neighbors = set()
        for eid in face['edge_ids']:
            edge = edges[eid]
            if edge['edge_type'].lower() != 'circular' or len(edge['face_ids']) != 2:
                continue
            neighbors.update(other for other in edge['face_ids']
                             if other != fid and faces[other]['surface_type'].lower() == 'planar')
        for pair in combinations(sorted(neighbors), 2):
            region = _region(inventory, fid, pair)
            if region is not None:
                matches.append((fid, pair, region))
    if len(matches) != 1:
        return []
    fid, pair, region = matches[0]
    sources = [fid, *pair]
    source_edges = sorted({eid for face in sources for eid in faces[face]['edge_ids']})
    unit = inventory['unit']
    def parameter(name, value):
        return {'id': name, 'dimension': 'length', 'value': value, 'unit': unit,
                'classification': 'unclassified', 'confirmation': 'unconfirmed'}
    return [{
        'id': 'SLOT-' + fid + '-' + '-'.join(pair),
        'kind': 'possible_finite_cylindrical_slot',
        'snapshot_id': inventory['snapshot_id'],
        'source_faces': sources, 'source_edges': source_edges,
        'evidence': [{'type': 'native_carriers_and_adjacency',
                      'snapshot_id': inventory['snapshot_id'],
                      'cylinder_face': fid, 'side_faces': list(pair),
                      'shared_circular_edges': [side[3] for side in region['sides']],
                      'native_face_data': {f: faces[f]['native_face_data'] for f in sources},
                      'uniqueness': 'one match within this carrier-and-adjacency rule only'}],
        'parameters': [parameter('slot.width', region['width']), parameter('slot.radius', region['radius'])],
        'measured_geometry': {'axis_direction': region['axis'],
                              'midplane_axis_point': region['midplane_axis_point'],
                              'width': region['width'], 'radius': region['radius'], 'unit': unit},
        'alternatives': ['intersection or compound feature with the same carriers'],
        'open_items': ['Full trimmed boundaries and material occupancy are not established by carrier adjacency.',
                       'Construction order, dimensional intent and edit validity require separate evidence.'],
        'capability_requirements': ['complete_trimmed_boundary', 'section_and_material_occupancy',
                                    'human_design_intent_confirmation'],
        'depends_on': [], 'confirmed': False, 'confirmation': {'status': 'unconfirmed'},
    }]
