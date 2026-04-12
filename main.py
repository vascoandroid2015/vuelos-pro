import os
import requests
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# ==================== CONFIGURACIÓN ====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@Vuelos_Peninsula_Canarias_Penins"

PRECIO_MAXIMO = 95
DIAS_A_BUSCAR = 35

ISLAS = ["fue", "ace"]
PENINSULA = ["bio", "vit", "eas", "ovd"]

CIUDADES = {
    "fue": "Fuerteventura", "ace": "Lanzarote",
    "bio": "Bilbao", "vit": "Vitoria",
    "eas": "San Sebastián", "ovd": "Asturias"
}

# ==================== UTIL ====================

def enviar(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def limpiar(texto):
    try:
        return float(texto.replace("€", "").replace(",", "").replace(" ", "").strip())
    except:
        return None

# ==================== SCRAPING ====================

def buscar_google(page, o, d, fecha):
    url = f"https://www.google.com/travel/flights?q=Flights%20to%20{d}%20from%20{o}%20on%20{fecha};sc=1"
    precios = []

    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(2000)

        elementos = page.locator('div[aria-label*="€"]').all_text_contents()

        for p in elementos[:6]:
            precio = limpiar(p)
            if precio and precio > 20:
                precios.append(precio)

    except Exception as e:
        print("Google error:", e)

    return precios


def buscar_skyscanner(page, o, d, fecha):
    url = f"https://www.skyscanner.es/transport/flights/{o}/{d}/{fecha}/?adultsv2=1&cabinclass=economy&stops=1"
    precios = []

    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(6000)

        elementos = page.locator('[data-test-id="price"]').all_text_contents()

        for p in elementos[:6]:
            precio = limpiar(p)
            if precio:
                precios.append(precio)

    except Exception as e:
        print("Skyscanner error:", e)

    return precios


def buscar_kayak(page, o, d, fecha):
    url = f"https://www.kayak.es/flights/{o}-{d}/{fecha}?sort=bestflight_a&fs=stops=0,1"
    precios = []

    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(6000)

        elementos = page.locator('div[class*="price"]').all_text_contents()

        for p in elementos[:6]:
            precio = limpiar(p)
            if precio and precio > 20:
                precios.append(precio)

    except Exception as e:
        print("Kayak error:", e)

    return precios

# ==================== LOW COST DIRECTO ====================

def buscar_ryanair(o, d, fecha):
    precios = []
    url = f"https://www.ryanair.com/api/farfnd/3/oneWayFares/{o}/{d}/cheapestPerDay?outboundMonth={fecha[:7]}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()

        for dia in data.get("outboundFlights", []):
            if fecha in dia.get("dateOut", ""):
                precio = dia.get("price", {}).get("value")
                if precio:
                    precios.append(float(precio))

    except Exception as e:
        print("Ryanair error:", e)

    return precios


def buscar_vueling(o, d, fecha):
    precios = []
    url = f"https://www.vueling.com/es/reservar-vuelos/resultados?origin={o}&destination={d}&date={fecha}"

    try:
        r = requests.get(url, timeout=10)
        if "€" in r.text:
            import re
            encontrados = re.findall(r'(\\d{2,3})€', r.text)
            for p in encontrados[:3]:
                precios.append(float(p))

    except Exception as e:
        print("Vueling error:", e)

    return precios


def buscar_binter(o, d, fecha):
    precios = []
    url = f"https://www.bintercanarias.com/es/book?origin={o}&destination={d}&date={fecha}"

    try:
        r = requests.get(url, timeout=10)
        if "€" in r.text:
            import re
            encontrados = re.findall(r'(\\d{2,3})€', r.text)
            for p in encontrados[:3]:
                precios.append(float(p))

    except Exception as e:
        print("Binter error:", e)

    return precios

# ==================== CORE ====================

def buscar_vuelos():
    resultados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )

        page = context.new_page()

        print(f"Buscando vuelos < {PRECIO_MAXIMO}€...")

        for dias in range(1, DIAS_A_BUSCAR + 1):
            fecha = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")

            for o in ISLAS:
                for d in PENINSULA:

                    precios = (
                        buscar_google(page, o, d, fecha) +
                        buscar_skyscanner(page, o, d, fecha) +
                        buscar_kayak(page, o, d, fecha) +
                        buscar_ryanair(o, d, fecha) +
                        buscar_vueling(o, d, fecha) +
                        buscar_binter(o, d, fecha)
                    )

                    for precio in precios:
                        if precio and precio < PRECIO_MAXIMO:
                            resultados.append((precio, o, d, fecha))

            for o in PENINSULA:
                for d in ISLAS:

                    precios = (
                        buscar_google(page, o, d, fecha) +
                        buscar_skyscanner(page, o, d, fecha) +
                        buscar_kayak(page, o, d, fecha) +
                        buscar_ryanair(o, d, fecha) +
                        buscar_vueling(o, d, fecha) +
                        buscar_binter(o, d, fecha)
                    )

                    for precio in precios:
                        if precio and precio < PRECIO_MAXIMO:
                            resultados.append((precio, o, d, fecha))

        browser.close()

    resultados = list(set(resultados))
    return sorted(resultados, key=lambda x: x[0])[:5]

# ==================== OUTPUT ====================

def formatear(v):
    fecha = datetime.strptime(v[3], "%Y-%m-%d").strftime("%d/%m/%Y")
    return f"""✈️ <b>VUELO BARATO DETECTADO</b>

🛫 Origen: <b>{CIUDADES[v[1]]}</b>
🛬 Destino: <b>{CIUDADES[v[2]]}</b>
📅 Fecha: <b>{fecha}</b>

💰 Precio: <b>{v[0]}€</b>

🔗 https://www.google.com/travel/flights
"""

# ==================== MAIN ====================

if __name__ == "__main__":
    vuelos = buscar_vuelos()

    if vuelos:
        for v in vuelos:
            enviar(formatear(v))
    else:
        enviar(f"❌ No se encontraron vuelos por debajo de {PRECIO_MAXIMO}€.")
