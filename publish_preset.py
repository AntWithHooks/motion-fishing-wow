"""Publish the current local Motion Fishing profile as the GitHub starter preset."""
from settings_store import load, publish_preset, settings_path

if __name__ == '__main__':
    profile = load()  # migrates the old APPDATA profile on first use
    samples = profile.get('imu_templates') or {}
    count = sum(len(samples.get(kind, [])) for kind in ('CAST','HOOK','NEGATIVE'))
    if not count:
        raise SystemExit('No learned gestures in the profile. Train some gestures first.')
    path = publish_preset(profile)
    print(f'Saved {count} learned gestures to {path}')
    print(f'Your personal profile stays at {settings_path()}')
    print('Local phyphox address was excluded from the public preset.')
