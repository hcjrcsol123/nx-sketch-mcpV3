"""Conditional finite stock patches bounded by the certified C5 cut wires."""
from collections import defaultdict
from fractions import Fraction as Q

from .nx2506_carrier_bound import dot, v, upper_float
from .nx2506_root_patches import arc_endpoint
from .nx2506_roll_s7_bound import nominal, face_edges, s8_constants, sqrt_bounds
from .nx2506_trim_bound import _curve, _controls, _bernstein_matrix_inverse, _evaluate


def cyclic_match(actual,expected):
    if len(actual)!=len(expected):
        return False
    doubled=actual+actual
    return any(doubled[i:i+len(actual)]==expected
               or doubled[i:i+len(actual)]==expected[::-1] for i in range(len(actual)))


def endpoint_distance(a,b):
    return sum(max(abs(x-y) for x in pair for y in target) for pair,target in zip(a,b))


def axial_circle_bound(edge,y,r,pair,angular_interval=(Q(0),Q("0.3")),endpoint_limit=Q("0.00001")):
    g=edge["geometry"]
    transverse_center=abs(Q(g["center"][0]))+abs(Q(g["center"][2]))
    if (edge["geometry_class"]!=10 or g["type"]!="circular_evaluator"
            or g["is_periodic"] or transverse_center>Q("0.000000001")):
        raise ValueError("expected the short original stock interface arc")
    a,b=map(Q,g["evaluator_limits"])
    if not angular_interval[0]<b-a<angular_interval[1]:
        raise ValueError("stock interface did not select the expected angular interval")
    u,w=v(g["x_axis"]),v(g["y_axis"])
    basis_error=(abs(sum(x*x for x in u)-1)+abs(sum(x*x for x in w)-1)
                 +abs(sum(x*y for x,y in zip(u,w)))+abs(u[1])+abs(w[1]))
    first,second=arc_endpoint(g,a),arc_endpoint(g,b)
    endpoint_error=min(max(endpoint_distance(first,p),endpoint_distance(second,q))
                        for p,q in (pair,list(reversed(pair))))
    if endpoint_error>endpoint_limit or basis_error>Q("0.000000001"):
        raise ValueError("native seam arc endpoint pair disagrees with the P3 ideal ring")
    circle_error=transverse_center+abs(Q(g["center"][1])-y)+2*abs(Q(g["radius"])-r)+8*Q(g["radius"])*basis_error
    return 5*circle_error+4*endpoint_error


def nominal_upper_vertices(plan):
    nodes={r["id"]:r for r in plan["construction"]["nodes"]}
    p={r["id"]:Q(r["value"]) for r in plan["parameters"]["regional"]}
    q=plan["construction"]["profiles"]["section6"]["templates"]
    result={}
    for i in range(22):
        member=f"member_{i:02d}"
        frame=nodes[member+"_straight_tool"]["frame"]
        a,b=v(frame["e_t"]),v(frame["e_r"])
        for side,template in q.items():
            end=template["endpoints"]["outer"]
            t,r=(Q(end[k]["value"]) for k in ("t_mm","r_mm"))
            xz=(t*a[0]+r*b[0],p["stock.Y6"],t*a[2]+r*b[2])
            result[member+"."+side]=tuple((p,p) for p in xz)
    return result


