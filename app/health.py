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
        try:
            if self.path == '/health':
                self._handle_health_check()
            elif self.path == '/':
                self._handle_root()
            elif self.path == '/ping':
                self._handle_ping()
            else:
                self._handle_not_found()
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в health handler: {e}")
            self._send_error_response(500, f"Internal server error: {str(e)}")
    
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
                "version": "1.0.0",
                "timestamp": "2025-09-14T10:08:15Z"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            
            response_json = json.dumps(health_data, indent=2)
            self.wfile.write(response_json.encode('utf-8'))
            
            logger.debug(f"✅ Health check response sent: {len(response_json)} bytes")
            
        except Exception as e:
            logger.error(f"❌ Error in health check: {e}")
            self._send_error_response(500, f"Health check failed: {str(e)}")
    
    def _handle_ping(self):
        """Обработка /ping endpoint для keep-alive"""
        try:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(b'pong')
            logger.debug("✅ Ping response sent")
        except Exception as e:
            logger.error(f"❌ Error in ping handler: {e}")
    
    def _handle_root(self):
        """Обработка корневого пути - ИСПРАВЛЕНО"""
        try:
            # Используем простой HTML без format() чтобы избежать KeyError
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Crypto Bot Status</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .status {{
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .endpoint {{
            margin: 15px 0;
            padding: 15px;
            background: #f8f9fa;
            border-left: 4px solid #007bff;
            border-radius: 4px;
        }}
        .endpoint strong {{
            color: #007bff;
            font-family: 'Monaco', 'Menlo', monospace;
        }}
        code {{
            background: #e9ecef;
            padding: 4px 8px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
        }}
        .symbol {{
            font-weight: bold;
            color: #28a745;
            font-size: 1.2em;
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #6c757d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Crypto Trading Bot Status</h1>
        <div class="status">
            <h2>✅ Bot is running successfully</h2>
            <p>Monitoring symbol: <span class="symbol">{SYMBOL}</span></p>
            <p>Version: 1.0.0 (Modular Architecture)</p>
        </div>
        
        <h3>📡 Available API Endpoints:</h3>
        
        <div class="endpoint">
            <strong>GET /health</strong><br>
            <small>Returns comprehensive bot health status and statistics in JSON format</small>
        </div>
        
        <div class="endpoint">
            <strong>GET /ping</strong><br>
            <small>Keep-alive ping endpoint (returns "pong" for uptime monitoring)</small>
        </div>
        
        <div class="endpoint">
            <strong>GET /</strong><br>
            <small>This status dashboard page</small>
        </div>
        
        <h3>🔧 Bot Features:</h3>
        <ul>
            <li>✅ Real-time WebSocket connection to Bybit</li>
            <li>✅ Telegram notifications for trading signals</li>
            <li>✅ Simple levels trading strategy</li>
            <li>✅ Automatic reconnection and error handling</li>
            <li>✅ Comprehensive health monitoring</li>
        </ul>
        
        <div class="footer">
            <p>🚀 Deployed on Render • Last updated: 2025-09-14</p>
        </div>
    </div>
</body>
</html>"""
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
            logger.debug("✅ Root page served successfully")
            
        except Exception as e:
            logger.error(f"❌ Error serving root page: {e}")
            self._send_error_response(500, f"Root page error: {str(e)}")
    
    def _handle_not_found(self):
        """Обработка 404 ошибок"""
        self._send_error_response(404, "Endpoint not found")
    
    def _send_error_response(self, status_code: int, message: str):
        """Отправка ошибки"""
        try:
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_data = {
                "error": message,
                "status_code": status_code,
                "timestamp": "2025-09-14T10:08:15Z"
            }
            self.wfile.write(json.dumps(error_data, indent=2).encode('utf-8'))
        except Exception as e:
            logger.error(f"❌ Failed to send error response: {e}")
    
    def log_message(self, format, *args):
        """Отключаем стандартные логи HTTP сервера для чистоты вывода"""
        pass

def start_health_server():
    """Запуск HTTP сервера для health check"""
    try:
        # Render использует переменную PORT, fallback на 10000
        port = int(os.environ.get('PORT', 10000))
        server_address = ('0.0.0.0', port)
        
        logger.info(f"🏥 Запуск health check сервера...")
        logger.info(f"📡 Адрес: {server_address[0]}:{server_address[1]}")
        
        server = HTTPServer(server_address, HealthCheckHandler)
        logger.info(f"🏥 Health check сервер запущен успешно на порту {port}")
        logger.info(f"📊 Доступные эндпоинты: /, /health, /ping")
        
        # Запускаем сервер
        server.serve_forever()
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА запуска health сервера: {e}")
        logger.error(f"📋 Тип ошибки: {type(e).__name__}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    # Для тестирования health сервера отдельно
    logging.basicConfig(level=logging.DEBUG)
    logger.info("🧪 Запуск health сервера в тестовом режиме...")
    start_health_server()
