import RPi.GPIO as GPIO
import os
import time
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Server configuration
host_name = '0.0.0.0'  # Listen on all network interfaces
host_port = 5000

# Motor driver pins (L298N)
# Left motor
in1_left = 24
in2_left = 23
en_left = 25

# Right motor
in3_right = 17
in4_right = 27
en_right = 22

# Global variables
rover_status = "STOPPED"  # Current rover status
current_speed = 100  # Default speed (%)
movement_direction = "FORWARD"  # Default direction (FORWARD or REVERSE)
is_turning = False  # Flag to indicate if the rover is currently turning

# Rover physical parameters
wheel_circumference = 22  # cm
rpm = 30  # motor rpm
perimeter_size = 100  # 1m = 100cm

# Position tracking
distance_traveled = 0  # Current distance in cm
total_distance = 0  # Total distance traveled
current_side = 1  # Current side of the square (1-4)
is_running = False
tracking_thread = None

def setupGPIO():
    GPIO.setmode(GPIO.BCM)
    
    # Motor pins setup
    GPIO.setup(in1_left, GPIO.OUT)
    GPIO.setup(in2_left, GPIO.OUT)
    GPIO.setup(en_left, GPIO.OUT)
    
    GPIO.setup(in3_right, GPIO.OUT)
    GPIO.setup(in4_right, GPIO.OUT)
    GPIO.setup(en_right, GPIO.OUT)
    
    # Initial state - motors stopped
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.LOW)

# Function to get system temperature
def getTemperature():
    try:
        temp = os.popen("/opt/vc/bin/vcgencmd measure_temp").read()
        if temp:
            return temp.strip()
        return "N/A"
    except:
        return "N/A"

# Calculate distance traveled per second based on rpm and wheel circumference
def calculate_distance_per_second():
    # rpm to rps (revolutions per second)
    rps = rpm / 60
    # distance per second = rps * circumference
    return rps * wheel_circumference  # cm per second

# Turn the rover right (90 degrees)
def turn_right():
    global is_turning
    
    is_turning = True
    print("Turning right (90 degrees)")
    
    # Set motors to turn right (left motor forward, right motor backward)
    GPIO.output(in1_left, GPIO.HIGH)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.HIGH)
    
    # Set motor speed
    left_pwm.ChangeDutyCycle(current_speed)
    right_pwm.ChangeDutyCycle(current_speed)
    
    # Calculate time needed for a 90-degree turn
    # This depends on your rover's physical characteristics and might need tuning
    # For a typical small rover, about 0.5-1 second is often enough for a 90-degree turn
    turn_time = 0.75  # seconds for 90-degree turn
    
    # Wait for the turn to complete
    time.sleep(turn_time)
    
    # Resume normal movement
    is_turning = False
    if movement_direction == "FORWARD":
        move_forward(current_speed)
    else:
        move_reverse(current_speed)

# Turn the rover left (90 degrees)
def turn_left():
    global is_turning
    
    is_turning = True
    print("Turning left (90 degrees)")
    
    # Set motors to turn left (left motor backward, right motor forward)
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.HIGH)
    GPIO.output(in3_right, GPIO.HIGH)
    GPIO.output(in4_right, GPIO.LOW)
    
    # Set motor speed
    left_pwm.ChangeDutyCycle(current_speed)
    right_pwm.ChangeDutyCycle(current_speed)
    
    # Calculate time needed for a 90-degree turn
    turn_time = 0.75  # seconds for 90-degree turn
    
    # Wait for the turn to complete
    time.sleep(turn_time)
    
    # Resume normal movement
    is_turning = False
    if movement_direction == "FORWARD":
        move_forward(current_speed)
    else:
        move_reverse(current_speed)

