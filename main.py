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
from PIL import Image, ImageDraw, ImageFont

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

def fetch_panchang(date_str, city="mumbai", lat=None, lng=None):
    """
    Fetches Hindu Almanac (Panchang) details for the specified date and city or coordinates.
    """
    url = "https://nityapanchangam.com/api/panchangam.php"
    params = {"date": date_str}
    if lat and lng:
        params["lat"] = lat
        params["lng"] = lng
        location_log = f"coordinates: {lat}, {lng}"
    else:
        params["city"] = city
        location_log = f"city: {city}"
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        logger.info(f"Fetching Panchang for {date_str} in {location_log}...")
        response = http_session.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching Panchang: {e}")
        return None


def get_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        try:
            return ImageFont.load_default(size=size)  # Pillow 10+
        except Exception:
            return ImageFont.load_default()

def get_text_width(text, font):
    if hasattr(font, "getlength"):
        return font.getlength(text)
    elif hasattr(font, "getsize"):
        return font.getsize(text)[0]
    else:
        return len(text) * 6

def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        if get_text_width(test_line, font) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return lines

def get_filtered_events(wiki_data):
    events = wiki_data.get('events', []) + wiki_data.get('selected', [])
    indian_events = []
    seen = set()
    for e in events:
        text = e.get('text', '')
        if text not in seen and is_indian_context(text):
            seen.add(text)
            indian_events.append({"year": e.get('year', ''), "text": text})
    return indian_events[:5]

def get_filtered_births(wiki_data):
    births = wiki_data.get('births', [])
    indian_births = []
    for b in births:
        text = b.get('text', '')
        if is_indian_context(text):
            indian_births.append({"year": b.get('year', ''), "text": text})
    return indian_births[:4]

def get_filtered_deaths(wiki_data):
    deaths = wiki_data.get('deaths', [])
    indian_deaths = []
    for d in deaths:
        text = d.get('text', '')
        if is_indian_context(text):
            indian_deaths.append({"year": d.get('year', ''), "text": text})
    return indian_deaths[:4]

def get_filtered_holidays(wiki_data, bharat_event=None):
    holidays = wiki_data.get('holidays', [])
    indian_holidays = []
    if bharat_event:
        name = bharat_event.get('event', '')
        etype = bharat_event.get('type', '')
        extras = bharat_event.get('extras', '')
        suffix = f" ({extras})" if extras else ""
        tprefix = f" [{etype}]" if etype else ""
        indian_holidays.append(f"🌟 {name}{tprefix}{suffix}")
    for h in holidays:
        text = h.get('text', '')
        if is_indian_context(text):
            indian_holidays.append(text)
    return indian_holidays[:4]

