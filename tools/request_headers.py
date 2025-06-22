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
    'Cookie': 'datadome=g~uN9jOTPpDWDkOPRSJaM5Y95oGAT3~J9eFkeZW4kB5kD0KN1PP_zQkcpT68Ab_0y4iby8FBJXMTgu15jsg045ybpZHec972SoQ8_T8OJBqQL9HK3LJGY9gA9eKUgyhv'
}

# Usage example:
# import requests
# response = requests.get('https://www.idealista.com/venta-viviendas/madrid-madrid/', headers=headers)
