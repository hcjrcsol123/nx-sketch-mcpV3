"""Finite native C14 ribbon acceptance on the canonical H215 head charts."""
from decimal import Decimal
from fractions import Fraction as Q

from .nx2506_carrier_bound import dot, upper_float, v
from .nx2506_head_trim import _edges, _unit_interval
from .nx2506_root_patches import arc_endpoint
from .nx2506_tail_trim_bound import _sqrt
from .root_exit_certificate import I


def _interval(values):
    a,b=map(Q,values)
    return I(I.of(a).lo,I.of(b).hi)


def _middle(interval):
    return (Q(interval.lo)+Q(interval.hi))/2


def _geometry(sector, branch):
    R=I.of(sector['RA_initial_source_binary64'])
    q=I.of(sector['ra_initial_source_binary64'])
    if branch is None:
        return I.of(0),R,q
    side=sector['branches'][branch]
    third=_interval(side['d_initial_exact_enclosure'])
    r=I.of(side['rb_initial_source_binary64'])
    return third,R-((r-q).square()-third.square()).sqrt(),r


def _contact(sector, branch):
    side=sector['branches'][branch]
    d=_interval(side['d_initial_exact_enclosure'])
    a=I.of(sector['ra_initial_source_binary64'])
    b=I.of(side['rb_initial_source_binary64'])
    gap=b-a
    root=(gap.square()-d.square()).sqrt()
    return -(a*d)/gap,I.of(sector['RA_initial_source_binary64'])+a*root/gap


def _cone_height(d2):
    # d2=(Y+17.5)^2+(Y-4)^2. The positive branch derivative exceeds 74.
    return (-27+(I.of(729)-8*(I.of(Decimal("322.25"))-d2)).sqrt())/4


def _contact_arc(edge, sector, branch, frame):
    g=edge['geometry']
    if edge['geometry_class']!=10 or g['type']!='circular_evaluator' or g['is_periodic']:
        raise ValueError('expected original A/B tangent circle')
    lo,hi=map(Q,g['evaluator_limits'])
    if not 0<hi-lo<2:
        raise ValueError('A/B original tangent arc spans an unexpected branch')
    s,rho=_contact(sector,branch)
    x,_,z=frame
    frame_i=tuple(_interval(pair) for pair in frame)
    a,_,b=frame_i
    exact_center=(s*a,I.of(4),s*b)
    upper=_cone_height(s.square()+rho.square())
    target=[]
    for y in (I.of(-16),upper):
        t=(rho.square()-(y-4).square()).sqrt()
        target.append((a*s+b*t,y,b*s-a*t))
    ends=[arc_endpoint(g,t) for t in (lo,hi)]
    def gap(actual,ideal):
        return sum(max(abs(x-Q(p)) for x in e for p in (i.lo,i.hi)) for e,i in zip(actual,ideal))
    end_error=min(max(gap(x,y) for x,y in zip(ends,k)) for k in (target,target[::-1]))
    center_error=gap([(Q(x),Q(x)) for x in g['center']],exact_center)
    near_axis=tuple((a+b)/2 for a,b in (x,(Q(0),Q(0)),z))
    u,w=v(g['x_axis']),v(g['y_axis'])
    basis=(abs(dot(u,u)-1)+abs(dot(w,w)-1)+abs(dot(u,w))
           +abs(dot(u,near_axis))+abs(dot(w,near_axis)))
    radius=Q(g['radius'])
    carrier=center_error+2*max(abs(radius-Q(q)) for q in (rho.lo,rho.hi))+8*radius*basis
    if end_error>Q('0.000001') or carrier>Q('0.000001'):
        raise ValueError('original and selected canonical tangency arcs do not pair')
    return 5*carrier+4*end_error


def _linear_poly_arc(points, axis, through, approximate, center_y=Q(4)):
    """Bound the XZ change to the positive canonical torus chart at equal s,Y."""
    from .nx2506_trim_bound import _product

    d,M,q=approximate
    difference=Q(0)
    for a,b in zip(points,points[1:]):
        t=[dot(p,through) for p in (a,b)]
        s=[dot(p,axis)-d for p in (a,b)]
        y=[p[1]-center_y for p in (a,b)]
        if min(t)<=25 or max(abs(k) for k in s)>=q:
            raise ValueError('head facet leaves the positive-transverse outer torus chart')
        radial=[x+y for x,y in zip(_product(t,t),_product(y,y))]
        u=[r+s2+M*M-q*q for r,s2 in zip(radial,_product(s,s))]
        elevated=_product(radial,[Q(1)]*len(radial))
        residual=max(abs(a-4*M*M*b) for a,b in zip(_product(u,u),elevated))
        low,high=_sqrt(min(radial))[0],_sqrt(max(radial))[1]
        target_w=_sqrt(q*q-max(abs(k) for k in s)**2)[0]
        ideal_t=_sqrt((M+target_w)**2-max(abs(k) for k in y)**2)[0]
        if ideal_t<=25 or target_w<=2 or low-M<=0:
            raise ValueError('head facet does not select the positive chart branch')
        denom=(min(u)+2*M*low)*(low-M+target_w)
        if denom<=0:
            raise ValueError('head same-chart correction denominator not positive')
        difference=max(difference,residual*(high+M+q)/(denom*(min(t)+ideal_t)))
    return difference


