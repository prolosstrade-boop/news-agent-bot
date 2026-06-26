import os
import requests
import feedparser
from datetime import datetime

print(f"🚀 Запуск: {datetime.now()}")

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ACTIVE_TOPICS = os.getenv("ACTIVE_TOPICS", "all")  # "all" или список через запятую

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ Ошибка: TELEGRAM_TOKEN или CHAT_ID не установлены")
    exit(1)

# === ТЕМЫ И КЛЮЧЕВЫЕ СЛОВА ===
TOPICS = {
    "politics": [
        "путин", "правительство", "дума", "совет федерации", "закон", "указ",
        "постановление", "выборы", "голосование", "партия", "министр", "госдума",
        "мишустин", "патрушев", "песков", "набиуллина", "матвиенко", "володин"
    ],
    "economy": [
        "экономика", "ввп", "инфляция", "безработица", "бизнес", "компания",
        "предприятие", "инвестиции", "рост", "спад", "реcession", "промышленность",
        "сельское хозяйство", "экспорт", "импорт", "торговля"
    ],
    "finance": [
        "банк", "цб", "центральный банк", "курс", "доллар", "евро", "юань",
        "акции", "облигации", "инвестиции", "вклад", "кредит", "ипотека",
        "налоги", "финансы", "рубль", "валюта", "биржа"
    ],
    "energy": [
        "нефть", "газ", "бензин", "дизель", "топливо", "энергетика", "электричество",
        "тарифы", "жкх", "тэк", "роснефть", "газпром", "лукойл", "новатэк",
        "спг", "нефтепровод", "газопровод", "уголь"
    ],
    "military": [
        "армия", "мо рф", "минобороны", "шойгу", "герасимов", "войска", "вооружение",
        "танк", "самолёт", "вертолёт", "ракета", "флот", "учения", "мобилизация",
        "спецоперация", "конфликт", "обстрел", "атака", "пво", "бпла"
    ],
    "tech": [
        "технологии", "it", "айти", "искусственный интеллект", "ии", "робот",
        "космос", "роскосмос", "спутник", "ракета-носитель", "цифровизация",
        "интернет", "связь", "5g", "чип", "процессор", "софт", "разработка"
    ],
    "social": [
        "общество", "здоровье", "медицина", "больница", "врач", "образование",
        "школа", "университет", "пенсия", "пособие", "льготы", "семья", "дети",
        "молодёжь", "спорт", "культура", "театр", "музей"
    ],
    "international": [
        "международный", "саммит", "оон", "ес", "евросоюз", "сша", "китай",
        "индия", "бРИКС", "снг", "одкб", "дипломатия", "посол", "лавров",
        "переговоры", "соглашение", "договор", "санкции"
    ]
}

# === ПОЛУЧЕНИЕ НОВОСТЕЙ ===
def get_news():
    feeds = [
        "https://tass.ru/rss/v2.xml",
        "https://ria.ru/export/rss2/archive/index.xml",
        "https://meduza.io/rss2/all",
        "https://www.vedomosti.ru/rss/news",
        "https://www.mk.ru/rss/index.xml",
        "http://duma.gov.ru/news/feed/",
        "https://lenta.ru/rss/news",
    ]
    
    news = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                news.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:200]
                })
        except Exception as e:
            print(f"Ошибка {feed_url}: {e}")
    
    return news

# === ОПРЕДЕЛЕНИЕ ТЕМЫ НОВОСТИ ===
def detect_topics(title, summary):
    text = (title + " " + summary).lower()
    detected = []
    
    for topic, keywords in TOPICS.items():
        if any(kw in text for kw in keywords):
            detected.append(topic)
    
    return detected

# === ПРОВЕРКА, ПОДХОДИТ ЛИ НОВОСТЬ ===
def should_send(detected_topics):
    if ACTIVE_TOPICS == "all":
        return True
    
    active_list = [t.strip() for t in ACTIVE_TOPICS.split(",")]
    return any(topic in active_list for topic in detected_topics)

# === ОТПРАВКА В TELEGRAM ===
def send_telegram(title, link, summary, topics):
    topics_emoji = {
        "politics": "🏛политика",
        "economy": "📊экономика",
        "finance": "💰финансы",
        "energy": "⛽энергетика",
        "military": "🎖оборона",
        "tech": "💻технологии",
        "social": "👥",
        "international": "🌍в мире"
    }
    
    topics_str = " ".join([topics_emoji.get(t, "📰") for t in topics])
    
    message = f"""{topics_str} 

📍 <b>{title}</b>

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
            print(f"✅ Отправлено [{', '.join(topics)}]: {title[:50]}")
            return True
        else:
            print(f"❌ Ошибка Telegram: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

# === ГЛАВНАЯ ФУНКЦИЯ ===
def main():
    print(f"📋 Активные темы: {ACTIVE_TOPICS}")
    
    news_list = get_news()
    print(f"📰 Найдено {len(news_list)} новостей")
    
    sent = 0
    skipped = 0
    
    for news in news_list:
        detected = detect_topics(news["title"], news["summary"])
        
        if not detected:
            print(f"⏭ Пропущено (нет темы): {news['title'][:50]}")
            skipped += 1
            continue
        
        if not should_send(detected):
            print(f"⏭ Пропущено (не та тема): {news['title'][:50]}")
            skipped += 1
            continue
        
        if send_telegram(news["title"], news["link"], news["summary"], detected):
            sent += 1
    
    print(f"✨ Готово! Отправлено {sent}, пропущено {skipped}")

if __name__ == "__main__":
    main()
