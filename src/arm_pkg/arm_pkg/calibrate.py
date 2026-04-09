import serial
import time

def main():
    print("--- RAW ESP32 CALIBRATION TOOL ---")
    try:
        ser = serial.Serial('/dev/esp32', 115200, timeout=1)
        time.sleep(2) # Wait for ESP32 to reset upon serial connection
    except Exception as e:
        print(f"Error opening /dev/esp32: {e}")
        return

    print("Enter angles format: BASE J1 J2 (e.g., 90 120 45)")
    print("Type 'q' to quit.")

    while True:
        cmd = input("Angles > ")
        if cmd.lower() == 'q':
            break
            
        try:
            parts = cmd.split()
            if len(parts) != 3:
                print("Must be exactly 3 numbers.")
                continue
                
            base, j1, j2 = map(int, parts)
            payload = f"RAW {base} {j1} {j2}\n"
            ser.write(payload.encode('utf-8'))
            print("Command sent.")
        except ValueError:
            print("Invalid input. Use integers.")

if __name__ == "__main__":
    main()
