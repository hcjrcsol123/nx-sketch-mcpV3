using System;
using System.Collections.Generic;
using System.Globalization;
using NXOpen;
using NXOpen.Features;
using NXOpen.GeometricUtilities;

// Dictionary uses the same equality comparer as HashSet without requiring
// a Tag ordering or a System.Core reference.
internal sealed class UG11TagSet
{
    private readonly Dictionary<Tag, bool> tags = new Dictionary<Tag, bool>();
    public int Count { get { return tags.Count; } }
    public bool Add(Tag tag) {
        if (tags.ContainsKey(tag)) return false;
        tags.Add(tag, true); return true;
    }
    public bool SetEquals(UG11TagSet other) {
        if (other == null || tags.Count != other.tags.Count) return false;
        foreach (Tag tag in tags.Keys) if (!other.tags.ContainsKey(tag)) return false;
        return true;
    }
}

// Narrow native solid operations for the P3 construction route. The caller owns
// the transaction, section construction, model update, and rollback on failure.
public static class UG11ExtrudeSolids
{
    public const double ModelingDistanceToleranceMm = 0.00025;
    public const double ModelingAngleToleranceDeg = 0.01;

    public static Feature CreateExtrude(Part part, Section section, Vector3d direction,
        double startMm, double endMm, string startFormula = null, string endFormula = null)
    {
        RequirePart(part); RequireInterval(startMm, endMm, "extrusion");
        Vector3d unit = Unit(direction);
        UG11TagSet inputs = SectionInputs(section);
        Direction d = part.Directions.CreateDirection(new Point3d(0, 0, 0), unit, SmartObject.UpdateOption.WithinModeling);
        Feature feature; ExtrudeBuilder b = part.Features.CreateExtrudeBuilder(null);
        try {
            b.Section = section; b.Direction = d;
            b.SetToleranceValues(ModelingDistanceToleranceMm, section.ChainingTolerance,
                ModelingDistanceToleranceMm, ModelingAngleToleranceDeg);
            b.FeatureOptions.BodyType = FeatureOptions.BodyStyle.Solid;
            b.Draft.DraftOption = SimpleDraft.SimpleDraftType.NoDraft;
            b.Draft.DraftAngle.RightHandSide = "0"; b.Draft.FrontDraftAngle.RightHandSide = "0"; b.Draft.BackDraftAngle.RightHandSide = "0";
            b.Offset.Option = NXOpen.GeometricUtilities.Type.NoOffset;
            b.Offset.StartOffset.RightHandSide = "0"; b.Offset.EndOffset.RightHandSide = "0";
            b.Limits.StartExtend.TrimType = Extend.ExtendType.Value; b.Limits.EndExtend.TrimType = Extend.ExtendType.Value;
            b.Limits.StartExtend.Value.RightHandSide = Formula(startFormula, startMm);
            b.Limits.EndExtend.Value.RightHandSide = Formula(endFormula, endMm);
            b.BooleanOperation.Type = BooleanOperation.BooleanType.Create;
            if (!b.Validate()) throw new InvalidOperationException("NX rejected the finite extrusion.");
            feature = b.CommitFeature();
        } finally { b.Destroy(); }
        RequireOneSolid(part, feature);
        ExtrudeBuilder read = part.Features.CreateExtrudeBuilder(feature);
        try {
            if (read.BooleanOperation.Type != BooleanOperation.BooleanType.Create || read.FeatureOptions.BodyType != FeatureOptions.BodyStyle.Solid ||
                read.Limits.StartExtend.TrimType != Extend.ExtendType.Value || read.Limits.EndExtend.TrimType != Extend.ExtendType.Value ||
                !Near(read.Limits.StartExtend.Value.Value, startMm) || !Near(read.Limits.EndExtend.Value.Value, endMm) ||
                read.Direction == null || !VectorNear(read.Direction.Vector, unit) || !inputs.SetEquals(SectionInputs(read.Section)))
                throw new InvalidOperationException("Committed extrusion differs from its native section, direction, finite limits, or create definition.");
            VerifyFormula(read.Limits.StartExtend.Value, startFormula); VerifyFormula(read.Limits.EndExtend.Value, endFormula);
            if (!SameTolerance(read.DistanceTolerance, ModelingDistanceToleranceMm) ||
                !SameTolerance(read.AngularTolerance, ModelingAngleToleranceDeg))
                throw new InvalidOperationException("Committed extrusion did not retain the requested modeling tolerances.");
        } finally { read.Destroy(); }
        return feature;
    }