def transition_transport(plan,late,radius_error):
    # Across the ideal C5 FIN spans the signs of t and |t|' agree with r
    # increasing toward the outer endpoint (or all decrease in reverse).
    # At the shared Y7 station this gives |F_u| >= 2*11*.65 > 14, where
    # F=t^2+n^2-Rshaft^2 and n=15-sqrt(lambda^2-v^2).
    templates=plan["construction"]["profiles"]["section6"]["templates"]
    for name,template in templates.items():
        c=_curve(nominal(template))
        cuts=sorted({Q(0),Q(1)}|{(k-c["a"])/(c["b"]-c["a"])
                      for k in c["knots"] if c["a"]<k<c["b"]})
        matrix=_bernstein_matrix_inverse(3)
        for a,b in zip(cuts,cuts[1:]):
            controls=_controls(c,a,b,matrix)
            dt=[3*(v[0]-u[0])/(b-a) for u,v in zip(controls,controls[1:])]
            dl=[3*(v[1]-u[1])/(b-a) for u,v in zip(controls,controls[1:])]
            lo,hi=min(r[0] for r in controls),max(r[0] for r in controls)
            if not all(-1<=v<=Q('-.8') for v in dt):
                raise ValueError("C5 tangential derivative envelope changed")
            if name=="F0002":
                ok=lo>0 and all(Q('0.65')<=v<=Q('0.9') for v in dl)
            else:
                ok=hi<0 and all(Q('-.9')<=v<=Q('-.65') for v in dl)
            if not ok:
                raise ValueError("C5 transition is not monotone in its common chart")
    # At the shared station add the observed cylinder/torus radius errors
    # to the s8 field difference (height certificate denominator 5).
    field=5*Q(late["maximum_height_difference_upper_mm"])+28*radius_error
    delta_u=field/14
    # Re-align only in a short neighborhood with 1.2<=v<=1.27. |F_u|<58
    # and F_v>=5, and the position Lipschitz speed along the exit is <40.
    if delta_u>=Q("0.0000001") or 12*delta_u>=Q("0.001"):
        raise ValueError("s7/s8 splice shift exceeds the local transport neighborhood")
    return 40*delta_u


