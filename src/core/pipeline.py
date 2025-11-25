import logging
import time
import json
from datetime import datetime
from typing import List
from db.connection import get_raw_connection
from modules.portals.osmwikidata.extract.osm_client import OSMClient
from modules.portals.osmwikidata.extract.wikidata_client import WikidataClient
from modules.portals.osmwikidata.load.inmuebles_ext import InmueblesLoader
from core.differ import DatasetDiffer
from core.notification_service import NotificationService

logger = logging.getLogger(__name__)

class OSMWikidataPipeline:
    def __init__(self, country: str = "ES", query_file: str = None):
        self.country = country
        self.osm_client = OSMClient(query_file)
        self.wikidata_client = WikidataClient()
        self.db_loader = InmueblesLoader()
        self.differ = DatasetDiffer(osmwikidata.inmuebles, osm_id)
        self.notification_service = NotificationService()
        self.run_id = None
    
    def extract_transform(self) -> List[dict]:
        all_data = []
        for batch in self.osm_client.stream_elements(self.country):
            qids = [el.get(tags, {}).get(wikidata) for el in batch if el.get(tags, {}).get(wikidata)]
            wd_data = self.wikidata_client.enrich_all(qids) if qids else {}
            
            for element in batch:
                tags = element.get(tags, {})
                qid = tags.get(wikidata)
                wd_info = wd_data.get(qid, {})
                
                all_data.append({
                    osm_id: f"{element[type]}_{element[id]}",
                    name: tags.get(name),
                    inferred_type: self._infer_type(tags),
                    denomination: tags.get(denomination),
                    diocese: wd_info.get(diocese),
                    operator: tags.get(operator),
                    wikidata_qid: qid,
                    inception: wd_info.get(inception),
                    commons_category: wd_info.get(commons_cat),
                    heritage_status: wd_info.get(heritage),
                    historic: tags.get(historic),
                    ruins: tags.get(ruins) == yes,
                    geom_wkt: self._get_geometry(element),
                    qa_flags: self._validate_qa(tags, qid),
                    source_refs: tags.get(source),
                    address_street: tags.get(addr:street),
                    address_city: tags.get(addr:city),
                    address_postcode: tags.get(addr:postcode),
                })
        return all_data
    
    def execute(self):
        started_at = datetime.now()
        summary = {status: running, diff: {added: 0, deleted: 0, modified: 0}}
        
        try:
            with get_raw_connection() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO osmwikidata.pipeline_runs (started_at, country, status) VALUES (%s, %s, %s) RETURNING run_id", (started_at, self.country, running))
                self.run_id = cur.fetchone()[0]
            
            data = self.extract_transform()
            changes_df, diff_summary = self.differ.compare(data)
            
            if diff_summary[added] + diff_summary[modified] + diff_summary[deleted] > 0:
                self.db_loader.bulk_insert_sql(data, self.run_id)
                summary[status] = success
            else:
                summary[status] = no_changes
            
            duration = (datetime.now() - started_at).seconds
            with get_raw_connection() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE osmwikidata.pipeline_runs SET finished_at = NOW(), status = %s, records_loaded = %s, execution_time_seconds = %s, diff_summary = %s WHERE run_id = %s", (summary[status], len(data), duration, json.dumps(diff_summary), self.run_id))
            
            summary[diff] = diff_summary
            
        except Exception as e:
            summary[status] = failed
            summary[error] = str(e)
            with get_raw_connection() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE osmwikidata.pipeline_runs SET status = failed, error_message = %s WHERE run_id = %s", (str(e), self.run_id))
        
        finally:
            self.notification_service.create(type=f"etl_{summary[status]}", title=f"ETL {self.country} - {summary[status]}", message=f"Added: {diff_summary[added]}", run_id=self.run_id, metadata=summary)
            self.db_loader.close()
    
    def _infer_type(self, tags: dict) -> str:
        return tags.get(building, tags.get(amenity, unknown))
    
    def _get_geometry(self, element: dict) -> str:
        if center in element:
            return f"POINT({element[center][lon]} {element[center][lat]})"
        return "POINT(0 0)"
    
    def _validate_qa(self, tags: dict, qid: str) -> dict:
        return {"missing_wikidata": qid is None, "no_name": "name" not in tags}
