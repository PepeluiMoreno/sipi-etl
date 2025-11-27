import os
import requests
from typing import Generator, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
import threading
from config.settings import settings

logger = logging.getLogger(__name__)

class OSMClient:
    def __init__(self, query_file: str = None):
        self.semaphore = threading.Semaphore(3)
        self.session = requests.Session()
        if query_file:
            self.query_template_path = query_file
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.query_template_path = os.path.join(current_dir, "queries", "churches.overpassql")
        if not os.path.exists(self.query_template_path):
            raise FileNotFoundError(f"Query template not found: {self.query_template_path}")
    
    def load_query(self, country: str, timeout: int) -> str:
        with open(self.query_template_path, "r", encoding="utf-8") as f:
            query = f.read()
        return query.replace("{{country}}", country).replace("{{timeout}}", str(timeout))
    
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(min=2, max=60))
    def stream_elements(self, country: str = "ES") -> Generator[List[Dict[str, Any]], None, None]:
        with self.semaphore:
            query = self.load_query(country, settings.overpass_timeout)
            response = self.session.post(settings.overpass_url, data=query, headers={"User-Agent": settings.user_agent}, timeout=settings.overpass_timeout)
            response.raise_for_status()
            data = response.json()
            elements = data.get("elements", [])
            batch_size = settings.osm_batch_size
            for i in range(0, len(elements), batch_size):
                yield elements[i : i + batch_size]
