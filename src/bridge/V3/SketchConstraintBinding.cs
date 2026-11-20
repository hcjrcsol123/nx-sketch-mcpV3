using System;
using System.Collections.Generic;
using NXOpen;
using NXOpen.UF;
using NXOpen.Utilities;

// Native construction only. Caller owns authorization, sketch/section, undo,
// solver verification, and persistence. Numeric input is not a driving relation.
public static class V3SketchConstraintBinding
{
    public struct Point2
    {
        public double X, Y;
        public Point2(double x, double y) { X = x; Y = y; }
    }
    public sealed class Frame
    {
        public Point3d Origin;
        public Vector3d XAxis, YAxis;
    }
    public sealed class EdgeSpec
    {
        public string Kind;
        public Point2 Start, Mid, End, Center;
        public double Radius;
        public int Order;
        public double[] Knots;
        public Point2[] Poles;
        public double[] Weights;
        public double[] ActiveRange;
    }
    public sealed class ProfileResult
    {
        public Curve[] Curves;
        // This records UF diagnostics, not solver acceptance or association.
        public int[][] SplineStateCodes;
    }

    public static ProfileResult Create(Part part, Sketch sketch, Frame frame, IList<EdgeSpec> edges)
    {
        if (part == null || sketch == null || frame == null || edges == null || edges.Count == 0)
            throw new ArgumentException("Part, sketch, frame and edges are required.");
        if (part.PartUnits != BasePart.Units.Millimeters || sketch.OwningPart.Tag != part.Tag)
            throw new ArgumentException("A millimetre part and its own sketch are required.");
        ValidateFrame(frame);
        // Validate every descriptor before any NX mutation.
        foreach (EdgeSpec edge in edges) ValidateEdge(edge);
        var curves = new List<Curve>();
        var stateCodes = new List<int[]>();
        foreach (EdgeSpec edge in edges)
        {
            Curve curve;
            int[] states = new int[0];
            if (edge.Kind == "line")
                curve = part.Curves.CreateLine(World(frame, edge.Start), World(frame, edge.End));
            else if (edge.Kind == "circle")
                curve = part.Curves.CreateArc(World(frame, edge.Center), frame.XAxis, frame.YAxis, edge.Radius, 0, 2 * Math.PI);
            else if (edge.Kind == "arc")
                curve = CreateArc(part, frame, edge);
            else
                curve = CreateSpline(frame, edge, out states);
            sketch.AddGeometry(curve, Sketch.InferConstraintsOption.InferNoConstraints);
            curves.Add(curve);
            stateCodes.Add(states);
        }
        return new ProfileResult { Curves = curves.ToArray(), SplineStateCodes = stateCodes.ToArray() };
    }

    // An associative studio-spline feature, separate from sketch geometry.
    // Every input is a native, length-valued expression in absolute model XYZ.
    // The caller owns all expressions and transaction/update lifecycle.
    public sealed class DrivenSplineResult
    {
        public NXOpen.Features.Feature Feature;
        public Spline Curve;
        public Point[] PolePoints;
        public Scalar[,] PoleScalars;
        public Expression[,] Coordinates;
    }
    public sealed class DrivenSplineReadback
    {
        public bool FeatureAssociative;
        public int Order;
        public bool Rational, Periodic;
        public double[] Knots;
        public Point4d[] Poles; // NX homogeneous coordinates, including weight
        public double[] BuilderKnots;
        public NXOpen.Features.StudioSplineBuilderEx.Types BuilderType;
        public int BuilderDegree;
        public bool BuilderAssociative;
        public Point[] BuilderConstraintPoints;
        public Point3d[] PolePointCoordinates;
        public NXOpen.Features.Feature[] Parents;
        public Expression[] FeatureExpressions;
        // Per coordinate, precisely the native GetUsingFeatures result. An empty
        // array is evidence, not replaced by an inferred association.
        public NXOpen.Features.Feature[,][] UsingFeatures;
    }

