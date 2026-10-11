#!/usr/bin/env python
"""Read an ESP32/Arduino boot log over serial, driving the reset line first.

Why this exists: firmware emits its boot banner (sensor probe result, DHCP
progress) exactly once, before any serial monitor attaches, and never repeats
it. Attaching a monitor to a running board therefore prints nothing and looks
like the firmware is dead. This toggles the reset line so capture starts at a
known power-on.

Usage:
    python capture_serial_with_reset.py [PORT] [SECONDS] [BAUD]

Defaults: COM5, 18 s, 115200.
Requires pyserial:  pip install pyserial
"""

import sys
import time

import serial


def capture(port="COM5", seconds=18.0, baud=115200):
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = baud
    ser.timeout = 0.3
    ser.dtr = False
    ser.rts = False
    ser.open()
    time.sleep(0.2)

    # RTS is wired to EN (reset) on common ESP32 dev boards; DTR must stay low
    # or the chip latches into the ROM bootloader instead of running the sketch.
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.15)
    ser.setRTS(False)
    time.sleep(0.1)
    ser.reset_input_buffer()

    deadline = time.time() + seconds
    raw = b""
    while time.time() < deadline:
        chunk = ser.read(256)
        if chunk:
            raw += chunk
    ser.close()

    text = raw.decode("utf-8", errors="replace")
    print("=== %d bytes from %s ==" % (len(raw), port))
    print(text if text.strip() else "(NO OUTPUT - wrong port, wrong baud, or board held in reset)")
    return text


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "COM5"
    s = float(sys.argv[2]) if len(sys.argv) > 2 else 18.0
    b = int(sys.argv[3]) if len(sys.argv) > 3 else 115200
    capture(p, s, b)
