"""Exact support-surface comparison for the analytic P4 face records.

These bounds use the recorded binary64 P3 preview and UF carrier parameters
as exact inputs. They cover the untrimmed supports, not the retained patches.
"""
from collections import Counter
from fractions import Fraction as Q
import math

from .nx2506_trim_bound import _curve, _evaluate, _product, bound_trim_pair


def v(x):
    return tuple(map(Q, x))


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def dot(a, b):
    return sum((x*y for x, y in zip(a, b)), Q())


def l1(a):
    return sum(map(abs, a), Q())


def norm_lower(vect):
    return max(map(abs, vect))


def direction_gap(a, b):
    """Bound distance between unit representatives of two unoriented axes."""
    if dot(a, b) < 0:
        b = tuple(-x for x in b)
    return 2*l1(sub(a, b)) / min(norm_lower(a), norm_lower(b))


def extent(point, box):
    return sum((max(abs(box[i]-p),abs(box[i+3]-p)) for i,p in enumerate(point)), Q())


def projection_anchor(point, axis, target):
    scale = dot(sub(target, point), axis) / dot(axis, axis)
    return tuple(p+scale*d for p,d in zip(point,axis))


def upper_float(x):
    result = float(x)
    return math.nextafter(result, math.inf) if Q(result)<x else result


def supports(plan):
    profiles = plan["construction"]["profiles"]
    p = {row["id"]: row["value"] for row in plan["parameters"]["regional"]}
    nodes = {row["id"]: row for row in plan["construction"]["nodes"]}
    result = []
    def add(id, ty, point, axis=(0,1,0), radius=0, minor=0):
        result.append((id, ty, v(point), v(axis), Q(radius), Q(minor)))

    stock=profiles["stock_profile"]
    vertices={row["id"]:row for row in stock["vertices"]}
    for c in stock["curves"]:
        a,b=(vertices[c[key]] for key in ("start","end"))
        ya,yb=a["y_mm"],b["y_mm"]
        ra,rb=a["radius_mm"],b["radius_mm"]
        if c["kind"]=="circular_arc":
            y,r=c["center_y_r_mm"]
            add("stock."+c["id"],19,(0,y,0),radius=r,minor=c["radius_mm"])
        elif ya==yb:
            add("stock."+c["id"],22,(0,ya,0))
        elif ra==rb and ra>0:
            add("stock."+c["id"],16,(0,ya,0),radius=ra)
        elif ra!=rb:
            slope=(Q(rb)-Q(ra))/(Q(yb)-Q(ya))
            apex=Q(ya)-Q(ra)/slope
            add("stock."+c["id"],17,(0,apex,0),axis=(0,1 if slope>0 else -1,0),radius=abs(slope))

    add("tail.left_wall",22,(-p["slot.width"]/2,0,0),axis=(1,0,0))
    add("tail.right_wall",22,(p["slot.width"]/2,0,0),axis=(1,0,0))
    add("tail.cylinder",16,(0,p["slot.axis_y"],p["slot.axis_z"]),axis=(1,0,0),radius=p["slot.radius"])
    for name,y in (("R31",0),("R32",0),("R40",p["head.Y40"])):
        add("head."+name,18,(0,y,0),radius=p["head."+name])
    for key in ("Y_lower_step","Y_head_step","lower_sphere_contact_y","upper_sphere_contact_y"):
        add("head."+key,22,(0,p["head."+key],0))
    add("head.cone",17,(0,p["head.cone_apex_Y"],0),
        radius=math.tan(p["head.cone_half_angle_initial_exact"]))
    for key in ("lower","upper"):
        add("head."+key+"_fillet",19,(0,p[f"head.{key}_fillet_y"],0),
            radius=p[f"head.{key}_fillet_major"],minor=p[f"head.r_{key}_fillet"])
    for i in range(6):
        prefix=f"head.sector.{i}."
        theta=p[prefix+"theta"]
        ax,az=math.cos(theta),math.sin(theta)
        add(prefix+"A_piece",19,(0,p["head.Y40"],0),axis=(ax,0,az),radius=p[prefix+"RA"],minor=p[prefix+"ra"])
        for j in range(2):
            key=prefix+f"branch.{j}."
            d=Q(p[key+"d"])
            add(key+"B_piece",19,(d*Q(ax),p["head.Y40"],d*Q(az)),axis=(ax,0,az),
                radius=p[key+"major_radius"],minor=p[key+"rb"])
            s=Q(p[key+"contact_s"])
            add(key+"seam",22,(s*Q(ax),0,s*Q(az)),axis=(ax,0,az))

    root=profiles["section6"]["edges"][5]
    root_y, root_r = root["center_t_r_mm"]
    if root_y!=0:
        raise ValueError("C5 section root center must have zero tangent coordinate")
    roll_r=next(item["value"] for item in plan["parameters"]["fixed_auxiliaries"] if item["id"]=="roll_axis_radius")
    for i in range(22):
        name=f"member_{i:02d}"
        s=nodes[name+"_straight_tool"]["frame"]["e_r"]
        add(name+".straight_root",16,(Q(root_r)*Q(s[0]),0,Q(root_r)*Q(s[2])),radius=root["radius_mm"])
        node=nodes[name+"_roll_tool"]
        add(name+".roll_root",19,node["axis_point_mm"],axis=node["axis_direction"],
            radius=abs(Q(roll_r)-Q(root_r)),minor=root["radius_mm"])
    return result


