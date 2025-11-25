import pytest
from sqlalchemy import create_engine
from config.settings import settings

@pytest.fixture
def sample_osm_element():
    return {"type": "node", "id": 123456, "lat": 40.416775, "lon": -3.703790, "tags": {"amenity": "place_of_worship", "name": "Iglesia de San Test", "building": "church", "denomination": "catholic", "wikidata": "Q12345"}, "version": 5, "timestamp": "2023-01-01T00:00:00Z"}

@pytest.fixture
def db_engine():
    return create_engine(settings.DB_CONN_STRING)

@pytest.fixture
def mock_osm_client(monkeypatch):
    from modules.portals.osmwikidata.extract.osm_client import OSMClient
    monkeypatch.setattr(OSMClient, "load_query", lambda self, country, timeout: "[out:json]; node(40.0, -4.0, 41.0, -3.0); out;")
    return OSMClient()

@pytest.fixture
def mock_wikidata_client():
    from modules.portals.osmwikidata.extract.wikidata_client import WikidataClient
    client = WikidataClient()
    client.session = None
    return client
