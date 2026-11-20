"""Bounded source-root intersections in finite UV tubes, offline only.

Decimal interval operations enclose recorded binary64 numbers, frame
normalization, trigonometry and every point in each parameter cell.  The
certificate does not turn an API approximation request into a distance bound.
"""
from decimal import Context, Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction
import math


class ExitCertificateError(ValueError):
    pass


_LO = Context(prec=32, rounding=ROUND_FLOOR)
_HI = Context(prec=32, rounding=ROUND_CEILING)
_ZERO = Decimal(0)


def _rounded(context, op, *args):
    with localcontext(context):
        return op(*args)


class I:
    def __init__(self, lo, hi=None):
        self.lo, self.hi = lo, lo if hi is None else hi
        if self.lo > self.hi:
            raise ExitCertificateError("invalid interval")

    @staticmethod
    def of(x):
        if isinstance(x, I): return x
        if isinstance(x, Fraction):
            n, d = Decimal(x.numerator), Decimal(x.denominator)
            return I(_rounded(_LO, lambda a,b:a/b,n,d), _rounded(_HI,lambda a,b:a/b,n,d))
        if isinstance(x, float):
            if not math.isfinite(x): raise ExitCertificateError("nonfinite input")
            return I(Decimal.from_float(x))
        return I(Decimal(x))

    def __add__(a,b):
        b=I.of(b); return I(_rounded(_LO,lambda x,y:x+y,a.lo,b.lo),_rounded(_HI,lambda x,y:x+y,a.hi,b.hi))
    __radd__=__add__
    def __neg__(a): return I(a.hi.copy_negate(),a.lo.copy_negate())
    def __sub__(a,b): return a+-I.of(b)
    def __rsub__(a,b): return I.of(b)+-a
    def __mul__(a,b):
        b=I.of(b); pairs=[(x,y) for x in (a.lo,a.hi) for y in (b.lo,b.hi)]
        return I(min(_rounded(_LO,lambda x,y:x*y,*p) for p in pairs),max(_rounded(_HI,lambda x,y:x*y,*p) for p in pairs))
    __rmul__=__mul__
    def __truediv__(a,b):
        b=I.of(b)
        if b.lo <= 0 <= b.hi: raise ExitCertificateError("division through zero")
        pairs=[(x,y) for x in (a.lo,a.hi) for y in (b.lo,b.hi)]
        return I(min(_rounded(_LO,lambda x,y:x/y,*p) for p in pairs),max(_rounded(_HI,lambda x,y:x/y,*p) for p in pairs))
    def square(a):
        if a.lo <= 0 <= a.hi: return I(_ZERO,max((I.of(a.lo)*a.lo).hi,(I.of(a.hi)*a.hi).hi))
        return a*a
    def sqrt(a):
        if a.lo < 0: raise ExitCertificateError("negative square root")
        # Decimal.sqrt is correctly rounded to nearest; adjacent representable
        # decimals strictly enclose it, including under directed contexts.
        with localcontext(_LO): lo=a.lo.sqrt().next_minus()
        with localcontext(_HI): hi=a.hi.sqrt().next_plus()
        return I(lo,hi)


def _trig(x):
    """Midpoint Taylor plus the global one-Lipschitz trig bounds."""
    if x.lo < -5 or x.hi > 5: raise ExitCertificateError("trigonometric domain")
    center=I.of((Fraction(x.lo)+Fraction(x.hi))/2)
    spread=max((x-center).hi,(center-x).hi)
    xx=center.square(); sin=center; cos=I.of(1); st=center; ct=I.of(1)
    for k in range(1,22):
        st=-(st*xx)/((2*k)*(2*k+1)); sin=sin+st
        ct=-(ct*xx)/((2*k-1)*(2*k)); cos=cos+ct
    # Conservative bound covers both first omitted terms on this domain.
    eps=I.of(spread)+I.of(Decimal('0.000000000000001'))
    eps=I(eps.hi.copy_negate(),eps.hi)
    return sin+eps,cos+eps


