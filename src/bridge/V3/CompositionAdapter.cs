using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.RegularExpressions;
using NXOpen;
using NXOpen.Features;
using NXOpen.UF;
using NxSketchMcp.M2;

public sealed partial class M2OpenModelAdapter : IV3CompositionAdapter
{
    private const string V3CompositionNode = "NX_SKETCH_MCP_V3_NODE";
    private const string V3CompositionArtifact = "NX_SKETCH_MCP_V3_COMPOSITION";
    private const string V3CompositionConsumed = "NX_SKETCH_MCP_V3_CONSUMED_BY";
    private const string V3CompositionScope = "saved_independent_copy";

    private sealed class V3CompositionPlan
    {
        internal BindingState Binding;
        internal List<Dictionary<string, object>> Steps;
        internal string Revision, Before, BeforeGeometry, After, AfterGeometry;
        internal bool Dirty, Applied, Marked;
        internal double BeforeDistanceTolerance, BeforeAngleTolerance;
        internal Dictionary<string, object> Outputs;
    }

    public V3BlockBindingSnapshot PrepareComposition(M2ModelBinding binding, string revision, List<object> steps)
    {
        BindingState state = RequireState(binding);
        RequireWritableSimplePart(state.WorkPart);
        RequireMillimeterPartAndUnit(state.WorkPart, "mm", "mm");
        if (binding.ArtifactScope != V3CompositionScope)
            throw new M2ModelException("UNSUPPORTED_MODEL", "V3 composition requires a saved independent copy");
        string reason;
        if (!IsBindingCurrent(binding, out reason)) throw new M2ModelException("STALE_BINDING", reason);
        SnapshotResult current = Capture(binding, state);
        if (binding.RevisionId != revision) throw new M2ModelException("STALE_REVISION", "work part changed");
        Part part = state.WorkPart;
        Dictionary<string, Feature> known = CompositionFeatures(part);
        bool marked = part.HasUserAttribute(V3CompositionArtifact, NXObject.AttributeType.String, 0);
        if (!marked && (part.Features.GetFeatures().Length != 0 || part.Bodies.ToArray().Length != 0 ||
            part.Curves.ToArray().Length != 0 || part.Sketches.ToArray().Length != 0 || part.Expressions.ToArray().Length != 0))
            throw new M2ModelException("UNSUPPORTED_MODEL", "V3 composition starts on a blank work part");
        double beforeDistance, beforeAngle;
        CompositionReadTolerances(part, out beforeDistance, out beforeAngle);
        if (marked && !CompositionTolerancesMatch(beforeDistance, beforeAngle))
            throw new M2ModelException("UNSUPPORTED_MODEL", "marked composition part has unexpected modeling tolerances");
        HashSet<string> ids = new HashSet<string>(known.Keys, StringComparer.Ordinal);
        HashSet<string> live = new HashSet<string>(known.Where(item => CompositionActiveBodies(part, item.Value).Length != 0)
            .Select(item => item.Key), StringComparer.Ordinal);
        HashSet<string> expressions = new HashSet<string>(part.Expressions.ToArray().Select(e => e.Name), StringComparer.Ordinal);
        List<Dictionary<string, object>> commands = new List<Dictionary<string, object>>();
        foreach (object item in steps)
        {
            Dictionary<string, object> step = CompositionMap(item);
            string id = CompositionString(step, "id");
            if (!Regex.IsMatch(id, @"^[A-Za-z0-9_.-]{1,100}$") || !ids.Add(id)) throw CompositionInvalid("duplicate or invalid logical id " + id);
            string kind = CompositionString(step, "kind");
            switch (kind)
            {
                case "expression":
                    string name = CompositionString(step, "name");
                    if (!Regex.IsMatch(name, @"^v3_[A-Za-z_0-9]{1,90}$") || expressions.Contains(name))
                        throw CompositionInvalid("duplicate or invalid V3 expression " + name);
                    CompositionFormula(step, "formula", expressions);
                    CompositionUnit(part, step);
                    expressions.Add(name);
                    break;
                case "extrude":
                case "revolve":
                    CompositionFrame(CompositionMap(step["frame"]));
                    foreach (object edge in CompositionList(step, "edges"))
                    {
                        var descriptor = CompositionMap(edge);
                        V3SketchConstraintBinding.EdgeSpec geometry = CompositionEdge(descriptor);
                        if (descriptor.ContainsKey("point_expressions"))
                            CompositionPointReferences(descriptor, "point_expressions", geometry.Kind == "line" ? 2 :
                                geometry.Kind == "arc" ? 3 : 0, expressions);
                        if (descriptor.ContainsKey("pole_expressions"))
                            CompositionPointReferences(descriptor, "pole_expressions", geometry.Poles == null ? 0 :
                                geometry.Poles.Length, expressions);
                        if (descriptor.ContainsKey("radius_expression") &&
                            (geometry.Kind != "circle" || geometry.Center.X != 0 || geometry.Center.Y != 0 ||
                             !expressions.Contains(CompositionString(descriptor, "radius_expression"))))
                            throw CompositionInvalid("driven circle must be centered at the sketch origin and use a current expression");
                    }
                    CompositionExtent(step, kind);
                    if (step.ContainsKey("axis_points_expressions"))
                    {
                        if (kind != "revolve") throw CompositionInvalid("axis points are specific to a revolve");
                        CompositionPointReferences(step, "axis_points_expressions", 2, expressions);
                    }
                    if (step.ContainsKey("start_formula")) CompositionFormula(step, "start_formula", expressions);
                    if (step.ContainsKey("end_formula")) CompositionFormula(step, "end_formula", expressions);
                    live.Add(id);
                    break;
                case "prism":
                    CompositionFrame(step);
                    if (CompositionVector(step["lengths"], 3).Any(v => v <= 0))
                        throw CompositionInvalid("clip prism sides must be positive");
                    live.Add(id);
                    break;
                case "boolean":
                    string op = CompositionString(step, "operation");
                    if (op != "unite" && op != "subtract" && op != "intersect") throw CompositionInvalid("unknown Boolean operation");
                    var target = CompositionString(step, "target");
                    if (!live.Remove(target)) throw CompositionInvalid("Boolean target is unavailable: " + target);
                    var tools = CompositionList(step, "tools").Select(x => x as string).ToArray();
                    bool retain = CompositionRetainTools(step);
                    if (tools.Length == 0 || tools.Distinct().Count() != tools.Length ||
                        tools.Any(t => t == null || !live.Contains(t))) throw CompositionInvalid("Boolean tools are unavailable or duplicated");
                    if (!retain) live.ExceptWith(tools);
                    live.Add(id);
                    break;
                default:
                    throw CompositionInvalid("unknown composition step " + kind);
            }
            commands.Add(step);
        }
        V3CompositionPlan plan = new V3CompositionPlan {
            Binding = state, Steps = commands, Revision = revision,
            Before = CanonicalSemanticSnapshot(current.Snapshot), BeforeGeometry = CaptureFullGeometry(part), Dirty = part.IsModified, Marked = marked,
            BeforeDistanceTolerance = beforeDistance, BeforeAngleTolerance = beforeAngle
        };
        return new V3BlockBindingSnapshot { RevisionId = revision, AdapterState = plan,
            PublicView = new Dictionary<string, object> { { "step_ids", commands.Select(c => (string)c["id"]).ToArray() } } };
    }