    public static Feature CreatePrism(Part part, Point3d origin, Vector3d xAxis, Vector3d yAxis,
        double xLength, double yLength, double zLength)
    {
        RequirePart(part); RequirePoint(origin);
        Vector3d x = Unit(xAxis), y = Unit(yAxis);
        if (Math.Abs(x.X*y.X + x.Y*y.Y + x.Z*y.Z) > 1e-10) throw new ArgumentException("Prism axes must be orthogonal.");
        Positive(xLength); Positive(yLength); Positive(zLength);
        Feature feature; BlockFeatureBuilder b = part.Features.CreateBlockFeatureBuilder(null);
        try {
            b.SetOriginAndLengths(origin, Number(xLength), Number(yLength), Number(zLength));
            b.SetOrientation(x, y); b.SetBooleanOperationAndTarget(Feature.BooleanType.Create, null);
            if (!b.Validate()) throw new InvalidOperationException("NX rejected the finite clipping prism.");
            feature = b.CommitFeature();
        } finally { b.Destroy(); }
        RequireOneSolid(part, feature);
        BlockFeatureBuilder read = part.Features.CreateBlockFeatureBuilder(feature);
        try {
            Vector3d rx, ry; read.GetOrientation(out rx, out ry);
            if (read.BooleanType != Feature.BooleanType.Create || !PointNear(read.Origin, origin) ||
                !VectorNear(rx, x) || !VectorNear(ry, y) || !Near(read.Length.Value, xLength) ||
                !Near(read.Width.Value, yLength) || !Near(read.Height.Value, zLength))
                throw new InvalidOperationException("Committed clipping prism differs from its origin, axes, lengths, or create definition.");
        } finally { read.Destroy(); }
        return feature;
    }

    // retainTarget is intentionally unsupported: place stock in the tool slot
    // and retainTools=true for the roll/stock intersection.
    public static Feature Boolean(Part part, string operation, Body target, Body[] tools, bool retainTarget, bool retainTools)
    {
        if (retainTarget) throw new ArgumentException("Place the body to retain in the tool collector.", "retainTarget");
        Feature f = UG11BooleanFactory.Create(part, operation, target, tools, retainTools, ModelingDistanceToleranceMm);
        // V2 verifies all output solids; a Boolean may produce several bodies.
        return f;
    }

