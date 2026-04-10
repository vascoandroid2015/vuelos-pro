import os
import requests
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# ==================== CONFIGURACIÓN ====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@Vuelos_Peninsula_Canarias_Penins"

PRECIO_MAXIMO = 95
DIAS_ANTELACION = 35

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
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def limpiar(texto):
    try:
        return float(texto.replace("€", "").replace(",", "").replace(" ", "").strip())
    except:
        return None

def buscar_skyscanner(page, o, d, fecha):
    url = f"https://www.skyscanner.es/transport/flights/{o}/{d}/{fecha}/?adultsv2=1&cabinclass=economy"
    precios = []
    try:
        page.goto(url, timeout=50000)
        page.wait_for_timeout(4000)
        elementos = page.locator('[data-test-id="price"]').all_text_contents()
        for p in elementos[:5]:
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
        page.goto(url, timeout=50000)
        page.wait_for_timeout(4500)
        elementos = page.locator('span[jsname="V67aGc"]').all_text_contents()
        for p in elementos[:5]:
            precio = limpiar(p)
            if precio:
                precios.append(precio)
    except:
        pass
    return precios

def buscar_vuelos():
    resultados = []
    fecha_objetivo = (datetime.now() + timedelta(days=DIAS_ANTELACION)).strftime("%Y-%m-%d")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        
        print(f"Buscando vuelos para el {fecha_objetivo} (+{DIAS_ANTELACION} días)...")
        
        # Islas → Península
        for o in ISLAS:
            for d in PENINSULA:
                precios = buscar_skyscanner(page, o, d, fecha_objetivo) + buscar_google(page, o, d, fecha_objetivo)
                for precio in precios:
                    if precio and precio < PRECIO_MAXIMO:
                        resultados.append((precio, o, d, fecha_objetivo))
        
        # Península → Islas
        for o in PENINSULA:
            for d in ISLAS:
                precios = buscar_skyscanner(page, o, d, fecha_objetivo) + buscar_google(page, o, d, fecha_objetivo)
                for precio in precios:
                    if precio and precio < PRECIO_MAXIMO:
                        resultados.append((precio, o, d, fecha_objetivo))

        browser.close()

    # Eliminar duplicados y ordenar por precio
    resultados = list(set(resultados))
    return sorted(resultados, key=lambda x: x[0])[:3], fecha_objetivo

def formatear(v):
    fecha = datetime.strptime(v[3], "%Y-%m-%d").strftime("%d/%m/%Y")
    return f"""✈️ <b>VUELO BARATO CON 35 DÍAS DE ANTELACIÓN</b>

🛫 Origen: <b>{CIUDADES[v[1]]}</b>
🛬 Destino: <b>{CIUDADES[v[2]]}</b>
📅 Fecha del vuelo: <b>{fecha}</b>

💰 Precio encontrado: <b>{v[0]}€</b>

🔗 Buscar vuelo: https://www.google.com/travel/flights
"""

if __name__ == "__main__":
    vuelos, fecha_objetivo = buscar_vuelos()

    if vuelos:
        for v in vuelos:
            enviar(formatear(v))
    else:
        # Mensaje cuando NO encuentra vuelos baratos
        fecha_formateada = datetime.strptime(fecha_objetivo, "%Y-%m-%d").strftime("%d/%m/%Y")
        enviar(f"""❌ <b>No se encontraron vuelos baratos</b>

📅 Fecha consultada: <b>{fecha_formateada}</b> 
⏳ Con {DIAS_ANTELACION} días de antelación

💸 No hay vuelos por debajo de {PRECIO_MAXIMO}€ en las rutas monitorizadas.""")
        enviar(f"❌ No se encontraron vuelos por debajo de {PRECIO_MAXIMO}€ en los próximos {DIAS_A_BUSCAR} días.")
