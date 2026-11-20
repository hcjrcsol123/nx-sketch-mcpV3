"""Offline P3 flank expression graph with bounded numerical previews.

This produces a planning expression, never a native or executable plan.
Source local coordinates are accepted binary64 observations; the preview does
not independently bound their transformation from the original 3-D source.
"""
from decimal import Decimal
from fractions import Fraction as F
import json
import math
from pathlib import Path

from .root_exit_certificate import I, _trig
from .spline_restrict import restrict_bspline


class FlankParameterError(ValueError):
    pass


PATHS={
    'decision':'docs/v3/decisions/p3-independent-flank-connection-angles-user-decision.json',
    'templates':'docs/v3/decisions/p3-shared-flank-templates-user-decision.json',
    'bindings':'workspace/v3/p3/P3-DECISIONS-02/decision-bindings-c2.json',
    'observations':'workspace/v3/p3/P3-SWEPT-ANALYSIS-01/mechanical-observations.json',
    'weights':'workspace/v3/p3/P3-FLANK-DRIVERS-01/calculation.json',
    'stock':'workspace/v3/p3/P3-STOCK-01/meridian-plan-c2.json',
    'frame_contract':'workspace/v3/p3/P3-SOURCE-FRAME-01/frame-contract-c2.json',
}
LABELS=('F0002','F0024')
FREE=(2,3,4)
FIXED=(0,6)


def _read(root,relative):
    try:
        if not isinstance(relative,str) or not relative.strip(): raise FlankParameterError('invalid input path')
        path=(root/relative).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file(): raise FlankParameterError('input outside project')
        def unique(pairs):
            out={}
            for k,v in pairs:
                if k in out: raise FlankParameterError('duplicate JSON key')
                out[k]=v
            return out
        with path.open(encoding='utf-8') as stream:
            return json.load(stream,object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(FlankParameterError('nonfinite JSON')))
    except (OSError,ValueError) as exc:
        raise FlankParameterError('cannot read required input: '+relative) from exc


def _f(value):
    if type(value) not in (float,int) or not math.isfinite(value): raise FlankParameterError('expected finite numeric input')
    return F.from_float(value) if type(value) is float else F(value)


def _frac(pair):
    if not isinstance(pair,list) or len(pair)!=2 or any(type(x) is not int for x in pair) or pair[1]<=0:
        raise FlankParameterError('invalid exact rational')
    return F(*pair)


def _pair(x): return [x.numerator,x.denominator]
def _abs_upper(x): return max(abs(F(x.lo)),abs(F(x.hi)))
def _mid(x): return (F(x.lo)+F(x.hi))/2


def _preview(x):
    value=float(_mid(x))
    if not math.isfinite(value): raise FlankParameterError('nonfinite numeric preview')
    exact=F.from_float(value)
    error=max(abs(exact-F(x.lo)),abs(exact-F(x.hi)))
    return {'value':value,'lower':str(x.lo),'upper':str(x.hi),
            'binary64_absolute_error_upper':str(I.of(error).hi)}


def _atan_series(x):
    """atan enclosure for |x|<=1/2 via alternating series and remainder."""
    if x.lo<Decimal('-.5') or x.hi>Decimal('.5'): raise FlankParameterError('atan series domain')
    xx=x.square(); term=x; out=I.of(0)
    for n in range(40):
        out=out+(term/(2*n+1) if n%2==0 else -(term/(2*n+1)))
        term=term*xx
    # 0.5**81/81 < 1e-26; widen for both signs.
    return out+I(Decimal('-1e-25'),Decimal('1e-25'))


def _pi():
    return 16*_atan_series(I.of(F(1,5)))-4*_atan_series(I.of(F(1,239)))


def _atan_positive_ratio(x):
    if x.lo<0 or x.hi>1: raise FlankParameterError('atan ratio outside supported domain')
    if x.hi<=Decimal('.5'): return _atan_series(x)
    if x.lo>Decimal('.5'): return _pi()/4+_atan_series((x-1)/(x+1))
    raise FlankParameterError('atan branch ambiguity')


