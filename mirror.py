#!/usr/bin/env python3
"""Mirror https://www.nextstoppackersmovers.com into this directory."""

from __future__ import annotations

import re
import ssl
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

BASE = "https://www.nextstoppackersmovers.com/"
OUT = Path(__file__).resolve().parent
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

SKIP_PREFIXES = ("mailto:", "tel:", "javascript:", "whatsapp:", "sms:", "data:")
EXTERNAL_HINTS = (
    "google.com",
    "googleapis.com",
    "gstatic.com",
    "googletagmanager.com",
    "google-analytics.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "threads.com",
    "wa.me",
    "whatsapp.com",
)
SKIP_PATH_PARTS = ("captcha.php",)

ATTR_RE = re.compile(
    r"""(?:href|src|data-src|data-lazy-src|data-bg|data-background|data-background-image|poster|content)\s*=\s*["']([^"']+)["']""",
    re.I,
)
SRCSET_RE = re.compile(r"""srcset\s*=\s*["']([^"']+)["']""", re.I)
CSS_URL_RE = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", re.I)
IMPORT_RE = re.compile(r"""@import\s+(?:url\()?['"]?([^'")\s]+)['"]?\)?""", re.I)
SITEMAP_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)

CTX = ssl.create_default_context()
LOCK = threading.Lock()

SEEDS = [
    BASE,
    urljoin(BASE, "sitemap.xml"),
    urljoin(BASE, "robots.txt"),
    urljoin(BASE, "index.html"),
    urljoin(BASE, "favicon.ico"),
    urljoin(BASE, "images/logo.png"),
    urljoin(BASE, "assets/images/favicon.webp"),
    urljoin(BASE, "assets/images/logo.webp"),
]


def is_internal(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    if not host:
        return True
    host = host.split(":")[0]
    return host in {"nextstoppackersmovers.com", "www.nextstoppackersmovers.com"}


def normalize(raw: str, page_url: str) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return None
    low = raw.lower()
    if low.startswith(SKIP_PREFIXES):
        return None
    absu = urljoin(page_url, raw)
    parsed = urlparse(absu)
    if parsed.scheme not in {"http", "https"}:
        return None
    host = parsed.netloc.lower()
    if any(h in host for h in EXTERNAL_HINTS):
        return None
    if not is_internal(absu):
        return None
    path = unquote(parsed.path or "/")
    if any(part in path.lower() for part in SKIP_PATH_PARTS):
        return None
    # Drop query strings for static files; keep HTML without query.
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def local_path(url: str) -> Path:
    parsed = urlparse(url)
    path = unquote(parsed.path or "/")
    if path.endswith("/") or path == "":
        path = path.rstrip("/") + "/index.html"
        path = path.lstrip("/")
        if path == "index.html" or path == "/index.html":
            return OUT / "index.html"
        return OUT / path
    path = path.lstrip("/")
    return OUT / path


def extract_urls(content: bytes, page_url: str, content_type: str, path: Path) -> set[str]:
    found: set[str] = set()
    text = ""
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        return found

    ctype = (content_type or "").lower()
    suffix = path.suffix.lower()
    is_html = "html" in ctype or suffix in {".html", ".htm", ""}
    is_css = "css" in ctype or suffix == ".css"
    is_xml = "xml" in ctype or suffix == ".xml"
    is_js = "javascript" in ctype or suffix == ".js"

    if is_xml:
        for loc in SITEMAP_LOC_RE.findall(text):
            n = normalize(loc, page_url)
            if n:
                found.add(n)

    if is_html or is_css or is_js or is_xml:
        for match in ATTR_RE.findall(text):
            n = normalize(match, page_url)
            if n:
                found.add(n)
        for srcset in SRCSET_RE.findall(text):
            for part in srcset.split(","):
                token = part.strip().split(" ")[0]
                n = normalize(token, page_url)
                if n:
                    found.add(n)

    if is_css or is_html:
        for match in CSS_URL_RE.findall(text):
            if match.startswith("data:"):
                continue
            n = normalize(match, page_url)
            if n:
                found.add(n)
        for match in IMPORT_RE.findall(text):
            n = normalize(match, page_url)
            if n:
                found.add(n)

    return found


def fetch(url: str) -> tuple[bytes, str, str]:
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "*/*",
            "Referer": BASE,
        },
    )
    with urlopen(req, context=CTX, timeout=40) as resp:
        data = resp.read()
        ctype = resp.headers.get("Content-Type", "")
        final = resp.geturl()
        return data, ctype, final


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pending: set[str] = set()
    seen: set[str] = set()
    saved: list[str] = []
    failed: list[tuple[str, str]] = []

    for seed in SEEDS:
        n = normalize(seed, BASE)
        if n:
            pending.add(n)

    # Seed sitemap pages even if sitemap fetch is slow.
    try:
        data, ctype, final = fetch(urljoin(BASE, "sitemap.xml"))
        dest = local_path(urljoin(BASE, "sitemap.xml"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        saved.append(str(dest.relative_to(OUT)))
        for loc in extract_urls(data, final, ctype, dest):
            pending.add(loc)
    except Exception as exc:
        failed.append(("sitemap.xml", str(exc)))

    workers = 8
    while pending:
        batch = []
        with LOCK:
            while pending and len(batch) < 24:
                url = pending.pop()
                if url in seen:
                    continue
                seen.add(url)
                batch.append(url)
        if not batch:
            break

        def work(url: str) -> tuple[str, set[str], str | None]:
            try:
                data, ctype, final = fetch(url)
            except HTTPError as exc:
                return url, set(), f"HTTP {exc.code}"
            except URLError as exc:
                return url, set(), f"URL {exc.reason}"
            except Exception as exc:
                return url, set(), str(exc)

            dest = local_path(final if is_internal(final) else url)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            rel = str(dest.relative_to(OUT))
            kids = extract_urls(data, final if is_internal(final) else url, ctype, dest)
            return rel, kids, None

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(work, url): url for url in batch}
            for fut in as_completed(futs):
                src = futs[fut]
                rel, kids, err = fut.result()
                if err:
                    failed.append((src, err))
                    print(f"FAIL {src} -> {err}")
                    continue
                saved.append(rel)
                print(f"OK   {rel}")
                for kid in kids:
                    if kid not in seen:
                        pending.add(kid)

    html_pages = sorted(p for p in saved if p.endswith(".html") or p.endswith(".htm"))
    report = OUT / "CLONE_REPORT.txt"
    lines = [
        f"Mirrored {BASE}",
        f"Files saved: {len(saved)}",
        f"HTML pages: {len(html_pages)}",
        f"Failures: {len(failed)}",
        "",
        "== HTML pages ==",
        *html_pages,
        "",
        "== Failures ==",
        *[f"{u} -> {e}" for u, e in failed],
        "",
        "== All files ==",
        *sorted(saved),
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "\n".join(lines[: 20 + len(html_pages)]))
    print(f"\nWrote {report}")


if __name__ == "__main__":
    main()
