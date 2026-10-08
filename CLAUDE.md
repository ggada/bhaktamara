# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python script that generates an EPUB 3 e-book (with NCX fallback) of the **Bhaktamara Stotra** (48 sacred verses by Acharya Manatunga). The script scrapes content from jainworld.com, processes Sanskrit text images and illustrations, and creates a reader-friendly EPUB optimized for e-ink devices.

## Environment Setup

This project uses Conda for dependency management:

```bash
# Create and activate the conda environment
conda env create -f environment.yml
conda activate bhaktamara

# Or update an existing environment
conda env update -f environment.yml --prune
```

### Dependencies
- Python 3.11
- requests (HTTP client)
- beautifulsoup4 + lxml (HTML parsing)
- Pillow (image processing)
- ebooklib (EPUB generation)

## Running the Script

```bash
# Generate the EPUB
python create_epub.py
```

**Output:** `Bhaktamara_Stotra.epub` in the current directory

The script will:
1. Fetch 48 shloka pages from https://jainworld.jainworld.com/bhs/
2. Extract Sanskrit text (transliteration + images), English translations, and illustrations
3. Process images (scale to 75%, preserve color)
4. Generate EPUB with title page, contents page, and 48 chapters

## Architecture

### Main Components

**`create_epub.py`** - Single-file script with these logical sections:

1. **Configuration**
   - Book metadata, URL patterns, shloka significance mapping

2. **XHTML Templates**
   - Page bodies only: ebooklib discards the hand-written `<head>`, so `style.css` is attached per page with `add_item(css_item)`
   - E-ink optimized CSS (tight spacing, serif font, monochrome-friendly borders)

3. **HTTP Helpers**
   - `polite_get()`: Retrying HTTP client with exponential backoff
   - `download_image()`: Fetch binary image data

4. **Image Processing**
   - `resize_media_scale()`: Scales images to 75% while preserving color
   - Handles both JPEG and GIF formats

5. **Content Extraction**
   - `extract_shloka_content()`: Core parsing logic
   - Extracts Sanskrit (red text), English (blue text), illustrations, and Sanskrit text images
   - Normalizes `<br />` tags, handles various HTML formats across pages

6. **XHTML Builders**
   - `xhtml_chapter()`: Generates chapter XHTML with significance, images, and text
   - `xhtml_contents()`: Contents page (opening line + significance per shloka), built after fetching
   - `xhtml_title()`: Title page

7. **Main Orchestration**
   - Loops through 48 shlokas
   - Applies manual overrides for shlokas 6 and 7, then `TEXT_FIXES` typo corrections
   - Assembles EPUB with ebooklib

### Key Design Decisions

- **Image handling**: Sanskrit text images (bhsNNt*.gif) are kept in original color and scaled to 75% for e-ink readability
- **Text extraction heuristics**: Uses color-based detection (red=Sanskrit transliteration, blue=English) with multiple fallback strategies for inconsistent source HTML
- **EPUB 3 + NCX**: ebooklib writes EPUB 3 (nav document required); the NCX keeps a TOC for EPUB 2-era readers
- **Manual overrides**: Shlokas 6 and 7 have hardcoded text due to formatting issues on source pages

## Common Tasks

### Testing Locally
```bash
# Run the script
python create_epub.py

# Verify EPUB structure (requires epubcheck)
epubcheck Bhaktamara_Stotra.epub
```

### Modifying Content
- **Change shloka significance**: Edit `SHLOKA_SIGNIFICANCE` dict
- **Adjust styling**: Edit `CSS` string
- **Fix extraction issues**: Modify `extract_shloka_content()`
- **Fix a typo in source text**: Add to `TEXT_FIXES` (shloka -> (field, wrong, right))
- **Add overrides**: Add to the main loop next to the shloka 6/7 overrides

### Image Processing
- **Change scaling**: Modify `scale=0.75` parameter in `resize_media_scale()` calls
- **Convert to B/W**: Uncomment and adapt ImageOps logic (currently removed to preserve color)

## Debugging

The script prints progress for each shloka:
```
Shloka 01: https://jainworld.jainworld.com/bhs/bhs01.htm
Shloka 02: https://jainworld.jainworld.com/bhs/bhs02.htm
...
```

Errors are caught per-shloka with full traceback, allowing partial EPUB generation if some pages fail.

## Notes

- The source website uses Windows-1252 encoding (CP1252), handled with fallback to UTF-8
- MP3 audio links are removed but images preserved
- The script is polite with 0.2s delays between requests
- All 48 verses must be fetched; the script fails if no chapters are added
