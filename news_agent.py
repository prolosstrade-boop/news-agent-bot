import os
import re
import json
import html
import hashlib
import requests
import feedparser
from datetime import datetime, timedelta

print(f"🚀 Запуск: {datetime.now()}")

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ACTIVE_TOPICS = os.getenv("ACTIVE_TOPICS", "all")
MAX_NEWS_AGE_HOURS = int(os.getenv("MAX_NEWS_AGE_HOURS", "4"))
SENT_NEWS_FILE = "sent_news.json"

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ TELEGRAM_TOKEN или CHAT_ID не установлены")
    exit(1)

# === ТЕМЫ (исправлены опечатки) ===
TOPICS = {
    "politics": [
        "путин", "правительство", "дума", "совет федерации", "закон", "указ",
        "постановление", "выборы", "голосование", "партия", "министр", "госдума",
        "мишустин", "патрушев", "песков", "набиуллина", "матвиенко", "володин"
    ],
    "economy": [
        "экономика", "ввп", "инфляция", "безработица", "бизнес", "компания",
        "предприятие", "инвестиции", "рост", "спад", "промышленность",
        "сельское хозяйство", "экспорт", "импорт", "торговля"
    ],
    "finance": [
        "банк", "цб рф", "центральный банк", "курс", "доллар", "евро", "юань",
        "акции", "облигации", "вклад", "кредит", "ипотека",
        "налоги", "финансы", "рубль", "валюта", "биржа", "ключевая ставка"
    ],
    "energy": [
        "нефть", "газ", "бензин", "дизель", "топливо", "энергетика", "электричество",
        "тарифы", "жкх", "тэк", "роснефть", "газпром", "лукойл", "новатэк",
        "спг", "нефтепровод", "газопровод", "уголь"
    ],
    "military": [
        "армия", "мо рф", "минобороны", "шойгу", "герасимов", "войска", "вооружение",
        "танк", "самолёт", "вертолёт", "ракета", "флот", "учения", "мобилизация",
        "спецоперация", "конфликт", "обстрел", "атака", "пво", "бпла", "дрон"
    ],
    "tech": [
        "технологии", "it", "айти", "искусственный интеллект", "ии", "робот",
        "космос", "роскосмос", "спутник", "цифровизация",
        "интернет", "связь", "5g", "чип", "процессор", "софт", "разработка", "яндекс", "сбер"
    ],
    "social": [
        "общество", "здоровье", "медицина", "больница", "врач", "образование",
        "школа", "университет", "пенсия", "пособие", "льготы", "семья", "дети",
        "молодёжь", "спорт", "культура", "театр", "музей"
    ],
    "international": [
        "международный", "саммит", "оон", "ес", "евросоюз", "сша", "китай",
        "индия", "брикс", "снг", "одкб", "дипломатия", "посол", "лавров",
        "переговоры", "соглашение", "договор", "санкции", "нат"
    ]
}

TOPICS_EMOJI = {
    "politics": "🏛",
    "economy": "📊",
    "finance": "💰",
    "energy": "⛽",
    "military": "🎖",
    "tech": "💻",
    "social": "👥",
    "international": "🌍"
}

