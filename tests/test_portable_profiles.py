"""Portable profile migration, packaging and safe publication tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import settings_store as store


class PortableProfileTests(unittest.TestCase):
    def _base(self, gesture_count=0):
        data = dict(store.DEFAULTS)
        data['imu_templates'] = {'CAST': [], 'HOOK': [], 'NEGATIVE': []}
        if gesture_count:
            ex = {'acc': [[0.0, 0.0, 0.0]]*24,
                  'rot': [[0.0, 0.0, 0.0]]*24}
            data['imu_templates']['HOOK'] = [ex for _ in range(gesture_count)]
        return data

    def test_settings_path_is_relative_to_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(store, 'application_dir', return_value=Path(tmp)):
                self.assertEqual(store.settings_path(), Path(tmp)/'profiles'/'settings.json')
                self.assertEqual(store.preset_path(), Path(tmp)/'profiles'/'default.json')

    def test_legacy_migration_preserves_all_gestures_and_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root/'old'/'settings.json'
            legacy.parent.mkdir()
            data = self._base(1)
            data['url'] = 'http://192.168.0.11:8080'
            legacy.write_text(json.dumps(data), encoding='utf-8')
            with patch.object(store, 'application_dir', return_value=root/'new'), \
                 patch.object(store, 'legacy_settings_path', return_value=legacy):
                loaded = store.load()
                self.assertEqual(loaded['url'],data['url'])
                self.assertEqual(len(loaded['imu_templates']['HOOK']),1)
                store.save(loaded)
                self.assertEqual(len(store.load()['imu_templates']['HOOK']),1)
                self.assertEqual(json.loads(legacy.read_text())['url'],data['url'])
                self.assertTrue(store.settings_path().exists())

    def test_cloned_repo_uses_public_preset_and_personal_edits_do_not_modify_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'profiles').mkdir()
            shared=self._base(1)
            shared['key']='F9'
            (root/'profiles'/'default.json').write_text(json.dumps(shared),'utf-8')
            with patch.object(store,'application_dir', return_value=root), \
                 patch.object(store,'legacy_settings_path',return_value=root/'absent'):
                local=store.load()
                self.assertEqual(local['key'],'F9')
                self.assertEqual(len(local['imu_templates']['HOOK']),1)
                local['url']='http://10.0.0.2:8080'
                store.save(local)
                self.assertEqual(store.load()['url'],'http://10.0.0.2:8080')
                self.assertEqual(json.loads((root/'profiles'/'default.json').read_text())['url'],'')

    def test_publish_redacts_ip_keeps_gestures_and_preserves_personal_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            data=self._base(2)
            data['url']='http://192.168.100.1:8080'
            with patch.object(store,'application_dir',return_value=root):
                store.save(data)
                dest=store.publish_preset(store.load())
                published=json.loads(dest.read_text('utf-8'))
                self.assertEqual(published['url'],'')
                self.assertEqual(published['imu_templates'],data['imu_templates'])
                self.assertEqual(store.load()['url'],data['url'])

    def test_existing_local_profile_wins_over_old_and_public(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'profiles').mkdir()
            local=self._base(); local['key']='F7'
            shared=self._base(); shared['key']='F8'
            old=self._base(); old['key']='F9'
            (root/'profiles'/'settings.json').write_text(json.dumps(local),'utf-8')
            (root/'profiles'/'default.json').write_text(json.dumps(shared),'utf-8')
            legacy=root/'legacy.json';legacy.write_text(json.dumps(old),'utf-8')
            with patch.object(store,'application_dir',return_value=root), \
                 patch.object(store,'legacy_settings_path',return_value=legacy):
                self.assertEqual(store.load()['key'],'F7')

    def test_frozen_path_adjacent_to_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            import sys
            with patch.object(sys, 'frozen', True, create=True), \
                 patch.object(sys, 'executable', str(Path(tmp)/'MotionFishing.exe')):
                self.assertEqual(store.application_dir(),Path(tmp).resolve())


if __name__=='__main__':
    unittest.main()
