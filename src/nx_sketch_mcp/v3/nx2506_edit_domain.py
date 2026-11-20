"""P4 edit-candidate checks; no execution or full-domain approval.

P3 defines a coupled domain. The sufficient local intervals use fixed stock
and head charts, with the stated tail and flank parameters allowed to vary.
"""
import math
import json
from collections.abc import Mapping
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from .flank_construction import C5, build_default_flank_candidate
from .nx2506_slot_interval import assess_tail_parameter_box, assess_tail_width_interval
from .root_exit_certificate import I

EDITED_DIRECTION_LIMIT_MM = Fraction('0.0004')

_P2_LOW = 1.2857096483109538
_P2_HIGH = 1.2859096483109538
_ANGLE_DRIVERS = frozenset(f'{side}.alpha_{role}_rad'
                           for side in ('F0002', 'F0024') for role in ('root', 'outer'))
_POLE_DRIVERS = frozenset(f'{side}.P{i}.{axis}_mm' for side in ('F0002', 'F0024')
                          for i in (2, 3, 4) for axis in ('t', 'r'))
_SHARED_FLANK_DRIVERS = {'pitch_radius_mm','root_radius_mm','phase_rad'}
_FLANK_DRIVERS = _ANGLE_DRIVERS | _POLE_DRIVERS | _SHARED_FLANK_DRIVERS
_TAIL_DRIVERS = frozenset(f'slot.{name}' for name in ('width', 'radius', 'axis_y', 'axis_z'))


def assess_stock_meridian_window(plan, windows):
    """Prove orientation and branch validity on a joint box of every stock driver."""
    from .nx2506_stock_bands import _exact_stock_parameters
    from .root_exit_certificate import _trig

    definitions = plan['parameters']['canonical_definitions']['stock']['nodes']
    drivers = {r['id'] for r in definitions if r['class'] in ('independent_local','external_independent_reference')}
    if set(windows)!=drivers or any(not lo<hi for lo,hi in windows.values()):
        raise ValueError('every independent stock driver needs one nonempty interval')
    p = _exact_stock_parameters(plan,windows)
    last = p['Y_mouth']
    stations = [p['Y'+str(i)] for i in (0,1,2,3,4,5,6,7,8,9,10,12,13,15,16,17,18)] + [last]
    station_margin = min((b-a).lo for a,b in zip(stations,stations[1:]))
    radius_margin = min(p['R'+str(i)].lo for i in range(20))
    arc8_gap = p['M8']-p['R9']
    arc19_gap = p['R17']-p['M19']
    angles = [p[r['id'].removeprefix('stock.')] for r in definitions if r['id'] in drivers and r['unit']=='rad']
    slopes = [sin/cos for angle in angles for sin,cos in [_trig(angle)]]
    checks = {
        'strict_axial_order_except_documented_radial_steps':station_margin>0,
        'positive_radii_and_length_inputs':radius_margin>0 and all(
            p[r['id'].removeprefix('stock.')].lo>0 for r in definitions if r['id'] in drivers),
        'step_radii_ordered':(p['R11']-p['M10']).lo>0 and (p['R14']-p['R13']).lo>0,
        'cone_positive_tangents_on_selected_branches':all(slope.lo>0 for slope in slopes),
        'quarter_arcs_s5_s10_keep_positive_radius':min(p['tube_R5'].lo,p['tube_R10'].lo)>0,
        's8_lower_radial_branch':arc8_gap.lo>0 and (p['tube_R8']-arc8_gap).lo>0,
        's19_outer_radial_branch':arc19_gap.lo>0 and (p['tube_R19']-arc19_gap).lo>0 and
            (p['Ycenter19']-p['Y18']).lo>0 and (last-p['Ycenter19']).lo>0 and
            (p['Ycenter19']+p['tube_R19']-last).lo>0,
        'fixed_roll_start_y_within_shaft':p['Y6'].hi<-71<p['Y7'].lo,
    }
    return {'schema':'p4-complete-stock-meridian-window/1',
            'status':'ideal_stock_meridian_proved' if all(checks.values()) else 'outside_proven_window',
            'driver_count':len(drivers),'driver_windows':windows,'checks':checks,
            'minimum_distinct_station_gap_mm':str(station_margin),
            'minimum_stock_radius_mm':str(radius_margin),
            'scope':('All independent stock inputs may vary simultaneously in these intervals for '
                     'the ideal closed coaxial meridian and its stated arc branches.'),
            'remaining':['Native regeneration over the entire box','Finite interactions of the edited '
                         'stock with tail, C5 and head tool trims and retained material'],
            'execution_approved':False}


def assess_head_carrier_window(plan, windows, mouth_window):
    """Check all independent head carrier/tangency inputs over a joint interval box."""
    from .flank_parameters import _pi

    head=plan['parameters']['canonical_definitions']['head']
    standard={'head.'+key for key in head['global_independent']}
    sectors=[]
    expected=set(standard)
    for i,sector in enumerate(head['sectors']):
        prefix=f'head.sector.{i}.'
        members=['theta','RA','ra']+[f'branch.{j}.{name}' for j,_ in enumerate(sector['branches'])
                                      for name in ('d','rb')]
        expected.update(prefix+key for key in members)
        sectors.append((prefix,members))
    if set(windows)!=expected or any(not low<high for low,high in windows.values()):
        raise ValueError('all independent head drivers need one nonempty interval')

    def enclosure(pair):
        a,b=pair
        return I(I.of(a).lo,I.of(b).hi)

    raw={key:enclosure(value) for key,value in windows.items()}
    h={key.removeprefix('head.'):raw[key] for key in standard}
    mouth=enclosure(mouth_window)
    y=h['Y40']
    sphere=h['R40']
    lower_center=h['Y_lower_step']+h['r_lower_fillet']
    upper_center=h['Y_head_step']-h['r_upper_fillet']
    contacts=[]
    axial_checks=[]
    for label,center in (('lower',lower_center),('upper',upper_center)):
        tube=h['r_'+label+'_fillet']
        difference=sphere-tube
        radial=difference.square()-(center-y).square()
        axial_checks.append(tube.lo>0 and difference.lo>0 and radial.lo>tube.square().hi)
        contacts.append(y+sphere*(center-y)/difference)
    stations=[-h['R31'],h['Y_lower_step'],*contacts,h['Y_head_step'],mouth,h['R32']]
    axial_clearance=min((b-a).lo for a,b in zip(stations,stations[1:]))
    angle=h['cone_half_angle_initial_exact']
    checks={
        'ordered_meridian_stations_and_shared_mouth':axial_clearance>0,
        'positive_sphere_radii_and_valid_internal_fillets':min(h[k].lo for k in ('R31','R32','R40'))>0 and all(axial_checks),
        'positive_cone_branch_and_half_angle':(h['Y_head_step']-h['cone_apex_Y']).lo>0 and angle.lo>0 and angle.hi<(_pi()/2).lo,
    }
    directional=[]
    for i,(prefix,members) in enumerate(sectors):
        p={key:raw[prefix+key] for key in members}
        directional.append(p['theta'])
        slides=[]
        for j in (0,1):
            d,b=p[f'branch.{j}.d'],p[f'branch.{j}.rb']
            gap=b-p['ra']
            radicand=gap.square()-d.square()
            if gap.lo>0 and radicand.lo>0:
                b_major=p['RA']-radicand.sqrt()
                slide=-(p['ra']*d)/gap
                selected = (b_major-b).lo>0 and (
                    (p['ra']-slide).lo>0 if j==0 else (p['ra']+slide).lo>0)
                slides.append(slide)
            else:
                selected=False
            checks[f'sector_{i}_branch_{j}_tangent_root_and_torus']=selected
        checks[f'sector_{i}_ordered_contact_planes']=(p['RA']-p['ra']).lo>0 and len(slides)==2 and slides[1].hi<0<slides[0].lo
    directional.sort(key=lambda x:x.lo)
    directional.append(directional[0]+2*_pi())
    gap=min((b-a).lo for a,b in zip(directional,directional[1:]))
    checks['six_distinct_angular_axes_preserve_order']=gap>Decimal('1.04')
    return {'schema':'p4-complete-head-carrier-window/1',
            'status':'ideal_head_carriers_proved' if all(checks.values()) else 'outside_proven_window',
            'driver_count':len(windows),'driver_windows':windows,'shared_mouth_window_mm':mouth_window,
            'minimum_axial_clearance_mm':str(axial_clearance),'minimum_axis_gap_rad':str(gap),'checks':checks,
            'scope':'Full simultaneous head carrier and tangent-branch intervals, with a bounded shared mouth.',
            'remaining':['Edited finite trim/material exposure and inter-region intersection charts',
                         'Continuous native regeneration and saved editing acceptance'],
            'execution_approved':False}