    public M2ParameterExecutionResult ExecuteComposition(M2ModelBinding binding, V3BlockBindingSnapshot prepared)
    {
        var evidence = new Dictionary<string, object>();
        var plan = prepared.AdapterState as V3CompositionPlan;
        BindingState state = RequireState(binding);
        Part part = state.WorkPart;
        string reason;
        if (plan == null || plan.Applied || plan.Binding != state || !IsBindingCurrent(binding, out reason))
            return ParameterResult("UNCHANGED", binding.RevisionId, evidence, "STALE_PLAN", "composition plan is stale");
        SnapshotResult before = Capture(binding, state);
        double currentDistance, currentAngle;
        CompositionReadTolerances(part, out currentDistance, out currentAngle);
        if (binding.RevisionId != plan.Revision || CanonicalSemanticSnapshot(before.Snapshot) != plan.Before ||
            CaptureFullGeometry(part) != plan.BeforeGeometry || part.IsModified != plan.Dirty ||
            !CompositionSameTolerance(currentDistance, plan.BeforeDistanceTolerance) ||
            !CompositionSameTolerance(currentAngle, plan.BeforeAngleTolerance))
            return ParameterResult("UNCHANGED", binding.RevisionId, evidence, "STALE_PLAN", "work part changed after prepare");

        List<object> sketchGeometry = CaptureGeometryRecords(part, true);
        Dictionary<string, Feature> features = CompositionFeatures(part);
        Dictionary<string, object> outputs = new Dictionary<string, object>();
        HashSet<string> changedBodies = new HashSet<string>(StringComparer.Ordinal);
        Session.UndoMarkId mark = state.Session.SetUndoMark(Session.MarkVisibility.Invisible, "V3 composition");
        string stepId = null;
        string error;
        try
        {
            if (!plan.Marked)
            {
                double distance = V3CompositionSolids.ModelingDistanceToleranceMm;
                double angle = V3CompositionSolids.ModelingAngleToleranceDeg;
                UFSession.GetUFSession().Modl.SetDistanceToleranceOfPart(part.Tag, ref distance);
                UFSession.GetUFSession().Modl.SetAngleToleranceOfPart(part.Tag, ref angle);
                part.SetUserAttribute(V3CompositionArtifact, 0, "1", Update.Option.Now);
            }
            CompositionReadTolerances(part, out currentDistance, out currentAngle);
            evidence["modeling_tolerances"] = CompositionToleranceEvidence(currentDistance, currentAngle);
            if (!CompositionTolerancesMatch(currentDistance, currentAngle))
                throw new InvalidOperationException("part modeling tolerances do not match the composition settings");
            foreach (Dictionary<string, object> step in plan.Steps)
            {
                stepId = CompositionString(step, "id");
                string kind = CompositionString(step, "kind");
                if (kind == "expression")
                {
                    Expression expression = part.Expressions.CreateWithUnits(CompositionString(step, "name") + "=" +
                        CompositionString(step, "formula"), CompositionUnit(part, step));
                    if (expression.IsInterpartExpression) throw new InvalidOperationException("composition requires a local expression");
                    outputs.Add(stepId, new Dictionary<string, object> { { "name", expression.Name }, { "value", expression.Value } });
                    continue;
                }
                Feature feature;
                var detail = new Dictionary<string, object>();
                if (kind == "boolean")
                {
                    Feature source = features[CompositionString(step, "target")];
                    Body target = CompositionActiveBodies(part, source).Single();
                    Body[] tools = CompositionList(step, "tools")
                        .SelectMany(t => CompositionActiveBodies(part, features[(string)t])).ToArray();
                    if (tools.Length < CompositionList(step, "tools").Count)
                        throw new InvalidOperationException("Boolean tool output is no longer active");
                    bool retain = CompositionRetainTools(step);
                    changedBodies.Add(RequiredJournalId(target, "composition target"));
                    if (!retain)
                        foreach (Body tool in tools) changedBodies.Add(RequiredJournalId(tool, "composition tool"));
                    feature = V3CompositionSolids.Boolean(part, CompositionString(step, "operation"), target, tools, false, retain);
                    detail["input_feature_ids"] = new[] { RequiredJournalId(source, "composition input") }.Concat(
                        CompositionList(step, "tools").Select(t => RequiredJournalId(features[(string)t], "composition input"))).ToArray();
                    detail["retain_tools"] = retain;
                    source.SetUserAttribute(V3CompositionConsumed, 0, stepId, Update.Option.Now);
                    if (!retain)
                        foreach (object input in CompositionList(step, "tools"))
                            features[(string)input].SetUserAttribute(V3CompositionConsumed, 0, stepId, Update.Option.Now);
                }
                else if (kind == "prism")
                {
                    var frame = CompositionFrame(step);
                    double[] sides = CompositionVector(step["lengths"], 3);
                    feature = V3CompositionSolids.CreatePrism(part, frame.Origin, frame.XAxis, frame.YAxis, sides[0], sides[1], sides[2]);
                }
                else
                    feature = CompositionProfileSolid(part, step, kind, detail);

                feature.SetUserAttribute(V3CompositionNode, 0, stepId, Update.Option.Now);
                features.Add(stepId, feature);
                detail["feature_id"] = RequiredJournalId(feature, "composition feature");
                detail["body_ids"] = feature.GetBodies().Select(b => RequiredJournalId(b, "composition output")).ToArray();
                outputs.Add(stepId, detail);
            }
            int updateErrors = state.Session.UpdateManager.DoUpdate(mark);
            evidence["update_error_count"] = updateErrors;
            if (updateErrors != 0) throw new InvalidOperationException("NX update returned errors");
            CompositionReadTolerances(part, out currentDistance, out currentAngle);
            evidence["modeling_tolerances"] = CompositionToleranceEvidence(currentDistance, currentAngle);
            if (!CompositionTolerancesMatch(currentDistance, currentAngle))
                throw new InvalidOperationException("part modeling tolerances changed during composition");
            SnapshotResult after = Capture(binding, state);
            CompositionPreserved(before.Snapshot, after.Snapshot, sketchGeometry, CaptureGeometryRecords(part, true), changedBodies);
            plan.After = CanonicalSemanticSnapshot(after.Snapshot);
            plan.AfterGeometry = CaptureFullGeometry(part);
            plan.Outputs = outputs;
            plan.Applied = true;
            evidence["outputs"] = outputs;
            evidence["readback_verified"] = true;
            evidence["preservation_verified"] = true;
            TryDeleteUndoMark(state.Session, mark);
            return ParameterResult("APPLIED", binding.RevisionId, evidence, null, null);
        }
        catch (Exception ex) { error = ex.GetType().Name + ": " + ex.Message; }
        evidence["failed_step"] = stepId;
        evidence["operation_error"] = error;
        evidence["completed_before_rollback"] = outputs.Keys.ToArray();
        try
        {
            state.Session.UndoToMarkWithStatus(mark, "V3 composition rollback");
            int errors = state.Session.UpdateManager.DoUpdate(mark);
            CompositionReadTolerances(part, out currentDistance, out currentAngle);
            evidence["rollback_modeling_tolerances"] = CompositionToleranceEvidence(currentDistance, currentAngle);
            bool same = errors == 0 && CompositionSameTolerance(currentDistance, plan.BeforeDistanceTolerance) &&
                CompositionSameTolerance(currentAngle, plan.BeforeAngleTolerance) &&
                CanonicalSemanticSnapshot(Capture(binding, state).Snapshot) == plan.Before &&
                CaptureFullGeometry(part) == plan.BeforeGeometry && part.IsModified == plan.Dirty &&
                part.HasUserAttribute(V3CompositionArtifact, NXObject.AttributeType.String, 0) == plan.Marked;
            evidence["rollback_readback_verified"] = same;
            if (same)
            {
                TryDeleteUndoMark(state.Session, mark);
                return ParameterResult("ROLLED_BACK", binding.RevisionId, evidence, "COMPOSITION_FAILED", error);
            }
        }
        catch (Exception ex) { evidence["rollback_error"] = ex.GetType().Name + ": " + ex.Message; }
        return ParameterResult("UNKNOWN", binding.RevisionId, evidence, "ROLLBACK_UNVERIFIED", error);
    }