def _dot(a,b): return sum((x*y for x,y in zip(a,b)),I.of(0))
def _norm(a):
    length=sum((x.square() for x in a),I.of(0)).sqrt()
    return [x/length for x in a]
def _cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def _frame(g):
    axis=_norm([I.of(x) for x in g['axis']]); raw=_norm([I.of(x) for x in g['u0_ref_direction']])
    dot=_dot(axis,raw); ref=_norm([raw[i]-dot*axis[i] for i in range(3)])
    return axis,ref,_norm(_cross(axis,ref))


def _evaluate(g, stock, frame, u, v):
    su,cu=_trig(u); sv,cv=_trig(v); axis,ref,tangent=frame
    radius=I.of(g['major_radius'])+I.of(g['minor_radius'])*cv
    radial=[cu*ref[i]+su*tangent[i] for i in range(3)]
    dradial=[-su*ref[i]+cu*tangent[i] for i in range(3)]
    p=[I.of(g['center'][i])+radius*radial[i]+I.of(g['minor_radius'])*sv*axis[i] for i in range(3)]
    du=[radius*x for x in dradial]
    dv=[-I.of(g['minor_radius'])*sv*radial[i]+I.of(g['minor_radius'])*cv*axis[i] for i in range(3)]
    x,y,z=p; dx,dy,dz=du; q=y-I.of(stock['center'][1]); R=I.of(stock['major_radius']); r=I.of(stock['minor_radius'])
    rho2=x.square()+z.square(); A=rho2+q.square()+R.square()-r.square()
    f=A.square()-4*R.square()*rho2
    rho2u=2*(x*dx+z*dz); derivative=2*A*(rho2u+2*q*dy)-4*R.square()*rho2u
    rho2v=2*(x*dv[0]+z*dv[2]); derivative_v=2*A*(rho2v+2*q*dv[1])-4*R.square()*rho2v
    return f,derivative,derivative_v,rho2,q


def _bezier_box(points, a, b):
    # Restrict a quadratic Bezier exactly, then use its convex hull.
    def lerp(x,y,t): return x+(y-x)*t
    out=[]
    for j in range(2):
        p0,p1,p2=[p[j] for p in points]
        at=lambda t: lerp(lerp(p0,p1,t),lerp(p1,p2,t),t)
        q0,q2=at(a),at(b)
        q1=q0+(b-a)*(lerp(p1-p0,p2-p1,a))
        out.append(I(I.of(min(q0,q1,q2)).lo,I.of(max(q0,q1,q2)).hi))
    return out


def _graph_window(g,stock,frame,fins,width,subdivisions=32):
    """Prove u-monotonicity on a rectangle containing the joined loop."""
    ulo,uhi=Fraction(16,5),Fraction(41,10)
    vlo,vhi=Fraction(-77,100),Fraction(77,100)
    for fin in fins:
        for span in fin['derived_joined_bezier_controls_exact']:
            for point in span:
                u,v=[Fraction(*pair) for pair in point]
                if not (ulo < u-Fraction(width.hi) and u+Fraction(width.hi) < uhi and vlo < v < vhi):
                    raise ExitCertificateError('FIN control outside graph window')
    worst=None
    for i in range(subdivisions):
        ua=ulo+(uhi-ulo)*Fraction(i,subdivisions); ub=ulo+(uhi-ulo)*Fraction(i+1,subdivisions)
        for j in range(subdivisions):
            va=vlo+(vhi-vlo)*Fraction(j,subdivisions); vb=vlo+(vhi-vlo)*Fraction(j+1,subdivisions)
            u=I(I.of(ua).lo,I.of(ub).hi); v=I(I.of(va).lo,I.of(vb).hi)
            _,derivative,_,_,_=_evaluate(g,stock,frame,u,v)
            if derivative.hi>=0: raise ExitCertificateError('graph window uniqueness proof failed')
            worst=derivative.hi if worst is None else max(worst,derivative.hi)
    return {'u_rad':['3.2','4.1'],'v_rad':['-0.77','0.77'],
            'cells':[subdivisions,subdivisions], 'dF_du_upper_mm4_per_rad':str(worst),
            'result':'at_most_one_stock_intersection_per_v_in_window',
            'scope':'covers joined FIN control hull and termination tubes; no conclusion outside window or on stock trim membership'}


