using System;
using System.Collections.Generic;
using System.Globalization;
using NXOpen;
using NxSketchMcp.M2;

// Diagnostic path only. The original IV3ReferenceAdapter remains unchanged.
public sealed partial class M2OpenModelAdapter
{
    private static bool V3DetailDirty(Part part, string stage, List<object> events, ref object firstChange)
    {
        Dictionary<string, object> sample = new Dictionary<string, object> {
            { "sequence", events.Count + 1 }, { "stage", stage }, { "dirty", null }
        };
        events.Add(sample);
        try
        {
            bool dirty = part.IsModified;
            sample["dirty"] = dirty;
            if (dirty && firstChange == null) firstChange = sample;
            return !dirty;
        }
        catch (Exception ex)
        {
            sample["error_type"] = ex.GetType().FullName;
            if (firstChange == null) firstChange = sample;
            return false;
        }
    }

    private static void V3DetailFailure(string stage, Exception ex, List<object> events, ref object firstChange)
    {
        Dictionary<string, object> failure = new Dictionary<string, object> {
            { "sequence", events.Count + 1 }, { "stage", stage }, { "dirty", null },
            { "error_type", ex.GetType().FullName }
        };
        events.Add(failure);
        if (firstChange == null) firstChange = failure;
    }

    private static string V3DetailUnavailable(object firstChange)
    {
        Dictionary<string, object> change = firstChange as Dictionary<string, object>;
        return change != null && change.ContainsKey("dirty") && change["dirty"] is bool && (bool)change["dirty"]
            ? "unavailable_after_dirty" : "unavailable_after_failure";
    }

    private static void V3DetailMark(string stage, string outcome, List<object> events, ref object firstChange)
    {
        Dictionary<string, object> item = new Dictionary<string, object> {
            { "sequence", events.Count + 1 }, { "stage", stage }, { "dirty", null }, { "outcome", outcome }
        };
        events.Add(item);
        if (firstChange == null) firstChange = item;
    }

