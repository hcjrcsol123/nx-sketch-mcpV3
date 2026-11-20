"""Conditional finite C5 root cylinder and roll-torus patch bounds."""
from collections import defaultdict
from fractions import Fraction as Q

from .nx2506_carrier_bound import dot,l1,sub,tangent_range,upper_float,v
from .nx2506_roll_s7_bound import face_edges,s8_constants,sqrt_bounds
from .nx2506_tail_trim_bound import _sincos


def arc_endpoint(g,angle):
    si,co=_sincos(Q(angle))
    out=[]
    r=Q(g["radius"])
    for ctr,x,y in zip(g["center"],g["x_axis"],g["y_axis"]):
        ca=sorted(Q(x)*r*c for c in co)
        sa=sorted(Q(y)*r*s for s in si)
        out.append((Q(ctr)+ca[0]+sa[0],Q(ctr)+ca[1]+sa[1]))
    return out


def point_gap(bounds,expected):
    return sum((max(abs(a-x),abs(b-x)) for (a,b),x in zip(bounds,expected)),Q())


def starting_arc_bound(arc,frame,reference):
    if arc["type"]!="circular_evaluator" or arc["is_periodic"]:
        raise ValueError("expected the original finite C5 root start arc")
    lo,hi=map(Q,arc["evaluator_limits"])
    if not Q(1)<hi-lo<Q(3):
        raise ValueError("native root arc did not select the short lower branch")
    u,w=v(arc["x_axis"]),v(arc["y_axis"])
    errors=abs(dot(u,u)-1)+abs(dot(w,w)-1)+abs(dot(u,w))+abs(u[1])+abs(w[1])
    if errors>Q("0.000000001"):
        raise ValueError("native root circle basis is not transverse")
    er,et=v(frame["e_r"]),v(frame["e_t"])
    data=reference["edges"][5]
    _,pitch=map(Q,data["center_t_r_mm"])
    radius=Q(data["radius_mm"])
    center=(pitch*er[0],Q(-71),pitch*er[2])
    radius_native=Q(arc["radius"])
    base=l1(sub(v(arc["center"]),center))+2*abs(radius-radius_native)+8*radius_native*errors
    target=[]
    for side in ("F0024","F0002"):
        end=reference["templates"][side]["endpoints"]["root"]
        t,r=[Q(end[k]["value"]) for k in ("t_mm","r_mm")]
        target.append((t*et[0]+r*er[0],Q(-71),t*et[2]+r*er[2]))
    first,second=arc_endpoint(arc,lo),arc_endpoint(arc,hi)
    endpoints=min(max(point_gap(first,a),point_gap(second,b)) for a,b in (target,list(reversed(target))))
    if endpoints>Q("0.000001"):
        raise ValueError("C5 root arc does not match expected finite endpoints")
    # After aligning the circular supports, an endpoint chord difference
    # controls its arc shift by pi/2; L1 adds a conservative factor two.
    return 5*base+4*endpoints


def prove_root_exit_window(Rerror,plan):
    stock=plan["construction"]["profiles"]["stock_profile"]["curves"]
    arc=next(c for c in stock if c["id"]=="s8")
    center,major=map(Q,arc["center_y_r_mm"])
    radi=Q(arc["radius_mm"])
    def rbox(v):
        d=v-71-center
        lo,hi=sqrt_bounds(radi**2-d**2)
        return major-hi-Rerror,major-lo+Rerror
    # Root arc has |t|<0.75, L in [3.67,3.91], and M within 0.01
    # of 15. The entire paired family exits in [2.1,3.1] mm of roll.
    a,b=Q("2.1"),Q("3.1")
    nmax=Q("15.01")-sqrt_bounds(Q("3.67")**2-a**2)[0]
    nmin=Q("14.99")-sqrt_bounds(Q("3.91")**2-b**2)[1]
    if nmax*nmax+Q("0.75")**2>=rbox(a)[0]**2 or nmin<=rbox(b)[1]:
        raise ValueError("root exit interval does not bracket the two graphs")
    # For 2.1<=v<=3.1, n>=10.99, L<=4, Q_s8 sqrt>4.5 and R_s8<14:
    # dF/dv >= 5.4v-6.3(v-1.23) >= 4.
    return (a,b,Q(4))