def tangent_range(x):
    """Exact rational sine/cosine Taylor bounds for positive cone half angles."""
    if not 0 < x < Q(5,4):
        raise ValueError("cone half angle outside supported domain")
    def trig(offset):
        end=20+offset
        value=sum(((-1)**i*x**(2*i+offset)/math.factorial(2*i+offset)
                   for i in range(10)),Q())
        remainder=x**end/math.factorial(end)
        return value-remainder,value+remainder
    slo,shi=trig(1)
    clo,chi=trig(0)
    if clo<=0:
        raise ValueError("cone cosine interval reaches zero")
    return slo/chi,shi/clo


def bound(record, candidate, box):
    _,kind,p,axis,r,minor=candidate
    q=v(record["point"])
    a=v(record["direction"])
    actual_r,actual_minor=Q(record["radius"]),Q(record["rad_data"])
    if kind==18:
        return l1(sub(q,p))+abs(actual_r-r), None
    if not norm_lower(a) or not norm_lower(axis):
        raise ValueError("zero normal or axis")
    rotation=direction_gap(axis,a)
    angle_degrees=90*rotation   # 2*asin(chord/2) <= (pi/2)*chord
    if kind==22:
        forward=abs(dot(a,sub(p,q)))/norm_lower(a)+rotation*extent(p,box)
        reverse=abs(dot(axis,sub(p,q)))/norm_lower(axis)+rotation*extent(q,box)
        return max(forward,reverse),angle_degrees
    if kind==16:
        q=projection_anchor(q,a,p)
        return l1(sub(q,p))+abs(actual_r-r)+rotation*max(extent(p,box),extent(q,box)),angle_degrees
    if kind==17:
        # Cone carriers are positive half-cones with the axis away from the apex.
        # radius here is the reference slope. Native rad_data is its half angle.
        low,high=tangent_range(actual_minor)
        slope_error=max(abs(low-r),abs(high-r))
        scale=max(extent(q,box),extent(p,box))
        return l1(sub(q,p))+(rotation+slope_error)*scale, angle_degrees+60*slope_error
    if kind==19:
        return (l1(sub(q,p))+abs(actual_r-r)+abs(actual_minor-minor)
               +rotation*max(actual_r+actual_minor,r+minor)),angle_degrees
    raise ValueError("unimplemented face support type")


