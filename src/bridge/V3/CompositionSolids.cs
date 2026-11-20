using System;
using System.Collections.Generic;
using System.Globalization;
using NXOpen;
using NXOpen.Features;
using NXOpen.GeometricUtilities;

// Narrow native solid operations for the P3 construction route. The caller owns
// the transaction, section construction, model update, and rollback on failure.
public static class V3CompositionSolids
{
    public const double ModelingDistanceToleranceMm = 0.00025;
    public const double ModelingAngleToleranceDeg = 0.01;

    public static Feature CreateExtrude(Part part, Section section, Vector3d direction,
        double startMm, double endMm, string startFormula = null, string endFormula = null)
    {
        RequirePart(part); RequireInterval(startMm, endMm, "extrusion");
        Vector3d unit = Unit(direction);
        HashSet<Tag> inputs = SectionInputs(section);
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

    public static Feature CreateRevolve(Part part, Section section, Point3d axisPoint, Vector3d axisDirection,
        double startDeg, double endDeg, string startFormula = null, string endFormula = null,
        Point axisStart = null, Point axisEnd = null)
    {
        RequirePart(part); RequirePoint(axisPoint); RequireInterval(startDeg, endDeg, "revolution");
        if (endDeg - startDeg > 360.0 || startDeg < -360.0 || endDeg > 360.0)
            throw new ArgumentOutOfRangeException("endDeg", "Revolution must have a positive span of at most 360 degrees within +/-360 degrees.");
        Vector3d unit = Unit(axisDirection); HashSet<Tag> inputs = SectionInputs(section);
        if ((axisStart == null) != (axisEnd == null))
            throw new ArgumentException("Both associative axis points must be supplied together.");
        Point p;
        Direction d;
        if (axisStart != null) {
            if (axisStart.OwningPart == null || axisEnd.OwningPart == null ||
                axisStart.OwningPart.Tag != part.Tag || axisEnd.OwningPart.Tag != part.Tag || axisStart.Tag == axisEnd.Tag)
                throw new ArgumentException("Associative axis points must be distinct points in the work part.");
            Point3d a = axisStart.Coordinates, z = axisEnd.Coordinates;
            RequirePoint(a); RequirePoint(z);
            Vector3d actual = Unit(new Vector3d(z.X - a.X, z.Y - a.Y, z.Z - a.Z));
            if (!PointNear(a, axisPoint) || !VectorNear(actual, unit))
                throw new ArgumentException("Associative axis points differ from the expected axis point and direction.");
            p = axisStart;
            d = part.Directions.CreateDirection(axisStart, axisEnd, SmartObject.UpdateOption.WithinModeling);
        } else {
            p = part.Points.CreatePoint(axisPoint);
            d = part.Directions.CreateDirection(axisPoint, unit, SmartObject.UpdateOption.WithinModeling);
        }
        Axis axis = part.Axes.CreateAxis(p, d, SmartObject.UpdateOption.WithinModeling);
        Feature feature; RevolveBuilder b = part.Features.CreateRevolveBuilder(null);
        try {
            b.Section = section; b.Axis = axis; b.FeatureOptions.BodyType = FeatureOptions.BodyStyle.Solid;
            b.Limits.StartExtend.TrimType = Extend.ExtendType.Value; b.Limits.EndExtend.TrimType = Extend.ExtendType.Value;
            b.Limits.SymmetricOption = false;
            b.Offset.Option = NXOpen.GeometricUtilities.Type.NoOffset;
            b.Offset.StartOffset.RightHandSide = "0"; b.Offset.EndOffset.RightHandSide = "0";
            b.Tolerance = ModelingDistanceToleranceMm;
            b.Limits.StartExtend.Value.RightHandSide = Formula(startFormula, startDeg);
            b.Limits.EndExtend.Value.RightHandSide = Formula(endFormula, endDeg);
            b.BooleanOperation.Type = BooleanOperation.BooleanType.Create;
            if (!b.Limits.Validate() || !b.Validate()) throw new InvalidOperationException("NX rejected the finite revolution.");
            feature = b.CommitFeature();
        } finally { b.Destroy(); }
        RequireOneSolid(part, feature);
        RevolveBuilder read = part.Features.CreateRevolveBuilder(feature);
        try {
            if (read.BooleanOperation.Type != BooleanOperation.BooleanType.Create || read.FeatureOptions.BodyType != FeatureOptions.BodyStyle.Solid ||
                read.Limits.StartExtend.TrimType != Extend.ExtendType.Value || read.Limits.EndExtend.TrimType != Extend.ExtendType.Value ||
                !Near(read.Limits.StartExtend.Value.Value, startDeg) || !Near(read.Limits.EndExtend.Value.Value, endDeg) ||
                read.Axis == null || read.Axis.Point == null || read.Axis.Direction == null ||
                !PointNear(read.Axis.Point.Coordinates, axisPoint) || !VectorNear(read.Axis.Direction.Vector, unit) ||
                !inputs.SetEquals(SectionInputs(read.Section)))
                throw new InvalidOperationException("Committed revolution differs from its native section, axis, finite limits, or create definition.");
            if (axisStart != null && (read.Axis.Point.Tag != axisStart.Tag || read.Axis.Direction.Tag != d.Tag))
                throw new InvalidOperationException("Committed revolution did not retain the associative axis objects.");
            VerifyFormula(read.Limits.StartExtend.Value, startFormula); VerifyFormula(read.Limits.EndExtend.Value, endFormula);
            if (!SameTolerance(read.Tolerance, ModelingDistanceToleranceMm) ||
                !SameTolerance(read.Section.AngleTolerance, ModelingAngleToleranceDeg))
                throw new InvalidOperationException("Committed revolution did not retain the requested modeling tolerances.");
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
        Feature f = V2BooleanFactory.Create(part, operation, target, tools, retainTools, ModelingDistanceToleranceMm);
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
        if (feature is Revolve) {
            RevolveBuilder b = part.Features.CreateRevolveBuilder(feature);
            try {
                var limits = Limits(b.Limits.StartExtend.Value, b.Limits.EndExtend.Value);
                limits["distance_tolerance_mm"] = b.Tolerance;
                limits["angle_tolerance_deg"] = b.Section.AngleTolerance;
                return limits;
            } finally { b.Destroy(); }
        }
        throw new ArgumentException("Expected native Extrude or Revolve.", "feature");
    }
    private static Dictionary<string, object> Limits(Expression a, Expression b) {
        return new Dictionary<string, object> { {"start_value", a.Value}, {"end_value", b.Value}, {"start_rhs", a.RightHandSide}, {"end_rhs", b.RightHandSide} };
    }
    private static void VerifyFormula(Expression value, string formula) {
        if (!String.IsNullOrWhiteSpace(formula) && !String.Equals(
            String.Concat(System.Linq.Enumerable.Where(value.RightHandSide, c => !Char.IsWhiteSpace(c))),
            String.Concat(System.Linq.Enumerable.Where(formula, c => !Char.IsWhiteSpace(c))), StringComparison.Ordinal))
            throw new InvalidOperationException("Committed native limit does not retain the requested formula.");
    }
    private static HashSet<Tag> SectionInputs(Section section) {
        if (section == null) throw new ArgumentNullException("section");
        SectionData[] data; section.GetSectionData(out data);
        if (data == null || data.Length == 0) throw new InvalidOperationException("Section has no native input data.");
        HashSet<Tag> tags = new HashSet<Tag>();
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
        Body[] bodies = f.GetBodies();
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