def assess_cross_region_clearances(plan, stock_windows, tail_windows, head_windows):
    """Verify cross-region constraints on the simultaneous stock, tail and head ranges."""
    from .nx2506_stock_bands import _exact_stock_parameters
    from .root_exit_certificate import _trig

    def box(value):
        lo,hi=(I.of(v) for v in value)
        return I(lo.lo,hi.hi)

    s=_exact_stock_parameters(plan,stock_windows)
    slots={k.removeprefix('slot.'):box(v) for k,v in tail_windows.items()}
    head={k.removeprefix('head.'):box(v) for k,v in head_windows.items()}
    radius,ay,az=(slots[k] for k in ('radius','axis_y','axis_z'))
    half=slots['width']/2
    def cutter_height(y):
        return az-(radius.square()-(I.of(y)-ay).square()).sqrt()
    def stock_side(r):
        return (r.square()-half.square()).sqrt()
    def axial_exit(z):
        return ay+(radius.square()-(az-z).square()).sqrt()

    side_exit=axial_exit(stock_side(s['R3']))
    center_exit=axial_exit(s['R3'])
    cone_slopes=[]
    for ident in ('alpha1','alpha3'):
        sn,cs=_trig(s[ident])
        cone_slopes.append(sn/cs)
    dy=s['Y3']-ay
    cutter_slope=dy/(radius.square()-dy.square()).sqrt()
    f0=cutter_height(s['Y0'])
    end_guard=(s['Y0']-ay).lo>0 and f0.lo>0 and (stock_side(s['R0'])-f0).lo>0
    r7_guard=(s['R1'].square()-half.square()-cutter_height(s['Y2']).square()).lo>0
    checks={
        'tail_lower_branch_and_end_notch':end_guard,
        'tail_side_still_active_along_the_first_cylinder':r7_guard,
        'tail_cutter_rises_slower_than_both_stock_cones':min(x.lo for x in cone_slopes)>cutter_slope.hi,
        'tail_side_and_center_exit_in_s4_in_order':(side_exit-s['Y3']).lo>0
            and (center_exit-side_exit).lo>0 and center_exit.hi<-144,
        'tail_cutter_cannot_reenter_after_center_exit':(cutter_height(-144)-s['R3']).lo>0
            and (cutter_height(-126)-s['M5']).lo>0 and s['Y4'].lo>-126
            and (s['Y5']-(ay+radius)).lo>0,
        'tail_core_clears_lower_cutter_branch':(az-radius).lo>4,
        'axially_separate_tail_c5_roll_and_head':s['Y4'].lo>-126 and center_exit.hi<-144
            and -67<head['R31'].hi.copy_negate() and head['Y_lower_step'].lo>-67,
    }
    mouth=s['Y_mouth']
    tube_y=mouth-head['Y40']
    half_cone=head['cone_half_angle_initial_exact']
    sn,cs=_trig(half_cone)
    cone_at_mouth=(sn/cs)*(mouth-head['cone_apex_Y'])
    limits=[cone_at_mouth.hi,head['R32'].hi]
    for i in range(6):
        prefix=f'sector.{i}.'
        major,a=head[prefix+'RA'],head[prefix+'ra']
        # For any torus point at the mouth, t² <= (M+q)²-(Y-Y40)²
        # and s² <= (|d|+q)². Bound the untrimmed tool conservatively.
        limits.append(((major+a).square()+a.square()-tube_y.square()).sqrt().hi)
        for side in (0,1):
            pre=prefix+f'branch.{side}.'
            d,b=head[pre+'d'],head[pre+'rb']
            M=major-((b-a).square()-d.square()).sqrt()
            span=max(abs(d.lo),abs(d.hi))
            limits.append(((M+b).square()+(I.of(span)+b).square()-tube_y.square()).sqrt().hi)
    mouth_clearance=(s['R19']-I.of(max(limits))).lo
    checks['head_tools_clear_the_shared_stock_mouth']=mouth_clearance>1
    checks['shared_stock_c5_shaft_keeps_positive_cap_clearance']=(
        s['Rshaft'].lo>12 and s['Rshaft'].hi<Decimal('13.1') and s['Y6'].hi<-71<s['Y7'].lo)
    return {'schema':'p4-cross-region-clearance-window/1',
            'status':'ideal_cross_region_clearances_proved' if all(checks.values()) else 'outside_proven_window',
            'checks':checks,'minimum_stock_mouth_clearance_mm':str(mouth_clearance),
            'tail_side_exit_mm':[str(side_exit.lo),str(side_exit.hi)],
            'tail_center_exit_mm':[str(center_exit.lo),str(center_exit.hi)],
            'scope':'Whole-window rear slot/stock exit and connection, separated cut stations, shared stock '
                    'shaft station/radius, and head removal tool clearance inside the shared mouth.',
            'remaining':['Simultaneous C5 roll trim and head exposure over every native combination'],
            'execution_approved':False}


def assess_head_exposure_window(plan, windows, mouth_window):
    """Extend the H215 ideal radial exposure and hidden-cap proof to the edit window."""
    from .root_exit_certificate import _trig

    carrier=assess_head_carrier_window(plan,windows,mouth_window)
    h={key.removeprefix('head.'):I(I.of(lo).lo,I.of(hi).hi) for key,(lo,hi) in windows.items()}
    y=h['Y40']
    upper_q=h['r_upper_fillet']
    upper_c=h['Y_head_step']-upper_q
    sphere_gap=h['R40']-upper_q
    major=(sphere_gap.square()-(upper_c-y).square()).sqrt()
    contact=y+h['R40']*(upper_c-y)/sphere_gap
    lower_disk=I.of(major.lo)
    upper_disk=I.of('27.69')
    y_bound=max(abs(h['Y_head_step'].lo),Decimal(16))
    sn,cs=_trig(h['cone_half_angle_initial_exact'])
    checks={
        'positive_and_ordered_ideal_carriers':carrier['status']=='ideal_head_carriers_proved',
        'upper_exposed_regions_have_nonempty_base_disk':(
            (h['R32'].square()-I.of(y_bound).square()).lo>upper_disk.square().hi
            and ((sn/cs)*(16-h['cone_apex_Y'])).lo>upper_disk.hi),
    }
    for i in range(6):
        k=f'sector.{i}.'
        a,RA=h[k+'ra'],h[k+'RA']
        spans=[]
        for branch in (0,1):
            p=k+f'branch.{branch}.'
            rb,d=h[p+'rb'],h[p+'d']
            gap=rb-a
            q=(gap.square()-d.square()).sqrt()
            RB=RA-q
            slide=-(a*d)/gap
            sabs=I.of(max(abs(slide.lo),abs(slide.hi)))
            spans.append(sabs.hi)
            rho=RA+a*q/gap
            step_radius2=sabs.square()+rho.square()-(h['Y_head_step']-y).square()
            # On the kept B side s and d have opposite signs, hence
            # |s| <= rb-|d| rather than rb+|d| on the exposed tube.
            dmin=min(abs(d.lo),abs(d.hi))
            sbound=rb-I.of(dmin)
            b_inner_guard=(upper_disk.square()-sbound.square()).lo>RB.square().hi
            checks[f'sector_{i}_branch_{branch}_inner_surface_hidden']=b_inner_guard and (RB-rb).lo>0
            checks[f'sector_{i}_branch_{branch}_step_cap_hidden']=step_radius2.hi<lower_disk.square().lo
            checks[f'sector_{i}_branch_{branch}_distinct_azimuth_wedge']=sbound.hi<(
                upper_disk*(I.of('.4')-I.of('.4')*I.of('.4').square()/6)).lo
        sa=I.of(max(spans))
        checks[f'sector_{i}_A_distinct_azimuth_wedge']=sa.hi<(
            upper_disk*(I.of('.4')-I.of('.4')*I.of('.4').square()/6)).lo
        inner=RA-(a.square()-sa.square()).sqrt()
        checks[f'sector_{i}_A_inner_surface_hidden']=(
            (upper_disk.square()-sa.square()).lo>inner.square().hi
            and (lower_disk.square()-sa.square()).lo>RA.square().hi)
        checks[f'sector_{i}_A_lower_clip_hidden']=(
            ((RA+a).square()+sa.square()-(contact-y).square()).hi<lower_disk.square().lo)
    return {'schema':'p4-ideal-edited-head-exposure-window/1',
            'status':'ideal_radial_exposure_proved' if all(checks.values()) else 'outside_proven_window',
            'checks':checks,'scope':('H215 hidden artificial cuts, disjoint exposed azimuth wedges and '
                                     'radial single-interval material over the complete ideal head driver box.'),
            'remaining':['Native finite trim/Boolean correspondence over the entire joint interval domain'],
            'execution_approved':False}