def _certify(source, *, cells=512, tube_rad='0.0002'):
    """Certify a bounded graph tube given the already validated F0123 C2 result.

    This function consumes a fresh result from torus_trim_certificate, not an
    untrusted certificate file. Parent identities and graph validity are owned
    by that caller; callers must not use manually asserted dictionaries.
    """
    if type(cells) is not int or not 1 <= cells <= 4096: raise ExitCertificateError('invalid cell count')
    width=I.of(Decimal(tube_rad))
    if width.lo <= 0 or width.hi > Decimal('0.01'): raise ExitCertificateError('invalid tube')
    if (source['target']['kind']!='current_prt' or source['target']['unit']!='mm'
        or source['source_trim']['returned_FIN_graph']['status']!='validated_derived_returned_FIN_graph'):
        raise ExitCertificateError('unsupported source')
    data=source['source_definition']; g=data['root_geometry']; parents=data['implicit_other_parents']
    if set(parents)!={'F0126','F0169'} or parents['F0126']['geometry']!=parents['F0169']['geometry']:
        raise ExitCertificateError('stock carriers differ')
    stock=parents['F0126']['geometry']
    if (stock['type']!=204 or stock['axis']!=[0,1,0] or stock['center'][0]!=0 or stock['center'][2]!=0
        or stock['u0_ref_direction']!=[0,0,1] or not stock['major_radius']>stock['minor_radius']>0):
        raise ExitCertificateError('unsupported stock torus frame')
    fins=[f for f in data['source_FINs'] if f['geometry_class']==11]
    if len(fins)!=2 or {f['other_parent_same_snapshot']['p1_semantic_label'] for f in fins}!={'F0126','F0169'}:
        raise ExitCertificateError('unsupported termination partition')
    if fins[0]['end_vertex']!=fins[1]['start_vertex']:
        raise ExitCertificateError('seam chain is not shared')
    if fins[0]['derived_joined_bezier_controls_exact'][-1][-1] != fins[1]['derived_joined_bezier_controls_exact'][0][0]:
        raise ExitCertificateError('seam UV join differs')
    frame=_frame(g); results=[]
    graph_window=_graph_window(g,stock,frame,data['source_FINs'],width)
    # At fixed v, ||dS/du|| <= R+r. This is a correspondence to the
    # returned FIN expression, not a bound to the original finite edge.
    spatial_bound=((I.of(g['major_radius'])+I.of(g['minor_radius']))*width).hi
    for fin in fins:
        spans=fin['derived_joined_bezier_controls_exact']
        if len(spans)!=1 or len(spans[0])!=3: raise ExitCertificateError('unsupported FIN basis')
        points=[[Fraction(*pair) for pair in p] for p in spans[0]]
        diffs=[points[i+1][1]-points[i][1] for i in range(2)]
        if not all(d<0 for d in diffs): raise ExitCertificateError('FIN v is not strictly decreasing')
        worst_left=None; worst_right=None; worst_derivative=None
        for i in range(cells):
            a,b=Fraction(i,cells),Fraction(i+1,cells)
            u,v=_bezier_box(points,a,b)
            box=I((u-width).lo,(u+width).hi)
            _,derivative,derivative_v,rho2,q=_evaluate(g,stock,frame,box,v)
            # F on either shifted FIN is enclosed by its midpoint value plus
            # the full-cell interval derivative times the signed displacement.
            midpoint=(a+b)/2
            um,vm=_bezier_box(points,midpoint,midpoint)
            left_mid,*_=_evaluate(g,stock,frame,um-width,vm)
            right_mid,*_=_evaluate(g,stock,frame,um+width,vm)
            slopes=[]
            for j in range(2):
                s0=2*((1-a)*(points[1][j]-points[0][j])+a*(points[2][j]-points[1][j]))
                s1=2*((1-b)*(points[1][j]-points[0][j])+b*(points[2][j]-points[1][j]))
                slopes.append(I(I.of(min(s0,s1)).lo,I.of(max(s0,s1)).hi))
            dFdt=derivative*slopes[0]+derivative_v*slopes[1]
            half=I.of((b-a)/2).hi
            displacement=I(half.copy_negate(),half)
            left=left_mid+displacement*dFdt
            right=right_mid+displacement*dFdt
            if left.lo<=0 or right.hi>=0 or derivative.hi>=0:
                raise ExitCertificateError('tube sign or uniqueness proof failed at cell %d'%i)
            # Inner radial branch and upper meridian branch, no squared-equation extraneous branch.
            if rho2.lo<=0 or rho2.hi >= I.of(stock['major_radius']).square().lo or q.lo<0:
                raise ExitCertificateError('stock branch guard failed at cell %d'%i)
            worst_left=left.lo if worst_left is None else min(worst_left,left.lo)
            worst_right=right.hi if worst_right is None else max(worst_right,right.hi)
            worst_derivative=derivative.hi if worst_derivative is None else max(worst_derivative,derivative.hi)
        results.append({'parent':fin['other_parent_same_snapshot']['p1_semantic_label'],
                        'position':fin['position'],'start_vertex':fin['start_vertex'],'end_vertex':fin['end_vertex'],
                        'u_tube_radius_rad':str(width.hi),'cells':cells,'left_F_lower_mm4':str(worst_left),
                        'right_F_upper_mm4':str(worst_right),'dF_du_upper_mm4_per_rad':str(worst_derivative),
                        'same_v_FIN_to_implicit_world_distance_upper_mm':str(spatial_bound),
                        'v_direction':'strictly_decreasing','result':'validated_unique_continuous_implicit_branch_in_tube'})
    return {'schema':'p3-f0123-root-exit-tube/0.1','source':source['target'], 'edges':results,'graph_window':graph_window,
            'status':'validated_tube_graph_API_source_association_conditional',
            'frame':'absolute part coordinates in mm; root UV in radians; normalized axis, projected normalized u0 reference, right-handed tangent',
            'parameter_scope':'each complete joined quadratic FIN t in [0,1], with strictly decreasing v; two independent edges share the joined UV endpoint',
            'closure':'same-tree directed five-FIN graph and joined UV endpoint inherited from the fresh source verifier; implicit endpoint-to-native-vertex association is conditional',
            'arithmetic':'32-digit directed decimal intervals, exact binary64 inputs and Taylor remainder enclosure',
            'api_curve_tolerance_mm':data['options']['curve_tolerance'],
            'error_budget':'tube world-distance bound concerns analytic composition of returned FIN versus selected implicit branch; API conversion request is a separate contract dependency and is not added as a proven Hausdorff bound',
            'conditions':['source FIN and implicit topology association relies on recorded API contract',
                          'tube does not exclude other branches outside it or establish native face domains',
                          'candidate S0, source stock patch domains, material side and total error budget remain conditional',
                          'the tube distance bound is not a complete 0.001 mm region error budget or P3 acceptance'],
            'execution_approved':False}


