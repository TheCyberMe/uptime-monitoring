import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

UPTIME_ROBOT_API_KEY = os.environ.get('UPTIME_ROBOT_API_KEY')
UPTIME_ROBOT_API_URL = "https://api.uptimerobot.com/v2"

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "ISP Monitor"})

@app.route('/isp-status', methods=['GET'])
def isp_status():
    """Returns ISP status as JSON"""
    try:
        payload = {
            'api_key': UPTIME_ROBOT_API_KEY,
            'format': 'json'
        }
        
        response = requests.post(
            f"{UPTIME_ROBOT_API_URL}/getMonitors",
            data=payload,
            timeout=10
        )
        
        data = response.json()
        
        if data.get('stat') != 'ok':
            return jsonify({'error': data.get('error')}), 400
        
        # Format data for Grafana
        isp_data = []
        for monitor in data.get('monitors', []):
            isp_data.append({
                'name': monitor.get('friendly_name'),
                'status': 'UP' if monitor.get('status') == 2 else 'DOWN',
                'status_code': monitor.get('status'),
                'url': monitor.get('url')
            })
        
        return jsonify({'data': isp_data, 'total': len(isp_data)})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)

