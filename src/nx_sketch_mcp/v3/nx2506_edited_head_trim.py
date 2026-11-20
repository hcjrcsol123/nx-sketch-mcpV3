"""Original finite head verification at an explicitly edited NX result."""
from collections import defaultdict
from fractions import Fraction as Q

from .nx2506_carrier_bound import dot, tangent_range, upper_float, v
from .nx2506_edit_domain import EDITED_DIRECTION_LIMIT_MM
from .nx2506_head_ribbon_acceptance import _linear_poly_arc, _sphere_height_residual
from .nx2506_roll_s7_bound import face_edges
from .nx2506_root_patches import arc_endpoint
from .nx2506_stock_bands import _exact_stock_parameters, hoop
from .nx2506_tail_trim_bound import _sqrt
from .nx2506_trim_bound import _product
from .root_exit_certificate import I, _trig


def _bounds(number):
    a=I.of(number)
    return Q(a.lo),Q(a.hi)


def _mid(number):
    return sum(_bounds(number))/2


def _gap(a,b):
    return sum(max(abs(Q(x)-Q(y)) for x in p for y in q) for p,q in zip(a,b))


def _xyz(values):
    return tuple(_bounds(p) for p in values)


def _pair_error(a,b):
    return min(max(_gap(p,q) for p,q in zip(a,order)) for order in (b,b[::-1]))


def _decreasing_root(fn,lo,hi):
    if fn(lo).lo<=0 or fn(hi).hi>=0:
        raise ValueError('edited finite head event lacks a strict bracket')
    for _ in range(45):
        m=(lo+hi)/2
        interval=fn(m)
        if interval.lo>0:
            lo=m
        elif interval.hi<0:
            hi=m
        else:
            break
    return I(I.of(lo).lo,I.of(hi).hi)


class EditedHead:
    """Exact branch parameters and finite endpoints for the chosen edited inputs."""
    def __init__(self,plan):
        self.p={r['id'].removeprefix('head.'):I.of(Q(r['value'])) for r in plan['parameters']['regional']
                if r['id'].startswith('head.')}
        p=self.p
        self.stock=_exact_stock_parameters(plan)
        self.mouth=self.stock['Y_mouth']
        self.y0=p['Y40']
        self.step=p['Y_head_step']
        self.sphere=p['R32']
        self.apex=p['cone_apex_Y']
        sn,cs=_trig(p['cone_half_angle_initial_exact'])
        self.slope=sn/cs
        self.q_upper=p['r_upper_fillet']
        self.y_upper=self.step-self.q_upper
        gap=p['R40']-self.q_upper
        self.r_upper=(gap.square()-(self.y_upper-self.y0).square()).sqrt()
        self.lower_contact=self.y0+p['R40']*(self.y_upper-self.y0)/gap
        self.junction=self._quadratic(self.sphere.square(),I.of(0))
        self.ribbons={}
        for i in range(6):
            self._sector(i)

    def _quadratic(self,total,other_center):
        sq=self.slope.square()
        a=1+sq
        b=-2*(sq*self.apex+other_center)
        c=sq*self.apex.square()+other_center.square()-total
        return (-b+(b.square()-4*a*c).sqrt())/(2*a)

    def cone_y(self,d2):
        return self._quadratic(d2,self.y0)

    def cone_field(self,y):
        return (self.slope*(y-self.apex)).square()+(y-self.y0).square()

    def sphere_field(self,y):
        return self.sphere.square()+self.y0.square()-2*self.y0*y

    def _sector(self,index):
        prefix=f'sector.{index}.'
        R,q=self.p[prefix+'RA'],self.p[prefix+'ra']
        sn,cs=_trig(self.p[prefix+'theta'])
        axis=(cs,I.of(0),sn)
        through=(sn,I.of(0),-cs)
        base={'d':I.of(0),'major':R,'minor':q,'axis':axis,'through':through,'phases':defaultdict(list)}
        self.ribbons['head.'+prefix+'A_piece']=base
        def a_event(level):
            w=(level-R.square()-q.square())/(2*R)
            return (q.square()-w.square()).sqrt()
        u_mouth=a_event(self.cone_field(self.mouth))
        u_fillet=a_event(self.r_upper.square()+(self.step-self.y0).square())
        base['phases']['fillet'].append(((-u_fillet,self.step),(u_fillet,self.step)))
        base['phases']['mouth'].append(((-u_mouth,self.mouth),(u_mouth,self.mouth)))
        for j,sign in ((0,1),(1,-1)):
            branch=prefix+f'branch.{j}.'
            d,rb=self.p[branch+'d'],self.p[branch+'rb']
            gap=rb-q
            dx=(gap.square()-d.square()).sqrt()
            rb_major=R-dx
            seam=-(q*d)/gap
            seam_radius=R+q*dx/gap
            seam_y=self.cone_y(seam.square()+seam_radius.square())
            b={'d':d,'major':rb_major,'minor':rb,'axis':axis,'through':through,
               'phases':defaultdict(list)}
            self.ribbons['head.'+branch+'B_piece']=b
            def radial_total(v_):
                s=I.of(Q(sign)*v_)
                return s.square()+(rb_major+(rb.square()-(s-d).square()).sqrt()).square()
            first=abs(_mid(seam))
            last=Q((rb+I.of(sign)*d).lo)-Q('.00000001')
            s1=sign*_decreasing_root(lambda x:radial_total(x)-self.sphere_field(self.step),first,last)
            s2=sign*_decreasing_root(lambda x:radial_total(x)-self.sphere_field(self.junction),first,last)
            tangent=((seam,self.step),(seam,seam_y))
            base['phases']['tangent'].append(tangent)
            b['phases']['tangent'].append(tangent)
            b['phases']['step'].append(((seam,self.step),(s1,self.step)))
            b['phases']['sphere'].append(((s1,self.step),(s2,self.junction)))
            b['phases']['cone'].append(((seam,seam_y),(s2,self.junction)))
            base['phases']['step'].append(((seam,self.step),(sign*u_fillet,self.step)))
            base['phases']['cone'].append(((seam,seam_y),(sign*u_mouth,self.mouth)))

    def xyz(self,chart,s,y):
        rho=chart['major']+(chart['minor'].square()-(s-chart['d']).square()).sqrt()
        t=(rho.square()-(y-self.y0).square()).sqrt()
        return _xyz(tuple(a*s+b*t if i!=1 else y for i,(a,b) in enumerate(zip(chart['axis'],chart['through']))))


