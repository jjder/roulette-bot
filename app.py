import os
import threading
import requests
import time
import io
import csv
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

# 4 Groups (9 Numbers Each)
GROUP_1 = set(range(1, 10))   # 1 to 9
GROUP_2 = set(range(10, 19))  # 10 to 18
GROUP_3 = set(range(19, 28))  # 19 to 27
GROUP_4 = set(range(28, 37))  # 28 to 36

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

def get_color_emoji(n):
    if n == 0:
        return "🟢"
    return "🔴" if n in RED_NUMBERS else "⚫"

def fetch_direct_spins(needed_count):
    """Fetch latest spins for real-time analytics"""
    url = f"{BASE_API}?size={max(needed_count, 50)}&sort=desc"
    results = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            data = r.json()
            for item in data:
                game_data = item.get("data", {})
                outcome = game_data.get("result", {}).get("outcome", {})
                if "number" in outcome and outcome.get("number") is not None:
                    results.append(int(outcome["number"]))
    except Exception:
        pass
    return results[:needed_count]

def fetch_1500_spins():
    """Fetch exactly 1500 latest spins from server"""
    url = f"{BASE_API}?size=1500&sort=desc"
    spins = []
    seen_ids = set()
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            for item in data:
                game_data = item.get("data", {})
                sid = game_data.get("id")
                outcome = game_data.get("result", {}).get("outcome", {})
                settled_at = game_data.get("settledAt", "")
                
                if "number" in outcome and outcome.get("number") is not None:
                    num = int(outcome["number"])
                    if sid and sid not in seen_ids:
                        seen_ids.add(sid)
                        
                        if num == 0:
                            color = "Green"
                            group = "Zero"
                            parity = "Zero"
                        else:
                            color = "Red" if num in RED_NUMBERS else "Black"
                            parity = "Even" if num % 2 == 0 else "Odd"
                            if 1 <= num <= 9:
                                group = "1-9"
                            elif 10 <= num <= 18:
                                group = "10-18"
                            elif 19 <= num <= 27:
                                group = "19-27"
                            else:
                                group = "28-36"

                        spins.append({
                            "id": sid,
                            "number": num,
                            "color": color,
                            "group": group,
                            "parity": parity,
                            "time": settled_at
                        })
                        if len(spins) >= 1500:
                            break
    except Exception as e:
        print("Fetch 1500 Error:", e)
    return spins

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

    # 3. Repeated Numbers Logic
    counts = Counter(spins)
    if count == 25:
        repeats = {num: cnt for num, cnt in counts.items() if cnt >= 2}
        repeat_title = "Repeated Numbers (≥2 times):"
    else:
        repeats = {num: cnt for num, cnt in counts.items() if cnt > 2}
        repeat_title = "Repeated Numbers (>2 times):"

    if repeats:
        repeat_list = [f"#{num} ({cnt}x)" for num, cnt in sorted(repeats.items(), key=lambda x: x[1], reverse=True)]
        repeat_str = ", ".join(repeat_list)
    else:
        repeat_str = "None"

    # 4. 4 Groups Performance
    g1_count = sum(1 for n in spins if n in GROUP_1)
    g2_count = sum(1 for n in spins if n in GROUP_2)
    g3_count = sum(1 for n in spins if n in GROUP_3)
    g4_count = sum(1 for n in spins if n in GROUP_4)
    non_zero_spins = g1_count + g2_count + g3_count + g4_count

    g1_pct = (g1_count / non_zero_spins * 100) if non_zero_spins > 0 else 0
    g2_pct = (g2_count / non_zero_spins * 100) if non_zero_spins > 0 else 0
    g3_pct = (g3_count / non_zero_spins * 100) if non_zero_spins > 0 else 0
    g4_pct = (g4_count / non_zero_spins * 100) if non_zero_spins > 0 else 0

    msg = (
        f"📊 <b>ANALYTICS REPORT: LAST {count} SPINS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"1️⃣ <b>Last 10 Spins Numbers:</b>\n"
        f"👉 {last_10_str}\n\n"
        f"2️⃣ <b>Overall Unhit Numbers (Last {count} Spins):</b>\n"
        f"🔴 <b>Red Unhit:</b> <code>{red_str}</code>\n"
        f"⚫ <b>Black Unhit:</b> <code>{black_str}</code>\n"
        f"🟢 <b>Zero (0) Trigger:</b> <b>{zero_status}</b>\n\n"
        f"3️⃣ <b>{repeat_title}</b>\n"
        f"🔥 <code>{repeat_str}</code>\n\n"
        f"4️⃣ <b>4-Group Performance (Excluding 0):</b>\n"
        f"• <b>1 to 9:</b> <code>{g1_pct:.1f}%</code> ({g1_count} spins)\n"
        f"• <b>10 to 18:</b> <code>{g2_pct:.1f}%</code> ({g2_count} spins)\n"
        f"• <b>19 to 27:</b> <code>{g3_pct:.1f}%</code> ({g3_count} spins)\n"
        f"• <b>28 to 36:</b> <code>{g4_pct:.1f}%</code> ({g4_count} spins)\n"
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
            ],
            [
                {"text": "📥 Download 1500 Spins (Excel)", "callback_data": "btn_download_1500"}
            ]
        ]
    }

