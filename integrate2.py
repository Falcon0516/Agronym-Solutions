import RPi.GPIO as GPIO
import os
import time
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Server configuration
host_name = '0.0.0.0'
host_port = 5000

# Rover motor pins
in1_left = 17
in2_left = 27
in3_right = 11
in4_right = 9
en_left = 25  # PWM pin for left motor
en_right = 8  # PWM pin for right motor

# Valve control pins
valve_in1 = 24
valve_in2 = 23
valve_en = 25  # Shared with en_left since they can't use same pin

# Global variables
rover_status = "STOPPED"
valve_status = "STOPPED"
current_speed = 75
valve_speed = 75
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

# PWM objects
pwm_left = None
pwm_right = None
valve_pwm = None

def setupGPIO():
    global pwm_left, pwm_right, valve_pwm
    
    GPIO.setmode(GPIO.BCM)
    
    # Rover motor setup
    GPIO.setup(in1_left, GPIO.OUT)
    GPIO.setup(in2_left, GPIO.OUT)
    GPIO.setup(in3_right, GPIO.OUT)
    GPIO.setup(in4_right, GPIO.OUT)
    GPIO.setup(en_left, GPIO.OUT)
    GPIO.setup(en_right, GPIO.OUT)
    
    # Valve control setup
    GPIO.setup(valve_in1, GPIO.OUT)
    GPIO.setup(valve_in2, GPIO.OUT)
    GPIO.setup(valve_en, GPIO.OUT)
    
    # Initialize PWM for rover motors
    pwm_left = GPIO.PWM(en_left, 1000)
    pwm_right = GPIO.PWM(en_right, 1000)
    pwm_left.start(0)
    pwm_right.start(0)
    
    # Initialize PWM for valve (shared with left motor enable)
    valve_pwm = pwm_left  # Share the PWM object
    
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
    pwm_left.ChangeDutyCycle(current_speed)
    pwm_right.ChangeDutyCycle(current_speed)
    rover_status = "RUNNING"

def move_reverse():
    global rover_status
    print("Rover moving reverse")
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.HIGH)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.HIGH)
    pwm_left.ChangeDutyCycle(current_speed)
    pwm_right.ChangeDutyCycle(current_speed)
    rover_status = "RUNNING"

def stop_rover():
    global rover_status
    print("Rover stopping")
    pwm_left.ChangeDutyCycle(0)
    pwm_right.ChangeDutyCycle(0)
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
    pwm_left.ChangeDutyCycle(current_speed)
    pwm_right.ChangeDutyCycle(current_speed)
    
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
    pwm_left.ChangeDutyCycle(current_speed)
    pwm_right.ChangeDutyCycle(current_speed)
    
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
    valve_pwm.ChangeDutyCycle(valve_speed)
    valve_status = "OPEN"

