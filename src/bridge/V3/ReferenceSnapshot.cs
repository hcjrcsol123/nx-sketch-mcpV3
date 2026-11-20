using System;
using System.Collections.Generic;
using NXOpen;
using NXOpen.Features;
using NXOpen.UF;
using NxSketchMcp.M2;

// Read-only native inventory. It deliberately does not call Capture, create
// builders/sections, save, or update the binding's cached semantic revision.
public sealed partial class M2OpenModelAdapter
{
    public Dictionary<string, object> InspectReference(M2ModelBinding binding, string revisionId, string snapshotId, string bodyId)
    {
        BindingState state = RequireState(binding);
        Part part = state.WorkPart;
        object dirtyBefore = null, dirtyAfter = null;
        List<object> guardErrors = new List<object>();
        ReadField(guardErrors, "part", "is_modified_before", delegate { return part.IsModified; }, out dirtyBefore);
        Dictionary<string, object> first = V3Inventory(part, state.Session, bodyId);
        Dictionary<string, object> second = V3Inventory(part, state.Session, bodyId);
        ReadField(guardErrors, "part", "is_modified_after", delegate { return part.IsModified; }, out dirtyAfter);

        bool inventoryEqual = false;
        bool comparisonSucceeded = false;
        try { inventoryEqual = String.Equals(M2Json.CanonicalText(first), M2Json.CanonicalText(second), StringComparison.Ordinal); comparisonSucceeded = true; }
        catch (Exception ex) { guardErrors.Add(V3Error("snapshot", "comparison", ex)); }
        bool dirtyEqual = dirtyBefore is bool && dirtyAfter is bool && (bool)dirtyBefore == (bool)dirtyAfter;
        bool revisionEqual = String.Equals(revisionId, binding.RevisionId, StringComparison.Ordinal);
        List<object> consistencyFaults = new List<object>();
        if (!(dirtyBefore is bool) || !(dirtyAfter is bool)) consistencyFaults.Add("dirty_state_unavailable");
        else if (!dirtyEqual) consistencyFaults.Add("dirty_state_changed");
        if (!comparisonSucceeded) consistencyFaults.Add("native_comparison_failed");
        else if (!inventoryEqual) consistencyFaults.Add("native_inventory_changed");
        if (!revisionEqual) consistencyFaults.Add("cached_revision_changed");
        bool errors = ((List<object>)first["errors"]).Count != 0 || ((List<object>)second["errors"]).Count != 0 || guardErrors.Count != 0;
        bool selected = (bool)first["selection_resolved"];
        bool complete = !errors && selected && inventoryEqual && dirtyEqual && revisionEqual;
        Dictionary<string, object> result = V3Map();
        result["schema"] = "v3-reference-inventory-v1";
        result["snapshot_id"] = snapshotId;
        result["ok"] = complete;
        result["complete"] = complete;
        result["read_consistency_fault"] = consistencyFaults.Count != 0;
        result["read_consistency_faults"] = consistencyFaults;
        result["inventory_complete"] = complete;
        result["geometry_details_complete"] = false;
        result["geometry_details_scope"] = "UF face data is partial; trimmed surfaces and full edge geometry are not represented";
        result["inventory"] = first;
        result["verification_sample_errors"] = second["errors"];
        result["guard_errors"] = guardErrors;
        result["read_effects"] = new Dictionary<string, object> { { "is_modified_before", dirtyBefore }, { "is_modified_after", dirtyAfter }, { "unchanged", dirtyEqual } };
        result["revision_freshness"] = "cached_not_refreshed";
        result["revision_matches_cached_before_and_after"] = revisionEqual;
        result["snapshot_consistency"] = new Dictionary<string, object> {
            { "two_native_samples_equal", inventoryEqual },
            { "coverage", "reported identity, units, versions, features, body candidates, and selected body topology and face data only" },
            { "proves_full_geometry_unchanged", false }
        };
        return result;
    }

