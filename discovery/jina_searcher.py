import aiohttp

async def search_industry_domains(industry: str, amount: int, session: aiohttp.ClientSession, api_key: str = None) -> list:
    """
    Uses Jina AI Search (s.jina.ai) to find URLs related to the target industry.
    """
    query = f"Latest {industry} startups companies list"
    url = f"https://s.jina.ai/{query}"
    
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                result = await resp.json()
                domains = []
                data = result.get("data", [])
                
                for item in data:
                    domain_url = item.get("url")
                    if domain_url:
                        domains.append(domain_url)
                
                # Deduplicate and limit to requested amount
                unique_domains = list(set(domains))
                return unique_domains[:amount]
            else:
                print(f"[Search Error] Status {resp.status}")
                return []
    except Exception as e:
        print(f"[Search Error] {e}")
        return []
