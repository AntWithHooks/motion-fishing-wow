"""phyphox Acceleration and Attitude experiment: synchronized acceleration/orientation.

The transport uses phyphox's HTTP API over a local Wi-Fi network.
Position and magnetic heading are NOT inferred; only linear acceleration is
rotated into phyphox's Earth-reference frame using the reported quaternion.
"""
from __future__ import annotations

import json
import math
from collections import deque
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen

ACC = ('acc_time', 'accX', 'accY', 'accZ')
ATT = ('t', 'w', 'x', 'y', 'z')
BUFFERS = ACC + ATT


def normalize_url(value: str) -> str:
    value = value.strip().rstrip('/')
    if not value:
        raise ValueError('Введите адрес phyphox')
    if '://' not in value:
        value = 'http://' + value
    parsed = urlsplit(value)
    if parsed.scheme != 'http' or not parsed.hostname or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise ValueError('Нужен корневой адрес HTTP, например http://172.20.10.1')
    return value


def rotate_vector(q: tuple[float, float, float, float], v: tuple[float, float, float]) -> tuple[float, float, float]:
    """Apply the unit quaternion's rotation to a phone-frame acceleration vector."""
    w, x, y, z = q
    norm = math.sqrt(w*w + x*x + y*y + z*z)
    if norm < .5 or not math.isfinite(norm):
        raise ValueError('Неверный кватернион')
    w, x, y, z = w / norm, x / norm, y / norm, z / norm
    vx, vy, vz = v
    # v' = v + 2*w*(q_xyz cross v) + 2*(q_xyz cross (q_xyz cross v))
    tx = 2 * (y*vz - z*vy)
    ty = 2 * (z*vx - x*vz)
    tz = 2 * (x*vy - y*vx)
    return (vx + w*tx + y*tz - z*ty,
            vy + w*ty + z*tx - x*tz,
            vz + w*tz + x*ty - y*tx)


def quaternion_multiply(a: tuple[float, float, float, float],
                        b: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """Hamilton quaternion product. q(t) maps phone vectors to Earth frame."""
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw*bw - ax*bx - ay*by - az*bz,
            aw*bx + ax*bw + ay*bz - az*by,
            aw*by - ax*bz + ay*bw + az*bx,
            aw*bz + ax*by - ay*bx + az*bw)