    public M2PartVerificationResult VerifyComposition(M2ModelBinding binding, V3BlockBindingSnapshot prepared)
    {
        BindingState state = RequireState(binding);
        var plan = prepared.AdapterState as V3CompositionPlan;
        string reason;
        if (plan == null || plan.Binding != state || !plan.Applied || !IsBindingCurrent(binding, out reason))
            throw new M2ModelException("INVALID_PLAN", "verified current composition required");
        Dictionary<string, Feature> features = CompositionFeatures(state.WorkPart);
        bool idsMatch = plan.Steps.Where(step => (string)step["kind"] != "expression").All(step =>
        {
            string id = (string)step["id"];
            Feature feature;
            return features.TryGetValue(id, out feature) && RequiredJournalId(feature, "composition feature") ==
                (string)((Dictionary<string, object>)plan.Outputs[id])["feature_id"];
        });
        double distance, angle;
        CompositionReadTolerances(state.WorkPart, out distance, out angle);
        bool tolerancesMatch = CompositionTolerancesMatch(distance, angle);
        bool same = idsMatch && tolerancesMatch && CanonicalSemanticSnapshot(Capture(binding, state).Snapshot) == plan.After &&
            CaptureFullGeometry(state.WorkPart) == plan.AfterGeometry;
        var checks = new Dictionary<string, object>();
        foreach (string key in new[] { "bindings", "geometry", "history", "non_target_preservation" })
            checks.Add(key, VerificationCheck(same ? "VERIFIED" : "MISMATCH", new Dictionary<string, object> {
                { "matches_execute", same }, { "logical_feature_ids_verified", idsMatch },
                { "modeling_tolerances", CompositionToleranceEvidence(distance, angle) }
            }));
        return new M2PartVerificationResult { Verified = same, RevisionId = binding.RevisionId, Checks = checks };
    }

