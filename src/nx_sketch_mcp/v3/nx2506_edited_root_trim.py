"""Original rational straight and rolled root trim verification at an edited NX point."""
from fractions import Fraction as Q

from .nx2506_c5_straight_trim import _original_strip_bound
from .nx2506_carrier_bound import dot, endpoints, rev_curve, tangent_range, upper_float, v, exact
from .nx2506_edit_domain import EDITED_DIRECTION_LIMIT_MM
from .nx2506_roll_s7_bound import face_edges, sqrt_bounds
from .nx2506_root_patches import arc_endpoint
from .nx2506_stock_bands import _exact_stock_parameters
from .nx2506_tail_trim_bound import _sincos
from .nx2506_trim_bound import bound_trim_pair
from .root_exit_certificate import I


def _rational_chart(record, tangent, radial, origin, mode):
    if not record.get('rational') or record.get('type')!=102:
        raise ValueError('expected an original rational root curve')
    values=record['weighted_poles_flat_xyzw']
    poles=[v(values[i:i+4]) for i in range(0,len(values),4)]
    if mode=='straight':
        meridian=[(dot(p[:3],tangent),dot(p[:3],radial),Q(0),p[3]) for p in poles]
    elif mode=='roll_front':
        meridian=[(dot(p[:3],tangent),origin*p[3]-dot(p[:3],radial),Q(0),p[3]) for p in poles]
    else:
        meridian=[(dot(p[:3],tangent),p[1]+71*p[3],Q(0),p[3]) for p in poles]
    if min(p[3] for p in meridian)<=0:
        raise ValueError('root rational weights are not positive')
    curve={'order':record['order'],'knots':record['knots'],
           'poles':[[exact(v_) for v_ in p] for p in meridian],'periodic':False,
           'interval':[record['start'],record['end']]}
    physical=[(p[0]/p[3],p[1]/p[3]) for p in meridian]
    spans=[b[0]-a[0] for a,b in zip(physical,physical[1:])]
    if not (all(x>0 for x in spans) or all(x<0 for x in spans)):
        raise ValueError('edited native root is not a single strict transverse graph')
    # For a rational Bézier with positive weights, the ratio of the two
    # derivatives is a weighted mean of ordered control-pair chord ratios.
    speed=max(1+abs(b[1]-a[1])/abs(b[0]-a[0]) for a,b in zip(physical,physical[1:]))
    return curve,speed


def _roll_field(t,height,pitch,radius,stock):
    arm=15-pitch+(I.of(radius*radius)-I.of(t).square()).sqrt()
    n=15-(arm.square()-I.of(height).square()).sqrt()
    c7=stock['Y7']+71
    rs=stock['M8']-(stock['tube_R8'].square()-(I.of(height)-c7).square()).sqrt()
    return (I.of(t).square()+n.square()).sqrt()-rs


def _roll_field_differential(t, height, pitch, radius, stock):
    w=(I.of(radius*radius)-t.square()).sqrt()
    arm=15-pitch+w
    cross=(arm.square()-height.square()).sqrt()
    n=15-cross
    rho=(t.square()+n.square()).sqrt()
    offset=height-(stock['Y7']+71)
    stock_slope=offset/(stock['tube_R8'].square()-offset.square()).sqrt()
    n_by_t=arm*t/(cross*w)
    n_by_height=height/cross
    return (t+n*n_by_t)/rho, n*n_by_height/rho-stock_slope


