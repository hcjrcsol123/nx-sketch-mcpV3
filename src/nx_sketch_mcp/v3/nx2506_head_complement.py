"""Finite complementary upper head regions paired with H215 ribbon edges."""
from collections import Counter, defaultdict
from fractions import Fraction as Q
import math

from .nx2506_carrier_bound import upper_float, v, dot
from .nx2506_roll_s7_bound import face_edges, sqrt_bounds
from .nx2506_root_patches import arc_endpoint
from .nx2506_stock_bands import hoop
from .nx2506_stock_c5_patches import endpoint_distance


def mul(interval, factor):
    return tuple(sorted(value*factor for value in interval))


def add(a, b):
    return a[0]+b[0],a[1]+b[1]


def axial_torus_vertex(params, label, point, y, radius):
    prefix=label.rsplit(".",1)[0]+"."
    theta=params[prefix+"theta"]
    aa=(Q(math.cos(float(theta))),Q(0),Q(math.sin(float(theta))))
    ee=(aa[2],Q(0),-aa[0])
    source=v(point)
    measured_s=dot(aa,source)
    if abs(measured_s)<Q("0.00001") or dot(ee,source)<=25:
        raise ValueError("head endpoint did not identify a positive-transverse A branch")
    dd=y-params["head.Y40"]
    rr=radius**2+dd**2
    R,q=params[prefix+"RA"],params[prefix+"ra"]
    # At fixed axial y and fixed global radius, the axial term s^2
    # cancels in (sqrt(rr-s^2)-R)^2+s^2=q^2.
    rho=(rr+R**2-q**2)/(2*R)
    s0,s1=sqrt_bounds(rr-rho**2)
    t0=sqrt_bounds(radius**2-s1**2)[0]
    t1=sqrt_bounds(radius**2-s0**2)[1]
    s=(s0,s1) if measured_s>0 else (-s1,-s0)
    answer=[add(mul(s,aa[0]),mul((t0,t1),ee[0])),
            (y,y),add(mul(s,aa[2]),mul((t0,t1),ee[2]))]
    if endpoint_distance([(q,q) for q in source],answer)>Q("0.000001"):
        raise ValueError("native arc vertex is not on the selected ideal side of the A ribbon")
    return answer


def finite_ring_interface(edge,y,radius,targets):
    g=edge["geometry"]
    if edge["geometry_class"]!=10 or g["type"]!="circular_evaluator" or g["is_periodic"]:
        raise ValueError("expected an original finite circular edge")
    a,b=map(Q,g["evaluator_limits"])
    if not 0<b-a<Q("3"):
        raise ValueError("upper head original arc has unexpected extent")
    first,second=arc_endpoint(g,a),arc_endpoint(g,b)
    endpoint=min(max(endpoint_distance(first,p),endpoint_distance(second,q))
                 for p,q in (targets,list(reversed(targets))))
    if endpoint>Q("0.000001"):
        raise ValueError("head circular evaluator does not pair with the ideal end events")
    u,w=v(g["x_axis"]),v(g["y_axis"])
    basis=abs(dot(u,u)-1)+abs(dot(w,w)-1)+abs(dot(u,w))+abs(u[1])+abs(w[1])
    if basis>Q("0.000000001"):
        raise ValueError("head axial arc does not have a transverse orthonormal frame")
    x,a,z=v(g["center"])
    native_radius=Q(g["radius"])
    support=abs(x)+abs(a-y)+abs(z)+2*abs(native_radius-radius)+8*native_radius*basis
    return 5*support+4*endpoint


def full_ring_error(loop,y,radius):
    actual=hoop(loop,allow_rounded_center=True)
    if actual is None:
        raise ValueError("expected an original complete circular ring")
    ay,r,e=actual
    lo,hi=radius
    return abs(ay-y)+2*max(abs(r-lo),abs(r-hi))+e


