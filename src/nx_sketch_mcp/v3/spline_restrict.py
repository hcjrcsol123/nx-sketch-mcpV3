"""Exact knot-insertion restriction of a supplied non-rational B-spline.

This is a mathematical operation on the supplied expression, not a native
surface trim, kernel accuracy claim, or editable engineering parameterization.
Input numbers denote their exact IEEE-754 binary64 values. Internal full-order
knots are rejected because their two sides can have different endpoint values.
"""
from bisect import bisect_right
from fractions import Fraction
import math


def _binary64(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name}: expected a finite binary64 number')
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f'{name}: expected a finite binary64 number') from exc
    if not math.isfinite(result) or (isinstance(value, int) and result != value):
        raise ValueError(f'{name}: expected an exactly representable finite binary64 number')
    return result


def _fraction(value):
    return Fraction.from_float(value)


def _pair(value):
    return [value.numerator, value.denominator]


def _upward(value):
    """Smallest available binary64 >= nonnegative exact rational, or infinity."""
    if value < 0:
        raise ValueError('bound must be nonnegative')
    try:
        result = float(value)
    except OverflowError:
        return math.inf
    if math.isinf(result):
        return result
    if Fraction.from_float(result) < value:
        result = math.nextafter(result, math.inf)
    return result


def _insert(knots, rows, order, value):
    """Insert value once in exact arithmetic, preserving the affine map."""
    degree = order - 1
    span = bisect_right(knots, value) - 1
    multiplicity = knots.count(value)
    new = []
    for i in range(len(rows) + 1):
        if i <= span - degree:
            new.append(rows[i][:])
        elif i >= span - multiplicity + 1:
            new.append(rows[i-1][:])
        else:
            denominator = knots[i+degree] - knots[i]
            if denominator <= 0:
                raise ValueError('invalid knot interval for insertion')
            alpha = (value - knots[i]) / denominator
            if not 0 <= alpha <= 1:
                raise ValueError('invalid knot insertion coefficient')
            new.append([(1-alpha)*left + alpha*right for left, right in zip(rows[i-1], rows[i])])
    return knots[:span+1] + [value] + knots[span+1:], new


def restrict_bspline(*, order, knots, poles, a, b, rational, weights=None):
    """Clamp a supplied binary64 non-rational B-spline to the explicit [a,b].

    Returns original data, clamped knots and rounded poles, exact dependency
    rows as [numerator, denominator] pairs, exact source influence bounds and
    an upward-rounded L1 position error bound. A zero dependency column alone
    is inactive. Source and result share the same parameter and coordinate
    units; the bound excludes all errors outside this expression.
    """
    if rational is not False or weights is not None:
        raise ValueError('only non-rational splines without weights are supported')
    if type(order) is not int or order < 2:
        raise ValueError('order must be an integer >= 2')
    if not isinstance(poles, (list, tuple)) or len(poles) < order:
        raise ValueError('pole count must be at least the order')
    source_poles = []
    dimension = None
    for row in poles:
        if not isinstance(row, (list, tuple)) or not row:
            raise ValueError('poles must be nonempty equal-length coordinate vectors')
        if dimension is None:
            dimension = len(row)
        if len(row) != dimension:
            raise ValueError('pole dimensions differ')
        source_poles.append([_binary64(x, 'pole') for x in row])
    if not isinstance(knots, (list, tuple)) or len(knots) != len(source_poles) + order:
        raise ValueError('knot count must equal pole count plus order')
    source_knots = [_binary64(x, 'knot') for x in knots]
    if any(x > y for x, y in zip(source_knots, source_knots[1:])):
        raise ValueError('knots must be nondecreasing')
    lower, upper = source_knots[order-1], source_knots[len(source_poles)]
    a, b = _binary64(a, 'a'), _binary64(b, 'b')
    if not lower <= a < b <= upper:
        raise ValueError('require a < b within the active spline domain')
    run = 0
    previous = None
    for value in source_knots:
        run = run + 1 if value == previous else 1
        if run > order or (lower < value < upper and run >= order):
            raise ValueError('invalid or discontinuous full-order interior knot')
        previous = value
    exact_knots = [_fraction(x) for x in source_knots]
    exact_a, exact_b = _fraction(a), _fraction(b)
    n = len(source_poles)
    rows = [[Fraction(int(i == j)) for j in range(n)] for i in range(n)]
    for value in (exact_a, exact_b):
        while exact_knots.count(value) < order:
            exact_knots, rows = _insert(exact_knots, rows, order, value)
    first = exact_knots.index(exact_a)
    end = bisect_right(exact_knots, exact_b)
    result_knots = exact_knots[first:end]
    result_count = len(result_knots) - order
    rows = rows[first:first+result_count]
    if result_count < order or len(rows) != result_count:
        raise ValueError('restriction could not form a valid clamped spline')
    source_exact = [[_fraction(x) for x in row] for row in source_poles]
    exact_poles = [[sum((coefficient * source_exact[j][d] for j, coefficient in enumerate(row)), Fraction())
                    for d in range(dimension)] for row in rows]
    try:
        result_poles = [[float(x) for x in row] for row in exact_poles]
    except OverflowError as exc:
        raise ValueError('derived pole cannot be represented as binary64') from exc
    if any(not math.isfinite(x) for row in result_poles for x in row):
        raise ValueError('derived pole cannot be represented as finite binary64')
    errors = [sum((abs(exact - _fraction(rounded)) for exact, rounded in zip(ex, rd)), Fraction())
              for ex, rd in zip(exact_poles, result_poles)]
    bound = max(errors, default=Fraction())
    coordinate_bounds = [max((abs(ex[d] - _fraction(rd[d])) for ex, rd in zip(exact_poles, result_poles)),
                             default=Fraction()) for d in range(dimension)]
    influence = [max((abs(row[j]) for row in rows), default=Fraction()) for j in range(n)]
    return {'source': {'order': order, 'knots': source_knots, 'poles': source_poles, 'rational': False},
            'interval': [a, b], 'order': order, 'knots': [float(x) for x in result_knots], 'poles': result_poles,
            'dependency_rows_exact': [[_pair(x) for x in row] for row in rows],
            'source_influence': [{'index': i, 'inactive': value == 0, 'nonzero': value != 0,
                                  'support_interval_hull': ([max(a, source_knots[i]),
                                                             min(b, source_knots[i+order])] if value else None),
                                  'upper_exact': _pair(value), 'upper': _upward(value)}
                                 for i, value in enumerate(influence)],
            'rounding_error_l1_upper_exact': _pair(bound), 'rounding_error_l1_upper': _upward(bound),
            'coordinate_error_upper_exact': [_pair(x) for x in coordinate_bounds],
            'coordinate_error_upper': [_upward(x) for x in coordinate_bounds],
            'influence_scope': 'supremum bound for each original basis on the supplied closed interval, including endpoints; support interval is a closed hull, not a claim that its endpoints are nonzero',
            'numeric_semantics': 'inputs interpreted as exact binary64; knot insertion and dependencies exact; output knots unchanged binary64 values; output poles rounded once to binary64',
            'bound_scope': 'only supplied non-rational B-spline expression on the explicit interval; excludes native approximation, frame, kernel and later edit errors',
            'derived_poles_are_independent': False}
