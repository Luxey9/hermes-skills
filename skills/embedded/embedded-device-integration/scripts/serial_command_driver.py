#!/usr/bin/env python3
"""Drive a firmware that accepts serial commands, timing the capture per command.

Usage:
    python serial_command_driver.py COM5 "L" 20 "E63" 90 "T" 60

Arguments are: <port> then repeated (command, seconds_to_capture) pairs.
The board is reset on open (RTS -> EN on ESP32) so the boot banner is caught,
which also proves which firmware is running before any command is sent.

Why this exists rather than hand-typed commands: hardware steps need to be
sequenced against the user's actions (tap / lift / tap again), and each step
takes a different amount of time. One shot per command means the capture window
matches the step, and the whole sequence is reproducible instead of ad-hoc.

Requires: pip install pyserial
"""
import sys
import time

import serial


def baca(ser, detik):
    out = b""
    t0 = time.time()
    while time.time() - t0 < detik:
        d = ser.read(256)
        if d:
            out += d
    return out.decode("utf-8", errors="replace")


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1

    port = sys.argv[1]
    rest = sys.argv[2:]
    pairs = []
    for i in range(0, len(rest) - 1, 2):
        pairs.append((rest[i], int(rest[i + 1])))
    if not pairs:
        print("need at least one <command> <seconds> pair")
        return 1

    ser = serial.Serial()
    ser.port = port
    ser.baudrate = 115200
    ser.timeout = 0.3
    # Assert both lines low before open so no spurious reset pulse is emitted.
    ser.dtr = False
    ser.rts = False
    ser.open()
    time.sleep(0.2)

    # RTS drives EN on ESP32: pulse it to reset, so the one-shot boot banner is caught.
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.15)
    ser.setRTS(False)
    time.sleep(0.1)
    ser.reset_input_buffer()

    print(baca(ser, 3))  # boot banner

    for cmd, detik in pairs:
        print(f"\n>>> KIRIM: {cmd}")
        ser.write((cmd + "\n").encode())
        ser.flush()
        print(baca(ser, detik))

    ser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
