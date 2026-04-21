# Bot Vuelos PRO

Bot en Python para buscar vuelos baratos entre Canarias y Península usando Playwright y enviar avisos a Telegram.

## Incluye

- `main.py`: script principal ya corregido
- `requirements.txt`: dependencias
- `.github/workflows/vuelos.yml`: automatización diaria con GitHub Actions

## Rutas configuradas

- Islas: Fuerteventura (`fue`), Lanzarote (`ace`)
- Península: Bilbao (`bio`), Vitoria (`vit`), San Sebastián (`eas`), Asturias (`ovd`)

## Secrets necesarios en GitHub

- `TELEGRAM_TOKEN`: token de tu bot
- `TELEGRAM_CHAT_ID`: canal o chat destino, por ejemplo `@tu_canal`

## Opciones configurables

Puedes cambiar por variables de entorno:

- `PRECIO_MAXIMO` (por defecto `95`)
- `DIAS_A_BUSCAR` (por defecto `35`)
- `TOP_RESULTADOS` (por defecto `5`)

## Despliegue

1. Sube el contenido a un repositorio.
2. Añade los secrets en GitHub.
3. Activa GitHub Actions.
4. Lanza `workflow_dispatch` para probar.

## Nota importante

Los comparadores de vuelos cambian selectores y pueden aplicar bloqueos anti-bot. El código está dejado bastante más robusto que el adjunto original, pero puede requerir retoques futuros en los selectores si alguna web cambia.
