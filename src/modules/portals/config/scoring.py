# Pesos y umbrales de scoring (para cualquier portal)
WEIGHTS = {"keywords": 70, "proximity": 20, "surface": 10}
PROXIMITY = {"enabled": True, "radius_meters": 200, "max_score": 20}
SURFACE = {"enabled": True, "min_size_m2": 300, "max_score": 10, "bonus": {"high_ceilings": 3, "multiple_floors": 3}}