def assess_head_finite_trim_window(plan, windows, mouth_window):
    """Verify ideal finite head trim events and their order over the joint box."""
    from .root_exit_certificate import _trig

    exposure = assess_head_exposure_window(plan, windows, mouth_window)

    def interval(pair):
        low, high = pair
        return I(I.of(low).lo, I.of(high).hi)

    h = {key.removeprefix('head.'):interval(pair) for key,pair in windows.items()}
    center = h['Y40']
    step = h['Y_head_step']
    mouth = interval(mouth_window)
    sphere = h['R32']
    apex = h['cone_apex_Y']
    sn,cs = _trig(h['cone_half_angle_initial_exact'])
    slope = sn/cs
    slope2 = slope.square()
    upper_tube = h['r_upper_fillet']
    fillet_y = step-upper_tube
    gap = h['R40']-upper_tube
    fillet_major = (gap.square()-(fillet_y-center).square()).sqrt()
    fillet_contact = center+h['R40']*(fillet_y-center)/gap

    def cone_field(y):
        y = I.of(y)
        return slope2*(y-apex).square()+(y-center).square()

    def sphere_field(y):
        return sphere.square()+center.square()-2*center*I.of(y)

    # Positive cone/sphere junction. The other root is outside the
    # previously accepted positive nappe and upper axial chart.
    a,b,c = 1+slope2,-2*slope2*apex,slope2*apex.square()-sphere.square()
    junction = (-b+(b.square()-4*a*c).sqrt())/(2*a)
    sphere_cone = sphere_field(junction)
    sphere_step = sphere_field(step)
    cone_mouth = cone_field(mouth)
    fillet_step = fillet_major.square()+(step-center).square()
    y_middle = I.of('-18.5')
    y_lower_clip = I.of('-17.2')

    def fillet_radius(y):
        return fillet_major+(upper_tube.square()-(y-fillet_y).square()).sqrt()

    r_contact = (h['R40'].square()-(fillet_contact-center).square()).sqrt()
    f_mid,f_top = fillet_radius(y_middle),fillet_radius(y_lower_clip)
    checks = {
        'H215_radial_exposure_and_artificial_caps':exposure['status']=='ideal_radial_exposure_proved',
        'positive_sphere_cone_event_inside_upper_axial_chart':junction.lo>12 and (mouth-junction).lo>0,
        'sphere_plane_before_sphere_cone_in_the_radial_chart':(sphere_step-sphere_cone).lo>0,
        'order_of_inner_fillet_and_mouth_transitions':(cone_mouth-fillet_step).lo>0,
        'lower_fillet_event_window_order':(y_middle-fillet_contact).lo>0 and
            (y_lower_clip-y_middle).lo>0 and (step-y_lower_clip).lo>0 and (y_lower_clip-fillet_y).lo>0,
        'positive_upper_head_center_for_sphere_height_derivative':center.lo>0,
    }
    sectors = []
    for i in range(6):
        prefix = f'sector.{i}.'
        major,tube = h[prefix+'RA'],h[prefix+'ra']
        a_max = (major+tube).square()
        r_mid = (a_max-(y_middle-center).square()).sqrt()
        r_top = (a_max-(y_lower_clip-center).square()).sqrt()
        checks[f'sector_{i}_A_stays_below_fillet_before_its_visible_chart'] = (
            r_mid.hi<min(r_contact.lo,f_mid.lo) and r_top.hi<min(f_mid.lo,f_top.lo))

        def positive_event(target):
            other = (target-major.square()-tube.square())/(2*major)
            if other.lo<=0 or (tube-other).lo<=0:
                return None
            return (tube.square()-other.square()).sqrt()

        mouth_event = positive_event(cone_mouth)
        step_event = positive_event(fillet_step)
        checks[f'sector_{i}_A_exposes_both_central_phases'] = (
            mouth_event is not None and step_event is not None and (step_event-mouth_event).lo>0)
        report = {'sector':i,'branches':[]}
        if mouth_event is not None and step_event is not None:
            report['A_positive_mouth_s_mm']=[str(mouth_event.lo),str(mouth_event.hi)]
            report['A_positive_fillet_s_mm']=[str(step_event.lo),str(step_event.hi)]
        for b in (0,1):
            key=prefix+f'branch.{b}.'
            radius,d=h[key+'rb'],h[key+'d']
            directed_d=-d if b==0 else d
            gap=radius-tube
            w=(gap.square()-d.square()).sqrt()
            b_major=major-w
            seam=tube*directed_d/gap
            seam_rho=major+tube*w/gap
            D_seam=seam.square()+seam_rho.square()
            outer=(radius-directed_d).square()+b_major.square()
            checks[f'sector_{i}_branch_{b}_finite_A_events_before_seam'] = (
                directed_d.lo>0 and step_event is not None and (seam-step_event).lo>0
                and (D_seam-sphere_step).lo>0 and (cone_mouth-D_seam).lo>0
                and (D_seam-cone_field(12)).lo>0)
            checks[f'sector_{i}_branch_{b}_finite_B_events_in_order'] = (
                (radius-directed_d-seam).lo>0 and b_major.lo>0
                and (D_seam-sphere_step).lo>0 and (sphere_step-sphere_cone).lo>0
                and (sphere_cone-outer).lo>0)
            report['branches'].append({'side':b,'contact_s_abs_mm':[str(seam.lo),str(seam.hi)]})
        sectors.append(report)
    return {'schema':'p4-ideal-edited-head-finite-trim-window/1',
            'status':'ideal_finite_trim_events_proved' if all(checks.values()) else 'outside_proven_window',
            'checks':checks,'sectors':sectors,
            'sphere_to_cone_y_mm':[str(junction.lo),str(junction.hi)],
            'method':('The A torus squared radial field strictly decreases in |s| away from its center. '
                      'Each B field decreases beyond its tangent seam because its displacement has '
                      'the opposite sign. Thus strict bracketing controls all finite event roots. '
                      'The upper fillet comparison is strictly increasing in Y where the A radial '
                      'branch is outside the fillet major circle; the earlier axial interval is hidden.'),
            'scope':'Ideal finite head boundaries and phase order throughout the declared driver windows.',
            'remaining':['Independent native finite trim and Boolean output bounds over the edit domain'],
            'execution_approved':False}


