import os
import time
import threading
from collections import Counter
import requests
from flask import Flask

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9284967785:AAG5zzD1swVFRVD-JowIU3gx3PPF1XND9XY")
CHAT_IDS = [cid.strip() for cid in os.environ.get("CHAT_IDS", "").split(",") if cid.strip()]

# Part 1: Clockwise from 9 to 6 (18 numbers)
PART_1 = [9, 31, 14, 20, 1, 33, 16, 24, 5, 10, 23, 8, 30, 11, 36, 13, 27, 6]

# Part 2: Clockwise from 22 to 34 (18 numbers - excluding 0)
PART_2 = [22, 18, 29, 7, 28, 12, 35, 3, 26, 32, 15, 19, 4, 21, 2, 25, 17, 34]

# Roulette Color Mappings
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

# In-memory storage for spins
history = []

# ==================== FLASK KEEP-ALIVE SERVER (FOR RENDER) ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Roulette Bot 24/7 Keep-Alive Server is Active!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ==================== TELEGRAM DISPATCHER ====================
def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram dispatch error: {e}")

def get_window_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "Last 25", "callback_data": "win_25"},
                {"text": "Last 30", "callback_data": "win_30"},
                {"text": "Last 35", "callback_data": "win_35"}
            ],
            [
                {"text": "Last 40", "callback_data": "win_40"},
                {"text": "Last 45", "callback_data": "win_45"},
                {"text": "Last 50", "callback_data": "win_50"}
            ]
        ]
    }

# ==================== REPORT GENERATION LOGIC ====================
def generate_window_report(window_size):
    total_spins = len(history)
    if total_spins == 0:
        return "⚠️ *No spin data recorded yet.*"

    actual_window = min(window_size, total_spins)
    sub_history = history[-actual_window:]
    hit_set = set(sub_history)

    # 1. Last 10 Spins Numbers
    last_10 = history[-10:] if total_spins >= 10 else history
    last_10_str = ", ".join(map(str, reversed(last_10)))

    # 2. Overall Unhit Numbers in this window (1 to 36)
    all_36 = set(range(1, 37))
    unhit_36 = all_36 - hit_set
    unhit_red = sorted([n for n in unhit_36 if n in RED_NUMBERS])
    unhit_black = sorted([n for n in unhit_36 if n in BLACK_NUMBERS])

    unhit_red_str = ", ".join(map(str, unhit_red)) if unhit_red else "None"
    unhit_black_str = ", ".join(map(str, unhit_black)) if unhit_black else "None"

    # Zero Status
    zero_hit = 0 in hit_set
    zero_status = "YES (HIT)" if zero_hit else "NO (NOT HIT)"

    # 3. Repeated Numbers (>2 times)
    counts = Counter(sub_history)
    repeats = {num: cnt for num, cnt in counts.items() if cnt > 2}
    if repeats:
        repeat_list = [f"`{num}` ({cnt}x)" for num, cnt in sorted(repeats.items(), key=lambda x: x[1], reverse=True)]
        repeat_str = ", ".join(repeat_list)
    else:
        repeat_str = "None"

    # 4. Wheel Parts Performance & Part-Wise Unhit Numbers (Excluding 0)
    p1_count = sum(1 for n in sub_history if n in PART_1)
    p2_count = sum(1 for n in sub_history if n in PART_2)
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

    report = (
        f"📊 *ANALYTICS REPORT: LAST {actual_window} SPINS*\n"
        f"*(Total Database Spins: {total_spins})*\n\n"
        f"1️⃣ *Last 10 Spins Numbers:*\n"
        f"👉 `{last_10_str}`\n\n"
        f"2️⃣ *Overall Unhit Numbers (Last {actual_window} Spins):*\n"
        f"🔴 Red Unhit: `{unhit_red_str}`\n"
        f"⚫ Black Unhit: `{unhit_black_str}`\n"
        f"🟢 *Zero (0) Trigger:* `{zero_status}`\n\n"
        f"3️⃣ *Repeated Numbers (>2 times):*\n"
        f"🔥 {repeat_str}\n\n"
        f"4️⃣ *Wheel Parts Performance (Excluding 0):*\n"
        f"• *Part 1 (9 to 6):* `{p1_pct:.1f}%` ({p1_count} spins)\n"
        f"  🔴 Red Unhit: `{', '.join(p1_red) if p1_red else 'None'}`\n"
        f"  ⚫ Black Unhit: `{', '.join(p1_black) if p1_black else 'None'}`\n\n"
        f"• *Part 2 (22 to 34):* `{p2_pct:.1f}%` ({p2_count} spins)\n"
        f"  🔴 Red Unhit: `{', '.join(p2_red) if p2_red else 'None'}`\n"
        f"  ⚫ Black Unhit: `{', '.join(p2_black) if p2_black else 'None'}`"
    )
    return report

# ==================== LIVE SPIN INGESTION ====================
def process_new_spin(num):
    history.append(num)
    total = len(history)

    color = "RED" if num in RED_NUMBERS else ("BLACK" if num in BLACK_NUMBERS else "GREEN")
    current_part = "Part 1" if num in PART_1 else ("Part 2" if num in PART_2 else "Zero")

    alert_text = (
        f"🎯 *Live Result:* `{num}` ({color} | {current_part})\n"
        f"🔄 *Total Recorded:* `{total}`\n\n"
        f"👇 *Select Window to View Analysis:*"
    )

    for chat_id in CHAT_IDS:
        send_telegram_message(chat_id, alert_text, reply_markup=get_window_keyboard())

# ==================== TELEGRAM BOT POLLING ====================
def telegram_polling():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=20"
            res = requests.get(url, timeout=25).json()
            if "result" in res:
                for item in res["result"]:
                    offset = item["update_id"] + 1

                    # Handle Button Clicks
                    if "callback_query" in item:
                        cq = item["callback_query"]
                        cb_data = cq.get("data", "")
                        from_chat_id = cq["message"]["chat"]["id"]

                        if cb_data.startswith("win_"):
                            w_size = int(cb_data.replace("win_", ""))
                            report = generate_window_report(w_size)
                            send_telegram_message(from_chat_id, report, reply_markup=get_window_keyboard())

                    # Handle Direct Commands (e.g., /25, 25, 30)
                    elif "message" in item and "text" in item["message"]:
                        text = item["message"]["text"].strip()
                        m_chat_id = item["message"]["chat"]["id"]
                        if str(m_chat_id) not in CHAT_IDS:
                            CHAT_IDS.append(str(m_chat_id))

                        clean = text.replace("/", "")
                        if clean.isdigit():
                            report = generate_window_report(int(clean))
                            send_telegram_message(m_chat_id, report, reply_markup=get_window_keyboard())
                        else:
                            send_telegram_message(m_chat_id, "🎲 Use buttons below to inspect spins:", reply_markup=get_window_keyboard())
            time.sleep(1)
        except Exception as e:
            print(f"Telegram polling error: {e}")
            time.sleep(5)

# ==================== MAIN GAME ENGINE ====================
def tracker_loop():
    print("Roulette Analytics Engine running...")
    while True:
        try:
            # લાઈવ ડેટા ફીડ API સાથે કનેક્ટ કરવાની જગ્યા
            time.sleep(15)
        except Exception as e:
            print(f"Tracker error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=telegram_polling, daemon=True).start()
    tracker_loop()
