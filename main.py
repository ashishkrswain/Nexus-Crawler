import asyncio
import aiohttp
import os
from discovery.cert_listener import CertStreamDiscoverer
from extraction.jina_scraper import extract_markdown
from database.db_manager import DatabaseManager

# Configuration
CONCURRENCY = 10 # Number of simultaneous extraction workers
JINA_API_KEY = None # Add your key here if you have one

async def worker(worker_id: int, queue: asyncio.Queue, session: aiohttp.ClientSession, db_manager: DatabaseManager):
    print(f"[Worker {worker_id}] Started.")
    while True:
        domain = await queue.get()
        print(f"[Worker {worker_id}] Processing: {domain}")
        
        # Send it to Jina AI
        content = await extract_markdown(domain, session, JINA_API_KEY)
        
        if content:
            # Save the clean data to the SQLite database
            db_manager.insert_company(domain, content)
            print(f"[Worker {worker_id}] SUCCESS -> {domain} ({len(content)} chars saved to DB)")
            
        queue.task_done()
        # Sleep to be polite to the API
        await asyncio.sleep(1)

async def main():
    # Initialize the Database
    print("[Main] Initializing SQLite Database...")
    db = DatabaseManager()
    
    # Start the background discovery thread
    discoverer = CertStreamDiscoverer()
    discoverer.start_background()
    
    # Asyncio queue to feed workers
    task_queue = asyncio.Queue()
    
    async with aiohttp.ClientSession() as session:
        # Create the pool of asynchronous workers
        workers = [
            asyncio.create_task(worker(i, task_queue, session, db))
            for i in range(CONCURRENCY)
        ]
        
        print("[Main] Workers started. Listening for live domains...")
        
        try:
            # Main event loop
            while True:
                # Pull newly discovered domains from the background thread
                new_domains = discoverer.get_domains(max_batch=20)
                
                # Push them into the asynchronous worker queue
                for d in new_domains:
                    await task_queue.put(d)
                
                # Wait before checking for more domains
                await asyncio.sleep(2)
                
        except KeyboardInterrupt:
            print("\n[Main] Stopping gracefully...")
        finally:
            # Cancel all workers on exit
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
