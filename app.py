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

# 3 Dozens (12 Numbers Each)
DOZEN_1 = set(range(1, 13))   # 1 to 12
DOZEN_2 = set(range(13, 25))  # 13 to 24
DOZEN_3 = set(range(25, 37))  # 25 to 36

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

def get_color_emoji(n):
    if n == 0:
        return "🟢"
    return "🔴" if n in RED_NUMBERS else "⚫"

def fetch_direct_spins(needed_count=30):
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
                            dozen = "None"
                            parity = "Zero"
                        else:
                            color = "Red" if num in RED_NUMBERS else "Black"
                            parity = "Even" if num % 2 == 0 else "Odd"
                            if num in DOZEN_1:
                                dozen = "1st Dozen (1-12)"
                            elif num in DOZEN_2:
                                dozen = "2nd Dozen (13-24)"
                            else:
                                dozen = "3rd Dozen (25-36)"

                        spins.append({
                            "id": sid,
                            "number": num,
                            "color": color,
                            "dozen": dozen,
                            "parity": parity,
                            "time": settled_at
                        })
                        if len(spins) >= 1500:
                            break
    except Exception as e:
        print("Fetch 1500 Error:", e)
    return spins

def analyze_30_spins():
    spins = fetch_direct_spins(30)
    total = len(spins)
    
    if total < 30:
        return f"⚠️ હાલમાં સર્વર પાસે માત્ર {total} સ્પિન ઉપલબ્ધ છે. કૃપા કરીને થોડીવાર પછી પ્રયાસ કરો."

    # 1. તમામ 30 લેટેસ્ટ નંબર્સ (લાઈવ ક્રમ)
    all_30_str = " ➔ ".join([f"{get_color_emoji(x)}{x}" for x in spins])

    # 2. આવી ગયેલા નંબર્સ (Hit Numbers - Red અને Black અલગ)
    hit_set = set(spins)
    hit_red = sorted([n for n in hit_set if n in RED_NUMBERS])
    hit_black = sorted([n for n in hit_set if n in BLACK_NUMBERS])
    hit_red_str = ", ".join(map(str, hit_red)) if hit_red else "None"
    hit_black_str = ", ".join(map(str, hit_black)) if hit_black else "None"

    # 3. નહીં આવેલા નંબર્સ (Unhit Numbers - Red અને Black અલગ)
    all_36 = set(range(1, 37))
    unhit_36 = all_36 - hit_set
    unhit_red = sorted([n for n in unhit_36 if n in RED_NUMBERS])
    unhit_black = sorted([n for n in unhit_36 if n in BLACK_NUMBERS])
    unhit_red_str = ", ".join(map(str, unhit_red)) if unhit_red else "None"
    unhit_black_str = ", ".join(map(str, unhit_black)) if unhit_black else "None"

    # 4. Zero (0) હિટ સ્ટેટસ
    zero_count = spins.count(0)
    zero_status = f"YES (HIT - {zero_count}x)" if zero_count > 0 else "NO (NOT HIT)"

    # 5. 2 થી વધુ વખત આવેલા નંબર્સ (> 2 times)
    counts = Counter(spins)
    repeats = {num: cnt for num, cnt in counts.items() if cnt > 2}
    if repeats:
        repeat_list = [f"{get_color_emoji(num)}#{num} ({cnt}x)" for num, cnt in sorted(repeats.items(), key=lambda x: x[1], reverse=True)]
        repeat_str = ", ".join(repeat_list)
    else:
        repeat_str = "None"

    # 6. 1, 2, 3 ડઝન ટકાવારી અને કાઉન્ટ (0 સિવાય)
    d1_count = sum(1 for n in spins if n in DOZEN_1)
    d2_count = sum(1 for n in spins if n in DOZEN_2)
    d3_count = sum(1 for n in spins if n in DOZEN_3)
    non_zero_spins = d1_count + d2_count + d3_count

    d1_pct = (d1_count / non_zero_spins * 100) if non_zero_spins > 0 else 0
    d2_pct = (d2_count / non_zero_spins * 100) if non_zero_spins > 0 else 0
    d3_pct = (d3_count / non_zero_spins * 100) if non_zero_spins > 0 else 0

    msg = (
        f"📊 <b>ANALYTICS REPORT: LAST 30 SPINS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"1️⃣ <b>All 30 Spins Flow (Latest to Old):</b>\n"
        f"👉 {all_30_str}\n\n"
        f"2️⃣ <b>આવી ગયેલા નંબર્સ (Hit Numbers):</b>\n"
        f"🔴 <b>Red Hit:</b> <code>{hit_red_str}</code>\n"
        f"⚫ <b>Black Hit:</b> <code>{hit_black_str}</code>\n\n"
        f"3️⃣ <b>નહીં આવેલા નંબર્સ (Unhit Numbers):</b>\n"
        f"🔴 <b>Red Unhit:</b> <code>{unhit_red_str}</code>\n"
        f"⚫ <b>Black Unhit:</b> <code>{unhit_black_str}</code>\n\n"
        f"4️⃣ <b>Zero (0) Trigger:</b> <b>{zero_status}</b>\n\n"
        f"5️⃣ <b>૨ થી વધુ વખત આવેલા નંબર્સ (> 2 times):</b>\n"
        f"🔥 {repeat_str}\n\n"
        f"6️⃣ <b>Dozens Performance (Excluding 0):</b>\n"
        f"• <b>1st Dozen (1-12):</b> <code>{d1_pct:.1f}%</code> ({d1_count} spins)\n"
        f"• <b>2nd Dozen (13-24):</b> <code>{d2_pct:.1f}%</code> ({d2_count} spins)\n"
        f"• <b>3rd Dozen (25-36):</b> <code>{d3_pct:.1f}%</code> ({d3_count} spins)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return msg

def get_menu_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🎯 Last 30 Spins", "callback_data": "btn_30"}
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
    writer.writerow(["Spin_No", "Round_ID", "Winning_Number", "Color", "Dozen", "Odd_Even", "Settled_At"])
    for idx, s in enumerate(spins, 1):
        writer.writerow([idx, s["id"], s["number"], s["color"], s["dozen"], s["parity"], s["time"]])

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
                    elif cb_data == "btn_30" and user_chat_id:
                        report = analyze_30_spins()
                        send_telegram(user_chat_id, report, get_menu_keyboard())

                # Handle incoming messages
                elif "message" in item:
                    msg = item["message"]
                    user_chat_id = msg.get("chat", {}).get("id")
                    msg_text = msg.get("text", "").strip()

                    if user_chat_id:
                        if msg_text in ["/start", "start"]:
                            welcome = (
                                "👋 <b>Auto Roulette Wheel Tracker</b>\n\n"
                                "નીચે આપેલા વિકલ્પોમાંથી પસંદ કરો:\n"
                                "• 🎯 <b>Last 30 Spins:</b> ૩૦ સ્પિનનું સંપૂર્ણ લાઇવ એનાલિસિસ\n"
                                "• 📥 <b>Download 1500 Spins:</b> તાજેતરના ૧,૫૦૦ સ્પિનની Excel ડાઉનલોડ"
                            )
                            send_telegram(user_chat_id, welcome, get_menu_keyboard())
                        elif msg_text.lower() in ["/download", "download", "excel", "1500"]:
                            handle_download_1500(user_chat_id)
                        elif msg_text.lower() in ["/30", "30", "spin", "spins"]:
                            report = analyze_30_spins()
                            send_telegram(user_chat_id, report, get_menu_keyboard())
                        else:
                            send_telegram(user_chat_id, "🎲 નીચે આપેલા બટનનો ઉપયોગ કરો:", get_menu_keyboard())
        except Exception:
            time.sleep(2)
        time.sleep(0.5)

# Run polling loop in background thread for Gunicorn & Render compatibility
threading.Thread(target=bot_polling_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