def _arc_pair_bound(edge,center,radius,axis,endpoints):
    g=edge['geometry']
    if edge['geometry_class']!=10 or g['type']!='circular_evaluator' or g['is_periodic']:
        raise ValueError('edited head finite arc is not an original circular evaluator')
    a,b=map(Q,g['evaluator_limits'])
    if not 0<b-a<3:
        raise ValueError('edited head circle has the wrong finite branch')
    rr=Q(g['radius'])
    u,w=v(g['x_axis']),v(g['y_axis'])
    axis=tuple(map(_mid,axis))
    basis=abs(dot(u,u)-1)+abs(dot(w,w)-1)+abs(dot(u,w))+abs(dot(u,axis))+abs(dot(w,axis))
    support=_gap(_xyz(g['center']),_xyz(center))+2*max(abs(rr-r) for r in _bounds(radius))+8*rr*basis
    end=_pair_error([arc_endpoint(g,t) for t in (a,b)],endpoints)
    if support+end>=Q('.001'):
        raise ValueError('edited head analytic arc endpoints are outside their finite match')
    return 5*support+4*end


def _cone_or_fillet_height(points,phase,ref,chart):
    q=Q(ref.q_upper.lo)
    major=_mid(ref.r_upper)
    y0=_mid(ref.y0)
    y_f=_mid(ref.y_upper)
    k=_mid(ref.slope)
    apex=_mid(ref.apex)
    maximum=Q(0)
    for a,b in zip(points,points[1:]):
        radial=[x[0]*y[0]+x[2]*y[2] for x,y in ((a,a),(a,b),(b,b))]
        rlo=_sqrt(min(radial))[0]
        if phase=='cone':
            st=[k*(p[1]-apex) for p in (a,b)]
            if min(st)<=29 or min(a[1],b[1])<=12:
                raise ValueError('edited upper cone left its positive transverse chart')
            radial_error=max(abs(x-y) for x,y in zip(radial,_product(st,st)))/(rlo+min(st))
            # d(r-k*(Y-apex))/dY is negative with magnitude >.999
            value=(radial_error+chart)/Q('.999')
        else:
            if phase!='fillet':
                raise ValueError('unknown edited original class-11 head phase')
            dy=[a[1]-y_f,b[1]-y_f]
            mid=[r+y+major*major-q*q for r,y in zip(radial,_product(dy,dy))]
            elevated=_product(radial,(Q(1),Q(1),Q(1)))
            residual=max(abs(x-4*major*major*y) for x,y in zip(_product(mid,mid),elevated))
            radius_hi=_sqrt(max(radial))[1]
            radial_to_chart=max(abs(rlo-major),abs(radius_hi-major))+chart
            field=residual/(min(mid)+2*major*rlo)+2*radial_to_chart*chart
            ymin=min(a[1],b[1])-Q('.001')
            rmin=rlo-chart-Q('.002')
            # F_Y=2(Y-y_f)-2(r-M)(Y-y0)/r. During the continuation
            # Y is below Y0, and r remains in the positive angular chart.
            if rmin<=28:
                raise ValueError('edited upper fillet radius outside the positive chart')
            slope=2*(ymin-y_f)-2*max(Q(0),major-rmin)*(y0-ymin)/rmin
            if slope<=1:
                raise ValueError('edited fillet phase derivative not separated from zero')
            value=field/slope
            if value>=Q('.001'):
                raise ValueError('edited fillet residual outside its checked Y continuation')
        maximum=max(maximum,value)
    return maximum


