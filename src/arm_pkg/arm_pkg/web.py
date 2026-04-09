import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from flask import Flask, render_template_string, jsonify
import threading
import subprocess

app = Flask(__name__)
ros_node = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Fixed-Cell Extraction UI</title></head>
<body style="background: #111; color: white; font-family: monospace; text-align: center;">
    <h2>SYSTEM MODE: FULL AUTO</h2>
    <img src="/api/video_feed" style="max-width: 600px; border: 2px solid #444;" />
    <br><br>
    <div style="margin-top: 20px;">
        <button onclick="fetch('/api/restart_ros', {method: 'POST'})" style="padding: 10px; background: #ffaa00; font-weight: bold;">RESTART PROGRAM</button>
        <button onclick="fetch('/api/recalibrate', {method: 'POST'})" style="padding: 10px; background: #0088ff; font-weight: bold; color: white;">RECALIBRATE CAMERA</button>
        <button onclick="fetch('/api/poweroff', {method: 'POST'})" style="padding: 10px; background: #8b0000; font-weight: bold; color: white;">SHUTDOWN SYSTEM</button>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/restart_ros', methods=['POST'])
def restart_ros():
    subprocess.Popen(["sudo", "systemctl", "restart", "rover_core.service"])
    return jsonify({"status": "restarting"})

@app.route('/api/poweroff', methods=['POST'])
def poweroff():
    subprocess.Popen(["sudo", "poweroff"])
    return jsonify({"status": "shutting_down"})

@app.route('/api/recalibrate', methods=['POST'])
def recalibrate():
    if ros_node:
        msg = String()
        msg.data = "RECALIBRATE"
        ros_node.ui_publisher.publish(msg)
    return jsonify({"status": "recalibrating"})

class WebUINode(Node):
    def __init__(self):
        super().__init__('web_ui_node')
        self.ui_publisher = self.create_publisher(String, '/ui/command', 10)

def main(args=None):
    global ros_node
    rclpy.init(args=args)
    ros_node = WebUINode()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, use_reloader=False)).start()
    rclpy.spin(ros_node)
    ros_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
