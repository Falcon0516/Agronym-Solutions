import RPi.GPIO as GPIO
import signal
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

# Set GPIO mode and define motor pins
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Motor A (Left Side)
MOTOR_A_PIN1 = 17  # Control pin 1
MOTOR_A_PIN2 = 22  # Control pin 2

# Motor B (Right Side)
MOTOR_B_PIN1 = 23  # Control pin 1
MOTOR_B_PIN2 = 24  # Control pin 2

# Setup pins
motor_pins = [MOTOR_A_PIN1, MOTOR_A_PIN2, MOTOR_B_PIN1, MOTOR_B_PIN2]
for pin in motor_pins:
    GPIO.setup(pin, GPIO.OUT)

def move_forward():
    print("Moving forward")
    GPIO.output(MOTOR_A_PIN1, GPIO.HIGH)
    GPIO.output(MOTOR_A_PIN2, GPIO.LOW)
    GPIO.output(MOTOR_B_PIN1, GPIO.HIGH)
    GPIO.output(MOTOR_B_PIN2, GPIO.LOW)

def move_backward():
    print("Moving backward")
    GPIO.output(MOTOR_A_PIN1, GPIO.LOW)
    GPIO.output(MOTOR_A_PIN2, GPIO.HIGH)
    GPIO.output(MOTOR_B_PIN1, GPIO.LOW)
    GPIO.output(MOTOR_B_PIN2, GPIO.HIGH)

def stop_motors():
    print("Stopping motors")
    GPIO.output(MOTOR_A_PIN1, GPIO.LOW)
    GPIO.output(MOTOR_A_PIN2, GPIO.LOW)
    GPIO.output(MOTOR_B_PIN1, GPIO.LOW)
    GPIO.output(MOTOR_B_PIN2, GPIO.LOW)

# Simple HTTP server to serve the control interface
class RoverControlHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        elif self.path == '/forward':
            move_forward()
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("Moving forward".encode())
        elif self.path == '/backward':
            move_backward()
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("Moving backward".encode())
        elif self.path == '/stop':
            stop_motors()
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("Stopped".encode())
        else:
            self.send_response(404)
            self.end_headers()

# Basic HTML interface
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Raspberry Pi Rover Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            text-align: center; 
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
        }
        .controls {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 30px 0;
        }
        .button {
            display: inline-block;
            padding: 15px 25px;
            font-size: 18px;
            cursor: pointer;
            text-align: center;
            color: white;
            border: none;
            border-radius: 8px;
            width: 150px;
            transition: transform 0.1s, opacity 0.2s;
        }
        .button:active {
            transform: scale(0.95);
        }
        .forward { background-color: #4CAF50; }
        .backward { background-color: #2196F3; }
        .stop { background-color: #f44336; }
        #status {
            margin-top: 20px;
            padding: 15px;
            font-weight: bold;
            background-color: #efefef;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Raspberry Pi Rover Control</h1>
        
        <div class="controls">
            <button class="button forward" onclick="sendCommand('forward')">Forward</button>
            <button class="button stop" onclick="sendCommand('stop')">Stop</button>
            <button class="button backward" onclick="sendCommand('backward')">Backward</button>
        </div>
        
        <div id="status">Status: Ready</div>
    </div>

    <script>
        function sendCommand(cmd) {
            fetch('/' + cmd)
                .then(response => response.text())
                .then(data => {
                    document.getElementById('status').innerText = 'Status: ' + data;
                })
                .catch(error => {
                    document.getElementById('status').innerText = 'Error: ' + error;
                });
        }
    </script>
</body>
</html>
"""

def cleanup():
    print("Cleaning up GPIO...")
    GPIO.cleanup()

def signal_handler(sig, frame):
    print('Shutting down gracefully...')
    cleanup()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start the web server on port 3000
    server_address = ('', 3000)
    httpd = HTTPServer(server_address, RoverControlHandler)
    
    print(f"Starting Rover Control Server on port 3000")
    print(f"Access the control panel at http://localhost:3000")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