def _radius_witness(ref,role,p):
    x,y,z=map(I.of,p)
    radial=(x.square()+z.square()).sqrt()
    margin=Q('.001')
    if role=='head.upper_fillet':
        # Near the center height the fillet is outside all A cutters, and
        # both end boundaries are more than a millimetre away.
        return max(map(abs,_bounds(y-ref.y_upper)))<Q('.2') and (
            radial-ref.r_upper-ref.q_upper*Q('.9')).lo>0
    if role=='head.Y_head_step':
        y=ref.step
        if not ((radial-(ref.sphere.square()-y.square()).sqrt()).lo>margin and
                (ref.r_upper-radial).lo>margin):
            return False
    elif role=='stock.s20':
        y=ref.mouth
        if not (radial.lo>42 and (ref.stock['R19']-radial).lo>margin):
            return False
    else:
        if not ((y-ref.step).lo>margin and (ref.mouth-y).lo>margin):
            return False
        sphere=(ref.sphere.square()-y.square()).sqrt()
        cone=ref.slope*(y-ref.apex)
        gap=(sphere-cone) if role=='head.R32' else (cone-sphere)
        if gap.lo<=margin:
            return False
    # Direct exact clearance against each active clipped A/B carrier.
    for name,ribbon in ref.ribbons.items():
        a,_,b=ribbon['axis']
        s=a*x+b*z
        t=b*x-a*z
        if t.hi<-margin:
            continue
        contacts=[edge[0][0] for edge in ribbon['phases']['tangent']]
        if name.endswith('.A_piece'):
            positive,negative=contacts
            if (s-positive).lo>margin or (negative-s).lo>margin:
                continue
        elif '.branch.0.' in name:
            if (contacts[0]-s).lo>margin:
                continue
        elif (s-contacts[0]).lo>margin:
            continue
        rho=(t.square()+(y-ref.y0).square()).sqrt()
        if ((rho-ribbon['major']).square()+(s-ribbon['d']).square()-ribbon['minor'].square()).lo<=Q('.05'):
            return False
    return True


