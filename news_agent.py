import os
import requests
import feedparser
from datetime import datetime

print(f"🚀 Запуск: {datetime.now()}")

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ Ошибка: TELEGRAM_TOKEN или CHAT_ID не установлены")
    exit(1)

# === КЛЮЧЕВЫЕ СЛОВА ===
KEYWORDS = [
    "срочно", "чс", "чрезвычайная ситуация", "атака", "обстрел",
    "взрыв", "санкции", "закон", "путин", "правительство",
    "курс", "доллар", "евро", "нефть", "газ", "бензин",
    "мобилизация", "указ", "постановление",
  "налоги", "фнс", "беспилотники", "ЦБ", "Центральный банк", "Набиулина",
    "Мишустин", "Шойгу", "СВО", "Специальная военная операция",
    "госдума", "государственная дума", "экономика", "безработица"
]

# === ПОЛУЧЕНИЕ НОВОСТЕЙ ===
def get_news():
    feeds = [
        "https://tass.ru/rss/v2.xml",
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://www.kommersant.ru/RSS/news.xml",  # добавить
    "https://rbc.ru/v10/ajax/get-news-feed/project/rbcnews/lastN/20",
    ]
    
    news = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                news.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:150]
                })
        except Exception as e:
            print(f"Ошибка {feed_url}: {e}")
    
    return news

# === ОТПРАВКА В TELEGRAM ===
def send_telegram(title, link, summary):
    message = f"""
    {datetime.now().strftime('%H:%M, %d.%m.%Y')}
🚨 <b>{title}</b>

📝 {summary}
🔗 <a href="{link}">Подробнее</a>
"""
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Отправлено: {title[:50]}")
            return True
        else:
            print(f"❌ Ошибка: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

# === ГЛАВНАЯ ФУНКЦИЯ ===
def main():
    news_list = get_news()
    print(f"📰 Найдено {len(news_list)} новостей")
    
    sent = 0
    for news in news_list:
        text = (news["title"] + " " + news["summary"]).lower()
        
        # Проверяем ключевые слова
        if any(kw in text for kw in KEYWORDS):
            if send_telegram(news["title"], news["link"], news["summary"]):
                sent += 1
    
    print(f"✨ Готово! Отправлено {sent} новостей")

if __name__ == "__main__":
    main()