def assess_analytic_carriers(inventory,plan):
    if inventory["status"]!="INVENTORY_COMPLETE" or plan["schema"]!="p3-final-mathematical-plan/1":
        raise ValueError("complete C14 inventory and accepted P3 plan required")
    known=supports(plan)
    # Common bounding volume. UF_MODL_ask_face_data boxes contain their
    # corresponding faces. Include the accepted P3 stock enclosure as well.
    stock=plan["construction"]["implementation_route"]["solid_enclosure"]["default_binary64_outward_preview"]
    r,y0,y1=map(Q,(stock["radial_upper_mm"],stock["y_lower_mm"],stock["y_upper_mm"]))
    boxes=[v(f["uf_face_data"]["bounding_box_mm"]) for f in inventory["faces"]]+[(-r,y0,-r,r,y1,r)]
    box=tuple(min(b[i] for b in boxes) if i<3 else max(b[i] for b in boxes) for i in range(6))
    results=[]
    for f in inventory["faces"]:
        d=f["uf_face_data"]
        kind=d["type"]
        candidates=[c for c in known if c[1]==kind]
        row={"face_tag_session_only":f["tag_session_only"],"uf_type":kind}
        if kind==19 and d["radius"]==0:
            candidates=[]
            row["reason"]="general revolved surface; UF face data carries axis but not the generator"
        if kind==17:
            candidates=[]
            row["reason"]="UF face data gives a section radius and unoriented axis, not the cone apex and nappe"
        if not candidates:
            row["status"]="unsupported_support"
        else:
            best=None
            for c in candidates:
                geom,angular=bound(d,c,box)
                if best is None or geom<best[0]:
                    best=(geom,angular,c[0])
            geom,angular,kind_id=best
            ok=geom<=Q("0.000141") and (angular is None or angular<=Q("0.01"))
            row.update(status="carrier_bound" if ok else "no_matching_carrier",
                       p3_support_id=kind_id, distance_upper_mm=upper_float(geom),
                       axis_or_plane_angle_upper_deg=upper_float(angular) if angular is not None else None)
        results.append(row)
    accepted=[row for row in results if row["status"]=="carrier_bound"]
    return {"schema":"p4-analytic-carrier-bounds/1",
            "face_count":len(results),"counts":dict(Counter(row["status"] for row in results)),
            "max_accepted_support_upper_mm":max((row["distance_upper_mm"] for row in accepted),default=None),
            "scope":"Untrimmed parent carriers. Plane and cylinder directions are bounded over the common containing box. Axes and origins are UF/P3 binary64 preview data.",
            "remaining":"Cone and freeform support data, finite trim correspondence and material coverage require separate proof.",
            "faces":results,"execution_approved":False}



def exact(value):
    return [value.numerator, value.denominator]


def source_curve(template, frame, axis_point=None):
    basis=template["basis"]
    et,er=v(frame["e_t"]),v(frame["e_r"])
    origin=v(frame["origin_mm"])
    poles=[]
    for pole in template["poles"]:
        t,r=Q(pole["t_mm"]["value"]),Q(pole["r_mm"]["value"])
        if axis_point is None:
            p=tuple(o+t*a+r*b for o,a,b in zip(origin,et,er))
        else:
            # The same carrier is swept by a quarter-turned generator.
            at=v(axis_point)
            p=(at[0]+t*et[0],at[1]+Q(15)-r,at[2]+t*et[2])
        poles.append([*map(exact,p),1])
    return {"order":basis["order"], "knots":basis["knots_exact"], "poles":poles,
            "periodic":False,"interval":basis["fin_interval_exact"]}


def read_generator(record):
    if record["type"]!=102 or record["rational"]:
        raise ValueError("expected the C5 nonrational BREP spline generator")
    values=record["weighted_poles_flat_xyzw"]
    return {"order":record["order"],"knots":record["knots"],
            "poles":[values[i:i+4] for i in range(0,len(values),4)],
            "periodic":False,"interval":[record["start"],record["end"]]}


def endpoints(curve):
    c=_curve(curve)
    result=[]
    for t in (c["a"],c["b"]):
        point=_evaluate(c,t)
        result.append(tuple(x/point[3] for x in point[:3]))
    return result


def sweep_candidates(plan):
    nodes={row["id"]:row for row in plan["construction"]["nodes"]}
    section=plan["construction"]["profiles"]["section6"]["templates"]
    result={205:[],206:[]}
    for i in range(22):
        name=f"member_{i:02d}"
        frame=nodes[name+"_straight_tool"]["frame"]
        roll=nodes[name+"_roll_tool"]
        axis=v(roll["axis_direction"])
        pivot=v(roll["axis_point_mm"])
        for name_side,template in section.items():
            curve=source_curve(template,frame)
            result[206].append((name+"."+name_side+".linear",curve,endpoints(curve),None,None))
            for axis_point in (None,roll["axis_point_mm"]):
                row=source_curve(template,frame,axis_point)
                result[205].append((name+"."+name_side+".roll",row,endpoints(row),axis,pivot))
    return result


