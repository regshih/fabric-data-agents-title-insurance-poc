from __future__ import annotations

import asyncio
import os
import time
from functools import lru_cache

import httpx2
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
MAX_QUESTION_LENGTH = 500
_HTTP_CLIENT = httpx2.AsyncClient(timeout=110.0)


def validate_question(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("question must be a string")
    question = " ".join(value.split())
    if not question:
        raise ValueError("question is required")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(f"question must be {MAX_QUESTION_LENGTH} characters or fewer")
    return question


def resolve_agent_id(agent: object) -> tuple[str, str]:
    key = str(agent or "direct").strip().lower()
    mapping = {
        "ontology": os.environ["FABRIC_ONTOLOGY_AGENT_ID"],
        "direct": os.environ["FABRIC_DIRECT_AGENT_ID"],
        "semantic": os.environ["FABRIC_SEMANTIC_AGENT_ID"],
        "hybrid": os.environ["FABRIC_HYBRID_AGENT_ID"],
    }
    if key not in mapping:
        raise ValueError("agent must be 'direct', 'ontology', 'semantic', or 'hybrid'")
    return key, mapping[key]


@lru_cache(maxsize=1)
def _fabric_credential() -> ClientSecretCredential:
    direct_secret = os.getenv("FABRIC_CLIENT_SECRET")
    if direct_secret:
        secret = direct_secret
    else:
        vault_url = os.environ["KEY_VAULT_URL"]
        managed_identity_client_id = os.getenv("MANAGED_IDENTITY_CLIENT_ID")
        identity = DefaultAzureCredential(managed_identity_client_id=managed_identity_client_id)
        secret = SecretClient(vault_url=vault_url, credential=identity).get_secret(
            os.getenv("FABRIC_CLIENT_SECRET_NAME", "fabric-client-secret")
        ).value
    if not secret:
        raise RuntimeError("Fabric application credential is unavailable")
    return ClientSecretCredential(
        tenant_id=os.environ["FABRIC_TENANT_ID"],
        client_id=os.environ["FABRIC_CLIENT_ID"],
        client_secret=secret,
    )


async def ask_data_agent(question: str, agent: object = "direct") -> dict[str, object]:
    safe_question = validate_question(question)
    agent_name, agent_id = resolve_agent_id(agent)
    workspace_id = os.environ["FABRIC_WORKSPACE_ID"]
    endpoint = (
        f"https://api.fabric.microsoft.com/v1/mcp/workspaces/{workspace_id}"
        f"/dataagents/{agent_id}/agent"
    )
    credential = _fabric_credential()
    access_token = await asyncio.to_thread(credential.get_token, FABRIC_SCOPE)
    started = time.perf_counter()

    _HTTP_CLIENT.headers["Authorization"] = f"Bearer {access_token.token}"
    async with (
        streamable_http_client(endpoint, http_client=_HTTP_CLIENT) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        tools = (await session.list_tools()).tools
        if not tools:
            raise RuntimeError("The published Data Agent exposed no MCP tool")
        tool = tools[0]
        question_argument = next(iter(tool.input_schema["properties"]))
        result = await session.call_tool(tool.name, {question_argument: safe_question})
        answer = "\n".join(getattr(block, "text", str(block)) for block in result.content)
        if getattr(result, "is_error", False):
            raise RuntimeError(answer or "The Data Agent returned an error")

    return {
        "agent": agent_name,
        "answer": answer,
        "elapsedSeconds": round(time.perf_counter() - started, 3),
        "syntheticData": True,
    }
