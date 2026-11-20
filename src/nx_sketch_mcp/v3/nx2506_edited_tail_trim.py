"""Finite original NX tail verification at one deliberate edit point."""
from collections import defaultdict
from fractions import Fraction as Q

from .nx2506_carrier_bound import dot, upper_float, v
from .nx2506_edit_domain import EDITED_DIRECTION_LIMIT_MM
from .nx2506_roll_s7_bound import face_edges
from .nx2506_root_patches import arc_endpoint
from .nx2506_stock_bands import _exact_stock_parameters, hoop
from .nx2506_stock_c5_patches import axial_circle_bound
from .root_exit_certificate import I


def _span(interval):
    value=I.of(interval)
    return Q(value.lo),Q(value.hi)


def _point(*coords):
    return tuple(_span(v_) for v_ in coords)


def _gap(a,b):
    return sum(max(abs(x-y) for x in p for y in q) for p,q in zip(a,b))


def _pair_error(a,b):
    return min(max(_gap(x,y) for x,y in zip(a,order)) for order in (b,b[::-1]))


def _centre(interval):
    return sum(_span(interval))/2


def _shape(plan,driver_values):
    stock=_exact_stock_parameters(plan)
    slot={k.removeprefix('slot.'):I.of(Q(v)) for k,v in driver_values.items() if k.startswith('slot.')}
    a=slot['width']/2
    ay,az,radius=slot['axis_y'],slot['axis_z'],slot['radius']
    def cutter(y):
        return az-(radius.square()-(I.of(y)-ay).square()).sqrt()
    def exit_y(z):
        return ay+(radius.square()-(az-z).square()).sqrt()
    def clip(r):
        return (r.square()-a.square()).sqrt()
    return stock,a,ay,az,radius,cutter,exit_y,clip


def _implicit_edge(row,graph,interval,index,curvature):
    points=[v(p) for p in row['points_mm']]
    if points[0][index]>points[-1][index]:
        points.reverse()
    coordinates=[p[index] for p in points]
    increments=[b-a for a,b in zip(coordinates,coordinates[1:])]
    tau,vertex=Q(row['chord_tolerance_mm']),Q(row['max_vertex_deviation_mm'])
    if (min(increments)<=0 or Q(row['max_midpoint_deviation_mm'])>tau or any(
            sum((a-b)**2 for a,b in zip(x,y))<=(2*vertex)**2 for x,y in zip(points,points[1:]))):
        raise ValueError('edited original tail facet chain is not a continuous graph')
    err=max(_gap(tuple((q,q) for q in p),graph(t)) for p,t in zip(points,coordinates))
    endpoints=max(abs(x-y) for x,i in zip((coordinates[0],coordinates[-1]),interval) for y in i)
    # Linear interpolation bound and affine finite endpoint pairing at
    # the selected graph speed. Add original NX edge coverage and vertex
    # adjustment once, by the ordered correspondence.
    return err+curvature*max(increments)**2/8+5*endpoints+tau+vertex


def _arc_bound(edge,center,rad,pair):
    g=edge['geometry']
    if edge['geometry_class']!=10 or g['type']!='circular_evaluator' or g['is_periodic']:
        raise ValueError('expected original finite edited cutter side arc')
    a,b=map(Q,g['evaluator_limits'])
    if not 0<b-a<2:
        raise ValueError('edited cutter circle did not select the lower branch')
    arc=Q(g['radius'])
    x,y=v(g['x_axis']),v(g['y_axis'])
    frame=abs(dot(x,x)-1)+abs(dot(y,y)-1)+abs(dot(x,y))+abs(x[0])+abs(y[0])
    support=_gap(_point(*g['center']),center)+2*max(abs(arc-v) for v in _span(rad))+8*arc*frame
    ends=_pair_error([arc_endpoint(g,a),arc_endpoint(g,b)],pair)
    if support+ends>=Q('.001'):
        raise ValueError('edited side arc assignment outside its short-angle enclosure')
    return 5*support+4*ends


