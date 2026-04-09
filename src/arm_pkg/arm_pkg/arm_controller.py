import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import serial
import json
import os
import math

# YOUR 8-POINT CALIBRATION MATRIX
# Format: {"cx": int, "cy": int, "base": int, "j1": int, "j2": int}
# YOU MUST OVERRIDE THESE WITH YOUR ACTUAL HARDWARE ANGLES
KNN_MATRIX = [
    {"cx": 220, "cy": 190, "base": 45, "j1": 120, "j2": 60}, # Top Left
    {"cx": 335, "cy": 190, "base": 90, "j1": 130, "j2": 70}, # Top Center
    {"cx": 450, "cy": 190, "base": 135,"j1": 120, "j2": 60}, # Top Right
    {"cx": 220, "cy": 285, "base": 45, "j1": 90,  "j2": 45}, # Mid Left
    {"cx": 450, "cy": 285, "base": 135,"j1": 90,  "j2": 45}, # Mid Right
    {"cx": 220, "cy": 380, "base": 45, "j1": 60,  "j2": 30}, # Bottom Left
    {"cx": 335, "cy": 380, "base": 90, "j1": 70,  "j2": 40}, # Bottom Center
    {"cx": 450, "cy": 380, "base": 135,"j1": 60,  "j2": 30}  # Bottom Right
]

class ArmControllerNode(Node):
    def __init__(self):
        super().__init__('arm_controller')
        self.sub = self.create_subscription(String, '/vision/target_data', self.target_callback, 10)
        
        try:
            self.ser = serial.Serial('/dev/esp32', 115200, timeout=1)
            self.get_logger().info("ESP32 Connected. Tucked to IDLE.")
        except serial.SerialException:
            self.get_logger().error("ESP32 missing on boot. Committing suicide to trigger respawn.")
            os._exit(1)

    def calculate_idw_angles(self, target_cx, target_cy):
        # Inverse Distance Weighting interpolation
        weight_sum = 0
        base_sum, j1_sum, j2_sum = 0, 0, 0
        
        for p in KNN_MATRIX:
            dist = math.sqrt((target_cx - p["cx"])**2 + (target_cy - p["cy"])**2)
            if dist < 1.0: # Exact match prevention
                return p["base"], p["j1"], p["j2"]
            
            weight = 1.0 / (dist ** 2) # Closer points have exponentially higher weight
            weight_sum += weight
            base_sum += p["base"] * weight
            j1_sum += p["j1"] * weight
            j2_sum += p["j2"] * weight
            
        return int(base_sum/weight_sum), int(j1_sum/weight_sum), int(j2_sum/weight_sum)

    def target_callback(self, msg):
        try:
            data = json.loads(msg.data)
            self.get_logger().info(f"Extracting: {data['name']}. Flat: {data['is_flat']}")
            
            base, j1, j2 = self.calculate_idw_angles(data['cx'], data['cy'])
            
            # Send coordinates to ESP32 firmware
            command = f"EXTRACT {base} {j1} {j2} {int(data['is_flat'])} {int(data['bio_status'])}\n"
            self.ser.write(command.encode('utf-8'))
            
            # Wait for ESP32 to finish physical movement and reply "DONE"
            response = self.ser.readline().decode('utf-8').strip()
            if "DONE" not in response:
                self.get_logger().warn("Unexpected response from ESP32.")
            
        except serial.SerialException:
            self.get_logger().error("Serial dropped mid-execution! Forcing respawn.")
            os._exit(1)
            
def main(args=None):
    rclpy.init(args=args)
    node = ArmControllerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
