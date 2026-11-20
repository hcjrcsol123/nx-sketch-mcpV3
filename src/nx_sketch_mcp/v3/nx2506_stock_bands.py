"""Finite bounds for stock patches identified by two complete transverse hoops."""
from fractions import Fraction as Q
import math

from .nx2506_carrier_bound import upper_float


def hoop(loop, allow_rounded_center=False):
    fins=loop["child"]["children"]
    if len(fins)!=1:
        return None
    edge,=[child["child"] for child in fins[0]["child"]["children"]]
    g=edge["geometry"]
    if (edge["geometry_class"]!=10 or g["type"]!="circular_evaluator"
            or not g["is_periodic"] or not g["arc_is_periodic"]):
        return None
    a,b=g["evaluator_limits"]
    if abs((b-a)-math.tau)>1e-12:
        return None
    x,y,z=map(Q,g["center"])
    ex,ey=tuple(map(Q,g["x_axis"])),tuple(map(Q,g["y_axis"]))
    center_offset=abs(x)+abs(z)
    plane_offset=abs(ex[1])+abs(ey[1])
    if center_offset+plane_offset> (Q("0.000000001") if allow_rounded_center else 0):
        return None
    # The recorded basis deviation contributes separately to the positional bound.
    magnitude_error=abs(sum(t*t for t in ex)-1)+abs(sum(t*t for t in ey)-1)
    orthogonality=abs(sum(a*b for a,b in zip(ex,ey)))
    if magnitude_error+orthogonality>Q("0.000000001"):
        return None
    radius=Q(g["radius"])
    return y,radius,center_offset+4*radius*(magnitude_error+orthogonality+plane_offset)


def assess_stock_bands(capture,supports,plan,limit=Q('0.000141')):
    names={row["face_tag_session_only"]:row["p3_support_id"] for row in supports["faces"]}
    profile=plan["construction"]["profiles"]["stock_profile"]
    vertices={row["id"]:row for row in profile["vertices"]}
    definitions={f"stock.{row['id']}":row for row in profile["curves"]}
    boxes={row["role"]:row["inventory"]["uf_face_data"]["bounding_box_mm"] for row in capture["selection"]}
    records=[]
    for row in capture["results"]:
        d=row["detail"]
        key=d["face_tag"]
        label=names[key]
        curve=definitions.get(label)
        if curve is None:
            continue
        face=d["topology"]
        if len(face["children"])!=2:
            continue
        g=face["geometry"]
        if g["type"] not in (201,202,204,209):
            continue
        axis=g["normal"] if g["type"]==209 else g["axis"]
        if axis not in ([0,1,0],[0,-1,0]):
            continue
        if g["type"]==201 and any(g["point_on_axis"][j]!=0 for j in (0,2)):
            continue
        if g["type"]==202 and any(g["point_at_apex"][j]!=0 for j in (0,2)):
            continue
        hoops=[hoop(loop) for loop in face["children"]]
        if any(x is None for x in hoops):
            continue
        ideal=[tuple(Q(vertices[curve[k]][n]) for n in ("y_mm","radius_mm")) for k in ("start","end")]
        sort_by=1 if g["type"]==209 else 0
        ideal.sort(key=lambda row:row[sort_by])
        hoops.sort(key=lambda row:row[sort_by])
        if ideal[0][sort_by]>=ideal[1][sort_by] or hoops[0][sort_by]>=hoops[1][sort_by]:
            continue
        if g["type"]==204:
            upper=torus_band_bound(g,curve,hoops,ideal,boxes[row["role"]])
            if upper is None:
                continue
        else:
            if curve["kind"]!="line":
                continue
            bounds=[abs(a[0]-b[0])+2*abs(a[1]-b[1])+a[2] for a,b in zip(hoops,ideal)]
            upper=max(bounds)
        if upper<=limit:
            records.append({"face_tag_session_only":key,"p3_support_id":label,
                            "conditional_finite_band_upper_mm":upper_float(upper),
                            "both_periodic_edges_verified":True})
    return {"schema":"p4-stock-conditional-finite-bands/1",
            "face_count":len(records),
            "maximum_conditional_band_upper_mm":max((x["conditional_finite_band_upper_mm"] for x in records),default=None),
            "scope":"Ordinary finite stock cylinder/cone/plane/torus bands with two periodic coaxial hoops, against P3 binary64 preview.",
            "assumptions":["The two reported original periodic class10 circle evaluators define both complete trim rings.",
                           "A regular consistently oriented BREP selects the bounded connected band between the rings.",
                           "The indicated P3 stock segments are exposed over their complete two-ring bands."],
            "method":"Affine axial/radial interpolation or paired meridian arcs at common azimuth; exact binary64 endpoint and frame perturbation bounds.",
            "execution_approved":False,"faces":records}


