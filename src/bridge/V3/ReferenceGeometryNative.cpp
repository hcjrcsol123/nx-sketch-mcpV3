// NX-process-only, read-only prototype. Never call with a tag from another session.
#include <uf.h>
#include <uf_brep.h>
#include <uf_csys.h>
#include <uf_modl.h>
#include <uf_part.h>
#include <uf_eval.h>
#include <stdint.h>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <locale>
#include <new>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
const int kMaxElements = 100000;
const size_t kMaxJson = 2u * 1024u * 1024u;
const int kSkipped = -2147483647;
const size_t kMaxEvents = 4096;

struct ProbeEvent {
    const char *stage; tag_t tag; int type; int before, after, rc;
    bool called, has_rc, cleanup;
};

// Diagnostic probes execute the same traversal and native calls, but geometry
// text is discarded so it cannot crowd out the bounded event evidence.
struct DiscardBuffer : std::streambuf {
    std::streamsize xsputn(const char *, std::streamsize n) override { return n; }
    int_type overflow(int_type ch) override { return traits_type::not_eof(ch); }
    pos_type seekoff(off_type, std::ios_base::seekdir, std::ios_base::openmode) override { return pos_type(0); }
};

struct Context {
    UF_BREP_options_t options;
    UF_BREP_mapping_t mapping;
    int tokens[4]; double data[4];
    UF_BREP_geom_type_t source[2], extracted[2];
    bool incomplete, cleanup_failed, native_failure;
    int nodes;
    bool diagnostic, stopped, dirty_seen, event_overflow, full_detail, geometry_overflow;
    tag_t part_tag;
    int first_dirty;
    const char *failure_reason;
    std::vector<ProbeEvent> events;
    std::vector<uint32_t> edge_tags;
    std::vector<uint8_t> edge_kinds;
    std::vector<bool> edge_seen;
    Context(double curve, double surface, tag_t part = 0) : incomplete(false), cleanup_failed(false), native_failure(false), nodes(0), diagnostic(part != 0), stopped(false), dirty_seen(false), event_overflow(false), full_detail(false), geometry_overflow(false), part_tag(part), first_dirty(0), failure_reason(NULL) {
        if (diagnostic) events.reserve(kMaxEvents);
        tokens[0] = UF_BREP_FINSP_OPTION; tokens[1] = UF_BREP_EDGE3D_OPTION;
        tokens[2] = UF_BREP_CURVE_DIST_OPTION; tokens[3] = UF_BREP_BSURF_DIST_OPTION;
        data[0] = 1; data[1] = 1; data[2] = curve; data[3] = surface;
        options.count = 4; options.options = tokens; options.opt_data = data;
        source[0] = UF_BREP_BLEND_GEOM; extracted[0] = UF_BREP_BSURFACE_GEOM;
        source[1] = UF_BREP_INTERSECTION_GEOM; extracted[1] = UF_BREP_SPLINE_GEOM;
        mapping.count = 2; mapping.source = source; mapping.extracted = extracted;
    }
};

// Separate topology budget keeps space available for a complete event trace.
struct LimitedBuffer : std::streambuf {
    Context& c; std::string value;
    explicit LimitedBuffer(Context& context) : c(context) { value.reserve(64 * 1024); }
    std::streamsize xsputn(const char *s, std::streamsize n) override {
        if (n < 0 || value.size() + static_cast<size_t>(n) > 900u * 1024u) {
            c.geometry_overflow = c.native_failure = c.stopped = true; c.failure_reason = "geometry_output_limit"; return n;
        }
        if (!c.geometry_overflow) value.append(s, static_cast<size_t>(n));
        return n;
    }
    int_type overflow(int_type ch) override {
        if (!traits_type::eq_int_type(ch, traits_type::eof())) { char v = traits_type::to_char_type(ch); xsputn(&v, 1); }
        return traits_type::not_eof(ch);
    }
    pos_type seekoff(off_type, std::ios_base::seekdir, std::ios_base::openmode) override { return pos_type(value.size()); }
};

