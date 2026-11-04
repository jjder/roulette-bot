import os
import threading
import requests
import time
from collections import Counter
from flask import Flask

# Minimal web service required by Render.com free tier
app = Flask(__name__)

@app.route('/')
def home():
    return "Auto Roulette Bot is Running 24/7 on Free Web Service!"

# ================= CONFIGURATION =================
BOT_TOKEN = "9039066795:AAFdu2sSYHMfGoj8o0py7sxhUOx9POk8mwk"
# =================================================

BASE_API = "https://api-cs.casino.org/svc-evolution-game-events/api/autoroulette"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Origin": "https://www.casinoorg-india.com",
    "Referer": "https://www.casinoorg-india.com/india/casinoscores/auto-roulette/",
    "Accept": "application/json, text/plain, */*"
}

# European Roulette Clockwise Wheel Sequence
WHEEL_ORDER = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
    5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

def get_color_emoji(n):
    if n == 0:
        return "🟢"
    return "🔴" if n in RED_NUMBERS else "⚫"

def fetch_direct_spins(needed_count):
    """Fetch latest spins using page=0 and sort=desc for real-time accuracy"""
    results = []
    page = 0
    while len(results) < needed_count and page <= 2:
        url = f"{BASE_API}?page={page}&size=100&sort=desc"
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if not data:
                    break
                for item in data:
                    game_data = item.get("data", {})
                    outcome = game_data.get("result", {}).get("outcome", {})
                    if "number" in outcome and outcome.get("number") is not None:
                        num = int(outcome["number"])
                        results.append(num)
                page += 1
            else:
                break
        except Exception:
            break
    return results[:needed_count]

def find_wheel_empty_streaks(appeared_nums, gap_size=9):
    """Detect 9+ consecutive unhit numbers strictly following European wheel sequence"""
    extended_wheel = WHEEL_ORDER + WHEEL_ORDER
    n = len(WHEEL_ORDER)
    found_gaps = []
    
    current_run = []
    i = 0
    while i < n * 2:
        num = extended_wheel[i]
        if num not in appeared_nums:
            current_run.append(num)
        else:
            if len(current_run) >= gap_size:
                sub = current_run[:gap_size]
                if sub not in found_gaps:
                    found_gaps.append(current_run)
            current_run = []
        i += 1
        
    if len(current_run) >= gap_size:
        if current_run not in found_gaps:
            found_gaps.append(current_run)

    unique_gaps = []
    seen_sets = []
    for g in found_gaps:
        s = set(g)
        if not any(s.issubset(x) or x.issubset(s) for x in seen_sets):
            unique_gaps.append(g)
            seen_sets.append(s)

    return unique_gaps