def torus_band_bound(g,curve,hoops,ideal,box):
    if curve["kind"]!="circular_arc" or g["center"][0]!=0 or g["center"][2]!=0:
        return None
    start,span=curve["start_rad"],curve["sweep_rad"]
    if not 0<abs(span)<math.pi:
        return None
    cy=Q(g["center"][1])
    minor=Q(g["minor_radius"])
    # A complement meridian arc contains an axial extremum not on the
    # nominated P3 arc. A containing box can exclude that other band.
    excluded=False
    for angle,station in ((0,cy+minor),(math.pi,cy-minor)):
        travelled=((angle-start)*math.copysign(1,span))%math.tau
        if abs(span)+0.001<travelled<math.tau-0.001 and (station<Q(box[1]) or station>Q(box[4])):
            excluded=True
    if not excluded:
        return None
    ry,radial=map(Q,curve["center_y_r_mm"])
    center_gap=abs(cy-ry)+abs(Q(g["major_radius"])-radial)
    circle_gap=center_gap+2*abs(minor-Q(curve["radius_mm"]))
    endpoint=max(abs(a[0]-b[0])+abs(a[1]-b[1])+a[2] for a,b in zip(hoops,ideal))
    # On the corresponding circle, arc-length discrepancy is at most
    # (pi/2) times endpoint chord length; use 2 as the outward factor.
    return 2*(circle_gap+2*(endpoint+circle_gap))


_ARC_INPUTS = {'s5': ('Y4','M5','tube_R5'), 's10': ('Y9','M10','tube_R10'),
               's19': ('Ycenter19','M19','tube_R19')}


def stock_band_anchor_specs(capture, supports, plan, limit=Q('0.000141')):
    """Locate the later NX probes by physical ring coordinates, without session tags."""
    bands = assess_stock_bands(capture,supports,plan,limit)['faces']
    faces = {r['detail']['face_tag']:r['detail']['topology'] for r in capture['results']}
    profile = plan['construction']['profiles']['stock_profile']
    points = {r['id']:r for r in profile['vertices']}
    curves = {'stock.'+r['id']:r for r in profile['curves']}
    result = {}
    for row in bands:
        label = row['p3_support_id']
        face = faces[row['face_tag_session_only']]
        rings = [hoop(loop) for loop in face['children']]
        curve = curves[label]
        a,b = (points[curve[k]] for k in ('start','end'))
        if curve['kind']=='circular_arc':
            cy,cr = curve['center_y_r_mm']
            radius = curve['radius_mm']
            angle = curve['start_rad']+curve['sweep_rad']/2
            inside = [cr+radius*math.sin(angle),cy+radius*math.cos(angle),0]
            outside = [cr-radius*math.sin(angle),cy-radius*math.cos(angle),0]
        else:
            ya,ra,yb,rb = a['y_mm'],a['radius_mm'],b['y_mm'],b['radius_mm']
            inside = [(ra+rb)/2,(ya+yb)/2,0]
            outside = [max(ra,rb)+1,ya,0] if ya==yb else [rb+(rb-ra)/10,yb+(yb-ya)/10,0]
        result[label] = {'rings_y_r_mm': sorted([float(y),float(r)] for y,r,_ in rings),
                         'inside':inside,'outside':outside}
    return result


def _exact_stock_parameters(plan, windows=None):
    from .regional_construction import _expression
    from .root_exit_certificate import I, _trig

    def tangent(x):
        sn,cs = _trig(I.of(x))
        return sn/cs

    def square(x, exponent):
        if exponent != 2:
            raise ValueError('non-square in stock meridian formula')
        return I.of(x).square()

    parameters = {}
    windows = windows or {}
    for row in plan['parameters']['canonical_definitions']['stock']['nodes']:
        name = row['id'].removeprefix('stock.')
        if row['class'] == 'derived':
            value = _expression(row['expression'], parameters,
                                sqrt=lambda x:I.of(x).sqrt(), tan=tangent, power=square)
            parameters[name] = I.of(value)
        elif row['id'] in windows:
            low,high = windows[row['id']]
            parameters[name] = I(I.of(low).lo,I.of(high).hi)
        else:
            value = Q(*row['value_exact']) if 'value_exact' in row else Q(row['default'])
            parameters[name] = I.of(value)
    return parameters