def assess_c5_root_patches(capture,supports,plan):
    Rerror,names,geometries=s8_constants(plan,capture,supports)
    window=prove_root_exit_window(Rerror,plan)
    topology={r["detail"]["face_tag"]:r["detail"]["topology"] for r in capture["results"]}
    incidence=defaultdict(set)
    for key,face in topology.items():
        for e in face_edges(face):
            incidence[e["tag"]].add(key)
    profiles=plan["construction"]["profiles"]
    nodes={n["id"]:n for n in plan["construction"]["nodes"]}
    stock=profiles["stock_profile"]
    vertices={v["id"]:v for v in stock["vertices"]}
    c6=next(c for c in stock["curves"] if c["id"]=="s6")
    a,b=vertices[c6["start"]],vertices[c6["end"]]
    slope=(Q(b["radius_mm"])-Q(a["radius_mm"]))/(Q(b["y_mm"])-Q(a["y_mm"]))
    apex=Q(a["y_mm"])-Q(a["radius_mm"])/slope
    cone,=[geometries[i] for i,name in names.items() if name=="stock.s6"]
    if cone["type"]!=202 or cone["axis"]!=[0,1,0] or cone["point_at_apex"][0]!=0 or cone["point_at_apex"][2]!=0:
        raise ValueError("root trim requires canonical positive stock.s6 cone")
    lo,hi=tangent_range(Q(cone["half_apex_angle"]))
    dy_apex=abs(Q(cone["point_at_apex"][1])-apex)
    inverse=max(abs(1/k-1/slope) for k in (lo,hi))
    matches={f["p3_support_id"]:Q(f["distance_upper_mm"]) for f in supports["faces"]
             if f["p3_support_id"].endswith((".straight_root",".roll_root"))}
    rows=[]
    for id,name in names.items():
        if not name.endswith((".straight_root",".roll_root")):
            continue
        member=name.split(".")[0]
        roll=name.endswith(".roll_root")
        mode="roll" if roll else "linear"
        stock_name="stock.s8" if roll else "stock.s6"
        mate=member+(".straight_root" if roll else ".roll_root")
        expected={(10,mate),(10,member+".F0002."+mode),(10,member+".F0024."+mode),(11,stock_name)}
        edges=list(face_edges(topology[id]))
        links=[(e["geometry_class"],names[next(iter(incidence[e["tag"]]-{id}))]) for e in edges]
        if len(topology[id]["children"])!=1 or len(links)!=4 or set(links)!=expected:
            raise ValueError("root patch loop does not match its P3 material boundaries")
        front,=[e["geometry"] for e,k in zip(edges,links) if k==(10,mate)]
        arc_error=starting_arc_bound(front,nodes[member+"_straight_tool"]["frame"],profiles["section6"])
        if roll:
            # Use both raw cylinder/torus carrier perturbations when matching
            # the generator to the common root arc. Position errors below
            # 1e-6 also keep the full strip in L=[3.67,3.91], |t|<0.75.
            coordinates=2*arc_error+4*(matches[mate]+matches[name])
            if coordinates>Q("0.000001"):
                raise ValueError("root roll generator correspondence too loose")
            dn=5*coordinates
            height=(Q("1.5")*coordinates+31*dn+28*Rerror)/window[2]
            upper=12*coordinates+7*height
        else:
            height=dy_apex+arc_error/lo+13*inverse
            upper=arc_error+height
        rows.append({"face_tag_session_only":id,"p3_support_id":name,
                     "conditional_patch_upper_mm":upper_float(upper)})
    return {"schema":"p4-c5-root-conditional-finite-patches/1","face_count":len(rows),
            "maximum_conditional_patch_upper_mm":max(x["conditional_patch_upper_mm"] for x in rows),
            "scope":"22 root cylinders and 22 root tori under the complete class11 finite trim and material-side assumptions.",
            "method":"Original front arc comparison; cone entrance graph for straight roots and uniform s8 exit derivative for rolled roots.",
            "execution_approved":False,"faces":rows}


