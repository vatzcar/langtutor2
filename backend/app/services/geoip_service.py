import httpx

COUNTRY_TO_LOCALE: dict[str, str] = {
    "US": "en-US",
    "GB": "en-GB",
    "AU": "en-AU",
    "CA": "en-CA",
    "IN": "en-IN",
    "DE": "de-DE",
    "AT": "de-AT",
    "CH": "de-CH",
    "FR": "fr-FR",
    "BE": "fr-BE",
    "ES": "es-ES",
    "MX": "es-MX",
    "AR": "es-AR",
    "CO": "es-CO",
    "CL": "es-CL",
    "PE": "es-PE",
    "PT": "pt-PT",
    "BR": "pt-BR",
    "IT": "it-IT",
    "NL": "nl-NL",
    "RU": "ru-RU",
    "JP": "ja-JP",
    "KR": "ko-KR",
    "CN": "zh-CN",
    "TW": "zh-TW",
    "HK": "zh-HK",
    "SA": "ar-SA",
    "AE": "ar-AE",
    "EG": "ar-EG",
    "TR": "tr-TR",
    "PL": "pl-PL",
    "SE": "sv-SE",
    "NO": "nb-NO",
    "DK": "da-DK",
    "FI": "fi-FI",
    "TH": "th-TH",
    "VN": "vi-VN",
    "ID": "id-ID",
    "MY": "ms-MY",
    "PH": "fil-PH",
    "UA": "uk-UA",
    "CZ": "cs-CZ",
    "RO": "ro-RO",
    "HU": "hu-HU",
    "GR": "el-GR",
    "IL": "he-IL",
    "NG": "en-NG",
    "KE": "en-KE",
    "ZA": "en-ZA",
}


async def detect_locale_from_ip(ip: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "country,countryCode,city"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "country": data.get("country", ""),
                    "country_code": data.get("countryCode", ""),
                    "city": data.get("city", ""),
                }
    except Exception:
        pass

    return {"country": "", "country_code": "", "city": ""}


def build_locale(phone_language: str, country_code: str) -> str:
    # Try exact match: phone_language + country_code (e.g., "en-US")
    candidate = f"{phone_language}-{country_code}"
    if candidate in COUNTRY_TO_LOCALE.values():
        return candidate

    # Try country-based lookup
    if country_code in COUNTRY_TO_LOCALE:
        locale = COUNTRY_TO_LOCALE[country_code]
        # If the phone language matches the locale language prefix, use it
        if locale.startswith(phone_language):
            return locale

    # Fallback: phone_language + country_code
    return f"{phone_language}-{country_code}"