def _atan2_tr(t,r):
    """atan2(t,r), with exact-rational inputs enclosed by intervals."""
    ti,ri=I.of(t),I.of(r)
    if ti.lo<=0<=ti.hi or ri.lo<=0<=ri.hi: raise FlankParameterError('ambiguous default endpoint direction')
    tx=ti if ti.lo>0 else -ti; ry=ri if ri.lo>0 else -ri
    if tx.hi<=ry.lo: small=_atan_positive_ratio(tx/ry)
    elif ry.hi<tx.lo: small=_pi()/2-_atan_positive_ratio(ry/tx)
    else: raise FlankParameterError('ambiguous atan ratio branch')
    angle=small if ri.lo>0 else _pi()-small
    return angle if ti.lo>0 else -angle


def _assert_positive(x,message):
    if x.lo<=0: raise FlankParameterError(message)


def _load_inputs(root):
    data={key:_read(root,path) for key,path in PATHS.items()}
    decision=data['decision']; shared=data['templates']; binding=data['bindings']; obs=data['observations']; calc=data['weights']; stock=data['stock']; contract=data['frame_contract']
    expected=[{'template_label':s,'endpoint_role':role,'unit':'rad'} for s in LABELS for role in ('root','outer')]
    scope=decision.get('scope',{})
    if (decision.get('decision_id')!='P3-USER-INDEPENDENT-FLANK-CONNECTION-ANGLES-01'
        or decision.get('selected_option')!='4个连接角独立可编辑' or scope.get('independent_connection_angles')!=expected
        or scope.get('same_side_shared_across_22_members') is not True or scope.get('templates_remain_independent') is not True
        or scope.get('preserve_original_template_order_and_knots') is not True):
        raise FlankParameterError('angle decision missing or differs')
    if (decision.get('source_binding',{}).get('accepted_existing_binding')!=PATHS['bindings']
        or decision.get('source_binding',{}).get('source_calculation')!=PATHS['weights']
        or decision.get('source_binding',{}).get('prior_template_decision')!=PATHS['templates']):
        raise FlankParameterError('angle decision source bindings differ')
    sscope=shared.get('scope',{})
    if (shared.get('decision_id')!='P3-USER-SHARED-FLANK-TEMPLATES-01' or sscope.get('fixed_count')!=22
        or sscope.get('same_side_shared_across_members') is not True or sscope.get('two_independent_original_generators') is not True):
        raise FlankParameterError('shared template decision missing or differs')
    if binding.get('schema')!='p3-decision-bindings/1.0' or binding.get('execution_approved') is not False:
        raise FlankParameterError('unsupported C2 binding')
    flanks=binding['flanks']
    if (flanks.get('fixed_count')!=22 or flanks.get('same_side_shared') is not True
        or flanks.get('opposite_sides_independent') is not True or flanks.get('anchor_member_index')!=10
        or len(flanks.get('members',[]))!=22 or [x.get('member_index') for x in flanks['members']]!=list(range(22))):
        raise FlankParameterError('invalid shared placement mapping')
    frame=flanks.get('frame',{})
    if (frame.get('axis_direction')!=[0.0,1.0,0.0] or frame.get('plane_basis_u')!=[0.0,0.0,1.0]
        or frame.get('plane_basis_v')!=[1.0,0.0,0.0] or not isinstance(frame.get('axis_point'),list)
        or len(frame['axis_point'])!=3):
        raise FlankParameterError('unsupported placement frame')
    for x in frame['axis_point']: _f(x)
    if obs.get('coordinate_units')!='mm, rad' or stock.get('unit')!='mm' or stock.get('frame')!='Y_r_positive':
        raise FlankParameterError('unit or frame differs')
    if (contract.get('schema')!='p3-common-source-frame-contract/1'
        or contract.get('comparison')!='direct full bytes, no digest'
        or contract.get('current_reference_matches_common_before') is not True):
        raise FlankParameterError('common source frame contract missing')
    members=[x for x in obs['members'] if x.get('member')=='F0064']
    if len(members)!=1 or calc.get('reference_member')!='F0064': raise FlankParameterError('anchor source missing')
    sides={x['label']:x for x in members[0]['sides']}; weights={x['label']:x for x in calc['templates']}
    if set(sides)!=set(LABELS) or set(weights)!=set(LABELS) or set(flanks['templates'])!=set(LABELS):
        raise FlankParameterError('two original source templates required')
    vertices={x['id']:x for x in stock['vertices']}
    if _f(vertices['v6']['r'])!=_f(vertices['v7']['r']): raise FlankParameterError('stock shaft radius not constant')
    for label in LABELS:
        side=sides[label]; gen=side['generator']; native=flanks['templates'][label]['original_generator']; w=weights[label]
        if (gen['order']!=4 or native['order']!=4 or native['num_poles']!=7 or native['rational'] is not False
            or gen['domain']!=[0,1] or native['start']!=0 or native['end']!=1
            or len(gen['local_poles'])!=7 or gen['knots']!=native['knots']
            or [_pair(_f(x)) for x in gen['knots']]!=w['knots_binary64_exact']
            or [_pair(_f(x[0])) for x in side['section_edge_y_minus_71']['fin_uv_poles']]!=w['interval_binary64_exact']
            or side['snapshot_id']!=flanks['templates'][label]['snapshot_id']
            or side['source_path']!=flanks['templates'][label]['source']):
            raise FlankParameterError('original source basis or binding differs: '+label)
        snapshot=_read(root,side['source_path'])
        if (snapshot.get('snapshot_id')!=side['snapshot_id'] or snapshot.get('inventory',{}).get('units')!='Millimeters'
            or snapshot.get('inventory',{}).get('coordinate_system')!='absolute_part_coordinates'):
            raise FlankParameterError('original source snapshot, unit or frame differs: '+label)
        match=[x for x in contract.get('sources',[]) if x.get('snapshot_id')==side['snapshot_id']
               and x.get('snapshot_path','').replace('\\','/')==side['source_path']]
        if (len(match)!=1 or match[0].get('byte_equal_common_saved_part') is not True
            or match[0].get('part_path_matches_accepted_copy') is not True
            or match[0].get('units')!='Millimeters' or match[0].get('coordinate_system')!='absolute_part_coordinates'):
            raise FlankParameterError('template missing from common source frame contract: '+label)
        for pole in gen['local_poles']:
            if not isinstance(pole,list) or len(pole)!=3 or _f(pole[2])!=F(-124): raise FlankParameterError('unsupported generator frame')
    return data,members[0],sides,weights,_f(vertices['v6']['r'])


