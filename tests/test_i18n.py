import unittest
import tempfile
from pathlib import Path
import json
from unittest.mock import patch
import i18n
import settings_store as store


class LocalizationTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_language('en')

    def test_english_ui_and_dynamic_values(self):
        i18n.set_language('en')
        self.assertEqual(i18n.tr('ПОДКЛЮЧИТЬ'), 'CONNECT')
        self.assertEqual(i18n.tr('ЗАБРОС'), 'CAST')
        self.assertEqual(i18n.tr('ОЖИДАЕТСЯ ПОДСЕЧКА'), 'AWAITING HOOK')
        self.assertEqual(i18n.tr('Записано: 5 из 12 возможных   •   Рекомендуется 5–8'),
                         'Recorded: 5 of 12 possible   •   Recommended: 5–8')
        self.assertEqual(i18n.tr('2.40 м/с²'), '2.40 m/s²')
        self.assertEqual(i18n.tr('0.20 с'), '0.20 s')

    def test_russian_mode_is_identity(self):
        i18n.set_language('ru')
        source='ПОДКЛЮЧИТЬ'
        self.assertEqual(i18n.tr(source), source)

    def test_language_persists_and_old_profile_stays_russian(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'settings.json'
            target.write_text(json.dumps({'url':'http://192.0.2.55:8080','key':'F8'}))
            old=store.load(target)
            self.assertEqual(old['language'], 'ru')
            old['language']='en'
            store.save(old,target)
            self.assertEqual(store.load(target)['language'], 'en')

    def test_public_default_is_english_without_local_address(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(store,'preset_path',return_value=Path(folder)/'default.json'):
                shared={**store.DEFAULTS, 'language':'ru','url':'http://192.0.2.55:8080'}
                store.publish_preset(shared)
                saved=store.load(Path(folder)/'default.json')
                self.assertEqual(saved['language'],'en')
                self.assertEqual(saved['url'],'')


if __name__ == '__main__':
    unittest.main()
