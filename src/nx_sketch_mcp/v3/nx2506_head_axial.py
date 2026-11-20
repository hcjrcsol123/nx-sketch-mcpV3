"""Conditional finite bounds for the four lower axial head regions."""
from collections import defaultdict
from fractions import Fraction as Q

from .nx2506_carrier_bound import upper_float
from .nx2506_edit_domain import EDITED_DIRECTION_LIMIT_MM
from .nx2506_roll_s7_bound import face_edges,sqrt_bounds
from .nx2506_stock_bands import hoop


def assess_axial_head_bands(capture,supports,plan):
    faces={q["detail"]["face_tag"]:q["detail"]["topology"] for q in capture["results"]}
    boxes={q["inventory"]["tag_session_only"]:q["inventory"]["uf_face_data"]["bounding_box_mm"]
           for q in capture["selection"]}
    names={f["face_tag_session_only"]:f["p3_support_id"] for f in supports["faces"]}
    carrier={f["face_tag_session_only"]:Q(f["distance_upper_mm"]) for f in supports["faces"]}
    neighbors=defaultdict(set)
    for tag,t in faces.items():
        for e in face_edges(t):
            neighbors[e["tag"]].add(tag)
    p={q["id"]:Q(q["value"]) for q in plan["parameters"]["regional"]}
    a,b,c=(p["head."+n] for n in ("Y_lower_step","lower_sphere_contact_y","upper_sphere_contact_y"))
    radius31,radius40,y40=(p["head."+k] for k in ("R31","R40","Y40"))
    r_a=sqrt_bounds(radius31**2-a**2)
    r_l=p["head.lower_fillet_major"]
    r_b=sqrt_bounds(radius40**2-(b-y40)**2)
    r_c=sqrt_bounds(radius40**2-(c-y40)**2)
    expected={
      "head.R31": ({"head.Y_lower_step"},[(a,r_a)],203),
      "head.Y_lower_step": ({"head.R31","head.lower_fillet"},[(a,r_a),(a,(r_l,r_l))],209),
      "head.lower_fillet": ({"head.Y_lower_step","head.R40"},[(a,(r_l,r_l)),(b,r_b)],204),
      "head.R40": ({"head.lower_fillet","head.upper_fillet"},[(b,r_b),(c,r_c)],203),
    }
    result=[]
    for tag,name in names.items():
        if name not in expected:
            continue
        adjacent_ideal,ideal_rings,kind=expected[name]
        face=faces[tag]
        geometry=face["geometry"]
        adjacent=[names[next(iter(neighbors[e["tag"]]-{tag}))] for e in face_edges(face)]
        if set(adjacent)!=adjacent_ideal or len(adjacent)!=len(adjacent_ideal) or geometry["type"]!=kind:
            raise ValueError("axial head finite contact-ring graph changed")
        hoops=[hoop(loop,allow_rounded_center=True) for loop in face["children"]]
        if any(row is None for row in hoops) or len(hoops)!=len(ideal_rings):
            raise ValueError("an axial head loop is not an original full ring")
        if name=="head.R31":
            if Q(boxes[str(tag)][4]) >= Q(geometry["center"][1])+Q(geometry["radius"]):
                raise ValueError("lower cap not separated from the opposite pole")
        if name=="head.lower_fillet":
            if Q(boxes[str(tag)][4]) >= Q(geometry["center"][1])+Q(geometry["minor_radius"]):
                raise ValueError("opposite meridian torus arc remains possible")
        sort_key=(lambda row:row[1]) if kind==209 else (lambda row:row[0])
        hoops.sort(key=sort_key)
        ideal_rings.sort(key=sort_key)
        discrepancy=max(abs(a0-y)+max(abs(r-r0) for r0 in ri)+e
                        for (a0,r,e),(y,ri) in zip(hoops,ideal_rings))
        if discrepancy>Q("0.000001"):
            raise ValueError("axial head ring does not match ideal finite chart endpoints")
        # Interpolate radius on the step plane, or meridian angles on the
        # selected sphere/torus component. Chord to arc factor <=pi/2.
        # Another factor two covers radial spin in L1.
        bound=4*discrepancy+5*carrier[tag]
        result.append({"face_tag_session_only":tag,"p3_support_id":name,
                       "conditional_patch_upper_mm":upper_float(bound)})
    if len(result)!=4:
        raise ValueError("incomplete lower-axis phase coverage")
    return {"schema":"p4-head-axial-conditional-finite-patches/1","face_count":len(result),
            "maximum_conditional_patch_upper_mm":max(q["conditional_patch_upper_mm"] for q in result),
            "scope":"R31 cap, lower-step annulus, lower fillet band, R40 band under complete-original-ring and retained-material assumptions.",
            "execution_approved":False,"faces":result}