    private static Dictionary<string, object> V3Map() { return new Dictionary<string, object>(StringComparer.Ordinal); }
    private static Dictionary<string, object> V3Error(string scope, string field, Exception ex)
    {
        return new Dictionary<string, object> { { "object", scope }, { "field", field }, { "exception_type", ex.GetType().FullName }, { "message", ex.Message } };
    }
    private static void ReadField(List<object> errors, string scope, string field, Func<object> read, out object value)
    {
        value = null;
        try { value = read(); M2Json.CanonicalText(value); }
        catch (Exception ex) { value = null; errors.Add(V3Error(scope, field, ex)); }
    }
    private static void V3Field(Dictionary<string, object> map, List<object> errors, string scope, string field, Func<object> read)
    {
        object value; ReadField(errors, scope, field, read, out value); map[field] = value;
    }
    private static List<object> V3Tags(TaggedObject[] objects)
    {
        if (objects == null) throw new InvalidOperationException("NX returned a null topology array");
        List<object> result = new List<object>();
        foreach (TaggedObject value in objects)
        {
            if (value == null) throw new InvalidOperationException("NX returned a null topology object");
            result.Add(value.Tag.ToString());
        }
        result.Sort(delegate(object a, object b) { return StringComparer.Ordinal.Compare((string)a, (string)b); });
        return result;
    }
    private static Dictionary<string, object> V3Inventory(Part part, Session session, string bodyId)
    {
        Dictionary<string, object> data = V3Map(); List<object> errors = new List<object>();
        data["errors"] = errors; data["coordinate_system"] = "absolute_part_coordinates";
        data["identifier_scope"] = "current_session_and_revision_only";
        V3Field(data, errors, "part", "part_path", delegate { return part.FullPath; });
        V3Field(data, errors, "part", "part_tag", delegate { return part.Tag.ToString(); });
        V3Field(data, errors, "part", "units", delegate { return part.PartUnits.ToString(); });
        V3Field(data, errors, "part", "load_state", delegate { return part.PartLoadState.ToString(); });
        V3Field(data, errors, "part", "is_read_only", delegate { return part.IsReadOnly; });
        V3Field(data, errors, "session", "nx_running_full_release", delegate { return session.FullReleaseNumber.ToString(); });
        V3Field(data, errors, "part", "last_modified_major_version_uf", delegate { int value; UFSession.GetUFSession().Part.AskLastModifiedVersion(part.Tag, out value); return value; });
        V3Field(data, errors, "part", "minor_version_uf", delegate { int value; UFSession.GetUFSession().Part.AskMinorVersion(part.Tag, out value); return value; });
        data["uf_version_semantics"] = "part history version counters, not NX software release";
        data["saved_by_nx_release"] = null;
        data["saved_by_nx_release_status"] = "unknown";
        data["original_source"] = "unknown";
        List<object> features = new List<object>(); data["features"] = features;
        try
        {
            Feature[] source = part.Features.GetFeatures();
            if (source == null) throw new InvalidOperationException("NX returned null features");
            foreach (Feature feature in source)
            {
                if (feature == null) { errors.Add(V3Error("feature", "identity", new InvalidOperationException("NX returned a null feature"))); continue; }
                Dictionary<string, object> row = V3Map(); features.Add(row); string tag = feature.Tag.ToString(); row["tag"] = tag;
                V3Field(row, errors, tag, "journal_id", delegate { return feature.JournalIdentifier; });
                V3Field(row, errors, tag, "feature_type", delegate { return feature.FeatureType; });
                V3Field(row, errors, tag, "timestamp", delegate { return feature.Timestamp; });
                V3Field(row, errors, tag, "suppressed", delegate { return feature.Suppressed; });
            }
        }
        catch (Exception ex) { errors.Add(V3Error("part", "features", ex)); }
        List<object> bodies = new List<object>(); data["bodies"] = bodies;
        List<Body> matches = new List<Body>(); Body[] all = null;
        try { all = part.Bodies.ToArray(); if (all == null) throw new InvalidOperationException("NX returned null bodies"); }
        catch (Exception ex) { errors.Add(V3Error("part", "bodies", ex)); }
        if (all != null) foreach (Body body in all)
        {
            if (body == null) { errors.Add(V3Error("body", "identity", new InvalidOperationException("NX returned a null body"))); continue; }
            string tag = body.Tag.ToString(); Dictionary<string, object> row = V3Map(); row["tag"] = tag; bodies.Add(row);
            V3Field(row, errors, tag, "journal_id", delegate { return body.JournalIdentifier; });
            V3Field(row, errors, tag, "is_solid", delegate { return body.IsSolidBody; });
            V3Field(row, errors, tag, "is_sheet", delegate { return body.IsSheetBody; });
            if (bodyId != null && String.Equals(bodyId, row["journal_id"] as string, StringComparison.Ordinal)) matches.Add(body);
        }
        if (bodyId == null && all != null && all.Length == 1 && all[0] != null) matches.Add(all[0]);
        bodies.Sort(delegate(object a, object b) { return StringComparer.Ordinal.Compare((string)((Dictionary<string, object>)a)["tag"], (string)((Dictionary<string, object>)b)["tag"]); });
        bool resolved = matches.Count == 1; data["selection_resolved"] = resolved;
        data["selection_required"] = bodyId == null && !resolved;
        data["selection_error"] = bodyId != null && !resolved ? (matches.Count == 0 ? "BODY_NOT_FOUND" : "BODY_ID_AMBIGUOUS") : null;
        data["selected_body"] = resolved ? V3Body(matches[0], errors) : null;
        return data;
    }
    private static Dictionary<string, object> V3Body(Body body, List<object> errors)
    {
        Dictionary<string, object> data = V3Map(); data["tag"] = body.Tag.ToString();
        V3Field(data, errors, (string)data["tag"], "journal_id", delegate { return body.JournalIdentifier; });
        List<object> faces = new List<object>(), edges = new List<object>(); data["faces"] = faces; data["edges"] = edges;
        List<object> unknown = new List<object>(); data["unknown_surface_tags"] = unknown;
        Face[] fs = null; Edge[] es = null;
        try { fs = body.GetFaces(); if (fs == null) throw new InvalidOperationException("NX returned null faces"); }
        catch (Exception ex) { errors.Add(V3Error((string)data["tag"], "faces", ex)); }
        try { es = body.GetEdges(); if (es == null) throw new InvalidOperationException("NX returned null edges"); }
        catch (Exception ex) { errors.Add(V3Error((string)data["tag"], "edges", ex)); }
        if (fs != null) foreach (Face f in fs)
        {
            if (f == null) { errors.Add(V3Error("face", "identity", new InvalidOperationException("NX returned null face"))); continue; }
            string tag = f.Tag.ToString(); Dictionary<string, object> row = V3Map(); row["tag"] = tag; faces.Add(row);
            V3Field(row, errors, tag, "journal_id", delegate { return f.JournalIdentifier; });
            V3Field(row, errors, tag, "surface_type", delegate { return f.SolidFaceType.ToString(); });
            string surfaceType = row["surface_type"] as string;
            Face.FaceType parsed;
            if (surfaceType == null || surfaceType == "Undefined" || !Enum.TryParse<Face.FaceType>(surfaceType, out parsed) || !Enum.IsDefined(typeof(Face.FaceType), parsed)) unknown.Add(tag);
            V3Field(row, errors, tag, "edge_tags", delegate { return V3Tags(f.GetEdges()); });
            V3Field(row, errors, tag, "native_face_data", delegate {
                int type, normal; double[] origin = new double[3], direction = new double[3], box = new double[6]; double radius, radiusData;
                UFSession.GetUFSession().Modl.AskFaceData(f.Tag, out type, origin, direction, box, out radius, out radiusData, out normal);
                return new Dictionary<string, object> { { "uf_type", type }, { "origin", origin }, { "direction", direction }, { "bounding_box", box }, { "radius", radius }, { "radius_data", radiusData }, { "normal_sense", normal } };
            });
        }
        if (es != null) foreach (Edge e in es)
        {
            if (e == null) { errors.Add(V3Error("edge", "identity", new InvalidOperationException("NX returned null edge"))); continue; }
            string tag = e.Tag.ToString(); Dictionary<string, object> row = V3Map(); row["tag"] = tag; edges.Add(row);
            V3Field(row, errors, tag, "journal_id", delegate { return e.JournalIdentifier; });
            V3Field(row, errors, tag, "edge_type", delegate { return e.SolidEdgeType.ToString(); });
            V3Field(row, errors, tag, "face_tags", delegate { return V3Tags(e.GetFaces()); });
        }
        faces.Sort(delegate(object a, object b) { return StringComparer.Ordinal.Compare((string)((Dictionary<string, object>)a)["tag"], (string)((Dictionary<string, object>)b)["tag"]); });
        edges.Sort(delegate(object a, object b) { return StringComparer.Ordinal.Compare((string)((Dictionary<string, object>)a)["tag"], (string)((Dictionary<string, object>)b)["tag"]); });
        V3CheckAdjacency(faces, edges, errors);
        return data;
    }

