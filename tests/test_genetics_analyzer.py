import os
import sys
import time
import types
import pytest

# Provide dummy 'requests' and 'aiohttp' modules if they are not installed
if 'requests' not in sys.modules:
    dummy_requests = types.ModuleType('requests')
    class DummySession:
        def __init__(self):
            self.headers = {}
        def get(self, *args, **kwargs):
            pass
    dummy_requests.Session = DummySession
    sys.modules['requests'] = dummy_requests

if 'aiohttp' not in sys.modules:
    sys.modules['aiohttp'] = types.ModuleType('aiohttp')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from diabetes_backend.services.genetics_analyzer import PGSCatalogClient

class DummyResponse:
    def __init__(self, data):
        self._data = data
    def json(self):
        return self._data
    def raise_for_status(self):
        pass

def mock_get_factory(data):
    def mock_get(url, params=None, timeout=None):
        return DummyResponse(data)
    return mock_get


def test_search_scores_by_trait_success(monkeypatch):
    client = PGSCatalogClient()
    monkeypatch.setattr(client, '_wait_for_rate_limit', lambda: None)

    data = {
        'results': [
            {
                'id': 'PGS1',
                'ancestry_distribution': 'EUR',
                'variants_number': 200000,
            },
            {
                'id': 'PGS2',
                'ancestry_distribution': 'Multi',
                'variants_number': 5000,
            },
            {
                'id': 'PGS000014',
                'ancestry_distribution': 'EUR',
                'variants_number': 200000,
            },
        ]
    }

    monkeypatch.setattr(client.session, 'get', mock_get_factory(data))

    results = client.search_scores_by_trait('EFO_0000400', 'EUR')
    assert len(results) == 3
    # Ensure results are sorted by dmp_quality_score descending
    scores = [r['id'] for r in results]
    assert scores == ['PGS000014', 'PGS1', 'PGS2']


def test_search_scores_by_trait_error(monkeypatch):
    client = PGSCatalogClient()
    monkeypatch.setattr(client, '_wait_for_rate_limit', lambda: None)

    def raise_error(url, params=None, timeout=None):
        raise RuntimeError('network error')

    monkeypatch.setattr(client.session, 'get', raise_error)
    results = client.search_scores_by_trait('EFO_0000400', 'EUR')
    assert results == []


def test_wait_for_rate_limit(monkeypatch):
    client = PGSCatalogClient()
    client.call_timestamps = [90] * client.RATE_LIMIT

    monkeypatch.setattr(time, 'time', lambda: 100)
    sleep_called = {}
    def fake_sleep(seconds):
        sleep_called['seconds'] = seconds
    monkeypatch.setattr(time, 'sleep', fake_sleep)

    client._wait_for_rate_limit()
    assert sleep_called.get('seconds') == 50