    // Reopening a builder exposes both evaluated limits and their native RHS.
    public static Dictionary<string, object> ReadLimits(Part part, Feature feature)
    {
        RequirePart(part);
        if (feature is Extrude) {
            ExtrudeBuilder b = part.Features.CreateExtrudeBuilder(feature);
            try {
                var limits = Limits(b.Limits.StartExtend.Value, b.Limits.EndExtend.Value);
                limits["distance_tolerance_mm"] = b.DistanceTolerance;
                limits["angle_tolerance_deg"] = b.AngularTolerance;
                return limits;
            } finally { b.Destroy(); }
        }
        throw new ArgumentException("Expected native Extrude.", "feature");
    }
    private static Dictionary<string, object> Limits(Expression a, Expression b) {
        return new Dictionary<string, object> { {"start_value", a.Value}, {"end_value", b.Value}, {"start_rhs", a.RightHandSide}, {"end_rhs", b.RightHandSide} };
    }
    private static void VerifyFormula(Expression value, string formula) {
        if (!String.IsNullOrWhiteSpace(formula) && !String.Equals(
            System.Text.RegularExpressions.Regex.Replace(value.RightHandSide, @"\s", ""),
            System.Text.RegularExpressions.Regex.Replace(formula, @"\s", ""), StringComparison.Ordinal))
            throw new InvalidOperationException("Committed native limit does not retain the requested formula.");
    }
    private static UG11TagSet SectionInputs(Section section) {
        if (section == null) throw new ArgumentNullException("section");
        SectionData[] data; section.GetSectionData(out data);
        if (data == null || data.Length == 0) throw new InvalidOperationException("Section has no native input data.");
        UG11TagSet tags = new UG11TagSet();
        foreach (SectionData item in data) {
            if (item == null) throw new InvalidOperationException("Section contains null data.");
            SectionElementData[] elements; item.GetSectionElementsData(out elements);
            if (elements == null) throw new InvalidOperationException("Section elements are unavailable.");
            foreach (SectionElementData e in elements) {
                if (e == null) throw new InvalidOperationException("Section contains a null element.");
                DisplayableObject selected, a, b; Point3d pa, pb;
                try { e.GetSectionElementData1(out selected, out a, out pa, out b, out pb);
                    if (selected == null || !tags.Add(selected.Tag)) throw new InvalidOperationException("Section inputs must be distinct and readable.");
                } finally { e.Dispose(); }
            }
            item.Dispose();
        }
        if (tags.Count == 0) throw new InvalidOperationException("Section has no selected input objects.");
        return tags;
    }
    private static void RequireOneSolid(Part part, Feature f) {
        if (f == null || f.OwningPart == null || f.OwningPart.Tag != part.Tag) throw new InvalidOperationException("NX returned no feature in the work part.");
        BodyFeature bodyFeature = f as BodyFeature;
        if (bodyFeature == null) throw new InvalidOperationException("Feature does not expose native body outputs.");
        Body[] bodies = bodyFeature.GetBodies();
        if (bodies == null || bodies.Length != 1 || bodies[0] == null || !bodies[0].IsSolidBody || bodies[0].OwningPart.Tag != part.Tag)
            throw new InvalidOperationException("NX did not return exactly one solid output. Empty or disconnected results cannot be represented by this operation.");
    }
    private static void RequirePart(Part p) { if (p == null || p.PartUnits != BasePart.Units.Millimeters) throw new ArgumentException("A millimeter part is required.", "part"); }
    private static void RequireInterval(double a, double b, string label) { Finite(a); Finite(b); if (!(b > a)) throw new ArgumentException(label + " end must exceed start."); }
    private static void Positive(double x) { Finite(x); if (!(x > 0)) throw new ArgumentOutOfRangeException("length"); }
    private static void Finite(double x) { if (Double.IsNaN(x) || Double.IsInfinity(x)) throw new ArgumentException("Finite value required."); }
    private static void RequirePoint(Point3d p) { Finite(p.X); Finite(p.Y); Finite(p.Z); }
    private static Vector3d Unit(Vector3d v) {
        Finite(v.X); Finite(v.Y); Finite(v.Z); double scale = Math.Max(Math.Abs(v.X), Math.Max(Math.Abs(v.Y), Math.Abs(v.Z)));
        if (scale == 0) throw new ArgumentException("Direction must be nonzero.");
        double x = v.X/scale, y = v.Y/scale, z = v.Z/scale, length = Math.Sqrt(x*x+y*y+z*z);
        return new Vector3d(x/length,y/length,z/length);
    }
    private static bool Near(double a, double b) { return !Double.IsNaN(a) && !Double.IsInfinity(a) && Math.Abs(a-b) <= 1e-8 * Math.Max(1.0, Math.Abs(b)); }
    private static bool SameTolerance(double a, double b) { return Math.Abs(a-b) <= 1e-12; }
    private static bool VectorNear(Vector3d a, Vector3d b) { return Near(a.X,b.X) && Near(a.Y,b.Y) && Near(a.Z,b.Z); }
    private static bool PointNear(Point3d a, Point3d b) { return Near(a.X,b.X) && Near(a.Y,b.Y) && Near(a.Z,b.Z); }
    private static string Number(double x) { return x.ToString("R", CultureInfo.InvariantCulture); }
    private static string Formula(string formula, double value) { return String.IsNullOrWhiteSpace(formula) ? Number(value) : formula; }
}

public sealed class UG11BooleanBuilderCleanupException : Exception
{
    public UG11BooleanBuilderCleanupException(string message, Exception inner) : base(message, inner) { }
}

/// <summary>Native Boolean feature operations. The caller owns the NX transaction and rollback.</summary>
public static class UG11BooleanFactory
{
    public static Feature Create(Part part, string operation, Body target, Body[] tools, bool retainTools)
    {
        return Create(part, operation, target, tools, retainTools, null);
    }

