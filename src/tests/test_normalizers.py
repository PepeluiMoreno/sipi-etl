from modules.portals.osmwikidata.transform.normalizers import infer_type, should_keep, generate_qa_flags

def test_infer_type_from_building():
    assert infer_type({"building": "cathedral"}) == "cathedral"

def test_infer_type_from_amenity():
    assert infer_type({"amenity": "place_of_worship"}) == "place_of_worship"

def test_should_keep_no_name():
    assert should_keep({"building": "church"}, "church") is False

def test_generate_qa_flags():
    flags = generate_qa_flags({"name": "Test", "building": "church"}, "Q123")
    assert flags["missing_wikidata"] is False
