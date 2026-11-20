using System;
using System.Collections.Generic;
using NXOpen;
using NXOpen.Features;
using NxSketchMcp.M2;

// This is an NX-side adapter, not an authorization or transaction boundary.
// Call only on the bound STA within the bridge's prepare/execute/verify lifecycle.
// Native handles and journal IDs below are scoped to the current bound session.
public static class V3ParameterBinding
{
    public sealed class Snapshot
    {
        internal Part Part;
        internal Sketch Sketch;
        internal SketchDimensionalConstraint Dimension;
        internal Feature Feature;
        internal Expression Expression;
        public string Kind;
        public string ConsumerId;
        public string Name;
        public string Formula;
        public string Unit;
        public double Value;
        public List<string> Geometry = new List<string>();
        public List<string> UsingFeatures = new List<string>();
        public List<string> ReferencingExpressions = new List<string>();
    }

    // Resolve the Sketch and dimension through the current bridge binding, not a
    // persisted Tag. Geometry operands are native relations, not inferred users.
    public static Snapshot CaptureDimension(Part part, Sketch sketch, SketchDimensionalConstraint dimension)
    {
        if (part == null || sketch == null || dimension == null) Fail("Missing sketch dimension");
        if (sketch.OwningPart == null || sketch.OwningPart.Tag != part.Tag ||
            dimension.OwningPart == null || dimension.OwningPart.Tag != part.Tag) Fail("Dimension is outside the work part");
        int sketchCount = 0, dimensionCount = 0;
        Sketch[] sketches = part.Sketches.ToArray();
        if (sketches == null) Fail("Sketch inventory unavailable");
        foreach (Sketch item in sketches)
        {
            if (item == null) Fail("Null sketch in inventory");
            if (item.Tag == sketch.Tag) sketchCount++;
        }
        foreach (Sketch.ConstraintType type in Enum.GetValues(typeof(Sketch.ConstraintType)))
        {
            if (type == Sketch.ConstraintType.NoCon || type == Sketch.ConstraintType.LastConType) continue;
            SketchConstraint[] items = sketch.GetAllConstraintsOfType(Sketch.ConstraintClass.Any, type);
            if (items == null) Fail("Constraint inventory unavailable");
            foreach (SketchConstraint item in items)
            {
                if (item == null) Fail("Null constraint in inventory");
                if (item.Tag == dimension.Tag) dimensionCount++;
            }
        }
        if (sketchCount != 1 || dimensionCount != 1) Fail("Sketch or constraint is missing or ambiguous");
        if (dimension.DimensionState != SketchDimensionalConstraint.DimensionStateType.Driving)
            Fail("Reference dimensions cannot drive a parameter");
        Expression expression = dimension.AssociatedExpression;
        Snapshot result = CaptureExpression(part, expression);
        int relationCount = 0;
        foreach (Sketch item in sketches)
        {
            foreach (Sketch.ConstraintType type in Enum.GetValues(typeof(Sketch.ConstraintType)))
            {
                if (type == Sketch.ConstraintType.NoCon || type == Sketch.ConstraintType.LastConType) continue;
                SketchConstraint[] constraints = item.GetAllConstraintsOfType(Sketch.ConstraintClass.Any, type);
                if (constraints == null) Fail("Constraint inventory unavailable");
                foreach (SketchConstraint constraint in constraints)
                {
                    if (constraint == null) Fail("Null constraint in inventory");
                    SketchDimensionalConstraint other = constraint as SketchDimensionalConstraint;
                    if (other != null && other.AssociatedExpression != null && other.AssociatedExpression.Tag == expression.Tag)
                        relationCount++;
                }
            }
        }
        if (relationCount != 1) Fail("Expression does not uniquely belong to this dimension");
        result.Kind = "driving_dimension";
        result.ConsumerId = Id(dimension);
        result.Sketch = sketch;
        result.Dimension = dimension;
        Sketch.DimensionGeometry[] operands = dimension.GetDimensionGeometry();
        if (operands == null || operands.Length == 0) Fail("Dimension has no geometry operands");
        foreach (Sketch.DimensionGeometry operand in operands)
        {
            if (operand.Geometry == null || operand.Geometry.OwningPart == null || operand.Geometry.OwningPart.Tag != part.Tag)
                Fail("Dimension geometry is missing or outside the work part");
            result.Geometry.Add(Id(operand.Geometry) + "|" + operand.AssocType + "|" + operand.AssocValue);
        }
        result.Geometry.Sort(StringComparer.Ordinal);
        return result;
    }