def verify_edited_tail(capture,carriers,plan,driver_values,native):
    if (native.get('schema')!='p4-native-edited-tail-facets/1' or native.get('status')!='complete'
            or not native.get('disk_copy_unchanged')):
        raise ValueError('complete original edited tail material and facet evidence required')
    rows=native['faces']
    role_set={'tail.left_wall','tail.right_wall','tail.cylinder','stock.bottom_closure',
              'stock.s1','stock.s2','stock.s3','stock.s4'}
    if set(rows)!=role_set:
        raise ValueError('edited tail face coverage differs')
    s,a,ay,az,radius,cutter,exit_y,clip=_shape(plan,driver_values)
    R0,R1,R3=s['R0'],s['R1'],s['R3']
    Y0,Y1,Y2,Y3,Y4=(s['Y'+str(i)] for i in range(5))
    z0,z1,z3=map(clip,(R0,R1,R3))
    cutter0=cutter(Y0)
    tail_exit=exit_y(z3)
    rings={
        frozenset(('stock.bottom_closure','stock.s1')):(Y0,R0,z0),
        frozenset(('stock.s1','stock.s2')):(Y1,R1,z1),
        frozenset(('stock.s2','stock.s3')):(Y2,R1,z1),
        frozenset(('stock.s3','stock.s4')):(Y3,R3,z3),
    }
    lines={frozenset(('tail.cylinder','stock.bottom_closure')):
           (_point(-a,Y0,cutter0),_point(a,Y0,cutter0))}
    cut_arcs={}
    for key,x in (('tail.left_wall',-a),('tail.right_wall',a)):
        lines[frozenset((key,'stock.bottom_closure'))]=(_point(x,Y0,cutter0),_point(x,Y0,z0))
        lines[frozenset((key,'stock.s2'))]=(_point(x,Y1,z1),_point(x,Y2,z1))
        lines[frozenset((key,'stock.s4'))]=(_point(x,Y3,z3),_point(x,tail_exit,z3))
        cut_arcs[frozenset((key,'tail.cylinder'))]=(_point(x,ay,az),(_point(x,Y0,cutter0),_point(x,tail_exit,z3)))
    implicit={}
    for role,row in rows.items():
        for e in row['edges']:
            neighbor=e['neighbor']
            if role=='tail.cylinder' and neighbor=='stock.s4':
                def graph(x):
                    z=(R3.square()-I.of(x).square()).sqrt()
                    return _point(x,exit_y(z),z)
                x_extent=max(abs(Q(p[0])) for p in e['points_mm'])
                zmin=Q((R3.square()-I.of(x_extent).square()).sqrt().lo)
                root_min=(radius.square()-(az-I.of(zmin)).square()).sqrt()
                # z_xx=-R3²/z³ and Y_zz=-Rslot²/D³ (D positive).
                if zmin<Q('8.6') or root_min.lo<=16:
                    raise ValueError('edited tail cylinder exit left the expected branch')
                zsecond=Q(R3.hi)**2/zmin**3
                zfirst=Q(a.hi)/zmin
                gain=(Q(az.hi)-zmin)/Q(root_min.lo)
                curvature=zsecond*(1+gain)+Q(radius.hi)**2*zfirst*zfirst/Q(root_min.lo)**3
                value=_implicit_edge(e,graph,(_span(-a),_span(a)),0,curvature)
            elif role in ('tail.left_wall','tail.right_wall') and neighbor in ('stock.s1','stock.s3'):
                x=-a if role.endswith('left_wall') else a
                lo,hi,radlo,radhi=(Y0,Y1,R0,R1) if neighbor=='stock.s1' else (Y2,Y3,R1,R3)
                slope=(radhi-radlo)/(hi-lo)
                def graph(y):
                    Ro=radlo+(I.of(y)-lo)*slope
                    return _point(x,y,clip(Ro))
                y_min=min(Q(p[1]) for p in e['points_mm'])
                zmin=Q(clip(radlo+(I.of(y_min)-lo)*slope).lo)
                curvature=Q(a.hi)**2*Q(slope.hi)**2/zmin**3
                value=_implicit_edge(e,graph,(_span(lo),_span(hi)),1,curvature)
            else:
                raise ValueError('unrecognized original edited tail intersection phase')
            implicit[e['edge_tag_in_edited_capture']]=value
    if len(implicit)!=5:
        raise ValueError('incomplete original edited tail intersection edges')
    labels={r['face_tag_session_only']:r for r in carriers['faces']}
    faces={r['detail']['face_tag']:r['detail']['topology'] for r in capture['results']}
    adjacency=defaultdict(set)
    for tag,raw in faces.items():
        for e in face_edges(raw):
            adjacency[e['tag']].add(tag)
    result=[]
    for tag,record in labels.items():
        role=record['p3_support_id']
        if role not in role_set:
            continue
        anchors=rows[role]['material_anchors']
        if [r['containment_status'] for r in anchors]!=[1,2] or any(
                sum(abs(Q(a)-Q(b)) for a,b in zip(p['reference_mm'],p['carrier_point_mm']))>Q('0.00000001')
                for p in anchors):
            raise ValueError('edited tail original material-side witness differs')
        edges=[]
        for e in face_edges(faces[tag]):
            other,=adjacency[e['tag']]-{tag}
            pair=frozenset((role,labels[other]['p3_support_id']))
            if e['tag'] in implicit:
                upper=implicit[e['tag']]
            elif pair in rings:
                y,r,z=rings[pair]
                upper=axial_circle_bound(e,_centre(y),_centre(r),
                                       (_point(-a,y,z),_point(a,y,z)),
                                       angular_interval=(Q(4),Q(7)),endpoint_limit=Q('.0001'))
            elif pair in lines:
                g=e['geometry']
                if e['geometry_class']!=10 or g['type']!=101:
                    raise ValueError('edited tail guide changed from an original finite line')
                upper=_pair_error([_point(*g[k]) for k in ('start','end')],lines[pair])
            elif pair in cut_arcs:
                center,p= cut_arcs[pair]
                upper=_arc_bound(e,center,radius,p)
            elif pair=={'stock.s4','stock.s5'}:
                ring,=[r for r in faces[tag]['children'] if len(r['child']['children'])==1]
                iy,ir,frame=hoop(ring)
                upper=max(abs(iy-x) for x in _span(Y4))+max(abs(ir-x) for x in _span(R3))+frame
            else:
                raise ValueError('missing edited tail oriented edge counterpart: '+str(pair))
            edges.append(upper)
        carrier=Q(record['distance_upper_mm'])
        boundary=max(edges)+carrier
        if boundary>=Q('.001'):
            raise ValueError('edited tail boundary displacement outside its local carrier collar')
        # The same-axis angular chart is near-isometric for matched chord
        # gaps <.001 on the edited cylinders and cones (r>6.8). A plane
        # takes the short linear pairing. Native inside and outside trim
        # witnesses select the same P3 finite region; swept loops cover
        # the changed region in both directions.
        upper=Q('1.0002')*boundary+carrier
        result.append({'p3_support_id':role,'continuous_bidirectional_patch_upper_mm':upper_float(upper),
                       'status':'within_limit' if upper<=EDITED_DIRECTION_LIMIT_MM else 'bound_exceeds_limit'})
    maximum=max(row['continuous_bidirectional_patch_upper_mm'] for row in result)
    return {'schema':'p4-edited-original-tail-finite-patches/1','faces':result,'face_count':len(result),
            'status':'within_limit' if all(row['status']=='within_limit' for row in result) else 'bound_exceeds_limit',
            'continuous_bidirectional_patch_upper_mm':maximum,'execution_approved':False}