    private static bool V3DetailValidCleanTrace(Dictionary<string, object> diagnostic, uint partTag, uint faceTag,
        uint[] edgeTags, byte[] edgeKinds)
    {
        object value;
        if (!diagnostic.TryGetValue("schema", out value) || !Object.Equals(value, "v3-reference-geometry-probe-v3")) return false;
        if (!diagnostic.TryGetValue("part_tag", out value) || !V3DetailInteger(value, partTag)) return false;
        if (!diagnostic.TryGetValue("face_tag", out value) || !V3DetailInteger(value, faceTag)) return false;
        if (!diagnostic.TryGetValue("event_overflow", out value) || !(value is bool) || (bool)value) return false;
        if (!diagnostic.TryGetValue("geometry_overflow", out value) || !(value is bool) || (bool)value) return false;
        if (!diagnostic.TryGetValue("edge_coverage_complete", out value) || !(value is bool) || !(bool)value) return false;
        if (!diagnostic.TryGetValue("topology", out value) || !(value is Dictionary<string, object>)) return false;
        if (!diagnostic.TryGetValue("first_dirty_sequence", out value) || value != null) return false;
        List<object> trace = diagnostic.ContainsKey("events") ? diagnostic["events"] as List<object> : null;
        if (trace == null || trace.Count < 5) return false;
        int uvCount = 0, topologyCount = 0, releaseCount = 0, geometryCount = 0;
        Dictionary<string, int> pending = new Dictionary<string, int>(StringComparer.Ordinal);
        Dictionary<uint, byte> allowed = new Dictionary<uint, byte>();
        for (int i = 0; i < edgeTags.Length; i++) allowed.Add(edgeTags[i], edgeKinds[i]);
        Dictionary<uint, int> evaluatorStage = new Dictionary<uint, int>();
        HashSet<uint> visitedEdges = new HashSet<uint>();
        for (int i = 0; i < trace.Count; i++)
        {
            Dictionary<string, object> e = trace[i] as Dictionary<string, object>;
            if (e == null || !e.ContainsKey("sequence") || !V3DetailInteger(e["sequence"], (uint)(i + 1)) ||
                !e.ContainsKey("stage") || !(e["stage"] is string) || String.IsNullOrWhiteSpace((string)e["stage"]) ||
                !e.ContainsKey("called") || !(e["called"] is bool) || !(bool)e["called"] ||
                !e.ContainsKey("dirty_before") || !(e["dirty_before"] is bool) || (bool)e["dirty_before"] ||
                !e.ContainsKey("dirty_after") || !(e["dirty_after"] is bool) || (bool)e["dirty_after"] ||
                !e.ContainsKey("cleanup") || !(e["cleanup"] is bool) || !e.ContainsKey("uf_rc") ||
                !e.ContainsKey("tag") || !e.ContainsKey("topology_type")) return false;
            string stage = (string)e["stage"];
            bool cleanup = stage == "UF_BREP_free_geometry_data" || stage == "UF_BREP_release_topology" || stage == "UF_free_states" || stage == "UF_EVAL_free";
            bool noReturnCode = stage == "UF_BREP_ask_identifier" || stage == "UF_free_states";
            string[] evalStages = { "UF_EVAL_initialize_2", "UF_EVAL_is_arc", "UF_EVAL_ask_limits", "UF_EVAL_is_periodic", "UF_EVAL_ask_arc", "UF_EVAL_free" };
            int evalIndex = Array.IndexOf(evalStages, stage);
            bool recognized = cleanup || noReturnCode || stage == "UF_MODL_ask_face_uv_minmax" ||
                stage == "UF_BREP_ask_topology" || stage == "UF_BREP_ask_edge_class" ||
                stage == "UF_BREP_ask_geometry" || stage == "UF_CSYS_ask_matrix_values" || evalIndex >= 0;
            if (!recognized || (bool)e["cleanup"] != cleanup ||
                (noReturnCode ? e["uf_rc"] != null : !V3DetailInteger(e["uf_rc"], 0))) return false;
            uint eventTag, topologyType;
            if (!V3DetailUint(e["tag"], out eventTag) || !V3DetailUint(e["topology_type"], out topologyType)) return false;
            if (i == 0 && (stage != "UF_MODL_ask_face_uv_minmax" || eventTag != faceTag)) return false;
            if (i == 1 && (stage != "UF_BREP_ask_topology" || eventTag != faceTag)) return false;
            if (releaseCount != 0 && stage != "UF_free_states") return false;
            if (stage == "UF_MODL_ask_face_uv_minmax") uvCount++;
            if (stage == "UF_BREP_ask_topology") topologyCount++;
            if (stage == "UF_BREP_release_topology") { if (eventTag != faceTag) return false; releaseCount++; }
            if (evalIndex >= 0)
            {
                byte kind; int previous;
                if (!allowed.TryGetValue(eventTag, out kind) || kind != 1) return false;
                evaluatorStage.TryGetValue(eventTag, out previous);
                if (evalIndex != previous) return false;
                evaluatorStage[eventTag] = evalIndex == 5 ? 0 : previous + 1;
                if (evalIndex == 0) visitedEdges.Add(eventTag);
            }
            if (stage == "UF_BREP_ask_geometry" && topologyType == 8)
            {
                byte kind;
                if (!allowed.TryGetValue(eventTag, out kind) || kind == 1) return false;
                visitedEdges.Add(eventTag);
            }
            string geometryKey = eventTag.ToString(CultureInfo.InvariantCulture) + ":" + topologyType.ToString(CultureInfo.InvariantCulture);
            if (stage == "UF_BREP_ask_geometry")
            {
                geometryCount++; int count; pending.TryGetValue(geometryKey, out count); pending[geometryKey] = count + 1;
            }
            if (stage == "UF_BREP_free_geometry_data")
            {
                int count;
                if (!pending.TryGetValue(geometryKey, out count) || count == 0) return false;
                pending[geometryKey] = count - 1;
            }
        }
        foreach (int count in pending.Values) if (count != 0) return false;
        foreach (int count in evaluatorStage.Values) if (count != 0) return false;
        return uvCount == 1 && topologyCount == 1 && releaseCount == 1 && geometryCount > 0 && visitedEdges.Count == allowed.Count;
    }

