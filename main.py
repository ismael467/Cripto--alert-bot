import os
import time
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
DROP_THRESHOLD = -5.0  # % caída
CHECK_INTERVAL = 60    # segundos entre checks
WINDOW_MINUTES = 15    # ventana de tiempo

price_history = {}  # {coin_id: [(timestamp, price), ...]}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"})

def get_top_100_prices():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        return r.json()
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return []

def check_drops():
    coins = get_top_100_prices()
    if not coins:
        return

    now = time.time()
    window = WINDOW_MINUTES * 60
    alerts_sent = 0

    for coin in coins:
        cid = coin["id"]
        price = coin["current_price"]
        if price is None:
            continue

        # Guardar historial
        if cid not in price_history:
            price_history[cid] = []
        price_history[cid].append((now, price))

        # Limpiar entradas viejas (más de 20 min)
        price_history[cid] = [(t, p) for t, p in price_history[cid] if now - t <= 1200]

        # Buscar precio hace ~15 min
        old_entries = [(t, p) for t, p in price_history[cid] if now - t >= window]
        if not old_entries:
            continue

        old_price = old_entries[0][1]  # el más antiguo dentro de la ventana
        if old_price == 0:
            continue

        pct_change = ((price - old_price) / old_price) * 100

        if pct_change <= DROP_THRESHOLD:
            name = coin["name"]
            symbol = coin["symbol"].upper()
            msg = (
                f"🚨 <b>ALERTA DE CAÍDA</b>\n"
                f"🪙 {name} ({symbol})\n"
                f"📉 Caída: <b>{pct_change:.2f}%</b> en 15 min\n"
                f"💵 Precio actual: ${price:,.4f}\n"
                f"🕐 {datetime.utcnow().strftime('%H:%M:%S')} UTC"
            )
            send_telegram(msg)
            alerts_sent += 1
            print(f"ALERTA enviada: {symbol} {pct_change:.2f}%")

    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Check OK — {len(coins)} monedas, {alerts_sent} alertas")

def main():
    send_telegram("✅ <b>Bot de alertas iniciado</b>\nMonitoreando Top 100 cripto — alerta si caída ≥ 5% en 15 min")
    print("Bot iniciado...")
    while True:
        check_drops()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