def verify_axial_head_bands(capture, supports, plan, native_anchors, h215):
    """Resolve the four bounded lower patches against the exact P3 meridians."""
    if (native_anchors.get('schema') != 'p4-native-lower-axial-anchors/1'
            or native_anchors.get('disk_copy_unchanged') is not True
            or not h215['status'].startswith('H215 accepted')):
        raise ValueError('original axial face anchors and accepted P3 head required')
    comparison = assess_axial_head_bands(capture, supports, plan)
    faces = {r['p3_support_id']: r for r in comparison['faces']}
    anchors = native_anchors['anchors']
    if set(faces) != set(anchors):
        raise ValueError('lower head anchor coverage differs from the four original face regions')
    p = {row['id']:Q(row['value']) for row in plan['parameters']['regional']}
    canonical = {'head.R31':31, 'head.R40':40, 'head.Y40':4, 'head.Y_lower_step':-26,
                 'head.r_lower_fillet':6, 'head.lower_fillet_y':-20,
                 'head.upper_sphere_contact_y':-20}
    if any(p[k] != val for k,val in canonical.items()):
        raise ValueError('lower axial head defaults differ from the P3 meridian certificate')
    contact = Q(4)+Q(40)*(-20-4)/(40-6)
    major_rings = sqrt_bounds(Q(34**2-24**2))
    major_error = max(abs(r-p['head.lower_fillet_major']) for r in major_rings)
    contact_y_error = abs(p['head.lower_sphere_contact_y']-contact)
    # Radius of the R40 sphere has |dr/dY|<2 around the lower contact.
    # Its axial plus radial displacement is bounded by 3 times the Y shift.
    if not all(abs(y-4)<30 and 40**2-(y-4)**2>15**2
               for y in (contact,p['head.lower_sphere_contact_y'])):
        raise ValueError('cannot bound the lower contact sphere slope')
    transfer = {'head.R31':Q(0), 'head.Y_lower_step':4*major_error,
                'head.lower_fillet':4*max(major_error,3*contact_y_error)+5*major_error,
                'head.R40':12*contact_y_error}
    # Midpoint/exterior witnesses distinguish the allowed meridian interval
    # from the opposite sphere/torus band or plane side.
    stations = {'head.R31':(-29,-24), 'head.Y_lower_step':(-26,-26),
                'head.lower_fillet':(-25,-14), 'head.R40':(-22,-19)}
    rows = []
    for role, row in faces.items():
        paired = anchors[role]
        if ([r['role'] for r in paired]!=['inside','outside']
                or [r['containment_status'] for r in paired]!=[1,2]
                or tuple(r['reference_mm'][1] for r in paired)!=stations[role]):
            raise ValueError('axial head native trim classification differs: '+role)
        for r in paired:
            if sum(abs(Q(x)-Q(y)) for x,y in zip(r['reference_mm'],r['carrier_point_mm']))>Q('0.00000001'):
                raise ValueError('head anchor missed the original carrier')
        if role=='head.Y_lower_step' and [r['reference_mm'][0] for r in paired]!=[20,15]:
            raise ValueError('lower step anchors do not identify the finite annulus')
        distance = Q(row['conditional_patch_upper_mm'])+transfer[role]
        rows.append({'p3_support_id':role,'preview_to_canonical_upper_mm':upper_float(transfer[role]),
                     'continuous_bidirectional_patch_upper_mm':upper_float(distance)})
    maximum = max(r['continuous_bidirectional_patch_upper_mm'] for r in rows)
    return {'schema':'p4-native-lower-axial-finite-patches/1',
            'status':'within_limit' if Q(maximum)<=Q('0.000141') else 'bound_exceeds_limit',
            'face_count':len(rows),'continuous_bidirectional_patch_upper_mm':maximum,
            'scope':('Four complete lower head patches given original NX full-circle trim loops '
                     'and an accepted canonical H215 head.'),
            'proof':('The incident full original class-10 rings exhaust the trims. Native UV '
                     'inside/outside anchors select the cap, annulus or the matching meridian band. '
                     'Interpolating the paired intervals at common azimuth covers both faces. '
                     'Rational enclosures for sqrt(580) and the R40 lower contact add the '
                     'remaining preview-to-canonical displacement.'),
            'execution_approved':False,'faces':rows}