# === РАБОТА С ХЕШАМИ (защита от дублей) ===
def load_sent_hashes():
    """Загрузка хешей уже отправленных новостей"""
    if os.path.exists(SENT_NEWS_FILE):
        try:
            with open(SENT_NEWS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Оставляем только последние 2000 записей
                return data[-2000:]
        except Exception as e:
            print(f"⚠️  Ошибка загрузки хешей: {e}")
            return []
    return []

def save_sent_hashes(hashes):
    """Сохранение хешей в файл"""
    try:
        with open(SENT_NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(hashes[-2000:], f, ensure_ascii=False)
        print(f"💾 Сохранено {len(hashes)} хешей")
    except Exception as e:
        print(f"⚠️  Ошибка сохранения: {e}")

def get_news_hash(title, link):
    """Уникальный хеш новости"""
    text = f"{title}|{link}"
    return hashlib.md5(text.encode()).hexdigest()

# === ОЧИСТКА HTML ===
def clean_html(text):
    """Удаление HTML-тегов из текста"""
    if not text:
        return ""
    # Удаляем теги
    clean = re.sub(r'<[^>]+>', '', text)
    # Декодируем HTML-сущности
    clean = html.unescape(clean)
    # Убираем лишние пробелы
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

# === ИЗВЛЕЧЕНИЕ ИЗОБРАЖЕНИЯ ===
def extract_image(entry):
    """Извлечение URL изображения из RSS-записи"""
    # 1. media:content
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            url = media.get('url', '')
            if url and ('image' in media.get('type', '') or any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp'])):
                return url
    
    # 2. media:thumbnail
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        for thumb in entry.media_thumbnail:
            if thumb.get('url'):
                return thumb.get('url')
    
    # 3. <img> в HTML
    html_content = entry.get('summary', '') or ''
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None

# === ПОЛУЧЕНИЕ НОВОСТЕЙ (без дублей в списке) ===
def get_news():
    feeds = [
        ("ТАСС", "https://tass.ru/rss/v2.xml"),
        ("РИА", "https://ria.ru/export/rss2/archive/index.xml"),
        ("РБК", "https://rssexport.rbc.ru/rbcnews/news/20/full.rss"),
        ("Коммерсант", "https://www.kommersant.ru/RSS/news.xml"),
        ("Лента", "https://lenta.ru/rss/news"),  # Убран дубль!
        ("Интерфакс", "https://www.interfax.ru/rss.asp"),
        ("Известия", "https://iz.ru/xml/feed.php"),
    ]
    
    news = []
    for name, feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                # Извлекаем время публикации
                pub_time = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_time = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    try:
                        pub_time = datetime(*entry.updated_parsed[:6])
                    except:
                        pass
                
                # Извлекаем изображение
                image_url = extract_image(entry)
                
                news.append({
                    "source": name,
                    "title": clean_html(entry.get("title", "")),
                    "link": entry.get("link", ""),
                    "summary": clean_html(entry.get("summary", ""))[:300],
                    "published": pub_time,
                    "image_url": image_url
                })
        except Exception as e:
            print(f"⚠️  Ошибка {name}: {e}")
    
    return news

# === ФИЛЬТР СВЕЖЕСТИ ===
def is_fresh(pub_time):
    if not pub_time:
        return True  # Если время неизвестно — пропускаем
    age = datetime.now() - pub_time
    return age <= timedelta(hours=MAX_NEWS_AGE_HOURS)

# === ОПРЕДЕЛЕНИЕ ТЕМЫ ===
def detect_topics(title, summary):
    text = (title + " " + summary).lower()
    return [topic for topic, keywords in TOPICS.items() if any(kw in text for kw in keywords)]

# === ПРОВЕРКА ТЕМ ===
def should_send(detected_topics):
    if ACTIVE_TOPICS.lower() == "all":
        return True
    active_list = [t.strip().lower() for t in ACTIVE_TOPICS.split(",")]
    return any(topic in active_list for topic in detected_topics)

# === ОТПРАВКА В TELEGRAM ===
def send_telegram(title, link, summary, topics, pub_time, image_url):
    topics_str = " ".join([TOPICS_EMOJI.get(t, "📰") for t in topics])
    
    # Время публикации
    if pub_time:
        time_str = pub_time.strftime('%H:%M, %d.%m')
    else:
        time_str = datetime.now().strftime('%H:%M, %d.%m')
    
    # Экранируем HTML
    safe_title = html.escape(title)
    safe_summary = html.escape(summary)
    
    caption = f"""{topics_str}

📍 <b>{safe_title}</b>

📝 {safe_summary}

🔗 <a href="{link}">Подробнее</a>
⏰ {time_str}"""
    
    # Ограничение Telegram: 1024 символа для caption
    if len(caption) > 1020:
        caption = caption[:1017] + "..."
    
    # Попытка 1: с фото
    if image_url and image_url.startswith(('http://', 'https://')):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            response = requests.post(url, data={
                "chat_id": CHAT_ID,
                "photo": image_url,
                "caption": caption,
                "parse_mode": "HTML"
            }, timeout=15)
            
            if response.status_code == 200:
                return True
        except Exception as e:
            print(f"⚠️  Не удалось отправить фото: {e}")
    
    # Попытка 2: только текст
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": caption,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Telegram error: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

# === ГЛАВНАЯ ФУНКЦИЯ ===
def main():
    print(f"📋 Темы: {ACTIVE_TOPICS}")
    print(f"⏰ Макс. возраст: {MAX_NEWS_AGE_HOURS}ч")
    
    # Загружаем хеши
    sent_hashes = load_sent_hashes()
    print(f"📦 В истории: {len(sent_hashes)} новостей")
    
    news_list = get_news()
    print(f"📰 Найдено: {len(news_list)}")
    
    sent = 0
    skipped_old = 0
    skipped_topic = 0
    skipped_dup = 0
    new_hashes = []
    
    for news in news_list:
        # 1. Проверка свежести
        if not is_fresh(news["published"]):
            skipped_old += 1
            continue
        
        # 2. Определение темы
        detected = detect_topics(news["title"], news["summary"])
        if not detected or not should_send(detected):
            skipped_topic += 1
            continue
        
        # 3. Проверка дублей
        news_hash = get_news_hash(news["title"], news["link"])
        if news_hash in sent_hashes:
            skipped_dup += 1
            continue
        
        # 4. Отправка
        if send_telegram(
            news["title"], news["link"], news["summary"],
            detected, news["published"], news["image_url"]
        ):
            sent += 1
            new_hashes.append(news_hash)
            import time
            time.sleep(1)  # Rate limiting
    
    # Сохраняем новые хеши
    if new_hashes:
        sent_hashes.extend(new_hashes)
        save_sent_hashes(sent_hashes)
    
    print(f"\n✨ ИТОГО:")
    print(f"  ✅ Отправлено: {sent}")
    print(f"  ⏭ Старых: {skipped_old}")
    print(f"  🚫 По теме: {skipped_topic}")
    print(f"  🔄 Дублей: {skipped_dup}")

if __name__ == "__main__":
    main()