def close_valve():
    global valve_status
    print("Closing valve")
    GPIO.output(valve_in1, GPIO.LOW)
    GPIO.output(valve_in2, GPIO.HIGH)
    valve_pwm.ChangeDutyCycle(valve_speed)
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
    global is_running
    is_running = False
    if tracking_thread is not None:
        tracking_thread.join(1)
    stop_rover()
    stop_valve()
    if pwm_left is not None:
        pwm_left.stop()
    if pwm_right is not None:
        pwm_right.stop()
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
                "valve_speed": valve_speed,
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
            <title>Raspberry Pi Valve & Rover Control</title>
            <style>
                /* [Previous CSS styles remain exactly the same...] */
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Raspberry Pi Valve & Rover Control System</h1>
                </header>
                
                <div class="tabs">
                    <div class="tab active" onclick="changeTab('rover-tab')">Rover Control</div>
                    <div class="tab" onclick="changeTab('valve-tab')">Valve Control</div>
                </div>
                
                <div id="rover-tab" class="tab-content active">
                    <!-- [Rover control panel HTML remains exactly the same...] -->
                </div>
                
                <div id="valve-tab" class="tab-content">
                    <div class="control-panel">
                        <h2>Valve Control System</h2>
                        
                        <div class="valve-status" id="valve-status">Valve Status: {valve_status}</div>
                        
                        <div class="button-group">
                            <button onclick="sendCommand('VALVE_OPEN')" class="start">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M18 15l-6-6-6 6"></path>
                                </svg>
                                Open Valve
                            </button>
                            <button onclick="sendCommand('VALVE_CLOSE')" class="reverse">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M6 9l6 6 6-6"></path>
                                </svg>
                                Close Valve
                            </button>
                            <button onclick="sendCommand('VALVE_STOP')" class="stop">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>
                                </svg>
                                Emergency Stop
                            </button>
                        </div>
                        
                        <div class="slider-container">
                            <label for="valve-speed">Valve Speed:</label>
                            <input type="range" min="0" max="100" value="{valve_speed}" class="slider" id="valve-speed" 
                                oninput="document.getElementById('valveSpeedValue').textContent = this.value + '%'"
                                onchange="sendValveSpeed(this.value)">
                            <div>Current valve speed: <span id="valveSpeedValue">{valve_speed}%</span></div>
                        </div>
                    </div>
                </div>
                
                <footer>
                    <p>Raspberry Pi Valve & Rover Control System</p>
                    <p>Current System Temperature: <span id="footer-temp">{getTemperature()}</span></p>
                </footer>
            </div>
            
            <script>
                // Tab switching functionality
                function changeTab(tabId) {{
                    document.querySelectorAll('.tab-content').forEach(tab => {{
                        tab.classList.remove('active');
                    }});
                    
                    document.querySelectorAll('.tab').forEach(tab => {{
                        tab.classList.remove('active');
                    }});
                    
                    document.getElementById(tabId).classList.add('active');
                    
                    const index = tabId === 'rover-tab' ? 0 : 1;
                    document.querySelectorAll('.tab')[index].classList.add('active');
                }}
                
                // Update status every 1 second
                setInterval(function() {{
                    fetch('/status')
                        .then(response => response.json())
                        .then(data => {{
                            // Update rover status
                            document.getElementById('temperature').textContent = data.temperature;
                            document.getElementById('footer-temp').textContent = data.temperature;
                            document.getElementById('status').textContent = data.rover_status;
                            document.getElementById('direction').textContent = data.direction;
                            document.getElementById('side').textContent = data.currentSide;
                            document.getElementById('currentDistance').textContent = data.currentDistance;
                            document.getElementById('totalDistance').textContent = data.totalDistance;
                            document.getElementById('speedValue').textContent = data.speed + '%';
                            
                            // Update valve status
                            document.getElementById('valve-status').textContent = 'Valve Status: ' + data.valve_status;
                            document.getElementById('valveSpeedValue').textContent = data.valve_speed + '%';
                            
                            // Update UI based on valve status
                            const valveStatusElement = document.getElementById('valve-status');
                            valveStatusElement.className = 'valve-status';
                            if (data.valve_status === 'OPEN') {{
                                valveStatusElement.classList.add('open');
                            }} else if (data.valve_status === 'CLOSED') {{
                                valveStatusElement.classList.add('closed');
                            }}
                            
                            // Update rover position indicator
                            updateRoverPosition(data.currentSide, data.currentDistance);
                            
                            // Update side indicators
                            updateSideIndicators(data.currentSide);
                        }})
                        .catch(error => console.error('Error fetching data:', error));
                }}, 1000);
                
                function updateRoverPosition(side, distance) {{
                    const percentComplete = Math.min(distance / 100, 1) * 100;
                    let left = 0;
                    let top = 0;
                    
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
                
                function updateSideIndicators(currentSide) {{
                    for (let i = 1; i <= 4; i++) {{
                        const indicator = document.getElementById('side' + i);
                        indicator.className = 'side-indicator';
                        if (i == currentSide) {{
                            indicator.classList.add('active');
                        }}
                    }}
                }}
                
                function sendCommand(command) {{
                    fetch('/', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                        body: 'command=' + command
                    }}).catch(error => console.error('Error sending command:', error));
                }}
                
                function sendSpeed(speed) {{
                    fetch('/', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                        body: 'speed=' + speed
                    }}).catch(error => console.error('Error sending speed:', error));
                }}
                
                function sendValveSpeed(speed) {{
                    fetch('/', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                        body: 'valve_speed=' + speed
                    }}).catch(error => console.error('Error sending valve speed:', error));
                }}
            </script>
        </body>
        </html>'''
        
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        global rover_status, current_speed, valve_speed, movement_direction, is_running, tracking_thread
        
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
            print(f"Rover speed changed to {current_speed}%")
        
        elif 'valve_speed=' in post_data:
            valve_speed = int(post_data.split('=')[1])
            print(f"Valve speed changed to {valve_speed}%")
        
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
