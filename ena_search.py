import requests
import json

BASE_URL = "https://www.ebi.ac.uk/ena/portal/api"

def count_records(query, result_type="read_run"):
    url = f"{BASE_URL}/count"
    params = {
        "result": result_type,
        "query": query,
        "dataPortal": "ena"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        text = response.text.strip()
        number = text.split('\n')[-1].strip()
        return int(number)
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


def search_records(query, result_type="sample", limit=5):
    url = f"{BASE_URL}/search"
    params = {
        "result": result_type,
        "query": query,
        "limit": limit,
        "format": "json",
        "dataPortal": "ena"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


def get_searchable_fields(result_type="sample"):
    url = f"{BASE_URL}/searchFields"
    params = {
        "result": result_type,
        "dataPortal": "ena",
        "format": "json"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200 and response.text.strip():
        return response.json()
    else:
        return {"error": str(response.status_code)}


if __name__ == "__main__":
    print("=== ENA API Proof of Concept ===\n")

    print("1. Counting human sequencing runs...")
    count = count_records(query="tax_eq(9606)", result_type="read_run")
    print(f"   Total: {count:,}\n")

    print("2. Fetching 3 human samples...")
    samples = search_records(query="tax_eq(9606)", result_type="sample", limit=3)
    print(json.dumps(samples, indent=2))

    print("\n3. Getting searchable fields for 'sample'...")
    fields = get_searchable_fields("sample")
    print(f"   Found {len(fields)} searchable fields")
    print(f"   First 5: {[f['columnId'] for f in fields[:5]]}")