def verify_c5_straight_root_patches(capture,supports_index,plan,conditional,facets):
    """Verify all twenty-two original straight root cylinder patches."""
    from .nx2506_c5_straight_trim import _canonical_straight_transfer, _original_strip_bound
    from .nx2506_carrier_bound import supports
    from .nx2506_stock_bands import _exact_stock_parameters

    if (facets.get('schema')!='p4-native-c5-straight-facets/1' or facets.get('kind')!='root'
            or facets.get('status')!='complete' or facets.get('disk_copy_unchanged') is not True):
        raise ValueError('complete original straight-root facet evidence required')
    rows = [r for r in conditional['faces'] if r['p3_support_id'].endswith('.straight_root')]
    if len(rows)!=22 or {r['p3_support_id'] for r in rows}!=set(facets['faces']):
        raise ValueError('straight root role coverage differs')
    native = {r['detail']['face_tag']:r['detail']['topology'] for r in capture['results']}
    cone_id, = [f['face_tag_session_only'] for f in supports_index['faces'] if f['p3_support_id']=='stock.s6']
    cone = native[cone_id]['geometry']
    apex = Q(cone['point_at_apex'][1])
    slopes = tangent_range(Q(cone['half_apex_angle']))
    p3_cone, = [r for r in supports(plan) if r[0]=='stock.s6']
    exact_stock = _exact_stock_parameters(plan)
    frames = {r['id']:r['frame'] for r in plan['construction']['nodes'] if r['id'].endswith('_straight_tool')}
    section = plan['construction']['profiles']['section6']

    def constant(value):
        return {'lower':str(value),'upper':str(value),'value':value}

    envelope = {'poles': [
        *({'t_mm':constant(t),'r_mm':constant(r)} for t in (-1,1) for r in (11,13)),
        *(data['endpoints']['root'] for data in section['templates'].values()),
    ]}
    results = []
    for row in sorted(rows,key=lambda r:r['p3_support_id']):
        name = row['p3_support_id']
        member = name.split('.')[0]
        frame = frames[member+'_straight_tool']
        tangent,radial = v(frame['e_t']),v(frame['e_r'])
        face = native[row['face_tag_session_only']]
        carrier = face['geometry']
        center = v(carrier['point_on_axis'])
        radius = Q(carrier['radius'])
        edges = list(face_edges(face))
        front, = [r for r in edges if r['geometry']['type']=='circular_evaluator']
        physical = sorted(r['child']['geometry']['point'] for r in front['children'])
        facet = facets['faces'][name]
        if any(l1(sub(v(a),v(b)))>Q('0.00000001')
               for a,b in zip(physical,facet['upper_endpoints_mm'],strict=True)):
            raise ValueError('original root front edge no longer binds to the same carrier')
        tlo,thi = sorted(dot(v(p),tangent) for p in physical)
        center_t = dot(center,tangent)
        if (carrier['type']!=201 or carrier['axis'] not in ([0,1,0],[0,-1,0])
                or not Q('.73')<radius<Q('.75') or dot(tangent,tangent)<Q('.99')**2
                or max(abs(tlo-center_t),abs(thi-center_t))>=Q('.59')
                or any(dot(sub(v(p),center),radial)>=Q('-.4') for p in physical)):
            raise ValueError('root front is outside the monotone lower circular branch')
        # The original arc is the short lower branch already paired to P3.
        # Its projected t chart lift is <3 in world XZ L1 for |t-c|<.6,
        # root radius >.73 and tangent projection axis norm >.99.
        side_uncertainty = max(Q(row['conditional_patch_upper_mm']), starting_arc_bound(
            front['geometry'],frame,section))
        for edge in (r for r in edges if r['geometry']['type']==101):
            line = edge['geometry']
            bottom,top = sorted((v(line['start']),v(line['end'])),key=lambda p:p[1])
            upper_error = min(l1(sub(top,v(p))) for p in physical)
            vertical_error = abs(bottom[0]-top[0])+abs(bottom[2]-top[2])
            rlo,rhi = sqrt_bounds(bottom[0]**2+bottom[2]**2)
            lower_error = max(abs(bottom[1]-(apex+r/s)) for r in (rlo,rhi) for s in slopes)
            side_uncertainty = max(side_uncertainty,upper_error+vertical_error+lower_error)
        reach = abs(center[0])+abs(center[2])+2*radius
        trim = _original_strip_bound(facet,lambda p:dot(v(p),tangent),tlo,thi,Q(3),reach,
                                     apex,slopes,side_uncertainty)
        # The common local root circle is exact. Bound frame change over the
        # complete enclosing rectangle, and any endpoint angle adjustment
        # with a conservative fourfold chord-to-arc transport.
        transfer = 4*_canonical_straight_transfer(plan,envelope,frame,
                                                int(member.rsplit('_',1)[1]),p3_cone,exact_stock,reach+1)
        upper = trim+Q(row['conditional_patch_upper_mm'])+transfer
        results.append({'p3_support_id':name,'native_trim_upper_mm':upper_float(trim),
                        'preview_transfer_upper_mm':upper_float(transfer),
                        'continuous_bidirectional_patch_upper_mm':upper_float(upper),
                        'status':'within_limit' if upper<=Q('0.000141') else 'bound_exceeds_limit'})
    return {'schema':'p4-native-c5-straight-root-finite-patches/1','face_count':len(results),
            'status':'within_limit' if all(r['status']=='within_limit' for r in results) else 'bound_exceeds_limit',
            'continuous_bidirectional_patch_upper_mm':max(r['continuous_bidirectional_patch_upper_mm'] for r in results),
            'scope':'22 complete original straight root faces with NX-confirmed material side and full cone intersection chains.',
            'faces':results,'execution_approved':False}