def quaternion_inverse_unit(q: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    norm_sq = sum(x*x for x in q)
    if norm_sq < .25 or not math.isfinite(norm_sq):
        raise ValueError('Неверная ориентация')
    return (q[0]/norm_sq, -q[1]/norm_sq, -q[2]/norm_sq, -q[3]/norm_sq)


def relative_motion(
    movement: list[tuple[float, float, float, float]],
    attitudes: dict[float, tuple[float, float, float, float]],
) -> list[tuple[float, float, float, float]]:
    """Express each acceleration in gesture-start phone coordinates.

    q_rel(t)=inverse(q_start)*q(t). The Earth's absolute yaw/pitch/roll
    disappears. A changed grip relative to the player's hand is NOT solved.
    """
    if not movement:
        return []
    quats = [attitudes.get(sample[0]) for sample in movement]
    if any(q is None for q in quats):
        raise ValueError('Нет синхронизированных данных ориентации')
    q_start_inv = quaternion_inverse_unit(quats[0])
    result = []
    for sample, q in zip(movement, quats):
        q_rel = quaternion_multiply(q_start_inv, q)
        vec = rotate_vector(q_rel, sample[1:])
        result.append((sample[0], *vec))
    return result


class Phyphox:
    def __init__(self, url: str, timeout: float = 2.0):
        self.url = normalize_url(url)
        self.timeout = timeout
        self.last_acc_t: float | None = None
        self.last_att_t: float | None = None
        self.session: str | None = None
        self.orientations: deque[tuple[float, tuple[float, float, float, float]]] = deque(maxlen=450)
        self.pending: deque[tuple[float, float, float, float]] = deque(maxlen=300)

    def get(self, endpoint: str) -> dict:
        with urlopen(self.url + endpoint, timeout=self.timeout) as stream:
            return json.load(stream)

    def check(self) -> str:
        cfg = self.get('/config')
        names = {b.get('name') for b in cfg.get('buffers', [])}
        missing = set(BUFFERS) - names
        if missing:
            raise RuntimeError('Откройте в phyphox импортированный эксперимент «Acceleration and Attitude» '
                               '(НЕ «Ускорение без g»). Не найдены: ' + ', '.join(sorted(missing)))
        return cfg.get('localTitle') or cfg.get('title') or 'Acceleration and Attitude'

    @staticmethod
    def _unpack(data: dict, names: tuple[str, ...]) -> list[tuple[float, ...]]:
        arrays = [data.get(k, {}).get('buffer', []) for k in names]
        if len({len(a) for a in arrays}) != 1:
            raise ValueError('Разная длина буферов ' + ', '.join(names))
        output = []
        for values in zip(*arrays):
            try:
                row = tuple(float(v) for v in values)
            except (TypeError, ValueError):
                continue
            if all(math.isfinite(x) for x in row):
                output.append(row)
        return output

    def _reset(self):
        self.last_acc_t = None
        self.last_att_t = None
        self.orientations.clear()
        self.pending.clear()

    def _query(self) -> str:
        # On first request read only last sensor samples, not a huge recording.
        params: dict[str, str] = {}
        for names, last in ((ACC, self.last_acc_t), (ATT, self.last_att_t)):
            if last is None:
                params.update({name: '' for name in names})
            else:
                ref = names[0]
                params[ref] = repr(last)
                params.update({name: repr(last) + '|' + ref for name in names[1:]})
        return '/get?' + urlencode(params)

    def _nearest_attitude(self, t: float):
        if not self.orientations:
            return None
        # Nearest-sample matching. Gyro/acc sensors may have different cadence.
        nearest = min(self.orientations, key=lambda item: abs(item[0] - t))
        return nearest[1] if abs(nearest[0] - t) <= .10 else None

    def samples(self) -> tuple[list[tuple[tuple[float, ...], tuple[float, ...]]], bool, bool]:
        """Return [(phone-frame, Earth-frame, attitude quaternion)], measuring, session_changed."""
        payload = self.get(self._query())
        status = payload.get('status', {})
        new_session = status.get('session')
        changed = self.session is not None and new_session != self.session
        self.session = new_session
        if changed:
            self._reset()
            return [], bool(status.get('measuring')), True
        data = payload.get('buffer', {})
        for record in self._unpack(data, ATT):
            t, w, x, y, z = record
            if self.last_att_t is None or t > self.last_att_t:
                self.last_att_t = t
                self.orientations.append((t, (w, x, y, z)))
        for record in self._unpack(data, ACC):
            if self.last_acc_t is None or record[0] > self.last_acc_t:
                self.last_acc_t = record[0]
                self.pending.append(record)
        result = []
        # Wait briefly if orientation sensor lags, but never reuse a stale attitude.
        newest_att = self.orientations[-1][0] if self.orientations else float('-inf')
        while self.pending:
            a = self.pending[0]
            q = self._nearest_attitude(a[0])
            if q is None:
                if a[0] > newest_att and a[0] - newest_att <= .20:
                    break  # Next poll may supply the attitude sample.
                self.pending.popleft()  # No time-aligned orientation -> skip.
                continue
            self.pending.popleft()
            try:
                world_xyz = rotate_vector(q, (a[1], a[2], a[3]))
            except ValueError:
                continue
            result.append((a, (a[0], *world_xyz), q))
        if self.last_acc_t is not None:
            while self.orientations and self.orientations[0][0] < self.last_acc_t - 2:
                self.orientations.popleft()
        return result, bool(status.get('measuring')), False
