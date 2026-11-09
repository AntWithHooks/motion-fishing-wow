"""Motion Fishing v1.0: one IMU recognition mode, no legacy gesture modes."""
from __future__ import annotations
import json
import math
import os
import shutil
import sys
from pathlib import Path

DEFAULTS = {
    'url': '', 'key': 'F8', 'only_wow': True, 'language': 'en',
    'cast_threshold': 2.4, 'hook_threshold': 1.75,
    'cast_match_tolerance': .42, 'hook_match_tolerance': .42,
    'negative_match_tolerance': .36,
    'min_reversal_speed': .16, 'hook_direction_min_cosine': .50,
    'hook_max_rotation_degrees': 40., 'rotation_trigger_dps': 130., 'ambiguity_margin': .045,
    'cooldown': .85, 'hook_guard': 1.50, 'quiet_seconds': .20,
    'imu_templates': {'CAST': [], 'HOOK': [], 'NEGATIVE': []},
}
LIMITS = {
    'cast_threshold': (1., 8.), 'hook_threshold': (.75, 8.),
    'cast_match_tolerance': (.10, 1.50), 'hook_match_tolerance': (.10, 1.50),
    'negative_match_tolerance': (.10, 1.50),
    'min_reversal_speed': (.06, .60), 'hook_direction_min_cosine': (.10, .95),
    'hook_max_rotation_degrees': (10., 180.), 'rotation_trigger_dps': (50., 360.), 'ambiguity_margin': (0., .3),
    'cooldown': (.35, 3.), 'hook_guard': (.5, 4.), 'quiet_seconds': (.10, .5),
}


def application_dir() -> Path:
    """Keep user data adjacent to the source tree or the frozen .exe.

    Never use PyInstaller's temporary _MEIPASS folder for writable profiles.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def settings_path() -> Path:
    return application_dir() / 'profiles' / 'settings.json'


def preset_path() -> Path:
    return application_dir() / 'profiles' / 'default.json'


def legacy_settings_path() -> Path:
    """One-time migration source only; never written by this version."""
    return Path(os.getenv('APPDATA') or Path.home() / '.config') / 'MotionFishing' / 'settings.json'


def bundled_preset_path() -> Path:
    """The read-only template packed in a PyInstaller one-file executable."""
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'profiles' / 'default.json'


def ensure_local_profile() -> Path:
    """Initialize the portable profile without overwriting existing user data.

    Priority: local > legacy APPDATA > shared repo preset > bundled preset.
    """
    target = settings_path()
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    sources = (legacy_settings_path(), preset_path(), bundled_preset_path())
    for source in sources:
        if source.is_file() and source.resolve() != target.resolve():
            temp = target.with_suffix('.importing')
            try:
                shutil.copy2(source, temp)
                # Don't replace any local profile that appeared during the copy.
                if not target.exists():
                    temp.replace(target)
                return target
            finally:
                if temp.exists():
                    temp.unlink()
    return target


def valid_example(example) -> bool:
    if not isinstance(example, dict):
        return False
    for name in ('acc', 'rot'):
        matrix = example.get(name)
        if not isinstance(matrix, list) or len(matrix) != 24:
            return False
        if not all(isinstance(row, list) and len(row) == 3 and
                   all(isinstance(v, (float, int)) and not isinstance(v, bool)
                       and math.isfinite(v) and abs(v) < 10 for v in row)
                   for row in matrix):
            return False
    return True


def load(path: Path | None = None) -> dict:
    result = {**DEFAULTS, 'imu_templates': {'CAST': [], 'HOOK': [], 'NEGATIVE': []}}
    path = Path(path) if path is not None else ensure_local_profile()
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        # Old 1.1 profiles did not have a language setting: retain Russian for them.
        result['language'] = data.get('language', 'ru') if data.get('language', 'ru') in ('ru', 'en') else 'ru'
        if isinstance(data.get('url'), str):
            result['url'] = data['url']
        if data.get('key') in ([f'F{i}' for i in range(1, 13)] + ['SPACE','ENTER']):
            result['key'] = data['key']
        if isinstance(data.get('only_wow'), bool):
            result['only_wow'] = data['only_wow']
        for k, (lo, hi) in LIMITS.items():
            v = data.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
                result[k] = max(lo, min(hi, float(v)))
        previous = data.get('imu_templates') or {}
        if isinstance(previous, dict):
            for name in result['imu_templates']:
                examples = previous.get(name, [])
                if isinstance(examples, list):
                    result['imu_templates'][name] = [e for e in examples if valid_example(e)][-12:]
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        pass
    return result


def save(settings: dict, path: Path | None = None) -> None:
    path = Path(path) if path is not None else settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Preserve the old user profile once before dropping obsolete recognition modes.
    backup = path.with_name('settings-v0.9-backup.json')
    if path.exists() and not backup.exists():
        try:
            with path.open('r', encoding='utf-8') as previous_file:
                previous = json.load(previous_file)
            if isinstance(previous, dict) and any(k in previous for k in
                    ('templates','world_templates','relative_templates','motion_mode')):
                shutil.copy2(path, backup)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    tmp = path.with_suffix('.tmp')
    # Intentionally do not persist legacy modes or obsolete sample groups.
    payload = {k: settings[k] for k in DEFAULTS if k in settings}
    with tmp.open('w', encoding='utf-8') as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    tmp.replace(path)


def publish_preset(settings: dict | None = None) -> Path:
    """Publish trained gestures and shared settings without the machine-local IP.

    This file is intentionally committed to Git. The personal profile is not.
    """
    shared = dict(load() if settings is None else settings)
    shared['url'] = ''  # phyphox IP:port belongs to each player's home network
    shared['language'] = 'en'  # public release defaults to English; RU is one click away
    target = preset_path()
    save(shared, target)
    return target