def bound_brep_generator(g, candidates):
    curve=read_generator(g["generator"])
    kind=g["type"]
    if kind==206:
        if g["direction"] not in ([0,1,0],[0,-1,0]):
            raise ValueError("C5 extraction expected a vertical extrusion")
        # Translating the spline along its extrusion direction leaves the
        # complete carrier unchanged. Use the common start plane for comparison.
        for row in curve["poles"]:
            row[1]=-71*row[3]
    actual=endpoints(curve)
    options=[]
    for id,ref,expected,axis,pivot in candidates[kind]:
        for reverse in (False,True):
            pts=list(reversed(expected)) if reverse else expected
            endpoint_gap=max(l1(sub(a,b)) for a,b in zip(actual,pts))
            options.append((endpoint_gap,rev_curve(ref,reverse),id,axis,pivot))
    gap,reference,id,axis,pivot=min(options,key=lambda entry:entry[0])
    if gap>Q('0.00025'):
        return {"status":"no_matching_generator","nearest_endpoint_gap_mm":upper_float(gap)}
    measure=bound_trim_pair(curve,reference)
    distance=Q(*measure["hausdorff_l1_upper_mm_exact"])
    angle=Q(0)
    if kind==205:
        native_axis=v(g["axis"])
        shift=l1(sub(projection_anchor(v(g["point_on_axis"]),native_axis,pivot),pivot))
        rotation=direction_gap(axis,native_axis)
        nominal=_curve(reference)["poles"]
        reach=max(l1(sub(tuple(x/p[3] for x in p[:3]),pivot)) for p in nominal)
        # Align axes by an isometry. Difference of the two rotations at
        # equal spin weights the direction change by at most twice the radius.
        distance+=2*shift+2*rotation*reach
        angle=90*rotation
    return {"status":"carrier_bound" if distance<=Q("0.000141") and angle<=Q("0.01") else "generator_above_budget",
            "p3_support_id":id,
            "distance_upper_mm":upper_float(distance),
            "axis_or_plane_angle_upper_deg":upper_float(angle),
            "bound_basis":"exact rational spline comparison and common-axis sweep correspondence"}


def rev_curve(curve, reverse):
    return dict(curve, interval=list(reversed(curve["interval"]))) if reverse else curve


def brep_carrier(g):
    kind=g["type"]
    if kind==201:
        return (16,{"point":g["point_on_axis"],"direction":g["axis"],"radius":g["radius"],"rad_data":0})
    if kind==202:
        return (17,{"point":g["point_at_apex"],"direction":g["axis"],"radius":0,"rad_data":g["half_apex_angle"]})
    if kind==203:
        return (18,{"point":g["center"],"direction":g["axis"],"radius":g["radius"],"rad_data":0})
    if kind==204:
        return (19,{"point":g["center"],"direction":g["axis"],"radius":g["major_radius"],"rad_data":g["minor_radius"]})
    if kind==209:
        return (22,{"point":g["point_on_plane"],"direction":g["normal"],"radius":0,"rad_data":0})
    raise ValueError("unsupported untrimmed BREP carrier")


