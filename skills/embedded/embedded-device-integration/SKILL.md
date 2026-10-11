---
name: embedded-device-integration
description: Use when relocating a networked embedded device.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [embedded, esp32, arduino, ethernet, fingerprint-sensor, lan, dhcp, deployment]
    related_skills: [supabase-backend-debugging, systematic-debugging]
---

# Embedded Device Integration

Deploying, reconfiguring, or relocating a networked embedded device (ESP32/Arduino + Ethernet/WiFi) that talks to a local server. Covers the read-first workflow, the state layers that must ALL change on a move, and the LAN/on-device pitfalls that make a device look broken when the fault is elsewhere.

## When to Use

- The user asks to move, re-site, or re-configure a networked MCU device ("set to lab X", "pindah alat", new site name).
- The user asks how a device is wired to a PC/switch/router, or whether cabling alone is enough ("asal colok?").
- The user asks where a device's data actually lives (MCU flash vs sensor flash vs server DB).
- You are handed one firmware file and must explain the device↔server contract from it.

## Procedure

1. **Read the firmware before answering anything.** The firmware file *is* the device↔server contract: HTTP method, path, query params, response grammar, timeouts. Grep it rather than reasoning about what such a device "usually" does.
2. **Separate fact from inference, out loud.** One file in the folder means you know one side of the protocol only. State plainly what the firmware proves and what the server-side data model is merely inferred from it. Do not describe a DB schema as if you read it when the server source was not available — ask for the server file path instead.
3. **Answer "what must change?" as an enumerated checklist, not the one obvious constant.** A device move is never one edit. Enumerate all layers, then order them by dependency (register first, wipe second, flash third, cable fourth, boot last).
4. **Diagnostic ladder before physical rework.** Reach for the cheapest check first, in this order:
   - From the server PC, curl the endpoint with a dummy id and the target site name: any response at all (including a rejection) proves firmware→LAN→server is alive; empty/timeout means the network, not the app.
   - `ipconfig /all` (see the Windows/MSYS note below) to learn the machine's real subnet and whether the server IP in the firmware exists on any adapter at all.
   - Ping the device's reported IP.
   Read the device's own boot log over serial (`scripts/capture_serial_with_reset.py`) — it names the failing stage directly (`Fingerprint OK`, then the DHCP wait) and separates a dead device from a network fault in one shot.
   A rejection that names a domain fact ("not registered", "no schedule") is the server answering correctly, not a device fault — cross-check the roster against the device's own slot list before touching hardware (see `references/fingerprint-attendance-stack.md`).
   Only after those, suspect cable or hardware.

## State layers on a device move

Every layer must be handled; skipping any produces a device that runs but rejects everyone.

| Layer | Where | Action |
|---|---|---|
| Site identity + server address + unit ID | Firmware constants | Edit the site/room name, server IP, and the per-unit hardware address byte |
| Hardware address uniqueness | Firmware | Give every unit a distinct last byte — DHCP identifies clients by that address, so a duplicate means IP contention between units |
| Stored templates / calibration data | Sensor's own flash | Wipe or re-enroll — this data does NOT live in the MCU and follows the physical sensor |
| Server-side registry | Server DB | Register the new site AND its users/permissions before anyone scans |
| Network infrastructure | Router/switch/PC | A DHCP server must exist on the segment |

## Pitfalls

- **Sensor-side data follows the hardware, MCU-side data does not.** Fingerprint/calibration templates live in the sensor module's own flash: wiping or reflashing the MCU does not clear them, and swapping the sensor onto a different MCU carries them along. An ID is only a number — ID 17 means a different person in a different site — so reusing hardware in a new site without wiping silently maps old enrolments onto the new site's roster. The wipe is required *only* when the roster changes — see the next two pitfalls.
- **Do not prescribe a wipe by default; prove the roster changed first.** Reflashing a device that stays in its ORIGINAL site is the opposite case: its templates already match the roster, so wiping destroys real work for nothing. Before recommending a wipe, establish whether the sensor's slot numbers still correspond to the same people in the server's user table — ask for the DB file, or read the admin panel's list. If they match and the site name is unchanged, the correct action is *no wipe at all*: edit the firmware constant, flash, scan once, confirm the server logs the right name. A wipe is free only when the device genuinely moves between rosters, and the user may have to re-enrol everyone by hand as the price.
- **Never assert sensor slot or overwrite semantics from memory.** Whether storing into an already-occupied slot fails or silently replaces is a sensor-firmware behaviour, not a library one — read the installed library's doc comment for the store call (`Adafruit_Fingerprint.h/.cpp` under `Documents/Arduino/libraries/`) before telling the user a write will be rejected. If it is genuinely unknown, say so and have the user pick a free slot, which is safe either way.
- **Leftover slots with no matching server row are the real residue, not the whole sensor.** A slot whose person was removed from the server's user table makes its scans answer "not registered" forever, and no amount of wiping-by-policy is needed: delete that one ID via the admin panel's delete command. Prefer targeted deletes over a full wipe whenever the residual set is small.
- **Confirm where persistence lives by grepping the firmware**, not by assuming: search for the MCU-side persistence APIs (`EEPROM`, `LittleFS`, `SPIFFS`, `Preferences`, `SD`) and for the sensor-side calls (`storeModel`, `deleteModel`, `fingerSearch`, `createModel`). Hits on sensor calls plus zero hits on MCU persistence means the MCU is a stateless bridge.
- **`Ethernet.begin(mac)` with no arguments means DHCP.** An unmanaged switch has no DHCP server, so device + PC + switch alone never boot: the device loops on its "waiting for the server" path forever and shows an error LED. Fix is an upstream router with DHCP, or Windows ICS on the server PC (which pins that adapter to the ICS default `192.168.137.1`). A magic-looking server IP in old firmware is usually a leftover ICS default — verify against the current machine before keeping it.
- **Server and device must be on the same subnet.** Check the server PC's real adapter addresses before editing the firmware's server IP; a laptop with only Wi-Fi, a hypervisor host-only adapter, and a VPN tunnel has no usable wired server address until an adapter is added.
- **Windows Firewall rejects inbound by default.** Open the listening port once on the server PC:
  `netsh advfirewall firewall add rule name="<app>" dir=in action=allow protocol=TCP localport=<port>`