def assess_head_stock_containment_window(plan, stock_windows, head_windows):
    """Verify the entire edited head cut stays inside the edited stock away from the mouth."""
    from .nx2506_stock_bands import _exact_stock_parameters
    from .root_exit_certificate import _trig

    s = _exact_stock_parameters(plan, stock_windows)
    h = {name.removeprefix('head.'):I(I.of(lo).lo,I.of(hi).hi)
         for name,(lo,hi) in head_windows.items()}
    major = h['R40']
    center = h['Y40']
    upper = h['r_upper_fillet']
    upper_y = h['Y_head_step']-upper
    contact_y = center+major*(upper_y-center)/(major-upper)
    upper_major = ((major-upper).square()-(upper_y-center).square()).sqrt()
    lower = h['r_lower_fillet']
    lower_y = h['Y_lower_step']+lower
    lower_major = ((major-lower).square()-(lower_y-center).square()).sqrt()
    r40_last = (major.square()-(contact_y-center).square()).sqrt()
    above_lower_head = I.of(h['R31'].hi.copy_negate())
    section_cone_slope = (s['R15']-s['R14'])/(s['Y15']-s['Y14'])
    def stock_cone(y):
        return s['R14']+(I.of(y)-s['Y14'])*section_cone_slope

    up_to_step = max(h['R31'].hi,(lower_major+lower).hi,
                     r40_last.hi,(upper_major+upper).hi)
    first_a_y = I.of(contact_y.lo)
    sn,cs = _trig(h['cone_half_angle_initial_exact'])
    top_head_radius = max(h['R32'].hi,((sn/cs)*(s['Y_mouth']-h['cone_apex_Y'])).hi)
    max_a_radius = Decimal(0)
    for i in range(6):
        k = f'sector.{i}.'
        major_a,tube_a = h[k+'RA'],h[k+'ra']
        spans=[]
        for j in (0,1):
            prefix=k+f'branch.{j}.'
            d,b=h[prefix+'d'],h[prefix+'rb']
            displacement=-d if j==0 else d
            gap=b-tube_a
            rb_major=major_a-(gap.square()-d.square()).sqrt()
            spans.append((tube_a*displacement/gap).hi)
            # Exposed B side and d are opposite; |s| <= q_B-|d|.
            rb=( (rb_major+b).square()+(b-displacement).square() ).sqrt()
            top_head_radius=max(top_head_radius,rb.hi)
        r_a=((major_a+tube_a).square()+I.of(max(spans)).square()).sqrt()
        max_a_radius=max(max_a_radius,r_a.hi)
    top_head_radius=max(top_head_radius,max_a_radius)
    lower_clearance=(stock_cone(above_lower_head)-I.of(up_to_step)).lo
    a_clearance=(stock_cone(first_a_y)-I.of(max_a_radius)).lo
    upper_stock_min=min(stock_cone(I.of(h['Y_head_step'].lo)).lo,
                        *(s[name].lo for name in ('R15','R16','R17','R18','R19','M19')))
    top_clearance=(I.of(upper_stock_min)-I.of(top_head_radius)).lo
    # Lower head and entire A lower interval start on the increasing
    # s15 cone. Later stock cylinders and arcs are all above the chosen
    # lower envelope of their endpoint radii and the s19 outer center.
    checks = {
        'head_starts_on_increasing_s15_stock_cone':section_cone_slope.lo>0
            and (above_lower_head-s['Y14']).lo>0 and (s['Y15']-h['Y_head_step']).lo>0,
        'lower_head_inside_stock_at_all_axial_stations':lower_clearance>0,
        'A_lower_caps_inside_stock_at_first_exposed_station':a_clearance>0,
        'head_upper_tori_sphere_cone_clear_the_entire_outer_stock':top_clearance>0,
    }
    return {'schema':'p4-ideal-head-stock-containment-window/1',
            'status':'ideal_head_stock_containment_proved' if all(checks.values()) else 'outside_proven_window',
            'checks':checks,
            'minimum_clearance_mm':{'lower_axial':str(lower_clearance),'A_lower':str(a_clearance),
                                     'upper_head':str(top_clearance)},
            'execution_approved':False}


def prove_joint_ideal_edit_window(root, plan, driver_windows):
    """Combine the P3 analytic prerequisites over one complete driver window."""
    from .nx2506_stock_bands import _exact_stock_parameters

    stock_ids={r['id'] for r in plan['parameters']['canonical_definitions']['stock']['nodes']
               if r['class'] in ('independent_local','external_independent_reference')}
    stock={k:pair for k,pair in driver_windows.items() if k in stock_ids}
    flank={k:pair for k,pair in driver_windows.items() if k in _FLANK_DRIVERS}
    tail={k:pair for k,pair in driver_windows.items() if k in _TAIL_DRIVERS}
    head={k:pair for k,pair in driver_windows.items() if k.startswith('head.')}
    covered=stock.keys()|flank.keys()|tail.keys()|head.keys()
    if (set(driver_windows)!=covered or set(stock)!=stock_ids or set(flank)!=_FLANK_DRIVERS
            or set(tail)!=_TAIL_DRIVERS):
        raise ValueError('joint domain must cover all approved independent inputs exactly once')
    mouth=_exact_stock_parameters(plan,stock)['Y_mouth']
    proofs = {
        'stock_meridian':assess_stock_meridian_window(plan,stock),
        'stock_and_C5':assess_stock_c5_roll_window(root,plan,stock,flank),
        'tail_and_shared_interfaces':assess_cross_region_clearances(plan,stock,tail,head),
        'finite_head':assess_head_finite_trim_window(plan,head,(str(mouth.lo),str(mouth.hi))),
        'head_inside_stock':assess_head_stock_containment_window(plan,stock,head),
    }
    expected = ('ideal_stock_meridian_proved','ideal_stock_c5_roll_proved',
                'ideal_cross_region_clearances_proved','ideal_finite_trim_events_proved',
                'ideal_head_stock_containment_proved')
    admitted = tuple(f['status'] for f in proofs.values())==expected
    return {'schema':'p4-joint-ideal-edit-window/1',
            'status':'mathematical_window_proved' if admitted else 'mathematical_window_unproved',
            'driver_count':len(driver_windows),'driver_windows':driver_windows,'regional_proofs':proofs,
            'native_continuous_domain_status':'unverified','execution_approved':False}


def assess_joint_ideal_edit(overrides, proof):
    """Evaluate one explicit edit against a jointly proven mathematical window."""
    if not isinstance(overrides,Mapping):
        raise ValueError('overrides must be a mapping')
    if proof.get('schema')!='p4-joint-ideal-edit-window/1' or proof.get('status')!='mathematical_window_proved':
        raise ValueError('a proven joint mathematical window is required')
    windows=proof['driver_windows']
    outside=[]
    for name,value in overrides.items():
        if type(value) not in (float,int) or (type(value) is float and not math.isfinite(value)):
            raise ValueError('values must be finite dimensional numbers')
        if name not in windows or not float(windows[name][0])<=value<=float(windows[name][1]):
            outside.append(name)
    return {'schema':'p4-joint-ideal-edit-candidate/1','overrides':dict(overrides),
            'mathematically_admissible':not outside,'outside_proven_window':outside,
            'execution_approved':False}


def assess_edit_candidate(root, overrides=None):
    """Evaluate one simultaneous edit using the existing coupled P3 guards.

    A pass means only those guards passed; unverified material, topology,
    native geometry and error-budget conditions still block approval.
    """
    edits = dict(overrides or {})
    try:
        result = build_default_flank_candidate(root, edits)
    except (ValueError, ArithmeticError) as exc:
        return {'schema': 'p4-edit-candidate/1', 'overrides': edits,
                'candidate_status': 'rejected_by_evaluation',
                'reason': str(exc), 'edit_domain_validity': 'not_established',
                'execution_approved': False}
    candidate = {'schema': 'p4-edit-candidate/1', 'overrides': edits,
                 'candidate_status': 'necessary_checks_passed_unverified',
                 'c5_evaluation': result['c5_evaluation'],
                 'necessary_checks': result['candidate_domain_checks'],
                 'coupling': ['shared shaft diameter feeds stock and C5',
                              'shared C5 templates feed 22 straight and roll cutters',
                              'stock.Y_mouth is shared by head and stock'],
                 'edit_domain_validity': 'not_established', 'execution_approved': False,
                 'remaining': result['candidate_domain_checks']['remaining']}
    if set(edits) == {'slot.width'}:
        width = edits['slot.width']
        candidate['ideal_tail_interval'] = assess_tail_width_interval(width, width)
    return candidate


def assess_edit_admission(root, overrides):
    """Screen one simultaneous edit, then fail closed on unproved obligations.

    Driver names and units are those of the P3 construction inputs. Values are
    finite Python int/float values in mm or rad as defined by each driver.
    This pointwise screen is not a certificate for a surrounding interval.
    A passing screen is useful for selecting a candidate for further proof;
    it is not admission to the valid domain or authorization to write to NX.
    """
    if not isinstance(overrides, Mapping):
        raise ValueError('overrides must be a mapping of driver names to values')
    edits = dict(overrides)
    if any(not isinstance(key, str) or not key for key in edits):
        raise ValueError('driver names must be nonempty strings')
    def finite_number(value):
        if type(value) not in (int, float):
            return False
        try:
            return math.isfinite(value)
        except OverflowError:
            return False

    if any(not finite_number(value) for value in edits.values()):
        raise ValueError('driver values must be finite int or float, excluding bool')

    candidate = assess_edit_candidate(root, edits)
    passed = candidate['candidate_status'] == 'necessary_checks_passed_unverified'
    ideal_tail = None
    if passed and set(edits) == {'slot.width'}:
        ideal_tail = _assess_fixed_tail_admission(root, edits['slot.width'])
    coupled = None
    if passed and set(edits) == {'slot.width', 'F0002.P2.t_mm'}:
        coupled = _assess_fixed_tail_c5_admission(root, edits)
    angle = None
    if passed and len(edits) == 1 and next(iter(edits)) in _ANGLE_DRIVERS:
        name = next(iter(edits))
        angle = _assess_single_angle_admission(root, name, edits[name])
    flank_box = None
    tail_box = None
    if passed and edits and edits.keys() <= (_FLANK_DRIVERS | _TAIL_DRIVERS):
        tail_box = assess_tail_parameter_box()
        outside = [name for name, (lo, hi) in tail_box['windows_exact_mm'].items()
                   if name in edits and not float(lo) <= edits[name] <= float(hi)]
        tail_box['candidate_inside_box'] = not outside
        tail_box['outside'] = outside
        if edits.keys() & _FLANK_DRIVERS:
            flank_box = _assess_coupled_flank_admission(root, edits, tail_box)
    return {
        'schema': 'p4-edit-admission/1',
        'overrides': edits,
        'screen_status': 'necessary_checks_passed' if passed else 'rejected',
        'candidate': candidate,
        'ideal_tail': ideal_tail,
        'ideal_tail_and_spline_exits': coupled,
        'ideal_single_angle': angle,
        'ideal_coupled_flanks': flank_box,
        'ideal_tail_parameter_box': tail_box,
        'screen_scope': [
            'pointwise stock station, arc, and listed event checks; binary64',
            'pointwise head carrier, tangency and branch checks; binary64',
            'pointwise C5 section and roll-strip guards with shared shaft and 22 placements',
            'pointwise slot tail cross-section; not its complete finite exit',
        ],
        'not_established': [
            'complete edited stock, head, slot and 22-cutter material and trim topology',
            'whole-body source correspondence and continuous native boundary error',
            'native constraint propagation, solver behavior and saved geometry for the full domain',
        ],
        'valid_domain_admitted': False,
        'execution_approved': False,
    }


