# Autonomous Fixed-Cell Extraction System

An industrial-grade, headless edge AI appliance designed for zero-touch autonomous waste sorting. Built on ROS 2 (Humble) and deployed on an Nvidia Jetson, this system utilizes Llama 4 Vision for dynamic classification and an Experiential KNN Matrix for kinematics.

Designed for field resiliency, the architecture features aggressive hardware watchdogs, dynamic V4L2 symlink resolution, and self-recovering `systemd` daemon management.

<img width="720" height="1280" alt="image" src="https://github.com/user-attachments/assets/a9b3dbdf-4a4e-43fc-a808-fbb476b2ca69" />

## ⚙️ Hardware Stack
* **Compute:** Nvidia Jetson (ARM64 Ubuntu)
* **Microcontroller:** ESP32 (PWM Kinematics Execution)
* **Vision:** Logitech C270 HD Webcam
* **Actuation:** 3-Axis Servo Configuration
* **Networking:** Tailscale VPN + Mobile Hotspot Priority Override

## 🧠 System Architecture

The system operates entirely headless, orchestrated by a robust `core.launch.py` with strict respawn policies. 

### 1. The ROS 2 Nodes
* **`webcam_publisher`:** Captures and publishes 640x480 video. Features a custom Python symlink resolver that dynamically maps `udev` aliases (e.g., `/dev/webcam_c270`) to raw integers, bypassing Nvidia's GStreamer backend traps and forcing raw Video4Linux2 (V4L2) kernel access.
* **`detection` (Vision AI):** A headless processing node that applies a 40-frame Background Subtractor (MOG2) stability lock to filter motion blur. Upon target lock, it crops the ROI and fires a threaded asynchronous payload to Groq's API (Llama 4 Vision) for classification (Biological vs. Non-Biological) and structural analysis (Flat vs. Tall).
* **`arm_controller` (Kinematics):** Rejects brittle Inverse Kinematics math in favor of an **Experiential KNN Matrix** using Inverse Distance Weighting (IDW) across 8 physically verified strike points. Integrates dynamic "L-Retraction" logic based on the target's physical profile to safely clear the chassis.
* **`web` (Operator Dashboard):** A Flask-based UI served over `0.0.0.0:5000`. Exposes a zero-latency video feed, target JSON data, and passwordless kernel-level system controls (Reboot, Poweroff, Recalibrate).

### 2. Edge Resiliency Features
* **Hardware Watchdogs:** If the ESP32 serial connection drops mid-extraction, the controller node executes `os._exit(1)`, forcing the ROS 2 Launch Manager to violently kill and respawn the process.
* **Zero-Touch Boot:** Managed by `rover_core.service` using `Type=idle` with a 15-second safety buffer to guarantee OS networking and Tailscale tunnels are stabilized before Llama 4 and ROS initialize.
* **Static Hardware Binding:** Custom `udev` rules ensure the Linux kernel permanently locks the camera and ESP32 to predictable symlinks, regardless of USB enumeration order.

---

<img width="777" height="547" alt="image" src="https://github.com/user-attachments/assets/34fa93b1-b020-465a-b52d-c90a3ae0dab5" />


## 🚀 Deployment Guide

This system is designed as a plug-and-play appliance. 

### 1. Hardware Binding (`udev`)
Copy the rules to the Linux device manager and reload the kernel:
```bash
sudo cp deploy/99-rover-hardware.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

2. Sudo Bypass (Web UI Controls)

To allow the Flask dashboard to reboot the Jetson or restart the nodes without a password, append this to /etc/sudoers using sudo visudo:
Plaintext

innovizta ALL=(ALL) NOPASSWD: /usr/sbin/reboot, /usr/sbin/poweroff, /bin/systemctl restart rover_core.service

3. Build the ROS 2 Workspace

Install dependencies and compile for the ARM64 architecture:
Bash

pip3 install -r requirements.txt
colcon build --packages-select arm_pkg

4. Arm the System Daemon

Lock the startup script into the bootloader:
Bash

sudo cp deploy/rover_core.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rover_core.service
sudo systemctl start rover_core.service

⚠️ Hardware Wiring Mandate

DO NOT power the servos directly from the ESP32. Drawing stall current through the microcontroller will collapse the voltage, cause a brown-out, sever the USB serial connection, and trigger a safety shutdown of the kinematics node.

    Provide a dedicated 5V/6V power supply to the servo VCC/GND.

    CRITICAL: You must bridge the ESP32 GND to the external power supply GND. Floating grounds will result in catastrophic servo jitter.

    Signal pins map to GPIO 13 (Base), 12 (J1), and 14 (J2).

Engineered for strict hardware fault tolerance and autonomous recovery.