- **Boot order is migration order:** DHCP source (router / ICS) → server process listening → then the device. A device powered first never acquires a lease and needs a power cycle.
- **Enrolment slot range is sensor-limited** (commonly 1–127 on R307-class modules; some variants allow more). Storing outside the range fails at the sensor, not in your app.
- **A straight-through cable is always fine:** W5500-class Ethernet modules do auto-MDIX, so crossover cabling is never worth tracking down.
- **Never collapse "could not measure" into "not in the domain".** Firmware that maps EVERY failed match to the same sentinel the server reads as "finger not registered" turns a dirty scan into a false verdict: the user is told their enrolled finger does not exist. Map only the sensor's explicit not-found code to the unknown-finger value (needed for enrolment); give every other code its own sentinel that suppresses the server call and asks for a re-scan. These need opposite fixes, so the messages must differ. Verify the enum in the installed library header rather than trusting remembered code meanings — one vendor code observed here was absent from the library's own defines.
- **A successful store is not a matchable template.** Writing to sensor flash can succeed while the resulting template never matches its own finger. Treat enrolment as finished only after an immediate verification scan returns the expected ID with a healthy confidence; a build with no verification step cannot tell "enrolled" from "enrolled badly", and the user will report the impossible-sounding "enrolment succeeded but it says not registered".
- **One finger, one slot.** Enrolling the same finger into several slots gives the sensor several equally-good candidates, so the returned ID flaps between them from tap to tap. The symptom looks like random rejection ("it worked a minute ago") but follows the finger, not the wiring. Delete the duplicate slots; never leave a test enrolment behind on a slot whose server roster row belongs to somebody else — that makes one person's scans record under another's name.
- **A server-side command queue cleared on send, and only read when a scan arrives, replays stale commands one per tap.** Clearing the queue the moment the command is dispatched means an abandoned enrol/delete is never retired; if it also only gets read when a scan comes in, each tap burns one stale command and performs it again — silently wiping the very slots that were just enrolled. Diagnose from the device's serial response stream (the raw `STATUS|payload` lines), which shows the server's actual commands; do not infer them from the OLED. When a freshly enrolled slot disappears, suspect a queued delete before suspecting flash wear.
- **Do not halt the device on peripheral init failure.** Retry the peripheral probe a few times first (connectors work loose; sensors boot slowly), and if it still fails, continue running with the fault reported on the display instead of spinning in an infinite loop. A hard halt converts a degraded device into a dead one and hides whether the network half was ever fine.
- **Wait for finger release; do not use a fixed post-scan delay.** A blind delay after handling a scan creates a window where the sensor is ignored entirely, so taps inside it vanish with no feedback and the user calls it flaky. Poll for the sensor's no-finger code instead.

## Windows / MSYS shell notes

The terminal runs bash (MSYS) on Windows. Native Windows tools do not get path translation here, and `ipconfig /all` gets its `/all` munged into a path argument, which makes the tool print its own usage text instead of data. Re-run with arg conversion disabled:

```bash
MSYS2_ARG_CONV_EXCL='*' ipconfig /all
MSYS2_ARG_CONV_EXCL='*' getmac /v /fo list
```

An `ipconfig` invocation that returns usage/help text is a quoting problem, not a missing tool — do not conclude the command is unavailable.

## Reporting style for this user

Deliver a multi-step migration as a markdown checklist FILE in the device's own folder — phased in dependency order, `- [ ]` boxes, one phase per layer — then attach it with `MEDIA:` and keep the chat reply short. The file must carry a findings block that cites `file:line` for every code claim, a "still missing" list showing what is blocked on the user, and a closing section naming the bug(s) or risks found while reading the server source. When the user asks "bisa ga dibikin list?", they mean this file, not a longer chat message.

Reply in Indonesian, terse. Lead with the direct yes/no verdict on the user's proposed shortcut, then the checklist of what else must change. Use small markdown tables for "N things must change" and status→effect mappings. Quote firmware lines with their constants (site-name define, server IP, MAC byte) so the user can edit them directly. Never claim a server-side schema is confirmed without its source.

See `references/fingerprint-attendance-stack.md` for the concrete device/server contract of the lab attendance build (pinout, response grammar, enroll/delete flows).
See `references/arduino-esp32-cli-toolchain.md` for headless `arduino-cli` setup, the ESP32 core install (~8.5 GB), compile/upload commands, serial-port identification, and the flag/path quirks that cost time on Windows.
Run `scripts/capture_serial_with_reset.py COM5` to read a device's boot log — it drives the reset line itself so the one-shot boot banner is not missed.
Run `scripts/serial_command_driver.py COM5 "L" 20 "T" 40` to drive a firmware that accepts serial commands and time the capture per command — use it whenever step-by-step hardware actions need sequencing.
