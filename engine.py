"""Motion Fishing 1.0 — IMU segmentation and directional gesture checks."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

Raw = tuple[float, float, float, float]
Vector = list[list[float]]


def magnitude(sample: Raw) -> float:
    return math.sqrt(sum(v * v for v in sample[1:]))


def signature(samples: list[Raw], points: int = 24) -> Vector:
    """Time-resample a segment and normalize its acceleration amplitudes."""
    if len(samples) < 2:
        raise ValueError('Need >= 2 sensor samples')
    values = sorted(samples, key=lambda s: s[0])
    start, end = values[0][0], values[-1][0]
    if end <= start:
        raise ValueError('Zero duration')
    peak = max(magnitude(s) for s in values)
    if peak < 1e-6:
        raise ValueError('No motion')
    result: Vector = []
    j = 0
    for i in range(points):
        target = start + (end - start) * i / (points - 1)
        while j + 1 < len(values) - 1 and values[j + 1][0] < target:
            j += 1
        left, right = values[j], values[j + 1]
        alpha = 0. if right[0] == left[0] else (target - left[0]) / (right[0] - left[0])
        alpha = max(0., min(1., alpha))
        result.append([(left[k] * (1 - alpha) + right[k] * alpha) / peak for k in (1, 2, 3)])
    return result


def _dot(x: list[float], y: list[float]) -> float:
    return sum(a * b for a, b in zip(x, y))


def dtw_distance(left: Vector, right: Vector, band: int = 6) -> float:
    """Constrained multivariate DTW; mean Euclidean distance per path step."""
    n, m = len(left), len(right)
    if not n or not m or len(left[0]) != len(right[0]):
        return float('inf')
    dp = [[float('inf')] * (m + 1) for _ in range(n + 1)]
    steps = [[0] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.
    for i in range(1, n + 1):
        for j in range(max(1, i - band), min(m, i + band) + 1):
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(left[i-1], right[j-1])))
            options = [(dp[i-1][j], steps[i-1][j]),
                       (dp[i][j-1], steps[i][j-1]),
                       (dp[i-1][j-1], steps[i-1][j-1])]
            prev, count = min(options, key=lambda v: v[0])
            dp[i][j] = prev + dist
            steps[i][j] = count + 1
    return dp[n][m] / max(steps[n][m], 1)


def initial_impulse_axis(values: Vector) -> tuple[float, float, float] | None:
    """Signed direction of the FIRST energetic acceleration lobe.

    A single stroke produces two opposite accelerations (start/braking).
    Using the entire gesture or its strongest peak loses the intended travel
    direction. Instead use the earliest sustained lobe and stop when the signal
    reverses. The axis is expressed in gesture-start phone coordinates for
    relative mode, not Earth or absolute body coordinates.

    Returns None if the beginning is not sufficiently clear.
    """
    if len(values) < 8:
        return None
    mags = [math.sqrt(_dot(v, v)) for v in values]
    peak = max(mags)
    if peak < .12:
        return None
    threshold = max(.16, peak * .35)
    # Allow pre-roll quiet samples, but refuse late start: a missing acceleration
    # phase must not turn a braking lobe into a confident hook direction.
    start = next((i for i in range(min(len(values) * 2 // 3, len(values)))
                  if mags[i] >= threshold), None)
    if start is None:
        return None
    seed = values[start]
    axis = [0., 0., 0.]
    sample_count = 0
    for i in range(start, min(len(values), start + max(4, len(values) // 3))):
        v = values[i]
        if i > start and _dot(v, seed) < -.12 * mags[i] * mags[start]:
            break  # The braking half of the movement began.
        if mags[i] < threshold * .48:
            if sample_count >= 2:
                break
            continue
        for k in range(3):
            axis[k] += v[k]
        sample_count += 1
    norm = math.sqrt(sum(x*x for x in axis))
    if sample_count < 1 or norm < .15:
        return None
    return tuple(x/norm for x in axis)


def hook_direction_gate(query: Vector, hook_templates: list[Vector],
                        min_cosine: float = .50) -> tuple[bool, str, dict[str, float]]:
    """Reject a HOOK that starts in the wrong signed direction.

    Compare the first accelerating lobe against the trained hook examples.
    The angles are relative to the phone's axes at the start of each gesture.
    No sensor on the phone can identify 'towards your torso' from an arbitrary
    grip without calibration; the training examples provide that reference.
    """
    if not hook_templates:
        return False, 'нет обучающих примеров HOOK', {}
    axes = [initial_impulse_axis(t) for t in hook_templates]
    if any(v is None for v in axes):
        return False, 'нечёткие старые примеры HOOK — переобучи подсечку', {}
    # Do not silently use an inconsistent mix of towards/away hook examples.
    min_pair = min((_dot(a, b) for i, a in enumerate(axes) for b in axes[i+1:]),
                   default=1.)
    if min_pair < .05:
        return False, 'образцы HOOK противоречат по направлению — очисти и переобучи только рывок к себе', {'example_coherence': min_pair}
    current = initial_impulse_axis(query)
    if current is None:
        return False, 'не удалось определить начало рывка', {'example_coherence': min_pair}
    reference = [sum(a[k] for a in axes) for k in range(3)]
    normal = math.sqrt(sum(x*x for x in reference))
    if normal < .3:
        return False, 'нет единого направления в обучении HOOK', {'example_coherence': min_pair}
    reference = [x / normal for x in reference]
    cosine = max(-1., min(1., _dot(current, reference)))
    angle_deg = math.degrees(math.acos(cosine))
    stats = {'direction_cosine': cosine, 'direction_angle_degrees': angle_deg,
             'example_coherence': min_pair}
    if cosine < min_cosine:
        return False, f'неверное направление рывка: угол {angle_deg:.0f}° (порог {math.degrees(math.acos(min_cosine)):.0f}°)', stats
    return True, f'направление HOOK совпадает: угол {angle_deg:.0f}°', stats


def cast_reversal(samples: list[Raw], min_speed: float = .16) -> tuple[bool, str, dict[str, float]]:
    """Require *motion direction* reversal, not just acceleration reversal.

    Projection onto the motion's principal acceleration axis makes the check
    independent of device orientation. Short-window integration estimates
    velocity; offset-correction assumes the user starts/finishes approximately
    at rest. A one-way stroke with ordinary braking is not a cast.

    This is an IMU heuristic, not ground-truth position/velocity estimation.
    """
    if len(samples) < 9:
        return False, 'слишком мало данных для двух фаз', {}
    values = sorted(samples, key=lambda row: row[0])
    duration = values[-1][0] - values[0][0]
    if duration < .26:
        return False, 'движение короче 0.26 с', {'duration': duration}
    if duration > 2.4:
        return False, 'слишком длинное движение', {'duration': duration}

    dt = [values[i+1][0] - values[i][0] for i in range(len(values)-1)]
    if min(dt) <= 0 or max(dt) > .18:
        return False, 'пропущены измерения во время движения', {'max_gap': max(dt)}

    xyz = [row[1:] for row in values]
    # Time-weighted average accelerometer bias; a gesture should start/end
    # approximately at rest. Subtraction prevents constant offsets drifting v.
    area = [0., 0., 0.]
    for i, delta in enumerate(dt):
        for k in range(3):
            area[k] += (xyz[i][k] + xyz[i+1][k]) * .5 * delta
    mean = [v / duration for v in area]
    centered = [[point[k] - mean[k] for k in range(3)] for point in xyz]
    # Principal direction of acceleration. No numpy required.
    covariance = [[sum(p[i]*p[j] for p in centered) for j in range(3)] for i in range(3)]
    k = max(range(3), key=lambda i: covariance[i][i])
    axis = [1. if i == k else 0. for i in range(3)]
    for _ in range(16):
        v = [sum(covariance[i][j]*axis[j] for j in range(3)) for i in range(3)]
        norm = math.sqrt(sum(z*z for z in v))
        if norm < 1e-7:
            return False, 'нет выраженной оси движения', {}
        axis = [z/norm for z in v]

    projected = [sum(v[k]*axis[k] for k in range(3)) for v in centered]
    velocity = [0.]
    for i, delta in enumerate(dt):
        velocity.append(velocity[-1] + (projected[i] + projected[i+1]) * .5 * delta)

    peak_forward = max(0., max(velocity))
    peak_backward = max(0., -min(velocity))
    stats = {'forward_speed': peak_forward, 'backward_speed': peak_backward,
             'duration': duration}
    if min(peak_forward, peak_backward) < min_speed:
        return False, ('нет отчётливого возвратного движения: '
                       f'{min(peak_forward, peak_backward):.2f} < {min_speed:.2f} м/с'), stats
    if min(peak_forward, peak_backward) / max(peak_forward, peak_backward) < .22:
        return False, 'одна фаза значительно слабее другой', stats

    # A genuine reversal must persist; a split-second endpoint oscillation
    # should not count. Each direction needs at least 60 ms of signed speed.
    substantial = max(.08, min_speed * .55)
    positive_time = sum(dt[i] for i in range(len(dt)) if velocity[i] >= substantial)
    negative_time = sum(dt[i] for i in range(len(dt)) if velocity[i] <= -substantial)
    stats.update({'positive_time': positive_time, 'negative_time': negative_time})
    if min(positive_time, negative_time) < .06:
        return False, 'не хватает длительности одной из фаз', stats
    return True, 'обратный и прямой ход подтверждены', stats


@dataclass
class MotionSegmenter:
    threshold: float = 2.4
    end_ratio: float = .4
    quiet_seconds: float = .20
    max_seconds: float = 1.5
    pre_seconds: float = .12
    pre: deque = field(default_factory=lambda: deque(maxlen=40))
    active: list[Raw] = field(default_factory=list)
    last_loud: float | None = None
    last_time: float | None = None

    def reset(self) -> None:
        self.pre.clear()
        self.active.clear()
        self.last_loud = None
        self.last_time = None

    def feed(self, sample: Raw, rotation_rate_dps: float = 0.,
             rotation_threshold_dps: float = 130.) -> list[Raw] | None:
        t = sample[0]
        if self.last_time is not None and (t <= self.last_time or t - self.last_time > .6):
            self.reset()
        self.last_time = t
        mag = magnitude(sample)
        rotation_triggered = rotation_rate_dps >= rotation_threshold_dps
        self.pre.append(sample)
        while self.pre and t - self.pre[0][0] > self.pre_seconds:
            self.pre.popleft()
        if not self.active:
            if mag >= self.threshold or rotation_triggered:
                self.active = list(self.pre)
                self.last_loud = t
            return None
        self.active.append(sample)
        if mag >= self.threshold * self.end_ratio or rotation_rate_dps >= rotation_threshold_dps * .42:
            self.last_loud = t
        expired = t - self.active[0][0] >= self.max_seconds
        settled = self.last_loud is not None and t - self.last_loud >= self.quiet_seconds
        if not (expired or settled):
            return None
        result = self.active
        self.active = []
        self.last_loud = None
        if len(result) < 5 or result[-1][0] - result[0][0] < .10:
            return None
        return result


@dataclass
class FishingSession:
    line_out: bool = False
    last_action: float = float('-inf')
    last_cast: float = float('-inf')
    cooldown: float = .85
    hook_guard: float = 1.5

    def reset(self) -> None:
        self.line_out = False
        self.last_action = float('-inf')
        self.last_cast = float('-inf')

    @property
    def expected(self) -> str:
        return 'HOOK' if self.line_out else 'CAST'

    def validate(self, label: str, now: float) -> tuple[bool, str]:
        if label != self.expected:
            return False, 'ожидается ' + self.expected
        if now - self.last_action < self.cooldown:
            return False, 'пауза после предыдущего жеста'
        if label == 'HOOK' and now - self.last_cast < self.hook_guard:
            return False, 'слишком рано после заброса'
        return True, 'OK'

    def consume(self, label: str, now: float) -> tuple[bool, str]:
        ok, why = self.validate(label, now)
        if not ok:
            return False, why
        self.last_action = now
        if label == 'CAST':
            self.last_cast = now
            self.line_out = True
        else:
            self.line_out = False
        return True, 'OK'