    // The caller must obtain expression from the native Extrude builder's
    // EndExtend.Value and verify the requested feature is an Extrude. Membership
    // alone cannot distinguish start, end, draft and offset expressions.
    public static Snapshot CaptureExtrude(Part part, Feature feature, Expression endExpression)
    {
        if (part == null || feature == null || feature.OwningPart == null || feature.OwningPart.Tag != part.Tag ||
            !String.Equals(feature.FeatureType, "EXTRUDE", StringComparison.OrdinalIgnoreCase)) Fail("Expected a work-part Extrude");
        Feature[] features = part.Features.GetFeatures();
        if (features == null) Fail("Feature inventory unavailable");
        int count = 0;
        foreach (Feature item in features) { if (item == null) Fail("Null feature"); if (item.Tag == feature.Tag) count++; }
        if (count != 1) Fail("Feature is missing or ambiguous");
        Snapshot result = CaptureExpression(part, endExpression);
        Expression[] owned = feature.GetExpressions();
        if (owned == null) Fail("Feature expressions unavailable");
        count = 0;
        foreach (Expression item in owned) { if (item == null) Fail("Null feature expression"); if (item.Tag == endExpression.Tag) count++; }
        Feature[] nativeUsers = endExpression.GetUsingFeatures();
        int userCount = 0;
        if (nativeUsers == null) Fail("Native expression consumers unavailable");
        foreach (Feature item in nativeUsers) if (item != null && item.Tag == feature.Tag) userCount++;
        if (count != 1 || userCount != 1) Fail("Extrude does not uniquely use the supplied expression");
        result.Kind = "extrude_end";
        result.ConsumerId = Id(feature);
        result.Feature = feature;
        return result;
    }

    private static Snapshot CaptureExpression(Part part, Expression expression)
    {
        if (expression == null) Fail("Expression is missing");
        Expression[] all = part.Expressions.ToArray();
        if (all == null) Fail("Expression inventory unavailable");
        int count = 0;
        foreach (Expression item in all) { if (item == null) Fail("Null expression"); if (item.Tag == expression.Tag) count++; }
        if (count != 1 || expression.IsInterpartExpression) Fail("Expression is missing, ambiguous or interpart");
        if (expression.Units == null || !String.Equals(expression.Units.Symbol, "mm", StringComparison.Ordinal))
            Fail("Only millimetre length expressions are supported");
        if (String.IsNullOrWhiteSpace(expression.Name) || String.IsNullOrWhiteSpace(expression.RightHandSide) ||
            Double.IsNaN(expression.Value) || Double.IsInfinity(expression.Value)) Fail("Incomplete expression readback");
        Snapshot result = new Snapshot { Part = part, Expression = expression, Name = expression.Name,
            Formula = expression.RightHandSide, Unit = expression.Units.Symbol, Value = expression.Value };
        Feature[] users = expression.GetUsingFeatures();
        Expression[] refs = expression.GetReferencingExpressions();
        if (users == null || refs == null) Fail("Native expression consumers unavailable");
        foreach (Feature item in users)
        {
            if (item == null || item.OwningPart == null || item.OwningPart.Tag != part.Tag) Fail("Invalid expression feature consumer");
            result.UsingFeatures.Add(Id(item));
        }
        foreach (Expression item in refs)
        {
            if (item == null || String.IsNullOrWhiteSpace(item.Name)) Fail("Invalid referencing expression");
            result.ReferencingExpressions.Add(item.Name);
        }
        result.UsingFeatures.Sort(StringComparer.Ordinal);
        result.ReferencingExpressions.Sort(StringComparer.Ordinal);
        return result;
    }

    // The bridge MUST already have established authorization, checked revision,
    // created an undo mark and arranged rollback/UNKNOWN handling. This method
    // makes no update or success claim. After it returns, update and Capture again,
    // compare all native relations, and independently measure changed geometry.
    public static void Apply(Part part, Snapshot prepared, string name, string formula)
    {
        if (part == null || prepared == null || prepared.Part == null || prepared.Part.Tag != part.Tag ||
            String.IsNullOrWhiteSpace(name) || String.IsNullOrWhiteSpace(formula)) Fail("Invalid binding edit");
        Snapshot current = prepared.Dimension != null
            ? CaptureDimension(part, prepared.Sketch, prepared.Dimension)
            : CaptureExtrude(part, prepared.Feature, prepared.Expression);
        if (prepared.Expression.Tag != current.Expression.Tag || prepared.Kind != current.Kind ||
            prepared.ConsumerId != current.ConsumerId || prepared.Name != current.Name || prepared.Formula != current.Formula ||
            prepared.Unit != current.Unit || prepared.Value != current.Value || !Equal(prepared.Geometry, current.Geometry) ||
            !Equal(prepared.UsingFeatures, current.UsingFeatures) || !Equal(prepared.ReferencingExpressions, current.ReferencingExpressions))
            Fail("Binding changed since preparation");
        if (!String.Equals(name, current.Name, StringComparison.Ordinal)) part.Expressions.Rename(current.Expression, name);
        if (!String.Equals(formula, current.Formula, StringComparison.Ordinal))
            part.Expressions.EditExpressionWithUnits(current.Expression, current.Expression.Units, formula);
    }

    private static bool Equal(List<string> a, List<string> b)
    {
        if (a == null || b == null || a.Count != b.Count) return false;
        for (int i = 0; i < a.Count; i++) if (!String.Equals(a[i], b[i], StringComparison.Ordinal)) return false;
        return true;
    }
    private static string Id(NXObject value)
    {
        if (value == null || String.IsNullOrWhiteSpace(value.JournalIdentifier)) Fail("Native consumer has no session identifier");
        return value.JournalIdentifier;
    }
    private static void Fail(string message) { throw new M2ModelException("UNSUPPORTED_PARAMETER", message); }
}
