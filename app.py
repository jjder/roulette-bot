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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9039066795:AAFdu2sSYHMfGoj8o0py7sxhUOx9POk8mwk")
# =================================================

BASE_API = "https://api-cs.casino.org/svc-evolution-game-events/api/autoroulette"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Origin": "https://www.casinoorg-india.com",
    "Referer": "https://www.casinoorg-india.com/india/casinoscores/auto-roulette/",
    "Accept": "application/json, text/plain, */*"
}

# Part 1: Clockwise from 9 to 6 (18 numbers)
PART_1 = [9, 31, 14, 20, 1, 33, 16, 24, 5, 10, 23, 8, 30, 11, 36, 13, 27, 6]

# Part 2: Clockwise from 22 to 34 (18 numbers - excluding 0)
PART_2 = [22, 18, 29, 7, 28, 12, 35, 3, 26, 32, 15, 19, 4, 21, 2, 25, 17, 34]

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

def analyze_spins_request(count):
    spins = fetch_direct_spins(count)
    total = len(spins)
    
    if total < count:
        return f"⚠️ Server currently has {total} spins available. Please try again in a few moments."

    hit_set = set(spins)

    # 1. Last 10 Spins Numbers (Live Flow)
    last_10 = spins[:10]
    last_10_str = " ➔ ".join([f"{get_color_emoji(x)}{x}" for x in last_10])

    # 2. Overall Unhit Numbers (1 to 36)
    all_36 = set(range(1, 37))
    unhit_36 = all_36 - hit_set
    unhit_red = sorted([n for n in unhit_36 if n in RED_NUMBERS])
    unhit_black = sorted([n for n in unhit_36 if n in BLACK_NUMBERS])

    red_str = ", ".join(map(str, unhit_red)) if unhit_red else "None"
    black_str = ", ".join(map(str, unhit_black)) if unhit_black else "None"

    # Zero Hit Trigger Status
    zero_hit = 0 in hit_set
    zero_status = "YES (HIT)" if zero_hit else "NO (NOT HIT)"

    # 3. Numbers repeated > 2 times (3 or more)
    counts = Counter(spins)
    repeats = {num: cnt for num, cnt in counts.items() if cnt > 2}
    if repeats:
        repeat_list = [f"#{num} ({cnt}x)" for num, cnt in sorted(repeats.items(), key=lambda x: x[1], reverse=True)]
        repeat_str = ", ".join(repeat_list)
    else:
        repeat_str = "None"

    # 4. Wheel Halves Performance & Part-Wise Unhit Numbers (Excluding 0)
    p1_count = sum(1 for n in spins if n in PART_1)
    p2_count = sum(1 for n in spins if n in PART_2)
    non_zero_spins = p1_count + p2_count

    p1_pct = (p1_count / non_zero_spins * 100) if non_zero_spins > 0 else 0
    p2_pct = (p2_count / non_zero_spins * 100) if non_zero_spins > 0 else 0

    # Part 1 Missing (Red & Black)
    p1_missing = [n for n in PART_1 if n not in hit_set]
    p1_red = [str(n) for n in p1_missing if n in RED_NUMBERS]
    p1_black = [str(n) for n in p1_missing if n in BLACK_NUMBERS]

    # Part 2 Missing (Red & Black - excluding 0)
    p2_missing = [n for n in PART_2 if n not in hit_set]
    p2_red = [str(n) for n in p2_missing if n in RED_NUMBERS]
    p2_black = [str(n) for n in p2_missing if n in BLACK_NUMBERS]

    p1_red_str = ", ".join(p1_red) if p1_red else "None"
    p1_black_str = ", ".join(p1_black) if p1_black else "None"
    p2_red_str = ", ".join(p2_red) if p2_red else "None"
    p2_black_str = ", ".join(p2_black) if p2_black else "None"

    msg = (
        f"📊 <b>ANALYTICS REPORT: LAST {count} SPINS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"1️⃣ <b>Last 10 Spins Numbers:</b>\n"
        f"👉 {last_10_str}\n\n"
        f"2️⃣ <b>Overall Unhit Numbers (Last {count} Spins):</b>\n"
        f"🔴 <b>Red Unhit:</b> <code>{red_str}</code>\n"
        f"⚫ <b>Black Unhit:</b> <code>{black_str}</code>\n"
        f"🟢 <b>Zero (0) Trigger:</b> <b>{zero_status}</b>\n\n"
        f"3️⃣ <b>Repeated Numbers (&gt;2 times):</b>\n"
        f"🔥 <code>{repeat_str}</code>\n\n"
        f"4️⃣ <b>Wheel Parts Performance (Excluding 0):</b>\n"
        f"• <b>Part 1 (9 to 6):</b> <code>{p1_pct:.1f}%</code> ({p1_count} spins)\n"
        f"  🔴 Red Unhit: <code>{p1_red_str}</code>\n"
        f"  ⚫ Black Unhit: <code>{p1_black_str}</code>\n\n"
        f"• <b>Part 2 (22 to 34):</b> <code>{p2_pct:.1f}%</code> ({p2_count} spins)\n"
        f"  🔴 Red Unhit: <code>{p2_red_str}</code>\n"
        f"  ⚫ Black Unhit: <code>{p2_black_str}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━"
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

                    if user_chat_id:
                        if msg_text == "/start":
                            welcome = (
                                "👋 <b>Auto Roulette Wheel Tracker</b>\n\n"
                                "Select an option below to analyze live spins:\n"
                                "• 1️⃣ Last 10 Numbers (Live Flow)\n"
                                "• 2️⃣ Unhit Red, Black & Zero Trigger Status\n"
                                "• 3️⃣ Numbers Repeated &gt; 2 Times\n"
                                "• 4️⃣ Wheel Halves (Part 1 vs Part 2) & Missing Numbers"
                            )
                            send_telegram(user_chat_id, welcome, get_menu_keyboard())
                        else:
                            clean_val = msg_text.replace("/", "")
                            if clean_val.isdigit() and int(clean_val) in [25, 30, 35, 40, 45, 50]:
                                report = analyze_spins_request(int(clean_val))
                                send_telegram(user_chat_id, report, get_menu_keyboard())
                            else:
                                send_telegram(user_chat_id, "🎲 Please use the buttons below to analyze spins:", get_menu_keyboard())
        except Exception:
            time.sleep(2)
        time.sleep(0.5)

# Run polling loop in background thread for Gunicorn & Render compatibility
threading.Thread(target=bot_polling_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