def _s8_root_facet_field(capture, y0, major, tube):
    tau=Q(capture['chord_tolerance_mm'])
    vertex=Q(capture['max_vertex_deviation_mm'])
    points=[v(point) for point in capture['points_mm']]
    if Q(capture['max_midpoint_deviation_mm'])>tau or any(
            sum((x-y)**2 for x,y in zip(a,b))<=(2*vertex)**2 for a,b in zip(points,points[1:])):
        raise ValueError('original roll-root facet chain or chord allowance disagrees')
    errors=[]
    for x,y,z in points:
        if not Q('-68.899')<y<Q('-67.901') or abs(y-y0)>=Q('1.9') or tube<=Q('4.99'):
            raise ValueError('rolled root facet leaves tested s8 exit strip')
        root=sqrt_bounds(tube*tube-(y-y0)**2)
        rho=sqrt_bounds(x*x+z*z)
        errors.append(max(abs(r+delta-major) for r in rho for delta in root))
    chord=Q(0)
    for a,b,e1,e2 in zip(points,points[1:],errors,errors[1:]):
        xa,ya,za=a
        xb,yb,zb=b
        if min(xa*xa+za*za,xa*xb+za*zb,xb*xb+zb*zb)<=121:
            raise ValueError('s8 facet curvature denominator not separated from zero')
        # The second derivative of norm along a segment is bounded by
        # |delta XZ|²/min_r. S8's axial graph has |r_YY|<.3 here.
        second=((xa-xb)**2+(za-zb)**2)/11+Q('.3')*(ya-yb)**2
        chord=max(chord,max(e1,e2)+second/8)
    # The original edge is within the facet chord allowance. The stock
    # clearance function has Euclidean Lipschitz constant below 1.2.
    return chord+Q('1.2')*(tau+vertex)


def _root_exit_derivative(y7,tube):
    bounds=[]
    for i in range(20):
        a=Q('2.1')+Q(i,20)
        b=Q('2.1')+Q(i+1,20)
        upper_roll_root=sqrt_bounds(Q('3.9')**2-a*a)[1]
        offset=b-71-y7
        if offset<0:
            raise ValueError('expected rising inner s8 graph branch')
        lower_stock_root=sqrt_bounds(tube*tube-offset*offset)[0]
        bounds.append(Q('.998')*a/upper_roll_root-offset/lower_stock_root)
    return min(bounds)