def _assess_single_angle_admission(root, name, value):
    """Certify one fixed-box angle window using rational perturbation bounds."""
    original = json.loads((Path(root)/C5).read_text(encoding='utf8'))
    params = {x['id']: x for x in original['parameters']}
    angle = params[name]
    default = angle['preview']['value']
    low, high = _flank_window(angle)
    result = {'schema': 'p4-single-angle-ideal-admission/1', 'driver': name,
              'window_binary64_rad': [low, high], 'default_preview_rad': default,
              'other_drivers': 'fixed to accepted P3 defaults',
              'execution_approved': False}
    if not low <= value <= high:
        result.update({'ideal_whole_body_connected': False,
                       'ideal_angle_admitted': False,
                       'reason': 'outside the sufficient single-angle window'})
        return result
    proof = _bound_flank_box(root, original, params, {name: (low, high)})
    result.update(proof)
    result.update(ideal_angle_admitted=proof['ideal_whole_body_connected'],
                  angle_delta_from_exact_default_upper_rad=proof['driver_delta_upper'][name],
                  endpoint_coordinate_delta_upper_mm=proof['endpoint_delta_upper'][name])
    return result


def _flank_window(parameter):
    default = (parameter['preview']['value'] if 'preview' in parameter else
               float(Fraction(*parameter['value_exact'])))
    half_width = 1e-6 if parameter['unit']=='rad' else 1e-5
    return default - half_width, default + half_width


def _assess_coupled_flank_admission(root, edits, tail_box):
    """Check a simultaneous interval for all 19 C5 and four tail drivers."""
    original = json.loads((Path(root)/C5).read_text(encoding='utf8'))
    params = {x['id']: x for x in original['parameters']}
    windows = {name: _flank_window(params[name]) for name in sorted(_FLANK_DRIVERS)}
    result = {'schema': 'p4-coupled-flank-ideal-admission/1', 'windows_binary64': windows,
              'tail_width_mm': [4.9, 5.1], 'ideal_whole_body_connected': False,
              'tail_parameter_box': tail_box, 'execution_approved': False}
    outside = [name for name, (lo, hi) in windows.items() if name in edits and not lo <= edits[name] <= hi]
    outside.extend(tail_box['outside'])
    if outside:
        result['outside'] = outside
        return result
    result.update(_bound_flank_box(root, original, params, windows))
    tail_interval = assess_tail_width_interval(4.9, 5.1)
    result['tail_interval'] = tail_interval
    result['ideal_whole_body_connected'] &= tail_box['status'] == 'proved'
    return result


def _bound_flank_box(root, original, params, windows, stock=None):
    """Apply the exact endpoint elimination matrix to a simultaneous perturbation."""
    q = Fraction
    driver_deltas = {}
    for name, (low, high) in windows.items():
        parameter = params[name]
        if 'preview' in parameter:
            actual_lo, actual_hi = q(parameter['preview']['lower']), q(parameter['preview']['upper'])
        else:
            actual_lo = actual_hi = q(*parameter['value_exact'])
        driver_deltas[name] = max(abs(q(low)-actual_hi), abs(q(high)-actual_lo))
    shaft = q(*params['shaft_outer_diameter_mm']['value_exact'])/2
    shaft_interval = (shaft,shaft) if stock is None else (q(stock['Rshaft'].lo),q(stock['Rshaft'].hi))
    shaft_min,shaft_max=shaft_interval
    shaft_delta=max(abs(r-shaft) for r in shaft_interval)
    pitch, radius = (q(*params[key]['value_exact']) for key in ('pitch_radius_mm', 'root_radius_mm'))
    pitch_delta=driver_deltas.get('pitch_radius_mm',0)
    radius_delta=driver_deltas.get('root_radius_mm',0)
    pitch_min=pitch-pitch_delta
    radius_min,radius_max=radius-radius_delta,radius+radius_delta
    endpoint_deltas = {}
    sections = {}
    for label, template in original['templates'].items():
        poles = [{axis: [q(p[axis]['lower']), q(p[axis]['upper'])]
                  for axis in ('t_mm', 'r_mm')} for p in template['poles']]
        ends = {key: {axis: [q(point[axis]['lower']), q(point[axis]['upper'])]
                      for axis in ('t_mm', 'r_mm')}
                for key, point in template['endpoints'].items()}
        a, b = [[q(*v) for v in row] for row in template['endpoint_weights_exact']]
        det = a[1]*b[5] - a[5]*b[1]
        if det == 0 or det != q(*template['matrix_determinant_exact']):
            raise ValueError('endpoint elimination matrix changed')
        roles = ('outer', 'root') if label == 'F0002' else ('root', 'outer')
        target = {}
        for role in roles:
            name = f'{label}.alpha_{role}_rad'
            target[role] = (radius_max if role=='root' else shaft_max)*driver_deltas.get(name,0)
            if role=='root':
                target[role] += radius_delta+pitch_delta
            else:
                target[role] += shaft_delta
            if name in driver_deltas:
                endpoint_deltas[name] = str(target[role])
            for axis in ('t_mm', 'r_mm'):
                ends[role][axis][0] -= target[role]
                ends[role][axis][1] += target[role]
        for axis in ('t_mm', 'r_mm'):
            for i in (2, 3, 4):
                displacement = driver_deltas.get(f'{label}.P{i}.{axis}', 0)
                poles[i][axis][0] -= displacement
                poles[i][axis][1] += displacement
            for i, (u, v) in ((1, (b[5], -a[5])), (5, (-b[1], a[1]))):
                displacement = (abs(u/det)*target[roles[0]] + abs(v/det)*target[roles[1]]
                                + sum(abs((u*a[j]+v*b[j])/det)*driver_deltas.get(f'{label}.P{j}.{axis}', 0)
                                      for j in (2, 3, 4)))
                poles[i][axis][0] -= displacement
                poles[i][axis][1] += displacement
        sections[label] = {'poles': poles, 'endpoints': ends}
    def absolute(interval):
        return max(abs(interval[0]), abs(interval[1]))
    def iv(interval):
        return I(I.of(interval[0]).lo, I.of(interval[1]).hi)
    all_poles = [p for s in sections.values() for p in s['poles']]
    max_t = max([absolute(p['t_mm']) for p in all_poles]
                + [absolute(s['endpoints']['outer']['t_mm'])*q('13.1')/shaft_min
                   for s in sections.values()] + [radius_max])
    min_r = min([p['r_mm'][0] for p in all_poles] + [pitch_min-radius_max]
                + [s['endpoints']['outer']['r_mm'][0] for s in sections.values()])
    signs, increments, caps = [], [], []
    for label, section in sections.items():
        for pole in section['poles']:
            ti, ri = pole['t_mm'], pole['r_mm']
            signs.append(ri[0] > 0 and (ti[0] > 0 if label == 'F0002' else ti[1] < 0))
            caps.append(absolute(ti)**2+absolute(ri)**2 < q('13.1')**2)
        for a, b in zip(section['poles'], section['poles'][1:]):
            dt = iv(a['t_mm'])-iv(b['t_mm'])
            dr = (iv(a['r_mm'])-iv(b['r_mm']) if label == 'F0002'
                  else iv(b['r_mm'])-iv(a['r_mm']))
            increments.append(dr.lo > 0 and (dt-I.of(q('0.4'))*dr).lo > 0)
    ends = [s['endpoints'][role] for s in sections.values() for role in ('root', 'outer')]
    root_ends = [s['endpoints']['root'] for s in sections.values()]
    root_t = max(absolute(p['t_mm']) for p in root_ends)
    root_r_hi = max(p['r_mm'][1] for p in root_ends)
    root_branch = all(p['r_mm'][1] < pitch_min and absolute(p['t_mm']) < radius_min and
                      absolute(p['t_mm'])**2+absolute(p['r_mm'])**2 < shaft_min**2 for p in root_ends)
    c7 = (I(Decimal('1.235894765027'),Decimal('1.235894765031')) if stock is None else stock['Y7']+71)
    f7 = {}
    for label, section in sections.items():
        f7[label] = {}
        for which, pt in section['endpoints'].items():
            ti, ri = iv(pt['t_mm']), iv(pt['r_mm'])
            f = ti.square() + (15-((15-ri).square()-c7.square()).sqrt()).square()-iv(shaft_interval).square()
            f7[label][which] = [str(f.lo), str(f.hi)]
    signs_f7 = all(Decimal(f7[s]['root'][1]) < 0 < Decimal(f7[s]['outer'][0]) for s in f7)
    base = _assess_fixed_tail_c5_admission(root, {'slot.width': 5.0,
                                                   'F0002.P2.t_mm': 1.2858096483109538})
    checks = {
        'fixed_chart_and_baseline_body_proof': base['ideal_whole_body_connected'],
        'strict_pole_sides_and_radius': all(signs),
        'strict_pole_order_and_radial_star_slope': all(increments),
        'strict_control_hull_inside_cap': all(caps),
        'lower_root_circle_branch': root_branch,
        'section_in_reviewed_roll_strip': max_t < q('1.54') and min_r > q('11.1124'),
        'neighbor_wedges_disjoint': max_t/min_r < q('3.14')/22,
        'root_arc_radial_star': root_t < q('0.513') and radius_min**2-root_t**2 > q('0.52')**2,
        'root_arc_fixed_exit_bounds': q('11.112') < pitch_min-radius_max and root_r_hi < q('11.320') and radius_max < q('0.737'),
        'spline_L_between_2_9_and_3_69': all(q('2.9') < 15-p['r_mm'][1] and 15-p['r_mm'][0] < q('3.69') for p in ends),
        's7_transition_endpoint_signs': signs_f7,
    }
    return {
        'ideal_whole_body_connected': all(checks.values()),
        'checks': checks, 'endpoint_f_at_s7_junction_mm2': f7,
        'driver_delta_upper': {name: str(delta) for name, delta in driver_deltas.items()},
        'endpoint_delta_upper': endpoint_deltas,
        'proof': ('Each endpoint coordinate changes by at most its circle radius times the '
                  'maximum angle change plus the shifts in pitch and circle radius. '
                  'Shared phase rotates all wedges evenly around the fixed stock axis. '
                  'The constant exact endpoint matrix transfers '
                  'the endpoint and independent pole changes to P1/P5. Rational enclosures '
                  'certify strict section, pole-order, radial-star, roll-strip and wedge '
                  'guards across the whole interval, and directed intervals give the '
                  's7 endpoint signs. The fixed-box proof supplies the stock/head, '
                  'first-exit and connected-core arguments once these '
                  'stronger interval guards hold.'),
        'scope': ('stated C5 and tail inputs with accepted fixed P3 stock/head chart; '
                  'native edits, edited source correspondence and continuous boundary error remain open'),
    }


