import os
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import SYMBOL

# Импортируем стратегию
try:
    from strategy import strategy
except ImportError:
    from strategies import strategy

logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для health check"""
    
    def do_GET(self):
        """Обработка GET запросов"""
        if self.path == '/health':
            self._handle_health_check()
        elif self.path == '/':
            self._handle_root()
        elif self.path == '/ping':
            self._handle_ping()
        else:
            self._handle_not_found()
    
    def _handle_health_check(self):
        """Обработка /health endpoint"""
        try:
            stats = strategy.get_stats()
            health_data = {
                "status": "healthy",
                "service": "crypto-bot",
                "symbol": SYMBOL,
                "total_signals": stats.get("total_signals", 0),
                "last_signal": stats.get("last_signal"),
                "last_price": stats.get("last_price"),
                "version": "1.0.0"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(health_data, indent=2).encode())
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            self._send_error_response(500, "Internal server error")
    
    def _handle_ping(self):
        """Обработка /ping endpoint для keep-alive"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b'pong')
    
    def _handle_root(self):
        """Обработка корневого пути"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Crypto Bot Status</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 600px; margin: 0 auto; }
                .status { padding: 20px; background: #f0f8ff; border-radius: 8px; }
                .endpoint { margin: 10px 0; padding: 10px; background: #f9f9f9; border-radius: 4px; }
                code { background: #e8e8e8; padding: 2px 4px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Crypto Bot Status</h1>
                <div class="status">
                    <h2>✅ Bot is running</h2>
                    <p>Monitoring symbol: <strong>{symbol}</strong></p>
                </div>
                
                <h3>Available Endpoints:</h3>
                <div class="endpoint">
                    <strong>GET /health</strong><br>
                    <small>Returns bot health status and statistics in JSON format</small>
                </div>
                
                <div class="endpoint">
                    <strong>GET /ping</strong><br>
                    <small>Keep-alive ping endpoint (returns "pong")</small>
                </div>
                
                <div class="endpoint">
                    <strong>GET /</strong><br>
                    <small>This status page</small>
                </div>
            </div>
        </body>
        </html>
        """.format(symbol=SYMBOL)
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def _handle_not_found(self):
        """Обработка 404 ошибок"""
        self._send_error_response(404, "Not Found")
    
    def _send_error_response(self, status_code: int, message: str):
        """Отправка ошибки"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        error_data = {
            "error": message,
            "status_code": status_code
        }
        self.wfile.write(json.dumps(error_data).encode())
    
    def log_message(self, format, *args):
        """Отключаем логи HTTP сервера"""
        pass

def start_health_server():
    """Запуск HTTP сервера для health check"""
    try:
        port = int(os.environ.get('PORT', 10000))
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logger.info(f"🏥 Health check сервер запущен на порту {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Ошибка запуска health сервера: {e}")

if __name__ == "__main__":
    # Для тестирования
    start_health_server()