def verify_stock_bands(capture, supports, plan, anchor_capture, stf06, limit=Q('0.000141')):
    """Verify the twelve complete ordinary stock bands against canonical expressions."""
    accepted_source = (stf06.get('status') == 'STF06_conditional_accepted_P3_region_only'
                       or stf06.get('schema') == 'p4-joint-ideal-edit-window/1'
                       and stf06.get('status') == 'mathematical_window_proved')
    if (anchor_capture.get('schema') != 'p4-native-stock-band-anchors/1'
            or anchor_capture.get('disk_copy_unchanged') is not True
            or not accepted_source):
        raise ValueError('original C14 stock band anchors and accepted P3 source regions required')
    specs = stock_band_anchor_specs(capture,supports,plan,limit)
    bands = assess_stock_bands(capture,supports,plan,limit)['faces']
    anchors = anchor_capture['anchors']
    if len(specs)!=12 or set(specs)!=set(anchors):
        raise ValueError('all twelve complete stock bands must have native trim anchors')
    parameters = _exact_stock_parameters(plan)
    profile = plan['construction']['profiles']['stock_profile']
    points = {r['id']:r for r in profile['vertices']}
    curves = {'stock.'+r['id']:r for r in profile['curves']}

    def deviation(value, exact):
        value = Q(value)
        return max(abs(value-Q(exact.lo)),abs(value-Q(exact.hi)))

    result = []
    bounds = []
    for row in bands:
        label = row['p3_support_id']
        spec = specs[label]
        observed = anchors[label]
        if (observed['rings_y_r_mm'] != spec['rings_y_r_mm']
                or len(observed['points']) != 2):
            raise ValueError('native stock trim rings do not match comparison candidates')
        for point,role,status in zip(observed['points'],('inside','outside'),(1,2)):
            if (point['role']!=role or point['containment_status']!=status
                    or point['reference_mm']!=spec[role]
                    or sum(abs(Q(a)-Q(b)) for a,b in zip(point['reference_mm'],point['carrier_point_mm']))>Q('0.00000001')):
                raise ValueError('original stock material side differs: '+label)
        curve = curves[label]
        endpoints = [points[curve[k]] for k in ('start','end')]
        endpoint_error = max(
            deviation(x['y_mm'],parameters[x['y_parameter'].removeprefix('stock.')])
            + deviation(x['radius_mm'],parameters[x['radius_parameter'].removeprefix('stock.')])
            for x in endpoints)
        transfer = endpoint_error
        if curve['kind']=='circular_arc':
            exact_y,exact_r,exact_tube = (parameters[k] for k in _ARC_INPUTS[curve['id']])
            cy,cr = curve['center_y_r_mm']
            carrier_error = (deviation(cy,exact_y)+deviation(cr,exact_r)
                             +deviation(curve['radius_mm'],exact_tube))
            transfer = 4*endpoint_error+5*carrier_error
        bound = transfer+Q(row['conditional_finite_band_upper_mm'])
        bounds.append(bound)
        result.append({'p3_support_id':label,'canonical_preview_transfer_upper_mm':upper_float(transfer),
                       'continuous_bidirectional_patch_upper_mm':upper_float(bound)})
    maximum = max(r['continuous_bidirectional_patch_upper_mm'] for r in result)
    return {'schema':'p4-native-stock-finite-bands/1',
            'status':'within_limit' if (Q(maximum)<=limit if limit==Q('0.000141')
                                        else max(bounds)<=limit) else 'bound_exceeds_limit',
            'face_count':len(result),'continuous_bidirectional_patch_upper_mm':maximum,
            'scope':'Twelve original two-ring stock bands with NX-confirmed inside/outside anchors and canonical P3 stock arithmetic.',
            'proof':('The original full circles and native material anchors select each bounded band '
                     'or meridian branch. Affine interpolation of axial/radial endpoints or paired '
                     'meridian angles covers the finite native and target faces. Directed arithmetic '
                     'encloses exact default stock expression evaluation and its preview transfer.'),
            'execution_approved':False,'faces':result}

 