def assess_c5_stock_patches(capture,supports,plan,straight,roll,root,bands,late,events):
    names={row["face_tag_session_only"]:row["p3_support_id"] for row in supports["faces"]}
    carrier={row["face_tag_session_only"]:Q(row["distance_upper_mm"]) for row in supports["faces"]}
    face={r["detail"]["face_tag"]:r["detail"]["topology"] for r in capture["results"]}
    neighbors=defaultdict(set)
    for tag,t in face.items():
        for e in face_edges(t):
            neighbors[e["tag"]].add(tag)
    def neighbor(e,tag):
        other,=neighbors[e["tag"]]-{tag}
        return other
    known={}
    for data,key in ((straight,"conditional_patch_l1_upper_mm"),(roll,"conditional_patch_upper_mm"),
                     (root,"conditional_patch_upper_mm"),(bands,"conditional_finite_band_upper_mm")):
        for row in data["faces"]:
            if key in row:
                value=row[key]
                if isinstance(value,dict):
                    value=value["upper_mm"]
                known[row["face_tag_session_only"]]=Q(value)
    p={r["id"]:Q(r["value"]) for r in plan["parameters"]["regional"]}
    lower=nominal_upper_vertices(plan)
    upper={f"member_{i:02d}."+row["side"]:tuple(tuple(map(Q,p)) for p in row["candidate_event_xyz_interval_mm"])
           for row in events["rows"] for i in (row["member_index"],)}
    if len(upper)!=44:
        raise ValueError("complete P3 transition endpoint intervals required")
    R8error,_,geometry=s8_constants(plan,capture,supports)
    R7error=max(abs(Q(geometry[tag]["radius"])-p["stock.Rshaft"]) for tag,name in names.items()
                if name=="stock.s7")
    transport=transition_transport(plan,late,R8error+R7error)
    ready=[]
    interfaces={}
    for tag,name in names.items():
        if name!="stock.s7":
            continue
        topo=face[tag]
        if len(topo["children"])!=1:
            raise ValueError("s7 finite region should have one connected loop")
        edges=list(face_edges(topo))
        keys=[names[neighbor(e,tag)] for e in edges]
        first,=[k for k in keys if k.endswith(".F0002.linear")]
        second,=[k for k in keys if k.endswith(".F0024.linear")]
        i=int(first.split(".")[0][-2:])
        if int(second.split(".")[0][-2:])!=(i+1)%22:
            raise ValueError("s7 finite patch does not separate consecutive cutter sectors")
        A,B=(k.rsplit(".",1)[0] for k in (first,second))
        order=[B+".linear",B+".roll","stock.s8",A+".roll",A+".linear","stock.s6"]
        if not cyclic_match(keys,order):
            raise ValueError("s7 finite loop incidence disagrees with the ideal")
        for e,k in zip(edges,keys):
            if k in ("stock.s6","stock.s8"):
                y=p["stock.Y6"] if k=="stock.s6" else p["stock.Y7"]
                coords=lower if k=="stock.s6" else upper
                interfaces[e["tag"]]=axial_circle_bound(e,y,p["stock.Rshaft"],(coords[A],coords[B]))
        ready.append((tag,edges))
    if len(ready)!=22 or len(interfaces)!=44:
        raise ValueError("expected all 22 pairs of original C5 stock interface arcs")
    loops_needed=([f"member_{i:02d}.{k}" for i in range(22) for k in
                   ("F0002.linear","straight_root","F0024.linear","__ARC__")],
                  [f"member_{i:02d}.{k}" for i in range(22) for k in
                   ("F0024.roll","roll_root","F0002.roll","__ARC__")])
    for name,sibling,index in (("stock.s6","stock.s5",0),("stock.s8","stock.s9",1)):
        tag,=[i for i,k in names.items() if k==name]
        orders=[]
        for loop in face[tag]["children"]:
            order=[names[neighbor(fc["child"]["children"][0]["child"],tag)]
                   for fc in loop["child"]["children"]]
            orders.append(order)
        main,=[o for o in orders if len(o)==88]
        expected_pattern=[k if not k.endswith(".__ARC__") else "stock.s7" for k in loops_needed[index]]
        # Both charts can use opposite loop sense; test sector order and the
        # orientation within each four-edge group independently of the start.
        reverse_sectors=[k for i in range(21,-1,-1) for k in expected_pattern[4*i:4*i+4]]
        if [sibling] not in orders or not (cyclic_match(main,expected_pattern) or cyclic_match(main,reverse_sectors)):
            raise ValueError("stock band loop does not have the exact 22 sector pattern")
        ready.append((tag,list(face_edges(face[tag]))))
    results=[]
    for id,edges in ready:
        vals=[]
        for e in edges:
            other=neighbor(e,id)
            if e["tag"] in interfaces:
                vals.append(interfaces[e["tag"]])
            else:
                vals.append(known[other]+(transport if names[other].endswith(".roll") else 0))
        # With r>=11, chart (12*azimuth,Y) is at most 2-Lipschitz on
        # close corresponding boundary points. Loop homotopy doubles
        # the boundary envelope in the chart. The lift has slope <=4
        # for s6, <=2 for s7/s8 (axial slope below .7 mm/mm).
        edge=max(vals)
        height=16*edge if names[id]=="stock.s6" else 8*edge
        results.append({"face_tag_session_only":id,"p3_support_id":names[id],
                        "conditional_patch_upper_mm":upper_float(height+carrier[id])})
    return {"schema":"p4-c5-stock-conditional-finite-patches/1","face_count":len(results),
            "maximum_conditional_patch_upper_mm":max(r["conditional_patch_upper_mm"] for r in results),
            "interface_arc_count":len(interfaces),"maximum_original_interface_arc_upper_mm":upper_float(max(interfaces.values())),
            "transition_parameter_alignment_upper_mm":upper_float(transport),
            "scope":"s6 cone, 22 s7 cylindrical faces and s8 torus under the complete implicit-edge, paired-loop and retained-material assumptions.",
            "execution_approved":False,"faces":results}


