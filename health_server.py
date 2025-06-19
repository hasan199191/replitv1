from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json
import os
from datetime import datetime
import logging

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Log all requests
        logging.info(f"Health server received request: {self.path}")
        
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
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'Twitter Bot is running')
            
        elif self.path == '/' or self.path == '':
            # Root path - basic info - 404 SORUNU ÇÖZÜMÜ
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            root_data = {
                'service': 'Twitter Bot',
                'status': 'running',
                'message': 'Bot is active and posting tweets',
                'endpoints': {
                    '/health': 'Health check endpoint',
                    '/status': 'Status endpoint'
                },
                'last_updated': datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(root_data, indent=2).encode())
            
        else:
            # 404 for unknown paths
            logging.warning(f"Unknown path requested: {self.path}")
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_data = {
                'error': 'Not Found',
                'path': self.path,
                'available_endpoints': ['/health', '/status', '/']
            }
            
            self.wfile.write(json.dumps(error_data, indent=2).encode())
    
    def log_message(self, format, *args):
        # Enable HTTP logging for debugging
        logging.info(f"HTTP: {format % args}")

def start_health_server():
    """Start health check server in background thread"""
    try:
        port = int(os.environ.get('PORT', 10000))
        
        # Create server
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        
        def run_server():
            try:
                logging.info(f"🏥 Health server starting on 0.0.0.0:{port}")
                logging.info(f"🔗 Available endpoints:")
                logging.info(f"   - http://0.0.0.0:{port}/health")
                logging.info(f"   - http://0.0.0.0:{port}/status")
                logging.info(f"   - http://0.0.0.0:{port}/")
                server.serve_forever()
            except Exception as e:
                logging.error(f"❌ Health server error: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        logging.info(f"✅ Health server thread started on port {port}")
        return server
        
    except Exception as e:
        logging.error(f"❌ Failed to start health server: {e}")
        return None
