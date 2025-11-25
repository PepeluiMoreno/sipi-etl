from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from config.settings import settings

class ETLScheduler:
    def __init__(self, pipeline_class):
        self.pipeline_class = pipeline_class
        self.scheduler = BlockingScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=settings.DB_CONN_STRING_ORM)},
            job_defaults={"max_instances": 1, "coalesce": True}
        )
    
    def add_job(self, country: str = "ES", interval_hours: int = 24):
        self.scheduler.add_job(func=self.run_pipeline, trigger="interval", hours=interval_hours, id=f"etl_{country}", replace_existing=True, kwargs={"country": country})
    
    def run_pipeline(self, country: str):
        pipeline = self.pipeline_class(country=country)
        pipeline.execute()
    
    def start(self):
        self.scheduler.start()