def build_certificate(repository_root, *, queue, cells=512, tube_rad='0.0002'):
    """Revalidate the saved source, then prove its two finite tube graphs."""
    from .torus_trim_certificate import build_certificate as source_certificate
    source=source_certificate(repository_root,'F0123',queue=queue)
    return _certify(source,cells=cells,tube_rad=tube_rad)


def _exact_num(value):
    if type(value) not in (float,int) or not math.isfinite(value):
        raise ExitCertificateError('nonfinite or nonnumeric source domain')
    return Fraction.from_float(value) if type(value) is float else Fraction(value)


def _exact_pair(value):
    return [value.numerator,value.denominator]


def _prepare_multispan(source):
    """Validate complete source intervals against traversal-oriented spans."""
    if (source.get('target',{}).get('kind')!='current_prt'
        or source['target'].get('unit')!='mm'
        or source.get('source_trim',{}).get('returned_FIN_graph',{}).get('status')!='validated_derived_returned_FIN_graph'):
        raise ExitCertificateError('unsupported source')
    data=source['source_definition']; all_fins=data['source_FINs']
    fins=[f for f in all_fins if f['geometry_class']==11]
    if len(all_fins)!=4 or len(fins)!=1 or sum(f['geometry_class']==10 for f in all_fins)!=3:
        raise ExitCertificateError('requires four FINs and one class11 edge')
    fin=fins[0]; parents=data['implicit_other_parents']
    label=fin['other_parent_same_snapshot']['p1_semantic_label']
    if set(parents)!={label} or label not in ('F0126','F0169'):
        raise ExitCertificateError('unsupported or ambiguous source stock parent')
    stock=parents[label]['geometry']
    if (stock['type']!=204 or stock['axis']!=[0,1,0] or stock['center'][0]!=0 or stock['center'][2]!=0
        or stock['u0_ref_direction']!=[0,0,1] or not stock['major_radius']>stock['minor_radius']>0):
        raise ExitCertificateError('unsupported stock torus frame')
    direction=fin['traversal_is_forward']
    if type(direction) is not bool: raise ExitCertificateError('missing traversal direction')
    if fin.get('fin_geometry_sense') != (1 if direction else -1):
        raise ExitCertificateError('FIN direction conflicts with source sense')
    domain=fin['source_interval']; raw=fin['nonzero_spans']; controls=fin['derived_joined_bezier_controls_exact']
    if not isinstance(domain,list) or len(domain)!=2 or not isinstance(raw,list) or not raw or len(raw)!=len(controls):
        raise ExitCertificateError('source span count or domain mismatch')
    try:
        domain=[_exact_num(x) for x in domain]
        intervals=[[_exact_num(x) for x in pair] for pair in raw]
        if any(len(pair)!=2 for pair in intervals): raise ExitCertificateError('invalid source span')
        if (domain[0]>=domain[1] or intervals[0][0]!=domain[0] or intervals[-1][1]!=domain[1]
            or any(a>=b for a,b in intervals) or any(intervals[i][1]!=intervals[i+1][0] for i in range(len(intervals)-1))):
            raise ExitCertificateError('source spans do not cover complete domain')
        points=[[[Fraction(*pair) for pair in point] for point in span] for span in controls]
    except (TypeError,ValueError,ZeroDivisionError,IndexError) as exc:
        raise ExitCertificateError('invalid source span data') from exc
    if any(len(span)!=3 or any(len(point)!=2 for point in span) for span in points):
        raise ExitCertificateError('only nonrational quadratic spans are supported')
    if any(a[-1]!=b[0] for a,b in zip(points,points[1:])):
        raise ExitCertificateError('internal FIN span join differs')
    deltas=[span[i+1][1]-span[i][1] for span in points for i in (0,1)]
    if all(d<=0 for d in deltas) and all(span[-1][1]<span[0][1] for span in points): sign=-1
    elif all(d>=0 for d in deltas) and all(span[-1][1]>span[0][1] for span in points): sign=1
    else: raise ExitCertificateError('FIN v is not strictly monotonic across all spans')
    traversal_intervals=intervals if direction else [[b,a] for a,b in reversed(intervals)]
    return data,fin,label,stock,domain,points,traversal_intervals,sign


