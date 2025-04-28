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
valve_pwm = None

def setupGPIO():
    global valve_pwm
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

def turn_right():
    global is_turning, movement_direction
    is_turning = True
    print("Turning right")
    
    GPIO.output(in1_left, GPIO.HIGH)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.HIGH)
    
    time.sleep(0.75)
    stop_rover()
    is_turning = False
    if movement_direction == "FORWARD":
        move_forward()
    else:
        move_reverse()

def turn_left():
    global is_turning, movement_direction
    is_turning = True
    print("Turning left")
    
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.HIGH)
    GPIO.output(in3_right, GPIO.HIGH)
    GPIO.output(in4_right, GPIO.LOW)
    
    time.sleep(0.75)
    stop_rover()
    is_turning = False
    if movement_direction == "FORWARD":
        move_forward()
    else:
        move_reverse()

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

def calculate_distance_per_second():
    rps = rpm / 60
    return rps * wheel_circumference

def track_position():
    global distance_traveled, total_distance, is_running, rover_status, current_side, is_turning, movement_direction
    
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

def cleanup():
    global is_running, valve_pwm
    is_running = False
    if tracking_thread is not None:
        tracking_thread.join(1)
    stop_rover()
    stop_valve()
    if valve_pwm is not None:
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
        
        html = f'''<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Integrated Control System</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }}
                
                .container {{
                    max-width: 1000px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                    padding: 20px;
                }}
                
                header {{
                    background-color: #3498db;
                    color: white;
                    padding: 15px;
                    border-radius: 8px 8px 0 0;
                    text-align: center;
                    margin: -20px -20px 20px;
                }}
                
                h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                
                .control-panels {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                }}
                
                .control-panel {{
                    width: 48%;
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                }}
                
                .info-panel {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-around;
                    margin-bottom: 20px;
                }}
                
                .info-box {{
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 15px;
                    width: 45%;
                    text-align: center;
                    margin-bottom: 10px;
                }}
                
                .info-box h3 {{
                    margin-top: 0;
                    color: #3498db;
                }}
                
                .info-value {{
                    font-size: 20px;
                    font-weight: bold;
                }}
                
                .button-group {{
                    display: flex;
                    justify-content: center;
                    margin: 20px 0;
                }}
                
                button {{
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 10px 20px;
                    margin: 0 10px;
                    font-size: 16px;
                    cursor: pointer;
                }}
                
                button.start {{
                    background-color: #2ecc71;
                }}
                
                button.stop {{
                    background-color: #e74c3c;
                }}
                
                button.reverse {{
                    background-color: #f39c12;
                }}
                
                button.open {{
                    background-color: #2ecc71;
                }}
                
                button.close {{
                    background-color: #3498db;
                }}
                
                .slider-container {{
                    text-align: center;
                    margin-top: 20px;
                }}
                
                .slider {{
                    width: 80%;
                    max-width: 400px;
                }}
                
                .perimeter-display {{
                    margin-top: 30px;
                    text-align: center;
                }}
                
                .perimeter-box {{
                    display: inline-block;
                    width: 200px;
                    height: 200px;
                    border: 3px solid #3498db;
                    position: relative;
                }}
                
                .rover-indicator {{
                    position: absolute;
                    width: 20px;
                    height: 20px;
                    background-color: red;
                    border-radius: 50%;
                    transform: translate(-50%, -50%);
                }}
                
                footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #7f8c8d;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Integrated Control System</h1>
                </header>
                
                <div class="info-panel">
                    <div class="info-box">
                        <h3>Temperature</h3>
                        <div class="info-value"><span id="temperature">{getTemperature()}</span></div>
                    </div>
                    
                    <div class="info-box">
                        <h3>Rover Status</h3>
                        <div class="info-value">
                            <span id="roverStatus">{rover_status}</span>
                        </div>
                    </div>
                    
                    <div class="info-box">
                        <h3>Valve Status</h3>
                        <div class="info-value">
                            <span id="valveStatus">{valve_status}</span>
                        </div>
                    </div>
                    
                    <div class="info-box">
                        <h3>Direction</h3>
                        <div class="info-value">
                            <span id="direction">{movement_direction}</span>
                        </div>
                    </div>
                </div>
                
                <div class="control-panels">
                    <div class="control-panel">
                        <h2 style="text-align:center">Rover Controls</h2>
                        
                        <div class="button-group">
                            <button onclick="sendCommand('ROVER_START')" class="start">Start Rover</button>
                            <button onclick="sendCommand('ROVER_STOP')" class="stop">Stop Rover</button>
                            <button onclick="sendCommand('ROVER_REVERSE')" class="reverse">Reverse Direction</button>
                        </div>
                        
                        <div class="slider-container">
                            <label for="speed">Motor Speed:</label>
                            <input type="range" min="0" max="100" value="{current_speed}" class="slider" id="speed" 
                                   oninput="document.getElementById('speedValue').textContent = this.value + '%'"
                                   onchange="sendSpeed(this.value)">
                            <div>Current speed: <span id="speedValue">{current_speed}%</span></div>
                        </div>
                        
                        <div class="perimeter-display">
                            <h3>Position in Perimeter</h3>
                            <div class="perimeter-box">
                                <div id="roverPosition" class="rover-indicator" style="left: 0%; top: 0%;"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="control-panel">
                        <h2 style="text-align:center">Valve Controls</h2>
                        
                        <div class="button-group">
                            <button onclick="sendCommand('VALVE_OPEN')" class="open">Open Valve</button>
                            <button onclick="sendCommand('VALVE_CLOSE')" class="close">Close Valve</button>
                            <button onclick="sendCommand('VALVE_STOP')" class="stop">Stop Valve</button>
                        </div>
                    </div>
                </div>
                
                <footer>
                    <p>Integrated Control System</p>
                </footer>
            </div>
            
            <script>
                // Update status every 1 second
                setInterval(function() {{
                    fetch('/status')
                        .then(response => response.json())
                        .then(data => {{
                            document.getElementById('temperature').textContent = data.temperature;
                            document.getElementById('roverStatus').textContent = data.rover_status;
                            document.getElementById('valveStatus').textContent = data.valve_status;
                            document.getElementById('direction').textContent = data.direction;
                            document.getElementById('speedValue').textContent = data.speed + '%';
                            
                            // Update rover position indicator if needed
                            if (data.currentDistance !== undefined && data.currentSide !== undefined) {{
                                updateRoverPosition(data.currentSide, data.currentDistance);
                            }}
                        }})
                        .catch(error => console.error('Error fetching data:', error));
                }}, 1000);
                
                function updateRoverPosition(side, distance) {{
                    const percentComplete = Math.min(distance / 100, 1) * 100;
                    let left = 0;
                    let top = 0;
                    
                    // Calculate position based on current side and distance
                    switch(parseInt(side)) {{
                        case 1: // Top edge, left to right
                            left = percentComplete;
                            top = 0;
                            break;
                        case 2: // Right edge, top to bottom
                            left = 100;
                            top = percentComplete;
                            break;
                        case 3: // Bottom edge, right to left
                            left = 100 - percentComplete;
                            top = 100;
                            break;
                        case 4: // Left edge, bottom to top
                            left = 0;
                            top = 100 - percentComplete;
                            break;
                    }}
                    
                    const rover = document.getElementById('roverPosition');
                    rover.style.left = left + '%';
                    rover.style.top = top + '%';
                }}
                
                function sendCommand(command) {{
                    fetch('/', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/x-www-form-urlencoded',
                        }},
                        body: 'command=' + command
                    }})
                    .catch(error => console.error('Error sending command:', error));
                }}
                
                function sendSpeed(speed) {{
                    fetch('/', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/x-www-form-urlencoded',
                        }},
                        body: 'speed=' + speed
                    }})
                    .catch(error => console.error('Error sending speed:', error));
                }}
            </script>
        </body>
        </html>'''
        
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        global rover_status, current_speed, movement_direction, is_running, tracking_thread
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode("utf-8")
        
        if 'command=' in post_data:
            command = post_data.split('=')[1]
            
            # Rover commands
            if command == 'ROVER_START':
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
            
            elif command == 'ROVER_STOP':
                stop_rover()
            
            elif command == 'ROVER_REVERSE':
                movement_direction = "REVERSE" if movement_direction == "FORWARD" else "FORWARD"
                if rover_status == "RUNNING":
                    if movement_direction == "REVERSE":
                        move_reverse()
                    else:
                        move_forward()
            
            # Valve commands
            elif command == 'VALVE_OPEN':
                open_valve()
            
            elif command == 'VALVE_CLOSE':
                close_valve()
            
            elif command == 'VALVE_STOP':
                stop_valve()
        
        elif 'speed=' in post_data:
            current_speed = int(post_data.split('=')[1])
            print(f"Speed value changed to {current_speed}% (for display only)")
        
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
