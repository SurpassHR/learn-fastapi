import browser_cookie3 as bc3
from config import getConfig, setConfig

def get_secure_code():
    cookie_file = getConfig("chrome-cookie-file")
    jar = bc3.chrome(cookie_file=cookie_file, domain_name=".google.com")
    cookies = {}
    cookies[bc3.chrome.__name__] = {
        cookie.name: cookie.value for cookie in jar
    }
    for item in cookies.items():
        browser, cookies = item
        # print(f"{browser}: {cookies}")
        # print(cookies.get("__Secure-1PSID"))
        # print(cookies.get("__Secure-1PSIDTS"))

    return cookies.get("__Secure-1PSID"), cookies.get("__Secure-1PSIDTS")