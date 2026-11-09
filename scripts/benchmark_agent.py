from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import statistics
import time
import traceback
from pathlib import Path

import httpx2
import yaml
from azure.identity import AzureCliCredential
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from title_iq.fabric_api import read_state

REPORT_PREFIXES = {
    "direct": "direct-agent",
    "ontology": "ontology-agent",
    "semantic": "semantic-agent",
    "hybrid": "hybrid-agent",
}


def summarize_rows(rows: list[dict], agent: str, connection_mode: str, report_prefix: str) -> dict:
    if not rows:
        raise ValueError("Cannot summarize an empty response file")
    all_times = [float(row["total_seconds"]) for row in rows]
    successful_times = [float(row["total_seconds"]) for row in rows if str(row["success"]).lower() == "true"]

    def latency(times: list[float]) -> dict:
        if not times:
            return {key: None for key in ("mean", "p50", "p90", "p95", "minimum", "maximum")}
        ordered = sorted(times)
        return {
            "mean": statistics.mean(times),
            "p50": statistics.median(times),
            "p90": ordered[int(.9 * (len(times) - 1))],
            "p95": ordered[int(.95 * (len(times) - 1))],
            "minimum": min(times),
            "maximum": max(times),
        }

    summary = {
        "count": len(rows),
        "successful_count": len(successful_times),
        "failed_count": len(rows) - len(successful_times),
        "success_rate": len(successful_times) / len(rows),
        **latency(successful_times),
        "all_call_latency": latency(all_times),
        "failed_call_seconds": [float(row["total_seconds"]) for row in rows if str(row["success"]).lower() != "true"],
        "agent": agent,
        "connection_mode": connection_mode,
        "report_prefix": report_prefix,
    }
    return summary


async def ask_session(session: ClientSession, question: str) -> tuple[bool, str, float, str]:
    started = time.perf_counter()
    try:
        tools = (await session.list_tools()).tools
        tool = tools[0]
        schema = tool.input_schema
        question_arg = next(iter(schema["properties"]))
        result = await session.call_tool(tool.name, {question_arg: question})
        answer = "\n".join(getattr(block, "text", str(block)) for block in result.content)
        is_error = getattr(result, "is_error", None)
        if is_error is None:
            is_error = getattr(result, "isError", False)
        return not is_error, answer, time.perf_counter() - started, tool.name
    except Exception as exc:  # noqa: BLE001 - benchmark records failures rather than hiding them
        return False, "".join(traceback.format_exception(exc)), time.perf_counter() - started, ""


async def ask(endpoint: str, token: str, question: str) -> tuple[bool, str, float, str]:
    started = time.perf_counter()
    try:
        async with (
            httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=240.0) as http_client,
            streamable_http_client(endpoint, http_client=http_client) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            success, answer, _, tool = await ask_session(session, question)
            return success, answer, time.perf_counter() - started, tool
    except Exception as exc:  # noqa: BLE001 - benchmark records failures rather than hiding them
        return False, "".join(traceback.format_exception(exc)), time.perf_counter() - started, ""


