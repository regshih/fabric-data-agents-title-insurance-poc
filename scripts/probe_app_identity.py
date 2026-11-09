from __future__ import annotations

import argparse
import asyncio
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src" / "agent-demo"))

from fabric_agent_client import ask_data_agent


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", default="direct,ontology,semantic,hybrid")
    agents = tuple(value.strip() for value in parser.parse_args().agents.split(",") if value.strip())
    question = "How many open High or Critical title orders are there?"
    for agent in agents:
        try:
            result = await ask_data_agent(question, agent)
            print(
                json.dumps(
                    {
                        "agent": agent,
                        "success": True,
                        "seconds": result["elapsedSeconds"],
                        "answer": str(result["answer"])[:300],
                    }
                ),
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001 - probe must record each access result
            details = "".join(traceback.format_exception(exc))
            print(json.dumps({"agent": agent, "success": False, "error": details[-3000:]}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
