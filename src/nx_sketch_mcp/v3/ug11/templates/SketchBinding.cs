using System;
using System.Collections.Generic;
using NXOpen;
using NXOpen.UF;
using NXOpen.Utilities;

// Adapted from P4 SketchConstraintBinding for NX11. Feature.IsAssociative and Sketch.OriginPoint
// are unavailable in NX11; FeatureAssociative is null and the caller supplies an anchored point.
// Native construction only. Caller owns authorization, sketch/section, undo,
// solver verification, and persistence. Numeric input is not a driving relation.
public static class Ug11SketchBinding
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

    // Fixed frame datum is a native feature; its dependence must not be described
    // as expression-driven. The caller owns activation, update and undo.
    public static NXOpen.Features.Feature CreateFixedDatum(Part part, Frame frame)
    {
        if (part == null || frame == null || part.PartUnits != BasePart.Units.Millimeters) throw new ArgumentException("Millimetre part and frame required");
        ValidateFrame(frame);
        Vector3d x=frame.XAxis, y=frame.YAxis;
        Vector3d n=new Vector3d(x.Y*y.Z-x.Z*y.Y,x.Z*y.X-x.X*y.Z,x.X*y.Y-x.Y*y.X);
        Matrix3x3 m=new Matrix3x3(); m.Xx=x.X;m.Xy=x.Y;m.Xz=x.Z; m.Yx=y.X;m.Yy=y.Y;m.Yz=y.Z; m.Zx=n.X;m.Zy=n.Y;m.Zz=n.Z;
        var b=part.Features.CreateDatumPlaneBuilder(null);
        try { var plane=b.GetPlane(); plane.SetMethod(PlaneTypes.MethodType.Fixed); plane.EditFixedPlane(frame.Origin,m); plane.Evaluate(); return b.CommitFeature(); }
        finally { b.Destroy(); }
    }
    public static Sketch CreateSketchOnDatum(Part part, Frame frame, NXOpen.Features.Feature datum)
    {
        if (part == null || frame == null || !(datum is NXOpen.Features.DatumPlaneFeature) || datum.OwningPart.Tag != part.Tag) throw new ArgumentException("Native datum and frame required");
        ValidateFrame(frame); Vector3d x=frame.XAxis,y=frame.YAxis;
        Vector3d n=new Vector3d(x.Y*y.Z-x.Z*y.Y,x.Z*y.X-x.X*y.Z,x.X*y.Y-x.Y*y.X);
        var support=part.Planes.CreatePlane(PlaneTypes.MethodType.Coincident,PlaneTypes.AlternateType.One,frame.Origin,n,null,false,false,new NXObject[]{((NXOpen.Features.DatumPlaneFeature)datum).DatumPlane});
        var direction=part.Directions.CreateDirection(frame.Origin,x,SmartObject.UpdateOption.WithinModeling);
        var origin=part.Points.CreatePoint(frame.Origin); var b=part.Sketches.CreateSketchInPlaceBuilder2(null);
        try { b.PlaneReference=support;b.AxisReference=direction;b.SketchOrigin=origin;b.PlaneOption=Sketch.PlaneOption.ExistingPlane;b.OriginOption=OriginMethod.SpecifyPoint;
            var sk=(Sketch)b.Commit();sk.Activate(Sketch.ViewReorient.False);return sk; }
        finally {b.Destroy();}
    }
    // Anchor must be fixed on the active sketch; retain it for dimension reads.
    public static Point CreateFixedAnchor(Part part, Sketch sketch, Point3d origin)
    {
        if (part == null || sketch == null || sketch.OwningPart.Tag != part.Tag) throw new ArgumentException("Sketch outside part");
        Point p=part.Points.CreatePoint(origin);sketch.AddGeometry(p,Sketch.InferConstraintsOption.InferNoConstraints);
        sketch.CreateFixedConstraint(new Sketch.ConstraintGeometry(p,Sketch.ConstraintPointType.None,0));return p;
    }
    // Evaluate after native model update; never infer a driving relation from its requested formula.
    public static void VerifyDrivingDimension(Sketch sketch, SketchDimensionalConstraint dimension, Expression expression, Curve expectedCurve, double expectedValue, double tolerance)
    {
        if (sketch == null || dimension == null || expression == null || expectedCurve == null || !Finite(expectedValue) || !Finite(tolerance) || tolerance <= 0)
            throw new ArgumentException("Invalid dimension verification");
        int dof; var status=sketch.GetStatus(out dof);
        if (status == Sketch.Status.OverConstrained || status == Sketch.Status.InconsistentlyConstrained || dimension.DimensionState != SketchDimensionalConstraint.DimensionStateType.Driving ||
            dimension.AssociatedExpression == null || dimension.AssociatedExpression.Tag != expression.Tag || !Finite(expression.Value) || Math.Abs(expression.Value-expectedValue)>tolerance)
            throw new InvalidOperationException("Driving dimension or sketch solver mismatch");
        bool attached=false; foreach(var g in dimension.GetDimensionGeometry()) if(g.Geometry != null && g.Geometry.Tag==expectedCurve.Tag) attached=true;
        bool used=false; foreach(var f in expression.GetUsingFeatures()) if(f.Tag==sketch.Feature.Tag) used=true;
        if (!attached || !used) throw new InvalidOperationException("Dimension geometry or expression consumer missing");
    }

    public sealed class RearSlotSketch
    {
        public Sketch Sketch; public Arc Circle; public Point Anchor; public Section Section;
        public Expression AxisY, AxisZ, Radius, YDistance;
        public SketchDimensionalConstraint YDimension, ZDimension, RadiusDimension;
    }
    // Exact P4 rear-slot profile: one circle is equivalent to its two arcs.
    // Y is negative and Z positive in this explicitly bounded construction.
    public static RearSlotSketch CreateRearSlot(Part part, Expression axisY, Expression axisZ, Expression radius)
    {
        if (part == null || axisY == null || axisZ == null || radius == null ||
            axisY.OwningPart.Tag != part.Tag || axisZ.OwningPart.Tag != part.Tag || radius.OwningPart.Tag != part.Tag ||
            !Finite(axisY.Value) || !Finite(axisZ.Value) || !Finite(radius.Value) || axisY.Value >= 0 || axisZ.Value <= 0 || radius.Value <= 0)
            throw new ArgumentException("Rear slot needs negative Y, positive Z, positive radius and local expressions");
        Unit mm=part.UnitCollection.FindObject("MilliMeter");
        if(axisY.Units == null || axisZ.Units == null || radius.Units == null || axisY.Units.Tag != mm.Tag || axisZ.Units.Tag != mm.Tag || radius.Units.Tag != mm.Tag)
            throw new ArgumentException("Rear slot coordinates require millimetre expressions");
        Expression distance=part.Expressions.CreateWithUnits("v3_ug11_slot_y_distance=-"+axisY.Name,mm);
        Frame frame=new Frame { Origin=new Point3d(0,0,0), XAxis=new Vector3d(0,1,0), YAxis=new Vector3d(0,0,1) };
        var datum=CreateFixedDatum(part,frame); Sketch sk=CreateSketchOnDatum(part,frame,datum);
        Point anchor=CreateFixedAnchor(part,sk,frame.Origin);
        Arc circle=part.Curves.CreateArc(new Point3d(0,axisY.Value,axisZ.Value),frame.XAxis,frame.YAxis,radius.Value,0,2*Math.PI);
        sk.AddGeometry(circle,Sketch.InferConstraintsOption.InferNoConstraints);
        var origin=new Sketch.DimensionGeometry { Geometry=anchor, AssocType=Sketch.AssocType.Midpoint, AssocValue=0 };
        var center=new Sketch.DimensionGeometry { Geometry=circle, AssocType=Sketch.AssocType.ArcCenter, AssocValue=0 };
        var dy=sk.CreateDimension(Sketch.ConstraintType.HorizontalDim,center,origin,new Point3d(0,axisY.Value/2,axisZ.Value-2),distance,Sketch.DimensionOption.CreateAsDriving);
        var dz=sk.CreateDimension(Sketch.ConstraintType.VerticalDim,origin,center,new Point3d(0,axisY.Value-2,axisZ.Value/2),axisZ,Sketch.DimensionOption.CreateAsDriving);
        var dr=DriveRadius(sk,circle,radius,new Point3d(0,axisY.Value+radius.Value,axisZ.Value));
        sk.Update(); int dof; var status=sk.GetStatus(out dof);
        if(status != Sketch.Status.WellConstrained || dof != 0) throw new InvalidOperationException("Rear-slot sketch is not fully constrained");
        sk.Deactivate(Sketch.ViewReorient.False,Sketch.UpdateLevel.Model);
        Section section=part.Sections.CreateSection(0.0001,0.0001,0.5);
        section.SetAllowedEntityTypes(Section.AllowTypes.OnlyCurves);section.SetAllowRefCrvs(false);
        var rule=part.ScRuleFactory.CreateRuleCurveFeature(new NXOpen.Features.Feature[]{sk.Feature});
        section.AddToSection(new SelectionIntentRule[]{rule},circle,null,null,frame.Origin,Section.Mode.Create,true);
        return new RearSlotSketch {Sketch=sk,Circle=circle,Anchor=anchor,Section=section,AxisY=axisY,AxisZ=axisZ,Radius=radius,YDistance=distance,YDimension=dy,ZDimension=dz,RadiusDimension=dr};
    }
    // Called after update, and again after each edit with fresh native objects.
    public static void VerifyRearSlot(RearSlotSketch slot, double tolerance)
    {
        if(slot == null || !Finite(tolerance) || tolerance <= 0 || slot.AxisY.Value >= 0 || slot.AxisZ.Value <= 0 || slot.Radius.Value <= 0)
            throw new ArgumentException("Rear slot outside accepted sign domain");
        int dof; if(slot.Sketch.GetStatus(out dof) != Sketch.Status.WellConstrained || dof != 0)
            throw new InvalidOperationException("Rear-slot solver is not fully constrained");
        if(slot.YDistance.RightHandSide.Replace(" ","") != "-"+slot.AxisY.Name || !Finite(slot.AxisY.Value) || !Finite(slot.AxisZ.Value) || !Finite(slot.Radius.Value) || !Finite(slot.YDistance.Value) || Math.Abs(slot.YDistance.Value+slot.AxisY.Value)>tolerance)
            throw new InvalidOperationException("Rear-slot Y formula mismatch");
        if(slot.Anchor == null || slot.YDimension.ConstraintType != Sketch.ConstraintType.HorizontalDim || slot.ZDimension.ConstraintType != Sketch.ConstraintType.VerticalDim || slot.RadiusDimension.ConstraintType != Sketch.ConstraintType.RadiusDim)
            throw new InvalidOperationException("Rear-slot driving dimension types mismatch");
        Point3d anchor=slot.Anchor.Coordinates;
        if(!Finite(anchor.X)||!Finite(anchor.Y)||!Finite(anchor.Z)||Math.Abs(anchor.X)>tolerance||Math.Abs(anchor.Y)>tolerance||Math.Abs(anchor.Z)>tolerance)
            throw new InvalidOperationException("Rear-slot anchor moved");
        bool fixedAnchor=false;
        foreach(SketchConstraint constraint in slot.Sketch.GetAllConstraintsOfType(Sketch.ConstraintClass.Any,Sketch.ConstraintType.NoCon))
        {
            var g=constraint as SketchGeometricConstraint; if(g==null || g.ConstraintType!=Sketch.ConstraintType.Fixed) continue;
            foreach(var operand in g.GetGeometry()) if(operand.Geometry!=null && operand.Geometry.Tag==slot.Anchor.Tag) fixedAnchor=true;
        }
        if(!fixedAnchor) throw new InvalidOperationException("Rear-slot anchor is not fixed");
        foreach(var d in new SketchDimensionalConstraint[]{slot.YDimension,slot.ZDimension})
        {
            bool a=false, center=false;
            foreach(var operand in d.GetDimensionGeometry())
            {
                if(operand.Geometry!=null && operand.Geometry.Tag==slot.Anchor.Tag) a=true;
                if(operand.Geometry!=null && operand.Geometry.Tag==slot.Circle.Tag && operand.AssocType==Sketch.AssocType.ArcCenter) center=true;
            }
            if(!a || !center) throw new InvalidOperationException("Rear-slot coordinate dimension geometry mismatch");
        }
        VerifyDrivingDimension(slot.Sketch,slot.YDimension,slot.YDistance,slot.Circle,-slot.AxisY.Value,tolerance);
        VerifyDrivingDimension(slot.Sketch,slot.ZDimension,slot.AxisZ,slot.Circle,slot.AxisZ.Value,tolerance);
        VerifyDrivingDimension(slot.Sketch,slot.RadiusDimension,slot.Radius,slot.Circle,slot.Radius.Value,tolerance);
        Point3d c=slot.Circle.CenterPoint;
        if(!Finite(c.X) || !Finite(c.Y) || !Finite(c.Z) || !Finite(slot.Circle.Radius) || Math.Abs(c.X)>tolerance || Math.Abs(c.Y-slot.AxisY.Value)>tolerance || Math.Abs(c.Z-slot.AxisZ.Value)>tolerance || Math.Abs(slot.Circle.Radius-slot.Radius.Value)>tolerance)
            throw new InvalidOperationException("Rear-slot native center or radius mismatch");
    }

    // Reconstruct from the current opened part only. Tags and wrapper objects are
    // obtained afresh; no prior-session handle is accepted or retained.
    public static RearSlotSketch ReopenRearSlot(Part part)
    {
        if (part == null || part.PartUnits != BasePart.Units.Millimeters) throw new ArgumentException("Millimetre part required");
        Sketch found=null;
        foreach (Sketch sk in part.Sketches.ToArray())
        {
            var f=sk.Feature;
            if (f != null && f.HasUserAttribute("UG11_SLOT",NXObject.AttributeType.String,0) && f.GetStringUserAttribute("UG11_SLOT",0)=="rear_slot")
            { if(found != null) throw new InvalidOperationException("Rear-slot sketch marker is not unique"); found=sk; }
        }
        if(found == null) throw new InvalidOperationException("Rear-slot sketch marker missing");
        Arc circle=null; Point anchor=null;
        foreach(NXObject o in found.GetAllGeometry())
        {
            Arc a=o as Arc; Point p=o as Point;
            if(a != null) { if(circle != null) throw new InvalidOperationException("Multiple rear-slot arcs"); circle=a; }
            else if(p != null) { if(anchor != null) throw new InvalidOperationException("Multiple rear-slot anchors"); anchor=p; }
            else throw new InvalidOperationException("Unexpected rear-slot sketch geometry");
        }
        if(circle == null || anchor == null) throw new InvalidOperationException("Rear-slot circle or anchor missing");
        Expression y=null,z=null,r=null,yd=null;
        foreach(Expression e in part.Expressions.ToArray())
        {
            if(e.Name=="v3_slot_axis_y") { if(y != null) throw new InvalidOperationException("Duplicate Y expression"); y=e; }
            if(e.Name=="v3_slot_axis_z") { if(z != null) throw new InvalidOperationException("Duplicate Z expression"); z=e; }
            if(e.Name=="v3_slot_radius") { if(r != null) throw new InvalidOperationException("Duplicate radius expression"); r=e; }
            if(e.Name=="v3_ug11_slot_y_distance") { if(yd != null) throw new InvalidOperationException("Duplicate Y distance expression"); yd=e; }
        }
        if(y == null || z == null || r == null || yd == null) throw new InvalidOperationException("Rear-slot expression missing");
        SketchDimensionalConstraint dy=null,dz=null,dr=null;
        foreach(SketchConstraint c in found.GetAllConstraintsOfType(Sketch.ConstraintClass.Any,Sketch.ConstraintType.NoCon))
        {
            var d=c as SketchDimensionalConstraint; if(d==null || d.AssociatedExpression==null) continue;
            Tag t=d.AssociatedExpression.Tag;
            if(t==yd.Tag) { if(dy!=null) throw new InvalidOperationException("Duplicate Y dimension"); dy=d; }
            else if(t==z.Tag) { if(dz!=null) throw new InvalidOperationException("Duplicate Z dimension"); dz=d; }
            else if(t==r.Tag) { if(dr!=null) throw new InvalidOperationException("Duplicate radius dimension"); dr=d; }
            else throw new InvalidOperationException("Unexpected rear-slot dimensional constraint");
        }
        if(dy == null || dz == null || dr == null) throw new InvalidOperationException("Rear-slot dimension missing");
        return new RearSlotSketch { Sketch=found,Circle=circle,Anchor=anchor,AxisY=y,AxisZ=z,Radius=r,YDistance=yd,YDimension=dy,ZDimension=dz,RadiusDimension=dr };
    }

    // Reopen the extrude builder and check the actual persisted native Section's
    // feature rule, selected circle and the feature-history parent relationship.
    public static void VerifyRearSlotConsumer(Part part, NXOpen.Features.Feature extrude, RearSlotSketch slot)
    {
        if(part==null || !(extrude is NXOpen.Features.Extrude) || extrude.OwningPart.Tag!=part.Tag || slot==null || slot.Sketch==null || slot.Sketch.OwningPart.Tag!=part.Tag || slot.Circle==null)
            throw new ArgumentException("Current part, extrude and slot required");
        bool parent=false; foreach(var f in extrude.GetParents()) if(f.Tag==slot.Sketch.Feature.Tag) parent=true;
        if(!parent) throw new InvalidOperationException("Rear-slot sketch is not an extrude parent");
        var builder=part.Features.CreateExtrudeBuilder(extrude);
        try
        {
            if(builder.Section==null) throw new InvalidOperationException("Extrude section missing");
            SectionData[] data; builder.Section.GetSectionData(out data);
            if(data==null || data.Length==0) throw new InvalidOperationException("Extrude section has no data");
            int ruleCount=0, selectedCount=0;
            foreach(SectionData item in data)
            {
                if(item==null) throw new InvalidOperationException("Null section data");
                try
                {
                    SelectionIntentRule[] rules; item.GetRules(out rules);
                    if(rules==null) throw new InvalidOperationException("Section rules unavailable");
                    foreach(SelectionIntentRule rule in rules)
                    {
                        var featureRule=rule as CurveFeatureRule;
                        if(featureRule==null) throw new InvalidOperationException("Section does not use sketch feature rule");
                        NXOpen.Features.Feature[] features; featureRule.GetData(out features);
                        if(features==null || features.Length!=1 || features[0].Tag!=slot.Sketch.Feature.Tag)
                            throw new InvalidOperationException("Section feature rule is not the rear-slot sketch");
                        ruleCount++;
                    }
                    SectionElementData[] elements; item.GetSectionElementsData(out elements);
                    if(elements==null) throw new InvalidOperationException("Section elements unavailable");
                    foreach(SectionElementData element in elements)
                    {
                        if(element==null) throw new InvalidOperationException("Null section element");
                        try { DisplayableObject selected,a,b; Point3d pa,pb;
                            element.GetSectionElementData1(out selected,out a,out pa,out b,out pb);
                            if(selected==null || selected.Tag!=slot.Circle.Tag) throw new InvalidOperationException("Extrude section selects unexpected geometry");
                            selectedCount++;
                        } finally {element.Dispose();}
                    }
                } finally {item.Dispose();}
            }
            if(ruleCount!=1 || selectedCount!=1) throw new InvalidOperationException("Extrude section has unexpected rule or curve count");
        } finally {builder.Destroy();}
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
        public bool? FeatureAssociative;
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
                if (coordinates[i,j] == null || coordinates[i,j].OwningPart == null || coordinates[i,j].OwningPart.Tag != part.Tag || coordinates[i,j].Units == null || coordinates[i,j].Units.Tag != part.UnitCollection.FindObject("MilliMeter").Tag || !Finite(coordinates[i,j].Value))
                    throw new ArgumentException("Every pole coordinate must be a finite millimetre expression in this part.");
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
        var builder=((Part)input.Feature.OwningPart).Features.CreateStudioSplineBuilderEx(input.Feature);
        try
        {
            var constraints=builder.ConstraintManager.GetContents();
            var builderPoints=new Point[constraints.Length];
            for (int i=0; i<constraints.Length; i++) builderPoints[i]=constraints[i].Point;
            return new DrivenSplineReadback {
                FeatureAssociative=null, Order=input.Curve.Order,
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
        public bool? FeatureAssociative;
        public bool BuilderAssociative;
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
            if (xyz[i] == null || xyz[i].OwningPart == null || xyz[i].OwningPart.Tag != part.Tag || xyz[i].Units == null || xyz[i].Units.Tag != part.UnitCollection.FindObject("MilliMeter").Tag || !Finite(xyz[i].Value))
                throw new ArgumentException("Each coordinate must be a finite millimetre expression in this part.");
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
            FeatureAssociative=null, PointCoordinates=positions,
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

    // Verify the committed builder references and current expression consumers after update.
    // NX11 does not expose Feature.IsAssociative; never substitute builder data for it.
    public static void VerifyDrivenCurve(DrivenCurveResult input, double tolerance)
    {
        if (!Finite(tolerance) || tolerance <= 0) throw new ArgumentException("Invalid tolerance");
        var read=ReadDrivenCurve(input);
        if (!read.BuilderAssociative || read.BuilderPoints.Length != input.Points.Length)
            throw new InvalidOperationException("Curve builder is not associative or has wrong point count");
        for (int i=0;i<input.Points.Length;i++)
        {
            if (read.BuilderPoints[i] == null || read.BuilderPoints[i].Tag != input.Points[i].Point.Tag)
                throw new InvalidOperationException("Curve builder point mismatch");
            double[] xyz={read.PointCoordinates[i].X,read.PointCoordinates[i].Y,read.PointCoordinates[i].Z};
            for (int j=0;j<3;j++)
            {
                if (!Finite(xyz[j]) || !Finite(input.Points[i].Coordinates[j].Value) || Math.Abs(xyz[j]-input.Points[i].Coordinates[j].Value)>tolerance)
                    throw new InvalidOperationException("Curve point differs from expression");
                VerifySmartCoordinate(input.Points[i].Point, input.Points[i].Scalars, input.Points[i].Coordinates, j);
            }
        }
        if (input.Curve is Line && (!Near(read.LineStart,read.PointCoordinates[0],tolerance) ||
            !Near(read.LineEnd,read.PointCoordinates[1],tolerance)))
            throw new InvalidOperationException("Line endpoints differ from selected points");
        if (input.Curve is Arc)
        {
            Arc arc=(Arc)input.Curve; Point3d c; Vector3d x,y; arc.GetOrientation(out c,out x,out y);
            for (int i=0;i<3;i++) {
                Point3d q=read.PointCoordinates[i]; double dx=q.X-c.X, dy=q.Y-c.Y, dz=q.Z-c.Z;
                double u=dx*x.X+dy*x.Y+dz*x.Z, v=dx*y.X+dy*y.Y+dz*y.Z;
                double normal=dx*(x.Y*y.Z-x.Z*y.Y)+dy*(x.Z*y.X-x.X*y.Z)+dz*(x.X*y.Y-x.Y*y.X);
                if (!Finite(u) || !Finite(v) || !Finite(normal) || !Finite(arc.Radius) || Math.Abs(Math.Sqrt(u*u+v*v)-arc.Radius)>tolerance || Math.Abs(normal)>tolerance)
                    throw new InvalidOperationException("Arc point differs from native circle");
            }
            Func<double,Point3d> at=a=>new Point3d(c.X+arc.Radius*(Math.Cos(a)*x.X+Math.Sin(a)*y.X), c.Y+arc.Radius*(Math.Cos(a)*x.Y+Math.Sin(a)*y.Y), c.Z+arc.Radius*(Math.Cos(a)*x.Z+Math.Sin(a)*y.Z));
            Point3d start=at(arc.StartAngle), end=at(arc.EndAngle);
            if (!(Near(start,read.PointCoordinates[0],tolerance)&&Near(end,read.PointCoordinates[2],tolerance)) &&
                !(Near(end,read.PointCoordinates[0],tolerance)&&Near(start,read.PointCoordinates[2],tolerance)))
                throw new InvalidOperationException("Arc endpoints differ from selected points");
            Point3d m=read.PointCoordinates[1]; double mx=m.X-c.X,my=m.Y-c.Y,mz=m.Z-c.Z;
            double aMid=Math.Atan2(mx*y.X+my*y.Y+mz*y.Z,mx*x.X+my*x.Y+mz*x.Z);
            if (Positive(aMid-arc.StartAngle)>Positive(arc.EndAngle-arc.StartAngle)+1e-10)
                throw new InvalidOperationException("Arc does not follow requested midpoint branch");
        }
    }
    private static bool Near(Point3d a, Point3d b, double t)
    { return Math.Abs(a.X-b.X)<=t && Math.Abs(a.Y-b.Y)<=t && Math.Abs(a.Z-b.Z)<=t; }

    public static void VerifyDrivenSpline(DrivenSplineResult input, double[] knots, double tolerance)
    {
        if (knots == null || !Finite(tolerance) || tolerance <= 0) throw new ArgumentException("Invalid spline verification");
        var read=ReadDrivenSpline(input); int n=input.Coordinates.GetLength(0);
        if (!read.BuilderAssociative || read.BuilderType != NXOpen.Features.StudioSplineBuilderEx.Types.ByPoles ||
            read.BuilderDegree != 3 || read.Order != 4 || read.Rational || read.Periodic ||
            read.Poles.Length != n || read.BuilderConstraintPoints.Length != n || read.Knots.Length != knots.Length ||
            read.BuilderKnots.Length != knots.Length) throw new InvalidOperationException("Spline basis or builder mismatch");
        for (int k=0;k<knots.Length;k++) if (!Finite(knots[k]) || !Finite(read.Knots[k]) || !Finite(read.BuilderKnots[k]) || Math.Abs(read.Knots[k]-knots[k])>1e-12 || Math.Abs(read.BuilderKnots[k]-knots[k])>1e-12)
            throw new InvalidOperationException("Spline knot mismatch");
        for (int i=0;i<n;i++) {
            if (read.BuilderConstraintPoints[i] == null || read.BuilderConstraintPoints[i].Tag != input.PolePoints[i].Tag || read.Poles[i].W != 1.0)
                throw new InvalidOperationException("Spline selected point or weight mismatch");
            double[] xyz={read.Poles[i].X,read.Poles[i].Y,read.Poles[i].Z};
            double[] pt={read.PolePointCoordinates[i].X,read.PolePointCoordinates[i].Y,read.PolePointCoordinates[i].Z};
            for (int j=0;j<3;j++) {
                if (!Finite(xyz[j]) || !Finite(pt[j]) || !Finite(input.Coordinates[i,j].Value) || Math.Abs(xyz[j]-input.Coordinates[i,j].Value)>tolerance || Math.Abs(pt[j]-input.Coordinates[i,j].Value)>tolerance)
                    throw new InvalidOperationException("Spline pole differs from expression");
                Scalar[] scalars={input.PoleScalars[i,0],input.PoleScalars[i,1],input.PoleScalars[i,2]};
                Expression[] expressions={input.Coordinates[i,0],input.Coordinates[i,1],input.Coordinates[i,2]};
                VerifySmartCoordinate(input.PolePoints[i],scalars,expressions,j);
            }
        }
    }

    // Follow the actual persisted smart-object chain: selected point -> XYZ
    // scalar -> expression. GetUsingFeatures is retained as evidence only;
    // NX11 does not necessarily list the downstream curve/spline as a direct user.
    private static void VerifySmartCoordinate(Point point, Scalar[] expectedScalars, Expression[] expectedExpressions, int coordinate)
    {
        if(point==null || expectedScalars==null || expectedExpressions==null || expectedScalars.Length!=3 || expectedExpressions.Length!=3 || coordinate<0 || coordinate>2 || expectedScalars[coordinate]==null || expectedExpressions[coordinate]==null)
            throw new ArgumentException("Point, XYZ scalars and expressions required");
        Tag[] scalars; UFSession.GetUFSession().So.Ask3ScalarsOfPoint(point.Tag,out scalars);
        if(scalars==null || scalars.Length!=3 || scalars[coordinate]!=expectedScalars[coordinate].Tag)
            throw new InvalidOperationException("Point-to-scalar native dependency mismatch");
        Tag expr; UFSession.GetUFSession().So.AskExpOfScalar(scalars[coordinate],out expr);
        if(expr!=expectedExpressions[coordinate].Tag)
            throw new InvalidOperationException("Scalar-to-expression native dependency mismatch");
    }

    // These values come from the native spline pole array after verifying its
    // smart-coordinate chain and builder definition, not from requested input.
    public static Point3d[] CaptureSplinePoles(DrivenSplineResult input, double[] knots, double tolerance)
    {
        VerifyDrivenSpline(input,knots,tolerance);
        var poles=ReadDrivenSpline(input).Poles; var result=new Point3d[poles.Length];
        for(int i=0;i<poles.Length;i++) result[i]=new Point3d(poles[i].X,poles[i].Y,poles[i].Z);
        return result;
    }
    // Verify after a known source expression edit, with a before snapshot from
    // CaptureSplinePoles. The caller must also verify the edited source RHS/value
    // and choose a spline known by the formula graph to consume that driver.
    public static double VerifySplineEdited(DrivenSplineResult input, double[] knots, Point3d[] before, double tolerance, double minimumChange)
    {
        if(before==null || !Finite(minimumChange) || minimumChange<=tolerance) throw new ArgumentException("Prior poles and material change threshold required");
        Point3d[] after=CaptureSplinePoles(input,knots,tolerance);
        if(after.Length!=before.Length) throw new InvalidOperationException("Spline pole count changed");
        double maximum=0;
        for(int i=0;i<after.Length;i++)
        {
            if(!Finite(before[i].X)||!Finite(before[i].Y)||!Finite(before[i].Z)) throw new ArgumentException("Nonfinite prior pole");
            double dx=after[i].X-before[i].X,dy=after[i].Y-before[i].Y,dz=after[i].Z-before[i].Z;
            double change=Math.Sqrt(dx*dx+dy*dy+dz*dz); if(!Finite(change)) throw new InvalidOperationException("Nonfinite pole change");
            if(change>maximum) maximum=change;
        }
        if(maximum<minimumChange) throw new InvalidOperationException("Native spline poles did not respond to the edited driver");
        return maximum;
    }
    public static void VerifyExtrudeContainsCurve(Part part, NXOpen.Features.Feature feature, Curve curve)
    {
        if(part==null || !(feature is NXOpen.Features.Extrude) || curve==null || feature.OwningPart.Tag!=part.Tag || curve.OwningPart.Tag!=part.Tag)
            throw new ArgumentException("Current part, extrude, and curve required");
        var b=part.Features.CreateExtrudeBuilder(feature);
        try {
            if(b.Section==null) throw new InvalidOperationException("Extrude section missing");
            SectionData[] data; b.Section.GetSectionData(out data); if(data==null || data.Length==0) throw new InvalidOperationException("Section data missing");
            int matches=0;
            foreach(var item in data) {
                if(item==null) throw new InvalidOperationException("Null section data");
                try { SectionElementData[] elements; item.GetSectionElementsData(out elements);
                    if(elements==null) throw new InvalidOperationException("Section elements missing");
                    foreach(var element in elements) {
                        if(element==null) throw new InvalidOperationException("Null section element");
                        try { DisplayableObject selected,a,c; Point3d p1,p2; element.GetSectionElementData1(out selected,out a,out p1,out c,out p2);
                            if(selected!=null && selected.Tag==curve.Tag) matches++;
                        } finally {element.Dispose();}
                    }
                } finally {item.Dispose();}
            }
            if(matches!=1) throw new InvalidOperationException("Spline is not uniquely consumed by the native extrude section");
        } finally { b.Destroy(); }
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
    public static SketchGeometricConstraint CircleCenterAtOrigin(Sketch sketch, Arc circle, Point anchor)
    {
        if (sketch == null || circle == null || anchor == null || anchor.OwningPart.Tag != sketch.OwningPart.Tag || circle.OwningPart.Tag != sketch.OwningPart.Tag)
            throw new ArgumentException("Circle must belong to the sketch part.");
        return sketch.CreateCoincidentConstraint(
            new Sketch.ConstraintGeometry(circle, Sketch.ConstraintPointType.ArcCenter, 0),
            new Sketch.ConstraintGeometry(anchor, Sketch.ConstraintPointType.None, 0));
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
        bool end, bool horizontal, bool targetAfterOrigin, Expression expression, Point3d helpPoint, Point anchor)
    {
        if (sketch == null || curve == null || expression == null || anchor == null || anchor.OwningPart.Tag != sketch.OwningPart.Tag ||
            curve.OwningPart.Tag != sketch.OwningPart.Tag || expression.OwningPart.Tag != sketch.OwningPart.Tag)
            throw new ArgumentException("Curve and expression must belong to the sketch part.");
        var origin = new Sketch.DimensionGeometry { Geometry = anchor, AssocType = Sketch.AssocType.Midpoint, AssocValue = 0 };
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