def _s6_anchor(plan, native_points, apex, reciprocal_slope, boundary):
    profile = plan['construction']['profiles']['stock_profile']
    v5,v6 = profile['vertices'][5:7]
    ylo,yhi = Q(v5['y_mm']),Q(v6['y_mm'])
    found = []
    for row in native_points['faces']:
        point=v(row['point_mm'])
        x,y,z=point
        rlo,rhi=sqrt_bounds(x*x+z*z)
        if (row['uv_containment_status']==1 and ylo+Q('.02')<y<yhi-Q('.02')
                and max(abs(y-apex-u*reciprocal_slope) for u in (rlo,rhi))<Q('0.00000001')):
            found.append((point,row))
    point,row = found.pop() if len(found)==1 else (None,None)
    if point is None:
        raise ValueError('could not bind a unique original cone interior witness by physical position')
    radius=sqrt_bounds(point[0]**2+point[2]**2)[1]
    # The coupled C5 window bounds all profiles above radius 11.1124
    # before roll. This alternative witness lies strictly below all cuts.
    if radius<Q('11.10'):
        return {'point_mm':list(map(float,point)),'native_inside_trim_status':row['uv_containment_status'],
                'clearance_below_all_straight_c5_sections_mm':float(Q('11.1124')-radius)}
    # At this station no tail, head or roll cutter acts. A ring point may be
    # excluded only by a straight C5 cutter. Test the one nearby member
    # against its complete monotone flank in the local section chart.
    nearby = []
    for member in (n for n in plan['construction']['nodes'] if n['id'].endswith('_straight_tool')):
        frame=member['frame']
        t,r = dot(point,v(frame['e_t'])),dot(point,v(frame['e_r']))
        if r>10 and abs(t)<Q('1.55'):
            nearby.append((member['id'],t,r))
    if len(nearby)!=1:
        raise ValueError('s6 material witness is outside the tested C5 flank-anchor case')
    member,t,r=nearby[0]
    side='F0002' if t>0 else 'F0024'
    c=_curve(nominal(plan['construction']['profiles']['section6']['templates'][side]))
    lo,hi=c['a'],c['b']
    tlo,thi=_evaluate(c,lo)[0],_evaluate(c,hi)[0]
    if not thi<t<tlo:
        raise ValueError('s6 witness does not lie in the finite flank projection')
    for _ in range(34):
        m=(lo+hi)/2
        if _evaluate(c,m)[0]>t:
            lo=m
        else:
            hi=m
    # Both t coordinates decrease and radial coordinates are monotone on
    # their original FIN domains (the accepted C5 checks). Stored nominal
    # coordinates differ from the canonical segment by <1e-8.
    radius_lower = 15-max(_evaluate(c,lo)[1],_evaluate(c,hi)[1])
    clearance = radius_lower-r
    if clearance<=max(8*boundary,Q('0.001')):
        raise ValueError('s6 retained-side witness too close to the cutter boundary')
    return {'point_mm':list(map(float,point)),'native_inside_trim_status':row['uv_containment_status'],
            'nearest_c5_section':member+'.'+side,
            'p3_radial_clearance_to_flank_mm':float(clearance)}