def _values(defaults, overrides):
    if overrides is None: overrides={}
    if not isinstance(overrides,dict): raise FlankParameterError('overrides must be a mapping')
    unknown=set(overrides)-set(defaults)
    if unknown: raise FlankParameterError('unknown or noneditable parameter: '+','.join(sorted(unknown)))
    result=dict(defaults)
    for key,value in overrides.items(): result[key]=_f(value)
    return result


def _basis_and_effective_witness(side,A,B,det):
    """Bind endpoints and prove three effective shape responses independent."""
    knots=side['generator']['knots']
    a,b=[x[0] for x in side['section_edge_y_minus_71']['fin_uv_poles']]
    dummy=[[0.0] for _ in range(7)]
    def rows(end):
        try:
            result=restrict_bspline(order=4,knots=knots,poles=dummy,a=a,b=end,rational=False)
            return [[_frac(x) for x in row] for row in result['dependency_rows_exact']]
        except ValueError as exc:
            raise FlankParameterError('source basis restriction failed') from exc
    bound_rows=rows(b)
    if bound_rows[0]!=A or bound_rows[-1]!=B or any(x<0 for row in (A,B) for x in row):
        raise FlankParameterError('endpoint weights do not match original basis and FIN')
    points=[F(1,4),F(1,2),F(3,4)]
    if not all(_f(a)<u<_f(b) for u in points): raise FlankParameterError('interior witnesses outside source FIN')
    witnesses=[]
    for u in points:
        N=rows(float(u))[-1]
        if len(N)!=7 or any(x<0 for x in N) or sum(N)!=1:
            raise FlankParameterError('invalid restricted basis witness')
        response=[]
        for k in FREE:
            c1=(B[5]*A[k]-A[5]*B[k])/det
            c5=(A[1]*B[k]-B[1]*A[k])/det
            response.append(N[k]-N[1]*c1-N[5]*c5)
        witnesses.append({'parameter_exact':_pair(u),'basis_exact':[_pair(x) for x in N],
                          'effective_shape_coefficients_exact':[_pair(x) for x in response]})
    m=[[_frac(x) for x in row['effective_shape_coefficients_exact']] for row in witnesses]
    determinant=(m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])
                 -m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])
                 +m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]))
    if determinant==0: raise FlankParameterError('effective shape response matrix is singular')
    return witnesses,determinant


