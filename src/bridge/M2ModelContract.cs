using System;
using System.Collections.Generic;

namespace NxSketchMcp.M2
{
    // NXOpen is deliberately kept out of M2Bridge.dll. The loaded NX entry assembly
    // supplies this adapter, and every adapter call is made on the dispatcher STA.
    public interface IM2ModelAdapter
    {
        M2ModelBinding Takeover(string expectedPartPath, string artifactScope, string sessionEpoch,
            string loadInstanceId, int bindingEpoch);
        bool IsBindingCurrent(M2ModelBinding binding, out string reason);
        Dictionary<string, object> GetSession(M2ModelBinding binding);
        Dictionary<string, object> InspectPart(M2ModelBinding binding);
        Dictionary<string, object> InspectSketch(M2ModelBinding binding, string sketchId);
        void Release(M2ModelBinding binding);
    }

    // Optional read-only inventory; identifiers are local to the bound session.
    public interface IV3ReferenceAdapter
    {
        Dictionary<string, object> InspectReference(M2ModelBinding binding, string revisionId,
            string snapshotId, string bodyId);
    }

    // Optional P3 read: descriptors are semantic data, not persistent tags.
    public interface IV3ReferenceDetailAdapter
    {
        Dictionary<string, object> InspectReferenceDetail(M2ModelBinding binding, string revisionId,
            string snapshotId, string bodyId, V3ReferenceDetailRequest request);
    }

    public sealed class V3ReferenceDetailRequest
    {
        public double MatchLinear, CurveTolerance, SurfaceTolerance;
        public V3ReferenceFaceSelector[] Selectors;
    }

    public sealed class V3ReferenceFaceSelector
    {
        public string Label, SurfaceType;
        public int UfType, EdgeCount;
        public double[] BoundingBox;
    }

    // Exact, deterministic field comparison within one read/session. Paths use
    // JSON Pointer escaping; array order is significant and tags are not IDs
    // that can be reused in a later session.
    public static class V3InventoryDifference
    {
        public static List<object> Compare(object before, object after)
        {
            List<object> changes = new List<object>();
            Walk(before, true, after, true, "", changes);
            return changes;
        }

        private static string Key(string key) { return key.Replace("~", "~0").Replace("/", "~1"); }

        private static void Walk(object before, bool hasBefore, object after, bool hasAfter, string path, List<object> changes)
        {
            if (hasBefore && hasAfter)
            {
                Dictionary<string, object> a = before as Dictionary<string, object>;
                Dictionary<string, object> b = after as Dictionary<string, object>;
                if (a != null && b != null)
                {
                    SortedSet<string> keys = new SortedSet<string>(a.Keys, StringComparer.Ordinal);
                    keys.UnionWith(b.Keys);
                    foreach (string key in keys)
                    {
                        object av, bv; bool ah = a.TryGetValue(key, out av), bh = b.TryGetValue(key, out bv);
                        Walk(av, ah, bv, bh, path + "/" + Key(key), changes);
                    }
                    return;
                }
                System.Collections.IList left = before as System.Collections.IList;
                System.Collections.IList right = after as System.Collections.IList;
                if (left != null && right != null)
                {
                    int count = Math.Max(left.Count, right.Count);
                    for (int i = 0; i < count; i++)
                        Walk(i < left.Count ? left[i] : null, i < left.Count,
                             i < right.Count ? right[i] : null, i < right.Count,
                             path + "/" + i.ToString(System.Globalization.CultureInfo.InvariantCulture), changes);
                    return;
                }
                if (Object.Equals(before, after)) return;
            }
            changes.Add(new Dictionary<string, object> {
                { "path", path }, { "before_present", hasBefore }, { "before", before },
                { "after_present", hasAfter }, { "after", after }
            });
        }
    }

    // Restricted P2 block transaction; the bridge owns authorization and retains
    // the opaque adapter snapshot only for the current binding and session.
    // UNCHANGED is valid only before any model write. ROLLED_BACK requires
    // Evidence["rollback_readback_verified"] == true; otherwise freeze UNKNOWN.
    public interface IV3BlockBindingAdapter
    {
        V3BlockBindingSnapshot PrepareBlockBinding(M2ModelBinding binding, V3BlockBindingRequest request);
        M2ParameterExecutionResult ExecuteBlockBinding(M2ModelBinding binding, V3BlockBindingSnapshot plan);
        M2PartVerificationResult VerifyBlockBinding(M2ModelBinding binding, V3BlockBindingSnapshot plan);
    }

