"""Synthetic IMU regression tests (not a substitute for iPhone validation)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from engine import MotionSegmenter, cast_reversal, hook_direction_gate, FishingSession
from imu_recognizer import (make_example, classify, angular_rate_dps,
                            rotation_signature, separation)
from settings_store import load, save


def bell(t, center, width, velocity):
    v = velocity * math.exp(-0.5*((t-center)/width)**2)
    return -(t-center)/width**2*v


def motion(cast=False, sign=1):
    output = []
    for i in range(120):
        t = i*.012
        if cast:
            a = bell(t, .28,.10,-.85)+bell(t,.81,.10,1.0)
        else:
            a = bell(t,.58,.12,1.0)*sign
        output.append((t,a,0.,0.))
    return output


def quat_x(rad):
    return (math.cos(rad/2), math.sin(rad/2), 0., 0.)


def attitudes(m, final_degrees=0., left_yaw=0.):
    # Global initial orientation is irrelevant when the device grip is constant.
    from phyphox_client import quaternion_multiply
    initial = (math.cos(left_yaw/2),0,0,math.sin(left_yaw/2))
    return {t: quaternion_multiply(initial,quat_x(math.radians(final_degrees)*i/(len(m)-1)))
            for i,(t,*_) in enumerate(m)}


class ImuTests(unittest.TestCase):
    def setUp(self):
        self.cast = motion(cast=True)
        self.hook = motion()
        self.backwards = motion(sign=-1)
        self.cast_example, _ = make_example(self.cast, attitudes(self.cast))
        self.hook_example, _ = make_example(self.hook, attitudes(self.hook))
        self.trained = {'CAST':[self.cast_example], 'HOOK':[self.hook_example], 'NEGATIVE':[]}

    def test_rotation_angle_and_global_posture_invariance(self):
        from phyphox_client import relative_motion
        m = self.hook
        a = attitudes(m, 90, 0)
        b = attitudes(m, 90, 2)
        # Device-frame acceleration must be transformed by the same q_t; here
        # rotation trajectory itself must be independent of Earth initial yaw.
        for mapping in (a,b):
            rot, stats = rotation_signature(m, mapping)
            self.assertAlmostEqual(stats['rotation_path_degrees'],90.,places=4)
            self.assertAlmostEqual(stats['rotation_peak_degrees'],90.,places=4)
        ra,_ = rotation_signature(m,a)
        rb,_ = rotation_signature(m,b)
        for row_a,row_b in zip(ra,rb):
            for x,y in zip(row_a,row_b):
                self.assertAlmostEqual(x,y,places=5)

    def test_rotation_speed_from_attitude(self):
        self.assertAlmostEqual(angular_rate_dps(quat_x(0),quat_x(math.pi/2),.2),450.,places=4)
        self.assertEqual(angular_rate_dps(quat_x(0),quat_x(.1),.4),0.)

    def test_cast_has_two_phase_gate(self):
        self.assertTrue(cast_reversal(self.cast)[0])
        self.assertFalse(cast_reversal(self.hook)[0])
        label,_,_ = classify(self.cast_example,self.trained,True,0.)
        self.assertEqual(label,'CAST')

    def test_hook_toward_recognized(self):
        label,_,reason = classify(self.hook_example,self.trained,False,0.)
        self.assertEqual(label,'HOOK',reason)

    def test_reverse_hook_rejected(self):
        query,_ = make_example(self.backwards,attitudes(self.backwards))
        label,_,reason = classify(query,self.trained,False,0.,hook_limit=1.5)
        self.assertIsNone(label,reason)
        self.assertIn('направлен',reason.lower())

    def test_small_wrist_wobble_not_rejected_as_large_rotation(self):
        # A back-and-forth 5-degree wobble can accumulate > 40 degrees,
        # but its maximum departure from the start is only 5 degrees.
        angles = [0.0, 5.0, 0.0, -5.0] * 6
        total_path = sum(abs(b-a) for a,b in zip(angles, angles[1:]))
        peak = max(abs(a) for a in angles)
        self.assertGreater(total_path, 40.)
        self.assertEqual(peak, 5.)
        label, _, reason = classify(self.hook_example, self.trained, False, peak,
                                     hook_rotation_limit=40.)
        self.assertEqual(label, 'HOOK', reason)

    def test_one_phase_hook_not_required_to_have_cast_reversal(self):
        self.assertFalse(cast_reversal(self.hook)[0])
        label, _, reason = classify(self.hook_example, self.trained, False, 0.)
        self.assertEqual(label, 'HOOK', reason)

    def test_pronation_rejected_even_if_acceleration_identical_to_hook(self):
        rotating, stats = make_example(self.hook, attitudes(self.hook,100))
        label, scores, reason = classify(rotating,self.trained,False,stats['rotation_path_degrees'],
                                         hook_limit=1.5,hook_rotation_limit=40.)
        self.assertIsNone(label,reason)
        self.assertIn('вращение',reason)

    def test_negative_example_veto(self):
        templates = {k:list(v) for k,v in self.trained.items()}
        templates['NEGATIVE']=[self.hook_example]
        label,scores,reason = classify(self.hook_example,templates,False,0.)
        self.assertIsNone(label)
        self.assertIn('запрещённый',reason)
        self.assertEqual(scores['NEGATIVE'],0.)

    def test_unknown_on_independent_thresholds(self):
        noisy,_ = make_example(motion(cast=False,sign=-1),attitudes(self.hook))
        label,_,reason = classify(noisy,self.trained,False,0.,
                                  cast_limit=.1,hook_limit=.1)
        self.assertIsNone(label)
        self.assertIn('UNKNOWN',reason)

    def test_rotation_only_negative_can_segment(self):
        detector = MotionSegmenter(threshold=3.,quiet_seconds=.2)
        output=[]
        t=0.
        for idx in range(85):
            t=idx*.012
            rate = 190. if 20<=idx<45 else 0.
            event=detector.feed((t,0.,0.,0.),rate,130.)
            if event:
                output.append(event)
        self.assertEqual(len(output),1)
        self.assertGreater(len(output[0]),20)

    def test_pure_rotation_can_be_trained_as_negative(self):
        stationary=[(i*.012,0.,0.,0.) for i in range(90)]
        example,stats=make_example(stationary,attitudes(stationary,90))
        self.assertTrue(all(x==0 for row in example['acc'] for x in row))
        self.assertGreater(stats['rotation_path_degrees'],85)

    def test_missing_negative_is_allowed(self):
        self.assertIsNone(separation({'CAST':[],'HOOK':[],'NEGATIVE':[]}))
        self.assertIsInstance(separation(self.trained),float)

    def test_settings_migration_drops_old_recognition_modes(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'settings.json'
            old = {'url':'http://192.168.1.21:8080','motion_mode':'world',
                   'templates':{'CAST':[[[0,0,0]]*24]},
                   'relative_templates':{'HOOK':[[[0,0,0]]*24]},
                   'require_hook_direction':False}
            path.write_text(json.dumps(old),'utf-8')
            new=load(path)
            self.assertEqual(new['url'],old['url'])
            self.assertEqual(new['imu_templates'],{'CAST':[],'HOOK':[],'NEGATIVE':[]})
            self.assertNotIn('motion_mode',new)
            new['imu_templates']['HOOK']=[self.hook_example]
            save(new,path)
            self.assertTrue((path.parent/'settings-v0.9-backup.json').exists())
            written=json.loads(path.read_text('utf-8'))
            self.assertNotIn('relative_templates',written)
            self.assertEqual(len(load(path)['imu_templates']['HOOK']),1)

    def test_session_still_requires_cast_then_hook(self):
        sess=FishingSession()
        self.assertFalse(sess.consume('HOOK',10)[0])
        self.assertTrue(sess.consume('CAST',10)[0])
        self.assertFalse(sess.consume('HOOK',10.2)[0])
        self.assertTrue(sess.consume('HOOK',12)[0])


if __name__=='__main__':
    unittest.main()
