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

def enviar(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def limpiar(texto):
    try:
        return float(texto.replace("€", "").replace(",", "").replace(" ", "").strip())
    except:
        return None

# ==================== BÚSQUEDA EN 4 WEBS ====================
def buscar_skyscanner(page, o, d, fecha):
    url = f"https://www.skyscanner.es/transport/flights/{o}/{d}/{fecha}/?adultsv2=1&cabinclass=economy"
    precios = []
    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(4500)
        elementos = page.locator('[data-test-id="price"]').all_text_contents()
        for p in elementos[:6]:
            precio = limpiar(p)
            if precio:
                precios.append(precio)
    except:
        pass
    return precios

def buscar_google(page, o, d, fecha):
    url = f"https://www.google.com/travel/flights?q=flights+from+{o}+to+{d}+on+{fecha}"
    precios = []
    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)
        elementos = page.locator('span[jsname="V67aGc"]').all_text_contents()
        for p in elementos[:6]:
            precio = limpiar(p)
            if precio:
                precios.append(precio)
    except:
        pass
    return precios

def buscar_momondo(page, o, d, fecha):
    url = f"https://www.momondo.es/flight-search/{o}-{d}/{fecha}?sort=price_a"
    precios = []
    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(4500)
        elementos = page.locator('span[class*="price"]').all_text_contents()
        for p in elementos[:6]:
            precio = limpiar(p)
            if precio:
                precios.append(precio)
    except:
        pass
    return precios

def buscar_kayak(page, o, d, fecha):
    url = f"https://www.kayak.es/flights/{o}-{d}/{fecha}?sort=price_a"
    precios = []
    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(4500)
        elementos = page.locator('[class*="price"]').all_text_contents()
        for p in elementos[:6]:
            precio = limpiar(p)
            if precio and precio > 5:
                precios.append(precio)
    except:
        pass
    return precios

def buscar_vuelos():
    resultados = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        
        print(f"🔍 Buscando vuelos < {PRECIO_MAXIMO}€ en los próximos {DIAS_A_BUSCAR} días...")

        for dias in range(1, DIAS_A_BUSCAR + 1):
            fecha = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
            
            # Islas → Península
            for o in ISLAS:
                for d in PENINSULA:
                    precios = (buscar_skyscanner(page, o, d, fecha) +
                               buscar_google(page, o, d, fecha) +
                               buscar_momondo(page, o, d, fecha) +
                               buscar_kayak(page, o, d, fecha))
                    for precio in precios:
                        if precio and precio < PRECIO_MAXIMO:
                            resultados.append((precio, o, d, fecha))
            
            # Península → Islas
            for o in PENINSULA:
                for d in ISLAS:
                    precios = (buscar_skyscanner(page, o, d, fecha) +
                               buscar_google(page, o, d, fecha) +
                               buscar_momondo(page, o, d, fecha) +
                               buscar_kayak(page, o, d, fecha))
                    for precio in precios:
                        if precio and precio < PRECIO_MAXIMO:
                            resultados.append((precio, o, d, fecha))

        browser.close()

    # Eliminar duplicados y ordenar por precio (más baratos primero)
    resultados = list(set(resultados))
    return sorted(resultados, key=lambda x: x[0])[:3]

def formatear(v):
    fecha = datetime.strptime(v[3], "%Y-%m-%d").strftime("%d/%m/%Y")
    return f"""✈️ <b>VUELO BARATO DETECTADO EN LOS PRÓXIMOS 35 DÍAS</b>

🛫 Origen: <b>{CIUDADES[v[1]]}</b>
🛬 Destino: <b>{CIUDADES[v[2]]}</b>
📅 Fecha: <b>{fecha}</b>

💰 Precio: <b>{v[0]}€</b> (comparado en Skyscanner, Google, Momondo y Kayak)

🔗 Ver vuelo: https://www.google.com/travel/flights
"""

if __name__ == "__main__":
    vuelos = buscar_vuelos()

    if vuelos:
        for v in vuelos:
            enviar(formatear(v))
    else:
        enviar(f"❌ No se encontraron vuelos por debajo de {PRECIO_MAXIMO}€ en los próximos {DIAS_A_BUSCAR} días.")
