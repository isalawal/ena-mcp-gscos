import requests
import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

BASE_URL = "https://www.ebi.ac.uk/ena/portal/api"

app = Server("ena-mcp-server")


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="search_ena",
            description="Search the European Nucleotide Archive for genomic records. Use this to find samples, studies, or sequencing runs matching a query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "ENA query string e.g. tax_eq(9606) for human"
                    },
                    "result_type": {
                        "type": "string",
                        "description": "Data type to search: sample, read_run, or study",
                        "default": "sample"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (max 100)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="count_ena",
            description="Count how many records in ENA match a query. Use this before searching to understand the scale of results.",
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
            description="Get all fields that can be searched for a given ENA result type. Use this to discover what filters are available.",
            inputSchema={
                "type": "object",
                "properties": {
                    "result_type": {
                        "type": "string",
                        "description": "Data type: sample, read_run, or study",
                        "default": "sample"
                    }
                },
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):

    if name == "search_ena":
        query = arguments["query"]
        result_type = arguments.get("result_type", "sample")
        limit = arguments.get("limit", 5)

        response = requests.get(f"{BASE_URL}/search", params={
            "result": result_type,
            "query": query,
            "limit": limit,
            "format": "json",
            "dataPortal": "ena"
        })

        if response.status_code == 200:
            data = response.json()
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"ENA API error {response.status_code}: {response.text}"
            )]

    elif name == "count_ena":
        query = arguments["query"]
        result_type = arguments.get("result_type", "read_run")

        response = requests.get(f"{BASE_URL}/count", params={
            "result": result_type,
            "query": query,
            "dataPortal": "ena"
        })

        if response.status_code == 200:
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

    elif name == "get_searchable_fields":
        result_type = arguments.get("result_type", "sample")

        response = requests.get(f"{BASE_URL}/searchFields", params={
            "result": result_type,
            "dataPortal": "ena",
            "format": "json"
        })

        if response.status_code == 200 and response.text.strip():
            data = response.json()
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Error {response.status_code}"
            )]

    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


async def main():
    print("Starting ENA MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())