"""Continuous finite R32 interface arcs from same-session C14 and P3 captures.

Binary64 readbacks are treated as exact numbers. Evaluator curves and parameter
limits must faithfully describe the original class-10 edges; the capture does
not prove kernel edge/FIN coincidence or face interior. P3 H215's source-to-
ideal arc bounds are an explicit premise, not re-established here.
"""
from fractions import Fraction as Q
from math import factorial, isfinite, nextafter, inf
from .nx2506_tail_trim_bound import _loop_cycle, _sqrt


class HeadTrimError(ValueError):
    pass


def _q(x):
    if type(x) not in (int, float) or not isfinite(float(x)):
        raise HeadTrimError('expected finite binary64')
    return Q(x)


def _walk(n):
    yield n
    for c in n.get('children', []):
        yield from _walk(c['child'])


def _edges(d):
    rows = [n for n in _walk(d['topology']) if n.get('type') == 8]
    if len({n['tag'] for n in rows}) != len(rows):
        raise HeadTrimError('duplicate edge')
    return {n['tag']: n for n in rows}


def _trig(x, sine):
    if abs(x) > 7:
        raise HeadTrimError('angle outside certified Taylor range')
    off = 1 if sine else 0
    v = sum(((-1)**j*x**(2*j+off)/factorial(2*j+off)
             for j in range(60)), Q())
    rem = abs(x)**(120+off)/factorial(120+off)
    return v-rem, v+rem


def _scale(a, interval):
    x,y = (a*interval[0], a*interval[1])
    return (min(x,y),max(x,y))


def _circle(g):
    if (g.get('type') != 'circular_evaluator' or g.get('coordinate_system') != 'ABS'
        or g.get('is_periodic') is not False or g.get('arc_is_periodic') is not False
        or g.get('arc_limits') != g.get('evaluator_limits')):
        raise HeadTrimError('unsupported original finite circle')
    c = tuple(map(_q, g['center'])); x = tuple(map(_q, g['x_axis'])); y = tuple(map(_q, g['y_axis']))
    a,b = map(_q, g['evaluator_limits']); r = _q(g['radius'])
    if len(c)!=3 or len(x)!=3 or len(y)!=3 or x[1] or y[1] or not 0 < b-a < 1 or r <= 1:
        raise HeadTrimError('expected short planar circle')
    det = x[0]*y[2]-x[2]*y[0]
    if not det: raise HeadTrimError('degenerate frame')
    sign = 1 if det > 0 else -1
    normlo,normhi = _sqrt(x[0]*x[0]+x[2]*x[2])
    if normlo < Q('0.9') or normhi > Q('1.1'): raise HeadTrimError('bad frame norm')
    # Correct the displayed rounded axes to the unit x direction and its
    # oriented perpendicular. Bound correction in L1 over all parameters.
    normerr = max(abs(normlo-1),abs(normhi-1))
    xerr = (abs(x[0])+abs(x[2]))*normerr/normlo
    perp = (-sign*x[2], Q(0), sign*x[0])
    yerr = sum(abs(u-v) for u,v in zip(y,perp))+xerr
    err = xerr+yerr
    if err > Q('0.000000001'): raise HeadTrimError('frame correction too large')
    return c,x,y,a,b,r,sign,err


def _point(circle, t):
    c,x,y,_,_,r,_,_ = circle
    co,si = _trig(t,False),_trig(t,True)
    return tuple((c[i]+_scale(r*x[i],co)[0]+_scale(r*y[i],si)[0],
                  c[i]+_scale(r*x[i],co)[1]+_scale(r*y[i],si)[1]) for i in range(3))


def _gap(p,q):
    return sum(max(abs(a-d),abs(b-c)) for (a,b),(c,d) in zip(p,q))


def _compare(a,b):
    ca,_,_,la,ha,ra,sa,ea = a; cb,_,_,lb,hb,rb,sb,eb = b
    # A reversed parameter correspondence is mandatory for opposite frame senses.
    endpoints = (lb,hb) if sa == sb else (hb,lb)
    delta = max(_gap(_point(a,t),_point(b,u)) for t,u in zip((la,ha),endpoints))
    centers = sum(abs(x-y) for x,y in zip(ca,cb))
    radii = abs(ra-rb)
    correction = ra*ea+rb*eb
    chord = (delta+centers+radii+correction)/min(ra,rb)
    if chord >= Q('0.001'):
        raise HeadTrimError('endpoint correspondence not established')
    # Both arcs have sweep < 1 rad; small endpoint chord errors select the
    # same phase lift. |angle difference| <= 2*chord, and linear parameter
    # interpolation takes at most the larger endpoint phase difference.
    return centers+radii+2*ra*chord+correction, delta


def _parent_bound(c, event):
    center,_,_,_,_,r,_,err = c
    if event == 'canonical_y_minus16':
        ylo=yhi=Q(-16); rlo,rhi=_sqrt(Q(768))
    elif event == 'canonical_sphere_cone':
        slo,shi=_sqrt(Q(6967)); ylo=(-35+slo)/4; yhi=(-35+shi)/4
        rlo=ylo+Q('17.5'); rhi=yhi+Q('17.5')
    else: raise HeadTrimError('unknown event')
    return abs(center[0])+abs(center[2])+max(abs(center[1]-ylo),abs(center[1]-yhi))+max(abs(r-rlo),abs(r-rhi))+r*err


def _up(x):
    f=float(x)
    return nextafter(f,inf) if Q(f)<x else f


def _down(x):
    f=float(x)
    return nextafter(f,-inf) if Q(f)>x else f


