import RPi.GPIO as GPIO
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


host_name = 'localhost'  # IP Address of Raspberry Pi
host_port = 5000

in1 = 24
in2 = 23
en = 25


def setupGPIO():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(in1, GPIO.OUT)
    GPIO.setup(in2, GPIO.OUT)
    GPIO.setup(en, GPIO.OUT)
    GPIO.output(in1, GPIO.LOW)
    GPIO.output(in2, GPIO.LOW)


def getTemperature():
    temp = os.popen("/opt/vc/bin/vcgencmd measure_temp").read()
    return temp


class MyServer(BaseHTTPRequestHandler):
    p = None  # Define PWM object at class level

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def _redirect(self, path):
        self.send_response(303)
        self.send_header('Content-type', 'text/html')
        self.send_header('Location', path)
        self.end_headers()

    def do_GET(self):
        html = '''
        <html>
           <body style="width:960px; margin: 20px auto;">
           <h1>Welcome to my Raspberry Pi</h1>
           <p>Current GPU temperature is {}</p>
           <form action="/" method="POST">
               Automated valve control system
               <input type="submit" name="submit" value="ON">
               <input type="submit" name="submit" value="OFF">
               <input type="submit" name="submit" value="Stop">
           </form>
           </body>
           </html>
        '''
        temp = getTemperature()
        self.do_HEAD()
        self.wfile.write(html.format(temp[5:]).encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode("utf-8")
        post_data = post_data.split("=")[1]

        setupGPIO()

        # Initialize PWM only if it's not already initialized
        if MyServer.p is None:
            MyServer.p = GPIO.PWM(en, 1000)
            MyServer.p.start(0)  # Start with duty cycle 0

        if post_data == 'ON':
            print("Opening valve (forward)")
            GPIO.output(in1, GPIO.HIGH)
            GPIO.output(in2, GPIO.LOW)
            MyServer.p.ChangeDutyCycle(75)
            
            

        elif post_data == 'OFF':
            print("Closing valve (backward)")
            GPIO.output(in1, GPIO.LOW)
            GPIO.output(in2, GPIO.HIGH)
            MyServer.p.ChangeDutyCycle(75)
            
           

        else:
            print("Emergency Stop")
            GPIO.output(in1, GPIO.LOW)
            GPIO.output(in2, GPIO.LOW)
            MyServer.p.ChangeDutyCycle(0)

        self._redirect('/')  # Redirect back to the root URL


# Main entry point
if _name_ == '_main_':
    setupGPIO()
    http_server = HTTPServer((host_name, host_port), MyServer)
    print("Server Starts - %s:%s" % (host_name, host_port))

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()
        GPIO.cleanup()
        print("Server stopped and GPIO cleaned up")