    private static void V3CheckAdjacency(List<object> faces, List<object> edges, List<object> errors)
    {
        Dictionary<string, Dictionary<string, object>> faceMap = new Dictionary<string, Dictionary<string, object>>(StringComparer.Ordinal);
        Dictionary<string, Dictionary<string, object>> edgeMap = new Dictionary<string, Dictionary<string, object>>(StringComparer.Ordinal);
        foreach (Dictionary<string, object> face in faces)
        {
            string tag = (string)face["tag"];
            if (faceMap.ContainsKey(tag)) errors.Add(V3Error(tag, "identity", new InvalidOperationException("duplicate face tag")));
            else faceMap.Add(tag, face);
        }
        foreach (Dictionary<string, object> edge in edges)
        {
            string tag = (string)edge["tag"];
            if (edgeMap.ContainsKey(tag)) errors.Add(V3Error(tag, "identity", new InvalidOperationException("duplicate edge tag")));
            else edgeMap.Add(tag, edge);
        }
        foreach (Dictionary<string, object> face in faces)
        {
            List<object> adjacent = face["edge_tags"] as List<object>; if (adjacent == null) continue;
            foreach (string tag in adjacent)
            {
                Dictionary<string, object> edge; List<object> reverse;
                if (!edgeMap.TryGetValue(tag, out edge) || (reverse = edge["face_tags"] as List<object>) == null || !reverse.Contains(face["tag"]))
                    errors.Add(V3Error((string)face["tag"], "edge_tags", new InvalidOperationException("face-edge adjacency missing reverse edge or face reference: " + tag)));
            }
        }
        foreach (Dictionary<string, object> edge in edges)
        {
            List<object> adjacent = edge["face_tags"] as List<object>; if (adjacent == null) continue;
            foreach (string tag in adjacent)
            {
                Dictionary<string, object> face; List<object> reverse;
                if (!faceMap.TryGetValue(tag, out face) || (reverse = face["edge_tags"] as List<object>) == null || !reverse.Contains(edge["tag"]))
                    errors.Add(V3Error((string)edge["tag"], "face_tags", new InvalidOperationException("edge-face adjacency missing reverse face or edge reference: " + tag)));
            }
        }
    }
}