# Position tracking function to be run in a separate thread
def track_position():
    global distance_traveled, total_distance, is_running, rover_status, current_side, is_turning
    
    distance_per_second = calculate_distance_per_second()
    
    while is_running:
        if rover_status == "RUNNING" and not is_turning:
            # Update distance traveled on current side
            if movement_direction == "FORWARD":
                increment = distance_per_second
            else:  # REVERSE
                increment = -distance_per_second
                
            distance_traveled += increment
            total_distance += abs(increment)  # Total distance is always positive
            
            # Check if we've reached the end of current side
            if movement_direction == "FORWARD" and distance_traveled >= perimeter_size:
                print(f"Completed side {current_side} of perimeter")
                
                # Reset distance counter for next side
                distance_traveled = 0
                
                # Turn right at corner
                if current_side < 4:
                    current_side += 1
                else:
                    current_side = 1
                
                # Execute turn in main thread to avoid conflicts
                threading.Thread(target=turn_right).start()
                
            # For reverse direction, check if we've reached the beginning of current side
            elif movement_direction == "REVERSE" and distance_traveled <= 0:
                print(f"Completed side {current_side} of perimeter in reverse")
                
                # Reset distance counter for next side
                distance_traveled = perimeter_size
                
                # Move to previous side
                if current_side > 1:
                    current_side -= 1
                else:
                    current_side = 4
                
                # Execute turn in main thread to avoid conflicts
                threading.Thread(target=turn_left).start()
        
        # Update every second
        time.sleep(1)

# Motor control functions
def move_forward(speed_percent):
    global rover_status
    
    # Set motor direction for forward movement
    GPIO.output(in1_left, GPIO.HIGH)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.HIGH)
    GPIO.output(in4_right, GPIO.LOW)
    
    # Set motor speed
    left_pwm.ChangeDutyCycle(speed_percent)
    right_pwm.ChangeDutyCycle(speed_percent)
    
    rover_status = "RUNNING"
    
def move_reverse(speed_percent):
    global rover_status
    
    # Set motor direction for reverse movement
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.HIGH)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.HIGH)
    
    # Set motor speed
    left_pwm.ChangeDutyCycle(speed_percent)
    right_pwm.ChangeDutyCycle(speed_percent)
    
    rover_status = "RUNNING"

def stop_rover():
    global rover_status
    
    # Stop motors
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.LOW)
    
    # Set speed to 0
    left_pwm.ChangeDutyCycle(0)
    right_pwm.ChangeDutyCycle(0)
    
    rover_status = "STOPPED"