def assess_head_interface_arcs(capture, support, h215, p3_arcs, snapshots):
    """Compare all 12 actual finite arcs to H215 source and ideal arcs.

    snapshots maps source_face names to their P3 physical-edge capture. The
    result assumes valid evaluator semantics, exact shared ABS coordinates,
    and H215's corresponding finite target arc theorem. It makes no face-fill,
    material-side, tolerant kernel or entire-head acceptance claim.
    """
    if (capture.get('schema')!='p4-native-tail-brep/1' or capture.get('scope')!='all'
        or capture.get('stage')!='complete' or capture.get('status')!='PROBES_RETURNED'
        or capture.get('disk_copy_unchanged') is not True or capture.get('face_count')!=218
        or capture.get('returned_face_count')!=218 or capture.get('unvisited_roles')):
        raise HeadTrimError('incomplete C14 capture')
    if support.get('schema')!='p4-complete-untrimmed-carrier-bounds/1' or support.get('face_count')!=218:
        raise HeadTrimError('incomplete support assignment')
    if h215.get('schema')!='p3-head02-whole-head-accepted/1' or not h215.get('status','').startswith('H215 accepted'):
        raise HeadTrimError('missing accepted H215 premise')
    if p3_arcs.get('schema')!='p3-head02-sphere-captured-circle-arcs/1' or p3_arcs.get('complete_all_six') is not True:
        raise HeadTrimError('missing P3 arc inventory')
    ids={r['face_tag_session_only']:r for r in support['faces']}
    inv={int(r['inventory']['tag_session_only']):r['inventory'] for r in capture['selection']}
    det={r['detail']['face_tag']:r['detail'] for r in capture['results']}
    if len(ids)!=218 or set(ids)!=set(inv) or set(ids)!=set(det) or any(r.get('status')!='carrier_bound' for r in ids.values()):
        raise HeadTrimError('face identities or carriers do not match')
    adj={}
    for f,v in inv.items():
        for e in v['face_edge_tags_session_only']: adj.setdefault(int(e),[]).append(f)
    sources=[]
    for row in p3_arcs['records']:
        snap=snapshots[row['source_face']]
        if not snap.get('ok') or snap.get('read_consistency_fault') is not False:
            raise HeadTrimError('incomplete source capture')
        detail=snap['detail']
        if len(detail)!=1 or detail[0].get('label')!=row['source_face'] or detail[0].get('status')!='MATCHED':
            raise HeadTrimError('source face binding failed')
        diagnostic=detail[0]['diagnostic']
        if diagnostic.get('outcome')!='CLEAN_TRACE' or not diagnostic.get('edge_coverage_complete'):
            raise HeadTrimError('unclean source edge capture')
        edge=_edges(diagnostic).get(int(row['source_edge']))
        if edge is None or edge.get('geometry_class')!=10 or row.get('original_class')!=10:
            raise HeadTrimError('source original edge missing')
        proof=Q(row['full_finite_arc_bidirectional_upper_mm'])
        if proof<0 or proof>Q(p3_arcs['each_whole_arc_upper_mm']): raise HeadTrimError('invalid H215 arc budget')
        sources.append((row,_circle(edge['geometry']),proof))
    if len(sources)!=12 or len({(x[0]['source_face'],x[0]['event']) for x in sources})!=12:
        raise HeadTrimError('source arc inventory invalid')
    found=[]; used=set()
    spheres=[f for f in ids if ids[f]['p3_support_id']=='head.R32']
    if len(spheres)!=6: raise HeadTrimError('expected six R32 faces')
    for f in spheres:
        if det[f].get('outcome')!='CLEAN_TRACE' or not det[f].get('edge_coverage_complete'):
            raise HeadTrimError('unclean sphere trace')
        _loop_cycle(det[f],inv[f]); edges=_edges(det[f])
        for e,node in edges.items():
            neighbors=adj.get(e,[])
            if len(neighbors)!=2 or f not in neighbors: raise HeadTrimError('non-manifold sphere edge')
            other=next(v for v in neighbors if v!=f); kind=ids[other]['p3_support_id']
            if kind not in ('head.Y_head_step','head.cone'): continue
            if det[other].get('outcome')!='CLEAN_TRACE' or not det[other].get('edge_coverage_complete'):
                raise HeadTrimError('unclean adjacent face trace')
            _loop_cycle(det[other],inv[other]); peer=_edges(det[other]).get(e)
            if node.get('geometry_class')!=10 or peer is None or peer.get('geometry_class')!=10 or peer.get('geometry')!=node.get('geometry'):
                raise HeadTrimError('shared original circle mismatch')
            event='canonical_y_minus16' if kind=='head.Y_head_step' else 'canonical_sphere_cone'
            circle=_circle(node['geometry']); candidates=[]
            for row,ref,proof in sources:
                if row['event']!=event: continue
                try: bound,endpoint=_compare(circle,ref)
                except HeadTrimError: continue
                candidates.append((bound,endpoint,row,proof))
            if len(candidates)!=1: raise HeadTrimError('source finite arc match is not unique')
            bound,endpoint,row,proof=candidates[0]; key=(row['source_face'],row['source_edge'])
            if key in used: raise HeadTrimError('source arc matched twice')
            used.add(key)
            found.append({'native_sphere_face':f,'native_adjacent_face':other,'native_edge':e,
                'event':event,'p3_source_face':key[0],'p3_source_edge':key[1],
                'endpoint_interval_l1_upper_mm':_up(endpoint),
                'native_to_p3_source_arc_upper_mm':_up(bound),
                'p3_source_to_ideal_upper_mm':_up(proof),
                'native_to_h215_ideal_arc_upper_mm':_up(bound+proof),
                'native_to_same_phase_ideal_parent_circle_upper_mm':_up(_parent_bound(circle,event))})
    if len(found)!=12 or len(used)!=12: raise HeadTrimError('did not cover all 12 interface arcs')
    return {'schema':'p4-head-interface-finite-arcs/1','status':'conditional_continuous_arc_bounds',
            'count':len(found),'max_native_to_h215_ideal_arc_upper_mm':max(x['native_to_h215_ideal_arc_upper_mm'] for x in found),
            'max_native_to_p3_source_arc_upper_mm':max(x['native_to_p3_source_arc_upper_mm'] for x in found),
            'max_same_phase_parent_circle_upper_mm':max(x['native_to_same_phase_ideal_parent_circle_upper_mm'] for x in found),
            'limitations':['requires faithful original EVAL and finite limits, common ABS frame, H215 source-to-target theorem and valid topology',
             'no proof of tolerant kernel edge/FIN coincidence, face fill, material side, other head trims or global body'], 'arcs':found}


def _l1_point(a,b):
    return sum((abs(_q(x)-_q(y)) for x,y in zip(a,b)),Q())


def _native_ribbon(detail, inventory, ids, adjacency):
    _loop_cycle(detail,inventory)
    phases={}; vertices={}; incident={}
    for edge in _edges(detail).values():
        e=edge['tag']; neighbors=adjacency.get(e,[])
        if len(neighbors)!=2 or detail['face_tag'] not in neighbors:
            raise HeadTrimError('ribbon edge is not shared by exactly two faces')
        other=next(x for x in neighbors if x!=detail['face_tag'])
        kind=ids[other]['p3_support_id']
        if kind.startswith('head.sector.'):
            phase='AB_contact'; expected_class=10
        else:
            phase={'head.Y_head_step':'lower_y_minus16','head.upper_fillet':'lower_L_round',
                   'head.R32':'lower_sphere','head.cone':'upper_cone',
                   'stock.s20':'upper_y17'}.get(kind)
            expected_class=11
        if phase is None or edge.get('geometry_class')!=expected_class:
            raise HeadTrimError('unexpected native ribbon phase or edge class')
        phases[e]=phase
        vs=[v for v in _walk(edge) if v.get('type')==9]
        if len(vs)!=2: raise HeadTrimError('ribbon edge lacks two vertices')
        for v in vs:
            ident=v['local_identifier']; pt=v['geometry']['point']
            if ident in vertices and vertices[ident]!=pt: raise HeadTrimError('inconsistent native vertex')
            vertices[ident]=pt; incident.setdefault(ident,[]).append(phase)
    if any(len(x)!=2 for x in incident.values()): raise HeadTrimError('bad ribbon event incidence')
    fin_v=Q(0)
    for n in _walk(detail['topology']):
        if n.get('type')!=7: continue
        g=n.get('geometry',{}); poles=g.get('weighted_poles_flat_xyzw',[])
        if (g.get('type')!=102 or g.get('rational') is not False or not poles or len(poles)%4
            or any(_q(w)!=1 for w in poles[3::4])):
            raise HeadTrimError('unsupported native FIN control hull')
        n_poles=g.get('num_poles'); order=g.get('order'); knots=g.get('knots')
        if (type(n_poles)!=int or type(order)!=int or order<2 or n_poles<order
            or n_poles*4!=len(poles) or not isinstance(knots,list) or len(knots)!=n_poles+order):
            raise HeadTrimError('invalid native FIN spline dimensions')
        knots=list(map(_q,knots)); start=_q(g['start']); end=_q(g['end'])
        if any(a>b for a,b in zip(knots,knots[1:])) or not knots[order-1]<=start<end<=knots[n_poles]:
            raise HeadTrimError('invalid native FIN spline knots or active interval')
        fin_v=max(fin_v,*(abs(_q(v)) for v in poles[1::4]))
    if fin_v>=Q('1.29'): raise HeadTrimError('FIN control hull leaves P3 minor-angle interval')
    return phases,vertices,incident,fin_v


def _source_ribbon(face, region, source, endpoint):
    rows=region['source_ordered_edges']; phases={str(x['edge']):x['phase'] for x in rows}
    fins=source['faces'][face]['fins']
    if set(phases)!={str(x['p1_edge_tag']) for x in fins}:
        raise HeadTrimError('P3 face edge inventory mismatch')
    ends=[]
    for fin in fins:
        edge=str(fin['p1_edge_tag']); pts=fin['vertices_mm']
        if len(pts)!=2: raise HeadTrimError('bad P3 source vertices')
        for i,pt in enumerate(pts):
            bounds=[Q(event['vertex_to_canonical_event_endpoint_upper_mm'])
                    for r in endpoint['records'] if r['face']==face and str(r['edge'])==edge
                    for event in r['events'] if event['stored_vertex_index']==i]
            ends.append((phases[edge],pt,min(bounds) if bounds else None))
    return ends


