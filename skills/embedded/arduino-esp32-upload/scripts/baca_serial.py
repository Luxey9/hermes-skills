import serial, time, sys
# Baca serial dengan reset board supaya pesan boot ikut tertangkap.
# Pakai: python baca_serial.py COM4 18
port = sys.argv[1] if len(sys.argv) > 1 else "COM4"
durasi = int(sys.argv[2]) if len(sys.argv) > 2 else 18

ser = serial.Serial()
ser.port = port
ser.baudrate = 115200
ser.timeout = 0.3
ser.dtr = False
ser.rts = False
ser.open()
time.sleep(0.2)
ser.setDTR(False)
ser.setRTS(True)      # RTS ke ESP32 = EN (reset)
time.sleep(0.15)
ser.setRTS(False)
time.sleep(0.1)
ser.reset_input_buffer()

t0 = time.time()
buf = b""
while time.time() - t0 < durasi:
    data = ser.read(256)
    if data:
        buf += data

ser.close()
text = buf.decode("utf-8", errors="replace")
print("=== PANJANG:", len(buf), "byte ===")
print(text if text.strip() else "(TIDAK ADA OUTPUT)")