def _roll_exit_comparison(facet,tangent,t_source,t_expected,pitch,radius,stock):
    """Bound actual original exit positions directly in the edited ideal chart."""
    pts=[v(p) for p in facet['points_mm']]
    t0,t1=t_source
    l,h=t_expected
    scale=(h-l)/(t1-t0)
    if abs(scale-1)>Q('.001'):
        raise ValueError('edited root transverse finite interval shifted outside the checked chart')
    coords=[(l+(dot(p,tangent)-t0)*scale,p[1]+71) for p in pts]
    # Exact edited implicit field is monotone in |t| and v on this slice.
    # Bracket the selected s8 root over its whole transverse interval.
    span=max(abs(t) for t,_ in coords)
    if span>=Q('.52') or (not Q('.735')<radius<Q('.738')) or (
            _roll_field(span,Q('2.48'),pitch,radius,stock).hi>=0 or
            _roll_field(Q(0),Q('3.02'),pitch,radius,stock).lo<=0):
        raise ValueError('edited root s8 exit does not remain in the checked finite chart')
    # Bounds over |t|<=.52, 2.48<=v<=3.02. The arm is 3.66..3.9 mm,
    # sqrt(arm^2-v^2)>2, |arm_t|<1.01, |arm_tt|<4.3. This gives
    # |F_tt|<12, |F_tv|<2, |F_vv|<2.6 in the radial clearance field.
    vmin,vmax=Q('2.48'),Q('3.02')
    c7=stock['Y7']+71
    qt=Q(stock['tube_R8'].lo)
    arm_lo=15-pitch+sqrt_bounds(radius*radius-Q('.52')**2)[0]
    if (arm_lo<=Q('3.66') or 15-pitch+radius>=Q('3.9') or qt<=Q('4.99')
            or Q(c7.lo)<=Q('1.23') or any(not vmin<y<vmax for _,y in coords)):
        raise ValueError('edited roll exit violates the derivative chart assumptions')
    lower=[]
    for j in range(32):
        a=vmin+(vmax-vmin)*j/32
        b=vmin+(vmax-vmin)*(j+1)/32
        off=b-Q(c7.lo)
        near=sqrt_bounds(qt*qt-off*off)[0]
        lower.append(Q('.998')*a/sqrt_bounds(Q('3.9')**2-a*a)[1]-off/near)
    derivative=min(lower)
    if derivative<=Q('.49'):
        raise ValueError('edited roll root first-exit derivative is too small')
    endpoint_errors=[]
    for t,y in coords:
        estimate=_roll_field(t,y,pitch,radius,stock)
        endpoint_errors.append(max(abs(Q(estimate.lo)),abs(Q(estimate.hi))))
    tolerance=Q(facet['chord_tolerance_mm'])
    vertex=Q(facet['max_vertex_deviation_mm'])
    if Q(facet['max_midpoint_deviation_mm'])>tolerance or any(
            sum((a-b)**2 for a,b in zip(x,y))<=(2*vertex)**2 for x,y in zip(pts,pts[1:])):
        raise ValueError('edited original rolled exit chord tolerance was not confirmed')
    exit_difference=Q(0)
    def padded(a,b,width):
        lo,hi=sorted((a,b))
        return I(I.of(lo-width).lo,I.of(hi+width).hi)
    for a,b,x,y in zip(coords,coords[1:],endpoint_errors,endpoint_errors[1:]):
        dt,dv=abs(a[0]-b[0]),abs(a[1]-b[1])
        chord=max(x,y)+(12*dt*dt+4*dt*dv+Q('2.6')*dv*dv)/8
        t=padded(a[0],b[0],Q('.00002'))
        height=padded(a[1],b[1],Q('.001'))
        ft,fv=_roll_field_differential(t,height,pitch,radius,stock)
        if fv.lo<=Q('.4'):
            raise ValueError('local edited first-exit derivative loses its sign margin')
        ft_abs=max(map(abs,map(Q,(ft.lo,ft.hi))))*abs(scale)*Q('1.000001')
        fv_abs=max(map(abs,map(Q,(fv.lo,fv.hi))))
        lipschitz=sqrt_bounds(ft_abs*ft_abs+fv_abs*fv_abs)[1]
        local=(chord+lipschitz*(tolerance+vertex))/Q(fv.lo)
        if local>Q('.00098'):
            raise ValueError('edited first-exit root leaves its local continuation collar')
        exit_difference=max(exit_difference,local)
    return exit_difference


