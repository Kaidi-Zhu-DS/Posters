"""Deterministic collection of Chinese Posters catalogue metadata. No LLM."""
import argparse
import calendar
import csv
import hashlib
import html
import io
import json
import platform
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from importlib.metadata import version
from lxml import html as LH
from PIL import Image

BASE = "https://chineseposters.net"
FIELDS = {
    "title_zh": "field-titlechinese", "title_pinyin": "field-titlepinyin",
    "date_raw": "field-datetxt", "designers_raw": "field-taxonomy-artists",
    "publisher_raw": "field-publisher", "size_raw": "field-size",
    "call_number": "field-call-nr-", "collection": "field-collection",
    "notes_raw": "body", "themes_raw": "field-see-also-these-pages-",
    "catalog_raw": "field-iisg-identifier-2",
}

def now():
    return datetime.now(timezone.utc).isoformat()

def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def text(element):
    return " ".join(element.text_content().split())

def field(scope, name):
    elements = scope.xpath('.//*[contains(concat(" ",normalize-space(@class)," "), $class)]',
                           **{"class": " field--name-" + name + " "})
    if not elements:
        return "", []
    element = elements[0]
    items = element.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," field__item ")]') or [element]
    links = [{"name": text(a), "url": urllib.parse.urljoin(BASE, a.get("href"))}
             for a in element.xpath('.//a[@href]')]
    return " | ".join(text(item) for item in items), links

def dates(raw):
    """Auxiliary parsing only. Preserve raw dates and flag ambiguity."""
    years = re.findall(r"\b(?:18|19|20)\d{2}\b", raw)
    begin = end = month = None
    precision = "unknown"
    uncertain = bool(re.search(r"ca\.|\?|early|mid|late|approx|\d{4}s", raw, re.I))
    if re.search(r"original|reprint|edition", raw, re.I):
        precision = "complex"
    elif len(years) > 1:
        precision = "range"
        begin, end = int(years[0]), int(years[-1])
    elif len(years) == 1:
        begin = end = int(years[0])
        precision = "year"
        if re.search(r"\d{4}s", raw):
            precision, end = "decade", begin + 9
        else:
            for number, name in enumerate(calendar.month_name):
                if number and re.search(r"\b" + name + r"\b", raw, re.I):
                    month, precision = number, "month"
                    break
    review = uncertain or precision in {"complex", "unknown", "range", "decade"}
    return dict(year_start=begin, year_end=end, month=month,
                date_precision=precision, date_uncertain=uncertain,
                date_normalization_status="manual_review" if review else "parsed")

def parse_poster(data, url):
    doc = LH.fromstring(data.decode("utf-8"))
    articles = doc.xpath('//article[contains(@class,"node--type-posters")]')
    if not articles:
        raise ValueError("Poster article missing; inspect saved HTML and update selectors")
    scope = articles[0]
    headings = doc.xpath('//h1[contains(@class,"page-title")]')
    row = dict(poster_id=url.rstrip('/').rsplit('/', 1)[-1], source_url=url,
               title_en=text(headings[0]) if headings else "", html_sha256=digest(data))
    for key, name in FIELDS.items():
        value, links = field(scope, name)
        row[key] = value
        if key == "designers_raw": row["designers"] = links
        if key == "themes_raw": row["themes_site"] = links
        if key == "catalog_raw": row["catalog_url"] = links[0]["url"] if links else ""
    row["tags_site"] = [{"name": text(a), "url": urllib.parse.urljoin(BASE, a.get("href"))}
                        for a in doc.xpath('//section[contains(@id,"tag-block")]//a[starts-with(@href,"/tags/")]')]
    row.update(dates(row["date_raw"]))
    row["missing_fields"] = [key for key in FIELDS if not row[key]]
    row["images"] = [{"image_url": urllib.parse.urljoin(url, img.get("src")),
                      "image_alt": img.get("alt", "")}
                     for img in scope.xpath('.//*[contains(@class,"field--name-field-image")]//img[@src]')]
    return row

