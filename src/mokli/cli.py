"""Operator commands. `mokli serve` binds to localhost unless MOKLI_HOST says otherwise."""

from __future__ import annotations

import argparse
import asyncio

import uvicorn

from mokli.config import load_settings
from mokli.gateway.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="mokli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve")
    chat = sub.add_parser("chat")
    chat.add_argument("message")
    args = parser.parse_args()
    if args.command == "serve":
        settings = load_settings()
        uvicorn.run(create_app(settings), host=settings.mokli_host, port=settings.mokli_port)
        return
    asyncio.run(_chat(args.message))


async def _chat(message: str) -> None:
    from mokli.providers.openai_runtime import run_with_snapshot_tool

    text, calls = await run_with_snapshot_tool(message, "No live snapshot in the CLI one-shot.")
    print(text)
    print(f"tool_calls={calls}")


if __name__ == "__main__":
    main()