    public static DrivenSplineResult CreateDrivenCubicSpline(Part part, Expression[,] coordinates, double[] knots)
    {
        if (part == null || part.PartUnits != BasePart.Units.Millimeters || coordinates == null ||
            coordinates.Rank != 2 || coordinates.GetLength(1) != 3 || coordinates.GetLength(0) < 4 ||
            knots == null || knots.Length != coordinates.GetLength(0) + 4)
            throw new ArgumentException("A millimetre part, at least four XYZ expression poles and a cubic knot vector are required.");
        for (int i=0; i<coordinates.GetLength(0); i++)
            for (int j=0; j<3; j++)
                if (coordinates[i,j] == null || coordinates[i,j].OwningPart == null || coordinates[i,j].OwningPart.Tag != part.Tag)
                    throw new ArgumentException("Every pole coordinate must be an expression in this part.");
        for (int i=0; i<knots.Length; i++)
            if (!Finite(knots[i]) || (i>0 && knots[i]<knots[i-1])) throw new ArgumentException("Invalid knots.");
        for (int i=0; i<4; i++)
            if (knots[i] != 0 || knots[knots.Length-1-i] != 1) throw new ArgumentException("A normalized clamped cubic basis is required.");
        if (knots[4] <= 0 || knots[knots.Length-5] >= 1)
            throw new ArgumentException("Endpoint knot multiplicity exceeds cubic order.");
        int multiplicity=1;
        for (int i=1; i<knots.Length; i++)
        {
            multiplicity = knots[i] == knots[i-1] ? multiplicity+1 : 1;
            if (knots[i] > 0 && knots[i] < 1 && multiplicity > 3)
                throw new ArgumentException("Interior knot multiplicity exceeds cubic degree.");
        }
        int count=coordinates.GetLength(0);
        var points=new Point[count]; var scalars=new Scalar[count,3];
        NXOpen.Features.StudioSplineBuilderEx builder=part.Features.CreateStudioSplineBuilderEx(null);
        try
        {
            builder.Type=NXOpen.Features.StudioSplineBuilderEx.Types.ByPoles;
            builder.Degree=3;
            builder.IsAssociative=true;
            builder.IsPeriodic=false;
            for (int i=0; i<count; i++)
            {
                for (int j=0; j<3; j++)
                    scalars[i,j]=part.Scalars.CreateScalarExpression(coordinates[i,j], Scalar.DimensionalityType.Length, SmartObject.UpdateOption.WithinModeling);
                points[i]=part.Points.CreatePoint(scalars[i,0], scalars[i,1], scalars[i,2], SmartObject.UpdateOption.WithinModeling);
                NXOpen.Features.GeometricConstraintData data=builder.ConstraintManager.CreateGeometricConstraintData();
                data.Point=points[i];
                builder.ConstraintManager.Append(data);
            }
            builder.SetKnots((double[])knots.Clone());
            NXOpen.Features.Feature feature=builder.CommitFeature();
            if (feature == null) throw new InvalidOperationException("NX did not return a spline feature.");
            Spline curve=builder.Curve;
            if (curve == null)
            {
                foreach (NXObject entity in feature.GetEntities())
                {
                    Spline candidate=entity as Spline;
                    if (candidate == null) continue;
                    if (curve != null) throw new InvalidOperationException("NX returned multiple splines.");
                    curve=candidate;
                }
            }
            if (curve == null) throw new InvalidOperationException("NX did not return a spline curve.");
            return new DrivenSplineResult { Feature=feature, Curve=curve, PolePoints=points, PoleScalars=scalars, Coordinates=(Expression[,])coordinates.Clone() };
        }
        finally { builder.Destroy(); }
    }