def send_telegram(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=6)
    except Exception as e:
        print("Telegram Send Error:", e)

def send_telegram_document(chat_id, csv_buffer, filename, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    files = {"document": (filename, csv_buffer.getvalue().encode('utf-8'), "text/csv")}
    data = {"chat_id": chat_id, "caption": caption}
    try:
        requests.post(url, data=data, files=files, timeout=20)
    except Exception as e:
        print("Telegram Document Send Error:", e)

def answer_callback(callback_query_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_query_id}, timeout=4)
    except:
        pass

def handle_download_1500(chat_id):
    send_telegram(chat_id, "⏳ સર્વર પરથી તાજેતરના ૧,૫૦૦ સ્પિન ડાઉનલોડ થઈ રહ્યા છે, કૃપા કરીને થોડી સેકન્ડ રાહ જુઓ...")
    spins = fetch_1500_spins()
    
    if not spins:
        send_telegram(chat_id, "❌ સર્વર પરથી ડેટા ફેચ કરવામાં ક્ષતિ આવી. કૃપા કરીને થોડીવાર પછી પ્રયાસ કરો.", get_menu_keyboard())
        return

    # જૂના થી નવા ક્રમમાં
    spins.reverse()

    # Create CSV in-memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Spin_No", "Round_ID", "Winning_Number", "Color", "Group", "Odd_Even", "Settled_At"])
    for idx, s in enumerate(spins, 1):
        writer.writerow([idx, s["id"], s["number"], s["color"], s["group"], s["parity"], s["time"]])

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"AutoRoulette_1500_Spins_{timestamp}.csv"
    caption = f"✅ Auto Roulette ના પૂરા {len(spins)} સ્પિનની Excel ફાઇલ તૈયાર છે!"
    
    send_telegram_document(chat_id, output, filename, caption)
    send_telegram(chat_id, "🎲 અન્ય એનાલિસિસ માટે નીચેના બટન પસંદ કરો:", get_menu_keyboard())

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

                    if cb_data == "btn_download_1500" and user_chat_id:
                        handle_download_1500(user_chat_id)
                    else:
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
                                "Select an option below to analyze live spins or export raw data:\n"
                                "• 1️⃣ Last 10 Numbers (Live Flow)\n"
                                "• 2️⃣ Unhit Red, Black & Zero Trigger Status\n"
                                "• 3️⃣ Repeated Numbers\n"
                                "• 4️⃣ 4-Group Breakdown (1-9, 10-18, 19-27, 28-36)\n"
                                "• 📥 Download 1500 Spins (Excel)"
                            )
                            send_telegram(user_chat_id, welcome, get_menu_keyboard())
                        elif msg_text.lower() in ["/download", "download", "excel", "1500"]:
                            handle_download_1500(user_chat_id)
                        else:
                            clean_val = msg_text.replace("/", "")
                            if clean_val.isdigit() and int(clean_val) in [25, 30, 35, 40, 45, 50]:
                                report = analyze_spins_request(int(clean_val))
                                send_telegram(user_chat_id, report, get_menu_keyboard())
                            else:
                                send_telegram(user_chat_id, "🎲 Please use the buttons below to analyze spins or download data:", get_menu_keyboard())
        except Exception:
            time.sleep(2)
        time.sleep(0.5)

# Run polling loop in background thread for Gunicorn & Render compatibility
threading.Thread(target=bot_polling_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
