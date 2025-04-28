import RPi.GPIO as GPIO
import os
import time
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Server configuration
host_name = '0.0.0.0'  # Listen on all network interfaces
host_port = 3000

# Motor driver pins (Updated to match working code)
# Left motor
in1_left = 17
in2_left = 22

# Right motor
in3_right = 23
in4_right = 24

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
    GPIO.setup(in3_right, GPIO.OUT)
    GPIO.setup(in4_right, GPIO.OUT)
    
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
    
    # Time needed for a 90-degree turn (adjusted based on working code)
    turn_time = 0.75  # seconds for 90-degree turn
    
    # Wait for the turn to complete
    time.sleep(turn_time)
    
    # Stop motors after turn
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.LOW)
    
    # Resume normal movement
    is_turning = False
    if movement_direction == "FORWARD":
        move_forward()
    else:
        move_reverse()

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
    
    # Time needed for a 90-degree turn
    turn_time = 0.75  # seconds for 90-degree turn
    
    # Wait for the turn to complete
    time.sleep(turn_time)
    
    # Stop motors after turn
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.LOW)
    
    # Resume normal movement
    is_turning = False
    if movement_direction == "FORWARD":
        move_forward()
    else:
        move_reverse()

# Motor control functions
def move_forward():
    global rover_status
    
    print("Moving forward")
    
    # Set motor direction for forward movement
    GPIO.output(in1_left, GPIO.HIGH)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.HIGH)  
    GPIO.output(in4_right, GPIO.LOW)
    
    rover_status = "RUNNING"
    
def move_reverse():
    global rover_status
    
    print("Moving reverse")
    
    # Set motor direction for reverse movement
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.HIGH)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.HIGH)
    
    rover_status = "RUNNING"

def stop_rover():
    global rover_status
    
    print("Stopping rover")
    
    # Stop motors
    GPIO.output(in1_left, GPIO.LOW)
    GPIO.output(in2_left, GPIO.LOW)
    GPIO.output(in3_right, GPIO.LOW)
    GPIO.output(in4_right, GPIO.LOW)
    
    rover_status = "STOPPED"

# ... [Rest of your code remains exactly the same, including the RoverServer class and main execution block] ...

# Main entry point
if __name__ == '__main__':
    try:
        # Initialize GPIO at startup but don't start motors
        setupGPIO()
        GPIO._initialized = True
        stop_rover()  # Explicitly stop the rover at startup
        
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
