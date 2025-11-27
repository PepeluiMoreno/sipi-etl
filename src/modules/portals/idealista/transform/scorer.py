"""
Scoring religioso para Idealista
"""
from typing import Dict, List, Any
from src.modules.portals.idealista.config.keywords import POSITIVE, NEGATIVE, EXPLICIT
from src.modules.portals.idealista.config.scoring import WEIGHTS, PROXIMITY, SURFACE
from src.modules.portals.idealista.transform.geo_fallback import GeoFallback

class ReligiousPropertyScorer:
    def __init__(self):
        pass  # Sin estado, solo lógica

    def score(self, inmueble: Dict[str, Any]) -> tuple[float, List[str]]:
        score = 0
        evidences: List[str] = []

        # 1. Keywords (desde PY)
        text = f"{inmueble.get('titulo_completo', '')} {' '.join(inmueble.get('caracteristicas_extras', []))}"
        text_lower = text.lower()

        # Explícitas → 100 %
        if any(k in text_lower for k in EXPLICIT):
            score = 100
            evidencias.append("Keyword explícita (100 %)")
        else:
            # Positivas / negativas
            for kw in POSITIVE:
                if kw.lower() in text_lower:
                    score += WEIGHTS["keywords"] // len(POSITIVE)
                    evidencias.append(f"Keyword positiva '{kw}'")
            for kw in NEGATIVE:
                if kw.lower() in text_lower:
                    score -= WEIGHTS["keywords"] // len(NEGATIVE)
                    evidencias.append(f"Keyword negativa '{kw}'")

        # 2. Proximidad OSM (desde PY)
        lat, lon = inmueble.get("latitud"), inmueble.get("longitud")
        if lat is not None and lon is not None:
            churches = self.overpass.find_churches_nearby(lat, lon, PROXIMITY["radius_meters"])
            if churches:
                closest = churches[0]
                score += PROXIMITY["max_score"] * (1 - min(closest.distance / 300, 1))
                evidencias.append(f"{len(churches)} iglesia(s) OSM en {PROXIMITY['radius_meters']}m, más cercana a {closest.distance:.0f}m")

        # 3. Superficie y características (desde PY)
        m2 = inmueble.get("m2_construidos")
        if m2 and m2 >= SURFACE["min_size_m2"]:
            score += SURFACE["max_score"]
            evidencias.append(f"Superficie ≥ {SURFACE['min_size_m2']}m²")
        extras = " ".join(inmueble.get("caracteristicas_extras", [])).lower()
        if any(t in extras for t in ["techos altos", "doble altura"]):
            score += SURFACE["bonus"]["high_ceilings"]
            evidencias.append("Techos altos/doble altura")
        if any(t in extras for t in ["varias plantas", "múltiples niveles"]):
            score += SURFACE["bonus"]["multiple_floors"]
            evidencias.append("Múltiples niveles")

        return min(score, 100), evidencias