def _prove_multispan(source, *, cells=128, tube_rad='0.0002'):
    """Prove each nonzero quadratic span and the entire source graph window."""
    if type(cells) is not int or not 1<=cells<=4096: raise ExitCertificateError('invalid cell count')
    width=I.of(Decimal(tube_rad))
    if width.lo<=0 or width.hi>Decimal('0.01'): raise ExitCertificateError('invalid tube')
    data,fin,label,stock,domain,spans,intervals,sign=_prepare_multispan(source)
    g=data['root_geometry']; frame=_frame(g)
    graph_window=_graph_window(g,stock,frame,data['source_FINs'],width)
    bound=((I.of(g['major_radius'])+I.of(g['minor_radius']))*width).hi
    out=[]
    for span_index,(points,source_interval) in enumerate(zip(spans,intervals)):
        worst_left=worst_right=worst_derivative=None
        for i in range(cells):
            a,b=Fraction(i,cells),Fraction(i+1,cells)
            u,v=_bezier_box(points,a,b); box=I((u-width).lo,(u+width).hi)
            _,du,dv,rho2,q=_evaluate(g,stock,frame,box,v)
            midpoint=(a+b)/2; um,vm=_bezier_box(points,midpoint,midpoint)
            left_mid,*_=_evaluate(g,stock,frame,um-width,vm)
            right_mid,*_=_evaluate(g,stock,frame,um+width,vm)
            slopes=[]
            for j in range(2):
                def slope(t): return 2*((1-t)*(points[1][j]-points[0][j])+t*(points[2][j]-points[1][j]))
                s0,s1=slope(a),slope(b)
                slopes.append(I(I.of(min(s0,s1)).lo,I.of(max(s0,s1)).hi))
            dFdt=du*slopes[0]+dv*slopes[1]; half=I.of((b-a)/2).hi
            delta=I(half.copy_negate(),half)*dFdt
            left,right=left_mid+delta,right_mid+delta
            if left.lo<=0 or right.hi>=0 or du.hi>=0:
                raise ExitCertificateError('tube sign or uniqueness proof failed at span %d cell %d'%(span_index,i))
            if rho2.lo<=0 or rho2.hi>=I.of(stock['major_radius']).square().lo or q.lo<0:
                raise ExitCertificateError('stock branch guard failed at span %d cell %d'%(span_index,i))
            worst_left=left.lo if worst_left is None else min(worst_left,left.lo)
            worst_right=right.hi if worst_right is None else max(worst_right,right.hi)
            worst_derivative=du.hi if worst_derivative is None else max(worst_derivative,du.hi)
        out.append({'traversal_index':span_index,'source_interval_directed_exact':[_exact_pair(v) for v in source_interval],
                    'local_parameter':[0,1],'cells':cells,'left_F_lower_mm4':str(worst_left),
                    'right_F_upper_mm4':str(worst_right),'dF_du_upper_mm4_per_rad':str(worst_derivative),
                    'same_v_joined_FIN_to_implicit_world_distance_upper_mm':str(bound)})
    return {'schema':'p3-four-fin-multispan-exit/0.1','target':source['target'],
            'status':'validated_tube_graph_API_source_association_conditional','graph_window':graph_window,
            'source_graph':{'status':source['source_trim']['returned_FIN_graph']['status'],
                            'graph_evidence':source['source_trim']['returned_FIN_graph'],
                            'source_definition_status':data['status'],
                            'all_fins':data['source_FINs'],'root_geometry':g,
                            'root_geometry_sense':data['geometry_sense'],
                            'implicit_other_parents':data['implicit_other_parents'],
                            'options':data['options'],'mapping':data['mapping'],
                            'root_topology_state_count':data['root_topology_state_count'],
                            'reader_geometry_details_complete':data['reader_geometry_details_complete'],
                            'uv_join_max_linf_rad':source['source_trim']['returned_FIN_graph']['uv_join_max_linf_rad'],
                            'scope':'joined FIN graph; source identities remain same-tree and parent labels are semantic'},
            'termination':{'parent':label,'fin_position':fin['position'],
                           'start_vertex':fin['start_vertex'],'end_vertex':fin['end_vertex'],
                           'source_interval_exact':[_exact_pair(v) for v in domain],
                           'source_parameter_increases_with_traversal':fin['traversal_is_forward'],
                           'v_direction':'increasing' if sign==1 else 'decreasing',
                           'u_tube_radius_rad':str(width.hi),'spans':out},
            'frame':'recorded mm and absolute part coordinates; root normalized axis and projected normalized reference, right-handed tangent',
            'arithmetic':'binary64 inputs, exact rational knot and Bezier restriction, directed decimal intervals and Taylor enclosure',
            'api_curve_tolerance_mm':data['options']['curve_tolerance'],
            'conditions':['FIN/source association relies on the recorded API contract; no same-parameter API error inferred',
                          'full source parent trim domains, endpoints, material side and candidate S0 mapping remain conditional',
                          'window excludes extra intersection branches only within its stated rectangle',
                          'tube bound is not the complete 0.001 mm region error budget'],
            'execution_approved':False}