def _seam_collar(circle, axis, branch, sector):
    """Bound the whole original circle's displacement in canonical s."""
    if (circle.get('type')!='circular_evaluator' or circle.get('coordinate_system')!='ABS'
        or circle.get('is_periodic') is not False or circle.get('arc_is_periodic') is not False
        or circle.get('evaluator_limits')!=circle.get('arc_limits')):
        raise HeadTrimError('unsupported seam evaluator')
    c=tuple(map(_q,circle['center'])); x=tuple(map(_q,circle['x_axis'])); y=tuple(map(_q,circle['y_axis']))
    r=_q(circle['radius']); lo,hi=map(_q,circle['evaluator_limits'])
    if any(len(v)!=3 for v in (c,x,y)) or r<=0 or not lo<hi:
        raise HeadTrimError('invalid seam circle')
    nlo,nhi=_sqrt(axis[0]*axis[0]+axis[2]*axis[2])
    if nlo<=0: raise HeadTrimError('zero sector axis')
    projection=lambda v:axis[0]*v[0]+axis[2]*v[2]
    center=_scale(projection(c),(1/nhi,1/nlo))
    d0,d1=map(Q,branch['d_initial_exact_enclosure'])
    ra=_q(sector['ra_initial_source_binary64']); rb=_q(branch['rb_initial_source_binary64'])
    if not d0<=d1 or rb<=ra: raise HeadTrimError('invalid canonical seam')
    s0,s1=-ra*d1/(rb-ra),-ra*d0/(rb-ra)
    return max(abs(center[0]-s1),abs(center[1]-s0))+r*(abs(projection(x))+abs(projection(y)))/nlo


def assess_head_ribbon_events(capture, support, drivers, regions, source, endpoint):
    """Bind C14 ribbon loop vertices to P3 H206 events using phase and geometry.

    P3 edge IDs are used only within their original evidence; C14 identities are
    same-session only. UV control hulls witness parameter range but are not
    asserted equal to complete original class-11 intersection edges.
    """
    if (capture.get('schema')!='p4-native-tail-brep/1' or capture.get('scope')!='all'
        or capture.get('stage')!='complete' or capture.get('status')!='PROBES_RETURNED'
        or capture.get('disk_copy_unchanged') is not True or capture.get('face_count')!=218
        or capture.get('returned_face_count')!=218 or capture.get('unvisited_roles')):
        raise HeadTrimError('incomplete C14 capture')
    if (support.get('schema')!='p4-complete-untrimmed-carrier-bounds/1'
        or drivers.get('schema')!='p3-head02-confirmed-drivers/1'
        or regions.get('schema')!='p3-head02-whole-head-face-regions/0.1'
        or endpoint.get('schema')!='p3-head02-finite-endpoint-bound/1'):
        raise HeadTrimError('unexpected evidence schema')
    ids={r['face_tag_session_only']:r for r in support['faces']}
    inv={int(r['inventory']['tag_session_only']):r['inventory'] for r in capture['selection']}
    det={r['detail']['face_tag']:r['detail'] for r in capture['results']}
    if len(ids)!=218 or set(ids)!=set(inv) or set(ids)!=set(det): raise HeadTrimError('capture identity mismatch')
    adjacency={}
    for f,v in inv.items():
        for e in v['face_edge_tags_session_only']: adjacency.setdefault(int(e),[]).append(f)
    region_by_face={r['face']:r for r in regions['records'] if r['target'].get('kind')=='torus_outer_s_y_chart'}
    if len(region_by_face)!=18: raise HeadTrimError('expected 18 P3 ribbons')
    source_events={f:_source_ribbon(f,r,source,endpoint) for f,r in region_by_face.items()}
    faces=[f for f in ids if ids[f]['p3_support_id'].startswith('head.sector.')]
    if len(faces)!=18: raise HeadTrimError('expected 18 native ribbon faces')
    output=[]; used=set()
    for face in faces:
        d=det[face]
        if d.get('outcome')!='CLEAN_TRACE' or not d.get('edge_coverage_complete'):
            raise HeadTrimError('unclean native ribbon trace')
        phases,vertices,incident,fin_v=_native_ribbon(d,inv[face],ids,adjacency)
        uv=d.get('uv_box')
        if not isinstance(uv,list) or len(uv)!=4 or max(abs(_q(uv[2])),abs(_q(uv[3])))>=Q('1.29'):
            raise HeadTrimError('native UV box leaves P3 minor-angle interval')
        role='A' if ids[face]['p3_support_id'].endswith('.A_piece') else 'B'
        candidates=[]
        for source_face,region in region_by_face.items():
            if region['target']['role']!=role: continue
            ev=[]; valid=True
            for ident,pt in vertices.items():
                source_entries=source_events[source_face]; required=incident[ident]
                matched=[]
                for phase in required:
                    choices=[(_l1_point(pt,p),bound) for ph,p,bound in source_entries if ph==phase]
                    if not choices: valid=False; break
                    matched.append(min(choices,key=lambda z:z[0]))
                if not valid: break
                gap=max(x[0] for x in matched)
                if gap>=Q('0.00001'): valid=False; break
                # A H206 witness on either incident edge fixes the same corner.
                witnesses=[gap+b for _,b in matched if b is not None]
                ev.append({'native_vertex_id_face_local':ident,'phases':sorted(required),
                           'p3_vertex_l1_gap_upper_mm':_up(gap),
                           'h206_event_upper_mm':_up(min(witnesses)) if witnesses else None})
            if valid: candidates.append((source_face,region,ev))
        if len(candidates)!=1: raise HeadTrimError('ribbon geometry/phase match is not unique')
        sf,region,events=candidates[0]
        if sf in used: raise HeadTrimError('P3 ribbon matched twice')
        used.add(sf)
        sector=region['target']['sector']; axis=tuple(map(_q,drivers['sectors'][sector]['axis_source']))
        if axis[1]!=0: raise HeadTrimError('expected horizontal P3 axis')
        nlo,nhi=_sqrt(axis[0]*axis[0]+axis[2]*axis[2])
        tmin=min((axis[2]*_q(p[0])-axis[0]*_q(p[2]))/nhi for p in vertices.values())
        if nlo<=0 or tmin<=Q('25.57'): raise HeadTrimError('not on positive transverse side')
        output.append({'native_face':face,'native_support_id':ids[face]['p3_support_id'],
            'p3_face':sf,'sector':sector,'role':role,'branch':region['target'].get('branch'),
            'native_edge_phases':{str(k):v for k,v in phases.items()},'native_events':events,
            'native_fin_abs_v_control_upper_rad':_up(fin_v),
            'native_uv_box_abs_v_upper_rad':_up(max(abs(_q(uv[2])),abs(_q(uv[3])))),
            'vertex_positive_transverse_lower_mm':_down(tmin),
            'unmatched_h206_events':sum(x['h206_event_upper_mm'] is None for x in events)})
    if len(used)!=18: raise HeadTrimError('not all P3 ribbons matched')
    by_native={r['native_face']:r for r in output}
    collars=[]
    for row in output:
        if row['role']!='B': continue
        edge_ids=[int(e) for e,p in row['native_edge_phases'].items() if p=='AB_contact']
        if len(edge_ids)!=1: raise HeadTrimError('B ribbon must have one A contact')
        edge=edge_ids[0]; other=next(f for f in adjacency[edge] if f!=row['native_face'])
        ar=by_native.get(other); sector=drivers['sectors'][row['sector']]
        if (ar is None or ar['p3_face']!=sector['A_face'] or ar['sector']!=row['sector']
            or sector['branches'][row['branch']]['face']!=row['p3_face']):
            raise HeadTrimError('native A/B seam differs from P3 physical sector')
        node=_edges(det[row['native_face']])[edge]
        peer=_edges(det[other]).get(edge)
        if peer is None or peer.get('geometry')!=node.get('geometry'):
            raise HeadTrimError('native A/B seam evaluators differ')
        collar=_seam_collar(node['geometry'],tuple(map(_q,sector['axis_source'])),
                            sector['branches'][row['branch']],sector)
        if collar>Q('0.000000001'): raise HeadTrimError('seam collar too wide')
        row['seam_s_to_canonical_upper_mm']=_up(collar)
        row['adjacent_native_A_face']=other
        collars.append(collar)
        for incident_face in (row,ar):
            local_edge=_edges(det[incident_face['native_face']])[edge]
            local_ids={v['local_identifier'] for v in _walk(local_edge) if v.get('type')==9}
            for event in incident_face['native_events']:
                if (event['h206_event_upper_mm'] is None and event['phases']==['AB_contact','lower_y_minus16']
                    and event['native_vertex_id_face_local'] in local_ids):
                    incident_face.setdefault('lower_seam_s_collar_by_vertex',{})[str(event['native_vertex_id_face_local'])]=_up(collar)
    seam_missing=[]
    for row in output:
        for event in row['native_events']:
            if event['h206_event_upper_mm'] is None:
                key=str(event['native_vertex_id_face_local'])
                collar=row.get('lower_seam_s_collar_by_vertex',{}).get(key)
                if collar is None: raise HeadTrimError('unwitnessed non-seam event')
                vertices={v['local_identifier']:v['geometry']['point'] for v in _walk(det[row['native_face']]['topology']) if v.get('type')==9}
                y_error=abs(_q(vertices[event['native_vertex_id_face_local']][1])+16)
                event['seam_s_collar_upper_mm']=collar
                event['seam_y_minus16_upper_mm']=_up(y_error)
                seam_missing.append(max(Q(collar),y_error))
    gaps=[e['p3_vertex_l1_gap_upper_mm'] for f in output for e in f['native_events']]
    hbounds=[e['h206_event_upper_mm'] for f in output for e in f['native_events'] if e['h206_event_upper_mm'] is not None]
    return {'schema':'p4-head-ribbon-event-bindings/1','status':'event_bindings_only',
        'face_count':18,'vertex_count':len(gaps),'h206_event_count':len(hbounds),
        'max_p3_vertex_l1_gap_upper_mm':max(gaps),
        'max_h206_event_upper_mm':max(hbounds),
        'seam_circle_count':len(collars),'max_seam_s_collar_upper_mm':_up(max(collars)),
        'max_all_event_coordinate_upper_mm':_up(max([Q(x) for x in hbounds]+seam_missing)),
        'limitations':['loop and branch matching are conditional on valid native edge/FIN and material-side semantics',
          'positive transverse check is at vertices only; no full branch, finite face, or Hausdorff bound follows',
          'native converted FIN control hull is not an exact class-11 edge'], 'faces':output}


