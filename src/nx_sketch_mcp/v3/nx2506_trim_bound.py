"""Continuous bounds between explicitly supplied spatial B-spline trims.

All binary64 inputs are treated as exact numbers. A common affine parameter
maps [0,1] to each specified interval; it need not be the kernel's actual
edge/FIN correspondence. The output bounds only the mathematical curve images
in the records, not their relationship to a face, body, or source geometry.
"""
from bisect import bisect_right
from collections import Counter
from fractions import Fraction as Q
from math import comb, isfinite, nextafter, inf


class TrimBoundError(ValueError):
    """A complete continuous bound cannot be derived from the input."""


def _number(value):
    if isinstance(value, (list, tuple)) and len(value) == 2:
        if any(type(x) is not int for x in value) or value[1] <= 0:
            raise TrimBoundError('invalid exact rational pair')
        return Q(*value)
    if type(value) not in (int, float):
        raise TrimBoundError('expected binary64 or exact rational pair')
    try:
        v = float(value)
    except OverflowError as exc:
        raise TrimBoundError('number outside binary64 range') from exc
    if not isfinite(v) or (type(value) is int and int(v) != value):
        raise TrimBoundError('expected finite representable binary64')
    return Q(v)


def _curve(record):
    """Parse weighted homogeneous poles (wx, wy, wz, w), positive weights."""
    if not isinstance(record, dict):
        raise TrimBoundError('curve must be an object')
    order = record.get('order')
    if type(order) is not int or not 2 <= order <= 7:
        raise TrimBoundError('supported orders are 2 through 7')
    if record.get('periodic') is not False:
        raise TrimBoundError('only explicit nonperiodic representations supported')
    knots, poles = record.get('knots'), record.get('poles')
    if not isinstance(knots, (list, tuple)) or not isinstance(poles, (list, tuple)):
        raise TrimBoundError('missing knots or poles')
    if len(poles) < order or len(knots) != len(poles) + order:
        raise TrimBoundError('knot and pole counts inconsistent')
    k = [_number(x) for x in knots]
    if any(a > b for a, b in zip(k, k[1:])):
        raise TrimBoundError('knots must be nondecreasing')
    n, degree = len(poles), order-1
    if k[degree] >= k[n]:
        raise TrimBoundError('empty active domain')
    for t, count in Counter(k).items():
        if count > order or (k[degree] < t < k[n] and count >= order):
            raise TrimBoundError('discontinuous or invalid knot multiplicity')
    pole_format = record.get('pole_format', 'homogeneous')
    if pole_format not in ('homogeneous', 'cartesian_weight'):
        raise TrimBoundError('unsupported pole format')
    rows = []
    for p in poles:
        if not isinstance(p, (list, tuple)) or len(p) != 4:
            raise TrimBoundError('poles must be homogeneous [wx,wy,wz,w]')
        row = [_number(x) for x in p]
        if row[3] <= 0:
            raise TrimBoundError('all homogeneous pole weights must be positive')
        if pole_format == 'cartesian_weight':
            row = [row[0]*row[3], row[1]*row[3], row[2]*row[3], row[3]]
        rows.append(row)
    interval = record.get('interval')
    if not isinstance(interval, (list, tuple)) or len(interval) != 2:
        raise TrimBoundError('explicit directed interval required')
    a, b = map(_number, interval)
    if a == b or min(a, b) < k[degree] or max(a, b) > k[n]:
        raise TrimBoundError('invalid directed interval')
    return {'degree': degree, 'knots': k, 'poles': rows, 'a': a, 'b': b}


def _evaluate(c, u):
    p, k, rows, n = c['degree'], c['knots'], c['poles'], len(c['poles'])
    span = n-1 if u == k[n] else bisect_right(k, u)-1
    if not p <= span < n:
        raise TrimBoundError('parameter outside active domain')
    d = [rows[span-p+j][:] for j in range(p+1)]
    for level in range(1, p+1):
        for j in range(p, level-1, -1):
            i = span-p+j
            denom = k[i+p-level+1] - k[i]
            if denom <= 0:
                raise TrimBoundError('degenerate active knot interval')
            alpha = (u-k[i])/denom
            d[j] = [(1-alpha)*x+alpha*y for x, y in zip(d[j-1], d[j])]
    return d[p]