def verify_edited_head(capture,carrier_record,plan,ribbons,complement):
    """Cover the 18 ribbon and twenty complementary original edited faces."""
    if (ribbons.get('status')!='complete' or not ribbons.get('disk_copy_unchanged')
            or not complement.get('disk_copy_unchanged')):
        raise ValueError('edited original head finite readback is incomplete')
    ref=EditedHead(plan)
    topology={r['detail']['face_tag']:r['detail']['topology'] for r in capture['results']}
    by_id={r['face_tag_session_only']:r for r in carrier_record['faces']}
    by_role={r['p3_support_id']:r for r in carrier_record['faces'] if r['p3_support_id'] in ref.ribbons}
    if set(by_role)!=set(ref.ribbons) or set(ribbons['faces'])!=set(ref.ribbons):
        raise ValueError('head ribbon coordinate roles differ')
    incidence=defaultdict(set)
    for tag,face in topology.items():
        for edge in face_edges(face):
            incidence[edge['tag']].add(tag)
    vertex_map={}
    verified_edges={}
    result=[]
    for name,chart in ref.ribbons.items():
        row=by_role[name]
        raw=topology[row['face_tag_session_only']]
        edges={e['tag']:e for e in face_edges(raw)}
        phases={k:list(pairs) for k,pairs in chart['phases'].items()}
        native=ribbons['faces'][name]
        a,b=native['anchors']
        if (a['containment_status']!=1 or b['containment_status']!=2
                or abs(Q(a['carrier_point_mm'][1]))>Q('.001') or b['carrier_point_mm'][1]<19):
            raise ValueError('wrong edited ribbon native material witness')
        axis=tuple(map(_mid,chart['axis']))
        through=tuple(map(_mid,chart['through']))
        approximate=tuple(_mid(chart[k]) for k in ('d','major','minor'))
        transport=Q(row['distance_upper_mm'])+Q('0.000000001')
        bounds=[]
        for entry in native['edges']:
            edge=edges[entry['edge_index']]
            phase=entry['phase']
            pts=[v(p) for p in entry['points_mm']]
            actual=[_xyz(n['child']['geometry']['point']) for n in edge['children']]
            best=None
            for candidate in phases[phase]:
                target=[ref.xyz(chart,s,y) for s,y in candidate]
                for order in (False,True):
                    trial=(candidate[::-1],target[::-1]) if order else (candidate,target)
                    gap=max(_gap(x,y) for x,y in zip(actual,trial[1]))
                    if best is None or gap<best[0]:
                        best=(gap,candidate,*trial)
            if best is None or best[0]>=Q('.0001'):
                raise ValueError('edited head phase endpoint geometry does not match: '+name+' '+phase)
            _,used,coordinates,expected=best
            phases[phase].remove(used)
            for physical,position in zip(edge['children'],expected):
                vertex=physical['child']['local_identifier']
                if vertex in vertex_map and _gap(vertex_map[vertex],position)>Q('0.0000001'):
                    raise ValueError('independent edited design edge endpoints disagree at their shared vertex')
                vertex_map[vertex]=position
            if phase=='tangent':
                s=coordinates[0][0]
                center=(chart['axis'][0]*s,ref.y0,chart['axis'][2]*s)
                rho=chart['major']+(chart['minor'].square()-(s-chart['d']).square()).sqrt()
                value=_arc_pair_bound(edge,center,rho,chart['axis'],expected)
            else:
                tau,vertex=Q(entry['chord_tolerance_mm']),Q(entry['max_vertex_deviation_mm'])
                coords=[dot(p,axis) for p in pts]
                if (Q(entry['max_midpoint_deviation_mm'])>tau
                        or not (all(a<b for a,b in zip(coords,coords[1:]))
                                or all(a>b for a,b in zip(coords,coords[1:])))):
                    raise ValueError('edited head facet graph is not completely monotone on s')
                original_span=sorted((coords[0],coords[-1]))
                target_span=sorted((_bounds(p[0]) for p in coordinates))
                shift=max(abs(a-b) for a,span in zip(original_span,target_span) for b in span)
                chart_error=_linear_poly_arc(pts,axis,through,approximate,_mid(ref.y0))+Q('0.000000001')
                if phase in ('step','mouth'):
                    station=_mid(ref.step if phase=='step' else ref.mouth)
                    height=max(abs(p[1]-station) for p in pts)
                elif phase=='sphere':
                    height=_sphere_height_residual(pts,axis,approximate,_mid(ref.y0),_mid(ref.sphere))
                else:
                    height=_cone_or_fillet_height(pts,phase,ref,chart_error)
                # For the tiny phase extension, the checked outer chart
                # preserves cos(v)>.26. With R<29 and q<=15 this bounds
                # the same-s graph speed by <68 in 3D, including the
                # sphere numerator derivative and axial chart lift.
                d,M,q=approximate
                if max(abs(s-d) for s in coords)+shift>=Q('.965')*q:
                    raise ValueError('edited finite phase extension leaves the selected angular chart')
                value=tau+vertex+chart_error+Q('1.5')*height+68*shift+transport
            if edge['tag'] in verified_edges:
                verified_edges[edge['tag']]=max(value,verified_edges[edge['tag']])
            else:
                verified_edges[edge['tag']]=value
            bounds.append(value)
        if any(phases.values()):
            raise ValueError('edited original head loop does not cover each canonical phase exactly once')
        total=Q('1.0001')*(max(bounds)+transport)+transport
        result.append({'p3_support_id':name,'native_face_in_edited_inventory':row['face_tag_session_only'],
                       'continuous_bidirectional_patch_upper_mm':upper_float(total),
                       'status':'within_limit' if total<=EDITED_DIRECTION_LIMIT_MM else 'bound_exceeds_limit'})
    return _finish_complement(ref,topology,by_id,incidence,verified_edges,vertex_map,complement,result)


