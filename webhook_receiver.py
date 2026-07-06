import os
import time
import requests
import threading
from flask import Flask, request
from prometheus_client import Gauge, start_http_server, generate_latest
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Prometheus metrics
isp_status = Gauge('isp_status', 'ISP Status (1=UP, 0=DOWN)', ['site', 'isp', 'name'])
isp_latency = Gauge('isp_latency_ms', 'ISP Latency in ms', ['site', 'isp', 'name'])

# UPDATE THIS: Map YOUR actual monitor names to sites
MONITOR_MAPPING = {
    # OAK (Oakland) - US Site 1
    'OAK-ISP01-12.125.210.25': {'site': 'oak', 'isp': 'isp01', 'name': 'OAK-ISP01'},
    'OAK-ISP03-104.6.68.1': {'site': 'oak', 'isp': 'isp03', 'name': 'OAK-ISP03'},
    'OAK-ISP02-50.145.122.161': {'site': 'oak', 'isp': 'isp02', 'name': 'OAK-ISP02'},
    
    # CVG (Cincinnati) - US Site 2
    'CVG-ISP01-66.117.201.145': {'site': 'cvg', 'isp': 'isp01', 'name': 'CVG-ISP01'},
    'CVG-ISP02-98.103.101.145': {'site': 'cvg', 'isp': 'isp02', 'name': 'CVG-ISP02'},
    
    # MAA (Chennai) - India Site 1
    'MAA-ISP01-183.82.247.137': {'site': 'maa', 'isp': 'isp01', 'name': 'MAA-ISP01'},
    'MAA-ISP02-125.18.81.233': {'site': 'maa', 'isp': 'isp02', 'name': 'MAA-ISP02'},
    
    # BLR (Banglore)- India Site 2
    'BLR0002-TATA TELECOMMUNICATION': {'site': 'helium', 'isp': 'tatatele', 'name': 'BLR-TATATELE'},
    'BLR0002-AIRTEL': {'site': 'helium', 'isp': 'airtel', 'name': 'BLR-AIRTEL'},
    'BLR0002-TATA COMMUNICATION': {'site': 'helium', 'isp': 'tata-comm', 'name': 'BLR-TATA-COMM'},
    
    # Azure
    'Azure-168.61.16.155': {'site': 'azure', 'isp': 'azure', 'name': 'Azure-VM'},
}

UPTIME_ROBOT_API_KEY = os.environ.get('UPTIME_ROBOT_API_KEY')
UPTIME_ROBOT_API_URL = "https://api.uptimerobot.com/v2"

def fetch_uptime_status():
    """Fetch all monitors from Uptime Robot API"""
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
            logging.error(f"API Error: {data.get('error', 'Unknown error')}")
            return
        
        for monitor in data.get('monitors', []):
            name = monitor.get('friendly_name')
            status = monitor.get('status')  # 2=UP, 9=DOWN
            
            if name in MONITOR_MAPPING:
                mapping = MONITOR_MAPPING[name]
                
                # Convert status: 2=UP (1), 9=DOWN (0)
                isp_up = 1 if status == 2 else 0
                
                # Update metrics
                isp_status.labels(
                    site=mapping['site'],
                    isp=mapping['isp'],
                    name=mapping['name']
                ).set(isp_up)
                
                status_text = 'UP' if isp_up else 'DOWN'
                logging.info(f"Updated: {name} → {status_text}")
            else:
                logging.warning(f"Monitor not in mapping: {name}")
        
        logging.info(f"Successfully fetched {len(data.get('monitors', []))} monitors")
    
    except Exception as e:
        logging.error(f"Error fetching Uptime Robot data: {str(e)}")

def background_update():
    """Background thread that fetches status every 5 minutes"""
    while True:
        try:
            fetch_uptime_status()
            time.sleep(300)  # 5 minutes
        except Exception as e:
            logging.error(f"Background update error: {str(e)}")
            time.sleep(60)

@app.route('/', methods=['GET'])
def health():
    return {'status': 'ok', 'service': 'Uptime Robot API Monitor'}, 200

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.route('/status', methods=['GET'])
def status():
    """View current ISP status as JSON"""
    return {'message': 'Check /metrics for Prometheus format'}, 200

if __name__ == '__main__':
    # Fetch status immediately on startup
    fetch_uptime_status()
    
    # Start background thread for periodic updates
    update_thread = threading.Thread(target=background_update, daemon=True)
    update_thread.start()
    
    # Start Prometheus metrics server
    start_http_server(5000)
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
