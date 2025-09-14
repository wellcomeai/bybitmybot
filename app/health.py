import os
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from config import SYMBOL

# Импортируем стратегию
try:
    from strategy import strategy
except ImportError:
    from strategies import strategy

logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для health check - ИСПРАВЛЕНО ДЛЯ RENDER"""
    
    def do_GET(self):
        """Обработка GET запросов"""
        try:
            if self.path == '/health':
                self._handle_health_check()
            elif self.path == '/' or self.path == '':
                # ИСПРАВЛЕНО: Render по умолчанию пингует `/` - делаем его простым health check
                self._handle_simple_health_check()
            elif self.path == '/dashboard':
                self._handle_dashboard()
            elif self.path == '/ping':
                self._handle_ping()
            else:
                self._handle_not_found()
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в health handler: {e}")
            self._send_error_response(500, f"Internal server error: {str(e)}")
    
    def _handle_simple_health_check(self):
        """Простой health check для корневого пути - ДЛЯ RENDER"""
        try:
            # Render пингует `/` по умолчанию, возвращаем простой статус
            health_data = {
                "status": "healthy",
                "service": "crypto-bot",
                "timestamp": datetime.now().isoformat(),
                "check_type": "simple"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            response_json = json.dumps(health_data, indent=2)
            self.wfile.write(response_json.encode('utf-8'))
            
            logger.debug("✅ Simple health check (/) response sent")
            
        except Exception as e:
            logger.error(f"❌ Error in simple health check: {e}")
            self._send_error_response(500, f"Simple health check failed: {str(e)}")
    
    def _handle_health_check(self):
        """Детальный health check endpoint"""
        try:
            stats = strategy.get_stats()
            health_data = {
                "status": "healthy",
                "service": "crypto-bot",
                "symbol": SYMBOL,
                "total_signals": stats.get("total_signals", 0),
                "last_signal": stats.get("last_signal"),
                "last_price": stats.get("last_price"),
                "version": "1.0.2",
                "timestamp": datetime.now().isoformat(),
                "check_type": "detailed"
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
            
            logger.debug(f"✅ Detailed health check (/health) response sent: {len(response_json)} bytes")
            
        except Exception as e:
            logger.error(f"❌ Error in detailed health check: {e}")
            self._send_error_response(500, f"Health check failed: {str(e)}")
    
    def _handle_dashboard(self):
        """HTML Dashboard - перенесено с корневого пути"""  
        try:
            stats = strategy.get_stats()
            
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Crypto Bot Dashboard</title>
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
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        .endpoint {{
            margin: 15px 0;
            padding: 15px;
            background: #e9ecef;
            border-radius: 4px;
        }}
        code {{
            background: #d1ecf1;
            padding: 4px 8px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Crypto Trading Bot Dashboard</h1>
        <div class="status">
            <h2>✅ Bot Status: Running</h2>
            <p>Monitoring: <strong>{SYMBOL}</strong></p>
            <p>Version: 1.0.2 (Fixed for Render)</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>📊 Trading Stats</h3>
                <p>Total Signals: <strong>{stats.get('total_signals', 0)}</strong></p>
                <p>Last Signal: <strong>{stats.get('last_signal', 'None')}</strong></p>
                <p>Last Price: <strong>${stats.get('last_price', 'N/A')}</strong></p>
            </div>
            <div class="stat-card">
                <h3>🎯 Strategy Levels</h3>
                <p>Buy Level: <strong>${stats.get('buy_level', 'N/A')}</strong></p>
                <p>Sell Level: <strong>${stats.get('sell_level', 'N/A')}</strong></p>
            </div>
        </div>
        
        <h3>📡 API Endpoints:</h3>
        
        <div class="endpoint">
            <strong>GET /</strong> - Simple health check (JSON)<br>
            <small>Used by Render for health monitoring</small>
        </div>
        
        <div class="endpoint">
            <strong>GET /health</strong> - Detailed health status (JSON)<br>
            <small>Comprehensive bot statistics and health data</small>
        </div>
        
        <div class="endpoint">
            <strong>GET /ping</strong> - Keep-alive endpoint<br>
            <small>Returns "pong" for basic connectivity testing</small>
        </div>
        
        <div class="endpoint">
            <strong>GET /dashboard</strong> - This HTML dashboard<br>
            <small>Human-readable bot status and statistics</small>
        </div>
        
        <div style="margin-top: 30px; text-align: center; color: #6c757d;">
            <p>🚀 Deployed on Render • Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            <p><strong>Health Check Fix:</strong> Root path now returns JSON for Render compatibility</p>
        </div>
    </div>
</body>
</html>"""
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
            logger.debug("✅ Dashboard page served successfully")
            
        except Exception as e:
            logger.error(f"❌ Error serving dashboard: {e}")
            self._send_error_response(500, f"Dashboard error: {str(e)}")
    
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
    
    def _handle_not_found(self):
        """Обработка 404 ошибок"""
        available_paths = ["/", "/health", "/ping", "/dashboard"]
        error_data = {
            "error": "Endpoint not found",
            "status_code": 404,
            "available_paths": available_paths,
            "requested_path": self.path
        }
        
        self.send_response(404)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(error_data, indent=2).encode('utf-8'))
    
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
                "timestamp": datetime.now().isoformat(),
                "service": "crypto-bot"
            }
            self.wfile.write(json.dumps(error_data, indent=2).encode('utf-8'))
        except Exception as e:
            logger.error(f"❌ Failed to send error response: {e}")
    
    def log_message(self, format, *args):
        """Логируем только важные запросы"""
        # Логируем health check запросы для диагностики
        if 'health' in format or '/' in format:
            logger.debug(f"🌐 HTTP: {format % args}")

def start_health_server():
    """Запуск HTTP сервера для health check - RENDER COMPATIBLE"""
    try:
        # Render по умолчанию использует порт 10000
        port = int(os.environ.get('PORT', 10000))
        server_address = ('0.0.0.0', port)
        
        logger.info(f"🏥 Запуск Render-совместимого health сервера...")
        logger.info(f"📡 PORT переменная: {os.environ.get('PORT', 'не установлена, используем 10000')}")
        logger.info(f"📡 Слушаем: {server_address[0]}:{server_address[1]}")
        logger.info(f"🎯 Корневой путь `/` возвращает JSON для Render health check")
        
        # Создаем и запускаем сервер
        server = HTTPServer(server_address, HealthCheckHandler)
        logger.info(f"✅ HTTP сервер запущен на порту {port}")
        logger.info(f"📊 Доступные пути:")
        logger.info(f"   GET / - простой health check (JSON)")
        logger.info(f"   GET /health - детальный health check (JSON)") 
        logger.info(f"   GET /ping - keep-alive test")
        logger.info(f"   GET /dashboard - HTML dashboard")
        
        # Запускаем сервер (блокирующий вызов)
        server.serve_forever()
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА HTTP сервера: {e}")
        logger.error(f"📋 Тип ошибки: {type(e).__name__}")
        logger.error(f"📡 Значение PORT: {os.environ.get('PORT', 'НЕ УСТАНОВЛЕНА')}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    # Для тестирования health сервера отдельно
    logging.basicConfig(level=logging.INFO)
    logger.info("🧪 Запуск health сервера в тестовом режиме...")
    start_health_server()
