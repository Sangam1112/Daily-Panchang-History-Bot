# Today Special Bot 📅🕉🇮🇳

A automated Python script designed to run daily on GitHub Actions to fetch today's special information (Hindu Almanac/Panchang & Indian Historical Events) and send a beautifully formatted digest to a Telegram chat.

## Features

- **Hindu Almanac (Panchang)**: Retrieves daily Vara (day), Tithi, Nakshatra, Yoga, Karana, Sun timings (Sunrise & Sunset), Rahu Kalam, and Abhijit Muhurta computed for Delhi, India. Uses the free public API of [Nitya Panchangam](https://nityapanchangam.com/api/).
- **Major Events (Indian Context)**: Fetches historical events, notable birth/death anniversaries, and festivals/holidays from Wikipedia's "On This Day" feed API, filtered dynamically using regular expressions for Indian history, personalities, and cultural terms.
- **Global Holidays**: Lists major international days, festivals, and global observances for the day.
- **Telegram Pushes**: Sends a clean HTML-formatted message to a specified Telegram channel, group, or direct chat using a Telegram Bot.
- **Automated Scheduling**: Scheduled to run daily at **08:47 AM IST** (03:17 AM UTC) using GitHub Actions.

---

## Output Preview

```html
📅 DAILY UPDATE: July 04, 2026 (Saturday)

🕉 Hindu Almanac (Panchang - New Delhi)
• Vara (Day): Saturday
• Tithi: Chaturthi (Krishna)
• Nakshatra: Dhanishta
• Yoga: Priti
• Karana: Bava
• Sun Times: Sunrise: 5:28 AM | Sunset: 7:23 PM
• Rahu Kalam: 7:12 AM – 8:57 AM
• Abhijit Muhurta: 12:02 PM – 12:50 PM

🇮🇳 Major Events in Indian History
• [1947] The "Indian Independence Bill" is presented before the British House of Commons...

🎂 Notable Birth Anniversaries (India)
• [1898] Gulzarilal Nanda, Indian politician (died 1998)
• [1897] Alluri Sitarama Raju, Indian activist (died 1924)

🕯 Notable Remembrance Days (India)
• [1902] Swami Vivekananda, Indian monk and saint (born 1863)
• [1963] Pingali Venkayya, Indian activist, designed the Flag of India (born 1876)

🎉 Indian Festivals & Holidays
• The first evening of Dree Festival... (Apatani people, Arunachal Pradesh, India)

🌍 Global Holidays & Observances
• Independence Day (United States)
...
```

---

## Setup & Deployment

### 1. Telegram Bot Setup
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Create a new bot by sending `/newbot` and follow the instructions to get your **HTTP API Token** (`TELEGRAM_BOT_TOKEN`).
3. Create a Telegram channel, group, or simply use your own direct chat.
4. Add the bot to your channel or group as an Administrator with send message permissions.
5. Get your chat/channel ID (`TELEGRAM_CHAT_ID`):
   - For a direct chat with your bot, search for `@userinfobot` or `@GetIDsBot` and send a message. It will reply with your ID.
   - For a channel or group, forward a message from the group/channel to `@GetIDsBot`. The channel ID usually starts with `-100`.

### 2. GitHub Configuration
1. Push this project folder to a new repository on GitHub.
2. Navigate to your repository page.
3. Go to **Settings** > **Secrets and variables** > **Actions**.
4. Click **New repository secret** and add the following:
   - **Name**: `TELEGRAM_BOT_TOKEN`
   - **Value**: *Your Telegram Bot API Token*
5. Add another secret:
   - **Name**: `TELEGRAM_CHAT_ID`
   - **Value**: *Your Telegram Chat/Channel ID*
6. Make sure GitHub Actions are enabled under **Settings** > **Actions** > **General** > **Actions permissions** > Select "Allow all actions and reusable workflows".

### 3. Workflow Details
The GitHub Actions workflow is defined in `.github/workflows/daily_update.yml`.
It is configured with a cron expression to execute at **03:17 UTC**, which maps exactly to **08:47 AM IST** (UTC + 5:30).
> [!NOTE]
> GitHub Actions schedules can sometimes be delayed by 10-30 minutes based on GitHub's internal job queues. To run the bot manually at any time, you can trigger it via the **Actions** tab on GitHub by clicking **Run workflow**.

---

## Running Locally

To test the script locally:

1. Clone this project repository.
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your environment variables (optional for local logs, required for actual Telegram message sending):
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   export TELEGRAM_CHAT_ID="your_chat_id"
   ```
4. Execute the python script:
   ```bash
   python main.py
   ```
   *If environment variables are missing, the script will output the compiled message directly to the console instead of sending it to Telegram.*

## License

This project utilizes:
- [Nitya Panchangam Free API](https://nityapanchangam.com/api/) (Attribution under CC-BY 4.0 license is required).
- Wikipedia On This Day API.