def conditional_head_ribbon_edge_bounds(capture, bindings, same_s_graph_bound_mm):
    """Conditional per-phase finite boundary bounds, with an external premise.

    The caller must independently justify same_s_graph_bound_mm: it bounds the
    full native-to-ideal point displacement at common s on every corresponding
    phase graph, including parent-carrier and frame errors. For seam curves it
    bounds the corresponding same-y displacement. This is NOT a bound supplied
    by the support Hausdorff readback or by FIN control points.

    The remaining explicit premises are that each original finite boundary is
    exactly the indicated continuous graph or seam arc on the selected branch,
    phase ordering is preserved, and the P3 global speed inequalities apply to
    both graphs and to the small interval extensions between matched events.
    Native and target boundaries are mapped piecewise by a monotone affine
    correspondence between endpoint s (or seam y) values. Those premises are
    not independently demonstrated by this routine. A face bound also requires
    each face to be exactly the closed strip between the mapped upper and lower
    graphs, with no holes, extra boundaries or opposing material selection.
    """
    if bindings.get('schema')!='p4-head-ribbon-event-bindings/1' or bindings.get('face_count')!=18:
        raise HeadTrimError('ribbon event bindings required')
    if type(same_s_graph_bound_mm) not in (int,float) or not isfinite(float(same_s_graph_bound_mm)):
        raise HeadTrimError('finite externally justified graph bound required')
    graph=_q(same_s_graph_bound_mm)
    if graph<0: raise HeadTrimError('negative graph bound')
    details={x['detail']['face_tag']:x['detail'] for x in capture['results']}
    eps=_q(bindings['max_all_event_coordinate_upper_mm'])
    # P3 H208 chart: |dP/ds|<5.22, |dP/dy|<1.38,
    # |dy/ds|<40; seam interpolation uses |dy| <= eps.
    extension=(Q('5.22')+Q('1.38')*40)*eps
    bound=extension+graph
    rows=[]
    for row in bindings['faces']:
        events={e['native_vertex_id_face_local']:e for e in row['native_events']}
        for edge,phase in row['native_edge_phases'].items():
            node=_edges(details[row['native_face']])[int(edge)]
            vertices=[v['local_identifier'] for v in _walk(node) if v.get('type')==9]
            if len(vertices)!=2 or any(v not in events for v in vertices):
                raise HeadTrimError('edge endpoint event not bound')
            rows.append({'native_face':row['native_face'],'p3_source_face':row['p3_face'],
                'p3_sector':row['sector'],'p3_branch':row['branch'],
                'native_edge':int(edge),'phase':phase,
                'endpoint_events':vertices,'conditional_edge_upper_mm':_up(bound)})
    if len(rows)!=96: raise HeadTrimError('expected 96 face-edge incidences')
    return {'schema':'p4-head-ribbon-conditional-edge-bounds/1',
        'status':'hypothetical_conditional_on_external_same_s_graph_and_exact_phase_contract',
        'same_s_graph_bound_mm_supplied_by_caller':_up(graph),
        'event_coordinate_upper_mm':_up(eps),'event_extension_upper_mm':_up(extension),
        'max_conditional_edge_upper_mm':_up(bound),'face_edge_incidence_count':len(rows),
        'conditional_strips':[{'native_face':r['native_face'],'p3_source_face':r['p3_face'],
             'p3_sector':r['sector'],'p3_branch':r['branch'],
             'conditional_strip_upper_mm':_up(bound)} for r in bindings['faces']],
        'limitations':['The supplied same-s graph bound is a separate unproved quantitative premise; this routine does not derive it from carrier Hausdorff bounds.',
         'Also requires original edge-to-FIN and selected branch/phase correspondence, graph monotonicity, and P3 H208 speed bounds across the full patches and event extensions.',
         'C14 A/upper-fillet/step vertex coincidence with exact parent intersections is contradicted by assess_native_fillet_step_corners; no actual A-strip certificate follows.',
         'A strip bound additionally assumes exact face fill between the indicated upper and lower graphs; this is not established by the loops.',
         'Does not prove material side or kernel execution.'], 'edges':rows}


def _mul_interval(a,b):
    products=[x*y for x in a for y in b]
    return min(products),max(products)


def _unit_interval(v):
    v=tuple(x if isinstance(x,Q) else _q(x) for x in v)
    if len(v)!=3: raise HeadTrimError('invalid direction')
    lo,hi=_sqrt(sum((x*x for x in v),Q()))
    if lo<=Q('0.9') or hi>=Q('1.1'): raise HeadTrimError('non-unit or degenerate direction')
    return [_scale(x,(1/hi,1/lo)) for x in v]


def _interval_difference(a,b):
    return max(abs(a[0]-b[1]),abs(a[1]-b[0]))


def _point_interval(x):
    v=_q(x); return v,v


def _direction_error(actual,target):
    aa=tuple(map(_q,actual)); tt=tuple(map(_q,target))
    if sum((x*y for x,y in zip(aa,tt)),Q())<0: aa=tuple(-x for x in aa)
    return max(_interval_difference(x,y) for x,y in zip(_unit_interval(aa),_unit_interval(tt)))


