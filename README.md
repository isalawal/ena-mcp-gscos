# ENA MCP Server

A Model Context Protocol (MCP) server that exposes European Nucleotide Archive (ENA) REST APIs as callable tools for AI agents.

Built as a GSoC 2026 proof of concept for EMBL-EBI.

## What it does

Prevents AI hallucination by forcing AI agents to fetch real verified data from ENA before responding. The agent cannot invent genomic records because every response is fetched from ENA in real time.

## Tools

| Tool | Endpoint | Description |
|------|----------|-------------|
| search_ena | /search | Search ENA for genomic records |
| count_ena | /count | Count records matching a query |
| get_searchable_fields | /searchFields | Get fields you can filter by |
| get_return_fields | /returnFields | Get fields you can retrieve |
| get_result_types | /results | List all data types in ENA |
| get_accession_types | /accessionTypes | Get valid accession formats |
| get_controlled_vocab | /controlledVocab | Get valid values for a field |

## Setup

pip install mcp requests
python server.py

## Run tests

pip install pytest
pytest test_server.py -v

## Example queries

Search for human samples: tax_eq(9606), result_type: sample
Count mouse sequencing runs: tax_eq(10090), result_type: read_run
Get valid instrument platforms: field: instrument_platform

## Built for

Google Summer of Code 2026 - EMBL-EBI
Project: Expose a Subset of ENA REST Services as MCP
Mentor: Senthilnathan Vijayaraja
