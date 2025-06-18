from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json
import os
from datetime import datetime
import logging

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'service': 'twitter-bot',
                'version': '2.0.0',
                'uptime': 'running',
                'components': {
                    'browser': 'active',
                    'content_generator': 'active',
                    'email_handler': 'active'
                }
            }
            
            self.wfile.write(json.dumps(health_data, indent=2).encode())
        elif self.path == '/status':
            # Additional status endpoint
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Twitter Bot is running')
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        # Suppress default HTTP logging to avoid spam
        pass

def start_health_server():
    """Start health check server in background thread"""
    try:
        port = int(os.environ.get('PORT', 10000))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        
        def run_server():
            try:
                logging.info(f"Health server starting on port {port}")
                server.serve_forever()
            except Exception as e:
                logging.error(f"Health server error: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        logging.info(f"✅ Health server started on port {port}")
        return server
        
    except Exception as e:
        logging.error(f"❌ Failed to start health server: {e}")
        return None
