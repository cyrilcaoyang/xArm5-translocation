from flask import Flask, render_template, jsonify
import yaml
from xarm.wrapper import XArmAPI

# Initialize Flask app
app = Flask(__name__)

# Load configuration
try:
    with open('settings/xarm_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    arm_ip = config['host']
except FileNotFoundError:
    print("Error: xarm_config.yaml not found. Please ensure the file exists in the settings directory.")
    exit(1)
except KeyError:
    print("Error: 'host' key not found in xarm_config.yaml.")
    exit(1)


# Initialize xArm API
# arm = XArmAPI(arm_ip)

@app.route('/')
def index():
    """Serve the main control page."""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 