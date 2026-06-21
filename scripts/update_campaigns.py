#!/usr/bin/env python3
import hashlib
import json
import re
import ssl
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SERVICES = (
    "netflix", "spotify", "amazon prime", "prime video", "disney+",
    "youtube premium", "hbo max", "exxen", "tabii", "gain", "gaın",
    "tod", "bein connect", "beIN connect", "digiturk"
)
OFFER_WORDS = ("kampanya", "indirim", "hediye", "iade", "ücretsiz", "bedava", "%")
DATE_RE = re.compile(r"\b([0-3]?\d)[./-]([01]?\d)[./-](20\d{2})\b")


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_href = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current_href = dict(attrs).get("href")
            self.current_text = []

    def handle_data(self, data):
        if self.current_href is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current_href:
            self.links.append((self.current_href, " ".join(self.current_text).strip()))
            self.current_href = None
            self.current_text = []


def fetch(url):
    request = Request(url, headers={"User-Agent": "AbonelikTakibiCampaignBot/1.0 (+https://github.com/konakdursun-ui/abonelik-takibi-kampanyalar)"})
    context = ssl.create_default_context()
    with urlopen(request, timeout=25, context=context) as response:
        return response.read().decode("utf-8", errors="ignore")


def clean(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()


def meta(html, name):
    patterns = [
        rf'<meta[^>]+(?:name|property)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\']{re.escape(name)}["\']'
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I)
        if match:
            return clean(match.group(1))
    return ""


def extract_end_date(text):
    dates = []
    for day, month, year in DATE_RE.findall(text):
        try:
            dates.append(datetime(int(year), int(month), int(day), tzinfo=timezone.utc))
        except ValueError:
            pass
    return max(dates).date().isoformat() if dates else None


def same_official_domain(url, domain):
    host = (urlparse(url).hostname or "").lower()
    return host == domain or host.endswith("." + domain)


def discover(source):
    listing = fetch(source["url"])
    parser = LinkParser()
    parser.feed(listing)
    candidates = {}
    for href, text in parser.links:
        url = urljoin(source["url"], href)
        combined = (text + " " + url).lower()
        if not same_official_domain(url, source["domain"]):
            continue
        if any(service in combined for service in SERVICES) and any(word in combined for word in OFFER_WORDS):
            candidates[url.split("#")[0]] = text

    results = []
    for url, anchor_text in list(candidates.items())[:30]:
        try:
            html = fetch(url)
        except Exception:
            continue
        title = meta(html, "og:title") or meta(html, "twitter:title") or clean(anchor_text)
        description = meta(html, "og:description") or meta(html, "description")
        searchable = (title + " " + description + " " + clean(anchor_text)).lower()
        matched = [service for service in SERVICES if service in searchable]
        if not matched or not any(word in searchable for word in OFFER_WORDS):
            continue
        visible_summary = (title + " " + description).lower()
        if not any(service in visible_summary for service in matched):
            service_name = {"hbo max": "HBO Max", "amazon prime": "Amazon Prime", "prime video": "Prime Video", "youtube premium": "YouTube Premium"}.get(matched[0], matched[0].title())
            title = f'{source["name"]} {service_name} kampanyası'
            description = "Güncel koşullar için resmî kampanya sayfasını inceleyin."
        end_date = extract_end_date(clean(html[:200000]))
        expired = end_date is not None and end_date < datetime.now(timezone.utc).date().isoformat()
        campaign_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        results.append({
            "id": campaign_id,
            "title": title[:140],
            "provider": source["name"],
            "services": matched,
            "price": "Koşulları incele",
            "description": description[:320],
            "badge": "Resmî kaynak",
            "sourceUrl": url,
            "endDate": end_date,
            "status": "expired" if expired else "active"
        })
    return results


def main():
    sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    current = json.loads((ROOT / "campaigns.json").read_text(encoding="utf-8"))
    campaigns = {
        item["id"]: item for item in current.get("campaigns", [])
        if item["id"].startswith("turkcell-one-") or item.get("curation") == "verified"
    }
    for source in sources:
        try:
            for item in discover(source):
                campaigns[item["id"]] = item
        except Exception as error:
            print(f'{source["name"]}: {error}')
    output = {
        "updatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "campaigns": sorted(campaigns.values(), key=lambda item: (item["status"] != "active", item["provider"], item["title"]))
    }
    (ROOT / "campaigns.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