def _canonical_fillet_step_vertex(sector, point, y=Q(-16), radius=Q(30)):
    from .nx2506_head_trim import _unit_interval

    axis_x, _, axis_z = _unit_interval(sector['axis_source'])
    x, _, z = map(Q, point)
    measured_s = add(mul(axis_x, x), mul(axis_z, z))
    transverse = add(mul(axis_z, x), mul(axis_x, -z))
    if transverse[0] <= 25 or measured_s[0] <= 0 <= measured_s[1]:
        raise ValueError('fillet vertex does not determine a unique canonical event')
    major = Q(sector['RA_initial_source_binary64'])
    minor = Q(sector['ra_initial_source_binary64'])
    radial_square=radius**2+(y-4)**2
    radial = (radial_square+major**2-minor**2)/(2*major)
    s_bounds = sqrt_bounds(radial_square-radial**2)
    t_bounds = sqrt_bounds(radial**2-(y-4)**2)
    sense = 1 if measured_s[0] > 0 else -1
    s_bounds = mul(s_bounds, sense)

    def product(a,b):
        values = [x*y for x in a for y in b]
        return min(values),max(values)

    return [add(product(s_bounds,axis_x),product(t_bounds,axis_z)),
            (y,y),
            add(product(s_bounds,axis_z),product(mul(t_bounds,-1),axis_x))]


