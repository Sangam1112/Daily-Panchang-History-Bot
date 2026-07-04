import os
import sys
import html
import logging
import requests
import re
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9 (though GitHub Actions runners use Python 3.10+)
    from backports.zoneinfo import ZoneInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# List of India-related keywords (compiled from geography, history, languages, notable names, etc.)
INDIAN_KEYWORDS = [
    r"\bindia(n)?\b", r"\bhindu(s|ism)?\b", r"\bbuddha\b", r"\bbuddhis(t|m)?\b", r"\bsikh(s|ism)?\b",
    r"\bjain(s|ism)?\b", r"\bdelhi\b", r"\bmumbai\b", r"\bkolkata\b", r"\bchennai\b", r"\bbangalore\b",
    r"\bhyderabad\b", r"\bpune\b", r"\bahmedabad\b", r"\bjaipur\b", r"\blucknow\b", r"\bpatna\b",
    r"\bcalcutta\b", r"\bbombay\b", r"\bmadras\b", r"\bbengal(i)?\b", r"\bpunjab(i)?\b", r"\bgujarat(i)?\b",
    r"\bmaharashtra(n)?\b", r"\bkarnataka\b", r"\bkerala\b", r"\btamil(ian)?\b", r"\btelangana\b",
    r"\bandhra\b", r"\bodisha\b", r"\bassam\b", r"\bkashmir(i)?\b", r"\brajasthan\b", r"\bbihar(i)?\b",
    r"\bgoa(n)?\b", r"\bharyana\b", r"\bhimachal\b", r"\buttar pradesh\b", r"\bmadhya pradesh\b",
    r"\bgandhi\b", r"\bnehru\b", r"\bmodi\b", r"\bvivekananda\b", r"\btagore\b", r"\bambbedkar\b",
    r"\bpatel\b", r"\bbose\b", r"\bshastri\b", r"\bsingh\b", r"\bnaidu\b", r"\bkrishnan\b", r"\braju\b",
    r"\bvenkayya\b", r"\bnanda\b", r"\bprasad\b", r"\broy\b", r"\bsharma\b", r"\bkumar\b", r"\bverma\b",
    r"\bpatil\b", r"\bdeshmukh\b", r"\bnair\b", r"\bpillai\b", r"\biyer\b", r"\biyengar\b", r"\brao\b",
    r"\breddy\b", r"\bchoudhury\b", r"\bdas\b", r"\bsen\b", r"\bgupta\b", r"\bbanerjee\b", r"\bchatterjee\b",
    r"\bmukherjee\b", r"\bkhan\b", r"\bali\b", r"\bahmed\b", r"\bshah\b", r"\bjoshi\b", r"\bmehta\b",
    r"\bbhatt\b", r"\bmughal(s)?\b", r"\bmaratha(s)?\b", r"\bchola(s)?\b", r"\bmauryan?\b", r"\bgupta\b",
    r"\bchalukya\b", r"\bpallava\b", r"\brashtrakuta\b", r"\bsatavahana\b", r"\bdelhi sultanate\b",
    r"\bnizam\b", r"\bpeshwa\b", r"\btipu sultan\b", r"\beast india company\b", r"\bbritish raj\b",
    r"\bswaraj\b", r"\bsatyagraha\b", r"\bkargil\b", r"\bindian army\b", r"\bsepoy\b", r"\bplassey\b",
    r"\bbuxar\b", r"\blok sabha\b", r"\brajya sabha\b", r"\bpanchayat\b", r"\btiranga\b", r"\bbollywood\b"
]

# Compile pattern for case-insensitive matching
INDIAN_PATTERN = re.compile("|".join(INDIAN_KEYWORDS), re.IGNORECASE)

def is_indian_context(text):
    return bool(INDIAN_PATTERN.search(text))

def fetch_panchang(date_str, city="delhi"):
    """
    Fetches Hindu Almanac (Panchang) details for the specified date and city.
    """
    url = "https://nityapanchangam.com/api/panchangam.php"
    params = {"date": date_str, "city": city}
    try:
        logger.info(f"Fetching Panchang for {date_str} in {city}...")
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching Panchang: {e}")
        return None

def fetch_wikipedia_events(month, day):
    """
    Fetches all historical events, births, deaths, and holidays from Wikipedia for a given month and day.
    """
    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/all/{month}/{day}"
    headers = {
        'User-Agent': 'DailySpecialBot/1.0 (contact: github-actions-bot@example.com)'
    }
    try:
        logger.info(f"Fetching Wikipedia events for {month}/{day}...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching Wikipedia events: {e}")
        return None

def format_panchang(panchang_data):
    """
    Formats Panchang data into a clean HTML block for Telegram.
    """
    if not panchang_data:
        return "⚠️ <i>Panchang data could not be retrieved today.</i>\n\n"

    # Safely extract values
    city = panchang_data.get('city', 'India')
    tithi = panchang_data.get('tithi', {}).get('name', 'N/A')
    nakshatra = panchang_data.get('nakshatra', {}).get('name', 'N/A')
    yoga = panchang_data.get('yoga', {}).get('name', 'N/A')
    karana = panchang_data.get('karana', {}).get('name', 'N/A')
    vara = panchang_data.get('vara', {}).get('name', 'N/A')
    
    sun = panchang_data.get('sun', {})
    sunrise = sun.get('sunrise', 'N/A')
    sunset = sun.get('sunset', 'N/A')
    
    muhurta = panchang_data.get('muhurta', {})
    rahu_kalam = muhurta.get('rahu_kalam', 'N/A')
    abhijit = muhurta.get('abhijit_muhurtam', 'N/A')

    text = (
        f"🕉 <b>Hindu Almanac (Panchang - {html.escape(city, quote=False)})</b>\n"
        f"• <b>Vara (Day):</b> {html.escape(vara, quote=False)}\n"
        f"• <b>Tithi:</b> {html.escape(tithi, quote=False)}\n"
        f"• <b>Nakshatra:</b> {html.escape(nakshatra, quote=False)}\n"
        f"• <b>Yoga:</b> {html.escape(yoga, quote=False)}\n"
        f"• <b>Karana:</b> {html.escape(karana, quote=False)}\n"
        f"• <b>Sun Times:</b> Sunrise: {html.escape(sunrise, quote=False)} | Sunset: {html.escape(sunset, quote=False)}\n"
        f"• <b>Rahu Kalam:</b> {html.escape(rahu_kalam, quote=False)}\n"
        f"• <b>Abhijit Muhurta:</b> {html.escape(abhijit, quote=False)}\n\n"
    )
    return text

