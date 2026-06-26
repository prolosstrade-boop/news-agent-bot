import os
import requests
import feedparser
import hashlib
from datetime import datetime
import traceback

print("=" * 60)
print(f"🚀 Запуск агента: {datetime.now()}")
print("=" * 60)

# === ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ===
print("\n📋 Проверка переменных окружения:")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TELEGRAM_TOKEN:
    print("❌ ОШИБКА: TELEGRAM_TOKEN не установлен!")
    exit(1)
else:
    print(f"✅ TELEGRAM_TOKEN: {TELEGRAM_TOKEN[:10]}...{TELEGRAM_TOKEN[-5:]}")

if not CHAT_ID:
    print("❌ ОШИБКА: CHAT_ID не установлен!")
    exit(1)
else:
    print(f"✅ CHAT_ID: {CHAT_ID}")

# === ТЕСТ TELEGRAM API ===
print("\n📱 Тест отправки в Telegram:")
try:
    test_message = f"🧪 Тестовое сообщение от новостного агента\n\n⏰ {datetime.now().strftime('%H:%M, %d.%m.%Y')}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": test_message,
        "parse_mode": "HTML"
    }
    
    print(f"  Отправка запроса на: {url}")
    response = requests.post(url, data=data, timeout=10)
    print(f"  Статус код: {response.status_code}")
    print(f"  Ответ: {response.text[:200]}")
    
    if response.status_code == 200:
        print("✅ Telegram API работает!")
    else:
        print(f"❌ Ошибка Telegram API: {response.text}")
        exit(1)
        
except Exception as e:
    print(f"❌ Исключение при отправке в Telegram:")
    print(traceback.format_exc())
    exit(1)

# === ТЕСТ RSS-ЛЕНТ ===
print("\n📰 Тест RSS-лент:")
rss_feeds = [
    ("ТАСС", "https://tass.ru/rss/v2.xml"),
    ("РИА", "https://ria.ru/export/rss2/archive/index.xml"),
]

for name, feed_url in rss_feeds:
    try:
        print(f"\n  Проверка {name}: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            print(f"  ⚠️  Предупреждение: {feed.bozo_exception}")
        
        print(f"  ✅ Найдено {len(feed.entries)} новостей")
        
        if feed.entries:
            first_entry = feed.entries[0]
            print(f"  Пример: {first_entry.get('title', 'N/A')[:80]}")
            
    except Exception as e:
        print(f"  ❌ Ошибка загрузки {name}:")
        print(f"  {traceback.format_exc()}")

print("\n" + "=" * 60)
print("✅ Диагностика завершена!")
print("=" * 60)