def assess_head_ribbon_parameter_errors(capture, bindings, support, drivers):
    """Bound native-to-canonical analytic coefficients in the resolved frames.

    B radii and offsets use the exact P3 d enclosures and tangent construction;
    the 6 sector axis directions use normalized P3 source axes. All readback
    binary64s are exact inputs; square root/tan intervals are outward rational.
    """
    from .nx2506_tail_trim_bound import _tan
    if bindings.get('schema')!='p4-head-ribbon-event-bindings/1' or bindings.get('face_count')!=18:
        raise HeadTrimError('resolved ribbon bindings required')
    if drivers.get('schema')!='p3-head02-confirmed-drivers/1': raise HeadTrimError('P3 driver schema mismatch')
    ds={r['detail']['face_tag']:r['detail'] for r in capture['results']}
    ids={r['face_tag_session_only']:r for r in support['faces']}
    errors=[]
    for row in bindings['faces']:
        g=ds[row['native_face']]['topology']['geometry']; sec=drivers['sectors'][row['sector']]
        if g.get('type')!=204: raise HeadTrimError('ribbon is not toroidal')
        if _q(g['axis'][1])!=0 or _q(sec['axis_source'][1])!=0:
            raise HeadTrimError('ribbon axes must be horizontal')
        axis=sec['axis_source']; a=_unit_interval(axis)
        axiserr=_direction_error(g['axis'],axis)
        ra=_q(sec['ra_initial_source_binary64']); major=_q(sec['RA_initial_source_binary64'])
        if row['role']=='A':
            centers=[(Q(0),Q(0)),(Q(4),Q(4)),(Q(0),Q(0))]
            m=(major,major); minor=ra
        else:
            b=sec['branches'][row['branch']]; dlo,dhi=map(Q,b['d_initial_exact_enclosure']); minor=_q(b['rb_initial_source_binary64'])
            if not dlo<=dhi or minor<=ra: raise HeadTrimError('invalid canonical B')
            d=(dlo,dhi); centers=[_mul_interval(d,a[0]),(Q(4),Q(4)),_mul_interval(d,a[2])]
            square=max(dlo*dlo,dhi*dhi); minsquare=Q(0) if dlo<=0<=dhi else min(dlo*dlo,dhi*dhi)
            radlo=(minor-ra)**2-square; radhi=(minor-ra)**2-minsquare
            if radlo<=0: raise HeadTrimError('B tangency radicand not positive')
            rlo,_=_sqrt(radlo); _,rhi=_sqrt(radhi); m=(major-rhi,major-rlo)
        cerror=max(_interval_difference(_point_interval(v),ref) for v,ref in zip(g['center'],centers))
        me=_interval_difference(_point_interval(g['major_radius']),m)
        qe=abs(_q(g['minor_radius'])-minor)
        errors.append(('ribbon',row['native_face'],max(axiserr,cerror,me,qe)))
    counts={}
    for f,record in ids.items():
        kind=record['p3_support_id']
        if kind not in ('head.R32','head.cone','head.Y_head_step','head.upper_fillet','stock.s20'): continue
        g=ds[f]['topology']['geometry']; counts[kind]=counts.get(kind,0)+1
        if kind=='head.R32':
            if g.get('type')!=203: raise HeadTrimError('sphere geometry mismatch')
            e=max(*(abs(_q(x)) for x in g['center']),abs(_q(g['radius'])-32))
        elif kind=='head.cone':
            if g.get('type')!=202: raise HeadTrimError('cone geometry mismatch')
            if _q(g['axis'][1])<=0: raise HeadTrimError('cone positive nappe points away from canonical axis')
            lo,hi=_tan(_q(g['half_apex_angle']))
            e=max(_direction_error(g['axis'],(0,1,0)),abs(_q(g['point_at_apex'][0])),
                  abs(_q(g['point_at_apex'][1])+Q('17.5')),abs(_q(g['point_at_apex'][2])),abs(lo-1),abs(hi-1))
        elif kind=='head.upper_fillet':
            if g.get('type')!=204: raise HeadTrimError('fillet geometry mismatch')
            e=max(_direction_error(g['axis'],(0,1,0)),abs(_q(g['center'][0])),abs(_q(g['center'][1])+Q('18.5')),
                  abs(_q(g['center'][2])),abs(_q(g['major_radius'])-30),abs(_q(g['minor_radius'])-Q('2.5')))
        else:
            if g.get('type')!=209: raise HeadTrimError('plane geometry mismatch')
            normal=tuple(map(_q,g['normal']))
            if normal[0] or normal[2] or not normal[1]: raise HeadTrimError('unsupported tilted axial plane')
            y=-16 if kind=='head.Y_head_step' else 17
            e=abs(_q(g['point_on_plane'][1])-y)
        errors.append((kind,f,e))
    if counts!={'head.R32':6,'head.Y_head_step':6,'head.cone':6,'head.upper_fillet':1,'stock.s20':1}:
        raise HeadTrimError('head parent face inventory mismatch')
    maximum=max(e for _,_,e in errors)
    if maximum>=Q('0.00000001'): raise HeadTrimError('coefficient perturbation exceeds local derivation')
    return {'schema':'p4-head-ribbon-parameter-errors/1','status':'exact_outward_coefficient_enclosures',
        'coefficient_error_upper_mm_or_unitless':_up(maximum),
        'coefficient_error_upper_exact':[maximum.numerator,maximum.denominator],
        'records':[{'kind':k,'native_face':f,'coefficient_error_upper_mm_or_unitless':_up(e)} for k,f,e in errors],
        'limitations':['P3 binary64 RA and minor radii are treated as exact initial independent drivers; d and derived B radius use canonical enclosures.',
          'E bounds each coefficient separately; E is not itself a finite edge or face bound.']}


def conditional_head_ribbon_graph_bound(parameters):
    """Apply the explicitly conditional H215 local graph perturbation bound.

    On a shared homotopy between canonical and native parents require:
    distance from each relevant axis/center <100 mm, |y-4|<25 mm,
    rho<50 mm, cos(v)>.25, t>25 mm; preserved outer branches and finite phase graph;
    and y-derivative magnitudes >=7 (sphere), >=70 (cone), >2 (fillet).
    Coefficient E bounds each Cartesian center/direction/radius/slope error.

    Rotating a horizontal frame costs <=200 E in a 100 mm enclosure; torus
    rho derivatives w.r.t. s,d,q are <=4 and t derivatives are <=2. Accounting
    for rotation, centers, radii and frame shift gives <=2000 E at common s,y.
    The sphere/cone/fillet implicit gradients are <300 in that enclosure,
    producing <600000 E residual from that point error; parent coefficients
    contribute <200000 E, accounting for 2E axis rotation, 100 mm lever arm,
    center, radius and cone slope errors. Division by minimum slope 2 and a
    <4 lift plus 2000 E gives a conservative B=4000000 E. These are conditional local
    inequalities, not evidence of actual edge branch selection or topology.
    """
    if parameters.get('schema')!='p4-head-ribbon-parameter-errors/1': raise HeadTrimError('parameter bounds required')
    E=Q(*parameters['coefficient_error_upper_exact'])
    if E<0 or E>=Q('0.00000001'): raise HeadTrimError('unsupported perturbation')
    B=4000000*E
    return {'schema':'p4-head-ribbon-conditional-same-s-graph/1',
        'status':'conditional_on_common_homotopy_and_derivative_bounds',
        'coefficient_error_upper_mm_or_unitless':_up(E),'same_s_graph_upper_mm':_up(B),
        'same_s_graph_upper_exact':[B.numerator,B.denominator],
        'assumptions':['continuous common outer branch and local homotopy with cos(v)>.25 and transverse t>25 mm',
         'distance from each relevant axis/center and radii <100 mm; |y-4|<25 mm and rho<50 mm',
         'implicit boundary y-derivative magnitudes >=7 sphere, >=70 cone, >2 upper fillet',
         'finite loop/phase order and original edge/FIN branch selection match H215; kernel material side not certified'],
        'limitations':['Branch, homotopy, derivative and finite topology premises are not proved by endpoint or FIN samples.',
         'This linear-E same-s bound does not bound square-root A/fillet/step event displacement; see assess_native_fillet_step_corners.']}