def assess_upper_fillet_patch(capture, supports, loop_binding, facet_capture, drivers, h215):
    """Bound the original filled upper-fillet face to the P3 canonical torus patch."""
    from .nx2506_head_trim import assess_fillet_facet_boundary

    if not h215['status'].startswith('H215 accepted'):
        raise ValueError('accepted canonical P3 head domains required')
    names = {r['face_tag_session_only']:r['p3_support_id'] for r in supports['faces']}
    faces = {r['detail']['face_tag']:r['detail']['topology'] for r in capture['results']}
    face_id, = [tag for tag,name in names.items() if name == 'head.upper_fillet']
    face = faces[face_id]
    binding, = [r for r in loop_binding['faces'] if r['p3_carrier'] == 'head.upper_fillet']
    sectors = {s['A_face']:s for s in drivers['sectors']}
    lower, upper = binding['oriented_neighbor_loops']
    if (lower != ['r40_union'] or len(upper) != 12 or set(upper[1::2]) != set(sectors)
            or set(binding['p3_source_faces']) != {'F0176', 'F0235'}):
        raise ValueError('upper fillet directed annulus does not match the canonical patch')
    geometry = face['geometry']
    x, y, z = map(Q, geometry['center'])
    if geometry['type'] != 204 or x or z or geometry['axis'] not in ([0,1,0], [0,-1,0]):
        raise ValueError('expected a coaxial original torus carrier')
    carrier_delta = (abs(y+Q('18.5')) + abs(Q(geometry['major_radius'])-30)
                     + abs(Q(geometry['minor_radius'])-Q('2.5')))
    lower_loop, = [r for r in face['children'] if len(r['child']['children']) == 1]
    lower_error = full_ring_error(lower_loop, Q(-20), (Q(32), Q(32)))
    adjacent = defaultdict(set)
    for tag, top in faces.items():
        for edge in face_edges(top):
            adjacent[edge['tag']].add(tag)
    at_corner = {}
    arcs = []
    for edge in face_edges(face):
        other, = adjacent[edge['tag']]-{face_id}
        label = names[other]
        if label.endswith('.A_piece'):
            sector = drivers['sectors'][int(label.split('.')[2])]
            for vertex in edge['children']:
                item = vertex['child']
                at_corner[item['local_identifier']] = _canonical_fillet_step_vertex(
                    sector, item['geometry']['point'])
        elif label == 'head.Y_head_step':
            arcs.append(edge)
        elif label != 'head.R40':
            raise ValueError('unexpected upper fillet neighbor')
    if len(at_corner) != 12 or len(arcs) != 6:
        raise ValueError('upper fillet finite step interfaces are incomplete')
    step_error = max(finite_ring_interface(
        edge, Q(-16), Q(30), [at_corner[r['child']['local_identifier']] for r in edge['children']])
        for edge in arcs)
    facet_bounds = assess_fillet_facet_boundary(facet_capture, drivers)
    anchors = {r['role']:r for r in facet_capture['material_anchors']}
    for role, xyz, status in (('inside',(Q('32.5'),Q('-18.5'),Q(0)),1),
                              ('outside',(Q(30),Q(-21),Q(0)),2)):
        entered = anchors[role]
        if (tuple(map(Q,entered['reference_mm'])) != xyz or entered['containment_status'] != status
                or sum(abs(Q(a)-b) for a,b in zip(entered['carrier_point_mm'],xyz)) > Q('0.00000001')):
            raise ValueError('independent native trim anchor classification differs')

    parameter_adjust = Q(0)
    for edge in facet_capture['edges']:
        e = Q(edge['max_vertex_deviation_mm'])
        points = [tuple(map(Q,p)) for p in edge['points_mm']]
        parameters = edge['original_edge_parameters']
        first, last = edge['original_edge_parameter_limits']
        sense = 1 if last > first else -1
        if (len(points) != len(parameters) or parameters[0] != first or parameters[-1] != last
                or any(sense*(b-a) <= 0 for a,b in zip(parameters,parameters[1:]))
                or any(sum((x-y)**2 for x,y in zip(a,b)) <= (2*e)**2 for a,b in zip(points,points[1:]))):
            raise ValueError('original edge does not admit a continuous endpoint-matched chord projection')
        parameter_adjust = max(parameter_adjust,e)
    # Endpoint-matched normalized projection onto each chord moves a point
    # by at most curve_tolerance + max_vertex_deviation. The existing
    # chord-to-P3 proof uses continuous affine matching in the A chart.
    ribbon_error = Q(facet_bounds['original_to_canonical_edge_upper_mm']) + parameter_adjust
    # Use a common torus in theta/phi. For two points on it, d² is
    # 4*r1*r2*sin²(dtheta/2) + 4*q²*sin²(dphi/2). The straight path in
    # the angle chart has speed bounded by r<=32.5 and q=2.5.
    boundary_delta = max(lower_error, step_error, ribbon_error) + carrier_delta
    if boundary_delta >= Q('0.001'):
        raise ValueError('boundary pairing outside the small-angle metric bound')
    # At d<1e-3, both half angles are <1e-3 and x/sin(x)<1.000001.
    path_factor = Q(13,11)*Q('1.000001')
    surface_delta = path_factor*boundary_delta + carrier_delta
    source_delta = Q('0.000859') + surface_delta
    return {'schema':'p4-upper-fillet-finite-patch/1',
            'status':'within_limit' if surface_delta<=Q('0.00025') and source_delta<=Q('0.001') else 'bound_exceeds_limit',
            'source_faces':['F0176','F0235'],
            'native_carrier_transport_mm':upper_float(carrier_delta),
            'lower_original_ring_upper_mm':upper_float(lower_error),
            'six_original_step_arcs_upper_mm':upper_float(step_error),
            'six_A_trim_pointwise_pairing_upper_mm':upper_float(ribbon_error),
            'continuous_bidirectional_patch_upper_mm':upper_float(surface_delta),
            'p3_global_plus_this_patch_upper_mm':upper_float(source_delta),
            'material_anchors':anchors,
            'scope':'The complete retained upper R2.5 fillet face, including both trim loops, with C14 face-boundary and curve tolerance semantics as documented by NX.',
            'proof':('Transport the original carrier to the canonical torus at unchanged angles. '
                     'Pair complete oriented boundaries and move each pair along a short torus path. '
                     'The canonical anchor at Y=-18.5 lies between the contact ring at Y=-20 and '
                     'the upper outline above Y=-17.2; native UV containment agrees. '
                     'Off the swept boundary the inside label is constant by relative winding from '
                     'the common anchor. Any point that changes inside/outside is within one path '
                     'length of both boundaries. This establishes the two filled-domain directions.'),
            'execution_approved':False}