    private static void CompositionReadTolerances(Part part, out double distance, out double angle)
    {
        UFSession.GetUFSession().Modl.AskDistanceToleranceOfPart(part.Tag, out distance);
        UFSession.GetUFSession().Modl.AskAngleToleranceOfPart(part.Tag, out angle);
    }

    private static bool CompositionSameTolerance(double actual, double expected)
    {
        return !Double.IsNaN(actual) && !Double.IsInfinity(actual) && Math.Abs(actual - expected) <= 1e-12;
    }

    private static bool CompositionTolerancesMatch(double distance, double angle)
    {
        return CompositionSameTolerance(distance, V3CompositionSolids.ModelingDistanceToleranceMm) &&
            CompositionSameTolerance(angle, V3CompositionSolids.ModelingAngleToleranceDeg);
    }

    private static Dictionary<string, object> CompositionToleranceEvidence(double distance, double angle)
    {
        return new Dictionary<string, object> {
            { "distance_mm", distance }, { "angle_degrees", angle },
            { "expected_distance_mm", V3CompositionSolids.ModelingDistanceToleranceMm },
            { "expected_angle_degrees", V3CompositionSolids.ModelingAngleToleranceDeg },
            { "verified", CompositionTolerancesMatch(distance, angle) }
        };
    }

    private static Feature CompositionProfileSolid(Part part, Dictionary<string, object> step, string kind,
        Dictionary<string, object> detail)
    {
        var frame = CompositionFrame(CompositionMap(step["frame"]));
        var edges = CompositionList(step, "edges").Select(CompositionMap).ToArray();
        Vector3d normal = new Vector3d(frame.XAxis.Y * frame.YAxis.Z - frame.XAxis.Z * frame.YAxis.Y,
            frame.XAxis.Z * frame.YAxis.X - frame.XAxis.X * frame.YAxis.Z, frame.XAxis.X * frame.YAxis.Y - frame.XAxis.Y * frame.YAxis.X);
        var curves = new Curve[edges.Length];
        var specs = edges.Select(CompositionEdge).ToArray();
        var sketchEdges = Enumerable.Range(0, edges.Length).Where(i => !edges[i].ContainsKey("point_expressions") &&
            !Object.Equals(edges[i].ContainsKey("method") ? edges[i]["method"] : null, "studio")).ToArray();
        var drivenSplines = new List<object>();
        var drivenCurves = new List<object>();
        if (sketchEdges.Length != 0)
        {
            Feature datum = M3NxFeatureFactory.CreateDatumPlane(part, frame.Origin, normal, frame.XAxis);
            Plane support = part.Planes.CreatePlane(PlaneTypes.MethodType.Coincident, PlaneTypes.AlternateType.One,
                frame.Origin, normal, null, false, false, new NXObject[] { ((DatumPlaneFeature)datum).DatumPlane });
            Sketch sketch = M3NxFeatureFactory.CreateSketchOnPlane(part, support, frame.Origin, normal, frame.XAxis);
            var dimensions = new List<object>();
            int dof;
            Sketch.Status status;
            try
            {
                var geometry = V3SketchConstraintBinding.Create(part, sketch, frame, sketchEdges.Select(i => specs[i]).ToArray());
                for (int j = 0; j < sketchEdges.Length; j++) curves[sketchEdges[j]] = geometry.Curves[j];
                foreach (int i in sketchEdges)
                {
                    if (!edges[i].ContainsKey("radius_expression")) continue;
                    Arc circle = (Arc)curves[i];
                    Expression expression = part.Expressions.ToArray().Single(e => e.Name == CompositionString(edges[i], "radius_expression"));
                    V3SketchConstraintBinding.CircleCenterAtOrigin(sketch, circle);
                    SketchDimensionalConstraint dimension = V3SketchConstraintBinding.DriveRadius(sketch, circle, expression,
                        new Point3d(circle.CenterPoint.X + circle.Radius * frame.XAxis.X, circle.CenterPoint.Y + circle.Radius * frame.XAxis.Y,
                            circle.CenterPoint.Z + circle.Radius * frame.XAxis.Z));
                    dimensions.Add(new Dictionary<string, object> {
                        { "constraint_id", RequiredJournalId(dimension, "driving radius") }, { "expression", expression.Name }
                    });
                }
                sketch.Update();
                sketch.CalculateStatus();
                status = sketch.GetStatus(out dof);
                if (status == Sketch.Status.OverConstrained || status == Sketch.Status.InconsistentlyConstrained ||
                    dimensions.Count != 0 && (status != Sketch.Status.WellConstrained || dof != 0))
                    throw new InvalidOperationException("NX sketch solver rejected constraints: " + status + " (" + dof + " DOF)");
            }
            finally { sketch.Deactivate(Sketch.ViewReorient.False, Sketch.UpdateLevel.Model); }
            detail["sketch_id"] = RequiredJournalId(sketch, "composition sketch");
            detail["driving_dimensions"] = dimensions;
            detail["sketch_status"] = status.ToString();
            detail["sketch_dof"] = dof;
        }
        var points = new Dictionary<string, V3SketchConstraintBinding.DrivenPoint>(StringComparer.Ordinal);
        var expressions = part.Expressions.ToArray().ToDictionary(e => e.Name, StringComparer.Ordinal);
        for (int i = 0; i < edges.Length; i++)
        {
            if (curves[i] != null) continue;
            curves[i] = edges[i].ContainsKey("point_expressions")
                ? CompositionDrivenEdge(part, frame, specs[i], edges[i], expressions, points, drivenCurves)
                : CompositionStudioSpline(part, frame, specs[i], edges[i], drivenSplines);
            curves[i].SetUserAttribute(V3SpatialPersistentId, 0,
                CompositionString(step, "id") + "/edge/" + i.ToString(CultureInfo.InvariantCulture), Update.Option.Now);
        }
        detail["studio_splines"] = drivenSplines;
        detail["driven_curves"] = drivenCurves;
        Section section = V3SketchConstraintBinding.CreateSection(part, new V3SketchConstraintBinding.ProfileResult { Curves = curves },
            frame.Origin, 0.0001, 0.0001, V3CompositionSolids.ModelingAngleToleranceDeg);
        double[] limits = CompositionExtent(step, kind);
        string startFormula = step.ContainsKey("start_formula") ? (string)step["start_formula"] : null;
        string endFormula = step.ContainsKey("end_formula") ? (string)step["end_formula"] : null;
        Feature feature;
        if (kind == "extrude")
            feature = V3CompositionSolids.CreateExtrude(part, section, CompositionDirection(step["direction"]),
                limits[0], limits[1], startFormula, endFormula);
        else
        {
            NXOpen.Point[] axisPoints = step.ContainsKey("axis_points_expressions")
                ? CompositionList(step, "axis_points_expressions").Cast<List<object>>().Select(row =>
                    V3SketchConstraintBinding.CreateDrivenPoint(part,
                        row.Cast<string>().Select(name => expressions[name]).ToArray()).Point).ToArray()
                : new NXOpen.Point[2];
            feature = V3CompositionSolids.CreateRevolve(part, section, CompositionPoint(step["axis_point"]),
                CompositionDirection(step["axis_direction"]), limits[0], limits[1], startFormula, endFormula,
                axisPoints[0], axisPoints[1]);
        }
        detail["native_limits"] = V3CompositionSolids.ReadLimits(part, feature);
        return feature;
    }