def generate_infographic_card(city, date_str, panchang_data, wiki_data, bharat_event=None):
    """
    Generates a beautiful daily infographic image card containing all sections.
    """
    # Create a dark-themed canvas (800 x 1360)
    width, height = 800, 1360
    bg_color = (15, 23, 42)  # #0F172A Slate-900
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Colors
    card_bg = (30, 41, 59) # #1E293B Slate-800
    border_color = (74, 85, 104) # #4A5568
    text_primary = (241, 245, 249) # #F1F5F9 Slate-50
    text_secondary = (148, 163, 184) # #94A3B8 Slate-400
    
    # Fonts
    bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    reg_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    title_font = get_font(bold_path, 28)
    sub_font = get_font(reg_path, 18)
    section_title_font = get_font(bold_path, 18)
    content_font = get_font(reg_path, 15)
    content_bold_font = get_font(bold_path, 15)
    footer_font = get_font(reg_path, 16)
    
    # Draw Outer Border
    draw.rectangle([15, 15, width-15, height-15], outline=border_color, width=2)
    
    # Draw Header Section
    draw.text((40, 35), "DAILY SPECIAL UPDATE", font=title_font, fill=text_primary)
    draw.text((40, 70), f"{city.upper()}  •  {date_str}", font=sub_font, fill=text_secondary)
    draw.line([30, 100, width-30, 100], fill=border_color, width=1)
    
    # Card 1: HINDU ALMANAC (x: 30 to 770, y: 120 to 330)
    draw.rounded_rectangle([30, 120, 770, 330], radius=10, fill=card_bg)
    draw.text((50, 135), "🕉 HINDU ALMANAC (PANCHANG)", font=section_title_font, fill=(245, 158, 11)) # Amber-500
    
    if panchang_data:
        vara = panchang_data.get('vara', {}).get('name', 'N/A')
        tithi = panchang_data.get('tithi', {}).get('name', 'N/A')
        nakshatra = panchang_data.get('nakshatra', {}).get('name', 'N/A')
        yoga = panchang_data.get('yoga', {}).get('name', 'N/A')
        karana = panchang_data.get('karana', {}).get('name', 'N/A')
        sun = panchang_data.get('sun', {})
        sunrise = sun.get('sunrise', 'N/A')
        sunset = sun.get('sunset', 'N/A')
        muhurta = panchang_data.get('muhurta', {})
        rahu = muhurta.get('rahu_kalam', 'N/A')
        abhijit = muhurta.get('abhijit_muhurtam', 'N/A')
        
        # Left Column (Vara, Tithi, Nakshatra, Yoga / Karana)
        p_y_left = 175
        p_items_left = [
            ("Vara (Day)", vara),
            ("Tithi", tithi),
            ("Nakshatra", nakshatra),
            ("Yoga / Karana", f"{yoga} / {karana}")
        ]
        for label, val in p_items_left:
            draw.text((50, p_y_left), f"{label}:", font=content_bold_font, fill=text_secondary)
            draw.text((180, p_y_left), str(val), font=content_font, fill=text_primary)
            p_y_left += 32
            
        # Right Column (Sunrise/Sunset, Abhijit Muhurta, Rahu Kalam)
        p_y_right = 175
        p_items_right = [
            ("Sunrise / Sunset", f"{sunrise} / {sunset}"),
            ("Abhijit Muh.", abhijit),
            ("Rahu Kalam", rahu)
        ]
        for label, val in p_items_right:
            draw.text((420, p_y_right), f"{label}:", font=content_bold_font, fill=text_secondary)
            draw.text((570, p_y_right), str(val), font=content_font, fill=text_primary)
            p_y_right += 32
    else:
        draw.text((50, 175), "Data not available", font=content_font, fill=text_secondary)

    # Card 2: HISTORICAL EVENTS (x: 30 to 770, y: 350 to 760)
    draw.rounded_rectangle([30, 350, 770, 760], radius=10, fill=card_bg)
    draw.text((50, 370), "🏛 HISTORICAL EVENTS", font=section_title_font, fill=(20, 184, 166)) # Teal-500
    
    ev_y = 410
    events_list = get_filtered_events(wiki_data) if wiki_data else []
    if events_list:
        for ev in events_list:
            year = ev['year']
            text = ev['text']
            prefix = f"• [{year}]  " if year else "• "
            
            draw.text((50, ev_y), prefix, font=content_bold_font, fill=(99, 102, 241)) # Indigo-500
            prefix_width = get_text_width(prefix, content_bold_font)
            
            wrapped_lines = wrap_text(text, content_font, width - 100 - prefix_width)
            for j, line in enumerate(wrapped_lines):
                draw.text((50 + prefix_width, ev_y), line, font=content_font, fill=text_primary)
                if j < len(wrapped_lines) - 1:
                    ev_y += 20
            ev_y += 26
    else:
        draw.text((50, ev_y), "No major historical events recorded on this day.", font=content_font, fill=text_secondary)

    # Card 3: BIRTH ANNIVERSARIES (x: 30 to 385, y: 780 to 1090)
    draw.rounded_rectangle([30, 780, 385, 1090], radius=10, fill=card_bg)
    draw.text((50, 800), "🎂 BIRTH ANNIVERSARIES", font=section_title_font, fill=(236, 72, 153)) # Pink-500
    
    b_y = 840
    births_list = get_filtered_births(wiki_data) if wiki_data else []
    if births_list:
        for b in births_list:
            year = b['year']
            text = b['text']
            prefix = f"• [{year}] " if year else "• "
            
            draw.text((50, b_y), prefix, font=content_bold_font, fill=text_secondary)
            pref_w = get_text_width(prefix, content_bold_font)
            
            wrapped = wrap_text(text, content_font, 335 - pref_w)
            for j, line in enumerate(wrapped):
                draw.text((50 + pref_w, b_y), line, font=content_font, fill=text_primary)
                if j < len(wrapped) - 1:
                    b_y += 18
            b_y += 26
    else:
        draw.text((50, b_y), "None recorded.", font=content_font, fill=text_secondary)

    # Card 4: REMEMBRANCE DAYS (x: 415 to 770, y: 780 to 1090)
    draw.rounded_rectangle([415, 780, 770, 1090], radius=10, fill=card_bg)
    draw.text((435, 800), "🕯 REMEMBRANCE DAYS", font=section_title_font, fill=(168, 85, 247)) # Purple-500
    
    d_y = 840
    deaths_list = get_filtered_deaths(wiki_data) if wiki_data else []
    if deaths_list:
        for d in deaths_list:
            year = d['year']
            text = d['text']
            prefix = f"• [{year}] " if year else "• "
            
            draw.text((435, d_y), prefix, font=content_bold_font, fill=text_secondary)
            pref_w = get_text_width(prefix, content_bold_font)
            
            wrapped = wrap_text(text, content_font, 335 - pref_w)
            for j, line in enumerate(wrapped):
                draw.text((435 + pref_w, d_y), line, font=content_font, fill=text_primary)
                if j < len(wrapped) - 1:
                    d_y += 18
            d_y += 26
    else:
        draw.text((435, d_y), "None recorded.", font=content_font, fill=text_secondary)

    # Card 5: FESTIVALS & HOLIDAYS (x: 30 to 770, y: 1110 to 1300)
    draw.rounded_rectangle([30, 1110, 770, 1300], radius=10, fill=card_bg)
    draw.text((50, 1130), "🎉 FESTIVALS & HOLIDAYS", font=section_title_font, fill=(16, 185, 129)) # Green-500
    
    h_y = 1170
    holidays_list = get_filtered_holidays(wiki_data, bharat_event=bharat_event) if wiki_data or bharat_event else []
    if holidays_list:
        for h in holidays_list:
            prefix = "• "
            draw.text((50, h_y), prefix, font=content_bold_font, fill=text_secondary)
            pref_w = get_text_width(prefix, content_bold_font)
            
            wrapped = wrap_text(h, content_font, width - 100 - pref_w)
            for j, line in enumerate(wrapped):
                draw.text((50 + pref_w, h_y), line, font=content_font, fill=text_primary)
                if j < len(wrapped) - 1:
                    h_y += 18
            h_y += 24
    else:
        draw.text((50, h_y), "No major festivals or holidays scheduled today.", font=content_font, fill=text_secondary)
        
    # Footer Section
    footer_text = "✨ Have a blessed and wonderful day ahead! ✨"
    f_w = get_text_width(footer_text, footer_font)
    draw.text(((width - f_w) // 2, 1320), footer_text, font=footer_font, fill=(245, 158, 11)) # Amber-500
    
    # Save image
    out_path = "daily_card.png"
    try:
        img.save(out_path)
        logger.info(f"Daily infographic card generated successfully at {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"Failed to save infographic card image: {e}")
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
        f"🕉 <b>HINDU ALMANAC (PANCHANG)</b>\n"
        f"• <b>Vara (Day):</b> <code>{html.escape(vara, quote=False)}</code>\n"
        f"• <b>Tithi:</b> <code>{html.escape(tithi, quote=False)}</code>\n"
        f"• <b>Nakshatra:</b> <code>{html.escape(nakshatra, quote=False)}</code>\n"
        f"• <b>Yoga / Karana:</b> <code>{html.escape(yoga, quote=False)}</code> / <code>{html.escape(karana, quote=False)}</code>\n\n"
        f"🌅 <b>SUN TIMINGS</b>\n"
        f"• <b>Sunrise:</b> <code>{html.escape(sunrise, quote=False)}</code> | <b>Sunset:</b> <code>{html.escape(sunset, quote=False)}</code>\n\n"
        f"⏱ <b>DAILY MUHURTAS</b>\n"
        f"• 🟢 <b>Abhijit Muhurta:</b> <code>{html.escape(abhijit, quote=False)}</code>\n"
        f"• 🔴 <b>Rahu Kalam:</b> <code>{html.escape(rahu_kalam, quote=False)}</code>\n\n"
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
            year_prefix = f"<code>{year}</code> — " if year else ""
            indian_events.append(f"• {year_prefix}{html.escape(text, quote=False)}")
    
    if indian_events:
        sections_text += "🏛 <b>HISTORICAL EVENTS</b>\n"
        sections_text += "\n".join(indian_events[:7]) + "\n\n"  # limit to top 7
    
    # 2. Notable births (India)
    births = wiki_data.get('births', [])
    indian_births = []
    for b in births:
        text = b.get('text', '')
        if is_indian_context(text):
            year = b.get('year', '')
            year_prefix = f"<code>{year}</code> — " if year else ""
            indian_births.append(f"• {year_prefix}{html.escape(text, quote=False)}")
            
    if indian_births:
        sections_text += "🎂 <b>BIRTH ANNIVERSARIES</b>\n"
        sections_text += "\n".join(indian_births[:5]) + "\n\n"  # limit to top 5

    # 3. Notable deaths (India)
    deaths = wiki_data.get('deaths', [])
    indian_deaths = []
    for d in deaths:
        text = d.get('text', '')
        if is_indian_context(text):
            year = d.get('year', '')
            year_prefix = f"<code>{year}</code> — " if year else ""
            indian_deaths.append(f"• {year_prefix}{html.escape(text, quote=False)}")
            
    if indian_deaths:
        sections_text += "🕯 <b>REMEMBRANCE DAYS</b>\n"
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
        sections_text += "🎉 <b>FESTIVALS & HOLIDAYS</b>\n"
        sections_text += "\n".join(indian_holidays[:5]) + "\n\n"

    return sections_text

def send_telegram_message(token, chat_id, message_text, photo_path=None, caption=None):
    """
    Sends the formatted message to Telegram. Handles message splitting 
    at paragraph boundaries if the content exceeds Telegram's 4096-character limit.
    If photo_path is provided, it first sends the photo using sendPhoto.
    """
    success = True

    # 1. Send the photo card first if provided
    if photo_path and os.path.exists(photo_path):
        photo_url = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            logger.info(f"Sending infographic card {photo_path} to Telegram...")
            with open(photo_path, "rb") as f:
                files = {"photo": f}
                payload = {
                    "chat_id": chat_id,
                    "caption": caption or "🗓 <b>DAILY UPDATE</b>",
                    "parse_mode": "HTML"
                }
                response = http_session.post(photo_url, data=payload, files=files, timeout=25)
                response_json = response.json()
                if response.status_code == 200 and response_json.get("ok"):
                    logger.info("Infographic card sent successfully!")
                else:
                    logger.error(f"Failed to send Telegram photo: {response_json}")
                    success = False
        except Exception as e:
            logger.error(f"Error sending Telegram photo: {e}")
            success = False

    # 2. Split text into paragraphs/sections at natural double newline boundaries
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

    # 2. Parse GPS coordinates if set in environment
    lat_env = os.environ.get("LAT")
    lng_env = os.environ.get("LNG")
    lat, lng = None, None
    if lat_env and lng_env:
        try:
            lat = float(lat_env)
            lng = float(lng_env)
            logger.info(f"Using custom GPS Coordinates: {lat}, {lng}")
        except ValueError as e:
            logger.error(f"Error parsing LAT/LNG environment variables: {e}")

    # 3. Fetch data
    city = os.environ.get("CITY", "mumbai").lower()
    panchang_data = fetch_panchang(date_str, city=city, lat=lat, lng=lng)
    wiki_data = fetch_wikipedia_events(month_str, day_str)
    bharat_event = fetch_bharat_festival(now_ist)

    # 4. Generate Infographic Card
    display_location = f"({lat}, {lng})" if (lat is not None and lng is not None) else city
    photo_path = generate_infographic_card(display_location, readable_date, panchang_data, wiki_data, bharat_event)

    # 5. Format message (Backup text version printed to local stdout log)
    display_location_upper = display_location.upper()
    header = (
        f"🗓 <b>DAILY UPDATE • {display_location_upper}</b>\n"
        f"<i>{readable_date}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    panchang_text = format_panchang(panchang_data)
    
    # Prepend a divider before wiki_text if live data was successfully fetched
    divider = "━━━━━━━━━━━━━━━━━━━━\n\n" if panchang_data else ""
    wiki_text = format_wikipedia_section(wiki_data, bharat_event=bharat_event)
    
    footer_divider = "━━━━━━━━━━━━━━━━━━━━\n"
    footer = f"{footer_divider}✨ <i>Have a blessed and wonderful day ahead!</i>"
    
    full_message = f"{header}{panchang_text}{divider}{wiki_text}{footer}"
    
    # 6. Handle Telegram delivery
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    # Print message to stdout for local execution visibility
    print("\n--- FORMATTED TELEGRAM MESSAGE (BACKUP TEXT) ---")
    print(full_message)
    print("------------------------------------------------\n")
    
    if telegram_token and telegram_chat_id:
        photo_caption = (
            f"🗓 <b>DAILY UPDATE • {display_location_upper}</b>\n"
            f"<i>{readable_date}</i>\n\n"
            f"✨ <i>Have a blessed and wonderful day ahead!</i>"
        )
        # Send ONLY the graphical card image to Telegram to prevent duplication
        success = send_telegram_message(
            telegram_token, 
            telegram_chat_id, 
            message_text="", 
            photo_path=photo_path, 
            caption=photo_caption
        )
        if not success:
            sys.exit(1)
    else:
        logger.warning(
            "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables are not set. "
            "Skipping Telegram delivery. Backup text printed to stdout."
        )

if __name__ == "__main__":
    main()