def assess_head_chart_guard(parameters, bindings, drivers, h215, strip, event_brackets):
    """Inflate accepted H215 chart margins by the actual C14 perturbation E.

    The P3 chart and event derivative intervals are accepted premises, not
    deduced from native FIN samples. This validates arithmetic guard margins
    for a local continuation under the following independent assumptions:
    (1) every physical event equation and its v derivative change by no more
    than 200000 E throughout the stated v neighborhood and parent homotopy;
    (2) branch/phase correspondence is preserved as in H215. The quantitative
    event perturbation estimate is an explicit premise until separately proved.
    The A/B boundary is the captured class-10 seam, not an asserted intersection
    of linearly interpolated, potentially non-tangent tori.
    """
    if (h215.get('schema')!='p3-head02-whole-head-accepted/1'
        or not h215.get('status','').startswith('H215 accepted')
        or strip.get('schema')!='p3-head02-torus-strip-bound/1'
        or event_brackets.get('schema')!='p3-head02-class11-finite-event-brackets/1'
        or parameters.get('schema')!='p4-head-ribbon-parameter-errors/1'
        or bindings.get('schema')!='p4-head-ribbon-event-bindings/1'):
        raise HeadTrimError('missing accepted H215 chart and event premises')
    if (Q(strip['chart_cos_v_strict_lower'])<Q('.27')
        or Q(strip['chart_metric_y_upper'])>Q('1.38')
        or Q(strip['chart_metric_s_upper'])>Q('5.22')
        or Q(strip['boundary_graph_abs_dy_ds_upper'])>40
        or Q(event_brackets['v_shift_strict_upper_rad'])>Q('0.0000000001')):
        raise HeadTrimError('P3 chart constants are outside the accepted range')
    E=Q(*parameters['coefficient_error_upper_exact'])
    if not 0<=E<Q('0.00000001'): raise HeadTrimError('unsupported E')
    # The P3 physical phase events have strict derivative bounds. Four events
    # are the source-only artificial fillet split; native C14 uses one arc.
    derivatives=[]; special=0
    for record in event_brackets['records']:
        for event in record['events']:
            lo,hi=map(Q,event['strictly_monotone_derivative'])
            if lo<=0<=hi: raise HeadTrimError('P3 event derivative changes sign')
            if event['event']=='F0176_F0235_seam_v0': special+=1
            else: derivatives.append(min(abs(lo),abs(hi)))
    if len(derivatives)!=96 or special!=4 or min(derivatives)<=Q('6.2'):
        raise HeadTrimError('P3 event derivative coverage or strict margin missing')
    for sector in drivers['sectors']:
        if not 8<_q(sector['ra_initial_source_binary64'])<16 or not 0<_q(sector['RA_initial_source_binary64'])<30:
            raise HeadTrimError('unsupported torus dimensions')
        for branch in sector['branches']:
            if not 8<_q(branch['rb_initial_source_binary64'])<16 or max(map(abs,map(Q,branch['d_initial_exact_enclosure'])))>=5:
                raise HeadTrimError('unsupported B radius or offset')
    # For f(v)=R²+q²+d²+2Rq cos(v)+2dq sin(v),
    # |f''| <= 2q(R+|d|) < 1120; 2000 also covers contact.
    # The 200000 E coefficient-to-event-residual/derivative estimate is
    # deliberately recorded as a premise, not asserted from sample geometry.
    window=Q('0.000001'); event_perturb=200000*E
    derivative=min(derivatives)-2000*window-event_perturb
    if derivative<=6 or event_perturb>=derivative*window:
        raise HeadTrimError('event root neighborhood not stable under supplied premise')
    sshift=16*window+500*E
    yshift=40*sshift+400000*E
    point_shift=Q('5.22')*sshift+Q('1.38')*yshift+2000*E
    # H215 gives canonical t>25.57, rho<40 and cos(v)>.27. Point and
    # frame displacements inflate those intervals. q>=8 and cos>.25 on the
    # bootstrap neighborhood imply |d cos(v)/d(s,d,q)|<1 each.
    tlower=Q('25.57')-point_shift-200*E
    rhoupper=40+point_shift+200*E
    coslower=Q('.27')-2*(sshift+500*E)
    # H208's cone denominator is >74. Upper fillet's outer branch satisfies
    # y+18.5>1.3 and dr/dy>=0; source sphere graph derivative is 8.
    sphere_slope=8-10000*E
    cone_slope=74-4*yshift-10000*E
    fillet_slope=2*(Q('1.3')-yshift-2*E)
    if not (tlower>25 and rhoupper<50 and coslower>Q('.25')
            and sphere_slope>7 and cone_slope>70 and fillet_slope>2):
        raise HeadTrimError('homotopy chart margin not retained')
    return {'schema':'p4-head-chart-margin-inflation/1',
        'status':'conditional_margin_arithmetic_not_event_perturbation_proof',
        'p3_physical_event_count':len(derivatives),'p3_artificial_split_event_count':special,
        'p3_event_derivative_abs_lower':_down(min(derivatives)),
        'event_window_rad':_up(window),'event_residual_and_derivative_perturbation_premise_upper':_up(event_perturb),
        'chart_s_inflation_mm':_up(sshift),'chart_y_inflation_mm':_up(yshift),
        'point_displacement_inflation_mm':_up(point_shift),
        'transverse_t_lower_mm':_down(tlower),'rho_upper_mm':_up(rhoupper),
        'cos_v_lower':_down(coslower),'sphere_slope_lower':_down(sphere_slope),
        'cone_slope_lower':_down(cone_slope),'fillet_slope_lower':_down(fillet_slope),
        'limitations':['The 200000 E uniform perturbation of each event residual and its derivative is an explicit unproved premise.',
          'The native A/fillet/step event has a square-root sensitivity; its reported vertex is not on either exact parent intersection circle.',
          'P3 canonical chart bounds and H215 source topology are accepted premises; C14 material orientation and exact FIN/edge/face correspondence are not proved.',
          'This independent-seam continuation does not establish existence or topology of the interpolated solid.']}


def assess_native_fillet_step_corners(capture, support, bindings):
    """Enclose actual upper-fillet/step intersections and native corner gaps.

    A strictly positive lower gap disproves exact coincidence of that reported
    vertex with the reported parent intersection, treating readbacks as exact.
    It does not measure the kernel's tolerant edge representation.
    """
    if bindings.get('schema')!='p4-head-ribbon-event-bindings/1':
        raise HeadTrimError('ribbon event bindings required')
    details={r['detail']['face_tag']:r['detail'] for r in capture['results']}
    ids={r['face_tag_session_only']:r['p3_support_id'] for r in support['faces']}
    inv={int(r['inventory']['tag_session_only']):r['inventory'] for r in capture['selection']}
    adjacency={}
    for f,v in inv.items():
        for e in v['face_edge_tags_session_only']: adjacency.setdefault(int(e),[]).append(f)
    fillets=[f for f in ids if ids[f]=='head.upper_fillet']
    if len(fillets)!=1: raise HeadTrimError('expected one native upper fillet')
    g=details[fillets[0]]['topology']['geometry']; center=tuple(map(_q,g['center'])); axis=tuple(map(_q,g['axis']))
    if g.get('type')!=204 or center[0] or center[2] or axis[0] or axis[2] or not axis[1]:
        raise HeadTrimError('unsupported noncoaxial fillet')
    M=_q(g['major_radius']); q=_q(g['minor_radius']); output=[]
    for row in bindings['faces']:
        if row['role']!='A': continue
        edges=_edges(details[row['native_face']]); le=[int(e) for e,p in row['native_edge_phases'].items() if p=='lower_L_round']
        if len(le)!=1: raise HeadTrimError('expected one native A/fillet edge')
        for vertex in [v for v in _walk(edges[le[0]]) if v.get('type')==9]:
            local=vertex['local_identifier']; point=tuple(map(_q,vertex['geometry']['point']))
            steps=[]
            for e,p in row['native_edge_phases'].items():
                if p!='lower_y_minus16': continue
                if not any(v.get('type')==9 and v.get('local_identifier')==local for v in _walk(edges[int(e)])): continue
                other=next(f for f in adjacency[int(e)] if f!=row['native_face']); steps.append(other)
            if len(steps)!=1 or ids[steps[0]]!='head.Y_head_step': raise HeadTrimError('corner step face not unique')
            plane=details[steps[0]]['topology']['geometry']; n=tuple(map(_q,plane['normal']))
            if plane.get('type')!=209 or n[0] or n[2] or not n[1]: raise HeadTrimError('tilted step unsupported')
            y=_q(plane['point_on_plane'][1]); rad=q*q-(y-center[1])**2
            if rad<0: raise HeadTrimError('reported fillet and step have no real intersection circle')
            rlo,rhi=_sqrt(rad); vlo,vhi=_sqrt(point[0]**2+point[2]**2)
            rings=[(M-rhi,M-rlo),(M+rlo,M+rhi)]
            def separation(interval):
                lo,hi=interval
                return max(Q(0),lo-vhi,vlo-hi)
            lower=min(map(separation,rings))
            output.append({'native_A_face':row['native_face'],'native_fillet_face':fillets[0],
                'native_step_face':steps[0],'native_fillet_edge':le[0],
                'vertex_id_face_local':local,'intersection_sqrt_radicand_mm_upper':_up(rhi),
                'vertex_plane_y_gap_mm_upper':_up(abs(point[1]-y)),
                'vertex_to_either_exact_intersection_circle_lower_mm':_down(lower)})
    if len(output)!=12: raise HeadTrimError('expected twelve A/fillet/step corners')
    return {'schema':'p4-head-fillet-step-tangency-diagnostic/1',
        'status':'native_parent_intersection_vertex_coincidence_not_established',
        'corner_count':len(output),
        'minimum_vertex_to_parent_circle_lower_mm':min(x['vertex_to_either_exact_intersection_circle_lower_mm'] for x in output),
        'maximum_intersection_sqrt_radicand_mm_upper':max(x['intersection_sqrt_radicand_mm_upper'] for x in output),
        'limitations':['The recorded binary64 carriers are treated as exact analytic parents.',
          'A positive gap concerns the reported vertex and exact intersection circles, not measured tolerant kernel edge geometry or FIN error.',
          'Tangency produces square-root, not generally linear, sensitivity to parent coefficient perturbations.'], 'corners':output}