def verify_c5_roll_root_patches(capture,support_index,plan,conditional,facets):
    """Verify all original rolled root patches with continuous s8 exit chains."""
    from .nx2506_carrier_bound import supports
    from .nx2506_c5_straight_trim import _canonical_straight_transfer
    from .nx2506_head_trim import _unit_interval
    from .nx2506_stock_bands import _exact_stock_parameters

    if (facets.get('schema')!='p4-native-c5-straight-facets/1' or facets.get('kind')!='roll_root'
            or facets.get('status')!='complete' or facets.get('disk_copy_unchanged') is not True):
        raise ValueError('complete original rolled root facet evidence required')
    rows=[r for r in conditional['faces'] if r['p3_support_id'].endswith('.roll_root')]
    if len(rows)!=22 or {r['p3_support_id'] for r in rows}!=set(facets['faces']):
        raise ValueError('rolled root role coverage differs')
    native={r['detail']['face_tag']:r['detail']['topology'] for r in capture['results']}
    s8_id,=[r['face_tag_session_only'] for r in support_index['faces'] if r['p3_support_id']=='stock.s8']
    g=native[s8_id]['geometry']
    y7,major,tube=Q(g['center'][1]),Q(g['major_radius']),Q(g['minor_radius'])
    if g['type']!=204 or g['axis'] not in ([0,1,0],[0,-1,0]) or g['center'][::2]!=[0,0]:
        raise ValueError('original s8 is not the expected coaxial stock torus')
    derivative=_root_exit_derivative(y7,tube)
    if derivative<=Q('.4'):
        raise ValueError('s8 rolled root clearance derivative too small')
    p3_cone,=[r for r in supports(plan) if r[0]=='stock.s6']
    frames={r['id']:r['frame'] for r in plan['construction']['nodes'] if r['id'].endswith('_straight_tool')}
    section=plan['construction']['profiles']['section6']
    exact_stock=_exact_stock_parameters(plan)
    preview={r['id'].removeprefix('stock.'):Q(r['value']) for r in plan['parameters']['regional']}
    stock_transfer=sum(max(abs(Q(endpoint)-preview[key]) for endpoint in
                           (exact_stock[key].lo,exact_stock[key].hi)) for key in ('Y7','M8','tube_R8'))
    def constant(value):
        return {'lower':str(value),'upper':str(value),'value':value}
    envelope={'poles':[
        *({'t_mm':constant(t),'r_mm':constant(r)} for t in (-1,1) for r in (11,15)),
        *(data['endpoints']['root'] for data in section['templates'].values()),
    ]}
    results=[]
    for row in sorted(rows,key=lambda r:r['p3_support_id']):
        name=row['p3_support_id']
        member=name.split('.')[0]
        frame=frames[member+'_straight_tool']
        face=native[row['face_tag_session_only']]
        carrier=face['geometry']
        center=v(carrier['center'])
        minor,major_root=Q(carrier['minor_radius']),Q(carrier['major_radius'])
        oriented=v(carrier['axis'])
        if dot(oriented,v(frame['e_t']))<0:
            oriented=tuple(-p for p in oriented)
        direction=_unit_interval(oriented)
        tangent=tuple((lo+hi)/2 for lo,hi in direction)
        radial=(-tangent[2],Q(0),tangent[0])
        # In the native chart t is measured from the torus center.
        reach=dot(center,radial)
        center_t=dot(center,tangent)
        if (carrier['type']!=204 or oriented[1] or center[1]!=-71 or not Q('14.99')<reach<Q('15.01')
                or abs(center_t)>=Q('0.000001')):
            raise ValueError('rolled root axis or origin outside the checked chart')
        edges=list(face_edges(face))
        front,=[e for e in edges if e['geometry_class']==10 and all(
            abs(Q(c['child']['geometry']['point'][1])+71)<Q('0.00000001') for c in e['children'])]
        original=sorted(c['child']['geometry']['point'] for c in front['children'])
        facet=facets['faces'][name]
        if any(l1(sub(v(a),v(b)))>Q('0.00000001')
               for a,b in zip(original,facet['upper_endpoints_mm'],strict=True)):
            raise ValueError('original rolled root front edge identity changed')
        tlo,thi=sorted(dot(v(p),tangent) for p in original)
        tmax=max(abs(tlo-center_t),abs(thi-center_t))+Q('0.000001')
        if not (tmax<Q('.52') and Q('3.67')<major_root+sqrt_bounds(minor*minor-tmax*tmax)[0]
                and major_root+minor<Q('3.9')
                and all(dot(v(point),radial)<reach-Q('3.6') for point in original)):
            raise ValueError('rolled root is outside its monotone outer-tube/inward-roll chart')
        front_shift=starting_arc_bound(front['geometry'],frame,section)
        side_shift=Q(0)
        for e in (r for r in edges if r['geometry_class']==10 and r['tag']!=front['tag']):
            geom=e['geometry']
            if geom['type']!='circular_evaluator' or not 0<Q(geom['evaluator_limits'][1])-Q(geom['evaluator_limits'][0])<Q('1.57'):
                raise ValueError('expected the original short rolled side arc')
            middle=dot(v(geom['center']),tangent)
            span=Q(geom['radius'])*(abs(dot(v(geom['x_axis']),tangent))+abs(dot(v(geom['y_axis']),tangent)))
            side_shift=max(side_shift,min(abs(middle-tlo),abs(middle-thi))+span)
            # The Y derivative of a circular arc is a sinusoid. A short
            # arc with equal nonzero signs at the two ends stays monotone.
            derivatives=[]
            for angle in geom['evaluator_limits']:
                sn,cs=_sincos(Q(angle))
                ys=[-Q(geom['x_axis'][1])*s+Q(geom['y_axis'][1])*c for s in sn for c in cs]
                derivatives.append((min(ys),max(ys)))
            if not (all(x[0]>0 for x in derivatives) or all(x[1]<0 for x in derivatives)):
                raise ValueError('roll side does not monotonically span the original axial strip')
        pad=2*max(front_shift,side_shift,Q('0.000000001'))
        field=_s8_root_facet_field(facet,y7,major,tube)
        # Lift has axial speed <2 and tangent speed <3 on the entire
        # graph strip. Therefore |dVexit/dt| <3/Fv. Use the same inner/
        # outer strip relation as the straight faces with the roof
        # provided by the unique rising s8 exit.
        height=field/derivative+front_shift+3*pad/derivative
        inside,outside=facet['material_anchors']
        anchor=v(inside['carrier_point_mm'])
        if (inside['containment_status']!=1 or outside['containment_status']!=2
                or not tlo+pad<dot(anchor,tangent)<thi-pad
                or not Q(-71)+height<anchor[1]<Q('-68.9')-height
                or Q(outside['carrier_point_mm'][1])>=Q(-71)-height):
            raise ValueError('rolled root inside/exterior witnesses disagree')
        trim=2*height+3*pad
        # Same-position A-frame change, derived s8 coefficients and the
        # bounded transverse root movement together fit this multiplier.
        frame_change=_canonical_straight_transfer(plan,envelope,frame,int(member.rsplit('_',1)[1]),
                                                  p3_cone,exact_stock,Q(20))
        transfer=20*(frame_change+stock_transfer)
        total=trim+Q(row['conditional_patch_upper_mm'])+transfer
        results.append({'p3_support_id':name,'native_trim_upper_mm':upper_float(trim),
                        'preview_transfer_upper_mm':upper_float(transfer),
                        'continuous_bidirectional_patch_upper_mm':upper_float(total),
                        'status':'within_limit' if total<=Q('.000141') else 'bound_exceeds_limit'})
    return {'schema':'p4-native-c5-roll-root-finite-patches/1','face_count':len(results),
            'status':'within_limit' if all(r['status']=='within_limit' for r in results) else 'bound_exceeds_limit',
            'continuous_bidirectional_patch_upper_mm':max(r['continuous_bidirectional_patch_upper_mm'] for r in results),
            'native_s8_clearance_derivative_min':float(derivative),
            'scope':'22 original rolled root torus patches with actual s8 exit chains.',
            'faces':results,'execution_approved':False}