// The caller independently establishes that part_tag is the loaded bound part.
// UF_PART_is_modified has no error channel and FALSE also covers an unloaded part.
template<class F> int probe(Context& c, const char *stage, tag_t tag, int type, bool cleanup, bool has_rc, F fn) {
    if (!c.diagnostic) return fn();
    if (c.stopped && !cleanup) return kSkipped;
    // Reserve slots for mandatory cleanups once ordinary probing reaches its cap.
    if (!cleanup && c.events.size() >= kMaxEvents - 8) {
        c.event_overflow = true; c.native_failure = true; c.stopped = true; return kSkipped;
    }
    ProbeEvent e = {stage, tag, type, UF_PART_is_modified(c.part_tag) ? 1 : 0, -1, kSkipped, false, has_rc, cleanup};
    if (e.before && !c.dirty_seen) { c.dirty_seen = true; c.first_dirty = static_cast<int>(c.events.size() + 1); c.stopped = true; }
    if (cleanup || !c.stopped) {
        e.called = true; e.rc = fn();
        e.after = UF_PART_is_modified(c.part_tag) ? 1 : 0;
        if (e.after && !c.dirty_seen) { c.dirty_seen = true; c.first_dirty = static_cast<int>(c.events.size() + 1); c.stopped = true; }
        if (has_rc && e.rc != 0) { c.native_failure = true; c.stopped = true; c.failure_reason = "native_call_failed"; }
    }
    if (c.events.size() < kMaxEvents) c.events.push_back(e);
    else { c.event_overflow = true; c.native_failure = true; c.stopped = true; }
    return e.called ? e.rc : kSkipped;
}

