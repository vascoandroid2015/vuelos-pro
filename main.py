import os
import re
import requests
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

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

def enviar(msg):
    if not TOKEN:
        print("⚠️ TELEGRAM_TOKEN no configurado")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def limpiar(texto):
    if not texto:
        return None
    try:
        # Limpia símbolos y convierte a float
        num = re.sub(r'[^\d.,]', '', texto.strip())
        num = num.replace(',', '.')
        return float(num)
    except:
        return None

# ==================== BÚSQUEDAS ====================

def buscar_skyscanner(page, o, d, fecha):
    url = f"https://www.skyscanner.es/transport/flights/{o}/{d}/{fecha}/?adults=1&adultsv2=1&cabinclass=economy&rtn=0"
    precios = []
    try:
        page.goto(url, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)  # pequeño buffer para render

        # Selectores más resistentes 2026
        elementos = page.locator('div[data-testid*="price"], span[class*="price"], [class*="Price"]').all_text_contents()
        for p in elementos[:6]:  # más elementos por si hay varios
            precio = limpiar(p)
            if precio and precio > 10:
                precios.append(precio)
    except Exception as e:
        print(f"❌ Skyscanner error {o}-{d} {fecha}: {e}")
    return precios

def buscar_google(page, o, d, fecha):
    url = f"https://www.google.com/travel/flights?q=one%20way%20flights%20from%20{o}%20to%20{d}%20on%20{fecha}"
    precios = []
    try:
        page.goto(url, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(4000)

        # Selectores comunes en Google Flights
        elementos = page.locator('span[jsname="V67aGc"], div[class*="price"], span[class*="currency"]').all_text_contents()
        for p in elementos[:6]:
            precio = limpiar(p)
            if precio and precio > 10:
                precios.append(precio)
    except Exception as e:
        print(f"❌ Google error {o}-{d} {fecha}: {e}")
    return precios

def buscar_momondo(page, o, d, fecha):
    url = f"https://www.momondo.es/flight-search/{o}-{d}/{fecha}?sort=price_a"
    precios = []
    try:
        page.goto(url, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(4000)

        elementos = page.locator('span[class*="price"], div[class*="Price"]').all_text_contents()
        for p in elementos[:6]:
            precio = limpiar(p)
            if precio and precio > 10:
                precios.append(precio)
    except Exception as e:
        print(f"❌ Momondo error {o}-{d} {fecha}: {e}")
    return precios

def buscar_kayak(page, o, d, fecha):
    url = f"https://www.kayak.es/flights/{o}-{d}/{fecha}?sort=price_a"
    precios = []
    try:
        page.goto(url, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(4000)

        elementos = page.locator('[class*="price"], span[class*="Price"]').all_text_contents()
        for p in elementos[:6]:
            precio = limpiar(p)
            if precio and precio > 10:
                precios.append(precio)
    except Exception as e:
        print(f"❌ Kayak error {o}-{d} {fecha}: {e}")
    return precios

def buscar_vuelos():
    resultados = []
    
    with sync_playwright() as p:
        # Lanzar con argumentos anti-detección
        browser = p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print(f"🔍 Buscando vuelos < {PRECIO_MAXIMO}€ para los próximos {DIAS_A_BUSCAR} días...")

        for dias in range(1, DIAS_A_BUSCAR + 1):
            fecha = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
            print(f"→ Día +{dias} ({fecha})")

            for o in ISLAS:
                for d in PENINSULA:
                    precios = (buscar_skyscanner(page, o, d, fecha) +
                               buscar_google(page, o, d, fecha) +
                               buscar_momondo(page, o, d, fecha) +
                               buscar_kayak(page, o, d, fecha))
                    for precio in set(precios):  # evitar duplicados en misma búsqueda
                        if precio and precio < PRECIO_MAXIMO:
                            resultados.append((precio, o, d, fecha))

            for o in PENINSULA:
                for d in ISLAS:
                    precios = (buscar_skyscanner(page, o, d, fecha) +
                               buscar_google(page, o, d, fecha) +
                               buscar_momondo(page, o, d, fecha) +
                               buscar_kayak(page, o, d, fecha))
                    for precio in set(precios):
                        if precio and precio < PRECIO_MAXIMO:
                            resultados.append((precio, o, d, fecha))

        browser.close()

    # Eliminar duplicados y ordenar por precio
    resultados = list(set(resultados))
    resultados = sorted(resultados, key=lambda x: x[0])[:5]  # top 5 más baratos
    return resultados

def formatear(v):
    fecha = datetime.strptime(v[3], "%Y-%m-%d").strftime("%d/%m/%Y")
    return f"""✈️ <b>VUELO BARATO DETECTADO</b>

🛫 Origen: <b>{CIUDADES[v[1]]}</b>
🛬 Destino: <b>{CIUDADES[v[2]]}</b>
📅 Fecha: <b>{fecha}</b>

💰 Precio: <b>{v[0]:.0f}€</b> (encontrado en múltiples comparadores)

🔗 Buscar ahora: https://www.google.com/travel/flights
"""

if __name__ == "__main__":
    vuelos = buscar_vuelos()

    if vuelos:
        print(f"✅ Encontrados {len(vuelos)} vuelos baratos")
        for v in vuelos:
            msg = formatear(v)
            enviar(msg)
            print(msg)
    else:
        msg = f"❌ No se encontraron vuelos por debajo de {PRECIO_MAXIMO}€ en los próximos {DIAS_A_BUSCAR} días."
        enviar(msg)
        print(msg)