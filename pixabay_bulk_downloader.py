"""
pixabay_bulk_downloader.py
--------------------------
Bulk-download CC0 images from Pixabay by keyword, organised into subfolders.
Downloaded images are automatically compressed to stay within a target size
range using Pillow — handy if you're feeding them into an app or CDN with
size limits.

Requirements:
    pip install requests pillow

Quick start:
    1. Grab a free API key at https://pixabay.com/api/docs/
    2. Paste it into PIXABAY_API_KEY below
    3. Edit KEYWORD_CATEGORIES to match what you actually need
    4. Run: python pixabay_bulk_downloader.py
"""

import io
import os
import time
import requests
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image


# ── Settings ──────────────────────────────────────────────────────────────────

OUTPUT_DIR = "downloaded_images"   # Where everything gets saved
IMAGES_PER_KEYWORD = 10            # Max images per search term
DELAY_BETWEEN_REQUESTS = 0.5       # Seconds to wait between downloads

# Size limits for saved images
MIN_SIZE_BYTES = 1 * 1024 * 1024   # 1 MB
MAX_SIZE_BYTES = 3 * 1024 * 1024   # 3 MB

# Pillow JPEG compression — starts high and steps down until the file fits
INITIAL_QUALITY = 95
MIN_QUALITY = 10
QUALITY_STEP = 5

# Paste your free Pixabay API key here (https://pixabay.com/api/docs/)
PIXABAY_API_KEY = ""

PIXABAY_URL = "https://pixabay.com/api/"


# ── Keyword categories ─────────────────────────────────────────────────────────
# Each key becomes a subfolder. Add, remove, or rename these freely.

KEYWORD_CATEGORIES = {
    "profiles": [
        "african woman portrait",
        "african man portrait",
        "young woman smiling",
        "young man smiling",
        "person face portrait",
    ],
    "listings/food_and_groceries": [
        "bread loaf",
        "eggs food",
        "cooking oil bottle",
        "maize meal bag",
        "soft drink can",
        "snacks chips",
        "sugar bag",
    ],
    "listings/clothing": [
        "tshirt clothing",
        "sneakers shoes",
        "jacket clothing",
        "dress clothing",
        "hat cap fashion",
    ],
    "listings/electronics": [
        "smartphone mobile phone",
        "earphones headphones",
        "laptop computer",
        "power bank charger",
        "electric kettle",
    ],
    "listings/household": [
        "cooking pot kitchen",
        "broom cleaning",
        "bucket plastic",
        "blanket bedding",
        "candle household",
    ],
    "listings/health_and_beauty": [
        "soap bar skincare",
        "hair products",
        "toothbrush dental",
        "lotion cream beauty",
    ],
    "listings/services": [
        "repair tools handyman",
        "delivery package courier",
        "tutoring education",
        "hair braiding salon",
    ],
}

# Optional: drop direct image URLs here and they'll be saved to from_urls/
DIRECT_URLS = [
    # "https://example.com/some-image.jpg",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_folder(path: str) -> Path:
    folder = Path(path)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def sanitize_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


def compress_image(image_bytes: bytes, target_path: Path) -> tuple[bool, int, int]:
    """
    Save image_bytes to target_path, compressing if needed to fit within
    MIN_SIZE_BYTES–MAX_SIZE_BYTES.

    - Already in range → saved as-is (no quality loss)
    - Under 1 MB → saved as-is (can't add detail that isn't there)
    - Over 3 MB → re-encoded as JPEG, quality stepped down until it fits

    Returns (success, original_kb, final_kb).
    """
    original_size = len(image_bytes)
    original_kb = original_size // 1024

    # Fits already — just write it
    if MIN_SIZE_BYTES <= original_size <= MAX_SIZE_BYTES:
        target_path.write_bytes(image_bytes)
        return True, original_kb, original_kb

    # Too small to inflate meaningfully
    if original_size < MIN_SIZE_BYTES:
        target_path.write_bytes(image_bytes)
        return True, original_kb, original_kb

    # Too large — compress with Pillow
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # JPEG doesn't support transparency, so convert if needed
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        quality = INITIAL_QUALITY
        best_buffer = None

        while quality >= MIN_QUALITY:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            size = buf.tell()

            if size <= MAX_SIZE_BYTES:
                best_buffer = buf
                if size >= MIN_SIZE_BYTES:
                    break  # Sweet spot found
            quality -= QUALITY_STEP

        # If still over the limit at MIN_QUALITY, use that anyway
        if best_buffer is None:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=MIN_QUALITY, optimize=True)
            best_buffer = buf

        best_buffer.seek(0)
        compressed = best_buffer.read()
        target_path.write_bytes(compressed)
        return True, original_kb, len(compressed) // 1024

    except Exception as e:
        print(f"    ✗ Compression error: {e} — saving original")
        target_path.write_bytes(image_bytes)
        return True, original_kb, original_kb


