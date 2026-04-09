import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import os
import time

class WebcamPublisher(Node):
    def __init__(self):
        super().__init__('webcam_publisher')
        self.camera_index = "/dev/webcam_c270"
        
        # The Dynamic Resolver
        try:
            real_path = os.path.realpath(self.camera_index)
            self.cam_int = int(real_path.replace('/dev/video', ''))
        except Exception as e:
            self.get_logger().error(f"Failed to resolve camera integer: {e}")
            self.cam_int = 0 

        self.publisher_ = self.create_publisher(Image, 'camera/image_raw', 10)
        self.timer = self.create_timer(0.033, self.timer_callback)
        self.cap = cv2.VideoCapture(self.cam_int, cv2.CAP_V4L2)
        self.bridge = CvBridge()

    def timer_callback(self):
        if not self.cap.isOpened():
            self.get_logger().warn("Camera missing. Attempting hardware reconnect...")
            self.cap = cv2.VideoCapture(self.cam_int, cv2.CAP_V4L2)
            time.sleep(1)
            return

        ret, frame = self.cap.read()
        if ret:
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = WebcamPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