def build_parameters(repository_root, overrides=None):
    root=Path(repository_root).resolve(strict=True)
    data,anchor,sides,weights,stock_radius=_load_inputs(root)
    flanks=data['bindings']['flanks']
    defaults={'pitch_radius_mm':_f(flanks['shared_pitch_circle_radius_mm']),
              'root_radius_mm':_f(flanks['shared_cylinder_radius_mm']),
              'phase_rad':_f(flanks['shared_phase_rad']),
              'shaft_outer_diameter_mm':2*stock_radius}
    for label in LABELS:
        poles=sides[label]['generator']['local_poles']
        for n in FREE:
            for j,axis in enumerate(('t','r')): defaults[f'{label}.P{n}.{axis}_mm']=_f(poles[n][j])
        for role in ('root','outer'): defaults[f'{label}.alpha_{role}_rad']=None
    values=_values(defaults,overrides); rp=values['pitch_radius_mm']; rho=values['root_radius_mm']; phase=values['phase_rad']; shaft=values['shaft_outer_diameter_mm']/2
    if not rp>rho>0 or not shaft>0 or not -5<phase<5: raise FlankParameterError('radius or phase outside supported domain')
    cap=F(131,10); roll=F(15)
    if not shaft<cap<roll or not rp+rho<cap: raise FlankParameterError('auxiliary cap and roll clearance guards failed')
    parameters=[]; templates={}; expressions=[]; solved={}; endpoints={}
    for label in LABELS:
        side=sides[label]; w=weights[label]; source=[[ _f(p[0]),_f(p[1])] for p in side['generator']['local_poles']]
        A,B=[[_frac(v) for v in row] for row in w['endpoint_weights_exact']]
        if len(A)!=7 or len(B)!=7 or sum(A)!=1 or sum(B)!=1: raise FlankParameterError('invalid exact endpoint weights')
        det=A[1]*B[5]-A[5]*B[1]
        if det==0 or det!=_frac(w['det_exact']): raise FlankParameterError('endpoint matrix not supported')
        witnesses,response_determinant=_basis_and_effective_witness(side,A,B,det)
        source_ends=[[sum((row[i]*source[i][j] for i in range(7)),F(0)) for j in range(2)] for row in (A,B)]
        root_index=1 if label=='F0002' else 0
        if w['root_endpoint']!=('b' if root_index else 'a'): raise FlankParameterError('root endpoint role differs')
        controls=[p[:] for p in source]
        for n in FREE:
            for j,axis in enumerate(('t','r')): controls[n][j]=values[f'{label}.P{n}.{axis}_mm']
        targets=[None,None]; endpoint_entries={}; angle_entries={}
        for role,index,center,radius in (('root',root_index,[F(0),rp],rho),('outer',1-root_index,[F(0),F(0)],shaft)):
            angle_id=f'{label}.alpha_{role}_rad'; angle=values[angle_id]
            # Independent angle defaults are anchored to the C2 default frame,
            # not recomputed when the current circle center/radius is edited.
            initial_center=[F(0),defaults['pitch_radius_mm']] if role=='root' else [F(0),F(0)]
            dt=source_ends[index][0]-initial_center[0]; dr=source_ends[index][1]-initial_center[1]
            if angle is None:
                angle_i=_atan2_tr(dt,dr)
                length=(I.of(dt).square()+I.of(dr).square()).sqrt()
                if length.lo<=0: raise FlankParameterError('zero source endpoint direction')
                endpoint=[I.of(center[0])+I.of(radius)*I.of(dt)/length,
                          I.of(center[1])+I.of(radius)*I.of(dr)/length]
                definition={'op':'atan2','t_exact':_pair(dt),'r_exact':_pair(dr)}
            else:
                angle_i=I.of(angle)
                if angle_i.lo < -5 or angle_i.hi > 5: raise FlankParameterError('connection angle outside supported trig domain')
                sine,cosine=_trig(angle_i)
                endpoint=[I.of(center[0])+I.of(radius)*sine,I.of(center[1])+I.of(radius)*cosine]
                definition={'op':'independent_input','value_exact':_pair(angle)}
            target_id=f'{label}.{role}.circle_point'
            expressions.append({'id':target_id,'op':'CircleEvaluate','center_expression':{'t':'0','r':'pitch_radius_mm' if role=='root' else '0'},
                                'evaluated_center_exact':{'t':_pair(center[0]),'r':_pair(center[1])},
                                'radius_expression':'root_radius_mm' if role=='root' else 'shaft_outer_diameter_mm/2',
                                'angle_parameter':angle_id,'convention':'t=t0+R*sin(alpha); r=r0+R*cos(alpha)',
                                'consumers':[f'{label}.spline_endpoint_{"a" if index==0 else "b"}',f'{label}.{role}_arc_endpoint']})
            targets[index]=endpoint;endpoint_entries[role]={'expression_ref':target_id,'t_mm':_preview(endpoint[0]),'r_mm':_preview(endpoint[1])}
            angle_entries[role]={'id':angle_id,'classification':'independent','unit':'rad','definition':definition,'preview':_preview(angle_i),
                                 'consumers':[target_id],'same_side_members':22}
        fixed_indices=(0,2,3,4,6); Q=[[I.of(x) for x in p] for p in controls]
        for j in range(2):
            rhs=[targets[k][j]-sum((I.of(row[i])*I.of(controls[i][j]) for i in fixed_indices),I.of(0)) for k,row in enumerate((A,B))]
            Q[1][j]=(rhs[0]*I.of(B[5])-I.of(A[5])*rhs[1])/I.of(det)
            Q[5][j]=(I.of(A[1])*rhs[1]-rhs[0]*I.of(B[1]))/I.of(det)
        # FDRV sufficient conditions, evaluated on enclosures, not previews.
        for p in Q:
            if p[1].lo<=0 or (p[0].lo<=0 if label=='F0002' else p[0].hi>=0):
                raise FlankParameterError('pole side or positive radius guard failed: '+label)
            if (p[0].square()+p[1].square()).hi >= I.of(cap*cap).lo: raise FlankParameterError('cap hull guard failed: '+label)
        for a,b in zip(Q,Q[1:]):
            _assert_positive(a[0]-b[0],'t monotonicity guard failed: '+label)
            _assert_positive(a[1]-b[1] if label=='F0002' else b[1]-a[1],'r monotonicity guard failed: '+label)
        rootpoint=targets[root_index]
        if rootpoint[1].hi>=I.of(rp).lo or _abs_upper(rootpoint[0])>=rho:
            raise FlankParameterError('root lower-circle branch guard failed: '+label)
        if (rootpoint[0].square()+rootpoint[1].square()).hi>=I.of(shaft*shaft).lo:
            raise FlankParameterError('root point is not inside shaft circle: '+label)
        guard_margins={
            'signed_t_lower_mm':min((p[0] if label=='F0002' else -p[0]).lo for p in Q),
            'r_lower_mm':min(p[1].lo for p in Q),
            'successive_t_drop_lower_mm':min((a[0]-b[0]).lo for a,b in zip(Q,Q[1:])),
            'successive_r_change_lower_mm':min((a[1]-b[1] if label=='F0002' else b[1]-a[1]).lo for a,b in zip(Q,Q[1:])),
            'cap_squared_clearance_lower_mm2':min((I.of(cap*cap)-(p[0].square()+p[1].square())).lo for p in Q),
            'root_below_pitch_center_lower_mm':(I.of(rp)-rootpoint[1]).lo,
            'root_t_circle_margin_lower_mm':I.of(rho-_abs_upper(rootpoint[0])).lo,
            'root_inside_shaft_squared_margin_lower_mm2':(I.of(shaft*shaft)-(rootpoint[0].square()+rootpoint[1].square())).lo,
        }
        if any(value<=0 for value in guard_margins.values()):
            raise FlankParameterError('strict domain margin not enclosed: '+label)
        changes=[sum((_abs_upper(Q[i][j]-I.of(source[i][j])) for j in range(2)),F(0)) for i in range(7)]
        curve_bound=max(changes)
        template={'source':{'label':label,'snapshot_id':side['snapshot_id'],'source_path':side['source_path'],
                            'source_local_poles_exact':[[ _pair(x) for x in p] for p in source],
                            'source_local_frame':'recorded F0064 t,r at generator y=-124; source transformation uncertainty not enclosed'},
                  'basis':{'order':4,'knots_exact':w['knots_binary64_exact'],'full_domain':[0,1],
                           'fin_interval_exact':w['interval_binary64_exact'],'rational':False,'num_poles':7},
                  'endpoint_weights_exact':w['endpoint_weights_exact'],'matrix_determinant_exact':w['det_exact'],
                  'solve':{'unknown_poles':[1,5],'rhs_poles':[0,2,3,4,6],
                           'expression':'[P1,P5] = inverse([[A1,A5],[B1,B5]]) * ([endpoint_a,endpoint_b] - sum(Aj,Bj)*Pj for j=0,2,3,4,6)',
                           'algebra':'exact rational weights, exact symbolic CircleEvaluate endpoints; numerical intervals enclose evaluation'},
                  'effective_shape_response':{'free_poles':list(FREE),'witnesses':witnesses,
                      'determinant_exact':_pair(response_determinant),
                      'scope':'nonzero determinant proves independent t or r shape responses at three interior FIN points, not a full-domain error sample'},
                  'interior_witness_points':[{'parameter_exact':item['parameter_exact'],
                       't_mm':_preview(sum((I.of(_frac(coef))*Q[i][0] for i,coef in enumerate(item['basis_exact'])),I.of(0))),
                       'r_mm':_preview(sum((I.of(_frac(coef))*Q[i][1] for i,coef in enumerate(item['basis_exact'])),I.of(0)))}
                       for item in witnesses],
                  'angles':angle_entries,'endpoints':endpoint_entries,
                  'poles':[{'index':i,'classification':'fixed_not_counted' if i in FIXED else 'derived' if i in (1,5) else 'independent',
                            't_mm':_preview(Q[i][0]),'r_mm':_preview(Q[i][1])} for i in range(7)],
                  'sufficient_domain_strict_lower_bounds':{k:str(v) for k,v in guard_margins.items()},
                  'curve_source_to_candidate_local_L1_upper_mm':str(I.of(curve_bound).hi),
                  'default_or_edit_scope':'complete original spline parameter domain; source local binary64 observations as exact inputs'}
        templates[label]=template; solved[label]=Q;endpoints[label]=targets
        parameters.extend(angle_entries.values())
        for n in FREE:
            for j,axis in enumerate(('t','r')):
                key=f'{label}.P{n}.{axis}_mm'
                column=FREE.index(n)
                witness=next((item for item in witnesses if _frac(item['effective_shape_coefficients_exact'][column])!=0),None)
                if witness is None: raise FlankParameterError('no effective finite-FIN support witness: '+key)
                parameters.append({'id':key,'classification':'independent','unit':'mm','value_exact':_pair(values[key]),
                                   'consumers':[f'{label}.spline',f'{label}.P1_P5_solve'],'same_side_members':22,
                                   'active_support_witness':{'source_FIN_parameter_exact':witness['parameter_exact'],
                                       'effective_weight_exact':witness['effective_shape_coefficients_exact'][column],
                                       'meaning':'nonzero response after P1/P5 endpoint elimination'}})
    # Convert phase changes into an explicit ideal placement bound; this does
    # not pretend that original observed world-to-local transforms are exact.
    delta=I.of(phase)+I.of(20)*_pi()/22-I.of(_f(anchor['angle_rad']))
    max_phase=_abs_upper(delta)
    placement={}
    for label in LABELS:
        source=templates[label]['source']['source_local_poles_exact']
        radius=max(sum((abs(_frac(x)) for x in p),F(0)) for p in source)
        placement[label]={'anchor_rotation_delta_rad':_preview(delta),
                          'rotation_displacement_upper_mm':str(I.of(radius*max_phase).hi),
                          'curve_plus_rotation_upper_mm':str(I.of(_f_bound(templates[label]['curve_source_to_candidate_local_L1_upper_mm'])+radius*max_phase).hi),
                          'scope':'ideal local source/candidate curves and F0064 anchor placement only; excludes recorded world-to-local conversion error'}
    for key in ('pitch_radius_mm','root_radius_mm','phase_rad'):
        consumers={'phase_rad':['22 member transforms'],
                   'pitch_radius_mm':['22 member transforms','22 member root circles','two root endpoints'],
                   'root_radius_mm':['22 member root circles','two root endpoints']}[key]
        parameters.append({'id':key,'classification':'independent_shared','unit':'rad' if key=='phase_rad' else 'mm',
                           'value_exact':_pair(values[key]),'consumers':consumers})
    parameters.append({'id':'shaft_outer_diameter_mm','classification':'external_stock_dependency_editability_unresolved','unit':'mm',
                       'value_exact':_pair(values['shaft_outer_diameter_mm']),'consumers':['stock shaft outer radius','both outer endpoints'],
                       'source':'P3-STOCK-01/meridian-plan-c2.json vertices v6/v7; diameter is twice that radius'})
    return {'schema':'p3-flank-parameter-expression/0.1','unit':'mm','angle_unit':'rad',
            'status':'offline_expression_and_guarded_candidate','source_inputs':PATHS,'parameters':parameters,'templates':templates,
            'circle_expressions':expressions,'placement_contract':{'frame':flanks['frame'],
                'angle_convention':flanks['angle_convention'],'axis_position_expression':flanks['axis_position_expression'],
                'rotation_expression':flanks['rotation_expression'],'reference_phase_rad':flanks['reference_phase_rad'],
                'anchor_member_index':flanks['anchor_member_index'],
                'local_candidate_mapping':'theta_i=phase_rad+i*2*pi/22; e_r=u*cos(theta_i)+v*sin(theta_i); e_t=-u*sin(theta_i)+v*cos(theta_i); ABS=axis_point+t*e_t+r*e_r with separately specified axial coordinate',
                'source_world_mapping_note':'C2 rotation_expression acts on source-world template; local t/r mapping uses theta_i and its observed anchor discrepancy is reported separately, not assumed exactly identical',
                'source':'workspace/v3/p3/P3-DECISIONS-02/decision-bindings-c2.json'},
            'member_placements':[{'member_index':m['member_index'],
                'p1_cylinder_face_id':m['p1_cylinder_face_id'],'side_face_ids':{k:v['p1_face_id'] for k,v in m['sides'].items()},
                'angle_expression':f'phase_rad + {m["member_index"]} * 2*pi/22',
                'template_refs':list(LABELS)} for m in flanks['members']],
            'source_reference_vs_current':{'pitch_radius_delta_mm':_pair(rp-_f(anchor['provisional_y_minus_71_cut_loop']['inner_carrier_center_local_t_r_mm'][1])),
              'phase_delta_rad':_pair(phase-_f(flanks['members'][0]['observed_angle_rad'])), 'anchor_placement':placement},
            'validation':{'simple_four_segment_loop':'sufficient strict interval guards passed',
                          'six_segment_auxiliary_roll_clearance':'sufficient strict interval guards passed with cap=13.1 mm, roll=15 mm',
                          'global_strict_margins_exact':{'pitch_minus_root_mm':_pair(rp-rho),'root_radius_mm':_pair(rho),
                              'shaft_radius_mm':_pair(shaft),'cap_minus_shaft_mm':_pair(cap-shaft),
                              'roll_minus_cap_mm':_pair(roll-cap),'cap_minus_pitch_and_root_mm':_pair(cap-rp-rho)},
                          'domain':'only inputs satisfying all checks in this function; no unrestricted parameter range asserted'},
            'limitations':['source local transform uncertainty and full source/candidate geometry are not enclosed',
                           'source finite trims, material side, native constraints and solver behavior remain unproven',
                           'placement bound applies to F0064 anchor only, not per-member residuals',
                           'no G1/tangent condition; source-side nonzero inactive pole weights retained'],
            'geometry_proven':False,'native_binding_verified':False,'execution_approved':False}


def _f_bound(decimal_string): return F(Decimal(decimal_string))
