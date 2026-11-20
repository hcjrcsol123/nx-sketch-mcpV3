"""Bind the C14 upper-head directed loops to the previously accepted P3 charts."""
from collections import Counter, defaultdict

from .nx2506_roll_s7_bound import face_edges


def collapse(seq):
    result=[]
    for name in seq:
        if not result or result[-1]!=name:
            result.append(name)
    if len(result)>1 and result[0]==result[-1]:
        result.pop()
    return result


def match_cycle(a,b):
    return len(a)==len(b) and any((a+a)[k:k+len(a)]==b for k in range(len(a)))


def build_source_cycles(source_faces,records,multipliers,map_neighbor):
    """Join source hemisphere charts by cancelling their opposite internal uses."""
    uses=[]
    parents={}
    def find(k):
        parents.setdefault(k,k)
        while parents[k]!=k:
            k=parents[k]
        return k
    def merge(a,b):
        parents[find(a)]=find(b)
    for f in source_faces:
        for i,loop in enumerate(records[f]["cycles"]):
            entries=loop["edges_in_arbitrary_cycle"]
            key=f+":"+str(i)
            sense=multipliers.get(key)
            if sense not in (-1,1):
                if len(source_faces)!=1:
                    raise ValueError("a merged P3 source chart has unproved loop orientation")
                # F0196's outer ring may be only an unoriented circle.
                if f!="F0196":
                    raise ValueError("P3 source face has unanchored orientation")
                sense=1
            for j,edge in enumerate(entries):
                target,=[n for n in edge["neighbor_faces"] if n!=f]
                a,b=(key,j),(key,(j+1)%len(entries))
                sign=(1 if edge["journal_endpoint_direction"]=="forward" else -1)*sense
                if sense<0:
                    a,b=b,a
                uses.append((edge["edge"],target,sign,a,b))
    buried=defaultdict(list)
    boundary=[]
    for e,n,sign,a,b in uses:
        if n in source_faces:
            buried[e].append((sign,a,b))
        else:
            boundary.append((a,b,map_neighbor(n)))
    for uses in buried.values():
        (g,a,b),(h,c,d)=uses
        if g+h!=0:
            raise ValueError("opposite directed uses expected at the merged P3 chart seam")
        merge(a,d)
        merge(b,c)
    graph={}
    for a,b,n in boundary:
        a,b=find(a),find(b)
        if a in graph:
            raise ValueError("multiple outgoing boundary uses in merged P3 chart")
        graph[a]=(b,n)
    result=[]
    while graph:
        first=next(iter(graph))
        labels=[]
        a=first
        while True:
            a,n=graph.pop(a)
            labels.append(n)
            if a==first:
                break
        result.append(collapse(labels))
    return result


def assess_directed_head_counterparts(capture,support,ribbons,sphere_arcs,source_graphs,
                                      orientations,lower_orientations,propagated,h215,regions):
    names={e["face_tag_session_only"]:e["p3_support_id"] for e in support["faces"]}
    faces={q["detail"]["face_tag"]:q["detail"]["topology"] for q in capture["results"]}
    adjacent=defaultdict(set)
    for tag,face in faces.items():
        for edge in face_edges(face):
            adjacent[edge["tag"]].add(tag)
    actual={r["native_face"]:r["p3_face"] for r in ribbons["faces"]}
    actual.update({r["native_sphere_face"]:r["p3_source_face"] for r in sphere_arcs["arcs"]})
    actual.update({k:"F0196" for k,n in names.items() if n=="stock.s20"})
    # Upper fillet and R40 have source seams that split a common carrier.
    upper_sources={r["face"] for r in regions["records"] if r["target"].get("carrier")=="R2.5"}
    r40=set(h215["r40_union_source_ids"])
    if len(upper_sources)!=2 or len(r40)!=2:
        raise ValueError("P3 merged carrier scope changed")
    for name,label in (("head.upper_fillet","upper_fillet_union"),("head.R40","r40_union"),("stock.s19","mouth_outer_stock")):
        ids=[i for i,n in names.items() if n==name]
        if len(ids)!=1:
            raise ValueError("C14 merged support no longer unique")
        actual[ids[0]]=label

    graph_labels={"head.cone":"cone_face","head.Y_head_step":"plane"}
    for id,n in names.items():
        if n not in graph_labels:
            continue
        nearby=set()
        for e in face_edges(faces[id]):
            other,=adjacent[e["tag"]]-{id}
            if names[other].endswith((".A_piece",".B_piece")):
                nearby.add(actual[other])
        field=graph_labels[n]
        matches=[row[field] for row in source_graphs[field]["records"]
                 if {piece[key] for piece in row["piecewise_AB_boundaries"] for key in ("A_face","B_face")}==nearby]
        if len(matches)!=1:
            raise ValueError("C14 head complement does not match a unique H215 finite graph")
        actual[id]=matches[0]
    records={e["face"]:e for group in (orientations,lower_orientations) for e in group["records"]}
    multipliers={r["face_cycle"]:r["multiplier"] for r in propagated["records"]}
    target_roles={"head.cone","head.R32","head.Y_head_step","head.upper_fillet","stock.s20"}
    result=[]
    for tag,n in names.items():
        if n not in target_roles:
            continue
        scope=upper_sources if n=="head.upper_fillet" else {actual[tag]}
        def neighbor_label(name):
            if name in r40:
                return "r40_union"
            if name in upper_sources:
                return "upper_fillet_union"
            if name not in actual.values():
                if n=="stock.s20":
                    return "mouth_outer_stock"
                raise ValueError("unbound source face incidence")
            return name
        expected=build_source_cycles(scope,records,multipliers,neighbor_label)
        native=[]
        for loop in faces[tag]["children"]:
            ids=[]
            for member in loop["child"]["children"]:
                edge=member["child"]["children"][0]["child"]
                other,=adjacent[edge["tag"]]-{tag}
                ids.append(actual[other])
            native.append(collapse(ids))
        if len(native)!=len(expected):
            raise ValueError("C14/P3 head complement loop multiplicity differs")
        available=expected[:]
        for loop in native:
            matches=[i for i,c in enumerate(available) if match_cycle(loop,c)]
            if len(matches)!=1:
                raise ValueError(f"directed loop does not pair for {n} {actual[tag]}; native {native!r}; P3 {expected!r}")
            available.pop(matches[0])
        result.append({"face_tag_session_only":tag,"p3_carrier":n,
                       "p3_source_faces":sorted(scope),"oriented_neighbor_loops":native})
    if len(result)!=20:
        raise ValueError("expected all 20 finite complementary head faces")
    return {"schema":"p4-head-directed-counterparts/1","face_count":len(result),"faces":result,
            "basis":"Same-session C14 ordered loops match accepted P3 geometric-neighbor cycles up to cyclic shift, with no reversal. P3 internal seams between merged carrier patches are removed by opposite directed uses.",
            "scope":"Combinatorial directed correspondence; dimensional native/ideal branch bounds are separate.",
            "execution_approved":False}