def assess_mapped_fillet_edges(capture, drivers=None):
    """Enclose nominal fillet residuals over the full mapped A/fillet edges."""
    from .nx2506_carrier_bound import read_generator
    from .nx2506_trim_bound import _bernstein_matrix_inverse, _controls, _curve

    # At nominal Y=-16 the R2.5 torus is tangent to the step. Its
    # meridian circle has center (rho,Y)=(30,-18.5).
    major, minor, center_y = Q(30), Q('2.5'), Q('-18.5')
    faces = {row['detail']['face_tag']: row['detail']['topology'] for row in capture['results']}
    edge_parents = {}
    for tag, face in faces.items():
        for edge in _edges({'topology': face}).values():
            edge_parents.setdefault(edge['tag'], []).append((tag, edge))

    def is_fillet(face):
        geometry = face['geometry']
        return (geometry['type'] == 204 and abs(_q(geometry['minor_radius'])-minor)<Q('0.00001')
                and abs(_q(geometry['center'][1])-center_y)<Q('0.00001'))

    result = []
    for paired in edge_parents.values():
        if len(paired) != 2 or not any(is_fillet(faces[k]) for k, _ in paired):
            continue
        torus_face = next((k for k, _ in paired if not is_fillet(faces[k])
                           and faces[k]['geometry']['type'] == 204), None)
        if torus_face is None:
            continue
        edge = next(e for k, e in paired if k == torus_face)
        if edge['geometry_class'] != 11 or edge['geometry']['type'] != 102:
            raise HeadTrimError('expected mapped intersection spline on the A fillet edge')
        curve = _curve(read_generator(edge['geometry']))
        delta = curve['b'] - curve['a']
        cuts = sorted({Q(0), Q(1), *((u-curve['a'])/delta for u in curve['knots']
                                     if min(curve['a'], curve['b']) < u < max(curve['a'], curve['b']))})
        inverse = _bernstein_matrix_inverse(curve['degree'])
        spans = [_controls(curve, a, b, inverse) for a, b in zip(cuts, cuts[1:])]
        y_bounds, rho_bounds, circle_residual = _fillet_span_bounds(spans)
        # |distance to meridian center - minor| = |F| / (distance + minor).
        # Compare in the same azimuth, so this also bounds distance to the
        # untrimmed ideal fillet carrier in 3D.
        row = {'native_edge_tag_session_only': edge['tag'], 'bezier_span_count': len(cuts)-1,
               'y_enclosure_mm': [_down(y_bounds[0]), _up(y_bounds[1])],
               'nominal_fillet_residual_mm2_upper': _up(circle_residual),
               'distance_to_nominal_fillet_carrier_mm_upper': _up(circle_residual/minor)}
        if drivers is not None:
            row.update(_bound_mapped_fillet_graph(spans, faces[torus_face]['geometry'], drivers,
                                                 y_bounds, rho_bounds, circle_residual))
        result.append(row)
    if len(result) != 6:
        raise HeadTrimError('expected six mapped A fillet intersection edges')
    summary = {'schema':'p4-mapped-upper-fillet-edge-residuals/1',
            'curve_mapping_tolerance_mm': capture['curve_tolerance_mm'], 'edge_count': len(result),
            'distance_to_nominal_fillet_carrier_mm_upper': max(
                row['distance_to_nominal_fillet_carrier_mm_upper'] for row in result),
            'scope':'Continuous directed bound from the exported spline images to the untrimmed nominal R2.5 torus.',
            'limitations':['Kernel mapping error, paired A surface, finite trim endpoints and reverse direction are outside this bound.'],
            'edges':result}
    if drivers is not None:
        summary['mapped_to_canonical_finite_hausdorff_upper_mm'] = max(
            row['mapped_to_canonical_finite_hausdorff_upper_mm'] for row in result)
        summary['finite_bound_scope'] = ('Both directions between the six exported spline trim images and '
                                         'the six canonical A/upper-fillet graph intervals.')
        summary['limitations'] = ['Accuracy of the NX conversion and the adjacent filled native faces are separate.']
    return summary


def _fillet_span_bounds(spans):
    from .nx2506_trim_bound import _product

    major, minor, center_y = Q(30), Q('2.5'), Q('-18.5')
    all_y, all_radial, residual = [], [], Q(0)
    for poles in spans:
        x, y, z, weights = zip(*poles)
        if any(w != 1 for w in weights):
            raise HeadTrimError('mapped A fillet edge must be polynomial')
        radial = [xx+zz for xx, zz in zip(_product(x, x), _product(z, z))]
        dy = [v-center_y for v in y]
        # (rho^2+(Y-Yc)^2+M^2-r^2)^2 - (2M rho)^2
        # is the torus implicit polynomial without a square root.
        summed = [rho2+dy2+major**2-minor**2 for rho2, dy2 in zip(radial, _product(dy, dy))]
        elevated_radial = _product(radial, [Q(1)]*len(radial))
        polynomial = [v-4*major**2*r for v, r in zip(_product(summed, summed), elevated_radial)]
        residual = max(residual, max(map(abs, polynomial)))
        all_y.extend(y)
        all_radial.extend(radial)
    radial_sq_lower = min(all_radial)
    rho_bounds = (_sqrt(radial_sq_lower)[0], _sqrt(max(all_radial))[1])
    divisor = radial_sq_lower + major**2 - minor**2 + 2*major*rho_bounds[0]
    if divisor <= 0:
        raise HeadTrimError('could not isolate the outer torus residual factor')
    return (min(all_y), max(all_y)), rho_bounds, residual/divisor


def _fillet_chain_bounds(capture, drivers):
    result = []
    for edge in capture['edges']:
        points = [tuple(map(_q, xyz)) + (Q(1),) for xyz in edge['points_mm']]
        spans = list(zip(points, points[1:]))
        row = _bound_mapped_fillet_graph(spans, {'axis': edge['A_axis']}, drivers,
                                        *_fillet_span_bounds(spans))
        chord_bound = Q(row['mapped_to_canonical_finite_hausdorff_upper_mm'])
        tolerance = _q(edge['chord_tolerance_mm'])
        result.append({'p3_A_face': row['p3_A_face'], 'point_count': len(points),
                       'native_chord_tolerance_mm': edge['chord_tolerance_mm'],
                       'chord_chain_to_canonical_hausdorff_upper_mm': _up(chord_bound),
                       'canonical_to_original_edge_upper_mm': _up(chord_bound+tolerance)})
    if {r['p3_A_face'] for r in result} != {s['A_face'] for s in drivers['sectors']} or len(result)!=6:
        raise HeadTrimError('chord chains do not cover all six P3 A fillet trims')
    return result


