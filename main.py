import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import requests
from playwright.sync_api import sync_playwright

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@Vuelos_Peninsula_Canarias_Penins")

PRECIO_MAXIMO = int(os.getenv("PRECIO_MAXIMO", "95"))
DIAS_A_BUSCAR = int(os.getenv("DIAS_A_BUSCAR", "35"))
TOP_RESULTADOS = int(os.getenv("TOP_RESULTADOS", "5"))
MAX_ESCALA_MINUTOS = int(os.getenv("MAX_ESCALA_MINUTOS", "1440"))

ISLAS = ["fue", "ace"]
PENINSULA = ["bio", "vit", "eas", "ovd"]

CIUDADES = {
    "fue": "Fuerteventura",
    "ace": "Lanzarote",
    "bio": "Bilbao",
    "vit": "Vitoria",
    "eas": "San Sebastián",
    "ovd": "Asturias",
}


def google_flights_url(origen: str, destino: str, fecha: str) -> str:
    q = quote_plus(
        f"one way flights from {origen} to {destino} on {fecha} with max layover {MAX_ESCALA_MINUTOS} minutes"
    )
    return f"https://www.google.com/travel/flights?q={q}"


FUENTES = {
    "google": google_flights_url,
    "skyscanner": lambda origen, destino, fecha: (
        f"https://www.skyscanner.es/transport/flights/{origen}/{destino}/{fecha}/"
        f"?adults=1&adultsv2=1&cabinclass=economy&rtn=0&max_stops=1&max_stopover_minutes={MAX_ESCALA_MINUTOS}"
    ),
    "momondo": lambda origen, destino, fecha: (
        f"https://www.momondo.es/flight-search/{origen}-{destino}/{fecha}?sort=price_a&fs=stops=-0,1;maxlayover={MAX_ESCALA_MINUTOS}"
    ),
    "kayak": lambda origen, destino, fecha: (
        f"https://www.kayak.es/flights/{origen}-{destino}/{fecha}?sort=price_a&fs=stops=-0,1;maxlayover={MAX_ESCALA_MINUTOS}"
    ),
}

SELECTORES_PRECIO = [
    '[data-testid*="price"]',
    '[class*="price"]',
    '[class*="Price"]',
    'span[jsname="V67aGc"]',
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/134.0.0.0 Safari/537.36"
)


def enviar(msg: str) -> None:
    if not TOKEN:
        print("⚠️ TELEGRAM_TOKEN no configurado; se muestra por consola.")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
        timeout=30,
    )

    if not response.ok:
        print(f"⚠️ Error enviando a Telegram: {response.status_code} {response.text[:200]}")


def limpiar_precio(texto: str):
    if not texto:
        return None

    texto = texto.replace("\xa0", " ").strip()
    coincidencias = re.findall(r"\d{1,4}(?:[.,]\d{1,2})?", texto)
    if not coincidencias:
        return None

    for bruto in coincidencias:
        valor = bruto.replace(".", "").replace(",", ".")
        try:
            precio = float(valor)
        except ValueError:
            continue
        if 10 <= precio <= 2000:
            return precio
    return None


def extraer_precios(page):
    precios = []
    vistos = set()

    for selector in SELECTORES_PRECIO:
        try:
            textos = page.locator(selector).all_text_contents()
        except Exception:
            continue
        for texto in textos[:20]:
            precio = limpiar_precio(texto)
            if precio and precio not in vistos:
                vistos.add(precio)
                precios.append(precio)
    return precios


def visitar_fuente(page, nombre: str, origen: str, destino: str, fecha: str):
    url_builder = FUENTES[nombre]
    url = url_builder(origen, destino, fecha)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        precios = extraer_precios(page)
        print(f"{nombre:<11} {origen}->{destino} {fecha}: {precios[:5]}")
        return precios
    except Exception as e:
        print(f"❌ {nombre} error {origen}-{destino} {fecha}: {e}")
        return []


def buscar_vuelos():
    resultados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=USER_AGENT,
            locale="es-ES",
            timezone_id="Europe/Madrid",
        )
        page = context.new_page()

        print(
            f"🔍 Buscando vuelos < {PRECIO_MAXIMO}€ para {DIAS_A_BUSCAR} días "
            f"con escala máxima de {MAX_ESCALA_MINUTOS} minutos"
        )
        rutas = [(o, d) for o in ISLAS for d in PENINSULA] + [(o, d) for o in PENINSULA for d in ISLAS]

        for offset in range(1, DIAS_A_BUSCAR + 1):
            fecha = (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")
            print(f"\n📅 {fecha}")
            for origen, destino in rutas:
                encontrados = []
                for fuente in FUENTES:
                    encontrados.extend(visitar_fuente(page, fuente, origen, destino, fecha))
                    time.sleep(1.2)

                for precio in sorted(set(encontrados)):
                    if precio < PRECIO_MAXIMO:
                        resultados.append(
                            {
                                "precio": precio,
                                "origen": origen,
                                "destino": destino,
                                "fecha": fecha,
                            }
                        )

        context.close()
        browser.close()

    unicos = {
        (r["precio"], r["origen"], r["destino"], r["fecha"]): r
        for r in resultados
    }
    ordenados = sorted(unicos.values(), key=lambda r: (r["precio"], r["fecha"]))
    return ordenados[:TOP_RESULTADOS]


def formatear(resultado: dict) -> str:
    fecha_txt = datetime.strptime(resultado["fecha"], "%Y-%m-%d").strftime("%d/%m/%Y")
    return (
        "✈️ VUELO BARATO DETECTADO\n\n"
        f"🛫 Origen: {CIUDADES[resultado['origen']]}\n"
        f"🛬 Destino: {CIUDADES[resultado['destino']]}\n"
        f"📅 Fecha: {fecha_txt}\n\n"
        f"💰 Precio: {resultado['precio']:.0f}€\n"
        f"⏱️ Escala máxima configurada: {MAX_ESCALA_MINUTOS} min\n\n"
        "🔗 Buscar ahora: https://www.google.com/travel/flights"
    )


def main():
    vuelos = buscar_vuelos()
    if vuelos:
        print(f"✅ Encontrados {len(vuelos)} vuelos baratos")
        for vuelo in vuelos:
            mensaje = formatear(vuelo)
            print(mensaje)
            print("-" * 60)
            enviar(mensaje)
    else:
        mensaje = (
            f"❌ No se encontraron vuelos por debajo de {PRECIO_MAXIMO}€ "
            f"en los próximos {DIAS_A_BUSCAR} días con escala máxima de {MAX_ESCALA_MINUTOS} minutos."
        )
        print(mensaje)
        enviar(mensaje)


if __name__ == "__main__":
    main()