    // Read native model state after the caller updates it; no requested values
    // are substituted for native knot, pole, or expression-consumer readback.
    public static DrivenSplineReadback ReadDrivenSpline(DrivenSplineResult input)
    {
        if (input == null || input.Feature == null || input.Curve == null || input.Coordinates == null || input.PolePoints == null)
            throw new ArgumentException("A committed driven spline result is required.");
        int count=input.Coordinates.GetLength(0);
        var usingFeatures=new NXOpen.Features.Feature[count,3][];
        var positions=new Point3d[count];
        for (int i=0; i<count; i++)
        {
            positions[i]=input.PolePoints[i].Coordinates;
            for (int j=0; j<3; j++) usingFeatures[i,j]=input.Coordinates[i,j].GetUsingFeatures();
        }
        var builder=input.Feature.OwningPart.Features.CreateStudioSplineBuilderEx(input.Feature);
        try
        {
            var constraints=builder.ConstraintManager.GetContents();
            var builderPoints=new Point[constraints.Length];
            for (int i=0; i<constraints.Length; i++) builderPoints[i]=constraints[i].Point;
            return new DrivenSplineReadback {
                FeatureAssociative=input.Feature.IsAssociative(), Order=input.Curve.Order,
                Rational=input.Curve.Rational, Periodic=input.Curve.Periodic,
                Knots=input.Curve.GetKnots(), Poles=input.Curve.GetPoles(), PolePointCoordinates=positions,
                BuilderKnots=builder.GetKnots(), BuilderType=builder.Type, BuilderDegree=builder.Degree,
                BuilderAssociative=builder.IsAssociative, BuilderConstraintPoints=builderPoints,
                Parents=input.Feature.GetParents(), FeatureExpressions=input.Feature.GetExpressions(), UsingFeatures=usingFeatures
            };
        }
        finally { builder.Destroy(); }
    }

    // Native expression-backed point can be shared by multiple adjacent feature
    // curves. Selection through a builder must still be read back and tested.
    public sealed class DrivenPoint
    {
        public Point Point;
        public Scalar[] Scalars;
        public Expression[] Coordinates;
    }
    public sealed class DrivenCurveResult
    {
        public NXOpen.Features.Feature Feature;
        public Curve Curve;
        public DrivenPoint[] Points; // line: start/end; arc: start/mid/end
    }
    public sealed class DrivenCurveReadback
    {
        public bool FeatureAssociative, BuilderAssociative;
        public Point[] BuilderPoints;
        public Point3d[] PointCoordinates;
        public NXOpen.Features.Feature[] Parents;
        public Expression[] FeatureExpressions;
        public NXOpen.Features.Feature[,][] UsingFeatures;
        public Point3d LineStart, LineEnd, ArcCenter;
        public double ArcRadius, ArcStartAngle, ArcEndAngle;
        public NXMatrix ArcMatrix;
    }

    public static DrivenPoint CreateDrivenPoint(Part part, Expression[] xyz)
    {
        if (part == null || part.PartUnits != BasePart.Units.Millimeters || xyz == null || xyz.Length != 3)
            throw new ArgumentException("A millimetre part and three XYZ expressions are required.");
        for (int i=0;i<3;i++)
            if (xyz[i] == null || xyz[i].OwningPart == null || xyz[i].OwningPart.Tag != part.Tag)
                throw new ArgumentException("Each coordinate must be an expression in this part.");
        Scalar[] scalars = new Scalar[3];
        for (int i=0;i<3;i++)
            scalars[i]=part.Scalars.CreateScalarExpression(xyz[i], Scalar.DimensionalityType.Length, SmartObject.UpdateOption.WithinModeling);
        Point point=part.Points.CreatePoint(scalars[0],scalars[1],scalars[2],SmartObject.UpdateOption.WithinModeling);
        return new DrivenPoint { Point=point, Scalars=scalars, Coordinates=(Expression[])xyz.Clone() };
    }

