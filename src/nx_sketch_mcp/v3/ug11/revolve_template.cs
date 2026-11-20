using System;
using System.Collections.Generic;
using System.Globalization;
using NXOpen;
using NXOpen.Features;
using NXOpen.GeometricUtilities;
using NXOpen.UF;

// UG11 port of V3CompositionSolids.CreateRevolve. The caller owns the part,
// ordered updates, transaction, native evidence persistence and failure policy.
public static class Ug11Revolve {
    public const double ModelingDistanceToleranceMm = 0.00025;
    public const double ModelingAngleToleranceDeg = 0.01;
    public static Feature CreateRevolve(Part part, Section section, Point3d axisPoint, Vector3d axisDirection,
        double startDeg, double endDeg, string startFormula = null, string endFormula = null,
        Point axisStart = null, Point axisEnd = null)
    {
        RequirePart(part); RequirePoint(axisPoint); RequireInterval(startDeg, endDeg, "revolution");
        if (endDeg - startDeg > 360.0 || startDeg < -360.0 || endDeg > 360.0)
            throw new ArgumentOutOfRangeException("endDeg", "Revolution must have a positive span of at most 360 degrees within +/-360 degrees.");
        Vector3d unit = Unit(axisDirection); List<Tag> inputs = SectionInputs(section);
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
                !SameInputs(inputs, SectionInputs(read.Section)))
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

    // A fresh readback after each update or reopen; the caller compares these
    // values against its independent expected geometry and recorded expressions.
    public static Dictionary<string, object> Readback(Part part, Feature feature) {
        RequirePart(part);
        if (!(feature is Revolve) || feature.OwningPart == null || feature.OwningPart.Tag != part.Tag)
            throw new ArgumentException("Expected a native Revolve in the work part.");
        RequireOneSolid(part, feature);
        Body body = FeatureBody(part, feature);
        double[] box = new double[6];
        UFSession.GetUFSession().Modl.AskBoundingBox(body.Tag, box);
        RevolveBuilder b = part.Features.CreateRevolveBuilder(feature);
        try {
            if (b.Axis == null || b.Axis.Point == null || b.Axis.Direction == null)
                throw new InvalidOperationException("Native revolve axis is unavailable.");
            var p = b.Axis.Point.Coordinates; var v = b.Axis.Direction.Vector;
            var inputs = SectionInputs(b.Section);
            return new Dictionary<string, object> {
                {"feature_type", feature.FeatureType}, {"feature_id", feature.JournalIdentifier},
                {"body_id", body.JournalIdentifier}, {"bounding_box_mm", box},
                {"section_input_tags", new List<Tag>(inputs)},
                {"axis_point_mm", new double[]{p.X,p.Y,p.Z}},
                {"axis_direction", new double[]{v.X,v.Y,v.Z}},
                {"axis_point_tag", b.Axis.Point.Tag}, {"axis_direction_tag", b.Axis.Direction.Tag},
                {"start_degrees", b.Limits.StartExtend.Value.Value},
                {"end_degrees", b.Limits.EndExtend.Value.Value},
                {"start_rhs", b.Limits.StartExtend.Value.RightHandSide},
                {"end_rhs", b.Limits.EndExtend.Value.RightHandSide},
                {"start_trim", b.Limits.StartExtend.TrimType.ToString()},
                {"end_trim", b.Limits.EndExtend.TrimType.ToString()},
                {"symmetric", b.Limits.SymmetricOption}, {"offset", b.Offset.Option.ToString()},
                {"boolean", b.BooleanOperation.Type.ToString()}, {"body_type", b.FeatureOptions.BodyType.ToString()},
                {"distance_tolerance_mm", b.Tolerance}, {"section_angle_tolerance_deg", b.Section.AngleTolerance}
            };
        } finally { b.Destroy(); }
    }
    private static void VerifyFormula(Expression value, string formula) {
        if (!String.IsNullOrWhiteSpace(formula) && !String.Equals(
            WithoutWhitespace(value.RightHandSide), WithoutWhitespace(formula), StringComparison.Ordinal))
            throw new InvalidOperationException("Committed native limit does not retain the requested formula.");
    }
    private static string WithoutWhitespace(string value) {
        if (value == null) throw new InvalidOperationException("Native formula is unavailable.");
        System.Text.StringBuilder result = new System.Text.StringBuilder();
        foreach (char c in value) if (!Char.IsWhiteSpace(c)) result.Append(c);
        return result.ToString();
    }
    // List.Contains uses EqualityComparer<Tag>.Default, matching the previous
    // HashSet<Tag> default equality without requiring System.Core.
    private static bool SameInputs(List<Tag> a, List<Tag> b) {
        if (a.Count != b.Count) return false;
        foreach (Tag tag in a) if (!b.Contains(tag)) return false;
        return true;
    }
    private static List<Tag> SectionInputs(Section section) {
        if (section == null) throw new ArgumentNullException("section");
        SectionData[] data; section.GetSectionData(out data);
        if (data == null || data.Length == 0) throw new InvalidOperationException("Section has no native input data.");
        List<Tag> tags = new List<Tag>();
        foreach (SectionData item in data) {
            if (item == null) throw new InvalidOperationException("Section contains null data.");
            SectionElementData[] elements; item.GetSectionElementsData(out elements);
            if (elements == null) throw new InvalidOperationException("Section elements are unavailable.");
            foreach (SectionElementData e in elements) {
                if (e == null) throw new InvalidOperationException("Section contains a null element.");
                DisplayableObject selected, a, b; Point3d pa, pb;
                try { e.GetSectionElementData1(out selected, out a, out pa, out b, out pb);
                    if (selected == null || tags.Contains(selected.Tag)) throw new InvalidOperationException("Section inputs must be distinct and readable.");
                    tags.Add(selected.Tag);
                } finally { e.Dispose(); }
            }
            item.Dispose();
        }
        if (tags.Count == 0) throw new InvalidOperationException("Section has no selected input objects.");
        return tags;
    }
    // NX11 exposes GetBodies on BodyFeature rather than Feature.
    private static Body FeatureBody(Part part, Feature f) {
        if (f == null || f.OwningPart == null || f.OwningPart.Tag != part.Tag)
            throw new InvalidOperationException("NX returned no feature in the work part.");
        BodyFeature bf = f as BodyFeature;
        if (bf == null) throw new InvalidOperationException("Revolve is not a native BodyFeature.");
        Body[] bodies = bf.GetBodies();
        if (bodies == null || bodies.Length != 1 || bodies[0] == null || !bodies[0].IsSolidBody ||
            bodies[0].OwningPart == null || bodies[0].OwningPart.Tag != part.Tag)
            throw new InvalidOperationException("NX did not return exactly one solid body.");
        return bodies[0];
    }
    private static void RequireOneSolid(Part part, Feature f) { FeatureBody(part, f); }
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
