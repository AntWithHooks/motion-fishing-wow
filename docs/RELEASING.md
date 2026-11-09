# Windows release checklist

1. Upload the full source files to the repository, including `motion_fishing_gui.py`, other modules, `tests/`, `assets/motion_fishing.ico`, **both PDF guides**, and `profiles/default.json`.
2. Keep **`profiles/settings.json` private**. Review shared gesture examples before publishing.
3. Run `python -m unittest discover -s tests -v` on the full project.
4. Open **Actions → Build Motion Fishing for Windows → Run workflow**. The workflow builds and uploads `MotionFishing-Windows-Portable.zip` as an Actions artifact.
5. Download that ZIP and test on an actual Windows PC with an iPhone running phyphox: connect, load profiles, toggle RU/EN, train CAST/HOOK/NEGATIVE, confirm the physical WoW key and gestures.
6. Open **Releases → Draft a new release**. Use a version tag (e.g. `v1.2.0`), describe known limitations, and attach the verified portable ZIP.
7. Tell users to download the **release ZIP**, not GitHub's automatic **Source code (zip)**.

A GitHub Actions artifact is **not automatically a GitHub Release**. Only publish a release after real-device verification.