def verify_s6_stock_face(capture,support_index,plan,straight,roots,bands,native_points,limit=Q('.000141')):
    """Verify the full one-face s6 cone bounded by the 22 straight cutter loops."""
    from .nx2506_stock_bands import _exact_stock_parameters, hoop

    for report,count in ((straight,44),(roots,22),(bands,12)):
        if report['status']!='within_limit' or report['face_count']!=count:
            raise ValueError('all shared original straight trim faces required')
    names={r['face_tag_session_only']:r['p3_support_id'] for r in support_index['faces']}
    faces={r['detail']['face_tag']:r['detail']['topology'] for r in capture['results']}
    incidence=defaultdict(set)
    for tag,face in faces.items():
        for edge in face_edges(face):
            incidence[edge['tag']].add(tag)
    tag,=[key for key,name in names.items() if name=='stock.s6']
    face=faces[tag]
    graph={e['tag']:next(iter(incidence[e['tag']]-{tag})) for e in face_edges(face)}
    lower,=[loop for loop in face['children'] if len(loop['child']['children'])==1]
    upper,=[loop for loop in face['children'] if len(loop['child']['children'])==88]
    order=[names[graph[r['child']['children'][0]['child']['tag']]] for r in upper['child']['children']]
    expected=[name for i in range(22) for name in (
        f'member_{i:02d}.F0002.linear',f'member_{i:02d}.straight_root',
        f'member_{i:02d}.F0024.linear','stock.s7')]
    reversed_sectors=[k for i in range(21,-1,-1) for k in expected[4*i:4*i+4]]
    if len(face['children'])!=2 or not (cyclic_match(order,expected) or cyclic_match(order,reversed_sectors)):
        raise ValueError('s6 did not cover all 22 original directed cutter loops')
    comparison={r['p3_support_id']:r for group in (straight,roots) for r in group['faces']}
    if set(comparison)!=set(order)-{'stock.s7'}:
        raise ValueError('incomplete accepted shared original cone edges')
    cut=max(Q(r['continuous_bidirectional_patch_upper_mm']) for r in comparison.values())
    # The source of the pointwise finite-patch upper from the straight
    # reports is the same projected t matching on the original lower edge;
    # its endpoints are aligned to the analytic lower graph.
    projection=max(Q(r['preview_transfer_upper_mm']) for r in straight['faces'])
    p=_exact_stock_parameters(plan)
    y5=p['Y5']
    r5=p['R5']
    inverse=(p['Y6']-p['Y5'])/(p['R6']-p['R5'])
    canon_apex=p['Y5']-p['R5']*inverse
    observed_y,observed_r,frame_shift=hoop(lower)
    lower_error=(max(abs(observed_y-Q(y)) for y in (y5.lo,y5.hi))
                 +max(abs(observed_r-Q(r)) for r in (r5.lo,r5.hi))+frame_shift)
    matches=nominal_upper_vertices(plan)
    values={r['id']:Q(r['value']) for r in plan['parameters']['regional']}
    arcs=[]
    for e in face_edges(face):
        other=graph[e['tag']]
        if names[other]!='stock.s7':
            continue
        siblings=[names[next(iter(incidence[f['tag']]-{other}))] for f in face_edges(faces[other])]
        a,=[r.removesuffix('.linear') for r in siblings if r.endswith('.F0002.linear')]
        b,=[r.removesuffix('.linear') for r in siblings if r.endswith('.F0024.linear')]
        arcs.append(axial_circle_bound(e,values['stock.Y6'],values['stock.Rshaft'],[matches[a],matches[b]],
                                      endpoint_limit=min(limit,Q('.0001'))))
    if len(arcs)!=22:
        raise ValueError('incomplete original s6/s7 finite interface arcs')
    geometry=face['geometry']
    if geometry['type']!=202 or geometry['axis']!=[0,1,0] or geometry['point_at_apex'][::2]!=[0,0]:
        raise ValueError('expected original positive coaxial cone')
    from .nx2506_carrier_bound import tangent_range
    native_lo,native_hi=tangent_range(Q(geometry['half_apex_angle']))
    native_apex=Q(geometry['point_at_apex'][1])
    canonical_slope=(p['R6']-p['R5'])/(p['Y6']-p['Y5'])
    carrier=max(abs((y-native_apex)*s-(y-a)*k)
                for y in (Q(p['Y5'].lo)-Q('.001'),Q(p['Y6'].hi)+Q('.001'))
                for s in (native_lo,native_hi)
                for a in (Q(canon_apex.lo),Q(canon_apex.hi))
                for k in (Q(canonical_slope.lo),Q(canonical_slope.hi)))
    boundary=max(cut,lower_error,max(arcs)+4*projection)+carrier
    # Short equal-Y/azimuth transport on the common canonical cone. Squared
    # chord distance is the sum of meridian displacement squared and
    # 4*r1*r2*sin²(dtheta/2). r stays within [10.9,12.3] on the narrow band.
    if boundary>=Q('.001'):
        raise ValueError('s6 trim pairing outside the short-path estimate')
    witness=_s6_anchor(plan,native_points,native_apex,2/(native_lo+native_hi),boundary)
    maximum=boundary*Q('12.3')/Q('10.9')*Q('1.000001')+carrier
    return {'schema':'p4-native-s6-complete-cone/1',
            'status':'within_limit' if maximum<=limit else 'bound_exceeds_limit',
            'face_count':1,
            'continuous_bidirectional_patch_upper_mm':upper_float(maximum),
            'original_edge_count':89,'paired_cutter_boundaries':66,'paired_stock_arcs':22,
            'material_anchor':witness,'canonical_carrier_transport_mm':upper_float(carrier),
            'faces':[{'p3_support_id':'stock.s6','continuous_bidirectional_patch_upper_mm':upper_float(maximum)}],
            'scope':'Entire C14 s6 cone including the lower hoop and the 88-use upper boundary.',
            'execution_approved':False}


