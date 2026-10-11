# Fingerprint Attendance Stack (ESP32 + Ethernet + Python server)

Concrete layout of the lab attendance device. Read alongside the "State layers on a device move" table in SKILL.md.

## Three tiers

```
MCU firmware (Main.ino)   RAM only — stateless bridge, forgets everything on power loss
      | UART (Serial2, 57600 baud)
Fingerprint sensor        Own flash. Stores finger TEMPLATES (ID 1..127), not images
      | UART
Server (Python, PC)       SQLite. Maps finger_id -> staff name + attendance log
```

The template is the output of the sensor's own model-creation step — a feature vector, not a reversible image — so the server never receives biometrics. A leaked server DB leaks roster numbers only.

## Device -> server request

HTTP GET over raw EthernetClient, connection closed each time, 3 s read timeout:

```
GET /api/scan?id=<fingerID>&lab=<SITE_NAME> HTTP/1.1
```

All decisions are server-side: the device sends every scan including unknown fingers. The ID lookup returns three distinct cases the device must not collapse:

| Return | Meaning |
|---|---|
| `-1` | no finger / image failed — do nothing |
| `0` | finger present but unknown |
| `>0` | matched, that is the ID |

Only the sensor's explicit not-found code may be sent as `0`. Every other match failure (dirty/partial read) must get its own device-side sentinel that skips the request — see the "Never collapse …" pitfall in SKILL.md. A device that sends `0` for dirty reads reports "not registered" for fingers that are registered, and the user cannot tell that case from a genuine unknown finger.

## Server -> device response

Body after the blank header line, format `STATUS|payload`:

| Status | Device action |
|---|---|
| `MASUK` / `KELUAR` | display status + staff name, green LED, 1 beep |
| `ENROLL` | enter enrolment mode for the ID in payload |
| `DELETE` | delete the ID in payload |
| `GAGAL` | rejected: red LED, 3 short beeps, reason text |

Server needs at least three data sets: staff (`finger_id` -> name), attendance log (to decide MASUK vs KELUAR from the last state), and a command queue (the device cannot know on its own whether a scan means enrol, delete, or attendance).

## Enrolment flow (triggered by server replying `ENROLL|<id>`)

