import RPi.GPIO as GPIO
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# Change to '0.0.0.0' to allow external connections
host_name = '0.0.0.0'  # Listen on all network interfaces
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
    try:
        temp = os.popen("/opt/vc/bin/vcgencmd measure_temp").read()
        if temp:
            return temp.strip()
        return "N/A"  # Return N/A if command returns empty
    except:
        return "N/A"  # Return N/A if command fails

class MyServer(BaseHTTPRequestHandler):
    p = None  # Define PWM object at class level
    
    def log_message(self, format, *args):
        # Override to show more detailed logs
        print(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        global valve_status, current_speed
        
        print(f"GET request received: {self.path}")  # Debug log
        
        # Serve temperature data as JSON for AJAX requests
        if self.path == '/temp':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # Add CORS header
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
                    justify-content: space-around;
                    margin-bottom: 20px;
                }
                
                .info-box {
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 15px;
                    width: 45%;
                    text-align: center;
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
                
                button.open {
                    background-color: #2ecc71;
                }
                
                button.close {
                    background-color: #e74c3c;
                }
                
                button.stop {
                    background-color: #95a5a6;
                }
                
                .slider-container {
                    text-align: center;
                    margin-top: 20px;
                }
                
                .slider {
                    width: 80%;
                    max-width: 400px;
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
                            <span id="status">''' + valve_status + '''</span>
                        </div>
                    </div>
                </div>
                
                <div class="control-panel">
                    <h2 style="text-align:center">Valve Controls</h2>
                    
                    <div class="button-group">
                        <button onclick="sendCommand('ON')" class="open">Open Valve</button>
                        <button onclick="sendCommand('OFF')" class="close">Close Valve</button>
                        <button onclick="sendCommand('Stop')" class="stop">Emergency Stop</button>
                    </div>
                    
                    <div class="slider-container">
                        <label for="speed">Motor Speed:</label>
                        <input type="range" min="0" max="100" value="''' + str(current_speed) + '''" class="slider" id="speed" 
                               oninput="document.getElementById('speedValue').textContent = this.value + '%'"
                               onchange="sendSpeed(this.value)">
                        <div>Current speed: <span id="speedValue">''' + str(current_speed) + '''%</span></div>
                    </div>
                </div>
                
                <footer>
                    <p>Raspberry Pi GPIO Control System</p>
                </footer>
            </div>
            
            <script>
                // Update temperature every 5 seconds
                setInterval(function() {
                    fetch('/temp')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('temperature').textContent = data.temperature;
                            document.getElementById('status').textContent = data.status;
                        })
                        .catch(error => console.error('Error fetching data:', error));
                }, 5000);
                
                function sendCommand(command) {
                    fetch('/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: 'submit=' + command
                    })
                    .then(response => {
                        // Force update immediately after command
                        fetch('/temp')
                            .then(response => response.json())
                            .then(data => {
                                document.getElementById('temperature').textContent = data.temperature;
                                document.getElementById('status').textContent = data.status;
                            });
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
        global valve_status, current_speed
        
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode("utf-8")
            print(f"POST data received: {post_data}")  # Debug log
            
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
            
        except Exception as e:
            print(f"Error in POST handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Server error: {str(e)}".encode("utf-8"))

# Make sure the PWM object is cleaned up properly
def cleanup():
    if MyServer.p is not None:
        MyServer.p.stop()
    GPIO.cleanup()
    print("PWM stopped and GPIO cleaned up")

# Main entry point
if __name__ == '__main__':
    try:
        setupGPIO()
        server_address = (host_name, host_port)
        http_server = HTTPServer(server_address, MyServer)
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