def edited_root_arc_carrier(g, plan):
    """Bound a circular root's alternative rational cubic representation."""
    from .nx2506_roll_s7_bound import split, sqrt_bounds

    generator = g["generator"]
    if (g["type"] not in (205,206) or generator.get("type")!=102 or not generator.get("rational")
            or generator.get("order")!=4 or generator.get("num_poles")!=4
            or generator.get("knots")!=[0,0,0,0,1,1,1,1] or
            (generator.get("start"),generator.get("end")) not in ((0,1),(1,0))):
        raise ValueError("expected original rational cubic root meridian")
    roll = g["type"]==205
    if roll and (g["axis"][1]!=0 or g["point_on_axis"][1]!=-71):
        raise ValueError("edited roll root axis outside its horizontal chart")
    if not roll and g["direction"] not in ([0,1,0],[0,-1,0]):
        raise ValueError("edited straight root is not axial")
    flat = generator["weighted_poles_flat_xyzw"]
    poles = [v(flat[i:i+4]) for i in range(0,len(flat),4)]
    weights = [p[3] for p in poles]
    if len(poles)!=4 or min(weights)<=0:
        raise ValueError("invalid original rational root weights")
    section = plan["construction"]["profiles"]["section6"]
    root_arc = section["edges"][5]
    zero,pitch = map(Q,root_arc["center_t_r_mm"])
    radius = Q(root_arc["radius_mm"])
    if zero or not Q(".73")<radius<Q(".75"):
        raise ValueError("root supports outside the lower circular branch")
    ends = [section["templates"][side]["endpoints"]["root"] for side in ("F0002","F0024")]
    design = sorted(Q(p["t_mm"]["value"]) for p in ends)
    guides = {n["id"]:n for n in plan["construction"]["nodes"]}
    best = None
    pivot = v(g["point_on_axis"]) if roll else None
    for i in range(22):
        member = f"member_{i:02d}"
        frame = guides[member+"_straight_tool"]["frame"]
        et,er = v(frame["e_t"]),v(frame["e_r"])
        center_y = 15-pitch if roll else pitch
        t_weighted = [dot(p[:3],et) for p in poles]
        height_weighted = [(p[1]+71*p[3]) if roll else dot(p[:3],er) for p in poles]
        points = [(t/w,h/w) for t,h,w in zip(t_weighted,height_weighted,weights)]
        desired = sorted((Q(p["t_mm"]["value"]),
                          15-Q(p["r_mm"]["value"]) if roll else Q(p["r_mm"]["value"])) for p in ends)
        gap = max(l1(sub(a,b)) for a,b in zip(sorted((points[0],points[-1])),desired))
        if roll:
            gap += abs(dot(pivot,er)-15)
        proposal = (gap,member,et,er,center_y,t_weighted,height_weighted,points)
        if best is None or gap<best[0]:
            best = proposal
    gap,member,et,er,mid,t_weighted,height_weighted,points=best
    if gap>Q("0.00025"):
        raise ValueError("original rational root endpoints do not select a unique C5 member")
    # In the local coordinates the lower circle is represented by a
    # negative radial offset for a straight root and a positive arm for
    # a rolled root. The rational Bézier denominator is positive.
    sign = 1 if roll else -1
    if max(abs(p[0]) for p in points)>=Q(".60") or any(sign*(p[1]-mid)<=Q(".4") for p in points):
        raise ValueError("original rational root is outside the selected half-circle chart")
    delta = [b[0]-a[0] for a,b in zip(points,points[1:])]
    if not (all(d>0 for d in delta) or all(d<0 for d in delta)):
        raise ValueError("original rational root tangential projection is not monotone")
    # Positive rational Bézier weights and strictly ordered projected
    # control coordinates imply a strictly monotone coordinate curve.
    centered = [h-mid*w for h,w in zip(height_weighted,weights)]
    spans=[list(zip(t_weighted,centered,weights))]
    for _ in range(3):
        spans=[branch for span in spans for branch in split(span)]
    vertical=Q(0)
    for span in spans:
        t,z,w=zip(*span)
        residual=max(abs(x+y-radius*radius*zz) for x,y,zz in zip(
            _product(t,t),_product(z,z),_product(w,w)))
        t_extent=max(abs(x/c) for x,c in zip(t,w))
        actual_min=min(sign*x/c for x,c in zip(z,w))
        ideal_min=sqrt_bounds(radius*radius-t_extent*t_extent)[0]
        # Divide the circle polynomial by the positive rational weight
        # squared and by the sum of the two branch magnitudes at common t.
        vertical=max(vertical,residual/(min(w)**2*(actual_min+ideal_min)))
    observed = sorted((points[0][0],points[-1][0]))
    t_error = max(abs(a-b) for a,b in zip(observed,design))
    # Pair complete finite tangent intervals. Root chart |dr/dt|<1.6.
    basis = abs(dot(et,et)-1)+abs(dot(er,er)-1)+abs(dot(et,er))
    if basis>Q("0.000000001"):
        raise ValueError("edited C5 projection frame is not orthonormal")
    error = vertical+Q("2.6")*t_error+100*basis
    angle = Q(0)
    if roll:
        direction = v(g["axis"])
        expected_pivot = tuple(Q(15)*x for x in er)
        expected_pivot = (expected_pivot[0],Q(-71),expected_pivot[2])
        shift = l1(sub(projection_anchor(pivot,direction,expected_pivot),expected_pivot))
        yaw = direction_gap(v(et),direction)
        # Native root generator is in the vertical plane through its
        # transverse roll axis. Roll can be at any physical angular phase.
        plane = max(abs(dot(sub(tuple(x/p[3] for x in p[:3]),pivot),er)) for p in poles)
        error += 2*shift+100*yaw+plane
        angle = 90*yaw
    return {"status":"carrier_bound" if error<=Q("0.000141") and angle<=Q(".01") else "generator_above_budget",
            "p3_support_id":member+(".roll_root" if roll else ".straight_root"),
            "distance_upper_mm":upper_float(error),"axis_or_plane_angle_upper_deg":upper_float(angle),
            "circle_graph_residual_upper_mm":upper_float(vertical),
            "tangent_endpoint_shift_upper_mm":upper_float(t_error),
            "bound_basis":"original positive rational Bézier root chart with exact homogeneous circle residual"}


