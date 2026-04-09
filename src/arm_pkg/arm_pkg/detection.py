import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import json
import base64
import os
import requests
import threading

# You MUST set this in your Jetson terminal: export GROQ_API_KEY="your_key_here"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "MISSING_KEY")

class VisionDetectionNode(Node):
    def __init__(self):
        super().__init__('detection')
        self.bridge = CvBridge()
        
        self.sub_cam = self.create_subscription(Image, 'camera/image_raw', self.image_callback, 10)
        self.sub_ui = self.create_subscription(String, '/ui/command', self.ui_callback, 10)
        self.pub_target = self.create_publisher(String, '/vision/target_data', 10)
        
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=50, detectShadows=False)
        self.roi = [190, 380, 220, 450] # [y1, y2, x1, x2]
        
        self.stability_counter = 0
        self.locked_target = None
        self.processing = False

    def ui_callback(self, msg):
        if msg.data == "RECALIBRATE":
            self.get_logger().info("Remote Command: Recalibrating Empty Table...")
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=50, detectShadows=False)
            self.stability_counter = 0
            self.processing = False

    def image_callback(self, msg):
        if self.processing:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        roi_frame = frame[self.roi[0]:self.roi[1], self.roi[2]:self.roi[3]]
        
        fg_mask = self.bg_subtractor.apply(roi_frame)
        _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        target_found = False
        for c in contours:
            if cv2.contourArea(c) > 800: # Minimum trash size
                x, y, w, h = cv2.boundingRect(c)
                cx = self.roi[2] + x + (w // 2)
                cy = self.roi[0] + y + (h // 2)
                
                self.stability_counter += 1
                target_found = True
                
                if self.stability_counter > 40:
                    self.get_logger().info(f"Target Locked at {cx}, {cy}. Firing Llama 4...")
                    self.locked_target = {"cx": cx, "cy": cy, "crop": roi_frame[y:y+h, x:x+w]}
                    self.processing = True
                    self.stability_counter = 0
                    threading.Thread(target=self.infer_target).start()
                break
                
        if not target_found:
            self.stability_counter = max(0, self.stability_counter - 1)

    def infer_target(self):
        try:
            _, buffer = cv2.imencode('.jpg', self.locked_target["crop"])
            b64_image = base64.b64encode(buffer).decode('utf-8')
            
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.2-90b-vision-preview", # Update to Llama 4 when Groq updates endpoint
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Classify this waste into exactly one of these classes: [Plastic, Paper, Metal, Biological, Unknown]. Respond strictly with a JSON object containing 'name' (string), 'bio_status' (boolean, true if Biological), and 'is_flat' (boolean, true if paper/cardboard/flat plastic)."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                        ]
                    }
                ],
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
            result = json.loads(response.json()['choices'][0]['message']['content'])
            
            result["cx"] = self.locked_target["cx"]
            result["cy"] = self.locked_target["cy"]
            
            msg = String()
            msg.data = json.dumps(result)
            self.pub_target.publish(msg)
            
        except Exception as e:
            self.get_logger().error(f"Inference failed: {e}")
            
        self.processing = False

def main(args=None):
    rclpy.init(args=args)
    node = VisionDetectionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
