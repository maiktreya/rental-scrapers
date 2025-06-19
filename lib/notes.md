# Fixing and checking scrapper

## Working request using curl-impersonate

```bash
curl_ff117 \
  -H "User-Agent: Mozilla/5.0 ..." \
  -H "Cookie: datadome=1pojXT~HDeACj12~n1naRzaYLrYc_O4icVzt2M6v_tqGQrNozhNTzn9df68HGFjSDP6A~Kq2ZUx3ckB~miYL2ZYwifj9SP7KKTll2O72gRNYaRUii5DJVCewrZt4F2zj" \
  -L "https://www.idealista.com/inmueble/108387485/"

  curl_ff117 \
  -H "User-Agent: Mozilla/5.0 ..." \
  -H "Cookie: datadome=1pojXT~HDeACj12~n1naRzaYLrYc_O4icVzt2M6v_tqGQrNozhNTzn9df68HGFjSDP6A~Kq2ZUx3ckB~miYL2ZYwifj9SP7KKTll2O72gRNYaRUii5DJVCewrZt4F2zj" \
  -L "https://www.idealista.com/inmueble/108387485/"
```

```bash
## get full headers
curl_ff117 -s -D - https://www.idealista.com > headers.txt
```

## Adapted headers working 18 06 2025

```python
# Establish persistent HTTPX session with browser-like headers to avoid blocking
BASE_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US;en;q=0.9",
    "accept-encoding": "gzip, deflate, br",
    "cookie": "datadome=1pojXT~HDeACj12~n1naRzaYLrYc_O4icVzt2M6v_tqGQrNozhNTzn9df68HGFjSDP6A~Kq2ZUx3ckB~miYL2ZYwifj9SP7KKTll2O72gRNYaRUii5DJVCewrZt4F2zj"
}

```

```python
    async with httpx.AsyncClient(
        headers=BASE_HEADERS, follow_redirects=True, timeout=10.0
    ) as session:
        current_url = base_url
```

...

Perfect! You've got a well-structured scraper with solid modularity, so integrating your **DataDome cookie** solution can be done cleanly and with minimal intrusion.

Here’s exactly how to implement it in your setup:

---

## ✅ **Step-by-step Implementation**

### 1. **Update `config.py` to include `DATADOME_COOKIE`**

Add this at the bottom or near your `BASE_HEADERS_STRUCTURE`:

```python
# Optional: Persistent DataDome cookie for bypassing bot protection (expires fast)
DATADOME_COOKIE: str = "datadome=1pojXT~HDeACj12~n1naRzaYLrYc_O4icVzt2M6v_tqGQrNozhNTzn9df68HGFjSDP6A~Kq2ZUx3ckB~miYL2ZYwifj9SP7KKTll2O72gRNYaRUii5DJVCewrZt4F2zj"
```

> 📝 Tip: For longer-term use, you might later write code to refresh this dynamically via Playwright.

---

### 2. **Update `utils.py` or header-building function (if exists)**

If you have a utility like `get_random_headers()`, **inject the `cookie`**:

```python
from .config import BASE_HEADERS_STRUCTURE, USER_AGENTS, DATADOME_COOKIE
import random

def get_random_headers() -> Dict[str, str]:
    headers = BASE_HEADERS_STRUCTURE.copy()
    headers["user-agent"] = random.choice(USER_AGENTS)
    headers["cookie"] = DATADOME_COOKIE
    return headers
```

---

### 3. **Apply headers in `httpx.AsyncClient` globally**

In any script where you create the `AsyncClient`, e.g., in your main runner or orchestrator:

```python
from utils import get_random_headers

async with httpx.AsyncClient(
    headers=get_random_headers(),
    follow_redirects=True,
    timeout=10.0
) as session:
    ...
```

Or if you're already passing headers directly, just update that `headers` dictionary to include `"cookie": DATADOME_COOKIE`.

---

### 4. ✅ You're done!

Every page request will now include your working `datadome` cookie and avoid the 403 block — at least while the cookie is valid for your IP.

---

## 🔄 Optional Future Enhancement

Later, consider:

- Automating cookie capture via **Playwright or Selenium**, storing it to a file or env var.
- Adding **cookie rotation** if you're running many concurrent requests or changing IPs.

---

Would you like me to generate a version of `get_random_headers()` that reads the `datadome` cookie from a `.env` or JSON file for easier updating?
