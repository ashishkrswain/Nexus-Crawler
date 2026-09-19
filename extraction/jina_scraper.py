import aiohttp
import asyncio

async def extract_json(domain: str, session: aiohttp.ClientSession, jina_api_key: str = None) -> str:
    """
    Calls Jina AI's Reader API, requesting JSON output format.
    """
    jina_url = f"https://r.jina.ai/https://{domain}"
    
    headers = {
        "Accept": "application/json"
    }
    if jina_api_key:
        headers["Authorization"] = f"Bearer {jina_api_key}"
        
    try:
        async with session.get(jina_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                # We return the raw text (which is a JSON string from Jina)
                content = await response.text()
                return content
            else:
                return None
    except Exception as e:
        return None
