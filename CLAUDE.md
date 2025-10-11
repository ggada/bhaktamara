# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python script that generates an EPUB 2.0.1 e-book of the **Bhaktamara Stotra** (48 sacred verses by Acharya Manatunga). The script scrapes content from jainworld.com, processes Sanskrit text images and illustrations, and creates a reader-friendly EPUB optimized for e-ink devices.

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
4. Generate EPUB with title page, index, and 48 chapters

## Architecture

### Main Components

**`create_epub.py`** - Single-file script with these logical sections:

1. **Configuration** (lines 28-51)
   - Book metadata, URL patterns, shloka significance mapping

2. **XHTML Templates** (lines 53-93)
   - EPUB 2.0.1 compliant XHTML 1.1 structure
   - E-ink optimized CSS (tight spacing, serif font, monochrome-friendly borders)

3. **HTTP Helpers** (lines 95-109)
   - `polite_get()`: Retrying HTTP client with exponential backoff
   - `download_image()`: Fetch binary image data

4. **Image Processing** (lines 111-130)
   - `resize_media_scale()`: Scales images to 75% while preserving color
   - Handles both JPEG and GIF formats

5. **Content Extraction** (lines 132-243)
   - `extract_shloka_content()`: Core parsing logic
   - Extracts Sanskrit (red text), English (blue text), illustrations, and Sanskrit text images
   - Normalizes `<br />` tags, handles various HTML formats across pages

6. **XHTML Builders** (lines 245-278)
   - `xhtml_chapter()`: Generates chapter XHTML with significance, images, and text
   - `xhtml_index()`: TOC with significance annotations
   - `xhtml_title()`: Title page

7. **Main Orchestration** (lines 280-390)
   - Loops through 48 shlokas
   - Applies manual overrides for shlokas 6 and 7 (lines 304-320)
   - Assembles EPUB with ebooklib

### Key Design Decisions

- **Image handling**: Sanskrit text images (bhsNNt*.gif) are kept in original color and scaled to 75% for e-ink readability
- **Text extraction heuristics**: Uses color-based detection (red=Sanskrit transliteration, blue=English) with multiple fallback strategies for inconsistent source HTML
- **EPUB 2.0.1 compliance**: Strict XHTML 1.1 + NCX for maximum reader compatibility
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
- **Change shloka significance**: Edit `SHLOKA_SIGNIFICANCE` dict (lines 37-51)
- **Adjust styling**: Edit `CSS` string (lines 74-93)
- **Fix extraction issues**: Modify `extract_shloka_content()` (lines 134-243)
- **Add overrides**: Add to main loop around line 340

### Image Processing
- **Change scaling**: Modify `scale=0.75` parameter in `resize_media_scale()` calls (lines 210, 231)
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
