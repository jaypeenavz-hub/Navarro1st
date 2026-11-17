"""Download sample product photography into static/img/products/.

Photos come from Pexels (free to use, no attribution required) and are matched to
each sample product by keyword. Run once after installing dependencies:

    .venv/Scripts/python.exe tools/fetch_images.py

The script talks to the network through `curl` because Pexels rate-limits plain
Python HTTP clients. Use --force to re-download, or --only <slug> for one product.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.seed import PRODUCTS  # noqa: E402

OUT_DIR = os.path.join(ROOT, "static", "img", "products")
CURL = shutil.which("curl") or "curl.exe"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# Curated, generic search terms give much better Pexels matches than brand names.
QUERIES = {
    "lenovo-ideapad-slim-3": "laptop computer",
    "asus-vivobook-15": "laptop notebook",
    "macbook-air-13-m2": "macbook laptop",
    "acer-aspire-go-15": "laptop student",
    "samsung-galaxy-tab-s6-lite": "tablet on desk",
    "dell-p2422h-24-monitor": "computer monitor",
    "asus-tuf-vg249q1a": "desktop monitor screen",
    "lg-27mp400-monitor": "monitor desk",
    "xiaomi-a27i-monitor": "computer screen",
    "arzopa-15-6-portable-monitor": "laptop and monitor",
    "keychron-k2-v2": "mechanical keyboard",
    "royal-kludge-rk61": "keyboard rgb",
    "logitech-mx-keys-s": "computer keyboard desk",
    "logitech-mx-master-3s": "computer mouse",
    "razer-deathadder-v2-x": "gaming mouse",
    "sony-wh-ch720n": "headphones",
    "hyperx-cloud-iii": "gaming headset",
    "airpods-pro-2-usbc": "wireless earbuds",
    "jbl-go-4": "bluetooth speaker",
    "moondrop-chu-ii": "earphones",
    "samsung-t7-1tb-ssd": "external ssd",
    "wd-elements-2tb": "external hard drive",
    "sandisk-ultra-128gb-microsd": "memory card",
    "kingston-dt-exodia-128gb": "usb flash drive",
    "crucial-bx500-480gb": "solid state drive",
    "ugreen-6-in-1-usb-c-hub": "usb hub",
    "anker-737-power-bank": "power bank",
    "baseus-gan5-pro-65w": "usb charger",
    "ugreen-100w-usb-c-cable": "usb cable",
    "tp-link-ue300-adapter": "ethernet network cable",
    "raspberry-pi-5-8gb": "raspberry pi",
    "arduino-uno-r3-starter-kit": "arduino board wires",
    "esp32-devkit-v1-3-pack": "circuit board microcontroller",
    "raspberry-pi-pico-w-2-pack": "electronics breadboard",
}

IMG_TAG = re.compile(r"<img[^>]+src=\"(https://images\.pexels\.com/photos/[^\"]+)\"[^>]*>", re.I)
ALT_ATTR = re.compile(r'alt="([^"]*)"', re.I)
STOPWORDS = {"the", "and", "for", "with", "of", "a", "to", "in", "on"}


def curl_bytes(url, timeout=45):
    """Return (body, http_status) using the system curl."""
    result = subprocess.run(
        [CURL, "-sL", "--compressed", "--max-time", str(timeout),
         "-H", f"User-Agent: {UA}",
         "-H", "Accept-Language: en-US,en;q=0.9",
         "-H", "Accept: text/html,application/xhtml+xml,*/*;q=0.8",
         "-w", "\n%{http_code}", url],
        capture_output=True,
    )
    body, _, status = result.stdout.rpartition(b"\n")
    try:
        code = int(status.strip() or 0)
    except ValueError:
        code = 0
    return body, code


def curl_to_file(url, destination, timeout=60):
    result = subprocess.run(
        [CURL, "-sL", "--compressed", "--max-time", str(timeout),
         "-H", f"User-Agent: {UA}", "-o", destination, url],
        capture_output=True,
    )
    return result.returncode == 0


def fetch_html(url, attempts=3):
    for attempt in range(attempts):
        body, status = curl_bytes(url)
        if status == 200 and body:
            return body.decode("utf-8", "ignore")
        time.sleep(3 + attempt * 3)
    return ""


def search_photos(keyword):
    """Return [(image_url, alt_text)] from a Pexels keyword search."""
    slug = keyword.replace(" ", "-")
    html = fetch_html(f"https://www.pexels.com/search/{slug}/")
    seen, results = set(), []
    for match in IMG_TAG.finditer(html):
        url = match.group(1).split("?")[0]
        if url in seen:
            continue
        seen.add(url)
        alt = ALT_ATTR.search(match.group(0))
        results.append((url, alt.group(1) if alt else ""))
    return results


def best_match(candidates, keyword):
    words = [w for w in re.split(r"[^a-z0-9]+", keyword.lower()) if w and w not in STOPWORDS]
    best, best_score = None, -1
    for url, alt in candidates:
        text = alt.lower()
        score = sum(1 for word in words if word in text)
        if score > best_score:
            best, best_score = (url, alt), score
    return best


def looks_like_image(path):
    try:
        with open(path, "rb") as handle:
            header = handle.read(12)
        return header.startswith(b"\xff\xd8") or header.startswith(b"\x89PNG") or b"WEBP" in header
    except OSError:
        return False


def main():
    parser = argparse.ArgumentParser(description="Download product photos for the catalogue")
    parser.add_argument("--force", action="store_true", help="re-download existing images")
    parser.add_argument("--only", help="only process one product slug")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    downloaded = skipped = failed = 0
    failures = []

    for name, slug, _category, _price, _stock, _rating, _count, _badge, seed_keyword, _desc in PRODUCTS:
        if args.only and slug != args.only:
            continue
        destination = os.path.join(OUT_DIR, f"{slug}.jpg")
        if os.path.exists(destination) and not args.force:
            skipped += 1
            continue

        keyword = QUERIES.get(slug, seed_keyword)
        candidates = search_photos(keyword)
        if not candidates:
            failed += 1
            failures.append((slug, "no search results (rate limited?)"))
            print(f"[fail] {slug:42} no results for “{keyword}”")
            time.sleep(5)
            continue

        url, alt = best_match(candidates, keyword)
        curl_to_file(f"{url}?auto=compress&cs=tinysrgb&w=1000", destination)
        if not looks_like_image(destination) or os.path.getsize(destination) < 6000:
            failed += 1
            failures.append((slug, "download rejected"))
            print(f"[fail] {slug:42} image download rejected")
            if os.path.exists(destination):
                os.remove(destination)
            continue

        downloaded += 1
        print(f"[ok]   {slug:42} {os.path.getsize(destination) // 1024:>4} KB  alt={alt[:44]!r}")
        time.sleep(1.2)

    print(f"\nDownloaded {downloaded}, skipped {skipped}, failed {failed}")
    for slug, error in failures:
        print(f"  - {slug}: {error}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
