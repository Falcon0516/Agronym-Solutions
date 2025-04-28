import RPi.GPIO as GPIO
import os
import time
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Server configuration
host_name = '0.0.0.0'
host_port = 3000

# Motor driver pins
in1_left = 17
in2_left = 22
in3_right = 23
in4_right = 24

# Global variables
rover_status = "STOPPED"
current_speed = 100
movement_direction = "FORWARD"
is_turning = False

# Rover physical parameters
wheel_circumference = 22  # cm
rpm = 30  # motor rpm
perimeter_size = 100  # 1m = 100cm

# Position tracking
distance_traveled = 0
total_distance = 0
current_side = 1
is_running = False
tracking_thread = None

def setupGPIO():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(in1_left, GPIO.OUT)
    GPIO.setup(in2_left, GPIO.OUT)
    GPIO.setup(in3_right, GPIO.OUT)
    GPIO.setup(in4_right, GPIO.OUT)
    stop_rover()

def getTemperature():
    try:
        temp = os.popen("/opt/vc/bin/vcgencmd measure_temp").read()
        return temp.strip() if temp else "N/A"
    except:
        return "N/A"

def calculate_distance_per_second():
    rps = rpm / 60
    return rps * wheel_circumference

def turn_right():
    global is_turning
    is_turning = True
    print("Turning right")
    
    GPIO.output(in1_left, GPIO.HIGH)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.HIGH)
    
    time.sleep(0.75)
    stop_rover()
    is_turning = False
    move_forward() if movement_direction == "FORWARD" else move_reverse()

def turn_left():
    global is_turning
    is_turning = True
    print("Turning left")
    
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.HIGH)
    GPIO.output(in3_right, GPIO.HIGH)
    GPIO.output(in4_right, GPIO.LOW)
    
    time.sleep(0.75)
    stop_rover()
    is_turning = False
    move_forward() if movement_direction == "FORWARD" else move_reverse()

def track_position():
    global distance_traveled, total_distance, is_running, rover_status, current_side, is_turning
    
    distance_per_second = calculate_distance_per_second()
    
    while is_running:
        if rover_status == "RUNNING" and not is_turning:
            increment = distance_per_second if movement_direction == "FORWARD" else -distance_per_second
            distance_traveled += increment
            total_distance += abs(increment)
            
            if (movement_direction == "FORWARD" and distance_traveled >= perimeter_size) or \
               (movement_direction == "REVERSE" and distance_traveled <= 0):
                
                print(f"Completed side {current_side}")
                distance_traveled = 0 if movement_direction == "FORWARD" else perimeter_size
                
                if movement_direction == "FORWARD":
                    current_side = current_side + 1 if current_side < 4 else 1
                    threading.Thread(target=turn_right).start()
                else:
                    current_side = current_side - 1 if current_side > 1 else 4
                    threading.Thread(target=turn_left).start()
        
        time.sleep(1)

def move_forward():
    global rover_status
    print("Moving forward")
    GPIO.output(in1_left, GPIO.HIGH)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.HIGH)
    GPIO.output(in4_right, GPIO.LOW)
    rover_status = "RUNNING"

def move_reverse():
    global rover_status
    print("Moving reverse")
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.HIGH)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.HIGH)
    rover_status = "RUNNING"

def stop_rover():
    global rover_status
    print("Stopping rover")
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.LOW)
    rover_status = "STOPPED"

def cleanup():
    global is_running
    is_running = False
    if tracking_thread is not None:
        tracking_thread.join(2)
    stop_rover()
    GPIO.cleanup()
    print("GPIO cleaned up")

class RoverServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status_data = {
                "temperature": getTemperature(),
                "status": rover_status,
                "direction": movement_direction,
                "speed": current_speed,
                "currentDistance": round(distance_traveled, 2),
                "totalDistance": round(total_distance, 2),
                "currentSide": current_side
            }
            self.wfile.write(str(status_data).replace("'", '"').encode("utf-8"))
            return
            
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = f"""<!DOCTYPE html>
        <html><head><title>Rover Control</title>
        <style>body {{ font-family: Arial; text-align: center; margin-top: 50px; }}
        button {{ padding: 10px 20px; font-size: 16px; margin: 10px; }}</style>
        </head><body>
        <h1>Rover Control</h1>
        <p>Status: {rover_status} | Direction: {movement_direction}</p>
        <button onclick="sendCommand('START')">Start</button>
        <button onclick="sendCommand('STOP')">Stop</button>
        <button onclick="sendCommand('REVERSE')">Reverse</button>
        <script>
        function sendCommand(cmd) {{
            fetch('/', {{ method: 'POST', headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
            body: 'command=' + cmd }});
        }}
        </script></body></html>"""
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        global rover_status, current_speed, movement_direction, is_running, tracking_thread
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode("utf-8")
        
        if 'command=' in post_data:
            command = post_data.split('=')[1]
            
            if command == 'START':
                if not hasattr(GPIO, "_initialized"):
                    setupGPIO()
                    GPIO._initialized = True
                
                if movement_direction == "FORWARD":
                    move_forward()
                else:
                    move_reverse()
                
                if not is_running:
                    is_running = True
                    tracking_thread = threading.Thread(target=track_position)
                    tracking_thread.daemon = True
                    tracking_thread.start()
            
            elif command == 'STOP':
                stop_rover()
            
            elif command == 'REVERSE':
                movement_direction = "REVERSE" if movement_direction == "FORWARD" else "FORWARD"
                if rover_status == "RUNNING":
                    move_reverse() if movement_direction == "REVERSE" else move_forward()
        
        self.send_response(303)
        self.send_header('Location', '/')
        self.end_headers()

if __name__ == '__main__':
    try:
        setupGPIO()
        server = HTTPServer((host_name, host_port), RoverServer)
        print(f"Server started at {host_name}:{host_port}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cleanup()