def assess_head_complement(capture,supports,plan,ribbon_edges,sphere_arcs):
    if ribbon_edges["face_edge_incidence_count"]!=96 or sphere_arcs["count"]!=12:
        raise ValueError("all head ribbon boundaries and original sphere arcs must be available")
    p={row["id"]:Q(row["value"]) for row in plan["parameters"]["regional"]}
    faces={r["detail"]["face_tag"]:r["detail"]["topology"] for r in capture["results"]}
    names={f["face_tag_session_only"]:f["p3_support_id"] for f in supports["faces"]}
    carrier={f["face_tag_session_only"]:Q(f["distance_upper_mm"]) for f in supports["faces"]}
    adjacent=defaultdict(set)
    outer_a_at_vertex=defaultdict(set)
    all_edges={}
    for key,face in faces.items():
        for e in face_edges(face):
            all_edges[e["tag"]]=e
            adjacent[e["tag"]].add(key)
            if names[key].endswith(".A_piece"):
                for vertex in e["children"]:
                    outer_a_at_vertex[vertex["child"]["local_identifier"]].add(names[key])

    # The remaining arcs at Y=-16 and Y=17 terminate on analytic A tori.
    pairs={
       frozenset(("head.upper_fillet","head.Y_head_step")):
            (p["head.Y_head_step"],p["head.upper_fillet_major"]),
       frozenset(("head.cone","stock.s20")):
            (p["stock.Y_mouth"],(p["stock.Y_mouth"]-p["head.cone_apex_Y"])*
                                      Q(math.tan(float(p["head.cone_half_angle_initial_exact"])))),
    }
    arcs={}
    for id,parents in adjacent.items():
        group=frozenset(names[i] for i in parents)
        if group not in pairs:
            continue
        y,r=pairs[group]
        edge=all_edges[id]
        ideal=[]
        for item in edge["children"]:
            vertex=item["child"]
            a,=outer_a_at_vertex[vertex["local_identifier"]]
            ideal.append(axial_torus_vertex(p,a,vertex["geometry"]["point"],y,r))
        if len(ideal)!=2:
            raise ValueError("expected two finite A-intersection endpoints")
        arcs[id]=finite_ring_interface(edge,y,r,ideal)
    if len(arcs)!=12:
        raise ValueError("incomplete upper fillet-step or mouth-cone original arcs")

    limits=defaultdict(list)
    for row in ribbon_edges["edges"]:
        limits[row["native_edge"]].append(Q(row["conditional_edge_upper_mm"]))
    for row in sphere_arcs["arcs"]:
        limits[row["native_edge"]].append(Q(row["native_to_h215_ideal_arc_upper_mm"]))
    for key,bound in arcs.items():
        limits[key].append(bound)

    y40=p["head.Y40"]
    r40=p["head.R40"]
    contact=p["head.upper_sphere_contact_y"]
    upper_r40=sqrt_bounds(r40*r40-(contact-y40)**2)
    plan_stock=plan["construction"]["profiles"]["stock_profile"]
    vertices={row["id"]:row for row in plan_stock["vertices"]}
    end=next(c for c in plan_stock["curves"] if c["id"]=="s20")
    mouth_outer=max(Q(vertices[end[k]]["radius_mm"]) for k in ("start","end"))

    results=[]
    for id,name in names.items():
        if name not in ("head.cone","head.Y_head_step","head.R32","head.upper_fillet","stock.s20"):
            continue
        top=faces[id]
        edges=list(face_edges(top))
        neighbors=[names[next(iter(adjacent[e["tag"]]-{id}))] for e in edges]
        classes=Counter("A" if x.endswith(".A_piece") else "B" if x.endswith(".B_piece") else x for x in neighbors)
        expected={
            "head.R32": {"B":2,"head.Y_head_step":1,"head.cone":1},
            "head.cone":{"A":2,"B":2,"stock.s20":1,"head.R32":1},
            "head.Y_head_step":{"A":2,"B":2,"head.upper_fillet":1,"head.R32":1},
            "head.upper_fillet":{"head.R40":1,"head.Y_head_step":6,"A":6},
            "stock.s20":{"head.cone":6,"A":6,"stock.s19":1},
        }
        if classes!=Counter(expected[name]):
            raise ValueError("upper head finite loop incidence disagrees with the mapped ribbons")
        loop_count=2 if name in ("head.upper_fillet","stock.s20") else 1
        if len(top["children"])!=loop_count:
            raise ValueError("upper head face loop multiplicity differs")
        for edge,other in zip(edges,neighbors):
            if other not in ("head.R40","stock.s19"):
                continue
            y,rr=(contact,upper_r40) if other=="head.R40" else (p["stock.Y_mouth"],(mouth_outer,mouth_outer))
            selected,=[loop for loop in top["children"] if len(loop["child"]["children"])==1]
            limits[edge["tag"]].append(full_ring_error(selected,y,rr))
        eps=max(max(limits[e["tag"]]) for e in edges)
        # Common projected domains with complete paired oriented loops.
        # Sphere/cone: (30*azimuth,Y), projection <=3 and lift <=4.
        # Upper torus: (30*azimuth,3*meridian angle), projection <=4, lift <=2.
        # Plane: Cartesian chart, projection and lift ==1.
        factor=24 if name in ("head.R32","head.cone") else 16 if name=="head.upper_fillet" else 2
        results.append({"face_tag_session_only":id,"p3_support_id":name,
                        "boundary_correspondence_upper_mm":upper_float(eps),
                        "conditional_patch_upper_mm":upper_float(factor*eps+carrier[id])})
    if len(results)!=20:
        raise ValueError("incomplete upper head counterpart face inventory")
    return {"schema":"p4-upper-head-complement-conditional-finite-patches/1","face_count":len(results),
            "max_class10_upper_fillet_and_mouth_arc_upper_mm":upper_float(max(arcs.values())),
            "maximum_conditional_patch_upper_mm":max(r["conditional_patch_upper_mm"] for r in results),
            "scope":"20 complementary finite patches, conditional on H215 ideal occupancy, original kernel edge/FIN semantics, paired directed loop winding and the stated ribbon bounds.",
            "method":"Exact endpoint evaluation on axial arcs, directed loop incidence checks, and chart boundary-layer fill bounds.",
            "execution_approved":False,"faces":results}


