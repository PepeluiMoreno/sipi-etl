from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_CONN_STRING: str = "postgresql://sipi:sipi@db:5432/sipi"
    DB_CONN_STRING_ORM: str = "postgresql://sipi:sipi@db:5432/sipi"
    
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    OVERPASS_TIMEOUT: int = 60
    OSM_BATCH_SIZE: int = 1000
    OSM_QUERY_FILE: str = "src/modules/portals/osmwikidata/extract/queries/churches.overpassql"
    
    WDQS_URL: str = "https://query.wikidata.org/sparql"
    WD_BATCH_SIZE: int = 50
    WD_MIN_DELAY: float = 1.0
    
    SCHEDULE_INTERVAL_HOURS: int = 24
    
    NOTIFICATIONS_ENABLED: bool = True
    SLACK_BOT_TOKEN: str = ""
    EMAIL_ALERT_TO: str = ""
    SMTP_HOST: str = "localhost"
    
    class Config:
        env_file = ".env"

settings = Settings()