def build_multispan_certificate(repository_root, target_label, *, queue, cells=128, tube_rad='0.0002'):
    """Revalidate one saved four-FIN root and prove its complete class11 span chain."""
    from .torus_trim_certificate import build_certificate as source_certificate
    source=source_certificate(repository_root,target_label,queue=queue)
    return _prove_multispan(source,cells=cells,tube_rad=tube_rad)


def build_double_fin_certificate(repository_root, target_label, *, queue, cells=512, tube_rad='0.0002'):
    """Apply the reviewed two-edge proof to the explicitly supported F0229."""
    if target_label!='F0229':
        raise ExitCertificateError('double-FIN extension supports only F0229')
    from .torus_trim_certificate import build_certificate as source_certificate
    source=source_certificate(repository_root,target_label,queue=queue)
    data=source['source_definition']; fins=[f for f in data['source_FINs'] if f['geometry_class']==11]
    if len(data['source_FINs'])!=5 or len(fins)!=2:
        raise ExitCertificateError('requires five FINs and two class11 edges')
    directed_domains=[]
    for fin in fins:
        original=fin['source_interval']; spans=fin['nonzero_spans']; forward=fin['traversal_is_forward']
        if (type(forward) is not bool or fin['fin_geometry_sense']!=(1 if forward else -1)
            or not isinstance(original,list) or len(original)!=2 or len(spans)!=1 or len(spans[0])!=2):
            raise ExitCertificateError('unsupported double-FIN interval or direction')
        lo,hi=map(_exact_num,original); sa,sb=map(_exact_num,spans[0])
        if lo>=hi or (sa,sb)!=(lo,hi): raise ExitCertificateError('double-FIN domain not covered')
        directed_domains.append([_exact_pair(v) for v in ((lo,hi) if forward else (hi,lo))])
    result=_certify(source,cells=cells,tube_rad=tube_rad)
    result['schema']='p3-double-fin-root-exit-tube/0.2'
    result['source_graph']={'graph_evidence':source['source_trim']['returned_FIN_graph'],
                            'source_definition_status':data['status'],'all_fins':data['source_FINs'],
                            'root_geometry':data['root_geometry'],'root_geometry_sense':data['geometry_sense'],
                            'implicit_other_parents':data['implicit_other_parents'],
                            'options':data['options'],'mapping':data['mapping'],
                            'root_topology_state_count':data['root_topology_state_count'],
                            'reader_geometry_details_complete':data['reader_geometry_details_complete']}
    for edge,fin,domain in zip(result['edges'],fins,directed_domains):
        edge['source_interval_directed_exact']=domain
        edge['source_parameter_increases_with_traversal']=fin['traversal_is_forward']
        edge['source_parent_detail']=data['implicit_other_parents'][edge['parent']]
    return result
