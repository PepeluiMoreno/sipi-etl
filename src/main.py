import argparse
from core.scheduler import ETLScheduler
from core.pipeline import OSMWikidataPipeline
from fastapi import FastAPI
from api.notifications import router as notifications_router

def run_cli():
    parser = argparse.ArgumentParser(description="SIPI-ETL")
    parser.add_argument("--country", default="ES")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--interval", type=int, default=24)
    parser.add_argument("--api", action="store_true")
    args = parser.parse_args()
    
    if args.api:
        app = FastAPI()
        app.include_router(notifications_router)
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    elif args.daemon:
        scheduler = ETLScheduler(OSMWikidataPipeline)
        scheduler.add_job(args.country, args.interval)
        scheduler.start()
    else:
        pipeline = OSMWikidataPipeline(country=args.country)
        pipeline.execute()

if __name__ == "__main__":
    run_cli()