class Fetcher:
    def __init__(self, root, delay, agent, offline=False):
        self.root, self.delay, self.agent, self.offline = root, delay, agent, offline
        self.robot = None
        self.last = 0

    def get(self, url, relative):
        if urllib.parse.urlparse(url).hostname != "chineseposters.net":
            raise ValueError("Off-site URL excluded: " + url)
        if self.robot is not None and not self.robot.can_fetch(self.agent, url):
            raise ValueError("robots.txt disallows: " + url)
        path = self.root / relative
        if path.exists() and path.stat().st_size:
            return path.read_bytes()
        if self.offline:
            raise FileNotFoundError("Offline cache miss: " + str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(4):
            time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            status = "error"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": self.agent})
                with urllib.request.urlopen(req, timeout=60) as response:
                    if urllib.parse.urlparse(response.url).hostname != "chineseposters.net":
                        raise ValueError("Off-site redirect excluded")
                    data = response.read()
                    status = response.status
                if not data: raise ValueError("Empty response")
                temp = path.with_suffix(path.suffix + ".tmp")
                temp.write_bytes(data)
                temp.replace(path)
                return data
            except urllib.error.HTTPError as error:
                status = error.code
                if error.code in {401, 403}: raise
                if attempt == 3 or error.code not in {429, 500, 502, 503, 504}: raise
                retry = error.headers.get("Retry-After", "")
                time.sleep(max(60 if error.code == 429 else 5 * 2**attempt,
                               int(retry) if retry.isdigit() else 0))
            except (urllib.error.URLError, TimeoutError):
                if attempt == 3: raise
                time.sleep(5 * 2**attempt)
            finally:
                with (self.root / "audit/requests.jsonl").open("a", encoding="utf-8") as log:
                    log.write(json.dumps(dict(url=url, timestamp=now(), status=status, attempt=attempt+1)) + "\n")

def collect(args):
    root = Path(args.out).resolve()
    for folder in ["audit", "raw_html", "records", "images"]:
        (root / folder).mkdir(parents=True, exist_ok=True)
    fetch = Fetcher(root, args.delay, args.user_agent, args.offline)
    robots = fetch.get(BASE + "/robots.txt", "audit/robots.txt")
    fetch.robot = urllib.robotparser.RobotFileParser()
    fetch.robot.parse(robots.decode("utf-8").splitlines())
    fetch.delay = max(fetch.delay, fetch.robot.crawl_delay(args.user_agent) or 0)
    fetch.get(BASE + "/about/faqs", "audit/faqs.html")
    urls, pages, seen_pages = [], [], set()
    url = BASE + "/posters/posters?page=0"
    while url:
        if url in seen_pages: raise ValueError("Pagination loop")
        seen_pages.add(url)
        page = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("page", ["0"])[0]
        data = fetch.get(url, f"raw_html/catalog_{page}.html")
        doc = LH.fromstring(data.decode("utf-8"))
        links = doc.xpath('//div[contains(@class,"view-content")]//a[starts-with(@href,"/posters/")]/@href')
        links = [urllib.parse.urljoin(BASE, u) for u in links if urllib.parse.urlparse(u).path.rstrip('/') != '/posters/posters']
        if not links: raise ValueError("Empty catalogue: inspect HTML")
        urls = list(dict.fromkeys(urls + links))
        pages.append(dict(url=url, sha256=digest(data), links=len(set(links))))
        if args.limit and len(urls) >= args.limit: break
        next_links = doc.xpath('//a[@rel="next"]/@href')
        url = urllib.parse.urljoin(url, next_links[0]) if next_links else None
    save_json(root / "audit/catalog_manifest.json", dict(pages=pages, urls=urls,
              traversal_complete=not bool(url), scope="catalogue-reachable poster detail pages"))
    selected = urls[:args.limit] if args.limit else urls
    rows = []
    for number, url in enumerate(selected, 1):
        pid = url.rstrip('/').rsplit('/', 1)[-1]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", pid): raise ValueError("Unsafe poster ID")
        checkpoint = root / "records" / (pid + ".json")
        row = None
        if checkpoint.exists():
            old = json.loads(checkpoint.read_text(encoding="utf-8"))
            if old.get("fetch_status") == "ok" and (not args.images or
               (old.get("download_images") and all((root / i["image_path"]).exists() for i in old["images"]))):
                row = old
        if row is None:
            try:
                data = fetch.get(url, f"raw_html/{pid}.html")
                row = parse_poster(data, url)
                if args.images:
                    if not row["images"]: raise ValueError("No display image found")
                    for index, image in enumerate(row["images"]):
                        ext = Path(urllib.parse.urlparse(image["image_url"]).path).suffix or ".jpg"
                        relative = f"images/{pid}" + (f"_{index+1}" if index else "") + ext
                        content = fetch.get(image["image_url"], relative)
                        with Image.open(io.BytesIO(content)) as im: im.verify()
                        with Image.open(io.BytesIO(content)) as im: width, height = im.size
                        image.update(image_path=relative, image_width=width, image_height=height,
                                     image_bytes=len(content), image_sha256=digest(content))
                row.update(fetch_status="ok", crawl_timestamp=now(), download_images=args.images)
            except Exception as error:
                row = dict(poster_id=pid, source_url=url, fetch_status="error", error=str(error), crawl_timestamp=now())
                if isinstance(error, urllib.error.HTTPError) and error.code in {401, 403, 429}:
                    save_json(checkpoint, row)
                    raise
            save_json(checkpoint, row)
        rows.append(row)
        print(f"{number}/{len(selected)} {pid}: {row['fetch_status']}", flush=True)
    assert len({r['poster_id'] for r in rows}) == len(rows)
    for row in rows:
        for image in row.get("images", []):
            if "image_path" in image:
                assert digest((root / image["image_path"]).read_bytes()) == image["image_sha256"]
    save_json(root / "metadata.json", rows)
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with (root / "metadata.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k,v in row.items()})
    with (root / "metadata.jsonl").open("w", encoding="utf-8") as f:
        for row in rows: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (root / "metadata.csv").open(encoding="utf-8-sig", newline="") as f:
        assert len(list(csv.DictReader(f))) == len(rows)
    errors = [r for r in rows if r["fetch_status"] != "ok"]
    save_json(root / "audit/errors.json", errors)
    save_json(root / "report.json", dict(processed=len(rows), successful=len(rows)-len(errors),
              failed=len(errors), completed_at=now(), limit=args.limit, download_images=args.images,
              python=platform.python_version(), packages={p:version(p) for p in ['lxml','Pillow']},
              script_sha256=digest(Path(__file__).read_bytes()), effective_delay=fetch.delay,
              missing_counts={k:sum(not r.get(k) for r in rows if r['fetch_status']=='ok') for k in FIELDS}))
    cards = []
    for row in rows:
        esc = lambda v: html.escape(str(v or ""))
        image = next((i for i in row.get('images',[]) if i.get('image_path')), None)
        picture = '<img loading="lazy" src="'+esc(image['image_path'])+'">' if image else ''
        cards.append('<article>'+picture+'<h3>'+esc(row.get('title_zh') or row.get('title_en') or row['poster_id'])+
                     '</h3><p>'+esc(row.get('date_raw'))+'</p><p>'+esc(row.get('designers_raw'))+
                     '</p><a href="'+esc(row['source_url'])+'">Source</a></article>')
    (root / 'preview.html').write_text('<!doctype html><meta charset="utf-8"><style>body{font:16px system-ui}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:20px}img{max-width:100%;height:220px;object-fit:contain}</style><h1>Chinese Posters collection</h1><main>'+''.join(cards)+'</main>', encoding='utf-8')
    (root / 'README.txt').write_text('Website catalogue snapshot, not a random sample of historical poster production.\nMetadata and site themes/tags are extracted without LLM. Dates are preliminary; date_raw remains authoritative.\nSee report.json and audit/errors.json before analysis. Display images are optional; no external high-resolution scans are fetched.\nCached files are reused on rerun. Use a new output directory for a fresh snapshot. Consult audit/faqs.html for image reuse conditions.\n', encoding='utf-8')
    if args.zip:
        destination = root.with_name(root.name + '.zip')
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for path in sorted(root.rglob('*')):
                if path.is_file() and path.suffix != '.tmp': archive.write(path, path.relative_to(root.parent))
        with zipfile.ZipFile(destination) as archive: assert archive.testzip() is None
        print('Archive:', destination)
    print('Errors:', len(errors), 'See audit/errors.json')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--limit', type=int, default=100, help='0 means all catalogue entries')
    parser.add_argument('--images', action='store_true')
    parser.add_argument('--zip', action='store_true')
    parser.add_argument('--delay', type=float, default=2.0)
    parser.add_argument('--offline', action='store_true', help='Use existing cache only')
    parser.add_argument('--user-agent', default='ChinesePostersResearch/1.0 (academic metadata collection)')
    args = parser.parse_args()
    if args.limit < 0 or args.delay < 0: parser.error('limit and delay must be nonnegative')
    collect(args)