def verify_edited_axial_head_bands(capture, supports, plan, native_anchors):
    """Verify the four complete lower axial faces of one edited assembly."""
    from .root_exit_certificate import I

    if (native_anchors.get('schema')!='p4-native-lower-axial-anchors/1'
            or not native_anchors.get('disk_copy_unchanged')):
        raise ValueError('original edited axial material witnesses required')
    comparison=assess_axial_head_bands(capture,supports,plan)
    values={r['id'].removeprefix('head.'):Q(r['value']) for r in plan['parameters']['regional']
            if r['id'].startswith('head.')}
    p={k:I.of(q) for k,q in values.items()}
    low=p['Y_lower_step']
    high=p['Y_head_step']
    center=p['Y40']
    rl,ru=p['r_lower_fillet'],p['r_upper_fillet']
    sphere=p['R40']
    cy_l,cy_u=low+rl,high-ru
    r_major=((sphere-rl).square()-(cy_l-center).square()).sqrt()
    low_contact=center+sphere*(cy_l-center)/(sphere-rl)
    up_contact=center+sphere*(cy_u-center)/(sphere-ru)
    expected={
        'lower_fillet_major':r_major,
        'lower_sphere_contact_y':low_contact,
        'upper_sphere_contact_y':up_contact,
    }
    preview_error=max(abs(values[k]-Q(a)) for k,number in expected.items() for a in (number.lo,number.hi))
    if preview_error>Q('0.00000001'):
        raise ValueError('edited P3 axial reference not bound to the exact meridian')
    # At both finite sphere contacts |dr/dY|<2. For the lower step
    # and the cap, the station and sphere inputs are already exact.
    if not all(abs((y-center).lo)<30 and abs((y-center).hi)<30 for y in (low_contact,up_contact)):
        raise ValueError('edited sphere contacts outside the reference slope range')
    radii=(p['R31'].square()-low.square()).sqrt()
    rows=[]
    for row in comparison['faces']:
        name=row['p3_support_id']
        inside,outside=native_anchors['anchors'][name]
        if [inside['containment_status'],outside['containment_status']]!=[1,2] or any(
                sum(abs(Q(a)-Q(b)) for a,b in zip(probe['reference_mm'],probe['carrier_point_mm']))>Q('0.00000001')
                for probe in (inside,outside)):
            raise ValueError('edited head axial witness does not select the intended native region')
        r,y,_=map(Q,inside['reference_mm'])
        _,yy,_=map(Q,outside['reference_mm'])
        if name=='head.R31':
            stable=-p['R31'].lo<y<low.lo and yy>low.hi
        elif name=='head.lower_fillet':
            stable=low.hi<y<low_contact.lo and yy>low_contact.hi
        elif name=='head.R40':
            stable=low_contact.hi<y<up_contact.lo and yy>up_contact.hi
        else:
            stable=radii.hi<r<r_major.lo and Q(outside['reference_mm'][0])<radii.lo
        if not stable:
            raise ValueError('native edited anchor does not match the exact bounded meridian region')
        # Apply the same finite angular endpoint transport as the original
        # analytic bands for the derived radius and station substitution.
        bound=Q(row['conditional_patch_upper_mm'])+20*preview_error
        rows.append({'p3_support_id':name,'continuous_bidirectional_patch_upper_mm':upper_float(bound),
                     'status':'within_limit' if bound<=EDITED_DIRECTION_LIMIT_MM else 'bound_exceeds_limit'})
    maximum=max(x['continuous_bidirectional_patch_upper_mm'] for x in rows)
    return {'schema':'p4-edited-native-axial-head-finite-patches/1',
            'status':'within_limit' if all(row['status']=='within_limit' for row in rows) else 'bound_exceeds_limit',
            'face_count':4,'faces':rows,'continuous_bidirectional_patch_upper_mm':maximum,
            'execution_approved':False}
