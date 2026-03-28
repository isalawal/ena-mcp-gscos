# server.py
# ENA MCP Server — exposes ENA Portal API endpoints as MCP tools
# that any AI agent (Claude, GPT, etc.) can call directly.
#
# The server prevents AI hallucination by forcing the agent to fetch
# real verified data from ENA before responding to a query.
#
# Part of GSoC 2026 application — EMBL-EBI
# GitHub: https://github.com/isalawal/ena-mcp-gscos

import requests
import json
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Base URL for all ENA Portal API calls
BASE_URL = "https://www.ebi.ac.uk/ena/portal/api"

# Initialise the MCP server with a name
# This name identifies the server to any AI agent that connects
app = Server("ena-mcp-server")


@app.list_tools()
async def list_tools():
    """
    Tell the AI agent what tools are available on this server.
    Each tool has a name, description, and input schema.
    The AI reads these to know what it can ask the server to do.
    """
    return [
        Tool(
            name="search_ena",
            description=(
                "Search the European Nucleotide Archive for genomic records. "
                "Use this to find samples, studies, or sequencing runs matching a query. "
                "Returns structured records with accession numbers and metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "ENA query string. Examples: "
                            "tax_eq(9606) for human, "
                            "tax_eq(10090) for mouse, "
                            "instrument_platform=ILLUMINA for Illumina runs"
                        )
                    },
                    "result_type": {
                        "type": "string",
                        "description": "Data type to search: sample, read_run, or study",
                        "default": "sample"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (default 5, max 100)",
                        "default": 5
                    }
                },
                "required": ["query"]  # query is the only required field
            }
        ),

        Tool(
            name="count_ena",
            description=(
                "Count how many records in ENA match a query. "
                "Use this before searching to understand the scale of results "
                "and avoid fetching unexpectedly large datasets."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "ENA query string e.g. tax_eq(9606) for human"
                    },
                    "result_type": {
                        "type": "string",
                        "description": "Data type: sample, read_run, or study",
                        "default": "read_run"
                    }
                },
                "required": ["query"]
            }
        ),

        Tool(
            name="get_searchable_fields",
            description=(
                "Get all fields that can be searched for a given ENA result type. "
                "Use this to discover what filters are available before constructing a query."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "result_type": {
                        "type": "string",
                        "description": "Data type: sample, read_run, or study",
                        "default": "sample"
                    }
                },
                "required": []  # no required fields - result_type has a default
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """
    Handle all tool calls from the AI agent.

    The AI sends a tool name + arguments.
    We call the real ENA API and return the result.
    This is the core function that prevents hallucination —
    the AI cannot invent data because it must fetch it here.
    """

    # ── TOOL 1: search_ena ──────────────────────────────────────
    if name == "search_ena":

        # Extract arguments — use defaults if not provided
        query = arguments["query"]
        result_type = arguments.get("result_type", "sample")
        limit = arguments.get("limit", 5)

        # Call the real ENA search endpoint
        response = requests.get(
            f"{BASE_URL}/search",
            params={
                "result": result_type,
                "query": query,
                "limit": limit,
                "format": "json",    # always request JSON
                "dataPortal": "ena"
            },
            timeout=15  # don't wait forever if ENA is slow
        )

        if response.status_code == 200:
            data = response.json()
            # Return structured JSON the AI can read and summarise
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
        else:
            # Return a clear error message instead of crashing
            return [TextContent(
                type="text",
                text=f"ENA API error {response.status_code}: {response.text}"
            )]

    # ── TOOL 2: count_ena ───────────────────────────────────────
    elif name == "count_ena":

        query = arguments["query"]
        result_type = arguments.get("result_type", "read_run")

        response = requests.get(
            f"{BASE_URL}/count",
            params={
                "result": result_type,
                "query": query,
                "dataPortal": "ena"
            },
            timeout=15
        )

        if response.status_code == 200:
            # ENA sometimes returns "count\n7273037"
            # so we extract just the number from the last line
            text = response.text.strip()
            number = text.split('\n')[-1].strip()
            return [TextContent(
                type="text",
                text=f"Records matching '{query}' in {result_type}: {int(number):,}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"ENA API error {response.status_code}: {response.text}"
            )]

    # ── TOOL 3: get_searchable_fields ───────────────────────────
    elif name == "get_searchable_fields":

        result_type = arguments.get("result_type", "sample")

        # format=json is required — without it ENA returns an empty response
        response = requests.get(
            f"{BASE_URL}/searchFields",
            params={
                "result": result_type,
                "dataPortal": "ena",
                "format": "json"
            },
            timeout=15
        )

        if response.status_code == 200 and response.text.strip():
            data = response.json()
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"ENA API returned empty response for result_type: {result_type}"
            )]

    # ── UNKNOWN TOOL ────────────────────────────────────────────
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}. Available tools: search_ena, count_ena, get_searchable_fields"
        )]


# ── SERVER STARTUP ──────────────────────────────────────────────
async def main():
    """
    Start the MCP server using stdio transport.
    The server listens for tool calls from an AI agent
    and routes them to the appropriate ENA API endpoint.
    """
    print("Starting ENA MCP Server...")
    print("Listening for tool calls from AI agents...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())