"""Fixed-stock interval certificates for the ideal P3 tail CSG.

The P3-TAIL-REGION-04 chart is taken at its stated exact decimal values:
R0=6.9, R1=7.9, R3=9, y0=-158.6, y1=-157.6, y2=-151.1,
y3=y2+1.1/sqrt(3), cutter radius=37.5 and axis (y,z)=(-162.6,42).
The stock is fixed. This proof is for the ideal chart, not
the floating-point/native model, source equivalence, or an arbitrary coupled
edit. See region-correspondence.md and P3-REAR-SLOT-01/region-construction.json.
"""

from fractions import Fraction as Q
from math import isfinite, isqrt


def _number(value):
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError('bounds must be finite real numbers')
    return Q(value)


def _sqrt(q):
    """Strict, outward rational bounds, including when q is a square."""
    if q < 0:
        raise ValueError('negative square-root argument')
    scale = 10**15
    n = isqrt(q.numerator * scale * scale // q.denominator)
    return Q(n, scale), Q(n + 1, scale)


def assess_tail_width_interval(lower_mm, upper_mm):
    """Certify each real width in [lower_mm, upper_mm] for the ideal tail.

    The sufficient accepted window is [4.9, 5.1] mm, not a maximum range.
    Inputs are interpreted exactly as their int/binary64 values. Outputs for
    exit stations are exact rational enclosure strings in mm, not estimates of
    manufacturing clearances. A passing result is conditional on the fixed P3
    stock chart and its established post-exit exclusion.
    """
    lo, hi = _number(lower_mm), _number(upper_mm)
    if not 0 < lo <= hi:
        raise ValueError('width interval must be positive and ordered')
    if lo < Q('4.9') or hi > Q('5.1'):
        return {'status': 'not_proved', 'reason': 'outside sufficient window [4.9, 5.1] mm',
                'execution_approved': False}

    result = _bound_tail(lo, hi, (Q('37.5'),)*2, (Q('-162.6'),)*2, (Q(42),)*2)
    return {
        **result,
        'schema': 'p4-ideal-tail-width-interval/1',
        'width_interval_mm': [lower_mm, upper_mm],
        'sufficient_window_mm': ['4.9', '5.1'],
        'fixed_inputs': 'P3 ideal decimal tail stock and all other slot inputs fixed',
    }


def assess_tail_parameter_box():
    """Certify a sufficient simultaneous interval for all four tail drivers."""
    windows = {'slot.width': ('4.9', '5.1'), 'slot.radius': ('37.49', '37.51'),
               'slot.axis_y': ('-162.61', '-162.59'), 'slot.axis_z': ('41.99', '42.01')}
    width, radius, axis_y, axis_z = (
        (min(Q(lo), Q(float(lo))), max(Q(hi), Q(float(hi)))) for lo, hi in windows.values())
    return {**_bound_tail(*width, radius, axis_y, axis_z),
            'schema': 'p4-ideal-tail-parameter-box/1', 'windows_exact_mm': windows}


def _bound_tail(lo, hi, radius, axis_y, axis_z):
    radius_lo, radius_hi = radius
    ay_lo, ay_hi = axis_y
    az_lo, az_hi = axis_z

    def f(y):
        lower, _ = _sqrt(radius_lo**2 - (y-ay_lo)**2)
        _, upper = _sqrt(radius_hi**2 - (y-ay_hi)**2)
        return az_lo-upper, az_hi-lower

    def root_for_height(zlo, zhi):
        # The positive radial branch h(z)=ay+sqrt(radius²-(az-z)²)
        # increases with ay, radius and z, and decreases with az.
        lower, _ = _sqrt(radius_lo**2 - (az_hi-zlo)**2)
        _, upper = _sqrt(radius_hi**2 - (az_lo-zhi)**2)
        return ay_lo+lower, ay_hi+upper

    a_lo, a_hi = lo/2, hi/2
    y0, y2 = Q('-158.6'), Q('-151.1')
    f0lo, f0hi = f(y0)
    _, f2hi = f(y2)
    _, f_after_cone_hi = f(Q('-150.4'))
    z0lo, _ = _sqrt(Q('6.9')**2 - a_hi**2)
    z9lo, _ = _sqrt(Q(9)**2 - a_hi**2)
    _, z9hi = _sqrt(Q(9)**2 - a_lo**2)
    side_lo, side_hi = root_for_height(z9lo, z9hi)
    center_lo, center_hi = root_for_height(Q(9), Q(9))

    # For y0..y3, f>0 and f'<1: the worst derivative is at -150.4;
    # check by squaring since (y-axis_y)>0. Both cone R' are >=1.
    dy = Q('-150.4') - ay_lo
    derivative_lt_one = 2*dy**2 < radius_lo**2
    # At each checkpoint, the minimum possible f exceeds the stock bound.
    # Past the last checkpoint the increasing cylinder branch remains clear
    # until the latest possible end of the tool, within the s5 arc chart.
    def f_exceeds(y, height):
        return ((az_lo-height)**2 > radius_hi**2-(y-ay_hi)**2 and az_lo > height)

    checks = {
        'positive_lower_branch_and_end_notch': 0 < f0lo and f0hi < z0lo,
        'side_clears_first_cylinder_at_y2': f2hi**2 + a_hi**2 < Q('7.9')**2,
        'early_cones_monotone': derivative_lt_one,
        'r9_exit_after_cone': f_after_cone_hi < z9lo and side_lo > Q('-150.4'),
        'positive_side_exit_before_center': side_hi < center_lo,
        'center_exit_on_r9': center_hi < Q('-144') and Q('-144') < Q('-125.273479089'),
        'positive_axial_branch': ay_hi < y0,
        'unaffected_core_and_upper_branch': az_lo-radius_hi > 4 and az_lo > 11,
        'no_reentry_after_r9_exit': (f_exceeds(Q(-144), Q(9)) and f_exceeds(Q(-126), Q(11))
                                    and ay_hi+radius_hi < Q('-123.273479089')),
    }
    # y3=-151.1+1.1/sqrt(3) is less than -150.4: (1.1/0.7)^2<3.
    checks['cone_end_before_r9_checkpoint'] = (Q('1.1')/Q('0.7'))**2 < 3
    status = 'proved' if all(checks.values()) else 'not_proved'
    return {
        'status': status,
        'checks': checks,
        'side_exit_y_mm_rational_enclosure': [str(side_lo), str(side_hi)],
        'center_exit_y_mm_rational_enclosure': [str(center_lo), str(center_hi)],
        'proof': 'Rational arithmetic and outward sqrt bounds; f is increasing; '
                 'f< R on the cones and f\' < R\' imply f²+a²-R² decreases there. '
                 'On cylinders the same expression increases. Junction checks '
                 'therefore keep both side exits on R9, followed by the center exit. '
                 'Fixed-stock exclusion checkpoints rule out re-entry after the center exit.',
        'scope': 'ideal finite tail cut and its side/center branch ordering only',
        'open_obligations': [
            'edited source/native finite-region correspondence and binary64/solver tolerance',
            'whole-body stock, other feature intersections and global error budget',
            'coupled C5 edits require independent section, sweep and stock guards',
        ],
        'execution_approved': False,
    }
