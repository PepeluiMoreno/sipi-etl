import requests
from typing import Dict, List, Any
from tenacity import retry, stop_after_attempt, wait_exponential
import time
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class WikidataClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/sparql-results+json", "User-Agent": settings.user_agent})
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=30))
    def fetch_batch(self, qids: List[str]) -> Dict[str, Dict[str, Any]]:
        wd_items = " ".join(f"wd:{q}" for q in qids)
        query = f"""SELECT ?item ?itemLabel ?inception ?heritage ?diocese ?coord ?commonsCat WHERE {{
VALUES ?item {{ {wd_items} }}
OPTIONAL {{ ?item wdt:P571 ?inception. }}
OPTIONAL {{ ?item wdt:P1435 ?heritage. }}
OPTIONAL {{ ?item wdt:P708 ?diocese. }}
OPTIONAL {{ ?item wdt:P625 ?coord. }}
OPTIONAL {{ ?item wdt:P373 ?commonsCat. }}
SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
}}"""
        time.sleep(settings.wd_min_delay)
        response = self.session.post(settings.wdqs_url, data={"query": query}, timeout=settings.wd_timeout_seconds)
        response.raise_for_status()
        data = response.json()
        wd_map = {}
        for binding in data.get("results", {}).get("bindings", []):
            qid = binding["item"]["value"].split("/")[-1]
            wd_map[qid] = {"inception": binding.get("inception", {}).get("value"), "heritage": binding.get("heritage", {}).get("value"), "diocese": binding.get("diocese", {}).get("value"), "commons_cat": binding.get("commonsCat", {}).get("value")}
        return wd_map
    
    def enrich_all(self, qids: List[str]) -> Dict[str, Dict[str, Any]]:
        if not qids:
            return {}
        batches = [qids[i : i + settings.wd_batch_size] for i in range(0, len(qids), settings.wd_batch_size)]
        logger.info(f"📚 Enriqueciendo {len(qids)} QIDs en {len(batches)} batches")
        all_data = {}
        for i, batch in enumerate(batches):
            try:
                result = self.fetch_batch(batch)
                all_data.update(result)
                logger.debug(f"✅ Batch {i+1}/{len(batches)} completado")
            except Exception as e:
                logger.error(f"Batch {i} falló: {e}")
        logger.info(f"✅ Enriquecidos {len(all_data)} elementos desde Wikidata")
        return all_data