    public static DrivenCurveResult CreateDrivenLine(Part part, DrivenPoint start, DrivenPoint end)
    {
        CheckDrivenPoints(part, new DrivenPoint[] { start,end });
        var builder=part.BaseFeatures.CreateAssociativeLineBuilder((NXOpen.Features.AssociativeLine)null);
        try
        {
            builder.Associative=true;
            builder.StartPointOptions=NXOpen.Features.AssociativeLineBuilder.StartOption.Point;
            builder.EndPointOptions=NXOpen.Features.AssociativeLineBuilder.EndOption.Point;
            builder.StartPoint.Value=start.Point;
            builder.EndPoint.Value=end.Point;
            NXOpen.Features.Feature feature=builder.CommitFeature();
            Curve curve=FindFeatureCurve(feature, typeof(Line));
            return new DrivenCurveResult { Feature=feature, Curve=curve, Points=new DrivenPoint[] { start,end } };
        }
        finally { builder.Destroy(); }
    }

    public static DrivenCurveResult CreateDrivenArc(Part part, DrivenPoint start, DrivenPoint mid, DrivenPoint end)
    {
        CheckDrivenPoints(part, new DrivenPoint[] { start,mid,end });
        var builder=part.BaseFeatures.CreateAssociativeArcBuilder((NXOpen.Features.AssociativeArc)null);
        try
        {
            builder.Associative=true;
            builder.Type=NXOpen.Features.AssociativeArcBuilder.Types.ThreePointArc;
            builder.StartPointOptions=NXOpen.Features.AssociativeArcBuilder.StartOption.Point;
            builder.MidPointOptions=NXOpen.Features.AssociativeArcBuilder.MidOption.Point;
            builder.EndPointOptions=NXOpen.Features.AssociativeArcBuilder.EndOption.Point;
            builder.StartPoint.Value=start.Point;
            builder.MidPoint.Value=mid.Point;
            builder.EndPoint.Value=end.Point;
            NXOpen.Features.Feature feature=builder.CommitFeature();
            Curve curve=FindFeatureCurve(feature, typeof(Arc));
            return new DrivenCurveResult { Feature=feature, Curve=curve, Points=new DrivenPoint[] { start,mid,end } };
        }
        finally { builder.Destroy(); }
    }

    public static DrivenCurveReadback ReadDrivenCurve(DrivenCurveResult input)
    {
        if (input == null || input.Feature == null || input.Curve == null || input.Points == null)
            throw new ArgumentException("A committed driven curve is required.");
        int n=input.Points.Length;
        var usingFeatures=new NXOpen.Features.Feature[n,3][];
        var positions=new Point3d[n];
        for (int i=0;i<n;i++)
        {
            positions[i]=input.Points[i].Point.Coordinates;
            for (int j=0;j<3;j++) usingFeatures[i,j]=input.Points[i].Coordinates[j].GetUsingFeatures();
        }
        var output=new DrivenCurveReadback {
            FeatureAssociative=input.Feature.IsAssociative(), PointCoordinates=positions,
            Parents=input.Feature.GetParents(), FeatureExpressions=input.Feature.GetExpressions(), UsingFeatures=usingFeatures
        };
        var line=input.Curve as Line;
        var arc=input.Curve as Arc;
        BasePart part=input.Feature.OwningPart;
        if (line != null)
        {
            var feature=input.Feature as NXOpen.Features.AssociativeLine;
            if (feature == null) throw new InvalidOperationException("Expected associative line feature.");
            var builder=part.BaseFeatures.CreateAssociativeLineBuilder(feature);
            try
            {
                output.BuilderAssociative=builder.Associative;
                output.BuilderPoints=new Point[] { builder.StartPoint.Value, builder.EndPoint.Value };
                output.LineStart=line.StartPoint; output.LineEnd=line.EndPoint;
            }
            finally { builder.Destroy(); }
        }
        else if (arc != null)
        {
            var feature=input.Feature as NXOpen.Features.AssociativeArc;
            if (feature == null) throw new InvalidOperationException("Expected associative arc feature.");
            var builder=part.BaseFeatures.CreateAssociativeArcBuilder(feature);
            try
            {
                output.BuilderAssociative=builder.Associative;
                output.BuilderPoints=new Point[] { builder.StartPoint.Value, builder.MidPoint.Value, builder.EndPoint.Value };
                output.ArcCenter=arc.CenterPoint; output.ArcRadius=arc.Radius;
                output.ArcStartAngle=arc.StartAngle; output.ArcEndAngle=arc.EndAngle; output.ArcMatrix=arc.Matrix;
            }
            finally { builder.Destroy(); }
        }
        else throw new ArgumentException("Expected line or arc.");
        return output;
    }

