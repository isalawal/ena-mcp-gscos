# ena_search.py
# Proof of concept: calls three ENA Portal API endpoints
# and returns real genomic data from the European Nucleotide Archive.
# Part of GSoC 2026 application — EMBL-EBI

import requests
import json

# Base URL for all ENA Portal API calls
BASE_URL = "https://www.ebi.ac.uk/ena/portal/api"


def count_records(query, result_type="read_run"):
    """
    Count how many ENA records match a given query.

    Args:
        query       : ENA query string e.g. tax_eq(9606) for human
        result_type : data type to count - read_run, sample, or study

    Returns:
        integer count of matching records
    """
    url = f"{BASE_URL}/count"

    # Build the request parameters
    params = {
        "result": result_type,   # what kind of data to count
        "query": query,          # the filter expression
        "dataPortal": "ena"      # target the ENA data portal
    }

    response = requests.get(url, params=params, timeout=15)

    if response.status_code == 200:
        # ENA sometimes returns "count\n7273037" so we extract
        # just the number from the last line of the response
        text = response.text.strip()
        number = text.split('\n')[-1].strip()
        return int(number)
    else:
        raise Exception(f"ENA API error {response.status_code}: {response.text}")


def search_records(query, result_type="sample", limit=5):
    """
    Search ENA and return matching genomic records as a list.

    Args:
        query       : ENA query string e.g. tax_eq(9606) for human samples
        result_type : data type to search - sample, read_run, or study
        limit       : max number of records to return (default 5)

    Returns:
        list of matching records as JSON objects
    """
    url = f"{BASE_URL}/search"

    # Build query parameters for the ENA Portal API
    params = {
        "result": result_type,   # what kind of data to search
        "query": query,          # the filter expression
        "limit": limit,          # how many results to return
        "format": "json",        # always request JSON responses
        "dataPortal": "ena"      # target the ENA data portal
    }

    response = requests.get(url, params=params, timeout=15)

    if response.status_code == 200:
        return response.json()   # return structured list of records
    else:
        raise Exception(f"ENA API error {response.status_code}: {response.text}")


def get_searchable_fields(result_type="sample"):
    """
    Get all fields that can be searched for a given result type.
    Useful for discovering what filters are available before searching.

    Args:
        result_type : data type - sample, read_run, or study

    Returns:
        list of searchable field objects with name and description
    """
    url = f"{BASE_URL}/searchFields"

    # format=json is required here — without it ENA returns empty response
    params = {
        "result": result_type,
        "dataPortal": "ena",
        "format": "json"
    }

    response = requests.get(url, params=params, timeout=15)

    if response.status_code == 200 and response.text.strip():
        return response.json()
    else:
        # Return a safe fallback instead of crashing
        return {"error": f"Empty or failed response: {response.status_code}"}


# ── DEMO ──────────────────────────────────────────────────────────
# Run this file directly to test all three ENA API functions
if __name__ == "__main__":
    print("=== ENA API Proof of Concept ===\n")

    # Test 1: Count how many human sequencing runs exist in ENA
    # 9606 is the NCBI taxonomy ID for Homo sapiens
    print("1. Counting human sequencing runs...")
    count = count_records(query="tax_eq(9606)", result_type="read_run")
    print(f"   Total: {count:,}\n")

    # Test 2: Fetch 3 real human sample records from ENA
    print("2. Fetching 3 human samples...")
    samples = search_records(
        query="tax_eq(9606)",
        result_type="sample",
        limit=3
    )
    print(json.dumps(samples, indent=2))

    # Test 3: Discover what fields we can search by for samples
    print("\n3. Getting searchable fields for 'sample'...")
    fields = get_searchable_fields("sample")
    if isinstance(fields, list):
        print(f"   Found {len(fields)} searchable fields")
        print(f"   First 5: {[f['columnId'] for f in fields[:5]]}")
    else:
        print(f"   {fields}")