void number(std::ostream& out, double v, Context& c) {
    if (out.tellp() > static_cast<std::streamoff>(kMaxJson)) throw std::length_error("detail output limit");
    if (!std::isfinite(v)) { out << "null"; c.incomplete = true; if (c.full_detail) c.native_failure = c.stopped = true; }
    else out << std::setprecision(17) << v;
}
void array(std::ostream& out, const double *v, int n, Context& c) {
    out << '[';
    if (!v || n < 0 || n > kMaxElements) { c.incomplete = true; if (c.full_detail) c.native_failure = c.stopped = true; }
    else for (int i = 0; i < n; ++i) { if (i) out << ','; number(out, v[i], c); }
    out << ']';
}
void matrix(std::ostream& out, tag_t tag, Context& c) {
    double m[9] = {0}; int rc = probe(c, "UF_CSYS_ask_matrix_values", tag, 0, false, true, [&]() { return UF_CSYS_ask_matrix_values(tag, m); });
    out << "\"matrix_tag\":" << tag << ",\"matrix_rc\":" << rc << ",\"matrix\":";
    if (rc) { out << "null"; c.incomplete = true; } else array(out, m, 9, c);
}
void geometry(std::ostream& out, const UF_BREP_geometry_t *g, Context& c, int depth) {
    if (!g || depth > (c.full_detail ? 4 : 8)) { out << "null"; c.incomplete = true; if (c.full_detail) c.native_failure = c.stopped = true; return; }
    out << "{\"type\":" << static_cast<int>(g->type);
    switch (g->type) {
    case UF_BREP_PLANE_GEOM:
        out << ",\"point_on_plane\":"; array(out, g->geom.plane.pt_on_plane, 3, c);
        out << ",\"normal\":"; array(out, g->geom.plane.normal, 3, c);
        out << ",\"u0_ref_direction\":"; array(out, g->geom.plane.u0_ref_direc, 3, c); break;
    case UF_BREP_CYLINDER_GEOM:
        out << ",\"point_on_axis\":"; array(out, g->geom.cylinder.pt_on_axis, 3, c);
        out << ",\"axis\":"; array(out, g->geom.cylinder.axis, 3, c);
        out << ",\"u0_ref_direction\":"; array(out, g->geom.cylinder.u0_ref_direc, 3, c);
        out << ",\"radius\":"; number(out, g->geom.cylinder.radius, c); break;
    case UF_BREP_CONE_GEOM:
        out << ",\"point_at_apex\":"; array(out, g->geom.cone.pt_at_apex, 3, c);
        out << ",\"axis\":"; array(out, g->geom.cone.axis, 3, c);
        out << ",\"u0_ref_direction\":"; array(out, g->geom.cone.u0_ref_direc, 3, c);
        out << ",\"half_apex_angle\":"; number(out, g->geom.cone.half_apex_angle, c); break;
    case UF_BREP_POINT_GEOM:
        out << ",\"point\":"; array(out, g->geom.point, 3, c); break;
    case UF_BREP_LINE_GEOM:
        out << ",\"start\":"; array(out, g->geom.line.start_point, 3, c);
        out << ",\"end\":"; array(out, g->geom.line.end_point, 3, c); break;
    case UF_BREP_ARC_GEOM:
        out << ','; matrix(out, g->geom.arc.matrix_tag, c);
        out << ",\"center\":"; array(out, g->geom.arc.arc_center, 3, c);
        out << ",\"radius\":"; number(out, g->geom.arc.radius, c);
        out << ",\"start\":"; number(out, g->geom.arc.start_angle, c);
        out << ",\"end\":"; number(out, g->geom.arc.end_angle, c); break;
    case UF_BREP_SPLINE_GEOM: {
        const UF_BREP_spline_t& s = g->geom.spline;
        out << ",\"num_poles\":" << s.num_poles << ",\"order\":" << s.order
            << ",\"rational\":" << (s.is_rational ? "true" : "false");
        if (s.num_poles <= 0 || s.order <= 0 || s.num_poles > kMaxElements / 4 || s.order > kMaxElements - s.num_poles || !s.knots || !s.poles) {
            c.incomplete = true; if (c.full_detail) c.native_failure = c.stopped = true;
            out << ",\"data_error\":\"invalid_or_excessive_spline\""; break;
        }
        out << ",\"knots\":"; array(out, s.knots, s.num_poles + s.order, c);
        out << ",\"weighted_poles_flat_xyzw\":"; array(out, &s.poles[0][0], s.num_poles * 4, c);
        out << ",\"start\":"; number(out, s.start_param, c);
        out << ",\"end\":"; number(out, s.end_param, c); break;
    }
    case UF_BREP_TORUS_GEOM:
        out << ",\"center\":"; array(out, g->geom.torus.center, 3, c);
        out << ",\"axis\":"; array(out, g->geom.torus.axis, 3, c);
        out << ",\"u0_ref_direction\":"; array(out, g->geom.torus.u0_ref_direc, 3, c);
        out << ",\"major_radius\":"; number(out, g->geom.torus.major_radius, c);
        out << ",\"minor_radius\":"; number(out, g->geom.torus.minor_radius, c); break;
    case UF_BREP_SPHERE_GEOM: {
        const UF_BREP_sphere_t& sphere = g->geom.sphere;
        bool valid = std::isfinite(sphere.radius) && sphere.radius > 0;
        for (int i = 0; i < 3; ++i)
            valid = valid && std::isfinite(sphere.center[i]) && std::isfinite(sphere.axis[i]) && std::isfinite(sphere.u0_ref_direc[i]);
        double axis_length = std::hypot(sphere.axis[0], std::hypot(sphere.axis[1], sphere.axis[2]));
        double ref_length = std::hypot(sphere.u0_ref_direc[0], std::hypot(sphere.u0_ref_direc[1], sphere.u0_ref_direc[2]));
        valid = valid && std::isfinite(axis_length) && axis_length > 0 && std::isfinite(ref_length) && ref_length > 0;
        if (valid) {
            double a[3], r[3];
            for (int i = 0; i < 3; ++i) { a[i] = sphere.axis[i] / axis_length; r[i] = sphere.u0_ref_direc[i] / ref_length; }
            double cross[3] = {a[1]*r[2]-a[2]*r[1], a[2]*r[0]-a[0]*r[2], a[0]*r[1]-a[1]*r[0]};
            valid = std::hypot(cross[0], std::hypot(cross[1], cross[2])) > 0;
        }
        if (!valid) {
            out << ",\"invalid\":true"; c.incomplete = c.native_failure = true;
            if (c.diagnostic) c.stopped = true;
            c.failure_reason = "invalid_sphere_data";
            break;
        }
        out << ",\"center\":"; array(out, sphere.center, 3, c);
        out << ",\"axis\":"; array(out, sphere.axis, 3, c);
        out << ",\"u0_ref_direction\":"; array(out, sphere.u0_ref_direc, 3, c);
        out << ",\"radius\":"; number(out, sphere.radius, c);
        out << ",\"scope\":\"underlying_sphere_only\",\"source_frame\":\"UF_BREP_native_unverified\"";
        break;
    }
    case UF_BREP_REVOLVE_GEOM:
        out << ",\"point_on_axis\":"; array(out, g->geom.revolve.pt_on_axis, 3, c);
        out << ",\"axis\":"; array(out, g->geom.revolve.rot_axis, 3, c);
        out << ",\"generator\":"; geometry(out, g->geom.revolve.generator, c, depth + 1); break;
    case UF_BREP_EXTRUDE_GEOM:
        out << ",\"direction\":"; array(out, g->geom.extrude.direction, 3, c);
        out << ",\"generator\":"; geometry(out, g->geom.extrude.generator, c, depth + 1); break;
    default:
        out << ",\"unsupported\":true"; c.incomplete = true; if (c.full_detail) c.native_failure = c.stopped = true; break;
    }
    out << '}';
}
void states(std::ostream& out, int n, UF_BREP_state_t *s, Context& c) {
    out << '[';
    if (n < 0 || n > kMaxElements || (n && !s)) {
        c.incomplete = true; if (c.full_detail) { c.native_failure = c.stopped = true; c.failure_reason = "invalid_native_states"; }
    }
    else for (int i = 0; i < n; ++i) {
        if (i) out << ',';
        out << "{\"code\":" << s[i].state_code << ",\"flag\":" << s[i].flag
            << ",\"tag\":" << s[i].ug_tag << ",\"value\":";
        array(out, s[i].value, 3, c); out << '}';
    }
    if (n) c.incomplete = true;
    out << ']';
}
struct StateOwner {
    UF_BREP_state_t *p; Context& c; tag_t tag;
    StateOwner(Context& context, tag_t object) : p(NULL), c(context), tag(object) {}
    void release() { if (p) { UF_BREP_state_t *old = p; p = NULL; probe(c, "UF_free_states", tag, 0, true, false, [&]() { UF_free(old); return 0; }); } }
    ~StateOwner() { release(); }
};
struct TreeOwner {
    UF_BREP_topology_t *p; Context& c; tag_t tag;
    TreeOwner(Context& context, tag_t object) : p(NULL), c(context), tag(object) {}
    int release() { if (!p) return 0; UF_BREP_topology_t *old = p; p = NULL;
        int rc = probe(c, "UF_BREP_release_topology", tag, 0, true, true, [&]() { return UF_BREP_release_topology(old, NULL); });
        if (rc) { c.cleanup_failed = true; c.stopped = c.diagnostic; } return rc; }
    ~TreeOwner() { release(); }
};
struct GeometryOwner {
    UF_BREP_geometry_t value; Context& c; tag_t tag; int topo_type;
    GeometryOwner(Context& context, tag_t object, int type) : c(context), tag(object), topo_type(type) { std::memset(&value, 0, sizeof value); }
    int release() { if (value.type == UF_BREP_GEOM_ALL) return 0;
        int rc = probe(c, "UF_BREP_free_geometry_data", tag, topo_type, true, true, [&]() { return UF_BREP_free_geometry_data(&value, NULL); });
        value.type = UF_BREP_GEOM_ALL;
        if (rc) { c.cleanup_failed = true; c.stopped = c.diagnostic; } return rc; }
    ~GeometryOwner() { release(); }
};

