# Agronym Solutions

Agronym Solutions focuses on developing smart agricultural devices by integrating hardware and software to revolutionize farming practices. Our primary goal is to increase productivity, promote eco-friendly agriculture, and enable remote farming with reduced manual labor, making advanced agricultural solutions accessible to a wide audience.

## Key Features

- **Automated Irrigation System**: Features a unique mechanism capable of operating pre-existing PVC ball valves already installed in fields. Unlike solenoid valves, this eliminates the need to replace existing plumbing systems, reducing costs significantly.
- **Web Control Interface**: A software interface allows users to control the valve mechanisms remotely via a web application.
- **Smart Automation**: The system can be set to an automated mode, utilizing sensors to control the irrigation mechanism.
- **Smart Weed Management & Surveillance**: Employs computer vision engineering and AI for a comprehensive software approach to weed management and field surveillance.

## Project Structure

The project includes Python scripts for integrating various hardware components and setting up the control interface:

- `agrvalve.py`, `acronymvalve.py`: Scripts for managing the automated valve mechanisms.
- `webmotor.py`: Handles the web interface integration with motor controls.
- `l298n.py`: Module for controlling motors using the L298N motor driver.
- `rover*.py`: Scripts related to the autonomous/remote-controlled agricultural rover.
- `integrate*.py`: Main integration scripts bringing together hardware control and software logic.

## Uniqueness

Our innovated mechanism for operating PVC ball valves means there is no need to replace the existing plumbing infrastructure in agricultural fields. It can be easily installed on pre-existing valves, significantly reducing the financial barrier to entry for smart farming technologies. This provides seamless integration of smart automation into agriculture, revolutionizing farming with greater precision and efficiency.