def verify_s7_s8_stock_faces(capture,support_index,plan,conditional,straight,roll,roots,anchors,
                             limit=Q('.000141')):
    """Verify each remaining C5-adjacent stock interface face on its finite region."""
    from .nx2506_stock_bands import _exact_stock_parameters, hoop

    if (anchors.get('schema')!='p4-native-s7-s8-anchors/1' or anchors.get('disk_copy_unchanged') is not True
            or any(r['status']!='within_limit' for r in (straight,roll,roots))):
        raise ValueError('accepted adjacent straight/roll trims and original stock material sides required')
    names={r['face_tag_session_only']:r['p3_support_id'] for r in support_index['faces']}
    faces={r['detail']['face_tag']:r['detail']['topology'] for r in capture['results']}
    pairs=defaultdict(set)
    for i,face in faces.items():
        for e in face_edges(face):
            pairs[e['tag']].add(i)
    def neighbor(edge,face):
        other,=pairs[edge['tag']]-{face}
        return names[other]
    edits=_exact_stock_parameters(plan)
    rshaft=edits['Rshaft']
    actual_y8=edits['Y8']
    actual_r8=edits['R8']
    rows=lambda report:{r['p3_support_id']:r for r in report['faces']}
    linear=rows(straight)
    rolled=rows(roll)
    rolled_roots=rows(roots)
    results=[]
    verified_interface=Q(conditional['maximum_original_interface_arc_upper_mm'])
    endpoint_transfer=4*max(Q(r['preview_transfer_upper_mm']) for r in rolled.values())
    arcs=verified_interface+endpoint_transfer
    for tag,name in sorted(names.items()):
        if name not in ('stock.s7','stock.s8'):
            continue
        face=faces[tag]
        edges=list(face_edges(face))
        neighbors={e['tag']:neighbor(e,tag) for e in edges}
        carrier=face['geometry']
        if name=='stock.s7':
            a,=[role for role in neighbors.values() if role.endswith('.F0002.linear')]
            b,=[role for role in neighbors.values() if role.endswith('.F0024.linear')]
            i=int(a.split('.')[0][-2:])
            if int(b.split('.')[0][-2:])!=(i+1)%22 or not cyclic_match(list(neighbors.values()),
                    [b,b.replace('.linear','.roll'),'stock.s8',a.replace('.linear','.roll'),a,'stock.s6']):
                raise ValueError('s7 cylinder loop no longer borders adjacent complete C5 cuts')
            key=f'stock.s7-gap-after-{i:02d}'
            bound=max(arcs,*(Q(linear[r]['continuous_bidirectional_patch_upper_mm']) for r in (a,b)),*(
                Q(rolled[role.replace('.linear','.roll')]['s7_boundary_path_mm'])+Q('0.0000001')
                +Q(rolled[role.replace('.linear','.roll')]['preview_transfer_upper_mm']) for role in (a,b)))
            off=max(abs(Q(carrier['radius'])-Q(z)) for z in (rshaft.lo,rshaft.hi))
            if carrier['type']!=201 or carrier['axis'] not in ([0,1,0],[0,-1,0]) or carrier['point_on_axis'][::2]!=[0,0]:
                raise ValueError('s7 native cylinder outside the paired coaxial chart')
            e,=[x for x in edges if neighbors[x['tag']]=='stock.s6']
            old=sorted(v(c['child']['geometry']['point']) for c in e['children'])
            anchor=anchors['faces'][key]
            new=sorted(map(v,anchor['lower_circle_endpoints_mm']))
            if any(endpoint_distance([(x,x) for x in a_],[(x,x) for x in b_])>Q('0.00000001')
                   for a_,b_ in zip(old,new,strict=True)):
                raise ValueError('s7 original ring-side reference identity changed')
            pt=v(anchor['gap_middle_mm'])
            if min(sum(abs(x-y) for x,y in zip(pt,endpoint)) for endpoint in old)<Q('.001'):
                raise ValueError('s7 anchor too close to its C5 cut endpoints')
        else:
            key='stock.s8'
            upper,=[r for r in face['children'] if len(r['child']['children'])==1]
            lower,=[r for r in face['children'] if len(r['child']['children'])==88]
            pattern=[neighbors[p['child']['children'][0]['child']['tag']] for p in lower['child']['children']]
            expected=[item for i in range(22) for item in (
                f'member_{i:02d}.F0024.roll',f'member_{i:02d}.roll_root',f'member_{i:02d}.F0002.roll','stock.s7')]
            reversed_sectors=[x for i in range(21,-1,-1) for x in expected[4*i:4*i+4]]
            if len(face['children'])!=2 or not (cyclic_match(pattern,expected) or cyclic_match(pattern,reversed_sectors)):
                raise ValueError('s8 does not have the complete paired 22-sector trim')
            ay,ar,frame=hoop(upper)
            ring=max(abs(ay-Q(y)) for y in (actual_y8.lo,actual_y8.hi))+max(
                abs(ar-Q(r)) for r in (actual_r8.lo,actual_r8.hi))+frame
            bound=max(arcs,ring,*(Q(rolled[k]['continuous_bidirectional_patch_upper_mm']) if k in rolled
                                 else Q(rolled_roots[k]['continuous_bidirectional_patch_upper_mm'])
                                 for k in set(pattern)-{'stock.s7'}))
            if carrier['type']!=204 or carrier['axis'] not in ([0,1,0],[0,-1,0]) or carrier['center'][::2]!=[0,0]:
                raise ValueError('s8 native torus outside the paired coaxial chart')
            off=sum(max(abs(Q(x)-Q(y)) for y in (edits[n].lo,edits[n].hi))
                    for x,n in zip((carrier['center'][1],carrier['major_radius'],carrier['minor_radius']),
                                   ('Y7','M8','tube_R8')))
            anchor=anchors['faces'][key]
        inside,outside=anchor['anchors']
        if ([inside['containment_status'],outside['containment_status']]!=[1,2]
                or sum(abs(Q(x)-Q(y)) for x,y in zip(inside['carrier_point_mm'],inside['reference_mm']))>Q('0.00000001')):
            raise ValueError('s7/s8 native material classification disagrees')
        if bound+off>=Q('.001'):
            raise ValueError('s7/s8 bound outside the small-angle chart transport')
        # Short paths between these nearly coincident points on the same
        # coaxial carrier increase physical length by <1.0001. The ring
        # radius changes by at most the meridian path length (<.001001)
        # and both endpoints have radius >12, so its ratio is bounded.
        # The actual and canonical domains share the same material witness;
        # off this continuously swept boundary the winding is unchanged.
        total=Q('1.0001')*(bound+off)+off
        results.append({'native_face_in_c14_brep_inventory':tag,'p3_support_id':name,
                        'finite_region_id':key,'continuous_bidirectional_patch_upper_mm':upper_float(total),
                        'carrier_transfer_upper_mm':upper_float(off),
                        'status':'within_limit' if total<=limit else 'bound_exceeds_limit'})
    if len(results)!=23 or {r['finite_region_id'] for r in results}!=set(anchors['faces']):
        raise ValueError('all twenty-two s7 regions and the original s8 region must be recorded individually')
    return {'schema':'p4-native-stock-s7-s8-finite-faces/1','face_count':len(results),'faces':results,
            'status':'within_limit' if all(r['status']=='within_limit' for r in results) else 'bound_exceeds_limit',
            'continuous_bidirectional_patch_upper_mm':max(r['continuous_bidirectional_patch_upper_mm'] for r in results),
            'scope':'Twenty-two original s7 faces and s8, with oriented finite trim and native material-side witnesses.',
            'execution_approved':False}