struct EvaluatorOwner {
    UF_EVAL_p_t p; Context& c; tag_t tag; int topo_type;
    EvaluatorOwner(Context& context, tag_t object, int type) : p(NULL), c(context), tag(object), topo_type(type) {}
    void release() { if (!p) return; UF_EVAL_p_t old = p; p = NULL;
        int rc = probe(c, "UF_EVAL_free", tag, topo_type, true, true, [&]() { return UF_EVAL_free(old); });
        if (rc) { c.cleanup_failed = c.native_failure = c.stopped = true; }
    }
    ~EvaluatorOwner() { release(); }
};

void circular_geometry(std::ostream& out, const UF_BREP_topology_t *t, Context& c) {
    EvaluatorOwner ev(c, t->tag, static_cast<int>(t->type));
    logical is_arc = false, is_periodic = false; double limits[2] = {0}; UF_EVAL_arc_t arc;
    std::memset(&arc, 0, sizeof arc);
    int rc = probe(c, "UF_EVAL_initialize_2", t->tag, static_cast<int>(t->type), false, true,
                   [&]() { return UF_EVAL_initialize_2(t->tag, &ev.p); });
    if (rc == 0 && !ev.p) { c.native_failure = c.stopped = true; c.failure_reason = "null_evaluator"; }
    if (!c.stopped) {
        rc = probe(c, "UF_EVAL_is_arc", t->tag, static_cast<int>(t->type), false, true,
                   [&]() { return UF_EVAL_is_arc(ev.p, &is_arc); });
        if (rc == 0 && !is_arc) { c.native_failure = c.stopped = true; c.failure_reason = "edge_not_evaluator_arc"; }
    }
    if (!c.stopped) probe(c, "UF_EVAL_ask_limits", t->tag, static_cast<int>(t->type), false, true,
                          [&]() { return UF_EVAL_ask_limits(ev.p, limits); });
    if (!c.stopped) probe(c, "UF_EVAL_is_periodic", t->tag, static_cast<int>(t->type), false, true,
                          [&]() { return UF_EVAL_is_periodic(ev.p, &is_periodic); });
    if (!c.stopped) probe(c, "UF_EVAL_ask_arc", t->tag, static_cast<int>(t->type), false, true,
                          [&]() { return UF_EVAL_ask_arc(ev.p, &arc); });
    if (!c.stopped) {
        bool valid = std::isfinite(arc.radius) && arc.radius > 0 && std::isfinite(limits[0]) && std::isfinite(limits[1]) &&
            limits[0] < limits[1] && std::isfinite(arc.limits[0]) && std::isfinite(arc.limits[1]) && arc.limits[0] < arc.limits[1] &&
            (is_periodic != 0) == (arc.is_periodic != 0);
        double x2 = 0, y2 = 0;
        for (int i = 0; i < 3; ++i) {
            valid = valid && std::isfinite(arc.center[i]) && std::isfinite(arc.x_axis[i]) && std::isfinite(arc.y_axis[i]);
            x2 += arc.x_axis[i]*arc.x_axis[i]; y2 += arc.y_axis[i]*arc.y_axis[i];
        }
        double cross[3] = {arc.x_axis[1]*arc.y_axis[2]-arc.x_axis[2]*arc.y_axis[1],
                           arc.x_axis[2]*arc.y_axis[0]-arc.x_axis[0]*arc.y_axis[2],
                           arc.x_axis[0]*arc.y_axis[1]-arc.x_axis[1]*arc.y_axis[0]};
        double cross2 = cross[0]*cross[0] + cross[1]*cross[1] + cross[2]*cross[2];
        if (!valid || !std::isfinite(x2) || !std::isfinite(y2) || !std::isfinite(cross2) || x2 <= 0 || y2 <= 0 || cross2 <= 0) {
            c.native_failure = c.stopped = true; c.failure_reason = "invalid_arc_data";
        }
    }
    if (c.stopped) out << "null";
    else {
        out << "{\"type\":\"circular_evaluator\",\"coordinate_system\":\"ABS\",\"radius\":"; number(out, arc.radius, c);
        out << ",\"center\":"; array(out, arc.center, 3, c);
        out << ",\"x_axis\":"; array(out, arc.x_axis, 3, c);
        out << ",\"y_axis\":"; array(out, arc.y_axis, 3, c);
        out << ",\"evaluator_limits\":"; array(out, limits, 2, c);
        out << ",\"arc_limits\":"; array(out, arc.limits, 2, c);
        out << ",\"is_periodic\":" << (is_periodic ? "true" : "false")
            << ",\"arc_is_periodic\":" << (arc.is_periodic ? "true" : "false")
            << ",\"direction_relation\":\"unverified\"}";
    }
    ev.release();
}
void topology(std::ostream& out, const UF_BREP_topology_t *t, Context& c, int depth) {
    if (!t || depth > (c.full_detail ? 6 : 16) || ++c.nodes > kMaxElements || (c.diagnostic && c.stopped)) {
        out << "null"; c.incomplete = true;
        if (c.full_detail && !c.stopped) c.native_failure = c.stopped = true;
        return;
    }
    int edge_kind = 0;
    if (c.full_detail && t->type == UF_BREP_EDGE_TOPO) {
        size_t i = 0; while (i < c.edge_tags.size() && c.edge_tags[i] != t->tag) ++i;
        if (i == c.edge_tags.size()) { c.native_failure = c.stopped = true; c.failure_reason = "edge_not_in_inventory"; out << "null"; return; }
        edge_kind = c.edge_kinds[i]; c.edge_seen[i] = true;
    }
    int id = 0; probe(c, "UF_BREP_ask_identifier", t->tag, static_cast<int>(t->type), false, false, [&]() { UF_BREP_ask_identifier(t, &id); return 0; });
    out << "{\"type\":" << static_cast<int>(t->type) << ",\"tag\":" << t->tag << ",\"local_identifier\":" << id;
    int geom_class = 0;
    if (t->type == UF_BREP_EDGE_TOPO) {
        int edge_class = 0;
        int class_rc = probe(c, "UF_BREP_ask_edge_class", t->tag, static_cast<int>(t->type), false, true, [&]() { return UF_BREP_ask_edge_class(t, &edge_class, &geom_class); });
        out << ",\"edge_class_rc\":" << class_rc << ",\"edge_class\":" << edge_class << ",\"geometry_class\":" << geom_class;
        if (class_rc) c.incomplete = true;
        if (c.full_detail && !c.stopped && edge_kind == 1 && geom_class != UF_BREP_EDGE_NORMAL) {
            c.native_failure = c.stopped = true; c.failure_reason = "circular_edge_not_normal";
        }
    }
    if (t->type == UF_BREP_FACE_TOPO || t->type == UF_BREP_FIN_TOPO || t->type == UF_BREP_EDGE_TOPO || t->type == UF_BREP_VERTEX_TOPO) {
        if (c.full_detail && t->type == UF_BREP_EDGE_TOPO && (edge_kind == 1 || c.stopped)) {
            out << ",\"geometry_rc\":null,\"geometry_sense\":null,\"states\":[],\"geometry\":";
            if (c.stopped) out << "null"; else circular_geometry(out, t, c);
        } else {
        GeometryOwner g(c, t->tag, static_cast<int>(t->type)); StateOwner state(c, t->tag); int count = 0;
        UF_BREP_orientation_t sense = t->type == UF_BREP_VERTEX_TOPO ? UF_BREP_ORIENTATION_NONE : UF_BREP_ORIENTATION_FORWARD;
        int rc = probe(c, "UF_BREP_ask_geometry", t->tag, static_cast<int>(t->type), false, true, [&]() { return UF_BREP_ask_geometry(t, &c.options, &c.mapping, &g.value, &sense, &count, &state.p); });
        out << ",\"geometry_rc\":" << rc << ",\"geometry_sense\":" << static_cast<int>(sense) << ",\"states\":";
        states(out, count, state.p, c);
        out << ",\"geometry\":";
        if (c.full_detail && t->type == UF_BREP_EDGE_TOPO && edge_kind != 1 && rc == 0 && g.value.type == UF_BREP_ARC_GEOM) {
            c.native_failure = c.stopped = true; c.failure_reason = "edge_type_mismatch";
        }
        if (rc || g.value.type == UF_BREP_GEOM_ALL) {
            out << "null"; c.incomplete = true;
            if (rc != kSkipped) { c.native_failure = true; if (c.diagnostic) c.stopped = true; }
        } else if (c.diagnostic && c.stopped) {
            out << "null"; c.incomplete = true;
        } else geometry(out, &g.value, c, 0);
        if (g.value.type != UF_BREP_GEOM_ALL) {
            int free_rc = g.release();
            out << ",\"geometry_free_rc\":" << free_rc;
            if (free_rc) { c.incomplete = true; c.cleanup_failed = true; }
        }
        }
    }
    out << ",\"children\":[";
    if (t->num_children < 0 || t->num_children > kMaxElements || (t->num_children && !t->children)) {
        c.incomplete = true; if (c.full_detail) c.native_failure = c.stopped = true;
    }
    else for (int i = 0; i < t->num_children && !(c.diagnostic && c.stopped); ++i) {
        if (i) out << ',';
        out << "{\"orientation\":" << t->children[i].orientation << ",\"child\":";
        topology(out, t->children[i].child, c, depth + 1); out << '}';
    }
    out << "]}";
}
}