def _finite_rolled_side_arc(g,tangent,radial,t,pitch,radius,stock):
    """Compare the original class-10 side guide with its finite ideal arc."""
    a,b=Q('2.48'),Q('3.02')
    if _roll_field(t,a,pitch,radius,stock).hi>=0 or _roll_field(t,b,pitch,radius,stock).lo<=0:
        raise ValueError('edited ideal side guide lacks a first-exit bracket')
    for _ in range(38):
        m=(a+b)/2
        f=_roll_field(t,m,pitch,radius,stock)
        if f.lo>0:
            b=m
        elif f.hi<0:
            a=m
        else:
            break
    arm_min,arm_max=(15-pitch+r for r in sqrt_bounds(radius*radius-t*t))
    arm=I(I.of(arm_min).lo,I.of(arm_max).hi)
    canonical=[]
    for h in (I.of(0),I(I.of(a).lo,I.of(b).hi)):
        n=15-(arm.square()-h.square()).sqrt()
        canonical.append([t*tangent[0]+n*radial[0],h-71,t*tangent[2]+n*radial[2]])
    observed=[arc_endpoint(g,Q(angle)) for angle in g['evaluator_limits']]
    def gap(incoming,reference):
        return sum(max(abs(o-Q(p)) for o in span for p in (I.of(w).lo,I.of(w).hi))
                   for span,w in zip(incoming,reference))
    end=min(max(gap(p,q) for p,q in zip(observed,order)) for order in (canonical,canonical[::-1]))
    center=(15*radial[0]+t*tangent[0],Q(-71),15*radial[2]+t*tangent[2])
    arc_r=Q(g['radius'])
    x,y=v(g['x_axis']),v(g['y_axis'])
    frame=(abs(dot(x,x)-1)+abs(dot(y,y)-1)+abs(dot(x,y))+abs(dot(x,tangent))+abs(dot(y,tangent)))
    support=sum(abs(Q(a)-b) for a,b in zip(g['center'],center))+2*max(
        abs(arc_r-arm_min),abs(arc_r-arm_max))+8*arc_r*frame
    if support+end>=Q('.001'):
        raise ValueError('edited side arc correspondence outside the short-angle bound')
    # Once centers, radii and planes are aligned, endpoints of two short
    # arcs differ by at most support+end. Converting this chord to angle
    # at radius above 3.6, including the tiny radius ratio, costs <1.001.
    return support+Q('1.001')*(support+end)


