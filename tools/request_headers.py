# Complete headers for successful requests
# Copy this dict and use it in your HTTP requests

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'Cookie': 'datadome=fhLlpg68ormOGVjGoJHUygzGovPIPFpi9BAW3loKrlzjHChyDsnspzB3ZmHHturtGoRkRjUFyxOlDfX6pjhRaZznyPjeNbrdgKU4l2eYI5cT8JQpnPzR1t6t9rhz0beV'
}

# Usage example:
# import requests
# response = requests.get('https://www.idealista.com/venta-viviendas/madrid-madrid/', headers=headers)