def _clear_from_head_tori(point, drivers):
    from .nx2506_head_ribbon_acceptance import _contact, _geometry, _interval
    from .nx2506_head_trim import _unit_interval
    from .root_exit_certificate import I

    x,y,z=map(I.of,point)
    collar=Q('.001')
    for sector in drivers['sectors']:
        a,_,b=(_interval(p) for p in _unit_interval(sector['axis_source']))
        s=a*x+b*z
        t=b*x-a*z
        if t.hi < -collar:
            continue
        positive,negative=(_contact(sector,j)[0] for j in (0,1))
        rho=(t.square()+(y-4).square()).sqrt()
        for branch in (None,0,1):
            if (branch is None and ((s-positive).lo>collar or (negative-s).lo>collar)
                    or branch==0 and (positive-s).lo>collar
                    or branch==1 and (s-negative).lo>collar):
                continue
            d,M,q=_geometry(sector,branch)
            clearance=(rho-M).square()+(s-d).square()-q.square()
            if clearance.lo<=Q('.05'):
                return False
    return True


def _complement_anchor(role, rows, drivers, stock):
    from .root_exit_certificate import I

    radius_at_minus16=stock['R14']+(I.of(-16)-stock['Y14'])*(
        (stock['R15']-stock['R14'])/(stock['Y15']-stock['Y14']))
    if not stock['Y14'].hi<-16<stock['Y15'].lo or min(radius_at_minus16.lo,stock['R17'].lo,
                                                        stock['R19'].lo,stock['M19'].lo)<43:
        raise ValueError('canonical head witness exceeds the proven stock enclosure')
    for row in rows:
        p=v(row['point_mm'])
        if row['native_inside_trim_status']!=1:
            continue
        radial=(I.of(p[0]).square()+I.of(p[2]).square()).sqrt()
        if radial.lo<27 or radial.hi>45:
            continue
        y=I.of(p[1])
        if role=='head.Y_head_step':
            y=I.of(-16)
            sphere=(1024-y.square()).sqrt()
            accepted=(radial-sphere).lo>Q('.001') and (30-radial).lo>Q('.001')
        elif role=='stock.s20':
            y=I.of(17)
            # A full ring on the mouth plane lies outside the cutter and
            # inside the exact stock outer radius.
            accepted=radial.lo>40 and (stock['R19']-radial).lo>Q('.001')
        else:
            if not Q('-15.999')<Q(y.lo)<=Q(y.hi)<Q('16.999') or radial.hi>=43:
                continue
            sphere=(1024-y.square()).sqrt()
            cone=y+Q('17.5')
            accepted=((sphere-cone).lo>Q('.001') if role=='head.R32' else (cone-sphere).lo>Q('.001'))
        if accepted and _clear_from_head_tori((p[0],Q(y.lo),p[2]),drivers):
            return row
    raise ValueError('no strict common original/canonical material witness for '+role)


