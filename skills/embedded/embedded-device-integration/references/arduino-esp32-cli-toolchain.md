# Headless Arduino/ESP32 toolchain on Windows (arduino-cli)

Installing, compiling, and flashing an ESP32 from the terminal with no Arduino IDE. Verified end to end: install → compile → upload → boot-log read.

## Install

```bash
export PATH="$HOME/AppData/Local/arduino-cli:$PATH"
cd "$HOME/AppData/Local/arduino-cli"
TAG=$(curl -s https://api.github.com/repos/arduino/arduino-cli/releases/latest | grep -m1 '"tag_name"' | cut -d'"' -f4)
curl -sL -o cli.zip "https://github.com/arduino/arduino-cli/releases/download/$TAG/arduino-cli_${TAG#v}_Windows_64bit.zip"
unzip -o cli.zip && ./arduino-cli.exe version
```

Then add the ESP32 board index and install the core:

```bash
./arduino-cli.exe config init --overwrite        # writes %LOCALAPPDATA%\Arduino15\arduino-cli.yaml
./arduino-cli.exe config add board_manager.additional_urls \
  https://espressif.github.io/arduino-esp32/package_esp32_index.json
./arduino-cli.exe core update-index
./arduino-cli.exe core install esp32:esp32       # ~8.5 GB installed
```

Layout after install: cores in `%LOCALAPPDATA%\Arduino15\packages`, user libraries in `Documents/Arduino/libraries`, downloaded archives cached in `%LOCALAPPDATA%\Arduino15\staging\packages`.

## Libraries

Install one per invocation — the name is the library name, not the `#include` name:

```bash
./arduino-cli.exe lib install "Ethernet"
./arduino-cli.exe lib install "Adafruit Fingerprint Sensor Library"
./arduino-cli.exe lib install "Adafruit GFX Library"
./arduino-cli.exe lib install "Adafruit SSD1306"
./arduino-cli.exe lib list
```

Ethernet-compatible modules on ESP32 may pull nothing extra; `Adafruit BusIO` arrives as a dependency of the Adafruit libraries.

## Compile and upload

```bash
./arduino-cli.exe compile --fqbn esp32:esp32:esp32 "C:/Users/<u>/.../Main"
./arduino-cli.exe upload -p COM5 --fqbn esp32:esp32:esp32 "C:/Users/<u>/.../Main"
```

- The sketch directory MUST be named exactly like the `.ino` file, and the path handed to the native exe must be a `C:/...` forward-slash native path.
- `esp32:esp32:esp32` is "ESP32 Dev Module"; `board listall esp32:esp32` lists the other variants (`esp32doit-devkit-v1`, `nodemcu-32s`, ...).
- A successful upload ends with `Hash of data verified.` per image plus `Hard resetting via RTS pin...`. Compile success prints the storage/dynamic-memory percentages — quote those as the proof the edit built.

## Reading the boot log

`arduino-cli monitor -p COM5 -b 115200` is WRONG: `-b` expects an FQBN and errors `Invalid FQBN: not an FQBN: 115200`. Correct form:

```bash
./arduino-cli.exe monitor -p COM5 --config baudrate=115200
```

Even then it usually prints nothing: the firmware's boot banner is emitted once, before the monitor attaches, and it never repeats. Use `scripts/capture_serial_with_reset.py COM5` instead — it toggles the reset line so capture starts at a known power-on and the banner is caught.

`pip install pyserial` first if the interpreter lacks it.

## Identifying the device's port (Windows/MSYS)

```bash
MSYS2_ARG_CONV_EXCL='*' reg query "HKLM\HARDWARE\DEVICEMAP\SERIALCOMM"
MSYS2_ARG_CONV_EXCL='*' powershell -NoProfile -Command "Get-PnpDevice -Class Ports -PresentOnly | Select-Object FriendlyName,Status | Format-List | Out-String"
./arduino-cli.exe board list
```

`CH340` is a generic USB-serial chip: phones, dev boards, and loose adapters all enumerate as `USB-SERIAL CH340`. So **a CH340 appearing is not proof the target device was attached**, and its COM number changes between plug-ins (the same chip moved COM4 → COM5 within one session). Confirm by comparing the port list before and after the user plugs the target in, or by reading the boot banner — never by "a CH340 is there, so it must be the board".

A device that has no USB port at all (bare Ethernet-module builds) can only be flashed through the MCU's own USB; the module's RJ45 is not a flashing path.

## Quirks that cost time

- **The 673 MB RISC-V compiler archive aborts mid-download.** `core install esp32:esp32` fails with a `Download failed: wsarecv: An established connection was aborted` after stalling at ~0.5% of the largest archive. Just re-run the identical command: completed archives stay in `staging/packages` and are reused, so each retry makes forward progress instead of restarting. Confirm progress by watching `du -sh %LOCALAPPDATA%/Arduino15` and `ls packages/esp32/tools`; the core is not listed by `core list` until extraction finishes.
- **A fresh config's first index command can fail** on `discovery builtin:mdns-discovery not found` and a missing `library_index.json`. Re-run the command (or run `core list`) — it self-heals by downloading the missing discovery tools and indexes.
- **Installs and the first compile exceed the 600 s foreground cap.** Start them as tracked background processes with completion notification and poll the file system for progress; do not re-run them. The first ESP32 compile builds the whole core and is the slowest one — later compiles are seconds.
- **MSYS paths break native invocations.** `$HOME/...` reaches the native exe as `C:\c\Users\...` and the tool answers `Can't open sketch: no such file or directory`. Build the sketch dir from `C:/Users/...` instead.
- **The toolchain is host-independent of the server role.** Flashing from the user's own laptop is fine even when the laptop is not the server PC and has no wired adapter — upload and serving are separate machines. Do not refuse an upload because the laptop cannot be on the device's LAN.
