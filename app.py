
from flask import Flask, render_template
from backend.detection import HIDDetector
import threading
import csv
import os

app = Flask(__name__)

# Initialize the detector
detector = HIDDetector()

def start_detector():
    """Start the HID detection in a separate thread"""
    try:
        print("Starting HID Detector...")
        detector.start_detection()  # Fixed method name
    except Exception as e:
        print(f"Error starting detector: {e}")

# Start the detector in a separate thread
detector_thread = threading.Thread(target=start_detector, daemon=True)
detector_thread.start()
print("HID Detector thread started")

@app.route('/')
def index():
    return render_template('index.html')  

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')  


@app.route('/logs')
def logs():
    """Display detection logs"""
    # TO GET THE LOGS FILE PATH
    current_file_path = os.path.abspath(__file__)
    current_folder = os.path.dirname(current_file_path)
    logs_file_path = os.path.join(current_folder, "data", "logs.csv") 
    
    data = []
    try:
        with open(logs_file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Ensure the CSV has the expected columns
                if 'Date' in row and 'Time Stamp' in row and 'Command detected' in row:
                    data.append({
                        'date': row['Date'],
                        'time': row['Time Stamp'],
                        'command': row['Command detected']
                    })
    except FileNotFoundError:
        print(f"Error: File not found at {logs_file_path}")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    
    # Reverse to show newest first
    # data.reverse()
    return render_template('logs.html', logs=data)

@app.route('/recovery')
def recovery_page():
    return render_template('recovery.html')

@app.route('/initiate_recovery', methods=['POST'])
def initiate_recovery():
    """Initiate system recovery - stop detection temporarily"""
    print("Initiating recovery...")
    try:
        # Stop the detector temporarily
        detector.stop_detection()
        print("HID Detection stopped for recovery")
        
        # Here you could add code to run your restore_audio.py script
        # or other recovery actions
        
        return {'status': 'success', 'message': 'Recovery initiated'}, 200
    except Exception as e:
        print(f"Error during recovery: {e}")
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/restart_detection', methods=['POST'])
def restart_detection():
    """Restart the HID detection after recovery"""
    print("Restarting HID Detection...")
    try:
        # Reinitialize and restart the detector
        global detector
        detector = HIDDetector()
        detector_thread = threading.Thread(target=start_detector, daemon=True)
        detector_thread.start()
        return {'status': 'success', 'message': 'Detection restarted'}, 200
    except Exception as e:
        print(f"Error restarting detection: {e}")
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/status')
def status():
    """Get current detection status"""
    try:
        # Check if detector is running (simplified check)
        status = "running" if detector and detector.listener else "stopped"
        return {'status': status}, 200
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

if __name__ == '__main__':
    print("Starting HIDefender Flask Application...")
    app.run(debug=True, host='0.0.0.0', port=5000)