    private static bool V3DetailUint(object value, out uint result)
    {
        result = 0;
        if (!(value is double) && !(value is int) && !(value is long)) return false;
        double number = Convert.ToDouble(value, CultureInfo.InvariantCulture);
        if (Double.IsNaN(number) || Double.IsInfinity(number) || number < 0 || number > UInt32.MaxValue || Math.Floor(number) != number) return false;
        result = (uint)number; return true;
    }

    private static bool V3DetailInteger(object value, uint expected)
    { uint number; return V3DetailUint(value, out number) && number == expected; }

    private static bool V3DetailEdgeMap(Dictionary<string, object> selected, Dictionary<string, object> face,
        out uint[] tags, out byte[] kinds)
    {
        tags = null; kinds = null;
        List<object> rawEdges = selected == null ? null : selected["edges"] as List<object>;
        List<object> faceEdges = face == null ? null : face["edge_tags"] as List<object>;
        if (rawEdges == null || faceEdges == null || faceEdges.Count == 0 || faceEdges.Count > 4096) return false;
        Dictionary<string, Dictionary<string, object>> edges = new Dictionary<string, Dictionary<string, object>>(StringComparer.Ordinal);
        foreach (object item in rawEdges)
        {
            Dictionary<string, object> edge = item as Dictionary<string, object>;
            string key = edge != null && edge.ContainsKey("tag") ? edge["tag"] as string : null;
            if (String.IsNullOrEmpty(key) || edges.ContainsKey(key)) return false;
            edges.Add(key, edge);
        }
        string faceTag = face["tag"] as string;
        if (String.IsNullOrEmpty(faceTag)) return false;
        tags = new uint[faceEdges.Count]; kinds = new byte[faceEdges.Count];
        HashSet<string> seen = new HashSet<string>(StringComparer.Ordinal);
        HashSet<uint> seenNumeric = new HashSet<uint>();
        for (int i = 0; i < faceEdges.Count; i++)
        {
            string key = faceEdges[i] as string;
            Dictionary<string, object> edge;
            uint parsed;
            if (String.IsNullOrEmpty(key) || !seen.Add(key) || !edges.TryGetValue(key, out edge) ||
                !UInt32.TryParse(key, NumberStyles.None, CultureInfo.InvariantCulture, out parsed) || parsed == 0 || !seenNumeric.Add(parsed)) return false;
            List<object> adjacent = edge.ContainsKey("face_tags") ? edge["face_tags"] as List<object> : null;
            if (adjacent == null || !adjacent.Contains(faceTag)) return false;
            string type = edge.ContainsKey("edge_type") ? edge["edge_type"] as string : null;
            byte kind = type == "Circular" ? (byte)1 : type == "Linear" ? (byte)2 :
                        type == "Spline" ? (byte)3 : type == "Intersection" ? (byte)4 : (byte)0;
            if (kind == 0) return false;
            tags[i] = parsed; kinds[i] = kind;
        }
        return true;
    }

