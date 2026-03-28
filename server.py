# server.py
# ENA MCP Server - exposes ENA Portal API endpoints as MCP tools
# that any AI agent (Claude, GPT, etc.) can call directly.
# Prevents hallucination - the AI must fetch real data, it cannot invent it.
# GSoC 2026 application - EMBL-EBI
# GitHub: https://github.com/isalawal/ena-mcp-gscos

import requests
import json
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# base URL for all ENA Portal API calls
BASE_URL = "https://www.ebi.ac.uk/ena/portal/api"

# initialise the MCP server
app = Server("ena-mcp-server")


@app.list_tools()
async def list_tools():
    """
    Tell the AI agent what tools are available.
    The AI reads these to know what it can ask the server to do.
    """
    return [

        # tool 1 - search ENA for matching genomic records
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
                            "tax_eq(10090) for mouse"
                        )
                    },
                    "result_type": {
                        "type": "string",
                        "description": "Data type: sample, read_run, or study",
                        "default": "sample"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (default 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),

        # tool 2 - count records before fetching them
        # useful for understanding scale before running search_ena
        Tool(
            name="count_ena",
            description=(
                "Count how many records in ENA match a query. "
                "Use this before searching to understand the scale of results."
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

        # tool 3 - find out what fields you can search by
        # call this before search_ena to know what filters are available
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
                "required": []
            }
        ),

        # tool 4 - find out what data you can get back from a search
        # pair this with get_searchable_fields before running search_ena
        Tool(
            name="get_return_fields",
            description=(
                "Get all fields that can be returned in ENA search results. "
                "Call this to see what data is available, then use "
                "the field names in your search_ena calls."
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
                "required": []
            }
        ),


        # tool 5 - list all data types in ENA
        # good starting point before any search
        Tool(
            name="get_result_types",
            description=(
                "Get all available result types in ENA. "
                "Call this first to understand what kinds of data exist "
                "before searching. Returns types like sample, read_run, study, assembly."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),


        # tool 6 - get valid accession types for search queries
        # useful when searching by specific accession format
        Tool(
            name="get_accession_types",
            description=(
                "Get all valid accession types that can be used in ENA search queries. "
                "Returns formats like PRJEB, SRS, ERR, SRR. Use this to validate "
                "accession numbers before searching."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),


        # tool 7 - get valid values for a specific ENA field
        # stops the AI guessing field values like instrument_platform
        Tool(
            name="get_controlled_vocab",
            description=(
                "Get valid values for a controlled vocabulary field in ENA. "
                "For example, pass instrument_platform to get valid options "
                "like ILLUMINA, OXFORD_NANOPORE, PACBIO_SMRT. "
                "Use this before searching to avoid invalid field values."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": "Field name to get valid values for e.g. instrument_platform"
                    },
                    "result_type": {
                        "type": "string",
                        "description": "Data type: sample, read_run, or study",
                        "default": "read_run"
                    }
                },
                "required": ["field"]
            }
        ),

    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """
    Handle all tool calls from the AI agent.
    The AI sends a tool name and arguments.
    We call the real ENA API and return the result.
    The AI cannot invent data because it must fetch it here.
    """

    # tool 1 - search ENA records
    if name == "search_ena":
        query = arguments["query"]
        result_type = arguments.get("result_type", "sample")
        limit = arguments.get("limit", 5)

        # call the real ENA search endpoint
        response = requests.get(
            f"{BASE_URL}/search",
            params={
                "result": result_type,
                "query": query,
                "limit": limit,
                "format": "json",
                "dataPortal": "ena"
            },
            timeout=15
        )

        if response.status_code == 200:
            return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]
        else:
            return [TextContent(type="text",
                text=f"ENA API error {response.status_code}: {response.text}")]

    # tool 2 - count matching records
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
            # ENA sometimes returns "count\n7273037" so extract just the number
            text = response.text.strip()
            number = text.split('\n')[-1].strip()
            return [TextContent(type="text",
                text=f"Records matching '{query}' in {result_type}: {int(number):,}")]
        else:
            return [TextContent(type="text",
                text=f"ENA API error {response.status_code}: {response.text}")]

    # tool 3 - get searchable fields
    elif name == "get_searchable_fields":
        result_type = arguments.get("result_type", "sample")

        # format=json is required - without it ENA returns an empty response
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
            return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]
        else:
            return [TextContent(type="text",
                text=f"empty response from ENA for result_type: {result_type}")]

    # tool 4 - get returnable fields
    elif name == "get_return_fields":
        result_type = arguments.get("result_type", "sample")

        # ask ENA what data columns we can get back for this result type
        # format=json is required - without it ENA returns an empty response
        response = requests.get(
            f"{BASE_URL}/returnFields",
            params={
                "result": result_type,
                "dataPortal": "ena",
                "format": "json"
            },
            timeout=15
        )

        if response.status_code == 200 and response.text.strip():
            return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]
        else:
            return [TextContent(type="text",
                text=f"empty response from ENA for result_type: {result_type}")]


    # tool 5 - get all result types from ENA
    elif name == "get_result_types":

        # no query needed, just returns everything ENA has
        response = requests.get(
            f"{BASE_URL}/results",
            params={
                "dataPortal": "ena",
                "format": "json"
            },
            timeout=15
        )

        if response.status_code == 200 and response.text.strip():
            return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]
        else:
            return [TextContent(type="text",
                text=f"ENA API error {response.status_code}: {response.text}")]


    # tool 6 - get valid accession types from ENA
    elif name == "get_accession_types":

        # returns all accession formats ENA recognises e.g. PRJEB, ERR, SRS
        response = requests.get(
            f"{BASE_URL}/accessionTypes",
            params={
                "dataPortal": "ena",
                "format": "json"
            },
            timeout=15
        )

        if response.status_code == 200 and response.text.strip():
            return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]
        else:
            return [TextContent(type="text",
                text=f"ENA API error {response.status_code}: {response.text}")]


    # tool 7 - get valid values for a controlled vocab field
    elif name == "get_controlled_vocab":

        field = arguments["field"]
        result_type = arguments.get("result_type", "read_run")

        # returns all accepted values for a given field
        # e.g. instrument_platform -> ILLUMINA, OXFORD_NANOPORE etc.
        response = requests.get(
            f"{BASE_URL}/controlledVocab",
            params={
                "field": field,
                "result": result_type,
                "dataPortal": "ena",
                "format": "json"
            },
            timeout=15
        )

        if response.status_code == 200 and response.text.strip():
            return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]
        else:
            return [TextContent(type="text",
                text=f"no controlled vocab found for field: {field}")]

    # unknown tool
    else:
        return [TextContent(type="text",
            text=f"unknown tool: {name}. available: search_ena, count_ena, get_searchable_fields, get_return_fields, get_result_types, get_accession_types, get_controlled_vocab")]


# server startup
async def main():
    """Start the MCP server and listen for tool calls from AI agents."""
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
