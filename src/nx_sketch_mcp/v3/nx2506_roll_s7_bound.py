"""Continuous stability of the C5 roll first-exit height against stock s7.

For 0..90 degree roll, an s7 exit satisfies y+71 = sqrt(lambda^2 -
(M-sqrt(Rshaft^2-t^2))^2). Compare those graph heights across the matched
native/P3 splines. This does not prove that the kernel chose the same finite
portion of either intersection graph or that the following s8 trim agrees.
"""
from collections import defaultdict
from fractions import Fraction as Q
from math import isqrt

from .nx2506_carrier_bound import direction_gap, exact, upper_float, v, dot
from .nx2506_trim_bound import _curve, _controls, _evaluate, _bernstein_matrix_inverse


def sqrt_bounds(x):
    if x < 0:
        raise ValueError("negative radius radicand")
    k = 10**20
    floor = isqrt(x.numerator*k*k//x.denominator)
    return Q(floor,k), Q(floor+1,k)


def abs_interval(lo,hi):
    return (Q(0) if lo<=0<=hi else min(abs(lo),abs(hi)),max(abs(lo),abs(hi)))


def bounds(rows,axis,error=Q(0)):
    values=[r[axis] for r in rows]
    return min(values)-error,max(values)+error


def split(rows):
    levels=[rows]
    while len(levels[-1])>1:
        levels.append([tuple((x+y)/2 for x,y in zip(a,b))
                       for a,b in zip(levels[-1],levels[-1][1:])])
    return ([row[0] for row in levels],[row[-1] for row in reversed(levels)])


def exit_box(rows,t_error,l_error,M,radius):
    lt,ht=abs_interval(*bounds(rows,0,t_error))
    low_l,high_l=bounds(rows,1,l_error)
    if low_l<=0:
        raise ValueError("roll radial strip must stay inside its transverse axis")
    min_r2=radius[0]**2-ht**2
    max_r2=radius[1]**2-lt**2
    qlo,qhi=sqrt_bounds(min_r2)[0],sqrt_bounds(max_r2)[1]
    clo,chi=M[0]-qhi,M[1]-qlo
    if clo<=0:
        raise ValueError("s7 exit branch selection requires positive radial offset")
    a_lo=low_l**2-chi**2
    a_hi=high_l**2-clo**2
    return (sqrt_bounds(max(Q(0),a_lo))[0],sqrt_bounds(max(Q(0),a_hi))[1],high_l,chi,ht,qlo)


def compare_cell(actual,reference,params):
    M,Ra,t_error,l_error,rad_error,m_error=params
    na=exit_box(actual,t_error,l_error,M,Ra)
    p3=exit_box(reference,Q(),Q(),(Q(15),Q(15)),(Q('12.1665'),Q('12.1665')))
    d_t=max(abs(a[0]-b[0]) for a,b in zip(actual,reference))+t_error
    d_l=max(abs(a[1]-b[1]) for a,b in zip(actual,reference))+l_error
    radii=Ra[1]+Q('12.1665')
    d_c=m_error+(radii*rad_error+(na[4]+p3[4])*d_t)/(na[5]+p3[5])
    d_A=(na[2]+p3[2])*d_l+(na[3]+p3[3])*d_c
    bound=min(max(na[1]-p3[0],p3[1]-na[0]),sqrt_bounds(d_A)[1])
    if na[0]+p3[0]>0:
        bound=min(bound,d_A/(na[0]+p3[0]))
    return bound


def record_curve(order,knots,poles,interval):
    return {"order":order,"knots":knots,"periodic":False,
            "poles":[[*map(exact,row),0,1] for row in poles],"interval":interval}


def nominal(template):
    basis=template["basis"]
    rows=[(Q(p["t_mm"]["value"]),Q(15)-Q(p["r_mm"]["value"])) for p in template["poles"]]
    return record_curve(basis["order"],basis["knots_exact"],rows,basis["fin_interval_exact"])


def native(geometry,nominal_axis,Ra):
    g=geometry["generator"]
    if g["type"]!=102 or g["order"]!=4 or g["rational"]:
        raise ValueError("expected a nonrational cubic roll generator")
    axis=v(geometry["axis"])
    origin=v(geometry["point_on_axis"])
    if axis[1]!=0 or origin[1]!=-71:
        raise ValueError("unexpected native roll axis orientation or station")
    if dot(axis,nominal_axis)<0:
        axis=tuple(-x for x in axis)
    transverse=(axis[2],Q(0),-axis[0])
    if dot(origin,transverse)<0:
        transverse=tuple(-x for x in transverse)
    norm2=dot(axis,axis)
    low=sqrt_bounds(norm2)[0]
    inv_error=abs(norm2-1)/(low*(low+1))
    flat=g["weighted_poles_flat_xyzw"]
    if any(w!=1 for w in flat[3::4]):
        raise ValueError("unexpected nonunit BREP generator weights")
    xyz=[v(flat[i:i+3]) for i in range(0,len(flat),4)]
    tangent=[dot(row,axis) for row in xyz]
    t_error=max(map(abs,tangent))*inv_error
    l_error=max(abs(dot(tuple(a-b for a,b in zip(row,origin)),transverse)) for row in xyz)/low
    moment=dot(origin,transverse)
    offset=abs(moment)*inv_error
    M=(moment-offset,moment+offset)
    Rdiff=max(abs(r-Q("12.1665")) for r in Ra)
    m_error=max(abs(m-15) for m in M)
    rows=[(t,row[1]+71) for t,row in zip(tangent,xyz)]
    return (record_curve(g["order"],g["knots"],rows,[g["start"],g["end"]]),
            (M,Ra,t_error,l_error,Rdiff,m_error))


def unite_partitions(a,b):
    cuts={Q(0),Q(1)}
    for c in (a,b):
        cuts.update((k-c["a"])/(c["b"]-c["a"]) for k in c["knots"]
                    if min(c["a"],c["b"])<k<max(c["a"],c["b"]))
    return sorted(cuts)


def paired_curves(data,ref):
    a,b=_curve(data),_curve(ref)
    a0,a1=(_evaluate(a,t) for t in (a["a"],a["b"]))
    b0,b1=(_evaluate(b,t) for t in (b["a"],b["b"]))
    if abs(a0[0]-b1[0])+abs(a1[0]-b0[0])<abs(a0[0]-b0[0])+abs(a1[0]-b1[0]):
        b["a"],b["b"]=b["b"],b["a"]
    return a,b


def compare_graphs(data,ref,params,target):
    a,b=paired_curves(data,ref)
    cuts=unite_partitions(a,b)
    matrix=_bernstein_matrix_inverse(3)
    work=[(_controls(a,s,t,matrix),_controls(b,s,t,matrix),0) for s,t in zip(cuts,cuts[1:])]
    maximum=Q(0)
    count=0
    while work:
        ac,bc,depth=work.pop()
        observed=compare_cell(ac,bc,params)
        if observed<=target or depth>=36:
            maximum=max(maximum,observed)
            count+=1
            continue
        a1,a2=split(ac)
        b1,b2=split(bc)
        work.extend(((a1,b1,depth+1),(a2,b2,depth+1)))
        if len(work)+count>20000:
            raise ValueError("s7 exit partition exceeded proof budget")
    return (maximum,count)


def assess_s7_exit_graphs(capture,supports,plan):
    names={row["face_tag_session_only"]:row["p3_support_id"] for row in supports["faces"]}
    geometries={row["detail"]["face_tag"]:row["detail"]["topology"]["geometry"] for row in capture["results"]}
    radii=[]
    for id,name in names.items():
        if name=="stock.s7":
            c=geometries[id]
            if c["type"]!=201 or c["axis"] not in ([0,1,0],[0,-1,0]) or c["point_on_axis"][0]!=0 or c["point_on_axis"][2]!=0:
                raise ValueError("stock s7 is not on the canonical axis")
            radii.append(Q(c["radius"]))
    Ra=(min(radii),max(radii))
    nodes={x["id"]:x for x in plan["construction"]["nodes"]}
    profiles=plan["construction"]["profiles"]["section6"]["templates"]
    target=Q("0.000008")
    rows=[]
    for i,name in names.items():
        if not name.endswith(".roll"):
            continue
        member,side,_=name.split(".")
        direction=v(nodes[member+"_roll_tool"]["axis_direction"])
        curve,params=native(geometries[i],direction,Ra)
        upper,count=compare_graphs(curve,nominal(profiles[side]),params,target)
        rows.append({"face_tag_session_only":i,"carrier":name,"exit_height_upper_mm":upper_float(upper),
                     "certified_cells":count,"target_met":upper<=target})
    return {"schema":"p4-s7-analytic-exit-stability/1","face_count":len(rows),
            "all_local_targets_met":len(rows)==44 and all(x["target_met"] for x in rows),
            "maximum_height_difference_upper_mm":max(x["exit_height_upper_mm"] for x in rows),
            "scope":"Continuous effect on same-parameter positive analytic s7 exit graph height; clamp negative squared heights to zero at the start. Native branch membership and s8 correspondence are separate.",
            "method":"Exact Bernstein local difference bounds, outward square roots, adaptive split near the tangent start.",
            "execution_approved":False,"faces":rows}



def paired_cells(a,b):
    cuts=unite_partitions(a,b)
    matrix=_bernstein_matrix_inverse(3)
    return [(_controls(a,s,t,matrix),_controls(b,s,t,matrix)) for s,t in zip(cuts,cuts[1:])]


def s8_constants(plan,capture,supports):
    names={row["face_tag_session_only"]:row["p3_support_id"] for row in supports["faces"]}
    geometries={row["detail"]["face_tag"]:row["detail"]["topology"]["geometry"] for row in capture["results"]}
    n,= [geometries[k] for k,id in names.items() if id=="stock.s8"]
    if n["type"]!=204 or n["axis"] not in ([0,1,0],[0,-1,0]) or n["center"][0]!=0 or n["center"][2]!=0:
        raise ValueError("s8 torus is not on the canonical stock axis")
    stock=plan["construction"]["profiles"]["stock_profile"]
    nominal=next(row for row in stock["curves"] if row["id"]=="s8")
    dy,major=map(Q,nominal["center_y_r_mm"])
    reference=(dy+71,major,Q(nominal["radius_mm"]))
    actual=(Q(n["center"][1])+71,Q(n["major_radius"]),Q(n["minor_radius"]))
    for transition,m,r in (reference,actual):
        # Over v=Y+71 in [1.2,2.6], |v-transition| <= 1.5.
        # Then the lower torus radicand is >4.6^2, R<14, and
        # 2*R*R' <= 6.1*max(v-1.23,0) for the inner branch.
        if not (Q('1.23')<=transition<=Q('1.24') and r>=Q('4.9')
                and r<=Q('5.1') and m-Q('4.6')<14):
            raise ValueError("s8 derivative envelope does not hold")
    delta=[abs(a-b) for a,b in zip(actual,reference)]
    # |partial R/partial r| <= 2 and |partial R/partial transition| <= 1.
    return delta[1]+2*delta[2]+delta[0],names,geometries


def assess_s8_exit_graphs(capture,supports,plan):
    R_error,names,geometries=s8_constants(plan,capture,supports)
    nodes={row["id"]:row for row in plan["construction"]["nodes"]}
    templates=plan["construction"]["profiles"]["section6"]["templates"]
    results=[]
    for key,id in names.items():
        if not id.endswith(".roll"):
            continue
        member,side,_=id.split(".")
        direction=v(nodes[member+"_roll_tool"]["axis_direction"])
        record,params=native(geometries[key],direction,(Q('12.1665'),Q('12.1665')))
        M,_,t_error,l_error,_,m_error=params
        a,b=paired_curves(record,nominal(templates[side]))
        cells=paired_cells(a,b)
        actual=[row for left,_ in cells for row in left]
        reference=[row for _,right in cells for row in right]
        for controls,error in ((actual,l_error),(reference,Q(0))):
            low,high=bounds(controls,1,error)
            if not Q('2.9')<=low<=high<=4 or M[0]<Q('14.99') or M[1]>Q('15.01'):
                raise ValueError("roll strip does not fit the s8 derivative envelope")
        dt=max(abs(x[0]-y[0]) for x,y in zip(actual,reference))+t_error
        dl=max(abs(x[1]-y[1]) for x,y in zip(actual,reference))+l_error
        ma=max(map(abs,bounds(actual,0,t_error)))
        mb=max(map(abs,bounds(reference,0)))
        # n(v)=M-sqrt(L^2-v^2) with 1.2<=v<=2.6.
        # |dn/dL|<4 from L in [2.9,4] and the positive sqrt >=1.
        dn=m_error+4*dl
        delta_F=(ma+mb)*dt+(M[1]+15)*dn+28*R_error
        # dF/dv >= 5.4v - 6.1 max(v-1.23,0) > 5
        # for F=t^2+n^2-R_s8^2 and v in [1.2,2.6].
        height=delta_F/5
        results.append({"face_tag_session_only":key,"carrier":id,"s8_height_difference_upper_mm":upper_float(height)})
    return {"schema":"p4-s8-analytic-exit-stability/1","face_count":len(results),
            "maximum_height_difference_upper_mm":max(x["s8_height_difference_upper_mm"] for x in results),
            "interval_y_plus_71_mm":[1.2,2.6],"lower_dF_dY_mm":5,
            "scope":"Same-parameter analytic s8 graph height where both positive branch roots occur in the indicated window. Finite branch and seam membership are separate.",
            "method":"Exact Bernstein pointwise generator error and rational derivative lower bound; no converted spline deviation is assumed.",
            "execution_approved":False,"faces":results}

def face_edges(topology):
    for loop in topology["children"]:
        for fin in loop["child"]["children"]:
            yield fin["child"]["children"][0]["child"]


def assess_roll_patches(capture,supports,plan,s7,s8):
    """Conditional patch bound retaining the existing first-exit/loop contract."""
    R8err,names,geometries=s8_constants(plan,capture,supports)
    byrole={r["role"]:r["inventory"] for r in capture["selection"]}
    face={row["detail"]["face_tag"]:row["detail"]["topology"] for row in capture["results"]}
    neighbors=defaultdict(set)
    edges={}
    bounds_by_face={}
    uv_by_face={}
    for row in capture["results"]:
        k=row["detail"]["face_tag"]
        bounds_by_face[k]=byrole[row["role"]]["uf_face_data"]["bounding_box_mm"]
        uv_by_face[k]=row["detail"]["uv_box"]
        for e in face_edges(face[k]):
            edges[e["tag"]]=e
            neighbors[e["tag"]].add(k)
    transitions=[edges[k] for k,fs in neighbors.items() if {names[f] for f in fs}=={"stock.s7","stock.s8"}]
    if len(transitions)!=22:
        raise ValueError("native stock s7/s8 seam coverage changed")
    p={p["id"]:Q(p["value"]) for p in plan["parameters"]["regional"]}
    for e in transitions:
        g=e["geometry"]
        if (e["geometry_class"]!=10 or g["type"]!="circular_evaluator"
                or Q(g["center"][1])!=p["stock.Y7"] or g["x_axis"][1]!=0 or g["y_axis"][1]!=0):
            raise ValueError("s7/s8 seams do not use the common transverse station")
    rn=tuple(Q(geometries[k]["radius"]) for k,name in names.items() if name=="stock.s7")
    rerror=max(abs(q-Q("12.1665")) for q in rn)
    tor,=[geometries[k] for k,name in names.items() if name=="stock.s8"]
    if Q(tor["center"][1])!=p["stock.Y7"]:
        raise ValueError("native torus center does not use the shared transition station")
    jump_r=max(abs(Q(tor["major_radius"])-Q(tor["minor_radius"])-r) for r in rn)
    ideal_s8=next(r for r in plan["construction"]["profiles"]["stock_profile"]["curves"] if r["id"]=="s8")
    ideal_jump=abs(Q(ideal_s8["center_y_r_mm"][1])-Q(ideal_s8["radius_mm"])-Q("12.1665"))
    # At the common seam any rounding jump changes F by <= 28 times the
    # radial jump. This adds to the away-from-tangency root comparison.
    splice_penalty=28*(jump_r+ideal_jump+max(Q(0),rerror-R8err))/5
    s7map={r["face_tag_session_only"]:Q(r["exit_height_upper_mm"]) for r in s7["faces"]}
    s8map={r["face_tag_session_only"]:Q(r["s8_height_difference_upper_mm"]) for r in s8["faces"]}
    nodes={n["id"]:n for n in plan["construction"]["nodes"]}
    templates=plan["construction"]["profiles"]["section6"]["templates"]
    result=[]
    for id,name in names.items():
        if not name.endswith(".roll"):
            continue
        member,side,_=name.split(".")
        topo=face[id]
        incidences=[]
        for e in face_edges(topo):
            others=neighbors[e["tag"]]-{id}
            if len(others)!=1:
                raise ValueError("roll boundary is not a two-face edge")
            neighbor=names[others.pop()]
            incidences.append((e["geometry_class"],neighbor))
            if neighbor==member+"."+side+".linear":
                seam=e["geometry"]
                if seam["type"]!=102:
                    raise ValueError("expected a spline on the linear-to-roll seam")
                poles=seam["weighted_poles_flat_xyzw"]
                if any(abs(Q(yy)/Q(w)+71)>Q('0.0000001') for yy,w in zip(poles[1::4],poles[3::4])):
                    raise ValueError("linear-to-roll seam does not lie at its expected station")
        expected={(10,member+"."+side+".linear"),(10,member+".roll_root"),(11,"stock.s7"),(11,"stock.s8")}
        if set(incidences)!=expected or len(incidences)!=4 or len(topo["children"])!=1:
            raise ValueError("native roll face does not have the expected four-edge loop")
        box=bounds_by_face[id]
        _,_,v0,v1=uv_by_face[id]
        if box[4]>-68.4 or not 0.7<v0<v1<1.571:
            raise ValueError("native trim is outside the supported axial roll window")
        direction=v(nodes[member+"_roll_tool"]["axis_direction"])
        g=geometries[id]
        native_curve,params=native(g,direction,(min(rn),max(rn)))
        M,_,t_err,l_err,_,m_err=params
        a,b=paired_curves(native_curve,nominal(templates[side]))
        cells=paired_cells(a,b)
        dt=max(abs(x[0]-y[0]) for ac,bc in cells for x,y in zip(ac,bc))+t_err
        dl=max(abs(x[1]-y[1]) for ac,bc in cells for x,y in zip(ac,bc))+l_err
        # If either root is below 1.2, s7 continuity keeps its counterpart
        # below the common seam; in this range dn/dv < 1/2. Otherwise use
        # the high-branch derivative and seam perturbation over [1.2,2.6].
        early=s7map[id]
        if Q('1.2')+early>Q('1.201') or Q('1.201')>p["stock.Y7"]+71:
            raise ValueError("s7 bound is too wide for the early-branch split")
        low=sqrt_bounds(Q('2.9')**2-Q('1.201')**2)[0]
        if Q('1.201')/low>=Q('0.5'):
            raise ValueError("early radial derivative too large")
        # M near 15 and the actual maximum L below 3.69 make the first exit
        # occur before 2.6 on both analytic branches.
        lambda_hi=max(row[1] for a_control,b_control in cells for row in a_control+b_control)+l_err
        if lambda_hi>Q('3.69') or M[0]-sqrt_bounds(lambda_hi**2-Q('2.6')**2)[1]<=Q('12.37'):
            raise ValueError("synthetic upper first-exit witness is insufficient")
        # The torus from s8 is bounded above by 12.37 at 2.6, both previews.
        upper_r=max(Q(tor["major_radius"])-sqrt_bounds(Q(tor["minor_radius"])**2-
                    (Q('2.6')-(Q(tor["center"][1])+71))**2)[0],
                    Q(ideal_s8["center_y_r_mm"][1])-sqrt_bounds(Q(ideal_s8["radius_mm"])**2-
                    (Q('2.6')-(Q(ideal_s8["center_y_r_mm"][0])+71))**2)[0])
        if upper_r>=Q('12.37'):
            raise ValueError("upper s8 stock clearance not established")
        late=s8map[id]+splice_penalty
        axis_error=direction_gap(v(g["axis"]),direction)
        frame_error=36*(axis_error+abs(dot(direction,direction)-1))
        same_height=2*dt+2*(m_err+4*dl)+frame_error
        face_bound=same_height+max(2*early,7*late)
        result.append({"face_tag_session_only":id,"carrier":name,"conditional_patch_upper_mm":upper_float(face_bound),
                       "early_height_upper_mm":upper_float(early),"late_height_upper_mm":upper_float(late)})
    return {"schema":"p4-roll-conditional-finite-patches/1","face_count":len(result),
            "maximum_conditional_patch_upper_mm":max(r["conditional_patch_upper_mm"] for r in result),
            "conditional_on":["each class11 edge follows the selected actual-parent intersection graph",
                              "one finite material-side roll patch selected between its verified loop edges",
                              "the original P3 finite domain and C14 face chart share the identified corresponding branch"],
            "scope":"Matched early and late positive roll exit graphs and full patch interpolation, under named finite-branch assumptions.",
            "execution_approved":False,"faces":result}


def _roll_facet_clearance(data, stock_radius, stock_torus=None):
    """Continuous stock-clearance residual along an original EXIT edge."""
    points=[v(p) for p in data['points_mm']]
    tol=Q(data['chord_tolerance_mm'])
    vertex=Q(data['max_vertex_deviation_mm'])
    pmin,pmax=data['original_edge_parameter_limits']
    orientation=1 if pmax>pmin else -1
    params=data['original_edge_parameters']
    if (len(params)!=len(points) or (params[0],params[-1])!=(pmin,pmax)
            or any(orientation*(b-a)<=0 for a,b in zip(params,params[1:]))
            or Q(data['max_midpoint_deviation_mm'])>tol):
        raise ValueError('rolled flank facet coverage is incomplete')
    errors=[]
    for x,y,z in points:
        radial=sqrt_bounds(x*x+z*z)
        if stock_torus is None:
            outer=(stock_radius,stock_radius)
        else:
            cy,m,r=stock_torus
            if abs(y-cy)>=Q('1.9') or r<=Q('4.99'):
                raise ValueError('rolled flank stock clip leaves the s8 meridian window')
            a,b=sqrt_bounds(r*r-(y-cy)**2)
            outer=(m-b,m-a)
        errors.append(max(abs(a-b) for a in radial for b in outer))
    residual=Q(0)
    for a,b,e1,e2 in zip(points,points[1:],errors,errors[1:]):
        x,y,z=a
        xx,yy,zz=b
        if (sum((p-q)**2 for p,q in zip(a,b))<=(2*vertex)**2
                or min(x*x+z*z,x*xx+z*zz,xx*xx+zz*zz)<=121):
            raise ValueError('facet chain lacks a positive radial chart or ordered chord endpoints')
        curvature=((x-xx)**2+(z-zz)**2)/11
        if stock_torus:
            curvature+=Q('.3')*(y-yy)**2
        residual=max(residual,max(e1,e2)+curvature/8)
    # 3D Lipschitz constants of r-stock(Y), including the documented
    # native edge distance plus the endpoint-matched clamped projection.
    return residual+(Q('1.2') if stock_torus else 1)*(tol+vertex)


def _root_final_height(t,arm,s8_parameters):
    y7,major,tube=s8_parameters
    def residual(h):
        n=15-sqrt_bounds(arm*arm-h*h)[0]
        nlow=15-sqrt_bounds(arm*arm-h*h)[1]
        rmin,rmax=sqrt_bounds(nlow*nlow+t*t)[0],sqrt_bounds(n*n+t*t)[1]
        lo,hi=sqrt_bounds(tube*tube-(h-71-y7)**2)
        return rmin-major+lo,rmax-major+hi
    a,b=Q('2.1'),Q('2.6')
    if residual(a)[1]>=0 or residual(b)[0]<=0:
        raise ValueError('rolled root endpoint does not have a bracketed s8 exit')
    for _ in range(47):
        m=(a+b)/2
        lo,hi=residual(m)
        if lo>0:
            b=m
        elif hi<0:
            a=m
        else:
            raise ValueError('insufficient rational precision in the root exit bracket')
    return a-71,b-71


def verify_c5_rolled_flank_patches(capture,support_index,plan,conditional,straight,roots,facets,limit=Q('.000141')):
    """Verify C14 rolled flanks one at a time through the early and late exit charts."""
    from .nx2506_c5_straight_trim import _canonical_straight_transfer
    from .nx2506_carrier_bound import supports
    from .nx2506_stock_bands import _exact_stock_parameters

    if (facets.get('schema')!='p4-native-c5-straight-facets/1' or facets.get('kind')!='roll_flank'
            or facets.get('status')!='complete' or facets.get('disk_copy_unchanged') is not True
            or straight.get('status')!='within_limit' or roots.get('status')!='within_limit'):
        raise ValueError('original C14 flank boundary and shared front/root evidence required')
    r8_error,names,geometry=s8_constants(plan,capture,support_index)
    topology={r['detail']['face_tag']:r['detail']['topology'] for r in capture['results']}
    pairs=defaultdict(set)
    for tag,t in topology.items():
        for edge in face_edges(t):
            pairs[edge['tag']].add(tag)
    s8=next(v_ for key,v_ in geometry.items() if names[key]=='stock.s8')
    stock_s8=(Q(s8['center'][1]),Q(s8['major_radius']),Q(s8['minor_radius']))
    stock=plan['construction']['profiles']['stock_profile']
    s8_preview=next(c for c in stock['curves'] if c['id']=='s8')
    p3_s8=(*map(Q,s8_preview['center_y_r_mm']),Q(s8_preview['radius_mm']))
    p3_radius=Q(stock['vertices'][7]['radius_mm'])
    p3_cone,=[r for r in supports(plan) if r[0]=='stock.s6']
    exact=_exact_stock_parameters(plan)
    stock_transfer=sum(max(abs(Q(value)-nominal) for value in (exact[key].lo,exact[key].hi))
                       for key,nominal in zip(('Y7','M8','tube_R8'),p3_s8))
    profiles=plan['construction']['profiles']['section6']['templates']
    frames={p['id']:p['frame'] for p in plan['construction']['nodes'] if p['id'].endswith('_straight_tool')}
    root_maps={r['p3_support_id']:r for r in roots['faces']}
    straight_maps={r['p3_support_id']:r for r in straight['faces']}
    result=[]
    for row in sorted(conditional['faces'],key=lambda r:r['carrier']):
        name,tag=row['carrier'],row['face_tag_session_only']
        member,side,_=name.split('.')
        frame=frames[member+'_straight_tool']
        section=facets['faces'][name]
        neighbors={}
        for e in face_edges(topology[tag]):
            other,=pairs[e['tag']]-{tag}
            neighbors[names[other]]=(e,other)
        s7=geometry[neighbors['stock.s7'][1]]
        if set(neighbors)!={name.replace('.roll','.linear'),member+'.roll_root','stock.s7','stock.s8'}:
            raise ValueError('original rolled flank loop no longer has four expected phases')
        front=neighbors[name.replace('.roll','.linear')][0]
        recent=section['upper_endpoints_mm']
        saved=sorted(v_['child']['geometry']['point'] for v_ in front['children'])
        if any(sum(abs(Q(x)-Q(y)) for x,y in zip(a,b))>Q('0.00000001') for a,b in zip(recent,saved)):
            raise ValueError('front start-curve physical identity differs')
        native_s7=Q(s7['radius'])
        axis=v(frame['e_t'])
        carrier,pars=native(geometry[tag],axis,(native_s7,native_s7))
        a,b=paired_curves(carrier,nominal(profiles[side]))
        cells=paired_cells(a,b)
        magnitude=1 if side=='F0002' else -1
        for actual,expected in cells:
            if any(not Q('2.9')-Q('.001')<p[1]<Q('3.69')+Q('.001') for p in actual+expected):
                raise ValueError('rolled flank leaves its non-singular radial chart')
            for points in (actual,expected):
                for u,w in zip(points,points[1:]):
                    dt=magnitude*(w[0]-u[0])
                    if not dt or -(w[1]-u[1])/dt<Q('.64'):
                        raise ValueError('rolled flank radial graph is not strict enough for clearance transport')
        # Restrict the closest-to-axis bounds to the finite active endpoints.
        endpoints_=[_evaluate(b,v_) for v_ in (b['a'],b['b'])]
        root_end=min(endpoints_,key=lambda p:abs(p[0]))
        if min(p[1] for p in endpoints_)<Q('2.9'):
            raise ValueError('rolled flank lower arm below the 2.9 mm speed guard')
        yexit=_root_final_height(root_end[0],root_end[1],p3_s8)
        nominal_intervals={'s7':((Q(-71),Q(-71)),(p3_s8[0],p3_s8[0])),
                           's8':((p3_s8[0],p3_s8[0]),yexit)}
        _,_,t_round,l_round,_,m_round=pars
        dt=max(abs(x[0]-y[0]) for p,q in cells for x,y in zip(p,q))+t_round
        dl=max(abs(x[1]-y[1]) for p,q in cells for x,y in zip(p,q))+l_round
        frame_error=36*(direction_gap(v(geometry[tag]['axis']),axis)+abs(dot(axis,axis)-1))
        arm_min=min(p[1] for actual,expected in cells for p in actual+expected)-l_round
        # Equal Y motion decomposes into transverse and radial changes.
        # For n=M-sqrt(L²-v²), |dn/dL| is largest at the smallest
        # arm and largest checked axial height.
        arm_gain=arm_min/sqrt_bounds(arm_min**2-Q('2.6')**2)[0]
        radial_error=m_round+arm_gain*dl
        transport=sqrt_bounds(dt*dt+radial_error*radial_error)[1]+frame_error
        if transport>=limit:
            raise ValueError('rolled face cannot be transported to its equal-Y candidate chart')
        phase_moves={}
        for phase,higher,axial_speed in (('s7',Q('.5'),Q('1.2')),('s8',Q(2),Q('2.3'))):
            chain=section['exits'][phase]
            ya,yb=sorted(Q(chain['points_mm'][k][1]) for k in (0,-1))
            target=nominal_intervals[phase]
            ends_error=max(abs(o-y) for o,bounds in zip((ya,yb),target) for y in bounds)
            pad=ends_error+Q(chain['chord_tolerance_mm'])+Q(chain['max_vertex_deviation_mm'])+Q('0.00000001')
            field=_roll_facet_clearance(chain,native_s7,stock_s8 if phase=='s8' else None)
            stock_error=r8_error if phase=='s8' else abs(native_s7-p3_radius)
            if phase=='s8':
                radius_max=max(sqrt_bounds(Q(x)**2+Q(z)**2)[1] for x,_,z in chain['points_mm'])
                # The existing broad axial speed bound <2.3 first
                # encloses the whole small Y readjustment. Here n<=rho
                # remains below 12.4. With v<=2.6 and M=15 this gives
                # |n_v|<=1, hence physical speed <1.42 and |F_v|<1.01.
                if (radius_max+Q(chain['chord_tolerance_mm'])+Q(chain['max_vertex_deviation_mm'])
                        +transport+3*pad<Q('12.4') and max(yb,*target[1])+pad<Q('-68.4')
                        and min(ya,*target[0])-pad>p3_s8[0]-Q('.001')):
                    higher,axial_speed=Q('1.01'),Q('1.42')
            # First adjust Y. Then at fixed Y, radial clearance is strict
            # in outward |t|. Since n/rho>.99 and dn/d|t|>.64, actual
            # path length per unit of clearance is <2.1 on the common sheet.
            phase_moves[phase]=axial_speed*pad+Q('2.1')*(field+transport+stock_error+higher*pad)
        inside,outside=section['material_anchors']
        pin=v(inside['carrier_point_mm'])
        if (inside['containment_status']!=1 or outside['containment_status']!=2
                or not Q('-70.9')<pin[1]<Q('-70.7') or outside['carrier_point_mm'][1]>=-71
                or sqrt_bounds(pin[0]**2+pin[2]**2)[1]>=p3_radius-Q('.01')):
            raise ValueError('rolled flank original material witness not in the common interior')
        # Shared root guide has continuous arc matching and the front
        # uses the same stored spline as the already verified straight wall.
        root_record=root_maps[member+'.roll_root']
        root=Q(root_record.get('rolled_side_arc_upper_mm',root_record['continuous_bidirectional_patch_upper_mm']))
        front_bound=Q(straight_maps[name.replace('.roll','.linear')]['native_trim_upper_mm'])
        movement=max(root,front_bound,*phase_moves.values())
        transfer=20*(stock_transfer+_canonical_straight_transfer(
            plan,profiles[side],frame,int(member.rsplit('_',1)[1]),p3_cone,exact,Q(20)))
        # In the common section-parameter/Y chart each original loop is
        # paired continuously, phase by phase, to the canonical loop.
        # Common inside/exterior witnesses fix the filled-domain choice.
        # Points whose winding changes are covered by the moving paths.
        total=movement+transport+transfer
        result.append({'p3_support_id':name,'s7_boundary_path_mm':upper_float(phase_moves['s7']),
                       's8_boundary_path_mm':upper_float(phase_moves['s8']),
                       'preview_transfer_upper_mm':upper_float(transfer),
                       'continuous_bidirectional_patch_upper_mm':upper_float(total),
                       'status':'within_limit' if total<=limit else 'bound_exceeds_limit'})
    if len(result)!=44 or {r['p3_support_id'] for r in result}!=set(facets['faces']):
        raise ValueError('rolled flank evidence coverage differs')
    return {'schema':'p4-native-c5-rolled-flank-finite-patches/1','faces':result,'face_count':len(result),
            'status':'within_limit' if all(r['status']=='within_limit' for r in result) else 'bound_exceeds_limit',
            'continuous_bidirectional_patch_upper_mm':max(r['continuous_bidirectional_patch_upper_mm'] for r in result),
            'scope':'Complete rolled flank surfaces with separate original s7/s8 exits and NX trim witnesses.',
            'execution_approved':False}