def assess_fillet_chord_chains(capture, drivers):
    """Compare chord chains read from original NX edges to canonical fillet trims."""
    result = _fillet_chain_bounds(capture, drivers)
    return {'schema': 'p4-native-fillet-chord-comparison/1',
            'canonical_to_original_edge_upper_mm': max(r['canonical_to_original_edge_upper_mm'] for r in result),
            'scope': ('Stable continuous bound in the canonical-to-original direction using NX '
                      'UF_MODL_ask_curve_points maximum chord-to-curve distance.'),
            'limitations': ['The available chord contract does not bound the opposite direction or the filled faces.'],
            'edges': result}


def assess_fillet_facet_boundary(capture, drivers):
    """Bound both directions using the documented NX facet-edge distance."""
    if (capture.get('schema') != 'p4-native-fillet-facets/1'
            or capture.get('status') != 'NX_TESSELLATION_WITHOUT_ERRORS'
            or capture.get('disk_copy_unchanged') is not True):
        raise HeadTrimError('valid original NX boundary tessellation required')
    for edge in capture['edges']:
        if edge['max_midpoint_deviation_mm'] > edge['chord_tolerance_mm']:
            raise HeadTrimError('original edge evaluator contradicts the tessellation distance')
    result = _fillet_chain_bounds(capture, drivers)
    for edge in result:
        # The facet distance applies between each full solid edge segment
        # and its corresponding boundary facet edge. The existing chain
        # comparison covers both complete finite images.
        edge['original_to_canonical_edge_upper_mm'] = edge['canonical_to_original_edge_upper_mm']
    maximum = max(row['original_to_canonical_edge_upper_mm'] for row in result)
    limit = Q('0.00025')
    return {'schema': 'p4-native-fillet-facet-comparison/1',
            'status': 'within_limit' if Q(maximum) <= limit else 'bound_exceeds_limit',
            'distance_limit_mm': float(limit),
            'canonical_to_original_edge_upper_mm': maximum,
            'original_to_canonical_edge_upper_mm': maximum,
            'facet_count': capture['facet_count'],
            'maximum_midpoint_deviation_mm': max(e['max_midpoint_deviation_mm'] for e in capture['edges']),
            'scope': ('Six original finite A/upper-fillet edges in NX2506 C14. Each corresponding '
                      'facet boundary chain is paired by the original edge endpoints and its closed loop.'),
            'basis': ('UF_FACET_tessellation_parameters_s.curve_dist_tolerance is the maximum distance '
                      'between a boundary facet edge and its represented solid curve segment. Sum it '
                      'with the rational bidirectional canonical-to-chain bound.'),
            'limitations': ['The distance bound applies to these six edges. Surface patch interiors, '
                            'other solid edges and the overall part remain separate.'],
            'edges': result}


def _bound_mapped_fillet_graph(spans, native_torus, drivers, y_bounds, rho_bounds, fillet_residual):
    from .nx2506_trim_bound import _product

    point = spans[0][0]
    matches = []
    for sector in drivers['sectors']:
        if _direction_error(native_torus['axis'], sector['axis_source']) > Q('0.00000001'):
            continue
        frame = _unit_interval(sector['axis_source'])
        a, b = (sum(frame[i])/2 for i in (0, 2))
        if b*point[0]-a*point[2] > 25:
            matches.append((sector, frame, a, b))
    if len(matches) != 1:
        raise HeadTrimError('could not bind the mapped edge to a unique positive-transverse A chart')
    sector, frame, a, b = matches[0]
    major, minor = (_q(sector[k]) for k in ('RA_initial_source_binary64', 'ra_initial_source_binary64'))
    s_limit, t_lower = Q('6.1'), Q('28.5')
    w_lower, y_shift_upper = Q('6.4'), Q('20.8')
    # On the outer A graph, w=sqrt(q²-s²), rho=R+w and
    # t=sqrt(rho²-(Y-4)²). The collar covers the whole finite fillet phase.
    if not (Q('28.9') < major < 29 and minor**2-s_limit**2 > w_lower**2
            and major+minor < 38 and (major+w_lower)**2-y_shift_upper**2 > t_lower**2
            and Q('-16.79') < y_bounds[0] <= y_bounds[1] < Q('-15.91')):
        raise HeadTrimError('mapped fillet is outside the validated analytic collar')
    # For world r=sqrt(s²+t²) and F=(r-30)²+(Y+18.5)²-2.5²,
    # r_Y=-(Y-4)/r and r_s=-R*s/(r*w). These give F_Y>1 and |F_s|<20.
    if not (s_limit**2+38**2 < 39**2
            and 2*Q('1.7')-2*(30-t_lower)*y_shift_upper/t_lower > 1
            and 2*9*29*s_limit/(t_lower*w_lower) < 20
            and 38*s_limit/(t_lower*w_lower) < 2 and y_shift_upper < t_lower):
        raise HeadTrimError('fillet root derivative collar could not be bounded')
    axis_error = max((frame[i][1]-frame[i][0])/2 for i in (0, 2))
    chart_error, first_s, last_s, direction = Q(0), None, None, None
    for poles in spans:
        if any(abs(x)+abs(z) >= 100 for x, _, z, _ in poles):
            raise HeadTrimError('mapped edge outside the bounded frame enclosure')
        s = [a*x+b*z for x, _, z, _ in poles]
        t = [b*x-a*z for x, _, z, _ in poles]
        dy = [y-4 for _, y, _, _ in poles]
        if max(map(abs, s)) >= s_limit or min(t) <= t_lower or max(t) >= 40:
            raise HeadTrimError('mapped edge leaves the positive-transverse chart')
        if last_s is not None and last_s != s[0]:
            raise HeadTrimError('mapped spline spans do not join')
        if first_s is None:
            first_s = s[0]
            direction = 1 if s[-1] > s[0] else -1
        if any(direction*(second-first) <= 0 for first, second in zip(s, s[1:])):
            raise HeadTrimError('projected mapped edge is not strictly monotone')
        last_s = s[-1]
        radial = [tt+yy for tt, yy in zip(_product(t, t), _product(dy, dy))]
        total = [r+ss+major**2-minor**2 for r, ss in zip(radial, _product(s, s))]
        numerator = [u-4*major**2*v for u, v in zip(_product(total, total),
                                                    _product(radial, [Q(1)]*len(radial)))]
        lower, upper = _sqrt(min(radial))[0], _sqrt(max(radial))[1]
        denominator = min(total)+2*major*lower
        if denominator <= 0 or lower-major+w_lower <= 0:
            raise HeadTrimError('could not isolate the positive A-torus factor')
        radial_error = max(map(abs, numerator))/(denominator*(lower-major+w_lower))
        chart_error = max(chart_error, radial_error*(upper+38)/(min(t)+t_lower))
    # The exact normalized axes enclose the rational comparison frame.
    chart_error += 200*axis_error
    # At Y=-16, world r=30. Substitute these into the A torus equation
    # to solve the two exact projected junction endpoints ±s.
    radial_sq = Q(30)**2+Q(20)**2
    radial = (radial_sq+major**2-minor**2)/(2*major)
    event = _sqrt(radial_sq-radial**2)
    s_lo, s_hi = sorted((first_s, last_s))
    endpoint_shift = max(abs(v-e) for v in (-s_lo, s_hi) for e in event)
    if max(event[1], abs(s_lo), abs(s_hi)) >= s_limit:
        raise HeadTrimError('fillet event leaves the validated chart')
    # Affinely pair the projected intervals. Hold y fixed while shifting s,
    # then use the strictly monotone fillet equation to correct y.
    rho_lo, rho_hi = rho_bounds
    radial_gradient = 2*(max(abs(rho_lo-30), abs(rho_hi-30))+chart_error)
    y_error = fillet_residual+radial_gradient*chart_error+20*endpoint_shift
    if y_error >= Q('0.01'):
        raise HeadTrimError('fillet root could leave the y collar')
    bound = chart_error+3*endpoint_shift+2*y_error
    return {'p3_A_face': sector['A_face'], 'projected_endpoint_shift_upper_mm': _up(endpoint_shift),
            'mapped_to_A_chart_upper_mm': _up(chart_error),
            'fillet_graph_y_correction_upper_mm': _up(y_error),
            'mapped_to_canonical_finite_hausdorff_upper_mm': _up(bound)}