def _mate_residual(points, phase, chart_error):
    max_error=Q(0)
    for a,b in zip(points,points[1:]):
        if phase in ('lower_y_minus16','upper_y17'):
            y=Q(-16) if phase=='lower_y_minus16' else Q(17)
            error=max(abs(a[1]-y),abs(b[1]-y))
        elif phase=='upper_cone':
            if min(a[1],b[1])<12:
                raise ValueError('upper cone outside positive exposed branch')
            rs=[x[0]*z[0]+x[2]*z[2] for x,z in ((a,a),(a,b),(b,b))]
            axial=[(x[1]+Q('17.5'))*(z[1]+Q('17.5')) for x,z in ((a,a),(a,b),(b,b))]
            # At fixed s, derivative of radius minus cone radius has
            # magnitude >1. The radius itself is 1-Lipschitz in XZ.
            error=max(abs(x-y) for x,y in zip(rs,axial))/(25+Q('29.5'))+chart_error
        else:
            raise ValueError('unsupported original head intersection phase')
        max_error=max(max_error,error)
    return max_error


def _sphere_height_residual(points, axis, approximate, center_y=Q(4), sphere_radius=Q(32)):
    """Compare the chord directly to the sphere/torus intersection height."""
    d,M,q=approximate
    maximum=Q(0)
    for a,b in zip(points,points[1:]):
        s1,s2=dot(a,axis),dot(b,axis)
        smallest=_sqrt(q*q-max(abs(s1-d),abs(s2-d))**2)[0]
        if smallest<=2:
            raise ValueError('sphere trim root not on the selected outer torus')
        errors=[]
        for p,s in ((a,s1),(b,s2)):
            lo,hi=_sqrt(q*q-(s-d)**2)
            heights=[(sphere_radius**2+center_y**2-s*s-(M+w)**2)/(2*center_y) for w in (lo,hi)]
            errors.append(max(abs(p[1]-y) for y in heights))
        # D²=s²+(M+sqrt(q²-(s-d)²))². Then Y=(1040-D²)/8.
        # Its |Y_ss| is M*q²/(4*w³). A linear chord's maximum
        # height interpolation error on this complete span is K*h²/8.
        curvature=M*q*q/(center_y*smallest**3)
        maximum=max(maximum,max(errors)+curvature*(s1-s2)**2/8)
    return maximum