    private static Curve CompositionDrivenEdge(Part part, V3SketchConstraintBinding.Frame frame,
        V3SketchConstraintBinding.EdgeSpec spec, Dictionary<string, object> edge, Dictionary<string, Expression> expressions,
        Dictionary<string, V3SketchConstraintBinding.DrivenPoint> points, List<object> evidence)
    {
        bool line = spec.Kind == "line";
        var local = line ? new[] { spec.Start, spec.End } : new[] { spec.Start, spec.Mid, spec.End };
        var rows = CompositionList(edge, "point_expressions").Cast<List<object>>()
            .Select(row => row.Cast<string>().ToArray()).ToArray();
        var bound = new V3SketchConstraintBinding.DrivenPoint[rows.Length];
        for (int i = 0; i < rows.Length; i++)
        {
            var p = local[i];
            var xyz = new[] { frame.Origin.X + p.X*frame.XAxis.X + p.Y*frame.YAxis.X,
                frame.Origin.Y + p.X*frame.XAxis.Y + p.Y*frame.YAxis.Y,
                frame.Origin.Z + p.X*frame.XAxis.Z + p.Y*frame.YAxis.Z };
            Expression[] source = rows[i].Select(name => expressions[name]).ToArray();
            for (int j = 0; j < 3; j++)
                if (source[j].Units == null || source[j].Units.Symbol != "mm" || Math.Abs(source[j].Value - xyz[j]) > 1e-8)
                    throw CompositionInvalid("profile point expression disagrees with the expected " + spec.Kind + " point");
            string key = String.Join("|", rows[i]);
            if (!points.TryGetValue(key, out bound[i]))
            {
                bound[i] = V3SketchConstraintBinding.CreateDrivenPoint(part, source);
                points.Add(key, bound[i]);
            }
        }
        var result = line ? V3SketchConstraintBinding.CreateDrivenLine(part, bound[0], bound[1])
            : V3SketchConstraintBinding.CreateDrivenArc(part, bound[0], bound[1], bound[2]);
        var actual = V3SketchConstraintBinding.ReadDrivenCurve(result);
        if (!actual.FeatureAssociative || !actual.BuilderAssociative || actual.BuilderPoints.Length != rows.Length)
            throw new InvalidOperationException("native " + spec.Kind + " lacks its associative point definition");
        var directUsers = new bool[rows.Length][];
        for (int i = 0; i < rows.Length; i++)
        {
            if (actual.BuilderPoints[i] == null || actual.BuilderPoints[i].Tag != bound[i].Point.Tag ||
                !CompositionNearPoint(actual.PointCoordinates[i], new Point3d(
                    bound[i].Coordinates[0].Value, bound[i].Coordinates[1].Value, bound[i].Coordinates[2].Value)))
                throw new InvalidOperationException("native " + spec.Kind + " lost a selected expression point");
            directUsers[i] = Enumerable.Range(0, 3)
                .Select(j => actual.UsingFeatures[i,j].Any(f => f.Tag == result.Feature.Tag)).ToArray();
        }
        if (line && (!CompositionNearPoint(actual.LineStart, actual.PointCoordinates[0]) ||
            !CompositionNearPoint(actual.LineEnd, actual.PointCoordinates[1])))
            throw new InvalidOperationException("native line endpoints differ from their expression points");
        if (!line) CompositionVerifyArc((Arc)result.Curve, actual.PointCoordinates);
        result.Feature.SetUserAttribute(V3SharedCoordinateExpressions, 0, "1", Update.Option.Now);
        evidence.Add(new Dictionary<string, object> { { "feature_id", RequiredJournalId(result.Feature, "driven curve") },
            { "point_expressions", rows }, { "direct_expression_users", directUsers } });
        return result.Curve;
    }

    private static bool CompositionNearPoint(Point3d value, Point3d expected)
    {
        return Math.Abs(value.X - expected.X) <= 1e-8 && Math.Abs(value.Y - expected.Y) <= 1e-8 &&
            Math.Abs(value.Z - expected.Z) <= 1e-8;
    }

