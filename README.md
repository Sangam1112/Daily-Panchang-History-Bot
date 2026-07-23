# Today Event Bot 📅🕉🇮🇳

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Automated-orange.svg)

An automated Python system designed to run daily via **GitHub Actions** to fetch today's special information—including the **Hindu Almanac (Panchang)** & **Indian Historical Events**—and send a beautifully formatted digest + infographic card to your **Telegram** chat.

---

## 🌟 Features

- 🕉 **Hindu Almanac (Panchang)**: Daily Vara (day), Tithi, Nakshatra, Yoga, Karana, Sunrise & Sunset, Rahu Kalam, and Abhijit Muhurta computed for Mumbai, India (or custom coordinates).
- 🏛 **Indian Historical Events**: Fetches historical events, birth/death anniversaries, and Indian festivals/holidays from Wikipedia's "On This Day" feed API.
- 🖼 **Daily Infographic Dashboard**: Automatically generates a high-resolution dashboard card (`daily_card.png`) containing Panchang details and historical events, pushed directly to Telegram.
- 📲 **Telegram Integration**: Delivers clean HTML digests and image cards directly to your Telegram channel or group.
- ⏰ **Automated Deletion**: Cleans up previous daily updates from Telegram at **09:00 PM IST** daily via serverless GitHub Actions cycle.
- 🛡 **Resilient Architecture**: Built-in exponential backoff, request retries, and automatic message split guard (for Telegram's 4,096-character API limit).

---

## 📋 Sample Digest Preview

```html
🗓 DAILY UPDATE • MUMBAI
July 04, 2026 (Saturday)
━━━━━━━━━━━━━━━━━━━━

🕉 HINDU ALMANAC (PANCHANG)
• Vara (Day): Saturday
• Tithi: Chaturthi (Krishna)
• Nakshatra: Dhanishta
• Yoga / Karana: Priti / Bava

🌅 SUN TIMINGS
• Sunrise: 6:05 AM | Sunset: 7:20 PM

⏱ DAILY MUHURTAS
• 🟢 Abhijit Muhurta: 12:19 PM – 1:07 PM
• 🔴 Rahu Kalam: 7:45 AM – 9:24 AM

━━━━━━━━━━━━━━━━━━━━

🏛 HISTORICAL EVENTS
• 1947 — The "Indian Independence Bill" is presented before the British House of Commons...

🎂 BIRTH ANNIVERSARIES
• 1898 — Gulzarilal Nanda, Indian politician (died 1998)
• 1897 — Alluri Sitarama Raju, Indian activist (died 1924)

🕯 REMEMBRANCE DAYS
• 1902 — Swami Vivekananda, Indian monk and saint (born 1863)

🎉 FESTIVALS & HOLIDAYS
• Dree Festival (Apatani people, Arunachal Pradesh, India)
```

---

## 🚀 Setup & Deployment

### 1. Telegram Bot Setup
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Create a new bot (`/newbot`) and copy your **HTTP API Token** (`TELEGRAM_BOT_TOKEN`).
3. Add the bot to your channel/group as an Administrator.
4. Get your `TELEGRAM_CHAT_ID` using [@GetIDsBot](https://t.me/GetIDsBot).

### 2. GitHub Configuration
In your repository (`Settings` -> `Secrets and variables` -> `Actions`), add:
- `TELEGRAM_BOT_TOKEN`: *Your Telegram Bot API Token*
- `TELEGRAM_CHAT_ID`: *Your Telegram Chat / Channel ID*

---

## 💻 Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run main script locally
python main.py
```

---

## 📄 License
This project utilizes data from:
- [Nitya Panchangam API](https://nityapanchangam.com/api/) (CC-BY 4.0).
- Wikipedia On This Day API.


## ⏰ Automated Schedule
Scheduled to run daily at **08:28 AM IST** (02:58 AM UTC) via GitHub Actions.
