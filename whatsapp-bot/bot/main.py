"""FastAPI app: WhatsApp webhook + small admin API.

Run:  uvicorn bot.main:build_app --factory --host 0.0.0.0 --port 8000
"""

import json
import logging

import anthropic
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from .agent import Bot
from .config import Settings
from .store import Store
from .whatsapp import WhatsAppClient, parse_messages, verify_signature

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings, bot: Bot | None = None, store: Store | None = None) -> FastAPI:
    store = store or Store(settings.db_path)
    bot = bot or Bot(
        client=anthropic.Anthropic(),
        whatsapp=WhatsAppClient(settings.whatsapp_token, settings.phone_number_id,
                                settings.graph_api_version),
        store=store,
        business=settings.business,
        model=settings.claude_model,
        effort=settings.claude_effort,
        owner_number=settings.owner_number,
        history_messages=settings.history_messages,
    )
    app = FastAPI(title="WhatsApp Claude bot")

    def require_admin(token: str | None) -> None:
        if not settings.admin_token or token != settings.admin_token:
            raise HTTPException(status_code=401, detail="bad admin token")

    @app.get("/health")
    def health() -> dict:
        return {"ok": True}

    @app.get("/webhook")
    def verify(request: Request) -> PlainTextResponse:
        """Meta calls this once when you register the webhook URL."""
        q = request.query_params
        if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == settings.verify_token:
            return PlainTextResponse(q.get("hub.challenge", ""))
        raise HTTPException(status_code=403, detail="verification failed")

    @app.post("/webhook")
    async def webhook(request: Request, background: BackgroundTasks,
                      x_hub_signature_256: str | None = Header(default=None)) -> dict:
        body = await request.body()
        if not verify_signature(settings.app_secret, body, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="bad signature")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="invalid json")
        # Answer Meta right away; Claude runs in the background (Meta retries slow webhooks).
        for msg in parse_messages(payload):
            if msg.msg_id and store.mark_processed(msg.msg_id):
                background.add_task(bot.handle, msg)
        return {"ok": True}

    # ---- admin API (header: X-Admin-Token) ----
    @app.get("/admin/requests")
    def list_requests(status: str | None = None,
                      x_admin_token: str | None = Header(default=None)) -> list[dict]:
        require_admin(x_admin_token)
        return store.list_requests(status)

    @app.post("/admin/requests/{request_id}/status/{status}")
    def update_request(request_id: int, status: str,
                       x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        if status not in {"new", "confirmed", "done", "cancelled"}:
            raise HTTPException(status_code=400, detail="unknown status")
        if not store.set_request_status(request_id, status):
            raise HTTPException(status_code=404, detail="not found")
        return {"ok": True}

    @app.get("/admin/handoffs")
    def handoffs(x_admin_token: str | None = Header(default=None)) -> list[dict]:
        require_admin(x_admin_token)
        return store.list_handoffs()

    @app.post("/admin/handoffs/{wa_id}/resume")
    def resume(wa_id: str, x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"resumed": store.clear_handoff(wa_id)}

    return app


def build_app() -> FastAPI:
    """Entry point for uvicorn: reads settings from the environment."""
    return create_app(Settings.from_env())
