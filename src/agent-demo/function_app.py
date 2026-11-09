from __future__ import annotations

import json
import logging
from pathlib import Path

import azure.functions as func
from fabric_agent_client import ask_data_agent

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
INDEX_HTML = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
LOGGER = logging.getLogger(__name__)


@app.route(route="", methods=["GET"])
def index(req: func.HttpRequest) -> func.HttpResponse:
    del req
    return func.HttpResponse(INDEX_HTML, mimetype="text/html", headers={"Cache-Control": "no-store"})


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    del req
    return func.HttpResponse(
        json.dumps({"status": "ok", "service": "fabric-title-iq-agent-demo"}),
        mimetype="application/json",
    )


@app.route(route="ask", methods=["POST"])
async def ask(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        if not isinstance(body, dict):
            raise TypeError("request body must be a JSON object")
        result = await ask_data_agent(body.get("question"), body.get("agent"))
        return func.HttpResponse(json.dumps(result), mimetype="application/json")
    except (TypeError, ValueError) as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=400,
            mimetype="application/json",
        )
    except Exception:
        LOGGER.exception("Data Agent request failed; prompt and answer bodies are intentionally not logged")
        return func.HttpResponse(
            json.dumps({"error": "The Data Agent request failed. Retry or contact the POC owner."}),
            status_code=502,
            mimetype="application/json",
        )
