"""WhatsApp Cloud API: webhook signature check, payload parsing, sending messages."""

import hashlib
import hmac
import logging
from dataclasses import dataclass

import requests

log = logging.getLogger(__name__)

MAX_TEXT_LEN = 4096  # WhatsApp text message limit


@dataclass
class IncomingMessage:
    msg_id: str
    wa_id: str          # sender phone number, digits only
    name: str           # sender profile name ("" if unknown)
    type: str           # text, image, audio, location, ...
    text: str           # text body ("" for non-text messages)


def verify_signature(app_secret: str, body: bytes, header: str | None) -> bool:
    """Check Meta's X-Hub-Signature-256 header (sha256=<hmac of raw body>)."""
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def parse_messages(payload: dict) -> list[IncomingMessage]:
    """Extract customer messages from a webhook payload (status updates are ignored)."""
    out: list[IncomingMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            names = {
                c.get("wa_id"): c.get("profile", {}).get("name", "")
                for c in value.get("contacts", [])
            }
            for m in value.get("messages", []):
                mtype = m.get("type", "")
                text = ""
                if mtype == "text":
                    text = m.get("text", {}).get("body", "")
                elif mtype == "button":
                    text = m.get("button", {}).get("text", "")
                elif mtype == "interactive":
                    inter = m.get("interactive", {})
                    reply = inter.get("button_reply") or inter.get("list_reply") or {}
                    text = reply.get("title", "")
                if text:
                    mtype = "text"
                out.append(IncomingMessage(
                    msg_id=m.get("id", ""),
                    wa_id=m.get("from", ""),
                    name=names.get(m.get("from"), ""),
                    type=mtype,
                    text=text,
                ))
    return out


class WhatsAppClient:
    def __init__(self, token: str, phone_number_id: str, api_version: str = "v22.0"):
        self._url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {token}"

    def _post(self, payload: dict) -> bool:
        payload = {"messaging_product": "whatsapp", **payload}
        try:
            resp = self._session.post(self._url, json=payload, timeout=15)
        except requests.RequestException as exc:
            log.error("WhatsApp send failed: %s", exc)
            return False
        if resp.status_code >= 400:
            log.error("WhatsApp API error %s: %s", resp.status_code, resp.text[:500])
            return False
        return True

    def send_text(self, to: str, text: str) -> bool:
        ok = True
        for i in range(0, len(text), MAX_TEXT_LEN):
            ok &= self._post({
                "to": to,
                "type": "text",
                "text": {"body": text[i:i + MAX_TEXT_LEN], "preview_url": True},
            })
        return ok

    def send_location(self, to: str, latitude: float, longitude: float,
                      name: str, address: str) -> bool:
        """Location pin - opens in Google Maps on the customer's phone."""
        return self._post({
            "to": to,
            "type": "location",
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "name": name,
                "address": address,
            },
        })
