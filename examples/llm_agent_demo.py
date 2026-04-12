# llm_agent_demo.py
# demonstrates real LLM querying of ENA via MCP tools
# Gemini decides which tools to call based on the user question
# all responses backed by real ENA data - no hallucinations

import requests
import json
import os
import time

BASE_URL = "https://www.ebi.ac.uk/ena/portal/api"
GEMINI_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"


def call_ena_tool(tool_name, tool_input):
    if tool_name == "search_ena":
        response = requests.get(f"{BASE_URL}/search", params={
            "result": tool_input.get("result_type", "sample"),
            "query": tool_input["query"],
            "limit": tool_input.get("limit", 5),
            "format": "json",
            "dataPortal": "ena"
        }, timeout=15)
        return response.json() if response.status_code == 200 else {"error": response.status_code}

    elif tool_name == "count_ena":
        response = requests.get(f"{BASE_URL}/count", params={
            "result": tool_input.get("result_type", "read_run"),
            "query": tool_input["query"],
            "dataPortal": "ena"
        }, timeout=15)
        if response.status_code == 200:
            number = int(response.text.strip().split("\n")[-1].strip())
            return {"count": number, "formatted": f"{number:,}"}
        return {"error": response.status_code}

    elif tool_name == "get_result_types":
        response = requests.get(f"{BASE_URL}/results", params={
            "dataPortal": "ena", "format": "json"
        }, timeout=15)
        return response.json() if response.status_code == 200 else {"error": response.status_code}

    return {"error": f"unknown tool: {tool_name}"}


def ask_gemini(question):
    print(f"\nUser: {question}")
    print("-" * 50)

    tools = [{"functionDeclarations": [
        {
            "name": "search_ena",
            "description": "Search ENA for real genomic records.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "ENA query e.g. tax_eq(9606)"},
                    "result_type": {"type": "STRING", "description": "sample, read_run, or study"},
                    "limit": {"type": "INTEGER", "description": "number of results"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "count_ena",
            "description": "Count how many ENA records match a query.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "ENA query string"},
                    "result_type": {"type": "STRING", "description": "sample, read_run, or study"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_result_types",
            "description": "Get all available data types in ENA.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "placeholder": {"type": "STRING", "description": "not used"}
                }
            }
        }
    ]}]

    contents = [{"role": "user", "parts": [{"text": question}]}]

    while True:
        payload = {"contents": contents, "tools": tools}
        response = requests.post(GEMINI_URL, json=payload, timeout=30)
        data = response.json()

        if "error" in data:
            print(f"Error: {data['error']['message']}")
            return

        parts = data["candidates"][0]["content"]["parts"]
        tool_calls = [p for p in parts if "functionCall" in p]

        if not tool_calls:
            text = "".join(p.get("text", "") for p in parts)
            print(f"\nGemini: {text}")
            return

        contents.append({"role": "model", "parts": parts})
        tool_results = []

        for part in tool_calls:
            fc = part["functionCall"]
            name = fc["name"]
            args = fc.get("args", {})
            print(f"\nGemini calls: {name}")
            print(f"  with: {json.dumps(args)}")
            result = call_ena_tool(name, args)
            print(f"  ENA returned: {str(result)[:120]}...")
            tool_results.append({
                "functionResponse": {
                    "name": name,
                    "response": {"result": json.dumps(result)}
                }
            })

        contents.append({"role": "user", "parts": tool_results})


if __name__ == "__main__":
    print("=== ENA MCP Server - LLM Agent Demo ===")
    print("Gemini queries real ENA data via MCP tools\n")

    questions = [
        "How many human sequencing runs are in ENA?",
        "Find me 3 human samples from ENA",
        "What types of data are available in ENA?"
    ]

    for i, question in enumerate(questions):
        ask_gemini(question)
        print("\n" + "=" * 50)
        if i < len(questions) - 1:
            print("waiting 10 seconds...")
            time.sleep(10)
