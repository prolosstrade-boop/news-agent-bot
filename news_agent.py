import os
import requests
import feedparser
import hashlib
from datetime import datetime, timedelta
import json

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # опционально

# Ключевые слова для фильтрации важных событий
IMPORTANT_KEYWORDS = [
    "срочно", "чс", "чрезвычайная ситуация", "атака", "обстрел",
    "взрыв", "санкции", "закон", "путин", "правительство",
    "курс", "доллар", "евро", "нефть", "газ", "бензин",
    "мобилизация", "указ", "постановление",
  "налоги", "фнс", "беспилотники"
]

# Файл для хранения отправленных новостей (чтобы не дублировать)
SENT_NEWS_FILE = "sent_news.json"

def load_sent_news():
    """Загрузка списка уже отправленных новостей"""
    if os.path.exists(SENT_NEWS_FILE):
        with open(SENT_NEWS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_sent_news(sent_news):
    """Сохранение списка отправленных новостей"""
    with open(SENT_NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(sent_news, f, ensure_ascii=False, indent=2)

def is_important(title, description):
    """Проверка, важна ли новость"""
    text = (title + " " + description).lower()
    return any(keyword in text for keyword in IMPORTANT_KEYWORDS)

def get_news_from_rss():
    """Получение новостей из RSS-лент"""
rss_feeds = [
    "https://tass.ru/rss/v2.xml",
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://www.kommersant.ru/RSS/news.xml",  # добавить
    "https://rbc.ru/v10/ajax/get-news-feed/project/rbcnews/lastN/20",
]
    
    news_list = []
    for feed_url in rss_feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:  # Последние 10 новостей
                news_list.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", "")[:200]
                })
        except Exception as e:
            print(f"Ошибка при загрузке {feed_url}: {e}")
    
    return news_list

def send_to_telegram(title, link, summary):
    """Отправка новости в Telegram"""
    message = f"""🚨 <b>Срочная новость</b>

📍 <b>{title}</b>

📝 {summary}

🔗 <a href="{link}">Читать полностью</a>

⏰ {datetime.now().strftime('%H:%M, %d.%m.%Y')}"""
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    response = requests.post(url, data=data)
    return response.status_code == 200

def main():
    print(f"🚀 Запуск агента: {datetime.now()}")
    
    # Загружаем список уже отправленных новостей
    sent_news = load_sent_news()
    
    # Получаем свежие новости
    news_list = get_news_from_rss()
    print(f"📰 Найдено {len(news_list)} новостей")
    
    new_notifications = 0
    
    for news in news_list:
        # Создаем уникальный хеш новости
        news_hash = hashlib.md5(news["title"].encode()).hexdigest()
        
        # Проверяем, не отправляли ли мы уже эту новость
        if news_hash in sent_news:
            continue
        
        # Проверяем, важна ли новость
        if not is_important(news["title"], news["summary"]):
            continue
        
        # Отправляем в Telegram
        success = send_to_telegram(news["title"], news["link"], news["summary"])
        
        if success:
            print(f"✅ Отправлено: {news['title']}")
            sent_news.append(news_hash)
            new_notifications += 1
        else:
            print(f"❌ Ошибка отправки: {news['title']}")
    
    # Сохраняем обновленный список
    save_sent_news(sent_news)
    
    print(f"✨ Готово! Отправлено {new_notifications} новых уведомлений")

if __name__ == "__main__":
    main()
