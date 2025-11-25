from unittest.mock import Mock
from modules.portals.osmwikidata.extract.osm_client import OSMClient

def test_osm_client_initialization():
    client = OSMClient()
    assert client.semaphore._value == 3

def test_stream_elements_success(monkeypatch):
    client = OSMClient()
    mock_response = Mock()
    mock_response.json.return_value = {"elements": [{"type": "node", "id": 1}]}
    mock_response.raise_for_status = Mock()
    client.session.post = Mock(return_value=mock_response)
    batches = list(client.stream_elements("ES"))
    assert len(batches) == 1
