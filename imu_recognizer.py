"""Single IMU classification pipeline: local start frame, acceleration + rotation.

The phone cannot sense direction *toward the user's torso* independently of
training and stable hand grip. The rotation gate is a heuristic, not a motion
tracking system; outputs must be calibrated on real gestures.
"""
from __future__ import annotations
import math
from engine import signature, dtw_distance, hook_direction_gate, cast_reversal
from phyphox_client import quaternion_inverse_unit, quaternion_multiply


def _normalize(q):
    n = math.sqrt(sum(x*x for x in q))
    if n < .5 or not math.isfinite(n):
        raise ValueError('Некорректный кватернион')
    return tuple(x/n for x in q)


def _rotation_vector(q):
    q = _normalize(q)
    if q[0] < 0:
        q = tuple(-v for v in q)
    sin_half = math.sqrt(sum(v*v for v in q[1:]))
    if sin_half < 1e-8:
        return [0., 0., 0.]
    theta = 2*math.atan2(sin_half, max(0., q[0]))
    return [theta*x/sin_half for x in q[1:]]


def _angle(q):
    return math.degrees(math.sqrt(sum(v*v for v in _rotation_vector(q))))


def rotation_signature(motion, attitudes, points=24):
    """Relative orientation trajectory (axis-angle), resampled in time.

    `attitudes` must supply a synchronized quaternion for every motion sample.
    The resulting vectors are expressed in the phone's START frame and thus
    invariant to a constant initial global orientation change.
    """
    if len(motion) < 2:
        raise ValueError('Мало точек для ориентации')
    quats = [_normalize(attitudes[t]) for t, *_ in motion]
    q_inv = quaternion_inverse_unit(quats[0])
    total = 0.
    records = []
    peak = 0.
    for i, (sample, q) in enumerate(zip(motion, quats)):
        rel = quaternion_multiply(q_inv, q)
        rv = _rotation_vector(rel)
        peak = max(peak, math.degrees(math.sqrt(sum(x*x for x in rv))))
        records.append((sample[0], *rv))
        if i:
            total += _angle(quaternion_multiply(quaternion_inverse_unit(quats[i-1]), q))
    # Resample without normalization: actual angular amplitude is discriminative.
    start, end = records[0][0], records[-1][0]
    if end <= start:
        raise ValueError('Неверная длительность')
    output = []
    j = 0
    for i in range(points):
        t = start + (end-start)*i/(points-1)
        while j+1 < len(records)-1 and records[j+1][0] < t:
            j += 1
        a,b = records[j:j+2]
        r = 0. if b[0] == a[0] else max(0.,min(1.,(t-a[0])/(b[0]-a[0])))
        output.append([a[k]*(1-r)+b[k]*r for k in (1,2,3)])
    return output, {'rotation_path_degrees': total, 'rotation_peak_degrees': peak}


def make_example(motion, attitudes):
    rot, stats = rotation_signature(motion, attitudes)
    try:
        acc = signature(motion)
    except ValueError as err:
        if 'No motion' not in str(err):
            raise
        # A rotation-only NEGATIVE example may have near-zero linear acceleration.
        acc = [[0.,0.,0.] for _ in range(24)]
    return {'acc': acc, 'rot': rot}, stats


def distance(a, b):
    return dtw_distance(a['acc'], b['acc']) + .33 * dtw_distance(a['rot'], b['rot'])


def score(query, templates):
    if not templates:
        return None
    best = sorted(distance(query, e) for e in templates)[:2]
    return sum(best)/len(best)


def separation(templates):
    casts, hooks = templates['CAST'], templates['HOOK']
    if not casts or not hooks:
        return None
    return min(distance(c,h) for c in casts for h in hooks)


def classify(query, templates, phase_ok, rotation_peak_degrees, *,
             cast_limit=.42, hook_limit=.42, negative_limit=.36,
             direction_cosine=.50, hook_rotation_limit=40., ambiguity=.045):
    """CAST / HOOK / UNKNOWN with independent thresholds and safety gates.

    Training of NEGATIVE is optional; when a negative example matches within its
    own threshold it vetoes sending any game command (conservative behaviour).
    """
    scores = {name: s for name in ('CAST','HOOK','NEGATIVE')
              if (s := score(query, templates[name])) is not None}
    if 'CAST' not in scores or 'HOOK' not in scores:
        return None, scores, 'Недостаточно обучающих примеров CAST и HOOK'
    if 'NEGATIVE' in scores and scores['NEGATIVE'] <= negative_limit:
        return None, scores, 'UNKNOWN: движение похоже на запрещённый пример'
    hook_ok, hook_why, stats = hook_direction_gate(query['acc'],
                                        [t['acc'] for t in templates['HOOK']], direction_cosine)
    gates = {
        'CAST': phase_ok,
        'HOOK': hook_ok and rotation_peak_degrees <= hook_rotation_limit,
    }
    limits = {'CAST': cast_limit, 'HOOK': hook_limit}
    viable = {name: scores[name] for name in ('CAST','HOOK')
              if scores[name] <= limits[name] and gates[name]}
    if not viable:
        reasons = []
        if not phase_ok:
            reasons.append('CAST: нет двухфазного замаха')
        elif scores['CAST'] > cast_limit:
            reasons.append('CAST: не похож на обучение')
        if rotation_peak_degrees > hook_rotation_limit:
            reasons.append(f'HOOK: вращение {rotation_peak_degrees:.0f}° > {hook_rotation_limit:.0f}°')
        elif not hook_ok:
            reasons.append('HOOK: '+hook_why)
        elif scores['HOOK'] > hook_limit:
            reasons.append('HOOK: не похож на обучение')
        return None, scores, 'UNKNOWN: ' + '; '.join(reasons)
    if len(viable) == 1:
        return next(iter(viable)), scores, 'OK'
    ranked = sorted(viable, key=lambda name: viable[name]/limits[name])
    if abs(viable[ranked[0]] - viable[ranked[1]]) < max(.018, ambiguity):
        return None, scores, 'UNKNOWN: обе модели подходят'
    return ranked[0], scores, 'OK'


def angular_rate_dps(previous, current, delta_t):
    """Compute gyro-like angular speed from two adjacent Attitude quaternions."""
    if delta_t <= 0 or delta_t > .3:
        return 0.
    delta = quaternion_multiply(quaternion_inverse_unit(_normalize(previous)), _normalize(current))
    return _angle(delta) / delta_t
