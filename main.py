import os
import requests
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@Vuelos_Peninsula_Canarias_Penins"

ISLAS = ["fue", "ace"]
PENINSULA = ["bio", "vit", "eas", "ovd"]

CIUDADES = {
    "fue": "Fuerteventura",
    "ace": "Lanzarote",
    "bio": "Bilbao",
    "vit": "Vitoria",
    "eas": "San Sebastián",
    "ovd": "Asturias"
}

def enviar(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def limpiar(texto):
    return float(texto.replace("€", "").replace(",", "").strip())

def buscar_skyscanner(page, o, d, fecha):
    url = f"https://www.skyscanner.es/transport/flights/{o}/{d}/{fecha}/"
    precios = []

    try:
        page.goto(url, timeout=40000)
        page.wait_for_timeout(3000)

        elementos = page.locator('[data-test-id="price"]').all_text_contents()
        for p in elementos[:2]:
            precios.append(limpiar(p))
    except:
        pass

    return precios

def buscar_google(page, o, d, fecha):
    url = f"https://www.google.com/travel/flights?q=flights+{o}+to+{d}+{fecha}"
    precios = []

    try:
        page.goto(url, timeout=40000)
        page.wait_for_timeout(4000)

        elementos = page.locator('span[jsname="V67aGc"]').all_text_contents()
        for p in elementos[:2]:
            precios.append(limpiar(p))
    except:
        pass

    return precios

def buscar_vuelos():
    resultados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()

        # 🔥 SOLO 15 DÍAS → clave para GitHub gratis
        for dias in range(1, 16):
            fecha = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")

            for o in ISLAS:
                for d in PENINSULA:
                    precios = buscar_skyscanner(page, o, d, fecha) + buscar_google(page, o, d, fecha)

                    for precio in precios:
                        residente = round(precio * 0.25, 2)

                        if residente < 40:
                            resultados.append((precio, residente, o, d, fecha))

            for o in PENINSULA:
                for d in ISLAS:
                    precios = buscar_skyscanner(page, o, d, fecha) + buscar_google(page, o, d, fecha)

                    for precio in precios:
                        residente = round(precio * 0.25, 2)

                        if residente < 40:
                            resultados.append((precio, residente, o, d, fecha))

        browser.close()

    return sorted(resultados, key=lambda x: x[1])[:2]

def formatear(v):
    fecha = datetime.strptime(v[4], "%Y-%m-%d").strftime("%d/%m/%Y")

    return f"""✈️ VUELO BARATO DETECTADO

Origen: {CIUDADES[v[2]]}
Destino: {CIUDADES[v[3]]}
Fecha: {fecha}

💸 Precio normal: {v[0]}€
🏝️ Precio residente: {v[1]}€

🔗 Ver vuelo: https://www.google.com/travel/flights
"""

if __name__ == "__main__":
    vuelos = buscar_vuelos()

    if vuelos:
        for v in vuelos:
            enviar(formatear(v))
    else:
        enviar("❌ No hay vuelos baratos hoy")