def analyze_spins_request(count):
    spins = fetch_direct_spins(count)
    total = len(spins)
    
    if total < count:
        return f"⚠️ Server currently has {total} spins available. Please try again in a few moments."

    appeared_nums = set(spins)
    all_roulette_nums = set(range(0, 37))
    missing_nums = all_roulette_nums - appeared_nums

    missing_red = sorted(list(missing_nums.intersection(RED_NUMBERS)))
    missing_black = sorted(list(missing_nums.intersection(BLACK_NUMBERS)))
    is_zero_missing = 0 in missing_nums

    red_str = ", ".join(map(str, missing_red)) if missing_red else "All Hit"
    black_str = ", ".join(map(str, missing_black)) if missing_black else "All Hit"
    zero_str = "🟢 0 (Missing - Not Hit)" if is_zero_missing else "✅ 0 Hit"

    # Number repeated more than 2 times
    freq = Counter(spins).most_common(1)
    repeat_str = "No"
    if freq:
        top_num, top_count = freq[0]
        if top_count > 2:
            repeat_str = f"#{top_num} ({top_count}x)"

    # Last 10 Numbers (Live Flow)
    last_10 = spins[:10]
    last_10_str = " ➔ ".join([f"{get_color_emoji(x)}{x}" for x in last_10])

    # Wheel 9+ empty gaps logic
    gaps = find_wheel_empty_streaks(appeared_nums, gap_size=9)
    if gaps:
        gap_items = []
        for idx, g in enumerate(gaps, 1):
            formatted_nums = " ➔ ".join([f"{get_color_emoji(x)}{x}" for x in g])
            gap_items.append(f"<b>Zone {idx} ({len(g)} Consecutive Numbers):</b>\n{formatted_nums}")
        wheel_gap_report = "\n\n🎯 <b>Wheel Order 9+ Consecutive Empty Numbers:</b>\n" + "\n\n".join(gap_items)
    else:
        wheel_gap_report = "\n\n🎯 <b>Wheel Order 9+ Consecutive Gap:</b>\n❌ No 9-number consecutive empty gap found."

    msg = (
        f"🎡 <b>Last {count} Spins Live Analysis</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📜 <b>Last 10 Numbers:</b>\n{last_10_str}\n\n"
        f"🎲 <b>Total Missing Numbers:</b> {len(missing_nums)} / 37\n\n"
        f"🔴 <b>Missing RED ({len(missing_red)}):</b>\n<code>{red_str}</code>\n\n"
        f"⚫ <b>Missing BLACK ({len(missing_black)}):</b>\n<code>{black_str}</code>\n\n"
        f"🟢 <b>ZERO Status:</b> {zero_str}\n\n"
        f"🔁 <b>Number Repeated > 2 Times:</b> {repeat_str}"
        f"{wheel_gap_report}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    return msg

def get_menu_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🎯 25 Spins", "callback_data": "btn_25"},
                {"text": "🎯 30 Spins", "callback_data": "btn_30"}
            ],
            [
                {"text": "🎯 35 Spins", "callback_data": "btn_35"},
                {"text": "🎯 40 Spins", "callback_data": "btn_40"}
            ],
            [
                {"text": "🎯 45 Spins", "callback_data": "btn_45"},
                {"text": "🎯 50 Spins", "callback_data": "btn_50"}
            ]
        ]
    }

def send_telegram(chat_id, text, reply_markup=None):
    """Sends messages directly to the initiating user's chat_id"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=6)
    except Exception as e:
        print("Telegram Send Error:", e)

def answer_callback(callback_query_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_query_id}, timeout=4)
    except:
        pass

def bot_polling_loop():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=20"
            res = requests.get(url, timeout=25).json()
            for item in res.get("result", []):
                offset = item["update_id"] + 1

                # Handle inline button clicks
                if "callback_query" in item:
                    cq = item["callback_query"]
                    cb_data = cq.get("data")
                    user_chat_id = cq.get("message", {}).get("chat", {}).get("id")
                    answer_callback(cq.get("id"))

                    counts = {"btn_25": 25, "btn_30": 30, "btn_35": 35, "btn_40": 40, "btn_45": 45, "btn_50": 50}
                    if cb_data in counts and user_chat_id:
                        report = analyze_spins_request(counts[cb_data])
                        send_telegram(user_chat_id, report, get_menu_keyboard())

                # Handle incoming messages
                elif "message" in item:
                    msg = item["message"]
                    user_chat_id = msg.get("chat", {}).get("id")
                    msg_text = msg.get("text", "").strip()

                    if msg_text == "/start" and user_chat_id:
                        welcome = (
                            "👋 <b>Auto Roulette Wheel Tracker</b>\n\n"
                            "Select an option below to analyze live spins:\n"
                            "• Last 10 Numbers (Live Flow)\n"
                            "• Missing Red, Black & Zero numbers\n"
                            "• Repeated Numbers (> 2 times)\n"
                            "• 9 Consecutive empty slots in Wheel Sequence"
                        )
                        send_telegram(user_chat_id, welcome, get_menu_keyboard())
        except Exception:
            time.sleep(2)
        time.sleep(0.5)

# Run polling loop in background thread
threading.Thread(target=bot_polling_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
