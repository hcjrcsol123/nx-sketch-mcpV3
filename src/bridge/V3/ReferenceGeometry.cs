using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
using NxSketchMcp.M2;

namespace NxSketchMcp.V3
{
    // Called only on the authorized NX thread with a freshly resolved tag.
    // Ownership, body binding, snapshot consistency and dirty guards belong to
    // the caller; this class must not be exposed as a standalone tag reader.
    public static class ReferenceGeometry
    {
        private const ulong MaxBytes = 2UL * 1024UL * 1024UL;

        [DllImport("ReferenceGeometryNative.dll", EntryPoint = "rg_read_face_v1", CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
        private static extern int ReadNative(uint tag, double curveTolerance, double surfaceTolerance, out IntPtr buffer, out ulong length);

        [DllImport("ReferenceGeometryNative.dll", EntryPoint = "rg_free_v1", CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
        private static extern void FreeNative(IntPtr buffer);

        [DllImport("ReferenceGeometryNative.dll", EntryPoint = "rg_probe_face_v2", CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
        private static extern int ProbeNative(uint partTag, uint faceTag, double curveTolerance, double surfaceTolerance, out IntPtr buffer, out ulong length);

        [DllImport("ReferenceGeometryNative.dll", EntryPoint = "rg_probe_face_v3", CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
        private static extern int ProbeNativeV3(uint partTag, uint faceTag, double curveTolerance, double surfaceTolerance,
            [In] uint[] edgeTags, [In] byte[] edgeKinds, uint count, out IntPtr buffer, out ulong length);

        // Edge arrays originate from this same bound face's guarded inventory.
        // Kind values: 1 Circular, 2 Linear, 3 Spline, 4 Intersection.
        public static Dictionary<string, object> ReadFaceWithEdges(uint partTag, uint faceTag, double curveTolerance, double surfaceTolerance, uint[] edgeTags, byte[] edgeKinds)
        {
            if (partTag == 0 || faceTag == 0 || Double.IsNaN(curveTolerance) || Double.IsInfinity(curveTolerance) || curveTolerance <= 0 ||
                Double.IsNaN(surfaceTolerance) || Double.IsInfinity(surfaceTolerance) || surfaceTolerance <= 0 ||
                edgeTags == null || edgeKinds == null || edgeTags.Length == 0 || edgeTags.Length > 4096 || edgeKinds.Length != edgeTags.Length)
                throw new ArgumentException("Current loaded part, face, positive tolerances and bounded edge inventory are required.");
            HashSet<uint> unique = new HashSet<uint>();
            for (int i = 0; i < edgeTags.Length; i++)
                if (edgeTags[i] == 0 || edgeKinds[i] < 1 || edgeKinds[i] > 4 || !unique.Add(edgeTags[i]))
                    throw new ArgumentException("Edge inventory must contain unique current tags and supported types.");
            IntPtr buffer = IntPtr.Zero;
            try
            {
                ulong length;
                int rc = ProbeNativeV3(partTag, faceTag, curveTolerance, surfaceTolerance, edgeTags, edgeKinds, (uint)edgeTags.Length, out buffer, out length);
                if (rc != 0) throw new InvalidOperationException("Native reference geometry read failed: " + rc);
                if (buffer == IntPtr.Zero || length == 0 || length > MaxBytes)
                    throw new InvalidOperationException("Invalid or excessive native reference geometry output.");
                byte[] bytes = new byte[(int)length]; Marshal.Copy(buffer, bytes, 0, bytes.Length);
                Dictionary<string, object> result = M2Json.ParseDetailObject(new UTF8Encoding(false, true).GetString(bytes));
                object schema, outcome;
                if (!result.TryGetValue("schema", out schema) || !Object.Equals(schema, "v3-reference-geometry-probe-v3") ||
                    !result.TryGetValue("outcome", out outcome) || !(Object.Equals(outcome, "CLEAN_TRACE") ||
                    Object.Equals(outcome, "DIRTY_STOP") || Object.Equals(outcome, "NATIVE_ERROR")))
                    throw new InvalidOperationException("Unexpected native reference geometry contract or outcome.");
                return result;
            }
            finally { if (buffer != IntPtr.Zero) FreeNative(buffer); }
        }

        // The authorized caller must establish that partTag is the current,
        // fully loaded bound part. UF_PART_is_modified(false) does not do so.
        public static Dictionary<string, object> ReadFaceDiagnostic(uint partTag, uint faceTag, double curveTolerance, double surfaceTolerance)
        {
            if (partTag == 0 || faceTag == 0 || Double.IsNaN(curveTolerance) || Double.IsInfinity(curveTolerance) || curveTolerance <= 0 ||
                Double.IsNaN(surfaceTolerance) || Double.IsInfinity(surfaceTolerance) || surfaceTolerance <= 0)
                throw new ArgumentException("Current loaded part, face and positive finite approximation tolerances are required.");
            IntPtr buffer = IntPtr.Zero;
            try
            {
                ulong length;
                int rc = ProbeNative(partTag, faceTag, curveTolerance, surfaceTolerance, out buffer, out length);
                if (rc != 0) throw new InvalidOperationException("Native reference geometry diagnostic failed: " + rc);
                if (buffer == IntPtr.Zero || length == 0 || length > MaxBytes)
                    throw new InvalidOperationException("Invalid or excessive native geometry diagnostic.");
                byte[] bytes = new byte[(int)length];
                Marshal.Copy(buffer, bytes, 0, bytes.Length);
                Dictionary<string, object> result = M2Json.ParseDetailObject(new UTF8Encoding(false, true).GetString(bytes));
                object schema, outcome;
                if (!result.TryGetValue("schema", out schema) || !Object.Equals(schema, "v3-reference-geometry-probe-v2") ||
                    !result.TryGetValue("outcome", out outcome) || !(Object.Equals(outcome, "CLEAN_TRACE") ||
                      Object.Equals(outcome, "DIRTY_STOP") || Object.Equals(outcome, "NATIVE_ERROR")))
                    throw new InvalidOperationException("Unexpected native reference geometry diagnostic contract or outcome.");
                return result;
            }
            finally { if (buffer != IntPtr.Zero) FreeNative(buffer); }
        }

        public static Dictionary<string, object> ReadFace(uint tag, double curveTolerance, double surfaceTolerance)
        {
            if (tag == 0 || Double.IsNaN(curveTolerance) || Double.IsInfinity(curveTolerance) || curveTolerance <= 0 ||
                Double.IsNaN(surfaceTolerance) || Double.IsInfinity(surfaceTolerance) || surfaceTolerance <= 0)
                throw new ArgumentException("Current face and positive finite approximation tolerances are required.");
            IntPtr buffer = IntPtr.Zero;
            try
            {
                ulong length;
                int rc = ReadNative(tag, curveTolerance, surfaceTolerance, out buffer, out length);
                if (rc != 0) throw new InvalidOperationException("Native reference geometry reader failed: " + rc);
                if (buffer == IntPtr.Zero || length == 0 || length > MaxBytes)
                    throw new InvalidOperationException("Invalid or excessive native geometry response.");
                byte[] bytes = new byte[(int)length];
                Marshal.Copy(buffer, bytes, 0, bytes.Length);
                string json = new UTF8Encoding(false, true).GetString(bytes);
                Dictionary<string, object> result = M2Json.ParseDetailObject(json);
                object schema, status;
                if (!result.TryGetValue("schema", out schema) || !Object.Equals(schema, "v3-reference-geometry-detail-v1") ||
                    !result.TryGetValue("status", out status) || !Object.Equals(status, "INCONCLUSIVE"))
                    throw new InvalidOperationException("Unexpected native reference geometry contract or status.");
                return result;
            }
            finally
            {
                if (buffer != IntPtr.Zero) FreeNative(buffer);
            }
        }
    }
}