def edited_shaft_interface_bounds(capture,support_index,plan):
    """Compare all forty-four original gap arcs at the edited cone and shoulder interfaces."""
    values={r["id"]:Q(r["value"]) for r in plan["parameters"]["regional"]}
    y7=values["stock.Y7"]
    rshaft=values["stock.Rshaft"]
    height=y7+71
    templates=plan["construction"]["profiles"]["section6"]["templates"]
    nodes={r["id"]:r for r in plan["construction"]["nodes"]}
    roots={}
    for side,view in templates.items():
        c=_curve(nominal(view))
        def f(u):
            t,arm,_,_=_evaluate(c,u)
            a,b=sqrt_bounds(arm**2-height**2)
            rr=(15-b,15-a)
            return tuple(t*t+n*n-rshaft*rshaft for n in rr)
        left,right=c["a"],c["b"]
        if f(left)[0]>0:
            left,right=right,left
        if f(left)[1]>=0 or f(right)[0]<=0:
            raise ValueError("edited C5 transition did not bracket the s7/s8 splice")
        for _ in range(41):
            middle=(left+right)/2
            lo,hi=f(middle)
            if lo>0:
                right=middle
            elif hi<0:
                left=middle
            else:
                break
        patch=[_evaluate(c,t) for t in (left,right)]
        ts=sorted(p[0] for p in patch)
        arms=sorted(p[1] for p in patch)
        ns=(15-sqrt_bounds(arms[1]**2-height**2)[1],15-sqrt_bounds(arms[0]**2-height**2)[0])
        roots[side]=(ts,ns)
    targets={}
    for i in range(22):
        key=f"member_{i:02d}"
        frame=nodes[key+"_straight_tool"]["frame"]
        tangential,radial=v(frame["e_t"]),v(frame["e_r"])
        for side,(ts,ns) in roots.items():
            targets[key+"."+side]=tuple(
                (y7,y7) if d==1 else (
                    min(t*tangential[d]+n*radial[d] for t in ts for n in ns),
                    max(t*tangential[d]+n*radial[d] for t in ts for n in ns))
                for d in range(3))
    earlier=nominal_upper_vertices(plan)
    labels={r["face_tag_session_only"]:r["p3_support_id"] for r in support_index["faces"]}
    faces={r["detail"]["face_tag"]:r["detail"]["topology"] for r in capture["results"]}
    incidence=defaultdict(set)
    for key,face in faces.items():
        for edge in face_edges(face):
            incidence[edge["tag"]].add(key)
    arcs=[]
    for key,name in labels.items():
        if name!="stock.s7":
            continue
        own={labels[next(iter(incidence[e["tag"]]-{key}))]:e for e in face_edges(faces[key])}
        a,=[r.removesuffix('.linear') for r in own if r.endswith('.F0002.linear')]
        b,=[r.removesuffix('.linear') for r in own if r.endswith('.F0024.linear')]
        for label,y,locations in (("stock.s6",values["stock.Y6"],earlier),("stock.s8",y7,targets)):
            bounds=axial_circle_bound(own[label],y,rshaft,(locations[a],locations[b]),
                                     endpoint_limit=Q('.0001'))
            arcs.append({"finite_gap_after":a.split(".")[0],"neighbor":label,
                         "original_edge_in_edited_inventory":own[label]["tag"],
                         "continuous_pairing_upper_mm":upper_float(bounds)})
    if len(arcs)!=44:
        raise ValueError("did not cover the forty-four true edited finite interface arcs")
    return {"schema":"p4-edited-stock-s7-interface-arcs/1","arcs":arcs,
            "maximum_original_interface_arc_upper_mm":max(e["continuous_pairing_upper_mm"] for e in arcs),
            "execution_approved":False}
