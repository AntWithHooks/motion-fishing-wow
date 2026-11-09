# 🎣 Motion Fishing

**Turn your iPhone into a gesture-controlled fishing rod for World of Warcraft: Forever.**

[🇷🇺 Читать по-русски](README.ru.md) · [Report a bug](../../issues/new/choose) · [Contribute](CONTRIBUTING.md)

![Platform](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D6) ![Phone](https://img.shields.io/badge/iPhone-iOS-222222) ![Network](https://img.shields.io/badge/connection-local%20Wi--Fi-00856A) ![Languages](https://img.shields.io/badge/UI-EN%20%7C%20RU-D5A640) ![License](https://img.shields.io/badge/license-MIT-blue)

> **Experimental project.** Source code and a [Windows portable release (v1.2.0)](https://github.com/AntWithHooks/motion-fishing-wow/releases/tag/v1.2.0) are available. Gesture recognition requires individual calibration.

## About

Motion Fishing is a free, unofficial motion controller for fishing in **WoW Forever**. Hold your iPhone like a fishing rod: make a two-part casting gesture to cast, then pull your arm back to hook a fish.

Your phone runs [phyphox](https://phyphox.org/), which sends accelerometer and orientation data to the Windows app over a **local Wi-Fi connection**. No Bluetooth connection, Mac, or custom iOS app is required.

```text
iPhone + phyphox        Local Wi-Fi          Windows + Motion Fishing           WoW Forever
Acceleration + attitude ───────────────────► CAST / HOOK / UNKNOWN ── key press ─► Fishing addon
```

## Features

- **CAST:** a two-phase gesture — back, then forward.
- **HOOK:** a learned pull gesture, with direction and rotation checks.
- **NEGATIVE:** examples of movements to reject, including wrist pronation and supination.
- **UNKNOWN:** no key press when a gesture fails the configured checks.
- **Relative coordinate frame:** movements are evaluated against the phone's orientation at the beginning of each gesture.
- **Personal gesture training:** independently adjustable recognition parameters and saved examples.
- **Portable profiles:** public `profiles/default.json` and personal `profiles/settings.json`.
- **English / Русский:** clear RU / EN switch in the main window.

The tool responds to deliberate player gestures. It does **not** detect bites automatically, fish unattended, or send repeated commands on a timer.

## Requirements

| | |
| --- | --- |
| PC | Windows 10 / 11 |
| Phone | iPhone with the free [phyphox](https://phyphox.org/) app |
| Network | Phone and PC on the same reachable local network (Ethernet for the PC is fine) |
| Game | WoW Forever with a compatible one-key fishing setup |
| Python | Not required **once a packaged Windows EXE is published** |

## Setup

1. Install **phyphox** on your iPhone.
2. Import the **Acceleration and Attitude** experiment into phyphox.
3. Connect iPhone and Windows PC to the same local network.
4. Open the experiment, press **Play**, enable **Remote Access**, and copy the address shown by phyphox.
5. Download the **portable ZIP from [Releases](https://github.com/AntWithHooks/motion-fishing-wow/releases/tag/v1.2.0)** (GitHub's automatic *Source code* ZIP is not the executable). Extract it into a writable folder and run `MotionFishing.exe`.
6. Enter the phyphox address and click **Connect**.
7. In WoW, set up a one-key fishing addon and verify its assigned key (e.g. `F8`) works with your physical keyboard. Select the same key in Motion Fishing.
8. Train several CAST, HOOK, and NEGATIVE examples. **Disable key sending** while testing recognition in the event log; enable it when ready to play.

The Windows release includes the packaged program; the source tree provides scripts for developers.

## How profiles work

| File | Meaning | Publish? |
| --- | --- | --- |
| `profiles/default.json` | Public starter preset / intentionally shared gestures | ✅ Yes |
| `profiles/settings.json` | Your local phyphox address, settings, training examples | ❌ No |

Keep `profiles/settings.json` out of Git. Only publish gesture examples you intentionally want to share. Presets may need adjustment for different users, hand grips and postures.

## Building

When project source files are uploaded, run `START.bat` on Windows with Python installed for development, or `BUILD_EXE.bat` to create a distributable EXE. The [Windows build workflow](.github/workflows/build-windows.yml) will then build a portable ZIP as a GitHub Actions artifact.

**Do not claim a release is ready until the artifact has been tested on Windows with an actual iPhone.**

## Contributing & disclaimer

Bug reports and improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Please remove private IP addresses and personal information from logs.

This is an **unofficial community project**, not affiliated with or endorsed by Blizzard Entertainment. Follow your server's rules regarding external input tools. World of Warcraft and its trademarks belong to their respective owners.

[MIT License](LICENSE) · [Русская версия](README.ru.md)