def assess_stock_c5_roll_window(root, plan, stock_windows, flank_windows):
    """Verify ideal C5 branch and first-exit guards with the shared stock drivers varying."""
    from .nx2506_stock_bands import _exact_stock_parameters

    if set(flank_windows)!=_FLANK_DRIVERS:
        raise ValueError('all independent C5 flank and placement drivers are required')
    stock=_exact_stock_parameters(plan,stock_windows)
    original=json.loads((Path(root)/C5).read_text(encoding='utf8'))
    params={row['id']:row for row in original['parameters']}
    flank=_bound_flank_box(root,original,params,flank_windows,stock)
    c7=stock['Y7']+71
    tube=stock['tube_R8']
    major=stock['M8']
    def s8(v):
        y=I.of(v)-c7
        return major-(tube.square()-y.square()).sqrt()
    def n(arm,height):
        return 15-(I.of(arm).square()-I.of(height).square()).sqrt()

    full_sweep_denominator=(tube.square()-(I.of('3.9')-c7).square()).sqrt()
    checks={
        'ordered_shaft_roll_stations':stock['Y6'].hi<-71 and c7.lo>0
            and stock['Y8'].lo>Decimal('-67.1') and stock['R9'].hi<Decimal('13.001'),
        'spline_exit_before_2_6':(n('3.69','2.6')-s8('2.6')).lo>0,
        'root_exit_after_2_1_and_before_3_1':s8('2.1').lo>Decimal('12.03')
            and s8('3.1').hi<Decimal('12.56') and (n('3.9','3.1')-s8('3.1')).lo>0,
        'early_and_late_exit_derivative_margins':c7.lo>Decimal('1.23') and tube.lo>Decimal('4.9')
            and (tube.square()-(I.of('2.6')-c7).square()).sqrt().lo>Decimal('4.6'),
        'whole_roll_radial_clearance_strictly_rises':(I.of('3.9')/full_sweep_denominator).hi<Decimal('.99'),
        'auxiliary_cap_and_axis_remain_clear':stock['Rshaft'].lo>12 and stock['R9'].hi<Decimal('13.1'),
    }
    success=flank['ideal_whole_body_connected'] and all(checks.values())
    return {'schema':'p4-joint-stock-c5-roll-window/1',
            'status':'ideal_stock_c5_roll_proved' if success else 'outside_proven_window',
            'checks':checks,'flank_chart_checks':flank['checks'],
            'scope':'All named stock and C5 input intervals, with the shared variable shaft and s7/s8 exit stations.',
            'remaining':['Head finite exposed regions under full editing','Continuous NX finite-boundary '
                         'verification on combined edited models'],
            'execution_approved':False}