    private static void CompositionVerifyArc(Arc arc, Point3d[] points)
    {
        Point3d center;
        Vector3d x, y;
        arc.GetOrientation(out center, out x, out y);
        Point3d start = ConicPoint(center, x, y, arc.Radius, arc.Radius, 0.0, arc.StartAngle);
        Point3d end = ConicPoint(center, x, y, arc.Radius, arc.Radius, 0.0, arc.EndAngle);
        Vector3d off = new Vector3d(points[1].X - center.X, points[1].Y - center.Y, points[1].Z - center.Z);
        double angle = Math.Atan2(off.X*y.X + off.Y*y.Y + off.Z*y.Z, off.X*x.X + off.Y*x.Y + off.Z*x.Z);
        double turn = 2 * Math.PI;
        double forward = (angle - arc.StartAngle) % turn;
        if (forward < 0) forward += turn;
        double sweep = (arc.EndAngle - arc.StartAngle) % turn;
        if (sweep < 0) sweep += turn;
        bool endpoints = CompositionNearPoint(start, points[0]) && CompositionNearPoint(end, points[2]) ||
                         CompositionNearPoint(start, points[2]) && CompositionNearPoint(end, points[0]);
        if (!endpoints || forward > sweep + 1e-10 || !CompositionNearPoint(points[1],
            ConicPoint(center, x, y, arc.Radius, arc.Radius, 0.0, angle)))
            throw new InvalidOperationException("native arc does not follow the requested three-point branch");
    }

    private static Curve CompositionStudioSpline(Part part, V3SketchConstraintBinding.Frame frame,
        V3SketchConstraintBinding.EdgeSpec spec, Dictionary<string, object> edge, List<object> evidence)
    {
        if (spec.Kind != "spline" || spec.Order != 4 || spec.Weights.Any(w => w != 1.0) || spec.ActiveRange != null)
            throw CompositionInvalid("Studio Spline expects the clamped nonrational cubic FIN profile");
        Unit mm = part.UnitCollection.FindObject("MilliMeter");
        List<object> names = edge.ContainsKey("pole_expressions") ? CompositionList(edge, "pole_expressions") : null;
        if (names != null && names.Count != spec.Poles.Length) throw CompositionInvalid("pole expression count does not match basis");
        var coordinates = new Expression[spec.Poles.Length, 3];
        var existing = part.Expressions.ToArray().ToDictionary(e => e.Name, StringComparer.Ordinal);
        for (int i = 0; i < spec.Poles.Length; i++)
        {
            var p = spec.Poles[i];
            var xyz = new[] { frame.Origin.X + p.X*frame.XAxis.X + p.Y*frame.YAxis.X,
                frame.Origin.Y + p.X*frame.XAxis.Y + p.Y*frame.YAxis.Y,
                frame.Origin.Z + p.X*frame.XAxis.Z + p.Y*frame.YAxis.Z };
            var namesRow = names == null ? null : names[i] as List<object>;
            if (names != null && (namesRow == null || namesRow.Count != 3)) throw CompositionInvalid("expected XYZ pole expression names");
            for (int j = 0; j < 3; j++)
            {
                coordinates[i,j] = namesRow == null
                    ? part.Expressions.CreateSystemExpressionWithUnits(xyz[j].ToString("R", CultureInfo.InvariantCulture), mm)
                    : existing[(string)namesRow[j]];
                if (coordinates[i,j].Units == null || coordinates[i,j].Units.Tag != mm.Tag ||
                    Math.Abs(coordinates[i,j].Value - xyz[j]) > 1e-9)
                    throw CompositionInvalid("coordinate expression disagrees with the expected world pole");
            }
        }
        var driven = V3SketchConstraintBinding.CreateDrivenCubicSpline(part, coordinates, spec.Knots);
        var read = V3SketchConstraintBinding.ReadDrivenSpline(driven);
        if (!read.FeatureAssociative || read.Order != 4 || read.Rational || read.Periodic ||
            read.Knots.Length != spec.Knots.Length || read.Poles.Length != spec.Poles.Length)
            throw new InvalidOperationException("native Studio Spline basis differs from the requested FIN spline");
        for (int i = 0; i < read.Knots.Length; i++)
            if (Math.Abs(read.Knots[i] - spec.Knots[i]) > 1e-12)
                throw new InvalidOperationException("native Studio Spline knot differs from FIN");
        for (int i = 0; i < read.Poles.Length; i++)
        {
            var p = read.Poles[i];
            var v = new[] { p.X, p.Y, p.Z };
            if (p.W != 1.0) throw new InvalidOperationException("native FIN weight differs");
            for (int j = 0; j < 3; j++)
                if (Math.Abs(v[j] - coordinates[i,j].Value) > 1e-9 ||
                    !read.UsingFeatures[i,j].Any(f => f.Tag == driven.Feature.Tag))
                    throw new InvalidOperationException("native FIN pole or expression consumer differs");
        }
        driven.Feature.SetUserAttribute(V3SharedCoordinateExpressions, 0, "1", Update.Option.Now);
        evidence.Add(new Dictionary<string, object> {
            { "feature_id", RequiredJournalId(driven.Feature, "Studio Spline") },
            { "knots", read.Knots }, { "pole_count", read.Poles.Length }, { "named_coordinate_inputs", names != null }
        });
        return driven.Curve;
    }

    private static Dictionary<string, Feature> CompositionFeatures(Part part)
    {
        var result = new Dictionary<string, Feature>(StringComparer.Ordinal);
        foreach (Feature feature in part.Features.GetFeatures())
        {
            if (!feature.HasUserAttribute(V3CompositionNode, NXObject.AttributeType.String, 0)) continue;
            result.Add(feature.GetStringUserAttribute(V3CompositionNode, 0), feature);
        }
        return result;
    }

