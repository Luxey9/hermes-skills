---
name: arduino-esp32-upload
description: Use when uploading ESP32 firmware or debugging fingerprint.
version: 1.0.0
author: ratman4080
license: MIT
metadata:
  hermes:
    tags: [esp32, arduino, firmware, fingerprint, serial, windows]
    related_skills: [embedded-device-integration]
---

# Arduino / ESP32 upload + fingerprint device work (Windows + MSYS bash)

## When to Use

- Compiling or uploading Arduino/ESP32 firmware from this Windows host.
- Flashing a sketch that has to talk to a device over USB serial (readback,
  send commands, parse replies).
- Diagnosing a fingerprint (R307/R305) attendance device: enroll failures,
  `GAGAL|ID Tidak Terdaftar`, erratic ids, or low confidence.
- NOT for: non-Arduino boards, USB-serial devices that need no firmware upload.

`terminal` runs git-bash: MSYS paths (`/c/...`) work for bash builtins, but NATIVE
tools (`arduino-cli.exe`, `node`, `git`) need `C:/...` forward-slash paths.
The toolchain is already installed — do NOT re-download 8.5 GB.

## Installed toolchain (this machine)

```
$HOME/AppData/Local/arduino-cli/arduino-cli.exe      v1.5.1
$HOME/AppData/Local/Arduino15/                       ESP32 core (~8.5 GB)
esp32:esp32@3.3.12     board: esp32:esp32:esp32      (ESP32 Dev Module)
libs (user): $HOME/Documents/Arduino/libraries/
  Ethernet 2.0.2 | Adafruit Fingerprint 2.1.4 | Adafruit GFX 1.12.6 | Adafruit SSD1306 2.5.17
```

Core install can drop mid-download (`esp-rv32` is 673 MB). Re-run the SAME command —
staged archives in `Arduino15/staging/packages/` are reused, so it extracts instead
of re-downloading. Do not delete that staging dir to "fix" a failure.

## Compile + upload (always with --output-dir)

`upload` alone on a sketch dir fails: "Compiled sketch not found". Compile with
`--output-dir`, then upload with `--input-dir`:

```bash
AC="$HOME/AppData/Local/arduino-cli/arduino-cli.exe"
SK="C:/path/to/SketchFolder"          # folder name MUST equal the .ino name
BUILD="$TMPDIR/build_xyz"
"$AC" compile --fqbn esp32:esp32:esp32 --output-dir "$BUILD" "$SK"
"$AC" upload  -p COM4 --fqbn esp32:esp32:esp32 --input-dir "$BUILD" "$SK"
```

First compile of a fresh core takes ~10 min; later ones are seconds. Do not kill it.

## Find the port (CH340 / CP210x)

```bash
MSYS2_ARG_CONV_EXCL='*' reg query "HKLM\HARDWARE\DEVICEMAP\SERIALCOMM"
"$AC" board list
```

The port moves between COM4/COM5 across replugs — always re-detect.
`Status: Unknown` means unplugged. A phone also enumerates as CH340: never assume a
CH340 port is the board — confirm the user actually plugged the ESP32.

## Read serial, capturing the boot banner

`arduino-cli monitor` prints nothing if the sketch already booted (the banner is
written once). Toggle RTS to reset the board while reading:

```python
ser = serial.Serial(port="COM4", baudrate=115200, timeout=0.3, dtr=False, rts=False)
ser.open(); time.sleep(0.2)
ser.setDTR(False); ser.setRTS(True); time.sleep(0.15); ser.setRTS(False)
```

Working scripts: `scripts/baca_serial.py` (read N s) and `scripts/kelola_drive.py`
(send cmd + read reply). `pip install pyserial` if missing.

## Fingerprint attendance device (R307)

When the task involves enrolling fingerprints or `GAGAL|ID Tidak Terdaftar`,
read `references/fingerprint-r307.md` first. Key invariant:

```
number in sensor slot N  ==  users.fingerprint_id N
```

Enroll does not create a DB row, and enroll "success" does not mean the template
is matchable. That file has the three gates, the `Kelola` command list, and the
confidence/slot-mismatch diagnosis.

## Timing pitfalls

- `$TMPDIR` (Hermes scratch) is pruned after ~24h — never store sketch sources there.
- A blind `delay(2000)` after a tap discards taps; wait for finger-lift instead.
- Interactive prompts on a serial-driven sketch need a LONG window (90 s), not 12 s,
  when two people coordinate. Add a countdown print.
- Interrupting a long upload leaves state UNKNOWN: re-check `board list` and the
  serial banner before redoing anything.