    private static void CheckDrivenPoints(Part part, DrivenPoint[] points)
    {
        if (part == null || part.PartUnits != BasePart.Units.Millimeters) throw new ArgumentException("A millimetre part is required.");
        foreach (DrivenPoint point in points)
            if (point == null || point.Point == null || point.Point.OwningPart == null || point.Point.OwningPart.Tag != part.Tag ||
                point.Coordinates == null || point.Coordinates.Length != 3)
                throw new ArgumentException("Every expression point must belong to the part.");
    }
    private static Curve FindFeatureCurve(NXOpen.Features.Feature feature, Type curveType)
    {
        if (feature == null) throw new InvalidOperationException("NX did not return a curve feature.");
        Curve found=null;
        foreach (NXObject entity in feature.GetEntities())
        {
            Curve curve=entity as Curve;
            if (curve == null || !curveType.IsInstanceOfType(curve)) continue;
            if (found != null) throw new InvalidOperationException("NX returned multiple curves for a feature.");
            found=curve;
        }
        if (found == null) throw new InvalidOperationException("NX feature did not return the requested curve.");
        return found;
    }

    // The rule follows these native curves; it does not assert that the section
    // is closed or that the selected curves are driven. Caller validates its domain.
    public static Section CreateSection(Part part, ProfileResult profile, Point3d helpPoint,
        double chainingTolerance, double distanceTolerance, double angleTolerance)
    {
        if (part == null || profile == null || profile.Curves == null || profile.Curves.Length == 0)
            throw new ArgumentException("Part and profile curves are required.");
        if (!Finite(chainingTolerance) || !Finite(distanceTolerance) || !Finite(angleTolerance) ||
            chainingTolerance <= 0 || distanceTolerance <= 0 || angleTolerance <= 0)
            throw new ArgumentException("Explicit positive section tolerances are required.");
        foreach (Curve curve in profile.Curves)
            if (curve == null || curve.OwningPart.Tag != part.Tag) throw new ArgumentException("Curve outside the part.");
        Section section = part.Sections.CreateSection(chainingTolerance, distanceTolerance, angleTolerance);
        section.SetAllowedEntityTypes(Section.AllowTypes.OnlyCurves);
        section.SetAllowRefCrvs(false);
        CurveDumbRule rule = part.ScRuleFactory.CreateRuleCurveDumb(profile.Curves);
        section.AddToSection(new SelectionIntentRule[] { rule }, profile.Curves[0], null, null,
            helpPoint, Section.Mode.Create, true);
        return section;
    }

    // Useful complete circle case: native center-to-origin coincidence plus a
    // separate driving radius. The caller decides whether these relations fit.
    public static SketchGeometricConstraint CircleCenterAtOrigin(Sketch sketch, Arc circle)
    {
        if (sketch == null || circle == null || circle.OwningPart.Tag != sketch.OwningPart.Tag)
            throw new ArgumentException("Circle must belong to the sketch part.");
        return sketch.CreateCoincidentConstraint(
            new Sketch.ConstraintGeometry(circle, Sketch.ConstraintPointType.ArcCenter, 0),
            new Sketch.ConstraintGeometry(sketch.OriginPoint, Sketch.ConstraintPointType.None, 0));
    }

    // and must check native solver status/DOF and reject conflicts or redundancy.
    public static SketchGeometricConstraint Coincident(Sketch sketch, Curve first, bool firstEnd, Curve second, bool secondEnd)
    {
        if (sketch == null || first == null || second == null) throw new ArgumentNullException();
        return sketch.CreateCoincidentConstraint(
            new Sketch.ConstraintGeometry(first, firstEnd ? Sketch.ConstraintPointType.EndVertex : Sketch.ConstraintPointType.StartVertex, 0),
            new Sketch.ConstraintGeometry(second, secondEnd ? Sketch.ConstraintPointType.EndVertex : Sketch.ConstraintPointType.StartVertex, 0));
    }

