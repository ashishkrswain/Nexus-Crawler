import aiohttp
import asyncio

async def extract_markdown(domain: str, session: aiohttp.ClientSession, jina_api_key: str = None) -> str:
    """
    Calls Jina AI's Reader API to extract markdown from a domain.
    """
    jina_url = f"https://r.jina.ai/https://{domain}"
    
    headers = {}
    if jina_api_key:
        headers["Authorization"] = f"Bearer {jina_api_key}"
        
    try:
        async with session.get(jina_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                content = await response.text()
                return content
            else:
                print(f"[Extraction] Failed {domain}: Status {response.status}")
                return None
    except Exception as e:
        # Many new domains won't have a website hosted yet, so this will fail often.
        print(f"[Extraction] Error for {domain}: {str(e)[:50]}")
        return None
