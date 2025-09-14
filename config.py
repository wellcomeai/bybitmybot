import os
from dotenv import load_dotenv

# Загружаем .env файл для локальной разработки
load_dotenv()

# ==== TELEGRAM ====
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ==== BYBIT ====
BYBIT_PUBLIC_WS = os.getenv('BYBIT_PUBLIC_WS', 'wss://stream.bybit.com/v5/public/spot')
BYBIT_API_KEY = os.getenv('BYBIT_API_KEY')  # Для будущих торговых функций
BYBIT_SECRET = os.getenv('BYBIT_SECRET')    # Для будущих торговых функций
BYBIT_TESTNET = os.getenv('BYBIT_TESTNET', 'True').lower() == 'true'

# ==== ТОРГОВЫЕ НАСТРОЙКИ ====
SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')
BUY_LEVEL = float(os.getenv('BUY_LEVEL', '27000'))
SELL_LEVEL = float(os.getenv('SELL_LEVEL', '26000'))

# ==== ОБЩИЕ НАСТРОЙКИ ====
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
RECONNECT_DELAY = int(os.getenv('RECONNECT_DELAY', '5'))

# Проверяем обязательные переменные
def validate_config():
    required_vars = {
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    
    missing = [var for var, value in required_vars.items() if not value]
    
    if missing:
        raise ValueError(f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}")
    
    print("✅ Конфигурация загружена успешно")
    print(f"📊 Символ: {SYMBOL}")
    print(f"📈 Уровень покупки: {BUY_LEVEL}")
    print(f"📉 Уровень продажи: {SELL_LEVEL}")
    print(f"🧪 Тестнет: {BYBIT_TESTNET}")

if __name__ == "__main__":
    validate_config()