async def run(args: argparse.Namespace) -> None:
    state = read_state()
    agent_config = {
        "direct": ("direct_data_agent_id", "direct_agent_published", "direct-agent", "standard"),
        "ontology": ("data_agent_id", "agent_published", "ontology-agent", "standard"),
        "semantic": (
            "semantic_data_agent_id",
            "semantic_agent_published",
            "semantic-agent",
            state.get("semantic_agent_runtime", "standard"),
        ),
        "hybrid": (
            "hybrid_data_agent_id",
            "hybrid_agent_published",
            "hybrid-agent",
            state.get("hybrid_agent_runtime", "standard"),
        ),
    }
    id_key, published_key, report_prefix, agent_runtime = agent_config[args.agent]
    agent_id = state.get(id_key)
    published = state.get(published_key)
    if not agent_id or not published:
        raise RuntimeError(f"publish the {args.agent} data agent before benchmarking")
    endpoint = f"https://api.fabric.microsoft.com/v1/mcp/workspaces/{state['workspace_id']}/dataagents/{agent_id}/agent"
    token = AzureCliCredential().get_token("https://api.fabric.microsoft.com/.default").token
    questions = yaml.safe_load(Path(args.questions_file).read_text(encoding="utf-8"))["questions"]
    if args.question_ids:
        selected_ids = {value.strip() for value in args.question_ids.split(",") if value.strip()}
        questions = [question for question in questions if question["id"] in selected_ids]
        missing_ids = selected_ids - {question["id"] for question in questions}
        if missing_ids:
            raise ValueError(f"Unknown question IDs: {', '.join(sorted(missing_ids))}")
    if args.limit:
        questions = questions[: args.limit]
    report_prefix = f"{report_prefix}-{args.report_tag}" if args.report_tag else report_prefix
    Path("reports").mkdir(exist_ok=True)
    responses_path = Path(f"reports/{report_prefix}-responses.csv")
    rows = []
    if args.resume and responses_path.exists():
        with responses_path.open(newline="", encoding="utf-8") as handle:  # noqa: ASYNC230 - one-time checkpoint load
            rows = list(csv.DictReader(handle))
        expected_keys = {(repetition, question["id"]) for repetition in range(1, args.repetitions + 1) for question in questions}
        existing_keys = {(int(row["repetition"]), row["question_id"]) for row in rows}
        if len(existing_keys) != len(rows) or not existing_keys.issubset(expected_keys):
            raise ValueError("Existing response file has duplicate or unexpected questions; choose a new report tag")
        if any(
            row["mode"] != args.mode
            or row["connection_mode"] != args.connection_mode
            or row["capacity_sku"] != str(state.get("capacity_sku"))
            or row["agent_runtime"] != agent_runtime
            for row in rows
        ):
            raise ValueError("Existing response file has a different benchmark configuration")

    def save_rows() -> None:
        if not rows:
            return
        temporary_path = responses_path.with_suffix(".csv.tmp")
        with temporary_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(responses_path)

    if args.mode == "warm":
        await ask(endpoint, token, questions[0]["question"])
    async def record_questions(session: ClientSession | None = None) -> None:
        for repetition in range(args.repetitions):
            for q in questions:
                if any(int(row["repetition"]) == repetition + 1 and row["question_id"] == q["id"] for row in rows):
                    continue
                if session:
                    success, answer, seconds, tool = await ask_session(session, q["question"])
                else:
                    success, answer, seconds, tool = await ask(endpoint, token, q["question"])
                criteria = q["criteria"]
                accuracy = sum(str(c).lower() in answer.lower() for c in criteria) / len(criteria)
                rows.append({
                    "question_id": q["id"], "question_class": q["class"], "mode": args.mode,
                    "connection_mode": args.connection_mode, "repetition": repetition + 1,
                    "success": success, "criteria_recall": accuracy, "total_seconds": round(seconds, 3),
                    "tool": tool, "capacity_sku": state.get("capacity_sku"), "agent_runtime": agent_runtime,
                    "answer": answer.replace("\n", " ")[:10000],
                })
                if args.checkpoint or args.resume:
                    save_rows()
                print(f"{args.agent} {q['id']} {len(rows)}/{args.repetitions * len(questions)} {seconds:.2f}s", flush=True)

    if args.connection_mode == "persistent":
        async with (
            httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=240.0) as http_client,
            streamable_http_client(endpoint, http_client=http_client) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            await record_questions(session)
    else:
        await record_questions()
    save_rows()
    summary = summarize_rows(rows, args.agent, args.connection_mode, report_prefix)
    Path(f"reports/{report_prefix}-benchmark-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=["direct", "ontology", "semantic", "hybrid"], default="ontology")
    parser.add_argument("--mode", choices=["cold", "warm"], default="warm")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="Run only the first N questions; zero runs all")
    parser.add_argument("--connection-mode", choices=["fresh", "persistent"], default="fresh")
    parser.add_argument("--report-tag", default="", help="Append a label to report file names")
    parser.add_argument("--checkpoint", action="store_true", help="Save responses after every question")
    parser.add_argument("--resume", action="store_true", help="Resume a checkpointed response file")
    parser.add_argument("--summary-only", action="store_true", help="Recalculate summary from an existing response file")
    parser.add_argument("--question-ids", default="", help="Comma-separated benchmark question IDs")
    parser.add_argument("--questions-file", default="benchmark/questions.yaml", help="YAML question suite")
    args = parser.parse_args()
    if args.summary_only:
        report_prefix = f"{REPORT_PREFIXES[args.agent]}-{args.report_tag}" if args.report_tag else REPORT_PREFIXES[args.agent]
        response_path = Path(f"reports/{report_prefix}-responses.csv")
        with response_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        summary = summarize_rows(rows, args.agent, args.connection_mode, report_prefix)
        Path(f"reports/{report_prefix}-benchmark-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
    else:
        asyncio.run(run(args))


if __name__ == "__main__":
    main()