    public Dictionary<string, object> InspectReferenceDetail(M2ModelBinding binding, string revisionId,
        string snapshotId, string bodyId, V3ReferenceDetailRequest request)
    {
        BindingState state = RequireState(binding);
        Part part = state.WorkPart;
        Dictionary<string, object> first = null, second = null;
        List<object> events = new List<object>(), details = new List<object>();
        List<Dictionary<string, object>> matched = new List<Dictionary<string, object>>();
        List<uint[]> faceEdgeTags = new List<uint[]>();
        List<byte[]> faceEdgeKinds = new List<byte[]>();
        object firstChange = null;
        bool consistencyFault = false, selectable = false, unique = false;
        bool nativeClean = false;
        string diffStatus = "unavailable_after_failure";
        List<object> changes = null;
        try
        {
            // UF_PART_is_modified alone returns false also when not loaded.
            if (!String.Equals(part.Tag.ToString(), binding.PartTag, StringComparison.Ordinal) ||
                !String.Equals(part.PartLoadState.ToString(), "FullyLoaded", StringComparison.Ordinal))
                throw new InvalidOperationException("Work part identity/load state is not established");
            if (!V3DetailDirty(part, "capture_before:pre", events, ref firstChange))
            { consistencyFault = true; diffStatus = V3DetailUnavailable(firstChange); goto Finish; }

            first = V3Inventory(part, state.Session, bodyId);
            if (!V3DetailDirty(part, "capture_before:post", events, ref firstChange))
            { consistencyFault = true; diffStatus = V3DetailUnavailable(firstChange); goto Finish; }
            if (((List<object>)first["errors"]).Count != 0)
            { V3DetailMark("capture_before", "inventory_errors", events, ref firstChange); consistencyFault = true; goto Finish; }
            selectable = (bool)first["selection_resolved"];
            Dictionary<string, object> selected = selectable ? first["selected_body"] as Dictionary<string, object> : null;
            if (!V3DetailDirty(part, "selector:pre", events, ref firstChange))
            { consistencyFault = true; diffStatus = V3DetailUnavailable(firstChange); goto Finish; }
            foreach (V3ReferenceFaceSelector selector in request.Selectors)
            {
                List<Dictionary<string, object>> found = new List<Dictionary<string, object>>();
                if (selected != null)
                {
                    foreach (object raw in (List<object>)selected["faces"])
                    {
                        Dictionary<string, object> face = (Dictionary<string, object>)raw;
                        Dictionary<string, object> data = face["native_face_data"] as Dictionary<string, object>;
                        if (data == null || !String.Equals(face["surface_type"] as string, selector.SurfaceType, StringComparison.Ordinal)
                            || Convert.ToInt32(data["uf_type"], CultureInfo.InvariantCulture) != selector.UfType
                            || ((List<object>)face["edge_tags"]).Count != selector.EdgeCount) continue;
                        double[] box = data["bounding_box"] as double[];
                        if (box == null || box.Length != 6) continue;
                        bool equal = true;
                        for (int i = 0; i < 6; i++)
                            if (Math.Abs(box[i] - selector.BoundingBox[i]) > request.MatchLinear) equal = false;
                        if (equal) found.Add(face);
                    }
                }
                Dictionary<string, object> detail = new Dictionary<string, object> {
                    { "label", selector.Label }, { "matching_count", found.Count },
                    { "status", found.Count == 1 ? "MATCHED" : "INCONCLUSIVE" },
                    { "matching_basis", "surface and UF type, bounding box and edge count only; not shape equivalence" },
                    { "observed_face", found.Count == 1 ? found[0] : null }
                };
                details.Add(detail);
                matched.Add(found.Count == 1 ? found[0] : null);
            }
            if (!V3DetailDirty(part, "selector:post", events, ref firstChange))
            { consistencyFault = true; diffStatus = V3DetailUnavailable(firstChange); goto Finish; }
            unique = matched.Count == request.Selectors.Length && matched.Count > 0;
            HashSet<string> selectedTags = new HashSet<string>(StringComparer.Ordinal);
            foreach (Dictionary<string, object> face in matched)
            {
                string selectedTag = face == null ? null : face["tag"] as string;
                if (String.IsNullOrEmpty(selectedTag) || !selectedTags.Add(selectedTag)) unique = false;
            }
            if (unique)
            {
                for (int i = 0; i < matched.Count; i++)
                {
                    uint[] tags; byte[] kinds;
                    if (!V3DetailEdgeMap(selected, matched[i], out tags, out kinds))
                    { V3DetailMark("edge_whitelist", "invalid_or_incomplete", events, ref firstChange); consistencyFault = true; goto Finish; }
                    faceEdgeTags.Add(tags); faceEdgeKinds.Add(kinds);
                }
                nativeClean = true;
                for (int i = 0; i < matched.Count; i++)
                {
                    if (!V3DetailDirty(part, "native:" + i + ":pre", events, ref firstChange))
                    { consistencyFault = true; diffStatus = V3DetailUnavailable(firstChange); goto Finish; }
                    uint tag = UInt32.Parse((string)matched[i]["tag"], CultureInfo.InvariantCulture);
                    Dictionary<string, object> diagnostic = NxSketchMcp.V3.ReferenceGeometry.ReadFaceWithEdges(
                        (uint)part.Tag, tag, request.CurveTolerance, request.SurfaceTolerance, faceEdgeTags[i], faceEdgeKinds[i]);
                    ((Dictionary<string, object>)details[i])["diagnostic"] = diagnostic;
                    string outcome = diagnostic["outcome"] as string;
                    Dictionary<string, object> nativeEvent = new Dictionary<string, object> {
                        { "sequence", events.Count + 1 }, { "stage", "native:" + i },
                        { "dirty", outcome == "DIRTY_STOP" ? (object)true : null },
                        { "outcome", outcome }, { "native_first_dirty_sequence", diagnostic.ContainsKey("first_dirty_sequence") ? diagnostic["first_dirty_sequence"] : null }
                    };
                    events.Add(nativeEvent);
                    if (outcome == "CLEAN_TRACE" && !V3DetailValidCleanTrace(diagnostic, (uint)part.Tag, tag, faceEdgeTags[i], faceEdgeKinds[i]))
                    {
                        consistencyFault = true; nativeClean = false;
                        nativeEvent["outcome"] = "INVALID_CLEAN_TRACE";
                        if (firstChange == null) firstChange = nativeEvent;
                        goto Finish;
                    }
                    if (outcome != "CLEAN_TRACE")
                    {
                        nativeClean = false; consistencyFault = true;
                        if (firstChange == null) firstChange = nativeEvent;
                        diffStatus = outcome == "DIRTY_STOP" ? "unavailable_after_dirty" : "unavailable_after_failure";
                        goto Finish;
                    }
                    if (!V3DetailDirty(part, "native:" + i + ":post", events, ref firstChange))
                    { nativeClean = false; consistencyFault = true; diffStatus = V3DetailUnavailable(firstChange); goto Finish; }
                }
            }
            if (!V3DetailDirty(part, "capture_after:pre", events, ref firstChange))
            { consistencyFault = true; diffStatus = V3DetailUnavailable(firstChange); goto Finish; }
            second = V3Inventory(part, state.Session, bodyId);
            if (!V3DetailDirty(part, "capture_after:post", events, ref firstChange))
            { consistencyFault = true; diffStatus = V3DetailUnavailable(firstChange); goto Finish; }
            if (((List<object>)second["errors"]).Count != 0)
            { V3DetailMark("capture_after", "inventory_errors", events, ref firstChange); consistencyFault = true; goto Finish; }
            changes = V3InventoryDifference.Compare(first, second);
            diffStatus = "complete";
            if (changes.Count != 0 || !String.Equals(revisionId, binding.RevisionId, StringComparison.Ordinal))
            { V3DetailMark("inventory_compare", changes.Count != 0 ? "fields_changed" : "revision_changed", events, ref firstChange); consistencyFault = true; }
        }
        catch (Exception ex)
        {
            V3DetailFailure("managed_exception", ex, events, ref firstChange);
            consistencyFault = true;
        }
    Finish:
        // If capture_after itself made the model dirty, preserve what was
        // already captured; no further NX reads are made to complete a diff.
        Dictionary<string, object> result = new Dictionary<string, object> {
            { "schema", "v3-reference-detail-v2" }, { "snapshot_id", snapshotId },
            { "ok", !consistencyFault && selectable && unique && nativeClean },
            { "complete", false }, { "geometry_details_complete", false },
            { "inventory_complete", !consistencyFault && first != null && second != null && selectable },
            { "read_consistency_fault", consistencyFault }, { "inventory", first },
            { "inventory_before", first }, { "inventory_after", second },
            { "inventory_diff", new Dictionary<string, object> { { "status", diffStatus }, { "changes", changes } } },
            { "diagnostic_events", events }, { "first_change", firstChange }, { "detail", details },
            { "detail_options", new Dictionary<string, object> { { "match_linear", request.MatchLinear },
                { "curve_tolerance", request.CurveTolerance }, { "surface_tolerance", request.SurfaceTolerance },
                { "unit", first == null ? null : first["units"] },
                { "note", "Matching and conversion settings are not model precision or shape verification." } } },
            { "revision_freshness", "cached_not_refreshed" },
            { "snapshot_consistency", new Dictionary<string, object> {
                { "two_native_samples_equal", diffStatus == "complete" && changes.Count == 0 },
                { "proves_full_geometry_unchanged", false } } }
        };
        return result;
    }
}
