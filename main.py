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
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def get_session():
    """
    Creates a requests Session with HTTP retry adapter.
    Retries up to 3 times for temporary network errors/rate-limiting, 
    with exponential backoff.
    """
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[500, 502, 503, 504, 429],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Global session with retries enabled
http_session = get_session()

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

# Exclusion patterns (non-Indian context, to filter out false positives from common surnames or religions)
EXCLUSION_KEYWORDS = [
    r"\bchinese\b", r"\bjapanese\b", r"\btibetan\b", r"\bsri lankan\b", 
    r"\bnepalese\b", r"\bthai\b", r"\bvietnamese\b", r"\bkorean\b",
    r"\bburmese\b", r"\bcanadian\b", r"\bamerican\b", r"\benglish\b", 
    r"\bbritish\b", r"\baustralian\b", r"\bfrench\b", r"\bgerman\b", 
    r"\bitalian\b", r"\bspanish\b", r"\bdutch\b", r"\bswedish\b", 
    r"\bnorwegian\b", r"\birish\b", r"\bscottish\b", r"\bwelsh\b", 
    r"\brussian\b", r"\bpolish\b", r"\bgreek\b", r"\bturkish\b", 
    r"\begyptian\b", r"\biranian\b", r"\bpersian\b", r"\biraqi\b", 
    r"\bsaudi\b", r"\bbrazilian\b", r"\bargentine\b", r"\bmexican\b"
]
EXCLUSION_PATTERN = re.compile("|".join(EXCLUSION_KEYWORDS), re.IGNORECASE)

# Words that override exclusions (if they are present, we allow the match anyway)
ALLOW_KEYWORDS = [r"\bindia(n)?\b", r"\bhindu(s|ism)?\b", r"\bsikh(s|ism)?\b", r"\bjain(s|ism)?\b"]
ALLOW_PATTERN = re.compile("|".join(ALLOW_KEYWORDS), re.IGNORECASE)

def is_indian_context(text):
    if not INDIAN_PATTERN.search(text):
        return False
    # If the text matches an exclusion keyword (e.g. "Chinese Buddhist", "Canadian ice hockey player Roy"),
    # we filter it out unless it explicitly mentions core Indian keywords.
    if EXCLUSION_PATTERN.search(text):
        if not ALLOW_PATTERN.search(text):
            return False
    return True

def fetch_panchang(date_str, city="mumbai"):
    """
    Fetches Hindu Almanac (Panchang) details for the specified date and city.
    """
    url = "https://nityapanchangam.com/api/panchangam.php"
    params = {"date": date_str, "city": city}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        logger.info(f"Fetching Panchang for {date_str} in {city}...")
        response = http_session.get(url, params=params, headers=headers, timeout=15)
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
        response = http_session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching Wikipedia events: {e}")
        return None

def fetch_bharat_festival(now_ist):
    """
    Fetches today's festival from the calendar-bharat project.
    """
    year = now_ist.strftime("%Y")
    month_name = now_ist.strftime("%B %Y")
    # Date key format: "July 4, 2026, Saturday" (no leading zero on day)
    date_key = f"{now_ist.strftime('%B')} {now_ist.day}, {now_ist.strftime('%Y, %A')}"
    
    url = f"https://jayantur13.github.io/calendar-bharat/calendar/{year}.json"
    try:
        logger.info(f"Fetching Indian festivals for year {year} from calendar-bharat...")
        response = http_session.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Access elements safely
        year_data = data.get(year, {})
        month_data = year_data.get(month_name, {})
        event_data = month_data.get(date_key)
        if event_data:
            logger.info(f"Found festival in calendar-bharat: {event_data.get('event')}")
            return event_data
    except Exception as e:
        logger.error(f"Error fetching calendar-bharat festivals: {e}")
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

def format_wikipedia_section(wiki_data, bharat_event=None):
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
    
    # Prepend calendar-bharat festival if present
    if bharat_event:
        event_name = bharat_event.get('event', '')
        event_type = bharat_event.get('type', '')
        event_extras = bharat_event.get('extras', '')
        extras_suffix = f" ({event_extras})" if event_extras else ""
        type_prefix = f" [{event_type}]" if event_type else ""
        indian_holidays.append(f"• 🌟 <b>{html.escape(event_name, quote=False)}</b>{type_prefix}{extras_suffix}")

    for h in holidays:
        text = h.get('text', '')
        if is_indian_context(text):
            indian_holidays.append(f"• {html.escape(text, quote=False)}")
            
    if indian_holidays:
        sections_text += "🎉 <b>Indian Festivals & Holidays</b>\n"
        sections_text += "\n".join(indian_holidays[:5]) + "\n\n"

    return sections_text

def send_telegram_message(token, chat_id, message_text):
    """
    Sends the formatted message to Telegram. Handles message splitting 
    at paragraph boundaries if the content exceeds Telegram's 4096-character limit.
    """
    # Split text into paragraphs/sections at natural double newline boundaries
    paragraphs = message_text.split("\n\n")
    chunks = []
    current_chunk = []
    current_len = 0
    
    for para in paragraphs:
        # If adding this paragraph exceeds 4000 characters, ship the current chunk
        if current_len + len(para) + 2 > 4000:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_len = len(para)
        else:
            current_chunk.append(para)
            current_len += len(para) + 2
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    success = True
    
    # Send each chunk as a separate message
    for i, chunk in enumerate(chunks, 1):
        # Clean trailing/leading spaces
        chunk = chunk.strip()
        if not chunk:
            continue
            
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            logger.info(f"Sending message chunk {i}/{len(chunks)} to Telegram (length {len(chunk)})...")
            response = http_session.post(url, json=payload, timeout=15)
            response_json = response.json()
            if response.status_code == 200 and response_json.get("ok"):
                logger.info(f"Chunk {i} sent successfully!")
            else:
                logger.error(f"Failed to send Telegram chunk {i}: {response_json}")
                success = False
        except Exception as e:
            logger.error(f"Error sending Telegram chunk {i}: {e}")
            success = False
            
    return success

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
    city = os.environ.get("CITY", "mumbai").lower()
    panchang_data = fetch_panchang(date_str, city=city)
    wiki_data = fetch_wikipedia_events(month_str, day_str)
    bharat_event = fetch_bharat_festival(now_ist)

    # 3. Format message
    header = f"📅 <b>DAILY UPDATE: {readable_date}</b>\n\n"
    panchang_text = format_panchang(panchang_data)
    wiki_text = format_wikipedia_section(wiki_data, bharat_event=bharat_event)
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
