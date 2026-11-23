"""One-way bridge: spaz.radio chat -> a tunaFluxer text channel.

spaz.radio's chat is MQTT over WebSocket (wss://radio.spaz.org:1885/mqtt),
topic "spazradio", payload {"user": "...", "message": "..."}.
This script only subscribes. It never publishes, so it posts nothing to
spaz.radio and does not show up in its online list.
Each message is sent to a Fluxer webhook with the spaz username shown.
"""
import json
import os
import ssl
import time
import random

import paho.mqtt.client as mqtt
import requests

WEBHOOK_URL = os.environ["FLUXER_WEBHOOK_URL"]          # .../webhooks/{id}/{token}
SPAZ_HOST = os.environ.get("SPAZ_HOST", "radio.spaz.org")
SPAZ_PORT = int(os.environ.get("SPAZ_PORT", "1885"))
SPAZ_PATH = os.environ.get("SPAZ_PATH", "/mqtt")
SPAZ_TOPIC = os.environ.get("SPAZ_TOPIC", "spazradio")
NAME_SUFFIX = os.environ.get("NAME_SUFFIX", " (spaz)")
TLS_INSECURE = os.environ.get("SPAZ_TLS_INSECURE", "0") == "1"

ZWSP = "​"
session = requests.Session()


def clean(text: str) -> str:
    # Stop "@everyone", "@here" and other mentions from pinging anyone.
    return text.replace("@", "@" + ZWSP)[:2000]


def post(user: str, message: str) -> None:
    body = {
        "content": clean(message),
        "username": (clean(user)[:80 - len(NAME_SUFFIX)] + NAME_SUFFIX) or "spaz",
    }
    for attempt in range(5):
        try:
            r = session.post(WEBHOOK_URL, json=body, timeout=15)
        except requests.RequestException as e:
            print(f"webhook error: {e}", flush=True)
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", "2"))
            time.sleep(min(wait, 30))
            continue
        if r.status_code >= 400:
            print(f"webhook {r.status_code}: {r.text[:200]}", flush=True)
        return


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"connected to spaz.radio: {reason_code}", flush=True)
    client.subscribe(SPAZ_TOPIC, qos=1)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8", "replace"))
        user, message = str(data["user"]).strip(), str(data["message"]).strip()
    except (ValueError, KeyError, TypeError):
        return
    if user and message:
        post(user, message)


def main():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"tunafluxer-bridge-{random.randint(1, 999999)}",
        transport="websockets",
        clean_session=True,
    )
    client.ws_set_options(path=SPAZ_PATH)
    if TLS_INSECURE:
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
    else:
        client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=2, max_delay=120)
    client.connect(SPAZ_HOST, SPAZ_PORT, keepalive=60)
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