static int read_face_impl(uint32_t part_tag, uint32_t face_tag, double curve_tol, double surface_tol, char **utf8_json, uint64_t *length,
                          const uint32_t *edge_tags = NULL, const uint8_t *edge_kinds = NULL, uint32_t edge_count = 0, bool full_detail = false) {
    if (!utf8_json || !length) return 1;
    *utf8_json = NULL; *length = 0;
    if (!face_tag || !std::isfinite(curve_tol) || curve_tol <= 0 || !std::isfinite(surface_tol) || surface_tol <= 0) return 1;
    try {
        Context c(curve_tol, surface_tol, part_tag);
        c.full_detail = full_detail;
        if (full_detail) {
            if (!edge_tags || !edge_kinds || !edge_count || edge_count > 4096) { c.native_failure = c.stopped = true; c.failure_reason = "invalid_edge_inventory"; }
            else for (uint32_t i = 0; i < edge_count; ++i) {
                bool duplicate = false;
                for (size_t j = 0; j < c.edge_tags.size(); ++j) if (c.edge_tags[j] == edge_tags[i]) duplicate = true;
                if (!edge_tags[i] || edge_kinds[i] < 1 || edge_kinds[i] > 4 || duplicate) { c.native_failure = c.stopped = true; c.failure_reason = "invalid_edge_inventory"; break; }
                c.edge_tags.push_back(edge_tags[i]); c.edge_kinds.push_back(edge_kinds[i]); c.edge_seen.push_back(false);
            }
        }
        // This bounded prototype cannot establish complete UV trimming or the
        // source of mapped curves. Always report the result as inconclusive.
        std::ostringstream out; out.imbue(std::locale::classic());
        out << "{\"schema\":\"" << (c.full_detail ? "v3-reference-geometry-probe-v3" : (c.diagnostic ? "v3-reference-geometry-probe-v2" : "v3-reference-geometry-detail-v1")) << "\",\"face_tag\":" << face_tag
            << ",\"tag_scope\":\"current_session_only\",\"status\":\"INCONCLUSIVE\",\"geometry_details_complete\":false"
            << ",\"options\":{\"finsp\":1,\"edge3d\":1,\"curve_tolerance\":";
        number(out, curve_tol, c); out << ",\"surface_tolerance\":"; number(out, surface_tol, c);
        out << ",\"tolerance_unit\":\"part_length_unit\",\"flatten\":false},\"mapping\":[\"BLEND_TO_BSURFACE\",\"INTERSECTION_TO_SPLINE\"]";
        double uv[4] = {0}; int uv_rc = probe(c, "UF_MODL_ask_face_uv_minmax", face_tag, 0, false, true, [&]() { return UF_MODL_ask_face_uv_minmax(face_tag, uv); });
        out << ",\"uv_box_rc\":" << uv_rc << ",\"uv_box\":";
        if (uv_rc) { out << "null"; c.incomplete = true; } else array(out, uv, 4, c);
        TreeOwner tree(c, face_tag); StateOwner state(c, face_tag); int count = 0;
        int rc = probe(c, "UF_BREP_ask_topology", face_tag, 0, false, true, [&]() { return UF_BREP_ask_topology(face_tag, &c.options, &tree.p, &count, &state.p); });
        out << ",\"topology_rc\":" << rc << ",\"topology_state_count\":" << count << ",\"topology_states\":";
        if (c.diagnostic) {
            out << "null"; DiscardBuffer discarded; std::ostream sink(&discarded);
            sink.imbue(std::locale::classic()); states(sink, count, state.p, c);
        } else states(out, count, state.p, c);
        out << ",\"topology\":";
        if (rc || !tree.p) { out << "null"; c.incomplete = true; if (rc != kSkipped) { c.native_failure = true; if (c.diagnostic) c.stopped = true; } }
        else if (c.diagnostic && c.stopped) { out << "null"; c.incomplete = true; }
        else if (c.full_detail) {
            LimitedBuffer storage(c); std::ostream bounded(&storage); bounded.imbue(std::locale::classic());
            topology(bounded, tree.p, c, 0);
            if (c.stopped || c.geometry_overflow) out << "null"; else out << storage.value;
        } else if (c.diagnostic) {
            out << "null"; DiscardBuffer discarded; std::ostream sink(&discarded);
            sink.imbue(std::locale::classic()); topology(sink, tree.p, c, 0);
        } else topology(out, tree.p, c, 0);
        int release_rc = 0;
        if (tree.p) release_rc = tree.release();
        state.release();
        out << ",\"topology_release_rc\":" << release_rc;
        if (release_rc) { c.incomplete = true; c.cleanup_failed = true; }
        bool edge_coverage = false;
        if (c.full_detail && !c.stopped && !c.native_failure && !c.dirty_seen) {
            edge_coverage = !c.edge_seen.empty();
            for (size_t i = 0; i < c.edge_seen.size(); ++i) if (!c.edge_seen[i]) edge_coverage = false;
            if (!edge_coverage) { c.native_failure = c.stopped = true; c.failure_reason = "edge_coverage_mismatch"; }
        }
        out << ",\"incomplete_observed\":" << (c.incomplete ? "true" : "false")
            << ",\"open_items\":[\"UV trim completeness and exact source types not established\",\"native results require independent validation\"]";
        if (c.diagnostic) {
            const char *outcome = (c.native_failure || c.cleanup_failed || c.event_overflow) ? "NATIVE_ERROR" : (c.dirty_seen ? "DIRTY_STOP" : "CLEAN_TRACE");
            out << ",\"part_tag\":" << part_tag;
            if (c.full_detail) out << ",\"geometry_overflow\":" << (c.geometry_overflow ? "true" : "false")
                                   << ",\"edge_coverage_complete\":" << (edge_coverage ? "true" : "false")
                                   << ",\"root_topology_states_omitted\":true";
            else out << ",\"diagnostic_omits_geometry_and_state_details\":true";
            out << ",\"outcome\":\"" << outcome << "\",\"first_dirty_sequence\":";
            if (c.first_dirty) out << c.first_dirty; else out << "null";
            if (c.full_detail) { out << ",\"failure_reason\":"; if (c.failure_reason) out << '"' << c.failure_reason << '"'; else out << "null"; }
            out << ",\"event_overflow\":" << (c.event_overflow ? "true" : "false")
                << ",\"dirty_sampling\":\"UF_PART_is_modified: no error channel; false also includes unloaded part\",\"events\":[";
            for (size_t i = 0; i < c.events.size(); ++i) {
                const ProbeEvent& e = c.events[i]; if (i) out << ',';
                out << "{\"sequence\":" << (i + 1) << ",\"stage\":\"" << e.stage << "\",\"tag\":" << e.tag
                    << ",\"topology_type\":" << e.type << ",\"cleanup\":" << (e.cleanup ? "true" : "false")
                    << ",\"called\":" << (e.called ? "true" : "false") << ",\"dirty_before\":" << (e.before ? "true" : "false") << ",\"dirty_after\":";
                if (e.after < 0) out << "null"; else out << (e.after ? "true" : "false");
                out << ",\"uf_rc\":"; if (!e.called || !e.has_rc) out << "null"; else out << e.rc;
                out << '}';
            }
            out << ']';
        }
        out << '}';
        // Allocation-capable UF read or release failure has unknown resource
        // state. Return no result; other owners still unwind normally.
        if (!c.diagnostic && (c.cleanup_failed || c.native_failure)) return 3;
        std::string text = out.str();
        if (text.size() > kMaxJson) return 2;
        char *buffer = static_cast<char *>(std::malloc(text.size() + 1));
        if (!buffer) return 2;
        std::memcpy(buffer, text.data(), text.size()); buffer[text.size()] = '\0';
        *utf8_json = buffer; *length = static_cast<uint64_t>(text.size()); return 0;
    } catch (...) { return 2; }
}

