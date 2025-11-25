from unittest.mock import Mock
from modules.portals.osmwikidata.extract.wikidata_client import WikidataClient

def test_fetch_batch():
    client = WikidataClient()
    client.session = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {"results": {"bindings": [{"item": {"value": "http://www.wikidata.org/entity/Q123"}, "inception": {"value": "1800"}}]}}
    mock_response.raise_for_status = Mock()
    client.session.post = Mock(return_value=mock_response)
    result = client.fetch_batch(["Q123"])
    assert "Q123" in result