    private static Body[] CompositionActiveBodies(Part part, Feature feature)
    {
        if (feature.HasUserAttribute(V3CompositionConsumed, NXObject.AttributeType.String, 0)) return new Body[0];
        HashSet<Tag> live = new HashSet<Tag>(part.Bodies.ToArray().Select(b => b.Tag));
        return feature.GetBodies().Where(b => b.IsSolidBody && live.Contains(b.Tag)).ToArray();
    }

    private static void CompositionPreserved(Dictionary<string, object> before, Dictionary<string, object> after,
        List<object> priorSketches, List<object> currentSketches, HashSet<string> changedBodies)
    {
        PreserveCompositionRecords(CompositionSketchGeometryByTag(priorSketches),
            CompositionSketchGeometryByTag(currentSketches), "journal_id", null, null);
        PreserveCompositionRecords((List<object>)before["features"], (List<object>)after["features"], "journal_id",
            new[] { "child_ids", "body_ids" }, null);
        PreserveCompositionRecords((List<object>)before["bodies"], (List<object>)after["bodies"], "journal_id",
            new[] { "face_refs", "volume_mm3", "bbox_mm" }, changedBodies);
        List<object> priorBodies = BodyMeasurementProjection(before).Where(item =>
            !changedBodies.Contains((string)((Dictionary<string, object>)item)["journal_id"])).ToList();
        var preservedIds = new HashSet<string>(priorBodies.Select(item => (string)((Dictionary<string, object>)item)["journal_id"]));
        List<object> currentBodies = BodyMeasurementProjection(after).Where(item =>
            preservedIds.Contains((string)((Dictionary<string, object>)item)["journal_id"])).ToList();
        Dictionary<string, object> comparison;
        if (!BodyMeasurementRecordsEqual(priorBodies, currentBodies, out comparison))
            throw new InvalidOperationException("non-target body measurement preservation failed: " + M2Json.CanonicalText(comparison));
        PreserveCompositionRecords((List<object>)before["expressions"], (List<object>)after["expressions"], "name",
            new[] { "using_features", "referencing_expressions" }, null);
    }

    private static List<object> CompositionSketchGeometryByTag(List<object> sketches)
    {
        // This comparison stays within one part load. NX can relabel geometry
        // JournalIdentifier strings when unrelated feature history is appended.
        var result = (List<object>)DeepCloneValue(sketches);
        foreach (Dictionary<string, object> sketch in result)
        {
            object value;
            var geometry = sketch.TryGetValue("geometry", out value) ? value as List<object> : null;
            if (geometry == null) continue;
            var byTag = new Dictionary<string, object>(StringComparer.Ordinal);
            foreach (Dictionary<string, object> item in geometry)
            {
                item.Remove("journal_id");
                byTag.Add((string)item["tag"], item);
            }
            sketch["geometry"] = byTag;
        }
        return result;
    }

    private static void PreserveCompositionRecords(List<object> before, List<object> after, string key,
        string[] ignored, HashSet<string> excluded)
    {
        var current = after.Cast<Dictionary<string, object>>().ToDictionary(item => (string)item[key], StringComparer.Ordinal);
        foreach (Dictionary<string, object> item in before)
        {
            string id = (string)item[key];
            if (excluded != null && excluded.Contains(id)) continue;
            Dictionary<string, object> actual;
            if (!current.TryGetValue(id, out actual))
                throw new InvalidOperationException("non-target " + id + " is missing");
            foreach (var entry in item)
            {
                if (ignored != null && ignored.Contains(entry.Key)) continue;
                object observed;
                if (!actual.TryGetValue(entry.Key, out observed) || !SemanticValuesEqual(entry.Value, observed, entry.Key))
                    throw new InvalidOperationException("non-target preservation failed for " + id + "." +
                        CompositionDifference(entry.Value, observed, entry.Key));
            }
        }
    }

    private static string CompositionDifference(object before, object after, string key)
    {
        var oldMap = before as Dictionary<string, object>;
        var newMap = after as Dictionary<string, object>;
        if (oldMap != null && newMap != null && oldMap.Count == newMap.Count)
        {
            foreach (var item in oldMap)
            {
                object value;
                if (!newMap.TryGetValue(item.Key, out value) || !SemanticValuesEqual(item.Value, value, item.Key))
                    return key + "." + CompositionDifference(item.Value, value, item.Key);
            }
        }
        var oldList = before as List<object>;
        var newList = after as List<object>;
        if (oldList != null && newList != null)
        {
            if (oldList.Count != newList.Count) return key + " count " + oldList.Count + " / " + newList.Count;
            for (int i = 0; i < oldList.Count; i++)
                if (!SemanticValuesEqual(oldList[i], newList[i], key))
                    return key + "[" + i + "]." + CompositionDifference(oldList[i], newList[i], key);
        }
        string left = M2Json.CanonicalText(before);
        string right = M2Json.CanonicalText(after);
        return key + " (" + left.Substring(0, Math.Min(left.Length, 90)) + " / " +
            right.Substring(0, Math.Min(right.Length, 90)) + ")";
    }

    private static M2ModelException CompositionInvalid(string message)
    { return new M2ModelException("INVALID_COMPOSITION", message); }

    private static Dictionary<string, object> CompositionMap(object data)
    {
        var result = data as Dictionary<string, object>;
        if (result == null) throw CompositionInvalid("expected composition object");
        return result;
    }

    private static List<object> CompositionList(Dictionary<string, object> data, string key)
    {
        object value;
        var result = data.TryGetValue(key, out value) ? value as List<object> : null;
        if (result == null || result.Count == 0) throw CompositionInvalid(key + " must be a nonempty array");
        return result;
    }