def assess_stock_tail_patches(capture,supports,plan,tail,bands):
    from collections import defaultdict
    from .nx2506_roll_s7_bound import face_edges,sqrt_bounds
    from .nx2506_stock_c5_patches import axial_circle_bound

    faces={q["detail"]["face_tag"]:q["detail"]["topology"] for q in capture["results"]}
    names={f["face_tag_session_only"]:f["p3_support_id"] for f in supports["faces"]}
    carriers={f["face_tag_session_only"]:Q(f["distance_upper_mm"]) for f in supports["faces"]}
    neighbors=defaultdict(set)
    for tag,t in faces.items():
        for edge in face_edges(t):
            neighbors[edge["tag"]].add(tag)
    data={q["id"]:Q(q["value"]) for q in plan["parameters"]["regional"]}
    expected={
        "stock.s1": {"stock.bottom_closure","stock.s2","tail.left_wall","tail.right_wall"},
        "stock.s2": {"stock.s1","stock.s3","tail.left_wall","tail.right_wall"},
        "stock.s3": {"stock.s2","stock.s4","tail.left_wall","tail.right_wall"},
        "stock.s4": {"stock.s3","stock.s5","tail.left_wall","tail.right_wall","tail.cylinder"},
    }
    rings={
        frozenset(("stock.s1","stock.s2")): ("stock.Y1","stock.R1"),
        frozenset(("stock.s2","stock.s3")): ("stock.Y2","stock.R1"),
        frozenset(("stock.s3","stock.s4")): ("stock.Y3","stock.R3"),
    }
    cut=Q(*tail["conditional_tail_face_upper_mm"]["exact"])
    reference_bands={q["p3_support_id"]:Q(q["conditional_finite_band_upper_mm"])
                     for q in bands["faces"]}
    out=[]
    for id,label in names.items():
        if label not in expected:
            continue
        edges=list(face_edges(faces[id]))
        adjacent=[names[next(iter(neighbors[e["tag"]]-{id}))] for e in edges]
        if set(adjacent)!=expected[label] or len(adjacent)!=len(expected[label]):
            raise ValueError("native tail stock patch loop does not match the ideal tail cut footprint")
        values=[]
        half=data["slot.width"]/2
        for e,nearest in zip(edges,adjacent):
            pair=frozenset((label,nearest))
            if pair in rings:
                yy,rr=(data[s] for s in rings[pair])
                z=sqrt_bounds(rr**2-half**2)
                ideals=[((sign*half,sign*half),(yy,yy),z) for sign in (-1,1)]
                values.append(axial_circle_bound(e,yy,rr,ideals,(Q(4),Q(7))))
            elif nearest=="stock.s5":
                values.append(reference_bands[nearest])
            else:
                values.append(cut)
        # The chart uses (12*azimuth,Y); radius >=6.9 gives a projection
        # Lipschitz constant below 3 for nearby paired points. Lift below
        # 4 and the boundary-layer/winding factor 2 give multiplier 24.
        upper=24*max(values)+carriers[id]
        out.append({"face_tag_session_only":id,"p3_support_id":label,
                    "conditional_patch_upper_mm":upper_float(upper)})
    return {"schema":"p4-tail-stock-conditional-finite-patches/1","face_count":len(out),
            "maximum_conditional_patch_upper_mm":max(row["conditional_patch_upper_mm"] for row in out),
            "scope":"Four outer stock patches adjacent to the finite tail cut, conditional on complete original loop and implicit-edge/material-side correspondence.",
            "execution_approved":False,"faces":out}


