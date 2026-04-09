from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(package='arm_pkg', executable='webcam_publisher', respawn=True, respawn_delay=2.0),
        Node(package='arm_pkg', executable='detection', respawn=True, respawn_delay=2.0),
        Node(package='arm_pkg', executable='arm_controller', respawn=True, respawn_delay=2.0),
        Node(package='arm_pkg', executable='web', respawn=True, respawn_delay=2.0)
    ])
