using System;
using System.Collections.Generic;

namespace NxSketchMcp.M2
{
    // Pure same-session topology predicate. Identifiers are transient inputs,
    // never persisted. Native identity, geometry, units and read-only auditing
    // remain the caller's responsibility.
    public static class V3SupportGraphPolicy
    {
        private static bool Exact(string[] actual, params string[] expected)
        {
            if (actual == null || actual.Length != expected.Length) return false;
            HashSet<string> a = new HashSet<string>(actual, StringComparer.Ordinal);
            HashSet<string> e = new HashSet<string>(expected, StringComparer.Ordinal);
            return a.Count == actual.Length && e.Count == expected.Length && a.SetEquals(e);
        }

        public static bool IsSupported(string externalFeature, string externalPlane, string internalDatum,
            string sketch, string csys, string xform, string referencePlane, string scalar,
            string direction, string point, string[] externalParents, string[] externalChildren,
            string[] datumParents, string[] datumChildren, string[] sketchParents,
            string[] planeParents, string[] csysParents, string[] xformParents,
            string[] planeAncestors, string[] csysAncestors, string[] xformAncestors)
        {
            string[] nodes = new string[] { externalFeature, externalPlane, internalDatum, sketch,
                csys, xform, referencePlane, scalar, direction, point };
            HashSet<string> distinct = new HashSet<string>(StringComparer.Ordinal);
            foreach (string node in nodes)
                if (String.IsNullOrWhiteSpace(node) || !distinct.Add(node)) return false;
            return Exact(externalParents) && Exact(externalChildren, internalDatum) &&
                Exact(datumParents, externalFeature) && Exact(datumChildren, sketch) &&
                Exact(sketchParents, internalDatum) &&
                Exact(planeParents, externalFeature, externalPlane) &&
                Exact(planeAncestors, externalFeature, externalPlane) &&
                Exact(csysParents, xform) && Exact(xformParents, referencePlane, scalar, direction, point) &&
                Exact(xformAncestors, referencePlane, scalar, direction, point, externalFeature, externalPlane) &&
                Exact(csysAncestors, xform, referencePlane, scalar, direction, point, externalFeature, externalPlane);
        }
    }
}