    public static Feature Create(Part part, string operation, Body target, Body[] tools, bool retainTools, double? distanceToleranceMm)
    {
        if (part == null) throw new ArgumentNullException("part");
        Feature.BooleanType nativeOperation = ParseOperation(operation);
        CheckBody(part, target, "target");
        if (tools == null || tools.Length == 0) throw new ArgumentException("At least one tool body is required.", "tools");
        UG11TagSet tags = new UG11TagSet();
        tags.Add(target.Tag);
        foreach (Body body in tools)
        {
            CheckBody(part, body, "tools");
            if (!tags.Add(body.Tag)) throw new ArgumentException("Target and tool bodies must be distinct.", "tools");
        }
        string[] expectedTargetTags = Tags(new Body[] { target });
        string[] expectedToolTags = Tags(tools);
        BooleanBuilder builder = null;
        Feature feature;
        try
        {
            builder = part.Features.CreateBooleanBuilderUsingCollector(null);
            if (builder == null) throw new InvalidOperationException("NX did not create a Boolean builder.");
            builder.Operation = nativeOperation;
            builder.RetainTarget = false;
            builder.RetainTool = retainTools;
            builder.ConvertToSew = false;
            if (distanceToleranceMm.HasValue) builder.Tolerance = distanceToleranceMm.Value;
            ScCollector toolCollector = part.ScCollectors.CreateCollector();
            if (toolCollector == null) throw new InvalidOperationException("NX did not create the Boolean tool collector.");
            builder.Targets.Add(target);
            toolCollector.ReplaceRules(new SelectionIntentRule[] { part.ScRuleFactory.CreateRuleBodyDumb(tools) }, false);
            builder.ToolBodyCollector = toolCollector;
            if (!builder.Validate()) throw new InvalidOperationException("NX rejected the Boolean definition.");
            feature = builder.CommitFeature();
            if (!(feature is BooleanFeature)) throw new InvalidOperationException("NX did not return a native BooleanFeature.");
        }
        finally { if (builder != null) Destroy(builder); }
        Dictionary<string, object> read = Read(part, feature, distanceToleranceMm);
        if ((string)read["operation"] != operation || (bool)read["retain_tools"] != retainTools ||
            !SameTags((string[])read["target_body_tags"], expectedTargetTags) ||
            !SameTags((string[])read["tool_body_tags"], expectedToolTags))
            throw new InvalidOperationException("Native Boolean associations or retain policy do not match the request: operation=" + operation + "/" + read["operation"] +
                ", retain=" + retainTools + "/" + read["retain_tools"] + ", target_tags=" + String.Join(",", expectedTargetTags) + "/" + String.Join(",", (string[])read["target_body_tags"]) +
                ", tool_tags=" + String.Join(",", expectedToolTags) + "/" + String.Join(",", (string[])read["tool_body_tags"]) + ".");
        return feature;
    }

    public static Dictionary<string, object> Read(Part part, Feature feature)
    {
        return Read(part, feature, null);
    }

    private static Dictionary<string, object> Read(Part part, Feature feature, double? expectedToleranceMm)
    {
        if (part == null) throw new ArgumentNullException("part");
        BooleanFeature boolean = feature as BooleanFeature;
        if (boolean == null || boolean.OwningPart == null || !boolean.OwningPart.Tag.Equals(part.Tag))
            throw new ArgumentException("A native BooleanFeature in the supplied part is required.", "feature");
        BooleanBuilder builder = null;
        try
        {
            builder = part.Features.CreateBooleanBuilderUsingCollector(boolean);
            if (builder == null) throw new InvalidOperationException("NX did not reopen the Boolean feature.");
            if (expectedToleranceMm.HasValue && !(Math.Abs(builder.Tolerance - expectedToleranceMm.Value) <= 1e-12))
                throw new InvalidOperationException("Committed Boolean did not retain the requested distance tolerance.");
            string operation = OperationName(builder.Operation);
            if (builder.RetainTarget || builder.CopyTargets || builder.CopyTools != builder.RetainTool || builder.ConvertToSew)
                throw new InvalidOperationException("Unsupported or inconsistent native Boolean target, retain, or sew policy.");
            Body[] targets = builder.Targets.GetArray();
            foreach (Body body in targets) CheckBody(part, body, "target");
            Body[] tools = CollectorBodies(part, builder.ToolBodyCollector, "tool");
            if (targets.Length != 1 || tools.Length == 0) throw new InvalidOperationException("Expected one Boolean target and at least one tool.");
            UG11TagSet inputs = new UG11TagSet();
            foreach (Body body in targets) inputs.Add(body.Tag);
            foreach (Body body in tools) if (!inputs.Add(body.Tag)) throw new InvalidOperationException("Boolean input bodies are not distinct.");
            BodyFeature bodyFeature = feature as BodyFeature;
            if (bodyFeature == null) throw new InvalidOperationException("Boolean feature does not expose native body outputs.");
            Body[] outputs = bodyFeature.GetBodies();
            if (outputs == null || outputs.Length == 0) throw new InvalidOperationException("NX returned no Boolean output bodies.");
            UG11TagSet outputTags = new UG11TagSet();
            foreach (Body body in outputs)
            {
                CheckBody(part, body, "output");
                if (!outputTags.Add(body.Tag)) throw new InvalidOperationException("NX returned duplicate Boolean output bodies.");
            }
            return new Dictionary<string, object> {
                { "feature_id", Id(feature) }, { "feature_tag", feature.Tag.ToString() },
                { "operation", operation }, { "native_operation", builder.Operation.ToString() },
                { "retain_tools", builder.RetainTool }, { "retain_target", builder.RetainTarget },
                { "copy_targets", builder.CopyTargets }, { "copy_tools", builder.CopyTools },
                { "target_body_ids", Ids(targets) }, { "target_body_tags", Tags(targets) },
                { "tool_body_ids", Ids(tools) }, { "tool_body_tags", Tags(tools) },
                { "output_body_ids", Ids(outputs) }, { "output_body_tags", Tags(outputs) }
            };
        }
        finally { if (builder != null) Destroy(builder); }
    }

