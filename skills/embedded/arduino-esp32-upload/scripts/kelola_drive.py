import serial, time, sys
# Driver untuk sketch Kelola: kirim perintah, baca balasan.
# Pakai: python kelola_drive.py COM4 "L" 20
#        python kelola_drive.py COM4 "E69" 200
#        python kelola_drive.py COM4 "D69" 12 "S1" 8
port = sys.argv[1]
pairs = []
rest = sys.argv[2:]
for i in range(0, len(rest), 2):
    pairs.append((rest[i], int(rest[i + 1])))

ser = serial.Serial()
ser.port = port
ser.baudrate = 115200
ser.timeout = 0.3
ser.dtr = False
ser.rts = False
ser.open()
time.sleep(0.2)
ser.setDTR(False)
ser.setRTS(True)
time.sleep(0.15)
ser.setRTS(False)
time.sleep(0.1)
ser.reset_input_buffer()

def baca(detik):
    out = b""
    t0 = time.time()
    while time.time() - t0 < detik:
        d = ser.read(256)
        if d:
            out += d
    return out.decode("utf-8", errors="replace")

print(baca(3))
for cmd, detik in pairs:
    print(f"\n>>> KIRIM: {cmd}")
    ser.write((cmd + "\n").encode())
    ser.flush()
    print(baca(detik))

ser.close()