def download_file(url: str, dest_path: Path) -> bool:
    """Fetch url, compress, write to dest_path. Returns True on success."""
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "pixabay-bulk-downloader/1.0"})
        resp.raise_for_status()

        success, orig_kb, final_kb = compress_image(resp.content, dest_path)
        if success and orig_kb != final_kb:
            print(f"      compressed {orig_kb} KB → {final_kb} KB")
        return success

    except Exception as e:
        print(f"    ✗ Download failed: {url}\n      {e}")
        return False


def pixabay_search(keyword: str, count: int = 10) -> list[str]:
    """Return up to `count` large image URLs from Pixabay for the given keyword."""
    params = {
        "key": PIXABAY_API_KEY,
        "q": keyword,
        "image_type": "photo",
        "safesearch": "true",
        "per_page": min(count, 20),
        "page": 1,
    }

    try:
        resp = requests.get(PIXABAY_URL, params=params, timeout=10,
                            headers={"User-Agent": "pixabay-bulk-downloader/1.0"})

        if resp.status_code == 400:
            print("  ✗ Pixabay returned 400 — double-check your API key.")
            return []

        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        return [h["largeImageURL"] for h in hits][:count]

    except Exception as e:
        print(f"  ✗ Search failed for '{keyword}': {e}")
        return []


# ── Main routines ─────────────────────────────────────────────────────────────

def download_from_keywords():
    print("\n" + "=" * 55)
    print("  KEYWORD DOWNLOADS")
    print("=" * 55)

    total = 0

    for category, keywords in KEYWORD_CATEGORIES.items():
        folder = make_folder(os.path.join(OUTPUT_DIR, category))
        print(f"\n📁 {category}")

        for keyword in keywords:
            print(f"  🔍 '{keyword}'")
            urls = pixabay_search(keyword, count=IMAGES_PER_KEYWORD)

            if not urls:
                print("     No results.")
                continue

            slug = sanitize_filename(keyword.replace(" ", "_"))

            for i, url in enumerate(urls, 1):
                filename = f"{slug}_{i:02d}.jpg"
                dest = folder / filename

                if dest.exists():
                    print(f"    – already exists: {filename}")
                    continue

                print(f"    ↓ {filename}")
                if download_file(url, dest):
                    print(f"    ✓ {dest.stat().st_size // 1024} KB")
                    total += 1

                time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n✅ Done — {total} new images saved.")
    return total


def download_from_url_list():
    if not DIRECT_URLS:
        print("\nNo direct URLs listed — skipping.")
        return 0

    print("\n" + "=" * 55)
    print("  DIRECT URL DOWNLOADS")
    print("=" * 55)

    folder = make_folder(os.path.join(OUTPUT_DIR, "from_urls"))
    downloaded = 0

    for i, url in enumerate(DIRECT_URLS, 1):
        base = Path(urlparse(url).path).stem or f"image_{i:03d}"
        filename = sanitize_filename(base) + ".jpg"
        dest = folder / filename

        if dest.exists():
            print(f"  – already exists: {filename}")
            continue

        print(f"  [{i}/{len(DIRECT_URLS)}] {url}")
        if download_file(url, dest):
            print(f"  ✓ {filename}  ({dest.stat().st_size // 1024} KB)")
            downloaded += 1

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n✅ Done — {downloaded} new images saved.")
    return downloaded


def print_summary():
    print("\n" + "=" * 55)
    print("  SUMMARY")
    print("=" * 55)

    total = 0
    for root, dirs, files in os.walk(OUTPUT_DIR):
        dirs.sort()
        imgs = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        if imgs:
            rel = os.path.relpath(root, OUTPUT_DIR)
            print(f"  📁 {rel}: {len(imgs)} images")
            total += len(imgs)

    print(f"\n  Total on disk : {total}")
    print(f"  Location      : {os.path.abspath(OUTPUT_DIR)}/")


if __name__ == "__main__":
    print("Pixabay Bulk Downloader")
    print(f"Output : {os.path.abspath(OUTPUT_DIR)}")
    print(f"Target : {MIN_SIZE_BYTES // (1024*1024)}–{MAX_SIZE_BYTES // (1024*1024)} MB per image")

    if not PIXABAY_API_KEY:
        print("\n⚠️  PIXABAY_API_KEY is empty.")
        print("   Get a free key at https://pixabay.com/api/docs/ and add it to the script.\n")

    download_from_keywords()
    download_from_url_list()
    print_summary()