    private static Feature.BooleanType ParseOperation(string operation)
    {
        if (operation == "unite") return Feature.BooleanType.Unite;
        if (operation == "subtract") return Feature.BooleanType.Subtract;
        if (operation == "intersect") return Feature.BooleanType.Intersect;
        throw new ArgumentException("Operation must be unite, subtract, or intersect.", "operation");
    }
    private static string OperationName(Feature.BooleanType operation)
    {
        if (operation == Feature.BooleanType.Unite) return "unite";
        if (operation == Feature.BooleanType.Subtract) return "subtract";
        if (operation == Feature.BooleanType.Intersect) return "intersect";
        throw new InvalidOperationException("Unsupported native Boolean operation.");
    }
    private static void CheckBody(Part part, Body body, string label)
    {
        if (body == null || body.OwningPart == null || !body.OwningPart.Tag.Equals(part.Tag) || !body.IsSolidBody)
            throw new ArgumentException("A solid " + label + " body in the supplied part is required.", label);
    }
    private static Body[] CollectorBodies(Part part, ScCollector collector, string label)
    {
        if (collector == null) throw new InvalidOperationException("Missing native Boolean " + label + " collector.");
        TaggedObject[] objects = collector.GetObjects();
        if (objects == null) throw new InvalidOperationException("Cannot read native Boolean " + label + " collector.");
        Body[] bodies = new Body[objects.Length];
        for (int i = 0; i < objects.Length; i++)
        {
            bodies[i] = objects[i] as Body;
            CheckBody(part, bodies[i], label);
        }
        return bodies;
    }
    private static string Id(NXObject obj)
    {
        string id = obj.JournalIdentifier;
        if (String.IsNullOrWhiteSpace(id)) throw new InvalidOperationException("NX object has no journal identifier.");
        return id;
    }
    private static string[] Ids(Body[] bodies)
    {
        string[] ids = new string[bodies.Length];
        for (int i = 0; i < bodies.Length; i++) ids[i] = Id(bodies[i]);
        return ids;
    }
    private static string[] Tags(Body[] bodies)
    {
        string[] tags = new string[bodies.Length];
        for (int i = 0; i < bodies.Length; i++) tags[i] = bodies[i].Tag.ToString();
        return tags;
    }
    private static bool SameTags(string[] observed, string[] expected)
    {
        if (observed.Length != expected.Length) return false;
        SortedSet<string> tags = new SortedSet<string>(observed, StringComparer.Ordinal);
        if (tags.Count != expected.Length) return false;
        foreach (string tag in expected) if (!tags.Remove(tag)) return false;
        return tags.Count == 0;
    }
    private static void Destroy(BooleanBuilder builder)
    {
        try { builder.Destroy(); }
        catch (Exception error) { throw new UG11BooleanBuilderCleanupException("NX Boolean builder destruction failed; model state is unknown.", error); }
    }
}
