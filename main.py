import asyncio
import aiohttp
import os
from dotenv import load_dotenv, set_key
from discovery.cert_listener import CertStreamDiscoverer
from extraction.jina_scraper import extract_json
from database.db_manager import DatabaseManager
from sheets_manager import SheetsManager

# Load environment variables
load_dotenv()
ENV_FILE = ".env"

# --- CONFIGURATION ---
CONCURRENCY = 10 
# Point this to your service account JSON file
CREDENTIALS_PATH = "/home/tracxn-lp-760/Downloads/dev/nim-sum/ashish_credentials.json"
# Read from .env
SHEET_URL = os.getenv("SHEET_URL")

async def check_jina_limits(session, api_key):
    """Pre-flight check to get Jina rate limits."""
    if not api_key:
        return
    print("\n[Tracker] Pinging Jina AI API for rate limits...")
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with session.get("https://r.jina.ai/https://example.com", headers=headers) as resp:
            rem_req = resp.headers.get("x-ratelimit-remaining-requests", "N/A")
            limit_req = resp.headers.get("x-ratelimit-limit-requests", "N/A")
            rem_tok = resp.headers.get("x-ratelimit-remaining-tokens", "N/A")
            print(f"=====================================")
            print(f"| JINA API STATUS                   |")
            print(f"| Requests left this minute: {rem_req}/{limit_req}")
            print(f"| Tokens left this minute:   {rem_tok}")
            print(f"=====================================\n")
    except Exception as e:
        print(f"[Tracker] Could not fetch limits: {e}\n")

async def interactive_setup(sheets: SheetsManager):
    """Handles the CLI logic for API keys before the crawler starts."""
    sheet_key = sheets.get_jina_api_key()
    env_key = os.getenv("JINA_API_KEY")
    
    current_key = sheet_key or env_key
    
    if not current_key:
        print("\n[!] No Jina API Key found.")
        new_key = input("Please paste your Jina AI API Key here: ").strip()
        if new_key:
            sheets.set_jina_api_key(new_key)
            set_key(ENV_FILE, "JINA_API_KEY", new_key)
            return new_key
        return None
        
    masked_key = f"{current_key[:6]}...{current_key[-4:]}" if len(current_key) > 10 else "***"
    print(f"\n[?] Jina API Key found: {masked_key}")
    choice = input("Do you want to use this key? [Enter for Yes, or type 'switch']: ").strip().lower()
    
    if choice == 'switch':
        new_key = input("Paste your NEW Jina AI API Key here: ").strip()
        if new_key:
            sheets.set_jina_api_key(new_key)
            set_key(ENV_FILE, "JINA_API_KEY", new_key)
            return new_key
            
    # If they press Enter, ensure it's saved in both places just in case
    if current_key and current_key != sheet_key:
        sheets.set_jina_api_key(current_key)
    if current_key and current_key != env_key:
        set_key(ENV_FILE, "JINA_API_KEY", current_key)
        
    return current_key

async def worker(worker_id: int, queue: asyncio.Queue, session: aiohttp.ClientSession, db_manager: DatabaseManager, sheets: SheetsManager, jina_key: str):
    print(f"[Worker {worker_id}] Started.")
    while True:
        domain = await queue.get()
        print(f"[Worker {worker_id}] Processing: {domain}")
        
        # Extract JSON using Jina AI
        json_content = await extract_json(domain, session, jina_key)
        
        if json_content:
            # 1. Save to local SQLite Backup
            db_manager.insert_company(domain, json_content)
            
            # 2. Push directly to Google Sheets (using a thread so it doesn't block async)
            await asyncio.to_thread(sheets.append_extracted_data, domain, json_content)
            
            print(f"[Worker {worker_id}] SUCCESS -> {domain} (Pushed to Sheet)")
            
        queue.task_done()
        await asyncio.sleep(1)

async def main():
    if not SHEET_URL or SHEET_URL == "PASTE_YOUR_SPREADSHEET_URL_HERE":
        print("ERROR: Please paste your Google Sheet URL into the SHEET_URL variable in your .env file!")
        return

    # 1. Initialize local DB
    db = DatabaseManager()
    
    # 2. Connect to Google Sheets & Provision UI
    sheets = SheetsManager(CREDENTIALS_PATH, SHEET_URL)
    
    # 3. Interactive CLI Setup
    jina_key = await interactive_setup(sheets)
    
    async with aiohttp.ClientSession() as session:
        # 4. Pre-Flight Tracker
        if jina_key:
            await check_jina_limits(session, jina_key)
        else:
            print("[Auth] No API Key provided. Running without authentication.")
            
        # 5. Start Discovery Thread
        discoverer = CertStreamDiscoverer()
        discoverer.start_background()
        
        # 6. Async Worker Pool
        task_queue = asyncio.Queue()
        
        workers = [
            asyncio.create_task(worker(i, task_queue, session, db, sheets, jina_key))
            for i in range(CONCURRENCY)
        ]
        
        print("[Main] Workers started. Listening for live domains...")
        
        try:
            while True:
                new_domains = discoverer.get_domains(max_batch=20)
                for d in new_domains:
                    await task_queue.put(d)
                await asyncio.sleep(2)
        except KeyboardInterrupt:
            print("\n[Main] Stopping gracefully...")
        finally:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
