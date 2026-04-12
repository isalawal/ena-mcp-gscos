# test_server.py
# basic tests for the ENA MCP server tools
# runs against the real ENA API so requires internet connection

import pytest
import requests
from server import cached_get, BASE_URL, _cache


def test_base_url_is_correct():
    # make sure we're pointing at the right API
    assert "ebi.ac.uk/ena/portal/api" in BASE_URL


def test_search_returns_results():
    # search for human samples and check we get something back
    response = cached_get(f"{BASE_URL}/search", {
        "result": "sample",
        "query": "tax_eq(9606)",
        "limit": 3,
        "format": "json",
        "dataPortal": "ena"
    })
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_count_returns_number():
    # count human read runs and check it's a big number
    response = cached_get(f"{BASE_URL}/count", {
        "result": "read_run",
        "query": "tax_eq(9606)",
        "dataPortal": "ena"
    })
    assert response.status_code == 200
    text = response.text.strip()
    number = int(text.split('\n')[-1].strip())
    assert number > 1000000  # should be millions


def test_searchable_fields_returns_list():
    # check that searchable fields returns a non-empty list
    response = cached_get(f"{BASE_URL}/searchFields", {
        "result": "sample",
        "dataPortal": "ena",
        "format": "json"
    })
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_return_fields_returns_list():
    # check that return fields returns a non-empty list
    response = cached_get(f"{BASE_URL}/returnFields", {
        "result": "sample",
        "dataPortal": "ena",
        "format": "json"
    })
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_result_types_returns_list():
    # check that ENA returns available data types
    response = cached_get(f"{BASE_URL}/results", {
        "dataPortal": "ena",
        "format": "json"
    })
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_cache_works():
    # call the same endpoint twice and check cache is populated
    params = {
        "result": "sample",
        "query": "tax_eq(9606)",
        "limit": 1,
        "format": "json",
        "dataPortal": "ena"
    }
    url = f"{BASE_URL}/search"

    # first call — hits ENA
    cached_get(url, params)

    # second call — should come from cache
    key = str(url) + str(sorted(params.items()))
    assert key in _cache  # confirm it was cached