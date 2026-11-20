"""Exact continuous comparison of exported native C5 input profile splines.

Inputs are native world-ABS homogeneous poles with unit weights and the P3
binary64 local-pole preview placed by the archived binary64 member frame.
This is not a bound to symbolic C5, source geometry, surfaces or Booleans.
"""
from fractions import Fraction as Q
import math
import re


class SplineBoundError(ValueError):
    """Inputs cannot support the stated cubic comparison."""


def _binary(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise SplineBoundError('expected a finite binary64 number')
    try:
        f = float(value)
    except OverflowError as exc:
        raise SplineBoundError('number outside binary64 range') from exc
    if not math.isfinite(f) or (type(value) is int and int(f) != value):
        raise SplineBoundError('number is not representable in binary64')
    return Q(f)


def _exact_pair(pair):
    if not isinstance(pair, list) or len(pair) != 2 or any(type(x) is not int for x in pair) or pair[1] == 0:
        raise SplineBoundError('invalid rational pair')
    return Q(*pair)


def _validate_basis(knots, poles):
    if len(poles) < 4 or len(knots) != len(poles) + 4:
        raise SplineBoundError('cubic knot/pole count mismatch')
    if any(a > b for a, b in zip(knots, knots[1:])):
        raise SplineBoundError('knots are not ordered')
    if not knots[0] == knots[1] == knots[2] == knots[3] < knots[-4] == knots[-3] == knots[-2] == knots[-1]:
        raise SplineBoundError('expected clamped cubic')
    if any(not knots[3] < k < knots[-4] for k in knots[4:-4]):
        raise SplineBoundError('invalid interior knot')
    for k in set(knots[4:-4]):
        if knots.count(k) > 3:
            raise SplineBoundError('discontinuous interior knot unsupported')


def _evaluate(knots, poles, u):
    """Exact de Boor evaluation; continuous clamped cubic only."""
    n = len(poles)
    if not knots[3] <= u <= knots[n]:
        raise SplineBoundError('evaluation outside spline domain')
    if u == knots[n]:
        span = n - 1
    else:
        span = next(i for i in range(3, n) if knots[i] <= u < knots[i+1])
    d = [list(poles[span-3+j]) for j in range(4)]
    for level in range(1, 4):
        for j in range(3, level-1, -1):
            i = span-3+j
            denom = knots[i+4-level] - knots[i]
            if denom == 0:
                raise SplineBoundError('degenerate active knot span')
            a = (u-knots[i])/denom
            d[j] = [(1-a)*x+a*y for x, y in zip(d[j-1], d[j])]
    return d[3]


def _bernstein(values):
    """Recover cubic Bernstein control vectors from values at 0,1/3,2/3,1."""
    p0, p1, p2, p3 = values
    a = [27*x-8*y-z for x, y, z in zip(p1, p0, p3)]
    b = [27*x-y-8*z for x, y, z in zip(p2, p0, p3)]
    return [p0, [(2*x-y)/18 for x, y in zip(a, b)],
            [(2*y-x)/18 for x, y in zip(a, b)], p3]


def _pair(q):
    return [q.numerator, q.denominator]


def _upper_float(q):
    value = float(q)
    if not math.isfinite(value):
        raise SplineBoundError('bound overflows binary64')
    return math.nextafter(value, math.inf)


def assess_native_c5_profiles(native, c5, final_plan):
    """Bound native versus P3 preview for every exported curve, in ABS mm.

    Normalized native u maps to lo+u*(hi-lo) in the original P3 FIN. All
    arithmetic after importing binary64 inputs is exact rational arithmetic.
    On every subspan from the union of the two knot sets, the difference is
    cubic. Its Bernstein control-point L1 maximum bounds every same-u 3D
    distance, and hence the two-sided Hausdorff distance. Result covers only
    supplied IDs; coverage_complete flags the expected set of 88 curves.
    """
    try:
        if native['schema'] != 'p4-native-c5-profiles/1' or c5['schema'] != 'p3-flank-parameter-expression/0.1' or final_plan['schema'] != 'p3-final-mathematical-plan/1':
            raise SplineBoundError('unexpected input schema')
        curves = native['curves']
        if not isinstance(curves, list) or not curves:
            raise SplineBoundError('no native curves')
        templates = c5['templates']
        final_templates = final_plan['construction']['profiles']['section6']['templates']
        nodes = final_plan['construction']['nodes']
        by_id = {n['id']: n for n in nodes}
        if len(by_id) != len(nodes):
            raise SplineBoundError('duplicate plan node')
        expected = {'member_%02d_%s_tool/edge/%d' % (i, kind, edge)
                    for i in range(22) for kind in ('straight', 'roll') for edge in (0, 4)}
        results = []
        seen = set()
        for curve in curves:
            ident = curve['id']
            match = re.fullmatch(r'member_(\d{2})_(straight|roll)_tool/edge/(0|4)', ident)
            if not match or ident not in expected or ident in seen:
                raise SplineBoundError('invalid or duplicate curve identity')
            seen.add(ident)
            member, kind, edge = int(match[1]), match[2], int(match[3])
            if curve['order'] != 4 or type(curve['order']) is not int or curve['rational'] is not False or curve['periodic'] is not False:
                raise SplineBoundError('native curve must be nonrational, nonperiodic cubic')
            nk = [_binary(x) for x in curve['knots']]
            npoles = []
            for row in curve['poles']:
                if not isinstance(row, list) or len(row) != 4:
                    raise SplineBoundError('native poles require [x,y,z,w]')
                xyz = [_binary(x) for x in row]
                if xyz[3] != 1:
                    raise SplineBoundError('native weight is not one')
                npoles.append(xyz[:3])
            _validate_basis(nk, npoles)
            if nk[0] != 0 or nk[-1] != 1:
                raise SplineBoundError('native knots must be normalized to [0,1]')
            side = 'F0024' if edge == 0 else 'F0002'
            template = templates[side]
            ft = final_templates[side]
            if template['basis'] != ft['basis'] or template['poles'] != ft['poles']:
                raise SplineBoundError('P3 template differs from final plan')
            basis = template['basis']
            if basis['order'] != 4 or basis['rational'] is not False:
                raise SplineBoundError('P3 spline basis is not a nonrational cubic')
            ok = [_exact_pair(x) for x in basis['knots_exact']]
            lo, hi = [_exact_pair(x) for x in basis['fin_interval_exact']]
            if any(Q(float(x)) != x for x in ok + [lo, hi]):
                raise SplineBoundError('P3 knot or FIN is not exact binary64')
            local = [[_binary(p['t_mm']['value']), _binary(p['r_mm']['value'])] for p in template['poles']]
            if basis['num_poles'] != len(local):
                raise SplineBoundError('P3 pole count mismatch')
            _validate_basis(ok, local)
            if not ok[3] <= lo < hi <= ok[len(local)]:
                raise SplineBoundError('invalid P3 FIN interval')
            straight = by_id['member_%02d_straight_tool' % member]
            roll = by_id['member_%02d_roll_tool' % member]
            if straight['frame'] != roll['frame']:
                raise SplineBoundError('straight and roll frames differ')
            frame = straight['frame']
            origin, et, er = ([_binary(x) for x in frame[k]] for k in ('origin_mm', 'e_t', 'e_r'))
            if len(origin) != 3 or len(et) != 3 or len(er) != 3:
                raise SplineBoundError('invalid member frame')
            opoles = [[origin[j]+p[0]*et[j]+p[1]*er[j] for j in range(3)] for p in local]
            cuts = sorted({Q(0), Q(1), *nk[4:-4],
                           *((k-lo)/(hi-lo) for k in ok[4:-4] if lo < k < hi)})
            bound = Q(0)
            for left, right in zip(cuts, cuts[1:]):
                values = []
                for k in range(4):
                    u = left+(right-left)*Q(k, 3)
                    a = _evaluate(nk, npoles, u)
                    b = _evaluate(ok, opoles, lo+u*(hi-lo))
                    values.append([x-y for x, y in zip(a, b)])
                bound = max(bound, *(sum(abs(x) for x in v) for v in _bernstein(values)))
            results.append({'id': ident, 'template': side, 'subspan_count': len(cuts)-1,
                            'l1_upper_mm_exact': _pair(bound), 'l1_upper_mm': _upper_float(bound)})
        maximum = max(Q(*r['l1_upper_mm_exact']) for r in results)
        return {'schema': 'p4-native-c5-spline-bound/1', 'curves': results,
                'curve_count': len(results), 'coverage_complete': seen == expected,
                'missing_ids': sorted(expected-seen), 'max_l1_upper_mm_exact': _pair(maximum),
                'max_l1_upper_mm': _upper_float(maximum),
                'scope': 'input profile curves against the archived P3 binary64 preview in the archived binary64 frame',
                'method': 'exact binary64 fractions, common knot partition, cubic Bernstein L1 convex-hull bound',
                'limitations': ['not a symbolic C5 or original source BREP correspondence bound',
                                'not a bound on generated surfaces, trims, Booleans or whole body',
                                'same normalized parameter and reported native curve data are assumed'],
                'execution_approved': False}
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        if isinstance(exc, SplineBoundError):
            raise
        raise SplineBoundError('incomplete or invalid comparison input') from exc
