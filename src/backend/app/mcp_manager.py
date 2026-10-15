from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.agent import ToolSpec


@dataclass(frozen=True)
class ServerConfig:
    name: str
    command: str
    args: list[str]


class MCPManager:
    """Startet MCP-Server per Config (ADR-002) und hält die stdio-Sessions offen."""

    def __init__(self, server_configs: list[ServerConfig]) -> None:
        self._configs = server_configs
        self._sessions: dict[str, ClientSession] = {}
        self._stop = anyio.Event()
        self._tg: Any = anyio.create_task_group()

    async def start(self) -> None:
        self._stop = anyio.Event()
        self._tg = anyio.create_task_group()
        await self._tg.__aenter__()
        for config in self._configs:
            self._tg.start_soon(self._open_session, config)
        for config in self._configs:
            with anyio.fail_after(20):
                while config.name not in self._sessions:
                    await anyio.sleep(0.05)

    async def stop(self) -> None:
        self._stop.set()
        await self._tg.__aexit__(None, None, None)

    async def list_tool_specs(self) -> list[ToolSpec]:
        specs: list[ToolSpec] = []
        for name, session in self._sessions.items():
            listing = await session.list_tools()
            for tool in listing.tools:
                specs.append(
                    ToolSpec(
                        name=f"{name}_{tool.name}",
                        description=tool.description or tool.name,
                        parameters=_tool_schema(tool),
                        handler=self._make_handler(name, tool.name),
                    )
                )
        return specs

    def connected_names(self) -> list[str]:
        return sorted(self._sessions)

    def _make_handler(self, server_name: str, tool_name: str):
        async def handler(arguments: dict[str, Any]) -> Any:
            session = self._sessions[server_name]
            result = await session.call_tool(tool_name, arguments or {})
            return {
                "content": [
                    {"type": block.type, "text": getattr(block, "text", None)}
                    for block in result.content
                    if block.type == "text"
                ],
                "is_error": getattr(result, "isError", False),
            }

        return handler

    async def _open_session(self, config: ServerConfig) -> None:
        import os

        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env={**os.environ},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._sessions[config.name] = session
                await self._stop.wait()
                self._sessions.pop(config.name, None)


def _tool_schema(tool: Any) -> dict[str, Any]:
    return getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None) or {
        "type": "object",
        "properties": {},
    }


def load_server_configs(path: str | Path, python: str | None = None) -> list[ServerConfig]:
    python = python or sys.executable
    path = Path(path)
    entries = json.loads(path.read_text())
    return [
        ServerConfig(
            name=entry["name"],
            command=python,
            args=[str((path.parent / entry["script"]).resolve())],
        )
        for entry in entries
    ]