def verify_head_complement_faces(capture,supports,plan,binding,drivers,ribbons,sphere,fillet,anchors):
    """Complete the nineteen complementary head faces using their accepted shared trim edges."""
    from .nx2506_carrier_bound import tangent_range
    from .nx2506_stock_bands import _exact_stock_parameters

    if any(r['status']!='within_limit' for r in (ribbons,fillet)):
        raise ValueError('all shared original ribbon and upper fillet trims are required')
    if anchors.get('schema')!='p4-native-head-complement-anchors/1' or anchors.get('disk_copy_unchanged') is not True:
        raise ValueError('original native complement witnesses are required')
    points=anchors['faces']
    names={r['face_tag_session_only']:r['p3_support_id'] for r in supports['faces']}
    geometry={r['detail']['face_tag']:r['detail']['topology'] for r in capture['results']}
    counterparts={r['face_tag_session_only']:r for r in binding['faces'] if r['p3_carrier']!='head.upper_fillet'}
    if len(counterparts)!=19 or set(map(str,counterparts))!=set(points):
        raise ValueError('original complement face correspondence is incomplete')
    adjacent=defaultdict(set)
    canonical_mouth={}
    for tag,face in geometry.items():
        for e in face_edges(face):
            adjacent[e['tag']].add(tag)
            if names[tag].endswith('.A_piece'):
                sector=drivers['sectors'][int(names[tag].split('.')[2])]
                for entry in e['children']:
                    node=entry['child']
                    if abs(node['geometry']['point'][1]-17)<1e-8:
                        canonical_mouth[node['local_identifier']]=_canonical_fillet_step_vertex(
                            sector,node['geometry']['point'],Q(17),Q('34.5'))
    ribbons_side={}
    for row in ribbons['faces']:
        for edge in row['edge_proofs']:
            key=edge['edge_in_c14_brep_inventory']
            ribbons_side[key]=max(Q(edge['continuous_pointwise_pairing_upper_mm']),ribbons_side.get(key,0))
    sphere_arcs={r['native_edge']:Q(r['native_to_h215_ideal_arc_upper_mm']) for r in sphere['arcs']}
    fillet_arcs=Q(fillet['six_original_step_arcs_upper_mm'])
    stock=_exact_stock_parameters(plan)
    mouth_delta=max(abs(Q(v)-17) for v in (stock['Y_mouth'].lo,stock['Y_mouth'].hi))
    if mouth_delta>Q('0.000000001'):
        raise ValueError('canonical stock mouth does not agree with the accepted exact head station')
    # Outward stock arithmetic encloses the independently accepted Y=17.
    # Its tiny interval width is transferred through the existing head
    # chart speeds and the paired finite axial endpoints.
    endpoint_transfer=80*mouth_delta
    output=[]
    for tag,related in sorted(counterparts.items()):
        name=names[tag]
        face=geometry[tag]
        g=face['geometry']
        if name=='head.R32':
            if g['type']!=203:
                raise ValueError('expected original sphere')
            transport=sum(map(abs,map(Q,g['center'])))+abs(Q(g['radius'])-32)
        elif name=='head.cone':
            if g['type']!=202 or g['axis']!=[0,1,0] or g['point_at_apex'][::2]!=[0,0]:
                raise ValueError('expected original positive coaxial head cone')
            apex=Q(g['point_at_apex'][1])
            slopes=tangent_range(Q(g['half_apex_angle']))
            transport=max(abs((y-apex)*s-y-Q('17.5')) for s in slopes for y in (12,17))
        else:
            y=Q(-16) if name=='head.Y_head_step' else Q(17)
            if g['type']!=209 or g['normal'] not in ([0,1,0],[0,-1,0]):
                raise ValueError('expected original axial head plane')
            transport=abs(Q(g['point_on_plane'][1])-y)
        bounds=[]
        for e in face_edges(face):
            ident=e['tag']
            other,=adjacent[ident]-{tag}
            neighbor=names[other]
            if ident in ribbons_side:
                upper=ribbons_side[ident]
            elif ident in sphere_arcs:
                upper=sphere_arcs[ident]
            elif neighbor=='head.upper_fillet' and name=='head.Y_head_step':
                upper=fillet_arcs
            elif {name,neighbor}=={'head.cone','stock.s20'}:
                targets=[canonical_mouth[r['child']['local_identifier']] for r in e['children']]
                upper=finite_ring_interface(e,Q(17),Q('34.5'),targets)
            elif neighbor=='stock.s19' and name=='stock.s20':
                one,=[r for r in face['children'] if len(r['child']['children'])==1]
                canonical=stock['R19']
                upper=full_ring_error(one,Q(17),(Q(canonical.lo),Q(canonical.hi)))
            else:
                raise ValueError('missing original complement boundary proof: '+str((name,neighbor,ident)))
            bounds.append(upper)
        boundary=max(bounds)+transport+endpoint_transfer
        if boundary>=Q('.001'):
            raise ValueError('complement edge correspondence outside the short carrier path bound')
        anchor=_complement_anchor(name,points[str(tag)],drivers,stock)
        # Great-circle transport, conical angular/meridian transport, or
        # planar interpolation stays within 1.0001 times the chord on these
        # small matching intervals (radius >27). The oriented loops share a
        # strict material witness outside the swept boundary tube.
        upper=Q('1.0001')*boundary+transport
        output.append({'p3_support_id':name,'p3_source_faces':related['p3_source_faces'],
                       'native_face_in_c14_brep_inventory':tag,'material_witness':anchor,
                       'boundary_pointwise_upper_mm':upper_float(boundary),
                       'continuous_bidirectional_patch_upper_mm':upper_float(upper),
                       'status':'within_limit' if upper<=Q('.000141') else 'bound_exceeds_limit'})
    return {'schema':'p4-native-head-complement-finite-faces/1','faces':output,'face_count':len(output),
            'status':'within_limit' if all(r['status']=='within_limit' for r in output) else 'bound_exceeds_limit',
            'continuous_bidirectional_patch_upper_mm':max(r['continuous_bidirectional_patch_upper_mm'] for r in output),
            'scope':'Six spherical, six conical, six step, and one mouth original head/stock faces with paired complete loops.',
            'execution_approved':False}