    private static string CompositionString(Dictionary<string, object> data, string key)
    {
        object value;
        string result = data.TryGetValue(key, out value) ? value as string : null;
        if (String.IsNullOrWhiteSpace(result)) throw CompositionInvalid(key + " is required");
        return result;
    }

    private static bool CompositionRetainTools(Dictionary<string, object> step)
    {
        object retain;
        if (!step.TryGetValue("retain_tools", out retain) || !(retain is bool))
            throw CompositionInvalid("retain_tools must be boolean");
        return (bool)retain;
    }

    private static Unit CompositionUnit(Part part, Dictionary<string, object> step)
    {
        string unit = step.ContainsKey("unit") ? CompositionString(step, "unit") : "mm";
        if (unit == "mm") return part.UnitCollection.FindObject("MilliMeter");
        if (unit == "rad") return part.UnitCollection.FindObject("Radians");
        if (unit == "1") return null;
        throw CompositionInvalid("unsupported NX expression unit " + unit);
    }

    private static void CompositionPointReferences(Dictionary<string, object> data, string field, int count,
        HashSet<string> expressions)
    {
        List<object> rows = CompositionList(data, field);
        if (count == 0 || rows.Count != count || rows.Any(row =>
        {
            var names = row as List<object>;
            return names == null || names.Count != 3 || names.Any(value => !(value is string) || !expressions.Contains((string)value));
        }))
            throw CompositionInvalid(field + " requires three current coordinate expressions per point");
    }

    private static void CompositionFormula(Dictionary<string, object> data, string key, HashSet<string> expressions)
    {
        string formula = CompositionString(data, key);
        if (!Regex.IsMatch(formula, @"^[A-Za-z0-9_().+*/^ -]{1,200}$"))
            throw CompositionInvalid("composition formula contains unsupported syntax");
        var functions = new HashSet<string>(new[] { "sin", "cos", "tan", "sqrt" }, StringComparer.Ordinal);
        foreach (Match match in Regex.Matches(formula, @"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]*"))
        {
            bool function = formula.Substring(match.Index + match.Length).TrimStart().StartsWith("(");
            if (function ? !functions.Contains(match.Value) : !expressions.Contains(match.Value))
                throw CompositionInvalid("unsupported composition formula operand " + match.Value);
        }
    }

    private static double CompositionNumber(object value)
    {
        if (!(value is double) && !(value is long) && !(value is int) && !(value is decimal))
            throw CompositionInvalid("expected a finite composition number");
        double result = Convert.ToDouble(value, CultureInfo.InvariantCulture);
        if (Double.IsInfinity(result) || Double.IsNaN(result)) throw CompositionInvalid("non-finite composition number");
        return result;
    }

    private static double[] CompositionVector(object value, int size)
    {
        var list = value as List<object>;
        if (list == null || list.Count != size) throw CompositionInvalid("wrong composition vector length");
        return list.Select(CompositionNumber).ToArray();
    }

    private static Point3d CompositionPoint(object value)
    {
        double[] a = CompositionVector(value, 3);
        return new Point3d(a[0], a[1], a[2]);
    }

    private static Vector3d CompositionDirection(object value)
    {
        double[] a = CompositionVector(value, 3);
        return new Vector3d(a[0], a[1], a[2]);
    }

    private static V3SketchConstraintBinding.Point2 CompositionPoint2(object value)
    {
        double[] a = CompositionVector(value, 2);
        return new V3SketchConstraintBinding.Point2(a[0], a[1]);
    }

    private static V3SketchConstraintBinding.Frame CompositionFrame(Dictionary<string, object> data)
    {
        return new V3SketchConstraintBinding.Frame { Origin = CompositionPoint(data["origin"]),
            XAxis = CompositionDirection(data["x_axis"]), YAxis = CompositionDirection(data["y_axis"]) };
    }

    private static V3SketchConstraintBinding.EdgeSpec CompositionEdge(Dictionary<string, object> edge)
    {
        var result = new V3SketchConstraintBinding.EdgeSpec { Kind = CompositionString(edge, "kind") };
        switch (result.Kind)
        {
            case "line":
            case "arc":
                result.Start = CompositionPoint2(edge["start"]);
                result.End = CompositionPoint2(edge["end"]);
                if (result.Kind == "arc") result.Mid = CompositionPoint2(edge["mid"]);
                break;
            case "circle":
                result.Center = CompositionPoint2(edge["center"]);
                result.Radius = CompositionNumber(edge["radius"]);
                break;
            case "spline":
                result.Order = Convert.ToInt32(CompositionNumber(edge["order"]));
                result.Knots = CompositionList(edge, "knots").Select(CompositionNumber).ToArray();
                if (edge.ContainsKey("active_range")) result.ActiveRange = CompositionVector(edge["active_range"], 2);
                double[][] poles = CompositionList(edge, "poles").Select(p => CompositionVector(p, 3)).ToArray();
                result.Poles = poles.Select(p => new V3SketchConstraintBinding.Point2(p[0], p[1])).ToArray();
                result.Weights = poles.Select(p => p[2]).ToArray();
                break;
            default:
                throw CompositionInvalid("unsupported profile edge " + result.Kind);
        }
        return result;
    }

    private static double[] CompositionExtent(Dictionary<string, object> step, string kind)
    {
        bool extrude = kind == "extrude";
        if (extrude) CompositionDirection(step["direction"]);
        else
        {
            CompositionPoint(step["axis_point"]);
            CompositionDirection(step["axis_direction"]);
        }
        double start = CompositionNumber(step[extrude ? "start" : "start_degrees"]);
        double end = CompositionNumber(step[extrude ? "end" : "end_degrees"]);
        if (start >= end || !extrude && end - start > 360) throw CompositionInvalid("invalid feature limits");
        return new[] { start, end };
    }
}