extern "C" __declspec(dllexport) int __cdecl rg_read_face_v1(uint32_t face_tag, double curve_tol, double surface_tol, char **utf8_json, uint64_t *length) {
    return read_face_impl(0, face_tag, curve_tol, surface_tol, utf8_json, length);
}

extern "C" __declspec(dllexport) int __cdecl rg_probe_face_v2(uint32_t part_tag, uint32_t face_tag, double curve_tol, double surface_tol, char **utf8_json, uint64_t *length) {
    if (!part_tag) { if (utf8_json) *utf8_json = NULL; if (length) *length = 0; return 1; }
    return read_face_impl(part_tag, face_tag, curve_tol, surface_tol, utf8_json, length);
}

extern "C" __declspec(dllexport) int __cdecl rg_probe_face_v3(uint32_t part_tag, uint32_t face_tag, double curve_tol, double surface_tol,
    const uint32_t *edge_tags, const uint8_t *edge_kinds, uint32_t edge_count, char **utf8_json, uint64_t *length) {
    if (!part_tag) { if (utf8_json) *utf8_json = NULL; if (length) *length = 0; return 1; }
    return read_face_impl(part_tag, face_tag, curve_tol, surface_tol, utf8_json, length, edge_tags, edge_kinds, edge_count, true);
}

extern "C" __declspec(dllexport) void __cdecl rg_free_v1(char *buffer) { std::free(buffer); }
