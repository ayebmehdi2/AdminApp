import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from bot.agent import Bot, FALLBACK_TEXT
from bot.config import Settings
from bot.main import create_app
from bot.store import Store
from bot.whatsapp import IncomingMessage, parse_messages, verify_signature

BUSINESS = json.load(open("business.example.json", encoding="utf-8"))
OWNER = "21600000000"
CUSTOMER = "21699999999"


# ---------------------------------------------------------------- fakes
class Block(SimpleNamespace):
    def model_dump(self, **_):
        return {k: v for k, v in vars(self).items()}


def text(t):
    return Block(type="text", text=t)


def tool(name, args, id_="tu_1"):
    return Block(type="tool_use", id=id_, name=name, input=args)


class FakeClaude:
    """Returns scripted responses and records each request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(json.loads(json.dumps(kwargs["messages"], default=vars)))
        self.last_kwargs = kwargs
        content, stop = self.responses.pop(0)
        return SimpleNamespace(content=content, stop_reason=stop)


class FakeWhatsApp:
    def __init__(self):
        self.sent = []

    def send_text(self, to, body):
        self.sent.append(("text", to, body))
        return True

    def send_location(self, to, lat, lng, name, address):
        self.sent.append(("location", to, lat, lng))
        return True


def make_bot(*responses):
    store = Store(":memory:")
    wa = FakeWhatsApp()
    claude = FakeClaude(*responses)
    bot = Bot(client=claude, whatsapp=wa, store=store, business=BUSINESS,
              model="claude-opus-5-5", owner_number=OWNER)
    return bot, claude, wa, store


def incoming(body, wa_id=CUSTOMER, mtype="text", msg_id="m1"):
    return IncomingMessage(msg_id=msg_id, wa_id=wa_id, name="Sami", type=mtype, text=body)


# ---------------------------------------------------------------- bot logic
def test_simple_reply_and_history():
    bot, claude, wa, store = make_bot(([text("We open at 11:00.")], "end_turn"),
                                      ([text("Yes, takeaway too.")], "end_turn"))
    bot.handle(incoming("When do you open?"))
    bot.handle(incoming("Takeaway?", msg_id="m2"))

    assert wa.sent == [("text", CUSTOMER, "We open at 11:00."),
                       ("text", CUSTOMER, "Yes, takeaway too.")]
    # second request carries the first exchange as history
    assert [m["role"] for m in claude.calls[1]] == ["user", "assistant", "user"]
    assert claude.last_kwargs["fallbacks"] == "default"
    assert claude.last_kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_send_location_tool():
    bot, claude, wa, _ = make_bot(([tool("send_location", {})], "tool_use"),
                                  ([text("Here we are!")], "end_turn"))
    bot.handle(incoming("Where are you?"))

    assert wa.sent[0] == ("location", CUSTOMER, BUSINESS["latitude"], BUSINESS["longitude"])
    assert wa.sent[1] == ("text", CUSTOMER, "Here we are!")
    tool_result = claude.calls[1][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["tool_use_id"] == "tu_1"


def test_record_request_saves_and_notifies_owner():
    args = {"kind": "order", "customer_name": "Sami", "details": "2 Classic Burger, takeaway",
            "requested_time": "20:30"}
    bot, _, wa, store = make_bot(([tool("record_request", args)], "tool_use"),
                                 ([text("Thanks! The team will confirm.")], "end_turn"))
    bot.handle(incoming("Yes confirm"))

    [req] = store.list_requests()
    assert req["details"] == "2 Classic Burger, takeaway" and req["wa_id"] == CUSTOMER
    owner_msgs = [s for s in wa.sent if s[1] == OWNER]
    assert "New order #1" in owner_msgs[0][2]


def test_handoff_stops_bot_until_resumed():
    bot, claude, wa, store = make_bot(
        ([tool("handoff_to_human", {"reason": "complaint"})], "tool_use"),
        ([text("Someone will reply soon.")], "end_turn"),
        ([text("Back again!")], "end_turn"),
    )
    bot.handle(incoming("I want a refund"))
    assert store.is_handed_off(CUSTOMER)

    bot.handle(incoming("hello??", msg_id="m2"))
    assert len(claude.calls) == 2  # bot did not call Claude
    assert wa.sent[-1][1] == OWNER and "hello??" in wa.sent[-1][2]

    bot.handle(incoming(f"#resume {CUSTOMER}", wa_id=OWNER, msg_id="m3"))
    assert not store.is_handed_off(CUSTOMER)
    bot.handle(incoming("still there?", msg_id="m4"))
    assert wa.sent[-1] == ("text", CUSTOMER, "Back again!")
    # message received during the handoff is merged into one user turn
    assert [m["role"] for m in claude.calls[-1]][-1] == "user"


def test_owner_reply_command():
    bot, _, wa, store = make_bot()
    bot.handle(incoming(f"#reply +{CUSTOMER} Your order is ready", wa_id=OWNER))
    assert ("text", CUSTOMER, "Your order is ready") in wa.sent


def test_refusal_hands_off():
    bot, _, wa, store = make_bot(([], "refusal"))
    bot.handle(incoming("something odd"))
    assert ("text", CUSTOMER, FALLBACK_TEXT["refusal"]) in wa.sent
    assert store.is_handed_off(CUSTOMER)


def test_non_text_message():
    bot, claude, wa, _ = make_bot()
    bot.handle(incoming("", mtype="image"))
    assert wa.sent == [("text", CUSTOMER, FALLBACK_TEXT["unsupported"])]
    assert claude.calls == []


# ---------------------------------------------------------------- webhook
SECRET = "app-secret"


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def payload(msg_id="wamid.1", body="hi"):
    return {"entry": [{"changes": [{"value": {
        "contacts": [{"wa_id": CUSTOMER, "profile": {"name": "Sami"}}],
        "messages": [{"id": msg_id, "from": CUSTOMER, "type": "text", "text": {"body": body}}],
    }}]}]}


@pytest.fixture
def api():
    settings = Settings(whatsapp_token="t", phone_number_id="p", verify_token="vt",
                        app_secret=SECRET, admin_token="adm", business=BUSINESS)
    bot, claude, wa, store = make_bot(([text("Hello!")], "end_turn"))
    return TestClient(create_app(settings, bot=bot, store=store)), wa, store


def test_webhook_verification(api):
    client, _, _ = api
    ok = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "vt",
                                        "hub.challenge": "42"})
    assert ok.status_code == 200 and ok.text == "42"
    bad = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "x",
                                         "hub.challenge": "42"})
    assert bad.status_code == 403


def test_webhook_rejects_bad_signature(api):
    client, wa, _ = api
    body = json.dumps(payload()).encode()
    r = client.post("/webhook", content=body, headers={"X-Hub-Signature-256": "sha256=bad"})
    assert r.status_code == 401 and wa.sent == []


def test_webhook_processes_once(api):
    client, wa, _ = api
    body = json.dumps(payload()).encode()
    for _ in range(2):  # Meta retry with the same message id
        r = client.post("/webhook", content=body, headers={"X-Hub-Signature-256": sign(body)})
        assert r.status_code == 200
    assert wa.sent == [("text", CUSTOMER, "Hello!")]


def test_admin_requires_token(api):
    client, _, _ = api
    assert client.get("/admin/requests").status_code == 401
    assert client.get("/admin/requests", headers={"X-Admin-Token": "adm"}).json() == []


def test_parse_and_signature_helpers():
    [m] = parse_messages(payload(body="yo"))
    assert (m.wa_id, m.name, m.text, m.type) == (CUSTOMER, "Sami", "yo", "text")
    assert parse_messages({"entry": [{"changes": [{"value": {"statuses": [{}]}}]}]}) == []
    assert not verify_signature(SECRET, b"x", None)
