import asyncio
import aiohttp
import os
import datetime
from dotenv import load_dotenv, set_key
from discovery.jina_searcher import search_industry_domains
from extraction.jina_scraper import extract_json
from database.db_manager import DatabaseManager
from sheets_manager import SheetsManager

# Load environment variables
load_dotenv()
ENV_FILE = ".env"

# --- CONFIGURATION ---
CONCURRENCY = 10 
CREDENTIALS_PATH = "/home/tracxn-lp-760/Downloads/dev/nim-sum/ashish_credentials.json"
SHEET_URL = os.getenv("SHEET_URL")

async def check_jina_limits(session, api_key):
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
            
    if current_key and current_key != sheet_key:
        sheets.set_jina_api_key(current_key)
    if current_key and current_key != env_key:
        set_key(ENV_FILE, "JINA_API_KEY", current_key)
        
    return current_key

async def interactive_targeting(sheets: SheetsManager):
    """Prompts the user for industry and target amount in the terminal."""
    sheet_industry, sheet_amount = sheets.get_settings()
    
    print("\n[?] TARGETING SETUP")
    
    ind_input = input(f"Enter Target Industry [Press Enter for '{sheet_industry}']: ").strip()
    industry = ind_input if ind_input else sheet_industry
    
    amt_input = input(f"Enter Target Amount [Press Enter for '{sheet_amount}']: ").strip()
    if amt_input.isdigit():
        amount = int(amt_input)
    else:
        amount = sheet_amount
        
    return industry, amount

async def process_url(url: str, session: aiohttp.ClientSession, jina_key: str, db_manager: DatabaseManager, batch_results: list):
    """Processes a single URL and appends it to the batch results list."""
    print(f"[Worker] Extracting: {url}")
    json_content = await extract_json(url, session, jina_key)
    
    if json_content:
        # Save to local SQLite Backup
        db_manager.insert_company(url, json_content)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        batch_results.append([timestamp, url, "SUCCESS", json_content, ""])
        print(f"[Worker] SUCCESS -> {url}")

async def main():
    if not SHEET_URL or SHEET_URL == "PASTE_YOUR_SPREADSHEET_URL_HERE":
        print("ERROR: Please paste your Google Sheet URL into the SHEET_URL variable in your .env file!")
        return

    # 1. Initialize local DB & Sheets
    db = DatabaseManager()
    sheets = SheetsManager(CREDENTIALS_PATH, SHEET_URL)
    
    # 3. Interactive CLI Setup
    jina_key = await interactive_setup(sheets)
    industry, target_amount = await interactive_targeting(sheets)
    
    print(f"\n[Targeting] Launching Batch: {target_amount} companies in '{industry}'")
    
    async with aiohttp.ClientSession() as session:
        # 4. Pre-Flight Tracker
        if jina_key:
            await check_jina_limits(session, jina_key)
            
        # 5. Search for domains
        print(f"[Discovery] Searching web for {target_amount} '{industry}' companies...")
        urls = await search_industry_domains(industry, target_amount, session, jina_key)
        
        if not urls:
            print("[!] No URLs found or search failed. Exiting.")
            return
            
        print(f"[Discovery] Found {len(urls)} target URLs! Starting extraction...\n")
        
        # 6. Batch Extraction
        batch_results = []
        semaphore = asyncio.Semaphore(CONCURRENCY)
        
        async def bounded_process(url):
            async with semaphore:
                await process_url(url, session, jina_key, db, batch_results)
                
        tasks = [asyncio.create_task(bounded_process(url)) for url in urls]
        await asyncio.gather(*tasks)
        
        # 7. Push batch to new tab
        if batch_results:
            print(f"\n[Batch Complete] Exporting {len(batch_results)} records to new Google Sheet tab...")
            sheets.create_batch_tab(industry, batch_results)
        else:
            print("\n[Batch Complete] No records were successfully extracted.")

if __name__ == "__main__":
    asyncio.run(main())