def _bernstein_matrix_inverse(p):
    """Exact inversion at p+1 distinct rational interpolation points."""
    rows = []
    for i in range(p+1):
        t = Q(i, p)
        rows.append([Q(comb(p, j))*t**j*(1-t)**(p-j) for j in range(p+1)]
                    + [Q(int(i == j)) for j in range(p+1)])
    for col in range(p+1):
        pivot = next((i for i in range(col, p+1) if rows[i][col]), None)
        if pivot is None:
            raise TrimBoundError('singular interpolation matrix')
        rows[col], rows[pivot] = rows[pivot], rows[col]
        divisor = rows[col][col]
        rows[col] = [x/divisor for x in rows[col]]
        for i in range(p+1):
            if i != col:
                v = rows[i][col]
                rows[i] = [x-v*y for x, y in zip(rows[i], rows[col])]
    return [r[p+1:] for r in rows]


def _controls(curve, left, right, inverse):
    p = curve['degree']
    values = []
    for i in range(p+1):
        t = left+(right-left)*Q(i, p)
        values.append(_evaluate(curve, curve['a']+t*(curve['b']-curve['a'])))
    return [[sum((inverse[i][j]*values[j][d] for j in range(p+1)), Q())
             for d in range(4)] for i in range(p+1)]


def _product(a, b):
    """Bernstein coefficients of a product, exact rational arithmetic."""
    m, n = len(a)-1, len(b)-1
    return [sum((a[i]*b[k-i]*Q(comb(m, i)*comb(n, k-i), comb(m+n, k))
                 for i in range(max(0, k-n), min(m, k)+1)), Q())
            for k in range(m+n+1)]


def _pair(x):
    return [x.numerator, x.denominator]


def _up(x):
    try:
        f = float(x)
    except OverflowError as exc:
        raise TrimBoundError('bound outside finite binary64 range') from exc
    if not isfinite(f):
        raise TrimBoundError('bound outside finite binary64 range')
    return nextafter(f, inf) if Q(f) < x else f


def bound_trim_pair(native, reference, *, max_subspans=10000):
    """Bound two directed B-spline image sets by common-affine-parameter L1.

    Curves specify `order`, `periodic: false`, full `knots`, homogeneous
    `poles` as [wx,wy,wz,w], and a directed `interval` [start,end]. Set
    `pole_format` to `cartesian_weight` for [x,y,z,w]; multiplication by w
    then uses exact arithmetic. The default format is `homogeneous`. Values may
    be exact binary64 integers/floats or rational [numerator,denominator].
    The map t -> start+t*(end-start), 0<=t<=1, is assumed for each curve.
    Both full interval images are covered, so this is a two-sided Hausdorff
    upper bound even if the asserted parameter correspondence is not geometric.
    The fit to the desired P3 feature and native BREP edge is separate evidence.
    """
    if type(max_subspans) is not int or not 1 <= max_subspans <= 100000:
        raise TrimBoundError('invalid subspan limit')
    a, b = _curve(native), _curve(reference)
    cuts = {Q(0), Q(1)}
    for c in (a, b):
        cuts.update((v-c['a'])/(c['b']-c['a']) for v in c['knots']
                    if min(c['a'], c['b']) < v < max(c['a'], c['b']))
    cuts = sorted(cuts)
    if len(cuts)-1 > max_subspans:
        raise TrimBoundError('subspan limit exceeded')
    inva, invb = _bernstein_matrix_inverse(a['degree']), _bernstein_matrix_inverse(b['degree'])
    maximum = Q()
    for left, right in zip(cuts, cuts[1:]):
        ca, cb = _controls(a, left, right, inva), _controls(b, left, right, invb)
        wa, wb = [r[3] for r in ca], [r[3] for r in cb]
        amin, bmin = min(wa), min(wb)
        if amin <= 0 or bmin <= 0:
            raise TrimBoundError('could not establish positive weight on subspan')
        numerators = []
        for dim in range(3):
            ab = _product([r[dim] for r in ca], wb)
            ba = _product([r[dim] for r in cb], wa)
            numerators.append([x-y for x, y in zip(ab, ba)])
        upper = max(sum(abs(numerators[d][i]) for d in range(3))
                    for i in range(len(numerators[0]))) / (amin*bmin)
        maximum = max(maximum, upper)
    return {'schema': 'p4-trim-curve-pair-bound/1',
            'subspan_count': len(cuts)-1,
            'hausdorff_l1_upper_mm_exact': _pair(maximum),
            'hausdorff_l1_upper_mm': _up(maximum),
            'method': 'exact rational common-knot partition, homogeneous Bernstein product and convex-hull L1 bound',
            'scope': 'two supplied directed interval images in a common Cartesian millimetre frame',
            'limitations': ['input representations and frame must independently be verified',
                            'no proof of BREP edge or face membership, topology, complete body coverage, surface distance or angle',
                            'no claim of agreement with a P3 symbolic curve unless supplied as reference',
                            'no kernel representation, model tolerance, or prior certificate error is included'],
            'execution_approved': False}
