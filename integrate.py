import RPi.GPIO as GPIO
import os
import time
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Server configuration
host_name = '0.0.0.0'
host_port = 3000

# Rover motor pins
in1_left = 17
in2_left = 27
in3_right = 11
in4_right = 9

# Valve control pins
valve_in1 = 24
valve_in2 = 23
valve_en = 25

# Global variables
rover_status = "STOPPED"
valve_status = "STOPPED"
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
    
    # Rover motor setup
    GPIO.setup(in1_left, GPIO.OUT)
    GPIO.setup(in2_left, GPIO.OUT)
    GPIO.setup(in3_right, GPIO.OUT)
    GPIO.setup(in4_right, GPIO.OUT)
    
    # Valve control setup
    GPIO.setup(valve_in1, GPIO.OUT)
    GPIO.setup(valve_in2, GPIO.OUT)
    GPIO.setup(valve_en, GPIO.OUT)
    
    # Initialize PWM for valve
    global valve_pwm
    valve_pwm = GPIO.PWM(valve_en, 1000)
    valve_pwm.start(0)
    
    # Initial state - all stopped
    stop_rover()
    stop_valve()

def getTemperature():
    try:
        temp = os.popen("/opt/vc/bin/vcgencmd measure_temp").read()
        return temp.strip() if temp else "N/A"
    except:
        return "N/A"

# Rover control functions
def move_forward():
    global rover_status
    print("Rover moving forward")
    GPIO.output(in1_left, GPIO.HIGH)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.HIGH)
    GPIO.output(in4_right, GPIO.LOW)
    rover_status = "RUNNING"

def move_reverse():
    global rover_status
    print("Rover moving reverse")
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.HIGH)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.HIGH)
    rover_status = "RUNNING"

def stop_rover():
    global rover_status
    print("Rover stopping")
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.LOW)
    rover_status = "STOPPED"

# Valve control functions
def open_valve():
    global valve_status
    print("Opening valve")
    GPIO.output(valve_in1, GPIO.HIGH)
    GPIO.output(valve_in2, GPIO.LOW)
    valve_pwm.ChangeDutyCycle(75)
    valve_status = "OPEN"

def close_valve():
    global valve_status
    print("Closing valve")
    GPIO.output(valve_in1, GPIO.LOW)
    GPIO.output(valve_in2, GPIO.HIGH)
    valve_pwm.ChangeDutyCycle(75)
    valve_status = "CLOSED"

def stop_valve():
    global valve_status
    print("Valve stopped")
    GPIO.output(valve_in1, GPIO.LOW)
    GPIO.output(valve_in2, GPIO.LOW)
    valve_pwm.ChangeDutyCycle(0)
    valve_status = "STOPPED"

def cleanup():
    global is_running
    is_running = False
    if tracking_thread is not None:
        tracking_thread.join(1)
    stop_rover()
    stop_valve()
    valve_pwm.stop()
    GPIO.cleanup()
    print("GPIO cleaned up")

class IntegratedServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status_data = {
                "temperature": getTemperature(),
                "rover_status": rover_status,
                "valve_status": valve_status,
                "direction": movement_direction,
                "currentDistance": round(distance_traveled, 2),
                "totalDistance": round(total_distance, 2)
            }
            self.wfile.write(str(status_data).replace("'", '"').encode("utf-8"))
            return
            
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = f"""<!DOCTYPE html>
        <html><head><title>Integrated Control System</title>
        <style>
            body {{ font-family: Arial; text-align: center; margin-top: 20px; }}
            .panel {{ 
                display: inline-block; 
                vertical-align: top; 
                margin: 10px; 
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
                width: 45%;
            }}
            h2 {{ color: #3498db; }}
            button {{ 
                padding: 10px 20px; 
                font-size: 16px; 
                margin: 5px; 
                border: none;
                color: white;
                border-radius: 5px;
                cursor: pointer;
            }}
            .rover-start {{ background-color: #2ecc71; }}
            .rover-stop {{ background-color: #e74c3c; }}
            .rover-reverse {{ background-color: #f39c12; }}
            .valve-open {{ background-color: #2ecc71; }}
            .valve-close {{ background-color: #3498db; }}
            .valve-stop {{ background-color: #e74c3c; }}
            .status {{ 
                padding: 10px; 
                margin: 10px; 
                border-radius: 5px;
                background-color: #f8f9fa;
            }}
        </style>
        </head>
        <body>
        <h1>Integrated Control System</h1>
        
        <div class="panel">
            <h2>Rover Control</h2>
            <div class="status">
                Status: <strong>{rover_status}</strong><br>
                Direction: <strong>{movement_direction}</strong>
            </div>
            <button class="rover-start" onclick="sendCommand('ROVER_START')">START</button>
            <button class="rover-stop" onclick="sendCommand('ROVER_STOP')">STOP</button>
            <button class="rover-reverse" onclick="sendCommand('ROVER_REVERSE')">REVERSE</button>
        </div>
        
        <div class="panel">
            <h2>Valve Control</h2>
            <div class="status">
                Status: <strong>{valve_status}</strong>
            </div>
            <button class="valve-open" onclick="sendCommand('VALVE_OPEN')">OPEN</button>
            <button class="valve-close" onclick="sendCommand('VALVE_CLOSE')">CLOSE</button>
            <button class="valve-stop" onclick="sendCommand('VALVE_STOP')">STOP</button>
        </div>
        
        <script>
        function sendCommand(cmd) {{
            fetch('/', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                body: 'command=' + cmd
            }});
        }}
        </script>
        </body></html>"""
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode("utf-8")
        
        if 'command=' in post_data:
            command = post_data.split('=')[1]
            
            # Rover commands
            if command == 'ROVER_START':
                if movement_direction == "FORWARD":
                    move_forward()
                else:
                    move_reverse()
            
            elif command == 'ROVER_STOP':
                stop_rover()
            
            elif command == 'ROVER_REVERSE':
                global movement_direction
                movement_direction = "REVERSE" if movement_direction == "FORWARD" else "FORWARD"
                if rover_status == "RUNNING":
                    move_reverse() if movement_direction == "REVERSE" else move_forward()
            
            # Valve commands
            elif command == 'VALVE_OPEN':
                open_valve()
            
            elif command == 'VALVE_CLOSE':
                close_valve()
            
            elif command == 'VALVE_STOP':
                stop_valve()
        
        self.send_response(303)
        self.send_header('Location', '/')
        self.end_headers()

if __name__ == '__main__':
    try:
        setupGPIO()
        server = HTTPServer((host_name, host_port), IntegratedServer)
        print(f"Server started at http://{host_name}:{host_port}")
        print("Press Ctrl+C to stop")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cleanup()