    public static SketchDimensionalConstraint DriveRadius(Sketch sketch, Arc circle, Expression expression, Point3d helpPoint)
    {
        if (sketch == null || circle == null || expression == null) throw new ArgumentNullException();
        if (circle.OwningPart.Tag != sketch.OwningPart.Tag || expression.OwningPart.Tag != sketch.OwningPart.Tag)
            throw new ArgumentException("Expression and curve must belong to the sketch part.");
        var geometry = new Sketch.DimensionGeometry { Geometry = circle, AssocType = Sketch.AssocType.None, AssocValue = 0 };
        var dimension = sketch.CreateRadialDimension(geometry, helpPoint, expression, Sketch.DimensionOption.CreateAsDriving);
        if (dimension == null || dimension.DimensionState != SketchDimensionalConstraint.DimensionStateType.Driving ||
            dimension.AssociatedExpression == null || dimension.AssociatedExpression.Tag != expression.Tag)
            throw new InvalidOperationException("NX did not bind the requested driving radius expression.");
        return dimension;
    }

    // A projected coordinate of a curve endpoint from the sketch origin.
    // Sign is represented by operand order; the defining expression is a
    // positive distance, not a signed world coordinate. Solver acceptance is
    // required, especially when coincident endpoints are also constrained.
    public static SketchDimensionalConstraint DriveEndpointCoordinate(Sketch sketch, Curve curve,
        bool end, bool horizontal, bool targetAfterOrigin, Expression expression, Point3d helpPoint)
    {
        if (sketch == null || curve == null || expression == null ||
            curve.OwningPart.Tag != sketch.OwningPart.Tag || expression.OwningPart.Tag != sketch.OwningPart.Tag)
            throw new ArgumentException("Curve and expression must belong to the sketch part.");
        var origin = new Sketch.DimensionGeometry { Geometry = sketch.OriginPoint, AssocType = Sketch.AssocType.Midpoint, AssocValue = 0 };
        var target = new Sketch.DimensionGeometry { Geometry = curve, AssocType = end ? Sketch.AssocType.EndPoint : Sketch.AssocType.StartPoint, AssocValue = 0 };
        var dimension = sketch.CreateDimension(horizontal ? Sketch.ConstraintType.HorizontalDim : Sketch.ConstraintType.VerticalDim,
            targetAfterOrigin ? origin : target, targetAfterOrigin ? target : origin,
            helpPoint, expression, Sketch.DimensionOption.CreateAsDriving);
        if (dimension == null || dimension.DimensionState != SketchDimensionalConstraint.DimensionStateType.Driving ||
            dimension.AssociatedExpression == null || dimension.AssociatedExpression.Tag != expression.Tag)
            throw new InvalidOperationException("NX did not bind the requested driving coordinate expression.");
        return dimension;
    }