def assess_brep_carriers(capture,plan):
    if capture["status"]!="PROBES_RETURNED" or capture["scope"]!="all":
        raise ValueError("complete all-face C14 BREP readback required")
    candidates=supports(plan)
    generators=sweep_candidates(plan)
    selection={row["role"]:row["inventory"] for row in capture["selection"]}
    results=[]
    stock=plan["construction"]["implementation_route"]["solid_enclosure"]["default_binary64_outward_preview"]
    r,lo,hi=map(Q,(stock["radial_upper_mm"],stock["y_lower_mm"],stock["y_upper_mm"]))
    for row in capture["results"]:
        d=row["detail"]
        role=row["role"]
        if d["outcome"]!="CLEAN_TRACE":
            raise ValueError("native face read did not complete cleanly")
        g=d["topology"]["geometry"]
        actual=v(selection[role]["uf_face_data"]["bounding_box_mm"])
        p3box=(-r,lo,-r,r,hi,r)
        box=tuple(min(a,b) if i<3 else max(a,b) for i,(a,b) in enumerate(zip(actual,p3box)))
        if g["type"] in (205,206) and g["generator"].get("rational"):
            result=edited_root_arc_carrier(g,plan)
        elif g["type"] in (205,206):
            result=bound_brep_generator(g,generators)
        else:
            kind,record=brep_carrier(g)
            choices=[c for c in candidates if c[1]==kind and
                     (kind!=17 or dot(c[3],v(record["direction"]))>0)]
            if kind==19:
                # Opposite head ribbons can have the same infinite torus.
                # Their positive-transverse finite charts occupy opposite
                # sides, which the native face enclosure disambiguates.
                center = tuple((a+b)/2 for a,b in zip(actual[:3],actual[3:]))
                choices = [c for c in choices if not c[0].startswith("head.sector.") or
                           dot(center,(c[3][2],0,-c[3][0]))>0]
            distance,angle,name=min(((*bound(record,c,box),c[0]) for c in choices),key=lambda entry:entry[0])
            result={"status":"carrier_bound" if distance<=Q("0.000141") and
                    (angle is None or angle<=Q("0.01")) else "no_matching_carrier",
                    "p3_support_id":name,"distance_upper_mm":upper_float(distance),
                    "axis_or_plane_angle_upper_deg":None if angle is None else upper_float(angle),
                    "bound_basis":"analytic BREP carrier and exact rational perturbation bound"}
        results.append({"face_tag_session_only":d["face_tag"],"brep_type":g["type"],**result})
    accepted=[x for x in results if x["status"]=="carrier_bound"]
    return {"schema":"p4-complete-untrimmed-carrier-bounds/1","native_face_count":capture["face_count"],
            "face_count":len(results),"counts":dict(Counter(row["status"] for row in results)),
            "max_accepted_support_upper_mm":max((row["distance_upper_mm"] for row in accepted),default=None),
            "scope":"Continuous untrimmed carrier correspondences against the P3 binary64 preview. Plane, cylinder and cone bounds cover the common containing box.",
            "remaining":"Finite native trim correspondence and whole-body occupancy, including reverse coverage of all P3 exposed regions.",
            "faces":results,"execution_approved":False}
