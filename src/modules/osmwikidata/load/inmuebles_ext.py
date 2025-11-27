import psycopg2
from psycopg2.extras import Json, execute_batch
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class InmueblesLoader:
    def __init__(self):
        self.conn = psycopg2.connect(settings.DB_CONN_STRING, connect_timeout=10)
        self.conn.autocommit = False
    
    def bulk_insert_sql(self, data: list[dict], run_id: int):
        sql = """
        INSERT INTO osmwikidata.inmuebles (osm_id, name, inferred_type, denomination, diocese, operator, wikidata_qid, inception, commons_category, heritage_status, historic, ruins, geom, qa_flags, source_refs, address_street, address_city, address_postcode, run_id)
        VALUES (%(osm_id)s, %(name)s, %(inferred_type)s, %(denomination)s, %(diocese)s, %(operator)s, %(wikidata_qid)s, %(inception)s, %(commons_category)s, %(heritage_status)s, %(historic)s, %(ruins)s, ST_SetSRID(ST_GeomFromText(%(geom_wkt)s), 4326), %(qa_flags)s, %(source_refs)s, %(address_street)s, %(address_city)s, %(address_postcode)s, %(run_id)s)
        ON CONFLICT (osm_id) DO UPDATE SET
            name = EXCLUDED.name,
            wikidata_qid = EXCLUDED.wikidata_qid,
            updated_at = NOW(),
            qa_flags = EXCLUDED.qa_flags
        """
        try:
            with self.conn.cursor() as cur:
                for row in data:
                    row["run_id"] = run_id
                    if isinstance(row.get("qa_flags"), dict):
                        row["qa_flags"] = Json(row["qa_flags"])
                execute_batch(cur, sql, data, page_size=1000)
            self.conn.commit()
            logger.info(f"✅ Inserted {len(data)} records")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Load failed: {e}")
            raise
    
    def close(self):
        self.conn.close()