    private static Arc CreateArc(Part part, Frame f, EdgeSpec e)
    {
        double ax = e.Start.X, ay = e.Start.Y, bx = e.Mid.X, by = e.Mid.Y, cx = e.End.X, cy = e.End.Y;
        double d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by));
        double a2 = ax * ax + ay * ay, b2 = bx * bx + by * by, c2 = cx * cx + cy * cy;
        double x = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d;
        double y = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d;
        double radius = Math.Sqrt((ax-x)*(ax-x) + (ay-y)*(ay-y));
        double start = Math.Atan2(ay-y, ax-x), mid = Math.Atan2(by-y, bx-x), end = Math.Atan2(cy-y, cx-x);
        double ccwEnd = Positive(end-start), ccwMid = Positive(mid-start);
        Vector3d yAxis = f.YAxis;
        if (ccwMid > ccwEnd)
        {
            yAxis = new Vector3d(-yAxis.X, -yAxis.Y, -yAxis.Z);
            start = -start; end = -end;
        }
        double sweep = Positive(end-start);
        return part.Curves.CreateArc(World(f, new Point2(x,y)), f.XAxis, yAxis, radius, start, start+sweep);
    }

    private static Curve CreateSpline(Frame f, EdgeSpec e, out int[] codes)
    {
        var data = new UFCurve.Spline();
        data.order = e.Order; data.num_poles = e.Poles.Length; data.knots = (double[])e.Knots.Clone();
        data.poles = new double[e.Poles.Length,4];
        for (int i=0; i<e.Poles.Length; i++)
        {
            double w = e.Weights == null ? 1.0 : e.Weights[i];
            Point3d p = World(f,e.Poles[i]);
            data.poles[i,0]=p.X*w; data.poles[i,1]=p.Y*w; data.poles[i,2]=p.Z*w; data.poles[i,3]=w;
            if (w != 1.0) data.is_rational=1;
        }
        data.start_param = e.ActiveRange == null ? data.knots[e.Order-1] : e.ActiveRange[0];
        data.end_param = e.ActiveRange == null ? data.knots[e.Poles.Length] : e.ActiveRange[1];
        double start = data.start_param, end = data.end_param;
        Tag tag; int count; UFCurve.State[] states;
        UFSession.GetUFSession().Curve.CreateSpline(ref data, out tag, out count, out states);
        codes = new int[count];
        for (int i=0; i<count; i++) codes[i]=states[i].state_code;
        // UF_CURVE_STATE_UNNORMALIZED reports t_native = t_input * v0 + v1.
        // Accept only that reparameterization and verify the whole native basis.
        double scale = 1.0, shift = 0.0;
        if (count == 1 && codes[0] == 52)
        {
            scale = states[0].value[0];
            shift = states[0].value[1];
            if (!Finite(scale) || !Finite(shift) || scale <= 0)
                throw new InvalidOperationException("NX reported an invalid affine spline parameter transform.");
        }
        else if (count != 0)
            throw new InvalidOperationException("NX spline state codes: " + String.Join(",", codes));
        UFCurve.Spline actual;
        UFSession.GetUFSession().Curve.AskSplineData(tag, out actual);
        if (actual.order != e.Order || actual.num_poles != e.Poles.Length ||
            Math.Abs(actual.start_param - (start * scale + shift)) > 1e-12 ||
            Math.Abs(actual.end_param - (end * scale + shift)) > 1e-12)
            throw new InvalidOperationException("NX changed the spline order, pole count or active input interval.");
        for (int i=0; i<e.Knots.Length; i++)
            if (Math.Abs(actual.knots[i] - (e.Knots[i] * scale + shift)) > 1e-12)
                throw new InvalidOperationException("NX changed a spline knot beyond affine reparameterization.");
        for (int i=0; i<e.Poles.Length; i++)
        {
            double w = e.Weights == null ? 1.0 : e.Weights[i];
            Point3d p = World(f, e.Poles[i]);
            var expected = new [] { p.X*w, p.Y*w, p.Z*w, w };
            for (int j=0; j<4; j++)
                if (Math.Abs(actual.poles[i,j] - expected[j]) > 1e-10)
                    throw new InvalidOperationException("NX changed a spline pole or weight.");
        }
        var curve = NXObjectManager.Get(tag) as Curve;
        if (curve == null) throw new InvalidOperationException("NX did not return a spline curve.");
        return curve;
    }

    private static void ValidateFrame(Frame f)
    {
        if (!Finite(f.Origin.X) || !Finite(f.Origin.Y) || !Finite(f.Origin.Z) || !Finite(f.XAxis.X) || !Finite(f.XAxis.Y) || !Finite(f.XAxis.Z) || !Finite(f.YAxis.X) || !Finite(f.YAxis.Y) || !Finite(f.YAxis.Z)) throw new ArgumentException("Non-finite frame.");
        double xx=f.XAxis.X*f.XAxis.X+f.XAxis.Y*f.XAxis.Y+f.XAxis.Z*f.XAxis.Z;
        double yy=f.YAxis.X*f.YAxis.X+f.YAxis.Y*f.YAxis.Y+f.YAxis.Z*f.YAxis.Z;
        double xy=f.XAxis.X*f.YAxis.X+f.XAxis.Y*f.YAxis.Y+f.XAxis.Z*f.YAxis.Z;
        if (Math.Abs(xx-1)>1e-9 || Math.Abs(yy-1)>1e-9 || Math.Abs(xy)>1e-9) throw new ArgumentException("Frame axes must be orthonormal.");
    }
    private static void ValidateEdge(EdgeSpec e)
    {
        if (e == null) throw new ArgumentException("Null edge.");
        if (e.Kind == "line") { Check(e.Start); Check(e.End); if (Distance(e.Start,e.End) <= 1e-12) throw new ArgumentException("Degenerate line."); }
        else if (e.Kind == "circle") { Check(e.Center); if (!Finite(e.Radius) || e.Radius <= 0) throw new ArgumentException("Invalid radius."); }
        else if (e.Kind == "arc")
        {
            Check(e.Start); Check(e.Mid); Check(e.End);
            double cross=(e.Mid.X-e.Start.X)*(e.End.Y-e.Start.Y)-(e.Mid.Y-e.Start.Y)*(e.End.X-e.Start.X);
            if (Math.Abs(cross) <= 1e-12 || Distance(e.Start,e.End)<=1e-12) throw new ArgumentException("Degenerate arc.");
        }
        else if (e.Kind == "spline")
        {
            if (e.Poles == null || e.Knots == null || e.Order < 2 || e.Order > e.Poles.Length || e.Knots.Length != e.Poles.Length+e.Order || (e.Weights != null && e.Weights.Length != e.Poles.Length)) throw new ArgumentException("Invalid spline basis.");
            for (int i=0;i<e.Poles.Length;i++) { Check(e.Poles[i]); if (e.Weights != null && (!Finite(e.Weights[i]) || e.Weights[i]<=0)) throw new ArgumentException("Invalid spline weight."); }
            for (int i=0;i<e.Knots.Length;i++) if (!Finite(e.Knots[i]) || (i>0 && e.Knots[i]<e.Knots[i-1])) throw new ArgumentException("Invalid knots.");
            if (e.Knots[e.Order-1] != 0 || e.Knots[e.Poles.Length] != 1) throw new ArgumentException("Spline parameter range must be normalized to 0..1.");
            for (int i=0;i<e.Order;i++) if (e.Knots[i]!=0 || e.Knots[e.Knots.Length-1-i]!=1) throw new ArgumentException("Spline must have clamped ends.");
            if (e.ActiveRange != null && (e.ActiveRange.Length != 2 || !Finite(e.ActiveRange[0]) || !Finite(e.ActiveRange[1]) ||
                e.ActiveRange[0] < 0 || e.ActiveRange[1] > 1 || e.ActiveRange[0] >= e.ActiveRange[1]))
                throw new ArgumentException("Invalid spline active interval.");
        }
        else throw new ArgumentException("Unsupported edge kind: " + e.Kind);
    }
    private static double Positive(double x) { x %= 2*Math.PI; return x<0 ? x+2*Math.PI : x; }
    private static double Distance(Point2 a, Point2 b) { return Math.Sqrt((a.X-b.X)*(a.X-b.X)+(a.Y-b.Y)*(a.Y-b.Y)); }
    private static bool Finite(double x) { return !Double.IsNaN(x) && !Double.IsInfinity(x); }
    private static void Check(Point2 p) { if (!Finite(p.X) || !Finite(p.Y)) throw new ArgumentException("Non-finite coordinate."); }
    private static Point3d World(Frame f, Point2 p) { return new Point3d(f.Origin.X+f.XAxis.X*p.X+f.YAxis.X*p.Y, f.Origin.Y+f.XAxis.Y*p.X+f.YAxis.Y*p.Y, f.Origin.Z+f.XAxis.Z*p.X+f.YAxis.Z*p.Y); }
}
