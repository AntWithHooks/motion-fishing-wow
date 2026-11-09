import json
import math
import unittest
from unittest.mock import patch
from phyphox_client import Phyphox, rotate_vector, quaternion_multiply, relative_motion


class FakePhyphox(Phyphox):
    def __init__(self):
        super().__init__('http://127.0.0.1')
        self.payloads = []
    def get(self, path):
        return self.payloads.pop(0)


def message(a, q, session='a'):
    names = ('acc_time', 'accX', 'accY', 'accZ', 't', 'w', 'x', 'y', 'z')
    cols = [list(x) for x in zip(*a)] + [list(x) for x in zip(*q)] if a and q else [[]] * 9
    data = {}
    for n, values in zip(names, cols):
        data[n] = {'buffer': values}
    return {'buffer': data, 'status': {'session': session, 'measuring': True}}


class PhyphoxTests(unittest.TestCase):
    def test_identity_rotation(self):
        self.assertEqual(rotate_vector((1., 0., 0., 0.), (1., 2., 3.)), (1., 2., 3.))

    def test_rotation_invariance_in_world_coordinates(self):
        angle = math.pi / 2
        q = (math.cos(angle/2), 0, 0, math.sin(angle/2))
        # Same physical acceleration observed after the phone rotates 90 deg.
        first = rotate_vector((1, 0, 0, 0), (0, 1, 0))
        second = rotate_vector(q, (1, 0, 0))
        self.assertAlmostEqual(first[0], second[0], places=6)
        self.assertAlmostEqual(first[1], second[1], places=6)

    def test_quarter_turn(self):
        x, y, z = rotate_vector((math.sqrt(.5), 0, 0, math.sqrt(.5)), (1., 0., 0.))
        self.assertAlmostEqual(x, 0, places=6)
        self.assertAlmostEqual(y, 1, places=6)
        self.assertAlmostEqual(z, 0, places=6)

    def test_relative_motion_ignores_global_rotation(self):
        # Same hand movement with a globally rotated initial body posture.
        def qz(angle):
            return (math.cos(angle/2), 0., 0., math.sin(angle/2))
        xs = [(i/20, 4.*math.sin(i*.2), 2.*math.cos(i*.3), 0.) for i in range(20)]
        delta = [qz(.4 * i / 19) for i in range(20)]
        attitudes_a = {sample[0]: q for sample, q in zip(xs, delta)}
        angles_b = {sample[0]: quaternion_multiply(qz(1.8), q) for sample, q in zip(xs, delta)}
        a = relative_motion(xs, attitudes_a)
        b = relative_motion(xs, angles_b)
        for left, right in zip(a,b):
            for lv, rv in zip(left,right):
                self.assertAlmostEqual(lv, rv, places=8)

    def test_relative_motion_preserves_direction_during_rotation(self):
        q0 = (1., 0., 0., 0.)
        q90 = (math.sqrt(.5), 0., 0., math.sqrt(.5))
        move = [(0., 1., 0., 0.), (0.1, 1., 0., 0.)]
        result = relative_motion(move, {0.: q0, 0.1: q90})
        self.assertAlmostEqual(result[0][1], 1., places=6)
        self.assertAlmostEqual(result[1][1], 0., places=6)
        self.assertAlmostEqual(result[1][2], 1., places=6)

    def test_relative_motion_missing_quaternion_rejects(self):
        with self.assertRaises(ValueError):
            relative_motion([(0., 1., 0., 0.)], {})

    def test_fetch_combined(self):
        api = FakePhyphox()
        api.payloads = [message([(0.5, 1., 2., 3.)], [(0.5, 1., 0., 0., 0.)])]
        result, measuring, changed = api.samples()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], (0.5, 1., 2., 3.))
        self.assertEqual(result[0][2], (1., 0., 0., 0.))
        self.assertTrue(measuring)
        self.assertFalse(changed)

    def test_missing_attitude_is_not_faked(self):
        api = FakePhyphox()
        api.payloads = [message([(0.5, 1., 2., 3.)], [(0.9, 1., 0., 0., 0.)])]
        result, _, _ = api.samples()
        self.assertEqual(result, [])

    def test_session_reset(self):
        api = FakePhyphox()
        api.payloads = [message([(0.5, 1., 2., 3.)], [(0.5, 1., 0., 0., 0.)], 'one'),
                        message([(0.01, 1., 2., 3.)], [(0.01, 1., 0., 0., 0.)], 'two')]
        api.samples()
        result, _, changed = api.samples()
        self.assertTrue(changed)
        self.assertEqual(result, [])
        self.assertIsNone(api.last_acc_t)

    def test_config_rejects_old_experiment(self):
        api = FakePhyphox()
        api.payloads = [{'buffers': [{'name': n} for n in ('acc_time','accX','accY','accZ')]}]
        with self.assertRaises(RuntimeError):
            api.check()

if __name__ == '__main__':
    unittest.main()