def verify_head_ribbons(original,binding,drivers,h215,parameter_errors,facets,fillet):
    """Return an individual accepted bound for each proven original head ribbon."""
    if (facets.get('schema')!='p4-native-head-ribbon-facets/1' or facets.get('status')!='complete'
            or facets.get('disk_copy_unchanged') is not True or not h215['status'].startswith('H215 accepted')
            or fillet.get('status')!='within_limit'):
        raise ValueError('verified native ribbon capture, fillet and canonical head plan required')
    details={r['detail']['face_tag']:r['detail'] for r in original['results']}
    rows={r['p3_face']:r for r in binding['faces']}
    if len(rows)!=18 or set(rows)!=set(facets['faces']):
        raise ValueError('eighteen individual original ribbons required')
    transport=2000*Q(*parameter_errors['coefficient_error_upper_exact'])
    endpoint=Q(binding['max_all_event_coordinate_upper_mm'])+Q('0.00000002')
    result=[]
    for name,row in sorted(rows.items()):
        sector=drivers['sectors'][row['sector']]
        branch=row['branch'] if row['role']=='B' else None
        coefficients=_geometry(sector,branch)
        approximate=tuple(map(_middle,coefficients))
        # The exact canonical B parameters/frame and these rational centers
        # differ by far below a nanometre; retain their explicit envelopes.
        rounding=10*sum(Q(v.hi)-Q(v.lo) for v in coefficients)
        unit=_unit_interval(sector['axis_source'])
        axis=tuple((a+b)/2 for a,b in unit)
        through=(axis[2],Q(0),-axis[0])
        old_edges=_edges(details[row['native_face']])
        data=facets['faces'][name]
        phases=[]
        for edge in data['edges']:
            tag=edge['edge_index']
            role=edge['phase']
            if row['native_edge_phases'][str(tag)]!=role:
                raise ValueError('head facet phase changed')
            pts=[v(p) for p in edge['points_mm']]
            if role=='AB_contact':
                j=branch if branch is not None else (0 if dot(pts[0],axis)>0 else 1)
                error=_contact_arc(old_edges[tag],sector,j,unit)
                basis='original class-10 tangent arc evaluator'
            elif role=='lower_L_round':
                error=Q(fillet['six_A_trim_pointwise_pairing_upper_mm'])+transport
                basis='shared proven finite upper fillet edge'
            else:
                tolerance=Q(edge['chord_tolerance_mm'])
                vertex=Q(edge['max_vertex_deviation_mm'])
                if (Q(edge['max_midpoint_deviation_mm'])>tolerance or any(
                        sum((x-y)**2 for x,y in zip(a,b))<=(2*vertex)**2 for a,b in zip(pts,pts[1:]))):
                    raise ValueError('original head intersection chord contract failed')
                coordinates=[dot(p,axis) for p in pts]
                difference=[s-t for s,t in zip(coordinates,coordinates[1:])]
                if not (all(d>0 for d in difference) or all(d<0 for d in difference)):
                    raise ValueError(f'{name} {role} does not form a monotone original s chart')
                chart=_linear_poly_arc(pts,axis,through,approximate)+rounding
                phase_error=(_sphere_height_residual(pts,axis,approximate)+10*rounding
                             if role=='lower_sphere' else _mate_residual(pts,role,chart))
                # Through the accepted chart, axial slope <1.5 and total
                # graph speed <61 bound pointwise finite endpoint matching.
                error=tolerance+vertex+chart+Q('1.5')*phase_error+61*endpoint+transport
                basis='original class-11 facet chain, analytic chart and endpoint-matched continuation'
            phases.append({'edge_in_c14_brep_inventory':tag,'phase':role,'method':basis,
                           'continuous_pointwise_pairing_upper_mm':upper_float(error)})
        inside,outside=data['anchors']
        # The first witness lies near the center of the verified A chart
        # or just beyond a B seam, below cone and above sphere at Y=0.
        # For this torus the sphere residual at Y=0 is D²-1040.
        point=v(inside['carrier_point_mm'])
        s=I.of(dot(point,axis))
        d,M,q=coefficients
        D2=s.square()+(M+(q.square()-(s-d).square()).sqrt()).square()
        if (inside['containment_status']!=1 or outside['containment_status']!=2
                or abs(point[1])>Q('.00001') or outside['carrier_point_mm'][1]<19
                or D2.lo<=Decimal(1080)):
            raise ValueError('native head witness is not on the accepted middle material strip')
        if branch is None:
            if abs(dot(point,axis))>Q('.001'):
                raise ValueError('A chart witness is away from its central section')
        else:
            contact,_=_contact(sector,branch)
            offset=(s-contact) if branch==0 else (contact-s)
            if not Decimal('.3')<offset.lo<=offset.hi<Decimal('.5'):
                raise ValueError('B chart witness does not lie outside its exact contact plane')
        boundary=max(Q(e['continuous_pointwise_pairing_upper_mm']) for e in phases)+transport
        # On the same canonical torus, short endpoint-matched paths in the
        # two angular coordinates (with rho >25) increase length by less
        # than .01%. The original and target trim windings agree at the
        # common inside/exterior witnesses; the swept paths bound both fills.
        if boundary>=Q('.001'):
            raise ValueError('ribbon loop perturbation outside near-isometric chart')
        total=Q('1.0001')*boundary+transport
        result.append({'p3_support_id':row['native_support_id'],'p3_source_face':name,
                       'native_face_in_c14_brep_inventory':row['native_face'],
                       'continuous_bidirectional_patch_upper_mm':upper_float(total),
                       'status':'within_limit' if total<=Q('.000141') else 'bound_exceeds_limit',
                       'edge_proofs':phases})
    return {'schema':'p4-native-head-ribbon-finite-faces/1','faces':result,'face_count':len(result),
            'status':'within_limit' if all(r['status']=='within_limit' for r in result) else 'bound_exceeds_limit',
            'continuous_bidirectional_patch_upper_mm':max(r['continuous_bidirectional_patch_upper_mm'] for r in result),
            'scope':'Eighteen original A/B head strip faces, under the original NX facet and H215 phase contracts.',
            'execution_approved':False}
