import asyncio
import aiohttp
import json
import os
from discovery.cert_listener import CertStreamDiscoverer
from extraction.jina_scraper import extract_markdown

# Configuration
CONCURRENCY = 10 # Number of simultaneous extraction workers
JINA_API_KEY = None # Add your key here if you have one
OUTPUT_DIR = "data"

async def worker(worker_id: int, queue: asyncio.Queue, session: aiohttp.ClientSession, output_file):
    print(f"[Worker {worker_id}] Started.")
    while True:
        domain = await queue.get()
        print(f"[Worker {worker_id}] Processing: {domain}")
        
        content = await extract_markdown(domain, session, JINA_API_KEY)
        
        if content:
            # We found a live website and extracted it!
            result = {
                "domain": domain,
                "content": content
            }
            # Save to JSONL
            output_file.write(json.dumps(result) + "\n")
            output_file.flush()
            print(f"[Worker {worker_id}] SUCCESS -> {domain} ({len(content)} chars)")
            
        queue.task_done()
        # Be nice to the API
        await asyncio.sleep(1)

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "results.jsonl")
    
    # Start the discovery thread
    discoverer = CertStreamDiscoverer()
    discoverer.start_background()
    
    # Asyncio queue to feed workers
    task_queue = asyncio.Queue()
    
    # Open the output file in append mode
    with open(out_path, 'a', encoding='utf-8') as output_file:
        async with aiohttp.ClientSession() as session:
            # Create worker pool
            workers = [
                asyncio.create_task(worker(i, task_queue, session, output_file))
                for i in range(CONCURRENCY)
            ]
            
            print("[Main] Workers started. Listening for domains...")
            
            try:
                # Main loop: pull from the thread queue and push to async queue
                while True:
                    new_domains = discoverer.get_domains(max_batch=20)
                    for d in new_domains:
                        await task_queue.put(d)
                    
                    # Wait a bit before checking for new domains again
                    await asyncio.sleep(2)
            except KeyboardInterrupt:
                print("\n[Main] Stopping gracefully...")
            finally:
                # Cancel workers on exit
                for w in workers:
                    w.cancel()
                await asyncio.gather(*workers, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
