"""Check complete same-session directed loops captured from the C14 BREP."""
from collections import Counter, defaultdict


def assess_directed_loops(capture):
    """The UF original fins orient edge vertex order (uf_brep_types.h)."""
    if (capture.get("scope")!="all" or capture.get("status")!="PROBES_RETURNED"
            or not capture.get("disk_copy_unchanged")):
        raise ValueError("complete unchanged C14 capture is required")
    uses=defaultdict(list)
    vertices={}
    face_graph=defaultdict(set)
    loop_count=0
    observations=[]
    for row in capture["results"]:
        detail=row["detail"]
        topology=detail["topology"]
        number=detail["face_tag"]
        if detail["outcome"]!="CLEAN_TRACE" or not detail["edge_coverage_complete"]:
            raise ValueError("native face read did not complete cleanly")
        if topology["type"]!=5 or topology["geometry_sense"] not in (-1,1):
            raise ValueError("unexpected BREP face or material orientation")
        for loop in topology["children"]:
            loop_count+=1
            loop=loop["child"]
            if loop["type"]!=6 or not loop["children"]:
                raise ValueError("missing BREP face loop")
            corners=[]
            order=[]
            for member in loop["children"]:
                fin=member["child"]
                if fin["type"]!=7 or len(fin["children"])!=1:
                    raise ValueError("expected exactly one edge per fin")
                link,=fin["children"]
                edge=link["child"]
                direction=link["orientation"]
                if direction not in (-1,1) or member["orientation"] not in (0,direction):
                    raise ValueError("inconsistent loop and fin orientation")
                ids=[]
                for occurrence in edge["children"]:
                    q=occurrence["child"]
                    if q["type"]!=9:
                        raise ValueError("expected an original BREP vertex")
                    key=q["local_identifier"]
                    point=q["geometry"]["point"]
                    if vertices.setdefault(key,point)!=point:
                        raise ValueError("same-session vertex identity changed position")
                    ids.append(key)
                if len(ids)==2:
                    if direction<0:
                        ids.reverse()
                    corners.append(tuple(ids))
                elif not ids and len(loop["children"])==1 and edge["geometry"]["type"]=="circular_evaluator" and edge["geometry"]["is_periodic"]:
                    # Closed full ring has no vertex entity. Its loop is
                    # continuous by the periodic original evaluator.
                    pass
                else:
                    raise ValueError("nonperiodic fin has no ordered vertex pair")
                order.append(edge["tag"])
                uses[edge["tag"]].append((number,direction,edge["geometry_class"]))
            if corners and any(b!=corners[(i+1)%len(corners)][0] for i,(_,b) in enumerate(corners)):
                raise ValueError("fin vertex order does not close")
            observations.append({"face_tag_session_only":number,"loop_identifier":loop["local_identifier"],
                                 "edge_order_session_only":order,"original_vertex_order_closes":True})
    for edge,rows in uses.items():
        if len(rows)!=2 or rows[0][0]==rows[1][0] or rows[0][1]+rows[1][1]!=0 or rows[0][2]!=rows[1][2]:
            raise ValueError("two incident faces do not use the edge oppositely")
        a,b=rows[0][0],rows[1][0]
        face_graph[a].add(b)
        face_graph[b].add(a)
    visited=set()
    queue=[next(iter(face_graph))]
    while queue:
        key=queue.pop()
        if key not in visited:
            visited.add(key)
            queue.extend(face_graph[key]-visited)
    if len(uses)!=capture["edge_count"] or len(visited)!=capture["face_count"]:
        raise ValueError("native directed topology coverage is incomplete")
    return {"schema":"p4-directed-native-loop-coverage/1","face_count":len(visited),
            "edge_count":len(uses),"vertex_identifier_count":len(vertices),"closed_loop_count":loop_count,
            "edge_classes":dict(Counter(str(rows[0][2]) for rows in uses.values())),
            "scope":"All reported C14 face loops have closed ordered vertices or a periodic edge; every shared edge has opposite fin traversal, valid in this same-session BREP.",
            "remaining":"Does not identify the corresponding P3 finite domain or establish dimensional conformity of tolerant FINs.",
            "loops":observations,"execution_approved":False}
