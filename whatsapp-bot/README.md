# WhatsApp + Claude business assistant

A WhatsApp bot you set up for a local business (restaurant, salon, clinic, garage…).
Customers message the business's WhatsApp number and Claude answers for the business, 24/7:

- **Answers questions** (hours, menu, prices, services, FAQ). It only uses the facts in `business.json`.
- **Sends the location as a map pin** that opens in Google Maps (`send_location` tool).
- **Takes orders and bookings.** It collects the details, asks the customer to confirm, saves the order and messages the owner on WhatsApp (`record_request`).
- **Hands off to a human** when a customer is unhappy or asks for a person. The bot goes quiet for that chat and forwards the customer's messages to the owner (`handoff_to_human`).
- **Replies in the customer's language** (French, Arabic, English…).

Each business you sign up gets its own deployment with its own `business.json`, its own WhatsApp number and its own database.

## How it works

```
Customer ──WhatsApp──▶ Meta Cloud API ──webhook──▶ this server ──▶ Claude
    ▲                                                 │  tools: location pin, save order, handoff
    └──────────────── reply / map pin ◀───────────────┘──▶ owner notified on WhatsApp
```

- `bot/main.py`: FastAPI app with the webhook (`GET` to verify it, `POST` to receive messages) and the admin API. It replies 200 to Meta straight away and handles each message in the background.
- `bot/agent.py`: the system prompt, the tools and the Claude tool-use loop. It also handles the owner's `#` commands.
- `bot/whatsapp.py`: signature check, payload parsing, sending text messages and location pins.
- `bot/store.py`: SQLite storage for chat history, message de-duplication, handoffs, and orders/bookings.

## Setup

1. **Claude API key**: create one at platform.claude.com.
2. **WhatsApp Cloud API**: at developers.facebook.com, create an app, add the *WhatsApp* product, and copy the **access token** (use a permanent System User token in production), the **Phone number ID** and the **App secret** (Settings → Basic).
3. **Configure**:
   ```bash
   cd whatsapp-bot
   cp .env.example .env               # fill in the values
   cp business.example.json business.json   # describe the business
   pip install -r requirements.txt
   set -a; . ./.env; set +a
   uvicorn bot.main:build_app --factory --host 0.0.0.0 --port 8000
   ```
4. **Expose it over HTTPS.** For testing, use `ngrok http 8000`. In production, use Render, Railway, Fly.io or a VPS; the `Dockerfile` is included. Put `business.json` in a volume mounted at `/data`; the database is saved there too.
5. **Register the webhook** in Meta under WhatsApp → Configuration: set the callback URL to `https://<your-host>/webhook`, set the verify token to your `WHATSAPP_VERIFY_TOKEN`, then subscribe to the **messages** field.
6. Send a message to the business number.

## For the business owner

The owner gets notifications on the WhatsApp number in `OWNER_WHATSAPP_NUMBER` and can control the bot by sending commands to the business number:

| Command | What it does |
|---|---|
| `#reply 21699999999 Your order is ready` | Sends that message to the customer from the business number |
| `#resume 21699999999` | Lets the bot answer that customer again after a handoff |
| `#handoffs` | Lists customers waiting for a human |

The admin API takes an `X-Admin-Token: $ADMIN_TOKEN` header:

- `GET /admin/requests?status=new`: orders and bookings
- `POST /admin/requests/{id}/status/{new|confirmed|done|cancelled}`
- `GET /admin/handoffs`, `POST /admin/handoffs/{number}/resume`

WhatsApp only lets a business send free-form messages within 24 hours of the other person's last message. Have the owner send any message to the business number once a day (for example `#handoffs`) so the notifications keep reaching them. Otherwise use the admin API, or add a message template.

## Claude settings and cost

- Model: `CLAUDE_MODEL` (default `claude-opus-5-5`). Effort: `CLAUDE_EFFORT` (default `low`, which is quick and enough for customer chat; raise it if the answers fall short).
- The system prompt (business info) is prompt-cached, so repeated messages are cheaper.
- **Refusal fallback is on**: if Claude's safety classifier declines a message, the API retries it on a fallback model (`fallbacks: "default"`). If that also declines, the bot hands the chat to the owner.
- The last 20 messages per customer are sent as history.

Before you set your prices, measure what one conversation actually costs you on your API usage page. Then charge a monthly fee that covers it with a good margin.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The tests use a fake Claude client and a fake WhatsApp client, so they make no network calls and cost nothing.

## Rules to respect

- Only reply to people who message the business first. Don't use the bot for cold bulk messaging, or Meta will ban the number.
- Tell customers they are talking to an automated assistant (put it in the business's profile or greeting).
- The business is responsible for the information in `business.json`. Keep prices and hours up to date.
