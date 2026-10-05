import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup

URL = "https://henaresaldia.com/eventos/mes/"
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DATA_FILE = "eventos.json"


def obtener_eventos():
    respuesta = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    respuesta.raise_for_status()

    soup = BeautifulSoup(respuesta.text, "html.parser")

    eventos = []

    # Los eventos de la agenda aparecen como enlaces dentro del calendario.
    for enlace in soup.find_all("a", href=True):
        texto = enlace.get_text(" ", strip=True)
        href = enlace["href"]

        if not texto:
            continue

        # Filtramos enlaces que parecen corresponder a eventos.
        if "/evento/" in href or "/eventos/" in href:
            eventos.append({
                "titulo": texto,
                "url": href
            })

    # Eliminar duplicados
    unicos = {}
    for evento in eventos:
        clave = evento["url"]
        unicos[clave] = evento

    return list(unicos.values())


def identificador(evento):
    contenido = evento["titulo"] + evento["url"]
    return hashlib.sha256(contenido.encode()).hexdigest()


def cargar_eventos():
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_eventos(eventos):
    with open(DATA_FILE, "w", encoding="utf-8") as archivo:
        json.dump(eventos, archivo, ensure_ascii=False, indent=2)


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    respuesta = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": mensaje,
            "disable_web_page_preview": False
        },
        timeout=30
    )

    respuesta.raise_for_status()


def main():
    eventos = obtener_eventos()

    anteriores = cargar_eventos()
    anteriores_ids = {
        identificador(evento)
        for evento in anteriores
    }

    nuevos = [
        evento
        for evento in eventos
        if identificador(evento) not in anteriores_ids
    ]

    # Guardamos el estado actual.
    guardar_eventos(eventos)

    # Primera ejecución: no queremos recibir 40 avisos de golpe.
    if not anteriores:
        print(f"Primera ejecución. Guardados {len(eventos)} eventos.")
        return

    if not nuevos:
        print("No hay eventos nuevos.")
        return

    mensaje = "🔔 Novedades en la agenda de Henares al Día\n\n"

    for evento in nuevos[:20]:
        mensaje += f"🆕 {evento['titulo']}\n{evento['url']}\n\n"

    if len(nuevos) > 20:
        mensaje += f"... y {len(nuevos) - 20} eventos más."

    enviar_telegram(mensaje)

    print(f"Enviados {len(nuevos)} eventos nuevos.")


if __name__ == "__main__":
    main()