    public sealed class V3BlockBindingRequest
    {
        public string RevisionId;
        public string SketchId;
        public string XConstraintId;
        public string YConstraintId;
        public string WidthConstraintId;
        public string HeightConstraintId;
        public string ExtrudeFeatureId;
        public string BodyId;
        public string Action;
        public string ValueText;
    }

    public sealed class V3BlockBindingSnapshot
    {
        public string RevisionId;
        public Dictionary<string, object> PublicView;
        public object AdapterState;
    }

    public interface IV3CompositionAdapter
    {
        V3BlockBindingSnapshot PrepareComposition(M2ModelBinding binding, string revision, List<object> steps);
        M2ParameterExecutionResult ExecuteComposition(M2ModelBinding binding, V3BlockBindingSnapshot plan);
        M2PartVerificationResult VerifyComposition(M2ModelBinding binding, V3BlockBindingSnapshot plan);
    }

    // Parameter editing is an optional, narrowly scoped extension. The bridge
    // creates and retains its own immutable plan after this adapter has resolved
    // the real NX constraint, expression, unit, and geometry relationship.
    public interface IM2OperationAdapter
    {
        M2ParameterPlanSnapshot PrepareParameterEdit(M2ModelBinding binding, M2ParameterEditRequest request);
        M2ParameterExecutionResult ExecuteParameterEdit(M2ModelBinding binding,
            M2ParameterPlanSnapshot prepared, string requestedValue, string requestedUnit);
    }

    // M2-7 adds explicit verification and saved-copy operations without making
    // these methods mandatory for older fixture adapters.
    public interface IM2M27ModelAdapter
    {
        M2PartVerificationResult VerifyParameterEdit(M2ModelBinding binding,
            M2ParameterPlanSnapshot prepared);
        M2SaveCopyResult SaveCopy(M2ModelBinding binding, string targetPath, bool reopen);
    }

    public sealed class M2PartVerificationResult
    {
        public bool Verified;
        public string RevisionId;
        public Dictionary<string, object> Checks;
        public string ErrorCode;
        public string ErrorMessage;
    }

    public sealed class M2SaveCopyResult
    {
        // SAVED means SaveAs completed. UNKNOWN means the adapter cannot prove
        // whether the output was saved or reopened; the bridge must freeze writes.
        public string State;
        public string PartPath;
        public string PartTag;
        public string RevisionId;
        public Dictionary<string, object> Identity;
        public bool Reopened;
        public Dictionary<string, object> Checks;
        public Dictionary<string, object> Evidence;
        public string ErrorCode;
        public string ErrorMessage;
    }

    public sealed class M2ParameterEditRequest
    {
        public string RevisionId;
        public string SketchId;
        public string ConstraintId;
        public string ValueText;
        public string Unit;
    }

    public sealed class M2ParameterPlanSnapshot
    {
        public string RevisionId;
        public string SketchId;
        public string ConstraintId;
        public string DimensionType;
        public string DimensionState;
        public string SketchFeatureId;
        public string ExpressionName;
        public string ExpressionRightHandSide;
        public string CurrentValue;
        public string Unit;
        public List<string> GeometryRefs;
        public object AdapterState;
    }

    public sealed class M2ParameterExecutionResult
    {
        // APPLIED, ROLLED_BACK, UNCHANGED, or UNKNOWN.
        public string State;
        public string RevisionId;
        public Dictionary<string, object> Evidence;
        public string ErrorCode;
        public string ErrorMessage;
    }

    public sealed class M2ModelBinding
    {
        // The bridge passes ArtifactScope to the NX adapter. ArtifactKind and
        // ArtifactAssessment are returned from native structure checks.
        public string ArtifactScope;
        public string ArtifactKind;
        public Dictionary<string, object> ArtifactAssessment;
        public bool IsReadOnly;
        public string SessionEpoch;
        public string LoadInstanceId;
        public int BindingEpoch;
        public string PartPath;
        public string PartTag;
        public string NxBuild;
        public string NxBuildSource;
        public string RevisionId;
        public string CanonicalSnapshot;
        public Dictionary<string, object> Identity;
        public object AdapterState;
    }

    public sealed class M2ModelException : Exception
    {
        public readonly string Code;
        public readonly Dictionary<string, object> Diagnostics;

        public M2ModelException(string code, string message) : this(code, message, null)
        {
        }

        public M2ModelException(string code, string message, Dictionary<string, object> diagnostics) : base(message)
        {
            Code = String.IsNullOrEmpty(code) ? "MODEL_READ_FAILED" : code;
            Diagnostics = diagnostics;
        }
    }
}
