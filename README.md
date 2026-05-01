# Pixabay Bulk Downloader

A simple script that downloads CC0 images from Pixabay in bulk, organised into subfolders by keyword category. Images are automatically compressed to a target size range using Pillow (useful when you need consistently sized assets without manually touching every file).

## What it does

- Searches Pixabay for a list of keywords you define
- Saves results into subfolders per category
- Compresses anything over 3 MB down to fit between 1–3 MB
- Skips files that already exist, so re-runs are safe
- Optionally downloads from a direct URL list too

## Requirements

Python 3.10+ and two packages:

```
pip install requests pillow
```

## Setup

1. Get a free API key from https://pixabay.com/api/docs/
2. Open `pixabay_bulk_downloader.py` and paste your key into:
   ```python
   PIXABAY_API_KEY = "your_key_here"
   ```
3. Edit `KEYWORD_CATEGORIES` to match what you actually want to download
4. Run it:
   ```
   python pixabay_bulk_downloader.py
   ```

## Configuration

All the main settings are at the top of the file:

| Variable | Default | What it does |
|---|---|---|
| `OUTPUT_DIR` | `downloaded_images` | Root folder for all downloads |
| `IMAGES_PER_KEYWORD` | `10` | How many images per search term |
| `MIN_SIZE_BYTES` | 1 MB | Floor for compression target |
| `MAX_SIZE_BYTES` | 3 MB | Ceiling — anything above this gets compressed |
| `DELAY_BETWEEN_REQUESTS` | `0.5s` | Pause between downloads |

## Compression behaviour

- **Already 1–3 MB** → saved as-is, no quality loss
- **Under 1 MB** → saved as-is (can't add detail that isn't there)
- **Over 3 MB** → Pillow re-encodes as JPEG, stepping quality down from 95 until it fits

## Output structure

```
downloaded_images/
├── profiles/
├── listings/
│   ├── food_and_groceries/
│   ├── clothing/
│   └── ...
└── from_urls/
```

## Notes

- All Pixabay images are **CC0** — no attribution required, free to use commercially