def _finish_complement(ref,topology,by_id,incidence,edges,vertices,native,result):
    roles={'head.upper_fillet','head.R32','head.cone','head.Y_head_step','stock.s20'}
    requested={str(tag) for tag,r in by_id.items() if r['p3_support_id'] in roles}
    if len(requested)!=20 or set(native['faces'])!=requested:
        raise ValueError('all twenty original edited head complement regions required')
    vertical=(I.of(0),I.of(1),I.of(0))
    for tag,registration in by_id.items():
        name=registration['p3_support_id']
        if name not in roles:
            continue
        face=topology[tag]
        witness=next((r for r in native['faces'][str(tag)] if r['native_inside_trim_status']==1
                      and _radius_witness(ref,name,v(r['point_mm']))),None)
        if witness is None:
            raise ValueError('no common strict native and edited design material witness: '+name)
        bounds=[]
        for edge in face_edges(face):
            edge_id=edge['tag']
            other,=incidence[edge_id]-{tag}
            neighbor=by_id[other]['p3_support_id']
            pair={name,neighbor}
            if edge_id in edges:
                bound=edges[edge_id]
            elif pair=={'head.R32','head.cone'}:
                y=ref.junction
                radius=(ref.sphere.square()-y.square()).sqrt()
            elif pair=={'head.R32','head.Y_head_step'}:
                y=ref.step
                radius=(ref.sphere.square()-y.square()).sqrt()
            elif pair=={'head.upper_fillet','head.Y_head_step'}:
                y,radius=ref.step,ref.r_upper
            elif pair=={'head.cone','stock.s20'}:
                y,radius=ref.mouth,ref.slope*(ref.mouth-ref.apex)
            elif pair in ({'stock.s19','stock.s20'},{'head.upper_fillet','head.R40'}):
                y,radius=((ref.mouth,ref.stock['R19']) if name=='stock.s20' else (
                        ref.lower_contact,(ref.p['R40'].square()-(ref.lower_contact-ref.y0).square()).sqrt()))
                matching=[loop for loop in face['children'] if len(loop['child']['children'])==1
                          and loop['child']['children'][0]['child']['children'][0]['child']['tag']==edge_id]
                ring,=matching
                yy,rr,basis=hoop(ring,allow_rounded_center=True)
                bounds.append(max(abs(yy-a) for a in _bounds(y))+max(abs(rr-a) for a in _bounds(radius))+basis)
                continue
            else:
                raise ValueError('original edited head complement edge lacks its analytic chart: '+str(pair))
            if edge_id not in edges:
                targets=[vertices[p['child']['local_identifier']] for p in edge['children']]
                bound=_arc_pair_bound(edge,(I.of(0),y,I.of(0)),radius,vertical,targets)
            bounds.append(bound)
        carrier=Q(registration['distance_upper_mm'])+Q('0.000000001')
        boundary=max(bounds)+carrier
        if boundary>=Q('.001'):
            raise ValueError('edited head boundary is outside the checked small carrier-path regime')
        # Short circular/spherical/conical paths in the common carrier
        # have a length within 1.0001 of these small matching chord gaps.
        # Away from the paths, the paired boundary windings keep the
        # selected finite material side, fixed by the strict witness.
        total=Q('1.0001')*boundary+carrier
        result.append({'p3_support_id':name,'native_face_in_edited_inventory':tag,
                       'material_witness':witness,'continuous_bidirectional_patch_upper_mm':upper_float(total),
                       'status':'within_limit' if total<=EDITED_DIRECTION_LIMIT_MM else 'bound_exceeds_limit'})
    if len(result)!=38:
        raise ValueError('the original edited remaining head has missing finite faces')
    maximum=max(Q(r['continuous_bidirectional_patch_upper_mm']) for r in result)
    return {'schema':'p4-edited-native-finite-head-remainder/1',
            'status':'within_limit' if all(r['status']=='within_limit' for r in result) else 'bound_exceeds_limit',
            'faces':result,'face_count':len(result),'continuous_bidirectional_patch_upper_mm':upper_float(maximum),
            'scope':'38 original finite ribbon, upper fillet and head complement faces at one edited point.',
            'execution_approved':False}