1. Capture image 1, 10 s timeout with a loading animation.
2. `image2Tz(1)`.
3. Wait for finger removal (the library's no-finger code).
4. Capture image 2, 10 s timeout, `image2Tz(2)`.
5. `createModel()` — fails as "fingers differ" if the two captures mismatch.
6. `storeModel(id)` — writes to the sensor flash.

Delete uses the sensor's delete call; a "bad location" error means that ID was never enrolled.

### The finger that ENROLLS is the finger that gets STORED

The operator who is physically placing a finger on the reader during an enrolment is the one written into the target slot. The server only chose the slot number — it has no way to know whose finger is on the glass.

This is the root of a whole family of confusing reports from a lab where the same person runs the enrolments:

| Observed | Actual cause |
|---|---|
| "enrolment succeeded, then it says not registered" | the operator enrolled their own finger into someone else's slot |
| "my finger works but records another name" | same cause — the scan matches, so it logs the slot's owner |
| "the real person's finger is now rejected" | their slot is occupied by the operator's template |
| "ID flapping / random rejection" | see the one-finger-one-slot pitfall in SKILL.md; repeated re-enrols of one finger create multiple candidates |

Operating rule, for the user and for you:

- The **owner of the slot must be the one who places the finger**. If the operator tests by enrolling themselves, that slot is now wrong and must be deleted and redone.
- Never leave a self-test enrolment on a slot owned by a real person. Enrol test fingers into free slots only and delete them afterwards.
- A run of "enrol a new slot, then it still says not registered" for every slot above some number is this symptom, not a hardware limit or a numbering boundary. The apparent threshold is coincidence — establish it by checking who placed the finger, not by theorising about a cutoff.
- Verify by reading the returned slot during a test scan. If a single finger answers with different slots on successive taps, that finger is enrolled more than once and the duplicates must be removed before anything else is diagnosed.

## Ethernet wiring (W5500-class module)

SPI, CS pin chosen in firmware; the rest are the MCU's default SPI pins.

| Module | MCU |
|---|---|
| VCC / GND | 3V3 / GND |
| CS | firmware-defined |
| SCK / MISO / MOSI | default SPI pins |
| RST / INT | unused in this build |

## Boot stage map (where a "dead" device actually is)

The firmware prints each stage to serial and mirrors it on the OLED. Reading the two together localises a fault in one pass:

| Serial | OLED | Stage / meaning |
|---|---|---|
| `Fingerprint OK` | `Booting...` then `Koneksi LAN... Mencari Server...` | Sensor probe passed, now inside the DHCP wait loop. Firmware is healthy — any fault from here is the network |
| `Fingerprint Error` | `Error` / `Cek Sensor FP` | Sensor UART dead; the firmware halts in an infinite loop |
| `Berhasil! IP: <ip>` | `Tersambung! <ip>` + green LED | Lease acquired, ready to serve scans |
| `Gagal dapat IP...` repeating every 5 s | `Menunggu PC...` + red LED | No DHCP answer — missing DHCP server or unplugged LAN, not a cable fault until proven |

Key consequence: seeing the LAN/DHCP progress text on the OLED while serial shows `Fingerprint OK` proves the reflash took and the sensor works. Do not go looking for a firmware problem at that point — the remaining work is cabling, DHCP, and the server process.

USB powers the board but carries no application traffic in these builds; all device→server data goes over the module's RJ45. USB is only the flashing and serial-log path.

## Site name is validated per user, not per device

The site name the device sends is checked against each user's own permission list, so a device moved to a new site works for exactly the users whose permission list contains that name. A user enrolled and registered but still rejected at a new site most often has a permission list missing that site — a data/UI fix in the admin panel, never a firmware or sensor fix. Confirm the permission list before touching hardware.

## Server-side validation is a chain of gates, all named in the rejection text

A scan passes several independent checks in order, each with its OWN rejection string. Because the messages differ, they localise the fault precisely — read the exact reason rather than treating any rejection as "not registered":

| Gate | Rejection text | Fault is in |
|---|---|---|
| ID exists in the user table | "not registered" | slot has no roster row, or id arrived as `0` |
| Site is in that user's permission list | "access denied" | permission list data |
| A class is scheduled for that site right now | "no schedule" | schedule data, or simply outside class hours |

Consequences worth telling the user up front:

- "No schedule" means the ID **was found** — it is the strongest evidence the finger, roster row, and permission list are all correct. Do not chase the sensor when this appears.
- A successful enrolment is invisible until a class is scheduled. Instruct the user to add or reuse a test schedule covering the current hour when validating the device outside class hours.
- The permission list is a comma-separated set; an empty value denies every site, it does not mean "all sites".
- The user table's key is the sensor slot number, so the slot/roster mapping is the single thing to cross-check when a registered finger is refused.

## Reading the sensor's own state without the server

When the server is unreachable or its admin panel is not available, two throwaway sketches answer almost every question — and both must be built with real display and buzzer feedback, not serial text alone:

1. **Slot inventory.** Walk the slot range calling the library's load-template call and print the slots that answer OK. This is read-only and non-destructive, and it settles "is the sensor empty / did my enrolment land" in one pass. Report capacity too — it varies by unit (R307-class modules are commonly 1-127, but a 300-slot unit was observed in the same build), so never hardcode the range from memory.
2. **Interactive admin.** A sketch that takes commands over serial and performs list / test-tap / delete / enrol, printing slot + confidence for every match.

Make the interactive one a real first-class tool, because enrolling blind is the single biggest source of wasted rounds:

- Always emit the whole step sequence on the display and a distinct beep per step — "place finger" → "lift" → "place again" → verify. A headless variant leaves the user tapping into a closed window and reporting "nothing happened".
- End every enrolment with an **immediate verification scan** and state the verdict explicitly ("correct slot" vs "stored but unmatchable" vs "already exists in another slot"). This is what distinguishes a good enrolment from one that will fail later.
- Print the match confidence. It is the fastest quality signal available: a good capture is many times higher than a careless one, and a low value predicts the flapping-ID symptom. It also tells a bad capture apart from a genuine non-match.
- If two captures are rejected as "fingers differ", the fix is technique, not hardware: the second placement must match the first in position and pressure. Re-run before suspecting the sensor.
- Keep these sketches in the project folder, not a temp dir — the scratch dir is pruned, and the tool is needed again.

Slot numbers are the server's primary key, so **never test-enrol onto a slot whose roster row belongs to a real person.** Enrol test fingers into free slots only, and delete them when done; a leftover test enrolment makes one person's scans record under another's name.

On the server side the set of valid site names is usually DERIVED FROM DATA, not from a config list you edit: the admin device endpoint enumerates distinct values of the schedule table's location column. A new site therefore becomes "registered" by adding a schedule row for it, and its staff rows must be added *before* anyone scans. Read the server source to learn which table drives the list rather than assuming a hardcoded list exists.

## Network recovery in firmware

On connection failure the device shows an error, plays a beep, then re-runs the DHCP begin and reports either a recovered IP (green) or "check cable" (red). This recovery is what makes a missing DHCP server look like a cable fault — the retry loop repeats every 5 s indefinitely at boot.

Note: the loop only re-runs DHCP on connection failure; there is no periodic lease-maintenance call, so long idle periods rely on a long lease or a static address.