def _assess_fixed_tail_c5_admission(root, edits):
    """Enclose the fixed two-driver box; certify finite roll exit roles."""
    q = Fraction
    width, t = edits['slot.width'], edits['F0002.P2.t_mm']
    tail = _assess_fixed_tail_admission(root, width)
    in_window = _P2_LOW <= t <= _P2_HIGH
    if not in_window or not tail['ideal_tail_admitted']:
        return {'ideal_spline_roles_admitted': False, 'tail': tail,
                'reason': 'outside the sufficient coupled box', 'execution_approved': False}

    candidates = [build_default_flank_candidate(root, {'F0002.P2.t_mm': end})
                  for end in (_P2_LOW, _P2_HIGH)]
    p = candidates[0]['stock_and_head']['parameters']
    templates = [c['section']['templates'] for c in candidates]
    params = {item['id']: item for item in candidates[0]['c5_parameters']}
    shaft = q(*params['shaft_outer_diameter_mm']['value_exact']) / 2
    pitch = q(*params['pitch_radius_mm']['value_exact'])
    root_radius = q(*params['root_radius_mm']['value_exact'])
    def bounds(coord):
        return q(coord['lower']), q(coord['upper'])
    def abs_upper(coord):
        lo, hi = bounds(coord)
        return max(abs(lo), abs(hi))
    def enclosure(coord):
        return I(Decimal(coord['lower']), Decimal(coord['upper']))
    all_sections = [section for item in templates for section in item.values()]
    max_t = max([abs_upper(pole['t_mm']) for section in all_sections
                 for pole in section['poles']]
                + [abs_upper(section['endpoints']['outer']['t_mm'])*q('13.1')/shaft
                   for section in all_sections] + [root_radius])
    min_r = min([bounds(pole['r_mm'])[0] for section in all_sections
                 for pole in section['poles']]
                + [bounds(section['endpoints']['outer']['r_mm'])[0]
                   for section in all_sections] + [pitch-root_radius])
    fixed_endpoints = all(templates[0][side]['endpoints'] == templates[1][side]['endpoints']
                          and all(a['r_mm'] == b['r_mm'] for a, b in
                                  zip(templates[0][side]['poles'], templates[1][side]['poles']))
                          for side in ('F0002', 'F0024'))
    c7 = I(Decimal('1.235894765027'), Decimal('1.235894765031'))
    endpoint_signs = {}
    for side in ('F0002', 'F0024'):
        section = templates[0][side]
        endpoint_signs[side] = {}
        for role in ('root', 'outer'):
            pt = section['endpoints'][role]
            ti, ri = enclosure(pt['t_mm']), enclosure(pt['r_mm'])
            f = ti.square() + (15-((15-ri).square()-c7.square()).sqrt()).square() - I.of(shaft).square()
            endpoint_signs[side][role] = [str(f.lo), str(f.hi)]
    signs_ok = all(Decimal(endpoint_signs[s]['root'][1]) < 0 <
                   Decimal(endpoint_signs[s]['outer'][0]) for s in endpoint_signs)
    endpoint_r = [bounds(section['endpoints'][role]['r_mm']) for section in all_sections
                  for role in ('root', 'outer')]
    section_l_bounds = all(q('2.9') < 15-hi and 15-lo < q('3.69')
                           for lo, hi in endpoint_r)
    c7_actual = q(p['stock.Y7']) + 71
    fixed_stock = (q('1.235894765027') < c7_actual < q('1.235894765031')
                   and p['stock.M8'] == 17.1665 and p['stock.tube_R8'] == 5.0
                   and p['stock.Y8'] == -67.0 and shaft == q(856141326037549, 70368744177664))
    # These rational comparisons bound n(v)>12.37 and R_s8(v)<12.37
    # at v=2.6, using L<3.69, 1.235894765027<c7 and M8<17.1666.
    at_upper = (q('3.69')**2-q('2.6')**2 < (15-q('12.37'))**2
                and q(25)-(q('2.6')-q('1.235894765027'))**2 >
                (q('17.1666')-q('12.37'))**2)
    # dF/dv >= 5.4*v-6.1*max(v-1.23,0), on the s8 part of
    # [1.2,2.6]. The lower bound is >5 at both ends of its linear pieces.
    derivative = (q('4.9')**2-q('1.5')**2 > q('4.6')**2
                  and 28/q('4.6') < q('6.1')
                  and 2*q('11.5')/q('3.69') > q('5.4')
                  and q('3.69')**2-q('1.2')**2 < q('3.5')**2
                  and q('5.4')*q('1.2') > 5
                  and q('5.4')*q('2.6')-q('6.1')*(q('2.6')-q('1.23')) > 5)
    root_r_hi = max(bounds(section['endpoints']['root']['r_mm'])[1] for section in all_sections)
    root_bounds = (q('11.112') < pitch-root_radius and root_r_hi < q('11.320')
                   and root_radius < q('0.737'))
    # At v=2.1, root L>=3.68 gives n<12, and |t|<.737.
    # R_s8>=M8-5>12.03. At v=3.1, L<3.888 gives n>12.61;
    # the rational square inequality bounds R_s8<12.56.
    root_at_low = (q('3.68')**2-q('2.1')**2 > 3**2
                   and 12**2+q('0.737')**2 < q('12.03')**2
                   and q('17.1664')-5 > q('12.03'))
    root_at_high = (q('3.9')**2-q('3.1')**2 < q('2.39')**2
                    and q(25)-(q('3.1')-q('1.235894765027'))**2 >
                    (q('17.1666')-q('12.56'))**2)
    # For the whole filled section, n/r>0.9905 and H'(y)<0.918*sin(phi).
    # Therefore r(phi)-H(y(phi)) strictly increases for 0<phi<pi/2.
    # d<3.9 also keeps the sweep before Y8; at phi=pi/2, n=15>H.
    nmin, tmax = q('11.1124'), q('1.54')
    qmax = q('3.9')-q('1.235894765027')
    full_sweep = (15-min_r < q('3.9') and qmax < 5
                  and nmin**2 > q('0.9905')**2*(nmin**2+tmax**2)
                  and qmax**2 < q('0.918')**2*(25-qmax**2)
                  and q(25)-qmax**2 > (q('17.1666')-15)**2)
    slope_margins = []
    for item in templates:
        for side in ('F0002', 'F0024'):
            for first, second in zip(item[side]['poles'], item[side]['poles'][1:]):
                t1, t2 = enclosure(first['t_mm']), enclosure(second['t_mm'])
                r1, r2 = enclosure(first['r_mm']), enclosure(second['r_mm'])
                # Both t coordinates decrease in pole order. F0002 moves
                # from outer to root, F0024 from root to outer.
                dr = r1-r2 if side == 'F0002' else r2-r1
                slope_margins.append((t1-t2-I.of(q('0.4'))*dr).lo)
    root_t = max(abs_upper(section['endpoints']['root']['t_mm'])
                 for section in all_sections)
    root_star = (root_t < q('0.513') and
                 root_radius**2-root_t**2 > q('0.52')**2 and
                 11-q('0.513')*q('2.3') > 0)
    # In clipped roll points n<=rho<=13. Hence 15-n>=2 and
    # dn/dr=(15-r)/(15-n)<3.9/2<2.3. The root arc has
    # |dr/dt|<.513/.52<1 on its selected lower branch.
    radial_star = (min_r > 11 and max_t < q('1.6') and
                   q('3.9')/2 < q('2.3') and
                   11*q('0.4')-q('1.6')*q('2.3') > 0)
    # f(y0)>4.7 for the lower tail cylinder branch, exactly by squaring.
    core_clear_tail = q('37.5')**2-q(4)**2 < (42-q('4.7'))**2
    fixed_roll_stock_radius = (fixed_stock and p['stock.R8'] == 13.0
                               and p['stock.R9'] == 13.0 and 15-min_r < 4)
    fixed_straight_stock_radius = (p['stock.R5'] == 11.0
                                   and p['stock.R6'] == float(shaft)
                                   and p['stock.R7'] == float(shaft)
                                   and p['stock.Y6'] < -71 < p['stock.Y7'])
    axial_gap = (p['stock.Y4'] < -125 and -71+q('3.9') < -67
                 and -67 < -32 < -31)
    checks = {
        'tail_finite_cut_and_connectivity': tail['ideal_tail_admitted'],
        'endpoint_circle_targets_and_r_poles_fixed': fixed_endpoints,
        'fixed_s7_s8_stock_chart': fixed_stock,
        'endpoint_f7_root_negative_outer_positive': signs_ok,
        'spline_L_between_2_9_and_3_69': section_l_bounds,
        's8_at_v_2_6_all_spline_points_outside': at_upper,
        's8_exit_derivative_lower_above_5': derivative,
        'fixed_root_arc_bounds': root_bounds,
        'root_arc_inside_at_v_2_1': root_at_low,
        'root_arc_outside_at_v_3_1': root_at_high,
        'full_sweep_first_exit_no_reentry': full_sweep,
        'section_in_reviewed_roll_strip': max_t < q('1.54') and min_r > q('11.1124'),
        'neighbor_wedges_disjoint': max_t/min_r < q('3.14')/22,
        'strict_flank_slope_at_both_p2_endpoints': all(x > 0 for x in slope_margins),
        'lower_root_arc_radial_star': root_star,
        'rolled_flank_radial_star_when_clipped': radial_star,
        'roll_stock_radius_at_most_13': fixed_roll_stock_radius,
        'straight_stock_radius_at_most_shaft': fixed_straight_stock_radius,
        'tail_core_r4_clear': core_clear_tail,
        'separate_tail_roll_and_head_stations': axial_gap,
    }
    return {
        'schema': 'p4-fixed-tail-c5-spline-roles/1',
        'ideal_spline_roles_admitted': all(checks.values()), 'checks': checks,
        'ideal_whole_body_connected': all(checks.values()),
        'minimum_flank_slope_margin_mm': str(min(slope_margins)),
        'endpoint_f_at_s7_junction_mm2': endpoint_signs,
        'section_abs_t_upper_mm': str(max_t), 'section_r_lower_mm': str(min_r),
        'p2_window_binary64_mm': [_P2_LOW, _P2_HIGH], 'tail': tail,
        'proof': ('The C5 endpoint equations have a fixed matrix and fixed circle targets; '
                  'P1/P5 tangential coordinates are affine in P2.t, radial coordinates are fixed. '
                  'Strict signed/ordered pole guards and convex cap/strip guards at both endpoints '
                  'therefore hold throughout the window. Each spline has strict signed t and '
                  'radial monotonicity. At Y7, F=t^2+(15-sqrt((15-r)^2-(Y7+71)^2))^2-Rshaft^2 '
                  'is strictly monotone along each spline, with opposite signs at its fixed endpoints, '
                  'so there is exactly one s7/s8 role transition on each spline. '
                  'On s7 F increases with v=Y+71; the rational derivative guard proves this '
                  'on s8 through v=2.6, where the whole spline is outside. '
                  'The unchanged lower root arc is inside at v=2.1 and outside at v=3.1. '
                  'The full section satisfies n/r>0.9905 while the s8 stock slope is '
                  '<0.918*sin(phi); therefore its radial stock clearance strictly increases '
                  'through the 90-degree roll. The roll remains before Y8, and all points '
                  'are outside at 90 degrees. Each initially interior point has exactly one '
                  'first exit and no re-entry. '
                  'The filled section lies in the t/r wedge; roll increases radial projection, '
                  'so the 22 equal-angle wedges are disjoint. At both P2 endpoints, every '
                  'flank pole increment satisfies d|t|>0.4 dr; affine dependence extends '
                  'this to the box and the positive B-spline derivative basis extends it '
                  'to the whole flank. Within stock, n>11 and dn/dr<2.3, so '
                  'n*d|t|/dr-|t|*dn/dr>11*0.4-1.6*2.3>0. '
                  'The unchanged lower root arc satisfies |t|<0.513 and '
                  'sqrt(root_radius^2-t^2)>0.52, so its angular extent also increases '
                  'toward its two flanks. Thus in each member sector each cutter ray '
                  'intersects the clipped section only in an outer segment. Its radial '
                  'connectors begin on the shaft and, by the first-exit guard, stay '
                  'outside stock; the cap radius 13.1 also exceeds the stock bound 13. '
                  'Between Y4 and -31, every retained cross-section point can move '
                  'radially inward to the common uncut r<4 core. The tail joins that '
                  'core by the separate tail path argument, and '
                  'a full stock section at y=-32 joins it to the unchanged head: '
                  'the accepted fixed-head proof gives an uncut outer band above y=-31.'),
        'scope': ('ideal retained-body connectivity and C5 spline/root first-exit roles, '
                  'conditional on accepted P3 fixed stock/head chart, head radial-cut '
                  'and outer-band proofs; complete edited trims and native/source error remain open'),
        'execution_approved': False,
    }


