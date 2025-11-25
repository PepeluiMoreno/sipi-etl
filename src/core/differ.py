from typing import Dict, List, Tuple
import pandas as pd
from db.connection import get_raw_connection

class DatasetDiffer:
    def __init__(self, table_name: str, key_column: str):
        self.table = table_name
        self.key_col = key_column
    
    def get_snapshot(self, run_id: int = None) -> pd.DataFrame:
        query = f"SELECT * FROM {self.table} WHERE run_id = %s OR run_id = (SELECT MAX(run_id) FROM osmwikidata.pipeline_runs WHERE status = success)"
        with get_raw_connection() as conn:
            return pd.read_sql(query, conn, params=(run_id,) if run_id else None)
    
    def compare(self, new_data: List[dict]) -> Tuple[pd.DataFrame, Dict]:
        old_df = self.get_snapshot()
        old_df.set_index(self.key_col, inplace=True)
        
        new_df = pd.DataFrame(new_data)
        new_df.set_index(self.key_col, inplace=True)
        
        added = new_df.index.difference(old_df.index)
        deleted = old_df.index.difference(new_df.index)
        common = new_df.index.intersection(old_df.index)
        
        new_df["data_hash"] = new_df.apply(lambda r: hash(tuple(r)), axis=1)
        old_df["data_hash"] = old_df.apply(lambda r: hash(tuple(r)), axis=1)
        modified = common[new_df.loc[common, "data_hash"] != old_df.loc[common, "data_hash"]]
        
        diff_summary = {"added": len(added), "deleted": len(deleted), "modified": len(modified), "unchanged": len(common) - len(modified)}
        changes_df = pd.concat([new_df.loc[added].assign(change_type="added"), new_df.loc[modified].assign(change_type="modified"), old_df.loc[deleted].assign(change_type="deleted")])
        return changes_df, diff_summary
