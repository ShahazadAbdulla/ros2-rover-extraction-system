#include <ESP32Servo.h>

Servo baseServo;
Servo j1Servo;
Servo j2Servo;

// Define your physical GPIO pins here
const int BASE_PIN = 13;
const int J1_PIN = 12;
const int J2_PIN = 14;

void setup() {
  Serial.begin(115200);
  
  // Allocate timers for ESP32 PWM
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  baseServo.setPeriodHertz(50);
  j1Servo.setPeriodHertz(50);
  j2Servo.setPeriodHertz(50);

  baseServo.attach(BASE_PIN, 500, 2400);
  j1Servo.attach(J1_PIN, 500, 2400);
  j2Servo.attach(J2_PIN, 500, 2400);

  // Lock to IDLE on boot
  baseServo.write(90);
  j1Servo.write(90);
  j2Servo.write(90);
  
  Serial.println("ESP32 Ready");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    // CALIBRATION OVERRIDE
    if (command.startsWith("RAW")) {
      int base, j1, j2;
      if (sscanf(command.c_str(), "RAW %d %d %d", &base, &j1, &j2) == 3) {
        baseServo.write(base);
        j1Servo.write(j1);
        j2Servo.write(j2);
        delay(500); 
        Serial.println("DONE"); // Handshake back to ROS
      }
    }
    
    // FULL AUTO EXTRACTION
    else if (command.startsWith("EXTRACT")) {
      int base, j1, j2, is_flat, bio;
      if (sscanf(command.c_str(), "EXTRACT %d %d %d %d %d", &base, &j1, &j2, &is_flat, &bio) == 5) {
        
        // 1. Approach Hover
        baseServo.write(base);
        delay(300);
        
        // 2. The Strike
        j1Servo.write(j1);
        j2Servo.write(j2);
        delay(400);

        // 3. The L-Retraction (Flat logic to clear the chassis)
        if (is_flat == 1) {
          baseServo.write(base > 90 ? base - 20 : base + 20); // Drag motion
          delay(300);
        }

        // 4. Dump Routing
        j1Servo.write(90); // Lift payload
        delay(200);
        if (bio == 1) {
           baseServo.write(180); // Drop in Bio Bin
        } else {
           baseServo.write(0);   // Drop in Non-Bio Bin
        }
        delay(800);

        // 5. Reset to IDLE
        baseServo.write(90);
        j1Servo.write(90);
        j2Servo.write(90);
        delay(300);

        // Release the ROS 2 lock
        Serial.println("DONE");
      }
    }
  }
}