def _assess_fixed_tail_admission(root, width):
    """Admit an ideal tail cut only, conditional on the accepted P3 chart.

    All non-width inputs are default; exact inequalities below do not certify
    the binary64 or native construction. The fixed-chart checks protect
    against accidentally applying this proof to a different parameter set;
    the P3 chart and its s5 radius bound remain explicit proof assumptions.
    """
    result = build_default_flank_candidate(root, {'slot.width': width})
    p = result['stock_and_head']['parameters']
    fixed = {'slot.radius': 37.5, 'slot.axis_y': -162.6, 'slot.axis_z': 42.0,
             'stock.Y0': -158.6, 'stock.Y1': -157.6, 'stock.Y2': -151.1,
             'stock.Y3': -150.4649147038914, 'stock.Y5': -123.2734790890097,
             'stock.R0': 6.9, 'stock.R1': 7.9, 'stock.R2': 7.9,
             'stock.R3': 9.0, 'stock.R4': 9.0, 'stock.R5': 11.0,
             'stock.M5': 11.0, 'stock.tube_R5': 2.0}
    chart_matches = all(p.get(k) == v for k, v in fixed.items())
    curves = result['stock_and_head']['stock_profile']['curves']
    early = [(c['id'], c['kind'], c['start'], c['end']) for c in curves[:5]]
    chart_matches = chart_matches and early == [
        ('s1', 'line', 'v0', 'v1'), ('s2', 'line', 'v1', 'v2'),
        ('s3', 'line', 'v2', 'v3'), ('s4', 'line', 'v3', 'v4'),
        ('s5', 'circular_arc', 'v4', 'v5')]
    if chart_matches:
        arc = curves[4]
        chart_matches = (arc['center_y_r_mm'] == [p['stock.Y4'], 11.0]
                         and arc['radius_mm'] == 2.0
                         and arc['start_rad'] == -math.pi/2
                         and arc['sweep_rad'] == math.pi/2)
    interval = assess_tail_width_interval(width, width)
    q = Fraction
    def f_exceeds(y, height):
        # f(y)=42-sqrt(37.5**2-(y+162.6)**2). Both sides
        # of the squared comparison are nonnegative on the stated support.
        dy = q(y) + q('162.6')
        radicand = q('37.5')**2 - dy**2
        return radicand >= 0 and q(42) > q(height) and radicand < (q(42)-q(height))**2
    checks = {
        'accepted_fixed_chart_previews': chart_matches,
        'finite_tail_branch_and_exit_order': interval['status'] == 'proved',
        'f_positive_on_stock_support': q(42) > q('37.5'),
        'f_above_r9_from_minus_144': f_exceeds('-144', '9'),
        'f_above_s5_radius_bound_from_minus_126': f_exceeds('-126', '11'),
        'r9_to_s5_station_in_interval': -126 < p['stock.Y4'] < -125.1,
        'all_straight_stations_are_y4': (
            len([n for n in result['csg_nodes'] if n['operation'] == 'extrude_profile']) == 22
            and all(n['y_limits_mm'][0] == p['stock.Y4']
                    for n in result['csg_nodes'] if n['operation'] == 'extrude_profile')),
    }
    return {
        'schema': 'p4-fixed-chart-ideal-tail-admission/1',
        'ideal_tail_admitted': all(checks.values()),
        'checks': checks,
        'width_mm': width,
        'interval_certificate': interval,
        'assumptions': [
            'accepted P3 tail stock chart: R=9 from the second cone to Y4, '
            'then the s5 stock radius is at most 11 through cutter support end Y=-125.1',
            'all drivers except slot.width fixed to the accepted P3 default chart',
            'P3 other cutters and head begin at or after Y4; their constructions are unchanged',
        ],
        'proof': (
            'On the cutter support intersecting stock, y+162.6 is positive, so f is increasing. '
            'The rational squared inequalities give f(-144)>9 and f(-126)>11. '
            'With the fixed stock chart, the cutter is absent after -144; '
            'therefore it is absent at Y4 and disjoint from the other features. '
            'The upper cylinder branch is above 42 while tail stock radius is at most 11. '
            'For every retained stock point in the affected interval, move vertically toward z=0: '
            'outside the width slab this remains outside the cutter; inside it the point has z<=f(y), '
            'so the path remains below the cutter. Next move x to zero in the stock disk, '
            'then along the stock axis to Y4. Since f>0 throughout, the paths avoid the cutter. '
            'Thus the retained tail is path-connected and joins the unchanged stock at Y4.'
        ),
        'scope': 'ideal finite tail cut and retained-tail connectivity only; not complete edited whole-body validity',
        'native_and_source_correspondence': 'not_established_for_this_edit',
        'execution_approved': False,
    }


def assess_tail_and_c5_interval(root, width_bounds, p2_t_bounds):
    """Enclose local ideal slot and C5 constraints over one two-driver box.

    All other inputs remain fixed. The C5 endpoint equations use a constant
    matrix and fixed circle targets, so P1 and P5 are affine in the edited
    P2 coordinate. Positive side/order guards are affine, and the cap-ball
    and roll-strip constraints are convex in those poles. Acceptance at both
    endpoints therefore establishes those local guards through the interval.
    """
    width_lo, width_hi = width_bounds
    p2_lo, p2_hi = p2_t_bounds
    if (type(p2_lo) not in (int, float) or type(p2_hi) not in (int, float)
            or not math.isfinite(p2_lo) or not math.isfinite(p2_hi) or p2_lo > p2_hi):
        raise ValueError('P2 bounds must be finite and ordered')
    tail = assess_tail_width_interval(width_lo, width_hi)
    endpoints = [assess_edit_candidate(root, {'F0002.P2.t_mm': t}) for t in (p2_lo, p2_hi)]
    affine_guards_pass = all(e['candidate_status'] == 'necessary_checks_passed_unverified' for e in endpoints)
    return {'schema': 'p4-tail-c5-local-domain-box/1',
            'slot_width_interval_mm': list(width_bounds), 'F0002_P2_t_interval_mm': list(p2_t_bounds),
            'ideal_tail_topology': tail,
            'ideal_c5_section_and_strip_guards': 'proved' if affine_guards_pass else 'not_proved',
            'c5_endpoint_checks': endpoints,
            'separation': 'With fixed stock, tail engagement ends before the first C5 straight station.',
            'scope': 'local ideal tail topology and C5 section/strip guards; full edited trims not established',
            'edit_domain_validity': 'not_established', 'execution_approved': False}
