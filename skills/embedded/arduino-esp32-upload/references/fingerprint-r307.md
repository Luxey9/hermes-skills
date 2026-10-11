# Fingerprint (R307) device: slot vs DB mismatch

The single most common false alarm: "enroll sukses tapi ID Tidak Terdaftar".
Three INDEPENDENT requirements must all hold; each failure has a different cause
but two of them share the same message.

## The three gates (server side, /api/scan)

| # | Requirement | Failure message |
|---|---|---|
| 1 | slot EXISTS in sensor | `GAGAL|ID Tidak Terdaftar` (`id=0`) |
| 2 | row `users.fingerprint_id = N` exists | `GAGAL|ID Tidak Terdaftar` (same text!) |
| 3 | that row's `hak_akses` contains the lab | `GAGAL|Akses Ditolak` |
| 4 | an active schedule exists for the lab now | `GAGAL|Tidak Ada Jadwal` |

Gate 4 is NOT a detection failure — the ID was found and matched. Out-of-hours
testing always hits it. `Tidak Ada Jadwal` = success at gate 2/3.

## THE INVARIANT

```
number stored at sensor slot N  ==  users.fingerprint_id N
```

Enroll does NOT create a DB row. Sensor flash and SQLite are separate stores.
Enrolling a number that has no `users` row stores fine, then every tap is rejected.
Always check the DB's used `fingerprint_id` range FIRST and enroll only inside it.

## Enroll success != usable template

`storeModel()` returning OK only means flash was written. `fingerSearch()` later
may still not match it. NEVER trust a bare "SUKSES" on the OLED. The `Kelola`
sketch's `E<n>` re-scans immediately after storing and prints:

```
[VERIF] cocok id=69 confidence=NNN
[VERIF] BENAR -> slot sesuai        <- only this means done
[VERIF] SALAH SLOT -> jari sudah ada di slot lain
[VERIF] GAGAL -> template tersimpan tapi tak bisa dicocokkan
```

If VERIF is not `BENAR`, treat the enroll as failed and redo it.

## Who taps during enroll == who gets stored

The operator is usually the one holding the device. If YOU put your finger down
during an enroll targeting slot N, YOUR finger lands in slot N — not the other
person's. Symptom: the other person is rejected, and the operator's taps register
as the wrong person. Always have the intended person tap.

## One finger in multiple slots = random results

Re-enrolling the same finger into new slots creates duplicates. `fingerSearch()`
returns the best match, which can be any of them, so results look erratic (jumps
between ids). Symptom seen: one finger matched id=64, id=65, id=58, id=81 on
different taps. Fix: delete duplicates (`D<n>`) so the finger has exactly one slot.

## Diagnostic commands (Kelola sketch)

```
L        list occupied slots
T        test tap x3 (needs finger within 15 s each)
W<n>     CONTINUOUS monitor n seconds -- tap anytime (best for diagnosis)
S<n>     security level 1..5 (1 = loosest). Rarely helps; see below.
D<n>     delete slot n
E<n>     enroll to n, then verify immediately
```

Send via `scripts/kelola_drive.py COM4 "W60" 70`.

Use `W` not `T` for human-in-the-loop: `T` has 15 s windows that people miss and
the run just prints "[!] tak ada jari / timeout", giving no data.

## Reading the confidence number

Higher is better. Observed on one R307:

| Situation | confidence |
|---|---|
| clean single tap, finger lifted between reads | 241, 399, 457, **664** |
| continuous re-read while finger held | 60-180 |

So low numbers during `W` (finger held down) are partially an artifact of
re-reading the same placement. `0x17` (undefined in the Adafruit library) appears
intermittently and means a failed search, not "not enrolled".

`S1..S5` (setSecurityLevel) made NO difference to confidence in testing —
do not spend time there. Real fixes: clean the sensor glass (dry microfibre).

## Firmware bugs worth knowing (Main.ino pattern)

```c
// WRONG: every search failure becomes id=0 -> server says "tidak terdaftar"
if (p == FINGERPRINT_OK) return finger.fingerID;
else return 0;

// RIGHT: only NOTFOUND is "unknown finger"; other codes are READ failures
error
if (p == FINGERPRINT_NOTFOUND) return 0;   // needed for enroll mode
return -2;                                  // show "Baca Gagal", send nothing
```

Also: a blind `delay(2000)` after a tap discards taps. Wait for
`FINGERPRINT_NOFINGER` instead. And do not `while(1)` on `verifyPassword()`
failure — retry 5x, then keep LAN alive and report only the sensor as broken.

## Firebase stale queue ("ghost" enroll/delete)

Server keeps `device_control/{lab}` = `{mode, target_id}` in Firebase and resets it
when the command is SENT, not when it succeeds. Stale entries make every tap consume
one queued command. Observed live via serial:

```
Respon Server: DELETE|63     <- deleted an already-good enrollment
Respon Server: ENROLL|64     <- forced enroll into someone else's slot
```

If a slot vanishes after a successful enroll, or enroll pops up unrequested,
suspect a stale `device_control` entry, not the hardware.