class RoverServer(BaseHTTPRequestHandler):
    # Class variables for PWM objects
    left_pwm = None
    right_pwm = None
    
    def log_message(self, format, *args):
        # Override to show more detailed logs
        print(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        global rover_status, current_speed, movement_direction, distance_traveled, total_distance, current_side
        
        print(f"GET request received: {self.path}")  # Debug log
        
        # Serve status data as JSON for AJAX requests
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # Add CORS header
            self.end_headers()
            temp = getTemperature()
            status_data = {
                "temperature": temp,
                "status": rover_status,
                "direction": movement_direction,
                "speed": current_speed,
                "currentDistance": round(distance_traveled, 2),
                "totalDistance": round(total_distance, 2),
                "currentSide": current_side
            }
            
            json_response = "{"
            for key, value in status_data.items():
                if isinstance(value, str):
                    json_response += f'"{key}": "{value}", '
                else:
                    json_response += f'"{key}": {value}, '
            json_response = json_response.rstrip(", ") + "}"
            
            self.wfile.write(json_response.encode("utf-8"))
            return
            
        # Serve main page
        temp = getTemperature()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Raspberry Pi Rover Control</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }
                
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                    padding: 20px;
                }
                
                header {
                    background-color: #3498db;
                    color: white;
                    padding: 15px;
                    border-radius: 8px 8px 0 0;
                    text-align: center;
                    margin: -20px -20px 20px;
                }
                
                h1 {
                    margin: 0;
                    font-size: 24px;
                }
                
                .info-panel {
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-around;
                    margin-bottom: 20px;
                }
                
                .info-box {
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 15px;
                    width: 45%;
                    text-align: center;
                    margin-bottom: 10px;
                }
                
                .info-box h3 {
                    margin-top: 0;
                    color: #3498db;
                }
                
                .info-value {
                    font-size: 20px;
                    font-weight: bold;
                }
                
                .control-panel {
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                }
                
                .button-group {
                    display: flex;
                    justify-content: center;
                    margin: 20px 0;
                }
                
                button {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 10px 20px;
                    margin: 0 10px;
                    font-size: 16px;
                    cursor: pointer;
                }
                
                button.start {
                    background-color: #2ecc71;
                }
                
                button.stop {
                    background-color: #e74c3c;
                }
                
                button.reverse {
                    background-color: #f39c12;
                }
                
                .slider-container {
                    text-align: center;
                    margin-top: 20px;
                }
                
                .slider {
                    width: 80%;
                    max-width: 400px;
                }
                
                .perimeter-display {
                    margin-top: 30px;
                    text-align: center;
                }
                
                .perimeter-box {
                    display: inline-block;
                    width: 200px;
                    height: 200px;
                    border: 3px solid #3498db;
                    position: relative;
                }
                
                .rover-indicator {
                    position: absolute;
                    width: 20px;
                    height: 20px;
                    background-color: red;
                    border-radius: 50%;
                    transform: translate(-50%, -50%);
                }
                
                footer {
                    text-align: center;
                    margin-top: 20px;
                    color: #7f8c8d;
                    font-size: 14px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Raspberry Pi Rover Control System</h1>
                </header>
                
                <div class="info-panel">
                    <div class="info-box">
                        <h3>Temperature</h3>
                        <div class="info-value"><span id="temperature">''' + temp + '''</span></div>
                    </div>
                    
                    <div class="info-box">
                        <h3>Rover Status</h3>
                        <div class="info-value">
                            <span id="status">''' + rover_status + '''</span>
                        </div>
                    </div>
                    
                    <div class="info-box">
                        <h3>Direction</h3>
                        <div class="info-value">
                            <span id="direction">''' + movement_direction + '''</span>
                        </div>
                    </div>
                    
                    <div class="info-box">
                        <h3>Side</h3>
                        <div class="info-value">
                            <span id="side">''' + str(current_side) + '''</span> of 4
                        </div>
                    </div>
                    
                    <div class="info-box">
                        <h3>Current Side Distance (cm)</h3>
                        <div class="info-value">
                            <span id="currentDistance">0.00</span> / 100.00
                        </div>
                    </div>
                    
                    <div class="info-box">
                        <h3>Total Distance (cm)</h3>
                        <div class="info-value">
                            <span id="totalDistance">0.00</span>
                        </div>
                    </div>
                </div>
                
                <div class="control-panel">
                    <h2 style="text-align:center">Rover Controls</h2>
                    
                    <div class="button-group">
                        <button onclick="sendCommand('START')" class="start">Start Rover</button>
                        <button onclick="sendCommand('STOP')" class="stop">Stop Rover</button>
                        <button onclick="sendCommand('REVERSE')" class="reverse">Reverse Direction</button>
                    </div>
                    
                    <div class="slider-container">
                        <label for="speed">Motor Speed:</label>
                        <input type="range" min="0" max="100" value="''' + str(current_speed) + '''" class="slider" id="speed" 
                               oninput="document.getElementById('speedValue').textContent = this.value + '%'"
                               onchange="sendSpeed(this.value)">
                        <div>Current speed: <span id="speedValue">''' + str(current_speed) + '''%</span></div>
                    </div>
                    
                    <div class="perimeter-display">
                        <h3>Position in Perimeter</h3>
                        <div class="perimeter-box">
                            <div id="roverPosition" class="rover-indicator" style="left: 0%; top: 0%;"></div>
                        </div>
                    </div>
                </div>
                
                <footer>
                    <p>Raspberry Pi Rover Control System</p>
                </footer>
            </div>
            
            <script>
                // Update status every 1 second
                setInterval(function() {
                    fetch('/status')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('temperature').textContent = data.temperature;
                            document.getElementById('status').textContent = data.status;
                            document.getElementById('direction').textContent = data.direction;
                            document.getElementById('side').textContent = data.currentSide;
                            document.getElementById('currentDistance').textContent = data.currentDistance;
                            document.getElementById('totalDistance').textContent = data.totalDistance;
                            
                            // Update rover position indicator on the square
                            updateRoverPosition(data.currentSide, data.currentDistance);
                        })
                        .catch(error => console.error('Error fetching data:', error));
                }, 1000);
                
                function updateRoverPosition(side, distance) {
                    const percentComplete = Math.min(distance / 100, 1) * 100;
                    let left = 0;
                    let top = 0;
                    
                    // Calculate position based on current side and distance
                    switch(parseInt(side)) {
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
                    }
                    
                    const rover = document.getElementById('roverPosition');
                    rover.style.left = left + '%';
                    rover.style.top = top + '%';
                }
                
                function sendCommand(command) {
                    fetch('/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: 'command=' + command
                    })
                    .catch(error => console.error('Error sending command:', error));
                }
                
                function sendSpeed(speed) {
                    fetch('/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: 'speed=' + speed
                    })
                    .catch(error => console.error('Error sending speed:', error));
                }
            </script>
        </body>
        </html>
        '''
        
        try:
            self.wfile.write(html.encode("utf-8"))
        except Exception as e:
            print(f"Error sending HTML response: {e}")
    
    def do_POST(self):
        global rover_status, current_speed, movement_direction, is_running, tracking_thread
        global distance_traveled, current_side
        
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode("utf-8")
            print(f"POST data received: {post_data}")  # Debug log
            
            # Handle rover control commands
            if 'command=' in post_data:
                command = post_data.split("=")[1]
                
                if command == 'START':
                    print("Starting rover")
                    # Initialize PWM if it's not already initialized
                    if RoverServer.left_pwm is None or RoverServer.right_pwm is None:
                        setupGPIO()
                        RoverServer.left_pwm = GPIO.PWM(en_left, 1000)
                        RoverServer.right_pwm = GPIO.PWM(en_right, 1000)
                        RoverServer.left_pwm.start(0)
                        RoverServer.right_pwm.start(0)
                    
                    # Set global references for use in control functions
                    global left_pwm, right_pwm
                    left_pwm = RoverServer.left_pwm
                    right_pwm = RoverServer.right_pwm
                    
                    # Start the rover in the current direction
                    if movement_direction == "FORWARD":
                        move_forward(current_speed)
                    else:
                        move_reverse(current_speed)
                    
                    # Start position tracking if not already running
                    if not is_running:
                        is_running = True
                        tracking_thread = threading.Thread(target=track_position)
                        tracking_thread.daemon = True
                        tracking_thread.start()
                
                elif command == 'STOP':
                    print("Stopping rover")
                    stop_rover()
                
                elif command == 'REVERSE':
                    print("Changing direction")
                    # Toggle direction
                    if movement_direction == "FORWARD":
                        movement_direction = "REVERSE"
                        # If currently running, apply the direction change
                        if rover_status == "RUNNING":
                            move_reverse(current_speed)
                    else:
                        movement_direction = "FORWARD"
                        # If currently running, apply the direction change
                        if rover_status == "RUNNING":
                            move_forward(current_speed)
            
            # Handle speed change
            elif 'speed=' in post_data:
                new_speed = int(post_data.split("=")[1])
                current_speed = new_speed
                
                # Apply new speed if motor is running
                if rover_status == "RUNNING":
                    left_pwm.ChangeDutyCycle(current_speed)
                    right_pwm.ChangeDutyCycle(current_speed)
                    print(f"Speed changed to {current_speed}%")
            
            # Redirect back to the main page
            self.send_response(303)
            self.send_header('Content-type', 'text/html')
            self.send_header('Location', '/')
            self.end_headers()
            
        except Exception as e:
            print(f"Error in POST handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Server error: {str(e)}".encode("utf-8"))

# Clean up function
def cleanup():
    global is_running
    
    # Stop the tracking thread
    is_running = False
    if tracking_thread is not None:
        tracking_thread.join(2)  # Wait up to 2 seconds for thread to finish
    
    # Stop PWM
    if hasattr(RoverServer, 'left_pwm') and RoverServer.left_pwm is not None:
        RoverServer.left_pwm.stop()
    if hasattr(RoverServer, 'right_pwm') and RoverServer.right_pwm is not None:
        RoverServer.right_pwm.stop()
    
    # Clean up GPIO
    GPIO.cleanup()
    print("PWM stopped and GPIO cleaned up")

# Main entry point
if __name__ == '__main__':
    try:
        server_address = (host_name, host_port)
        http_server = HTTPServer(server_address, RoverServer)
        print(f"Server Started - {host_name}:{host_port}")
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"Error starting server: {e}")
    finally:
        if 'http_server' in locals():
            http_server.server_close()
        cleanup()
        print("Server stopped")
