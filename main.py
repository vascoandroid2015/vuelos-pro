import os
import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MIN_PRECIO = 5000
MAX_PRECIO = 250000

def enviar(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ TELEGRAM no configurado")
        return
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def limpiar_precio(texto):
    try:
        num = re.sub(r'[^\d]', '', texto)
        return int(num) if num else None
    except:
        return None

def extraer_parcela(texto):
    texto = texto.lower()
    patrones = [r'(\d{2,5})\s?m2?', r'parcela\s?de?\s?(\d{2,5})', r'finca\s?de?\s?(\d{2,5})']
    for p in patrones:
        m = re.search(p, texto)
        if m:
            return m.group(1) + " m²"
    return "No especificado"

# ==================== MILANUNCIOS (con requests - más fiable) ====================
def milanuncios_requests():
    resultados = []
    url = "https://www.milanuncios.com/venta-de-casas-en-asturias/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
        print(f"Milanuncios requests → Código HTTP: {r.status_code}")
        
        if r.status_code != 200:
            print("   Bloqueado o error")
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select("article")[:60]
        print(f"   Milanuncios → {len(items)} anuncios encontrados con BeautifulSoup")

        for item in items:
            try:
                texto = item.get_text(" ", strip=True)
                precio = limpiar_precio(texto)
                link_tag = item.find("a")
                link = "https://www.milanuncios.com" + link_tag["href"] if link_tag else url

                if precio and MIN_PRECIO <= precio <= MAX_PRECIO:
                    resultados.append({
                        "titulo": texto[:160],
                        "precio": precio,
                        "link": link,
                        "fuente": "Milanuncios"
                    })
            except:
                continue
    except Exception as e:
        print(f"❌ Error Milanuncios requests: {e}")
    return resultados

# ==================== MAIN ====================
def main():
    print("🚀 Iniciando bot - Probando Milanuncios primero (más fácil de scrapear)...")

    todas = milanuncios_requests()

    # Si Milanuncios da 0, intentamos con Playwright (solo para debug)
    if len(todas) == 0:
        print("Milanuncios requests falló → probando Playwright en todos...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page()
            page.goto("https://www.milanuncios.com/venta-de-casas-en-asturias/", timeout=60000)
            page.wait_for_timeout(8000)
            page.screenshot(path="debug_milanuncios.png")
            browser.close()

    print(f"Total casas encontradas con precio válido: {len(todas)}")

    enviados = 0
    for item in todas[:15]:   # máximo 15 al día
        msg = f"""🏠 <b>CASA EN ASTURIAS</b> - {item['fuente']}

{item['titulo']}

💰 <b>{item['precio']:,} €</b>
🌳 Parcela: {extraer_parcela(item['titulo'])}

🔗 {item['link']}
"""
        enviar(msg)
        enviados += 1
        time.sleep(1.5)

    if enviados == 0:
        enviar("❌ Hoy no se encontraron casas baratas.\nPrueba la captura debug_milanuncios.png")
        print("❌ Sin resultados")
    else:
        print(f"✅ Enviadas {enviados} casas a Telegram")

if __name__ == "__main__":
    main()