def verify_stock_tail_patches(capture,supports,plan,conditional_tail,verified_tail,verified_bands,anchor_capture):
    """Verify the four external stock faces bordering the original tail cut."""
    if (verified_tail.get('status')!='within_limit' or verified_bands.get('status')!='within_limit'
            or anchor_capture.get('schema')!='p4-native-tail-stock-anchors/1'
            or anchor_capture.get('disk_copy_unchanged') is not True):
        raise ValueError('verified tail edges, ordinary bands, and stock trim anchors required')
    bands = assess_stock_bands(capture,supports,plan)
    base = assess_stock_tail_patches(capture,supports,plan,conditional_tail,bands)
    labels = {r['p3_support_id'] for r in base['faces']}
    anchors = anchor_capture['anchors']
    if set(anchors)!=labels or len(labels)!=4:
        raise ValueError('tail stock anchor coverage differs')
    # Each patch is a subset of a complete coaxial cylinder/cone in a strip
    # with 6.8<r<9.1. An equal-Y carrier map costs at most three times the
    # maximum meridian endpoint perturbation (both slopes are <2).
    params = _exact_stock_parameters(plan)
    profile = plan['construction']['profiles']['stock_profile']
    points = {r['id']:r for r in profile['vertices']}
    curves = {'stock.'+r['id']:r for r in profile['curves']}
    carriers = {q['p3_support_id']:Q(q['distance_upper_mm']) for q in supports['faces']
                if q['p3_support_id'] in labels}
    cut = max(Q(q['continuous_pointwise_boundary_upper_mm']) for q in verified_tail['edge_bounds'])
    cut += Q(verified_tail['canonical_transfer_upper_mm'])
    result = []
    for old in base['faces']:
        label = old['p3_support_id']
        a,b = anchors[label]
        if (a['role']!='inside' or a['containment_status']!=1
                or b['role']!='outside' or b['containment_status']!=2
                or a['reference_mm'][1]!=b['reference_mm'][1]
                or a['reference_mm'][0]!=b['reference_mm'][2]
                or b['reference_mm'][0]!=0 or a['reference_mm'][2]!=0):
            raise ValueError('tail stock retained/cut material-side anchors disagree')
        for item in (a,b):
            if sum(abs(Q(x)-Q(y)) for x,y in zip(item['carrier_point_mm'],item['reference_mm']))>Q('0.00000001'):
                raise ValueError('tail stock native anchor missed the carrier')
        ends = [points[curves[label][k]] for k in ('start','end')]
        def discrepancy(v,field):
            expected = params[v[field+'_parameter'].removeprefix('stock.')]
            source = Q(v[(field if field=='radius' else 'y')+'_mm'])
            return max(abs(source-Q(expected.lo)),abs(source-Q(expected.hi)))
        transfer = max(discrepancy(v,'y')+discrepancy(v,'radius') for v in ends)
        if (any(not Q('6.8')<Q(v['radius_mm'])<Q('9.1') for v in ends)
                or not all(min(v['y_mm'] for v in ends)<r['reference_mm'][1]<max(v['y_mm'] for v in ends)
                           for r in (a,b))):
            raise ValueError('tail stock face or anchor outside its paired meridian band')
        carrier = carriers[label]+3*transfer
        # The preserved comparison is 24*max(boundary terms)+carrier.
        # Reuse its original arc/line bounds and replace the implicit edges
        # by the verified pointwise facet-chain comparison.
        previous_edge_max = Q(old['conditional_patch_upper_mm'])/24
        boundary = max(cut,previous_edge_max)+3*transfer+carrier
        if boundary>=Q('.001'):
            raise ValueError('tail stock boundary outside small-angle winding proof')
        # Chord distance on a common cylinder/cone decomposes into meridian
        # distance and 4*r1*r2*sin²(dtheta/2). The short continuous chart
        # path is at most (9.1/6.8)*1.000001 times that chord distance.
        filled = Q('9.1')/Q('6.8')*Q('1.000001')*boundary+carrier
        result.append({'p3_support_id':label,'canonical_preview_transfer_upper_mm':upper_float(transfer),
                       'continuous_bidirectional_patch_upper_mm':upper_float(filled)})
    maximum = max(r['continuous_bidirectional_patch_upper_mm'] for r in result)
    return {'schema':'p4-native-tail-adjacent-stock-finite-patches/1',
            'status':'within_limit' if Q(maximum)<=Q('0.000141') else 'bound_exceeds_limit',
            'face_count':4,'continuous_bidirectional_patch_upper_mm':maximum,
            'scope':'Four complete retained coaxial stock faces adjacent to the finite tail cut.',
            'proof':('Complete paired loops inherit original finite arcs and shared verified tail '
                     'edges. Equal-Y carrier transport and short angular/meridian paths move the '
                     'boundaries on a common cone or cylinder. At the NX-confirmed retained and '
                     'cut anchors, material side agrees with P3. Outside the swept boundary, '
                     'the original and canonical trim winding remains identical.'),
            'execution_approved':False,'faces':result}