def verify_edited_root_faces(capture, carriers, plan, driver_values, facets):
    """Bind all original 44 edited root faces and both of their finite directions."""
    if facets.get('status')!='complete' or not facets.get('disk_copy_unchanged'):
        raise ValueError('complete original root tessellation required')
    selected={r['p3_support_id']:r for r in carriers['faces']
              if r['p3_support_id'].endswith(('.straight_root','.roll_root'))}
    if len(selected)!=44 or set(selected)!=set(facets['faces']):
        raise ValueError('edited root face identity is incomplete')
    faces={r['detail']['face_tag']:r['detail']['topology'] for r in capture['results']}
    cone=next(faces[r['face_tag_session_only']]['geometry'] for r in carriers['faces'] if r['p3_support_id']=='stock.s6')
    apex=Q(cone['point_at_apex'][1])
    slopes=tangent_range(Q(cone['half_apex_angle']))
    stock_ids={r['id'] for r in plan['parameters']['canonical_definitions']['stock']['nodes']}
    stock=_exact_stock_parameters(plan,{k:(val,val) for k,val in driver_values.items() if k in stock_ids})
    s6slope=(stock['R6']-stock['R5'])/(stock['Y6']-stock['Y5'])
    s6apex=stock['Y5']-stock['R5']/s6slope
    inv=I.of(1)/s6slope
    cone_motion=max(abs(apex-Q(p)) for p in (s6apex.lo,s6apex.hi))+20*max(
        abs(1/v_-Q(z)) for v_ in slopes for z in (inv.lo,inv.hi))
    pitch=Q(driver_values['pitch_radius_mm'])
    radius=Q(driver_values['root_radius_mm'])
    design=sorted(Q(data['endpoints']['root']['t_mm']['value']) for data in
                  plan['construction']['profiles']['section6']['templates'].values())
    frames={p['id']:p['frame'] for p in plan['construction']['nodes'] if p['id'].endswith('_straight_tool')}
    records=[]
    for name,row in sorted(selected.items()):
        face=faces[row['face_tag_session_only']]
        rolled=name.endswith('.roll_root')
        frame=frames[name.split('.')[0]+'_straight_tool']
        tangent,radial=v(frame['e_t']),v(frame['e_r'])
        generator=face['geometry']['generator']
        origin=dot(v(face['geometry']['point_on_axis']),radial) if rolled else Q(0)
        ref_chart,speed=_rational_chart(generator,tangent,radial,origin,'roll' if rolled else 'straight')
        edges=list(face_edges(face))
        front,=[r for r in edges if r['geometry_class']==10 and all(
            abs(Q(c['child']['geometry']['point'][1])+71)<Q('0.00000001') for c in r['children'])]
        original,_=_rational_chart(front['geometry'],tangent,radial,origin,'roll_front' if rolled else 'straight')
        front_error=min(Q(*bound_trim_pair(ref_chart,rev_curve(original,reverse))['hausdorff_l1_upper_mm_exact'])
                        for reverse in (False,True))
        weights=front['geometry']['weighted_poles_flat_xyzw'][3::4]
        heights=front['geometry']['weighted_poles_flat_xyzw'][1::4]
        front_error=max(front_error,max(abs(71+Q(y)/Q(w)) for y,w in zip(heights,weights,strict=True)))
        tlo,thi=sorted(p[0] for p in endpoints(ref_chart))
        facet=facets['faces'][name]
        saved=sorted(v(r['child']['geometry']['point']) for r in front['children'])
        readback=sorted(map(v,facet['upper_endpoints_mm']))
        if any(sum(abs(a-b) for a,b in zip(x,y))>Q('0.00000001') for x,y in zip(saved,readback,strict=True)):
            raise ValueError('edited root facet capture does not share the original front trim')
        side=Q(0)
        side_arc=Q(0)
        sides=[r for r in edges if r['geometry_class']==10 and r['tag']!=front['tag']]
        if len(sides)!=2:
            raise ValueError('edited original root does not use two finite side guides')
        for e in sides:
            g=e['geometry']
            ideal=[tlo,thi]
            if rolled:
                if g['type']!='circular_evaluator' or Q(g['evaluator_limits'][1])-Q(g['evaluator_limits'][0])>=Q('1.57'):
                    raise ValueError('edited rolled side is not its intended short circular arc')
                derivatives=[]
                for angle in g['evaluator_limits']:
                    sn,cs=_sincos(Q(angle))
                    rates=[-Q(g['x_axis'][1])*s+Q(g['y_axis'][1])*c for s in sn for c in cs]
                    derivatives.append((min(rates),max(rates)))
                if not (all(q[0]>0 for q in derivatives) or all(q[1]<0 for q in derivatives)):
                    raise ValueError('edited root side arc is not monotone in Y')
                center=dot(v(g['center']),tangent)
                width=Q(g['radius'])*(abs(dot(v(g['x_axis']),tangent))+abs(dot(v(g['y_axis']),tangent)))
                side=max(side,min(abs(center-q) for q in ideal)+width)
                target=min(design,key=lambda q:abs(center-q))
                side_arc=max(side_arc,_finite_rolled_side_arc(g,tangent,radial,target,pitch,radius,stock))
            else:
                if g['type']!=101:
                    raise ValueError('edited straight root side must be an original line')
                a,b=sorted((v(g['start']),v(g['end'])),key=lambda p:p[1])
                xlo,xhi=sqrt_bounds(a[0]*a[0]+a[2]*a[2])
                h=max(abs(a[1]-apex-x/s) for x in (xlo,xhi) for s in slopes)
                td=min(abs(dot(b,tangent)-q) for q in ideal)
                side=max(side,h+td+abs(a[0]-b[0])+abs(a[2]-b[2])+abs(b[1]+71))
        tiny=max(front_error,side,Q('0.00000001'))
        carrier=Q(row['distance_upper_mm'])
        if rolled:
            v_shift=_roll_exit_comparison(facet,tangent,(tlo,thi),design,pitch,radius,stock)
            inside,outside=facet['material_anchors']
            q=v(inside['carrier_point_mm'])
            if (inside['containment_status']!=1 or outside['containment_status']!=2
                    or not tlo+tiny<dot(q,tangent)<thi-tiny or not -70.1<q[1]<-69.9
                    or outside['carrier_point_mm'][1]>=-71):
                raise ValueError('edited rolled root does not retain the intended material side')
            # The exact affine t pairing is already used in the exit
            # comparison. At fixed Y the carrier radial transfer is at
            # most twice the circular-generator transfer.
            bound_=Q('1.8')*v_shift+2*carrier+20*tiny
            trim_upper=Q('1.8')*v_shift+20*tiny
        else:
            trim_upper=_original_strip_bound(facet,lambda p:dot(v(p),tangent),tlo,thi,2*speed,Q(18),
                                               apex,slopes,tiny)
            bound_=trim_upper+carrier*(1+Q(inv.hi))+cone_motion
        records.append({'p3_support_id':name,'native_finite_trim_upper_mm':upper_float(trim_upper),
                        **({'rolled_side_arc_upper_mm':upper_float(side_arc)} if rolled else {}),
                        'continuous_bidirectional_patch_upper_mm':upper_float(bound_),
                        'status':'within_limit' if bound_<=EDITED_DIRECTION_LIMIT_MM else 'bound_exceeds_limit'})
    return {'schema':'p4-edited-root-finite-patches/1','face_count':len(records),
            'status':'within_limit' if all(r['status']=='within_limit' for r in records) else 'bound_exceeds_limit',
            'maximum_patch_upper_mm':max(r['continuous_bidirectional_patch_upper_mm'] for r in records),
            'faces':records,'scope':'44 original edited C5 root finite faces at one native edit vector.',
            'execution_approved':False}