def format_wikipedia_section(wiki_data):
    """
    Filters and formats Wikipedia events, births, deaths, and holidays.
    """
    if not wiki_data:
        return "⚠️ <i>Historical events data could not be retrieved today.</i>\n\n"

    sections_text = ""
    
    # 1. Major events in India
    events = wiki_data.get('events', []) + wiki_data.get('selected', [])
    indian_events = []
    seen_events = set()
    for e in events:
        text = e.get('text', '')
        if text not in seen_events and is_indian_context(text):
            seen_events.add(text)
            year = e.get('year', '')
            year_prefix = f"<b>[{year}]</b> " if year else ""
            indian_events.append(f"• {year_prefix}{html.escape(text, quote=False)}")
    
    if indian_events:
        sections_text += "🇮🇳 <b>Major Events in Indian History</b>\n"
        sections_text += "\n".join(indian_events[:7]) + "\n\n"  # limit to top 7
    
    # 2. Notable births (India)
    births = wiki_data.get('births', [])
    indian_births = []
    for b in births:
        text = b.get('text', '')
        if is_indian_context(text):
            year = b.get('year', '')
            year_prefix = f"<b>[{year}]</b> " if year else ""
            indian_births.append(f"• {year_prefix}{html.escape(text, quote=False)}")
            
    if indian_births:
        sections_text += "🎂 <b>Notable Birth Anniversaries (India)</b>\n"
        sections_text += "\n".join(indian_births[:5]) + "\n\n"  # limit to top 5

    # 3. Notable deaths (India)
    deaths = wiki_data.get('deaths', [])
    indian_deaths = []
    for d in deaths:
        text = d.get('text', '')
        if is_indian_context(text):
            year = d.get('year', '')
            year_prefix = f"<b>[{year}]</b> " if year else ""
            indian_deaths.append(f"• {year_prefix}{html.escape(text, quote=False)}")
            
    if indian_deaths:
        sections_text += "🕯 <b>Notable Remembrance Days (India)</b>\n"
        sections_text += "\n".join(indian_deaths[:5]) + "\n\n"  # limit to top 5

    # 4. Holidays & Festivals
    holidays = wiki_data.get('holidays', [])
    indian_holidays = []
    global_holidays = []
    for h in holidays:
        text = h.get('text', '')
        if is_indian_context(text):
            indian_holidays.append(f"• {html.escape(text, quote=False)}")
        else:
            global_holidays.append(f"• {html.escape(text, quote=False)}")
            
    if indian_holidays:
        sections_text += "🎉 <b>Indian Festivals & Holidays</b>\n"
        sections_text += "\n".join(indian_holidays[:5]) + "\n\n"
        
    if global_holidays:
        sections_text += "🌍 <b>Global Holidays & Observances</b>\n"
        sections_text += "\n".join(global_holidays[:5]) + "\n\n"

    return sections_text

def send_telegram_message(token, chat_id, message_text):
    """
    Sends the formatted message to Telegram.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        logger.info("Sending message to Telegram...")
        response = requests.post(url, json=payload, timeout=15)
        response_json = response.json()
        if response.status_code == 200 and response_json.get("ok"):
            logger.info("Message sent successfully!")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response_json}")
            return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

def main():
    # 1. Get current date in IST
    ist_tz = ZoneInfo("Asia/Kolkata")
    now_ist = datetime.now(ist_tz)
    
    date_str = now_ist.strftime("%Y-%m-%d")
    month_str = now_ist.strftime("%m")
    day_str = now_ist.strftime("%d")
    readable_date = now_ist.strftime("%B %d, %Y (%A)")

    logger.info(f"Running daily update for date (IST): {readable_date}")

    # 2. Fetch data
    panchang_data = fetch_panchang(date_str)
    wiki_data = fetch_wikipedia_events(month_str, day_str)

    # 3. Format message
    header = f"📅 <b>DAILY UPDATE: {readable_date}</b>\n\n"
    panchang_text = format_panchang(panchang_data)
    wiki_text = format_wikipedia_section(wiki_data)
    footer = "✨ <i>Have a wonderful day ahead!</i>"
    
    full_message = f"{header}{panchang_text}{wiki_text}{footer}"
    
    # 4. Handle Telegram delivery
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    # Print message to stdout for log visibility
    print("\n--- FORMATTED TELEGRAM MESSAGE ---")
    print(full_message)
    print("----------------------------------\n")
    
    if telegram_token and telegram_chat_id:
        success = send_telegram_message(telegram_token, telegram_chat_id, full_message)
        if not success:
            sys.exit(1)
    else:
        logger.warning(
            "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables are not set. "
            "Skipping Telegram delivery. Message printed to stdout."
        )

if __name__ == "__main__":
    main()
