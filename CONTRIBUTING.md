# Contributing to Motion Fishing

Thanks for helping improve Motion Fishing!

## Before filing a bug

1. Check existing Issues.
2. Test with phyphox **Acceleration and Attitude**, **Play** and **Remote Access** enabled.
3. Confirm the iPhone and Windows PC are on the same reachable local network.
4. Check that the one-key fishing addon works using a **physical keyboard** key.
5. Describe what actually happened and what you expected.

Please include the Motion Fishing version, Windows version, iPhone model, whether sample data arrived, the gesture (CAST/HOOK/NEGATIVE), and relevant event-log messages. **Remove local IPs, personal settings, and private data.**

## Proposed improvements

Open a feature request before major changes. Useful areas include gesture segmentation, recognition metrics, diagnostic visualizations, accessibility, i18n, and packaging.

## Pull requests

- Keep changes focused and explain their purpose.
- Include tests for new recognition behavior.
- Preserve the distinction between `CAST`, `HOOK` and `UNKNOWN`.
- Do not add unattended fishing, automated bite detection or timed repeated input.
- Never commit `profiles/settings.json` or private captured measurements.
- Update both languages for user-visible text when applicable.

## Local development

Once all source files are uploaded, run the project through `START.bat` and use `python -m unittest discover -s tests -v` to check the test suite.

This is a volunteer, unofficial community project. Use respectful issue and PR discussions.
