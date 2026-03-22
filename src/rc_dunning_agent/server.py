import os

from fastapi import FastAPI, Header, HTTPException, Request

from rc_dunning_agent.engine import DunningEngine
from rc_dunning_agent.store import DunningStore
from rc_dunning_agent.webhook import RCWebhookHandler

app = FastAPI(title="RC Dunning Agent")

_db_path = os.environ.get("DUNNING_DB_PATH", "./dunning.db")
_auth_key = os.environ.get("RC_WEBHOOK_SECRET", "")

_store = DunningStore(_db_path)
_engine = DunningEngine(_store)
_handler = RCWebhookHandler(_engine, auth_key=_auth_key or None)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook/revenuecat")
async def webhook_revenuecat(
    request: Request,
    rc_webhook_secret: str | None = Header(None, alias="RC-Webhook-Secret"),
):
    payload = await request.json()
    try:
        result = _handler.handle(payload, auth_header=rc_webhook_secret)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return result
