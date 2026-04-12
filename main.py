import os
import re
import requests
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# ==================== CONFIGURACIÓN ====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@Vuelos_Peninsula_Canarias_Penins"

PRECIO_MAXIMO = 95
DIAS_A_BUSCAR = 10   # reducido para pruebas rápidas

ISLAS = ["fue", "ace"]
PENINSULA = ["bio", "vit", "eas", "ovd"]

CIUDADES = {
    "fue": "Fuerteventura", "ace": "Lanzarote",
    "bio": "Bilbao", "vit": "Vitoria",
    "eas": "San Sebastián", "ovd": "Asturias"
}

def enviar(msg):
    if not TOKEN:
        print("⚠️ No hay TELEGRAM_TOKEN")
        return
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def limpiar(texto):
    if not texto: return None
    try:
        num = re.sub(r'[^\d.,]', '', texto)
        return float(num.replace(',', '.'))
    except:
        return None

def extraer_precios_google(page):
    precios = []
    try:
        # Selectores más actualizados para Google Flights 2026
        price_selectors = [
            'span[jsname="V67aGc"]', 
            'div[class*="price"]', 
            '[data-test-id="price"]',
            'span[class*="currency"]',
            'div[role="button"] span'  # fallback
        ]
        
        for selector in price_selectors:
            elements = page.locator(selector).all()
            for el in elements:
                text = el.inner_text().strip()
                if '€' in text or any(c in text for c in '0123456789'):
                    precio = limpiar(text)
                    if precio and 20 < precio < 300:
                        precios.append(precio)
        
        # Fallback: buscar cualquier número grande seguido de €
        if len(precios) < 3:
            all_text = page.locator('body').inner_text()
            matches = re.findall(r'(\d{1,3}(?:[.,]\d{1,2})?)\s*€', all_text)
            for m in matches:
                p = limpiar(m)
                if p: precios.append(p)
    except Exception as e:
        print(f"Error extrayendo precios: {e}")
    return list(set(precios))

def buscar_vuelos():
    resultados = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("🚀 Iniciando prueba de scraping solo con Google Flights...")

        for dias in range(1, DIAS_A_BUSCAR + 1):
            fecha = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
            print(f"\n📅 Probando fecha: {fecha}")

            for o in ISLAS:
                for d in PENINSULA:
                    try:
                        url = f"https://www.google.com/travel/flights?q=one%20way%20flights%20from%20{o}%20to%20{d}%20on%20{fecha}"
                        print(f"   → {o.upper()} → {d.upper()}")

                        page.goto(url, timeout=60000, wait_until="networkidle")
                        page.wait_for_timeout(8000)  # espera generosa para carga JS

                        # Simular comportamiento humano
                        page.mouse.move(500, 300)
                        page.wait_for_timeout(1000)
                        page.evaluate("window.scrollBy(0, 600)")
                        page.wait_for_timeout(3000)

                        precios = extraer_precios_google(page)

                        print(f"      Precios detectados: {precios[:10]}")

                        # Guardar captura de pantalla para depuración
                        screenshot_path = f"screenshot_{o}-{d}_{fecha}.png"
                        page.screenshot(path=screenshot_path, full_page=False)
                        print(f"      📸 Captura guardada: {screenshot_path}")

                        for precio in precios:
                            if precio < PRECIO_MAXIMO:
                                resultados.append((precio, o, d, fecha))

                    except Exception as e:
                        print(f"      ❌ Error en {o}-{d} {fecha}: {str(e)[:80]}")

        browser.close()

    resultados = sorted(list(set(resultados)), key=lambda x: x[0])[:5]
    return resultados

def formatear(v):
    fecha_fmt = datetime.strptime(v[3], "%Y-%m-%d").strftime("%d/%m/%Y")
    return f"""✈️ <b>VUELO BARATO ENCONTRADO</b>

🛫 {CIUDADES[v[1]]} → 🛬 {CIUDADES[v[2]]}
📅 {fecha_fmt}
💰 <b>{v[0]:.0f}€</b>

🔗 https://www.google.com/travel/flights"""

if __name__ == "__main__":
    vuelos = buscar_vuelos()

    if vuelos:
        print(f"✅ Encontrados {len(vuelos)} vuelos baratos!")
        for v in vuelos:
            msg = formatear(v)
            enviar(msg)
            print(msg)
    else:
        msg = f"❌ No se encontraron vuelos < {PRECIO_MAXIMO}€ en los próximos {DIAS_A_BUSCAR} días.\nRevisa las capturas de pantalla en los artifacts."
        enviar(msg)
        print(msg)
