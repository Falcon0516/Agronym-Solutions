import RPi.GPIO as GPIO
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

host_name = 'localhost'  # IP Address of Raspberry Pi
host_port = 5000
in1 = 24
in2 = 23
en = 25

# Global variable to track valve status
valve_status = "STOPPED"
current_speed = 75  # Default speed value

def setupGPIO():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(in1, GPIO.OUT)
    GPIO.setup(in2, GPIO.OUT)
    GPIO.setup(en, GPIO.OUT)
    GPIO.output(in1, GPIO.LOW)
    GPIO.output(in2, GPIO.LOW)

def getTemperature():
    temp = os.popen("/opt/vc/bin/vcgencmd measure_temp").read()
    return temp[5:].strip()  # Remove 'temp=' and strip whitespace

class MyServer(BaseHTTPRequestHandler):
    p = None  # Define PWM object at class level
    
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
    def do_GET(self):
        global valve_status, current_speed
        
        # Serve CSS file
        if self.path == '/style.css':
            self.send_response(200)
            self.send_header('Content-type', 'text/css')
            self.end_headers()
            with open('style.css', 'rb') as file:
                self.wfile.write(file.read())
            return
        
        # Serve JavaScript file
        elif self.path == '/script.js':
            self.send_response(200)
            self.send_header('Content-type', 'text/javascript')
            self.end_headers()
            with open('script.js', 'rb') as file:
                self.wfile.write(file.read())
            return
            
        # Serve temperature data as JSON for AJAX requests
        elif self.path == '/temp':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            temp = getTemperature()
            self.wfile.write(f'{{"temperature": "{temp}", "status": "{valve_status}"}}'.encode("utf-8"))
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
            <title>Raspberry Pi Valve Control</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }
                
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 10px;
                    box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
                    padding: 20px;
                }
                
                header {
                    background-color: #3498db;
                    color: white;
                    padding: 20px;
                    border-radius: 10px 10px 0 0;
                    text-align: center;
                    margin: -20px -20px 20px;
                }
                
                h1 {
                    margin: 0;
                    font-size: 28px;
                }
                
                .info-panel {
                    display: flex;
                    justify-content: space-around;
                    margin-bottom: 30px;
                    flex-wrap: wrap;
                }
                
                .info-box {
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 15px;
                    width: 40%;
                    min-width: 200px;
                    margin: 10px;
                    text-align: center;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                }
                
                .info-box h3 {
                    margin-top: 0;
                    color: #3498db;
                }
                
                .info-value {
                    font-size: 24px;
                    font-weight: bold;
                }
                
                .control-panel {
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                }
                
                .control-panel h2 {
                    margin-top: 0;
                    color: #3498db;
                    text-align: center;
                }
                
                .button-group {
                    display: flex;
                    justify-content: center;
                    margin-bottom: 20px;
                    flex-wrap: wrap;
                }
                
                button {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 12px 25px;
                    margin: 0 10px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background-color 0.3s;
                    min-width: 100px;
                }
                
                button:hover {
                    background-color: #2980b9;
                }
                
                button.open {
                    background-color: #2ecc71;
                }
                
                button.open:hover {
                    background-color: #27ae60;
                }
                
                button.close {
                    background-color: #e74c3c;
                }
                
                button.close:hover {
                    background-color: #c0392b;
                }
                
                button.stop {
                    background-color: #95a5a6;
                }
                
                button.stop:hover {
                    background-color: #7f8c8d;
                }
                
                .slider-container {
                    text-align: center;
                    margin-top: 30px;
                }
                
                .slider-container label {
                    display: block;
                    margin-bottom: 10px;
                    font-weight: bold;
                }
                
                .slider {
                    width: 100%;
                    max-width: 400px;
                }
                
                .speed-value {
                    font-weight: bold;
                    color: #3498db;
                    margin-top: 10px;
                }
                
                .status {
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                
                .status.open {
                    background-color: rgba(46, 204, 113, 0.2);
                    color: #27ae60;
                }
                
                .status.close {
                    background-color: rgba(231, 76, 60, 0.2);
                    color: #c0392b;
                }
                
                .status.stopped {
                    background-color: rgba(149, 165, 166, 0.2);
                    color: #7f8c8d;
                }
                
                footer {
                    text-align: center;
                    margin-top: 30px;
                    color: #7f8c8d;
                    font-size: 14px;
                }
                
                @media (max-width: 600px) {
                    .info-box {
                        width: 100%;
                        margin: 10px 0;
                    }
                }
            </style>
            <script>
                window.onload = function() {
                    // Initial speed value from server
                    document.getElementById('speed').value = ''' + str(current_speed) + ''';
                    document.getElementById('speedValue').textContent = ''' + str(current_speed) + ''' + '%';
                    
                    // Update temperature every 2 seconds
                    setInterval(updateTemperature, 2000);
                    
                    // Add event listeners to buttons
                    document.getElementById('openValve').addEventListener('click', function() {
                        sendCommand('ON');
                    });
                    
                    document.getElementById('closeValve').addEventListener('click', function() {
                        sendCommand('OFF');
                    });
                    
                    document.getElementById('stopValve').addEventListener('click', function() {
                        sendCommand('Stop');
                    });
                    
                    // Add event listener to speed slider
                    document.getElementById('speed').addEventListener('input', function() {
                        document.getElementById('speedValue').textContent = this.value + '%';
                    });
                    
                    document.getElementById('speed').addEventListener('change', function() {
                        sendSpeed(this.value);
                    });
                }
                
                function updateTemperature() {
                    fetch('/temp')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('temperature').textContent = data.temperature;
                            
                            // Update status indicator
                            const statusElement = document.getElementById('status');
                            statusElement.textContent = data.status;
                            
                            // Remove all status classes
                            statusElement.classList.remove('open', 'close', 'stopped');
                            
                            // Add appropriate class based on status
                            if (data.status === 'OPEN') {
                                statusElement.classList.add('open');
                            } else if (data.status === 'CLOSED') {
                                statusElement.classList.add('close');
                            } else {
                                statusElement.classList.add('stopped');
                            }
                        });
                }
                
                function sendCommand(command) {
                    fetch('/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: 'submit=' + command
                    }).then(response => {
                        // Update immediately after command
                        updateTemperature();
                    });
                }
                
                function sendSpeed(speed) {
                    fetch('/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: 'speed=' + speed
                    });
                }
            </script>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Raspberry Pi Valve Control System</h1>
                </header>
                
                <div class="info-panel">
                    <div class="info-box">
                        <h3>Temperature</h3>
                        <div class="info-value"><span id="temperature">''' + temp + '''</span></div>
                    </div>
                    
                    <div class="info-box">
                        <h3>Valve Status</h3>
                        <div class="info-value">
                            <span id="status" class="status stopped">''' + valve_status + '''</span>
                        </div>
                    </div>
                </div>
                
                <div class="control-panel">
                    <h2>Valve Controls</h2>
                    
                    <div class="button-group">
                        <button id="openValve" class="open">Open Valve</button>
                        <button id="closeValve" class="close">Close Valve</button>
                        <button id="stopValve" class="stop">Emergency Stop</button>
                    </div>
                    
                    <div class="slider-container">
                        <label for="speed">Motor Speed:</label>
                        <input type="range" min="0" max="100" value="''' + str(current_speed) + '''" class="slider" id="speed">
                        <div class="speed-value">Current speed: <span id="speedValue">''' + str(current_speed) + '''%</span></div>
                    </div>
                </div>
                
                <footer>
                    <p>Raspberry Pi GPIO Control System &copy; ''' + time.strftime("%Y") + '''</p>
                </footer>
            </div>
        </body>
        </html>
        '''
        
        self.wfile.write(html.encode("utf-8"))
    
    def do_POST(self):
        global valve_status, current_speed
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode("utf-8")
        
        # Handle motor control commands
        if 'submit=' in post_data:
            command = post_data.split("=")[1]
            setupGPIO()
            
            # Initialize PWM only if it's not already initialized
            if MyServer.p is None:
                MyServer.p = GPIO.PWM(en, 1000)
                MyServer.p.start(0)  # Start with duty cycle 0
                
            if command == 'ON':
                print("Opening valve (forward)")
                GPIO.output(in1, GPIO.HIGH)
                GPIO.output(in2, GPIO.LOW)
                MyServer.p.ChangeDutyCycle(current_speed)
                valve_status = "OPEN"
            elif command == 'OFF':
                print("Closing valve (backward)")
                GPIO.output(in1, GPIO.LOW)
                GPIO.output(in2, GPIO.HIGH)
                MyServer.p.ChangeDutyCycle(current_speed)
                valve_status = "CLOSED"
            else:
                print("Emergency Stop")
                GPIO.output(in1, GPIO.LOW)
                GPIO.output(in2, GPIO.LOW)
                MyServer.p.ChangeDutyCycle(0)
                valve_status = "STOPPED"
        
        # Handle speed change
        elif 'speed=' in post_data:
            new_speed = int(post_data.split("=")[1])
            current_speed = new_speed
            
            # Apply new speed if motor is running
            if valve_status != "STOPPED" and MyServer.p is not None:
                MyServer.p.ChangeDutyCycle(current_speed)
                print(f"Speed changed to {current_speed}%")
        
        # Redirect back to the main page
        self.send_response(303)
        self.send_header('Content-type', 'text/html')
        self.send_header('Location', '/')
        self.end_headers()

# Make sure the PWM object is cleaned up properly
def cleanup():
    if MyServer.p is not None:
        MyServer.p.stop()
    GPIO.cleanup()
    print("PWM stopped and GPIO cleaned up")

# Main entry point
if __name__ == '__main__':
    setupGPIO()
    http_server = HTTPServer((host_name, host_port), MyServer)
    print("Server Started - %s:%s" % (host_name, host_port))
    
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()
        cleanup()
        print("Server stopped")
