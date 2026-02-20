import browser_cookie3 as bc3
from config import getConfig

def get_cookies_from_domain(domain_name: str, cookie_file: str) -> dict[str, str]:
    jar = bc3.chrome(cookie_file=cookie_file, domain_name=domain_name)
    cookies = {}
    cookies[bc3.chrome.__name__] = {
        cookie.name: cookie.value for cookie in jar
    }
    return cookies

def get_session_token(domain_list: list[str]) -> str:
    cookie_file = getConfig("chrome-cookie-file")
    for domain_name in domain_list:
        cookies = get_cookies_from_domain(domain_name, cookie_file)

        if not cookies:
            continue

        for item in cookies.items():
            _, cookies = item
            session_token = cookies.get("__Secure-next-auth.session-token")
            if session_token:
                return session_token

    return ""

def get_secure_code(domain_list: list[str]) -> tuple[str, str]:
    cookie_file = getConfig("chrome-cookie-file")
    for domain_name in domain_list:
        cookies = get_cookies_from_domain(domain_name, cookie_file)

        if not cookies:
            continue
        
        for item in cookies.items():
            _, cookies = item
            sec_1psid = cookies.get("__Secure-1PSID")
            sec_1psidts = cookies.get("__Secure-1PSIDTS")
            if sec_1psid and sec_1psidts:
                return sec_1psid, sec_1psidts

    return "", ""

if __name__ == "__main__":
    domain_list = ["https://labs.google/fx/vi/tools/flow", "labs.google", ".google.com"]
    res = get_session_token(domain_list=domain_list)
    print(res)

    domain_list = [".google.com"]
    res = get_secure_code(domain_list=domain_list)
    print(res)