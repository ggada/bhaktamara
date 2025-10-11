# build_bhaktamara_epub_epub2.py
# -*- coding: utf-8 -*-
"""
Bhaktamara Stotra (EPUB 2.0.1)

This version:
- Keeps Sanskrit text images (bhsNNt*.gif|jpg) in ORIGINAL color (no B/W),
  scaled to 75% for e-ink fit.
- Illustrations also scaled to 75% (color preserved).
- Transliteration forced italic for ALL shlokas.
- Tight line spacing; normalized <br />.
- Shloka 6 (Sanskrit + English) and Shloka 7 (Sanskrit) overrides included.
- EPUB 2 compliant XHTML 1.1 + NCX.
"""

import io
import re
import time
import uuid
import traceback
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from PIL import Image, ImageOps

BOOK_TITLE  = "Bhaktamara Stotra"
BOOK_AUTHOR = "Acharya Manatunga"
OUTPUT_FILE = "Bhaktamara_Stotra.epub"

BASE_URL = "https://jainworld.jainworld.com/bhs/"
CH_URL   = BASE_URL + "bhs{num:02d}.htm"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BhaktamaraEPUB/2.0)"}

SHLOKA_SIGNIFICANCE = {
    1:  "Invokes auspiciousness and spiritual purity.",
    4:  "Believed to remove fear and provide protection.",
    6:  "Recited for relief from diseases and health problems.",
    7:  "Known for removing obstacles and ensuring success in endeavors.",
    11: "Helps in gaining knowledge and wisdom.",
    15: "Considered effective for resolving legal matters and disputes.",
    18: "For relief from poverty and financial troubles.",
    24: "Protection from evil influences and black magic.",
    27: "Peace of mind and emotional stability.",
    31: "For fulfillment of wishes and desires.",
    36: "Relief from imprisonment or bondage.",
    44: "For the protection and well-being of family members.",
    48: "For spiritual liberation and ultimate peace.",
}

# ---------- XHTML shell ----------

DOCTYPE = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">'
HTML_HEAD = f"""<?xml version="1.0" encoding="utf-8"?> 
{DOCTYPE}
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
  <head>
    <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8" />
    <title>{{title}}</title>
    <link rel="stylesheet" type="text/css" href="style.css" />
  </head>
  <body>
    <div class="chapter">
      <h1>{{h1}}</h1>
"""
HTML_TAIL = """
    </div>
  </body>
</html>
"""

CSS = '''
/* minimal, e-ink-friendly */
body { margin:0; padding:1rem; font-family: serif; line-height:1.5; font-size:1.05rem; color:#000; background:#fff; }
h1 { font-size:1.5rem; margin:0 0 0.75rem 0; }
h2 { font-size:1.15rem; margin:0.9rem 0 0.4rem 0; }
p  { margin:0 0 0.6rem 0; }
a { text-decoration:none; } a:hover { text-decoration:underline; }
ul { padding-left:1.1rem; } li { margin:0.25rem 0; }
div.chapter { max-width:42rem; margin:0 auto; }
img { max-width:100%; height:auto; display:block; margin:0.4rem auto; }
.smallnote { font-size:0.95rem; color:#000; }

.significance { border:1px solid #000; padding:0.65rem; border-radius:4px; background:#fff; }
.sanskrit { border:1px solid #000; padding:0.65rem; border-radius:4px; background:#fff; }
.translation { border:1px solid #000; padding:0.65rem; border-radius:4px; background:#fff; }
.sanskrit-text { font-size:1.05rem; line-height:1.4; color:#000; text-align:center; font-style: italic; }
.translation-text { font-size:1.0rem; line-height:1.4; color:#000; text-align:justify; }
.sanskrit-gif { margin:0.35rem auto; }
.illustration { margin:0.5rem auto; }
'''

# ---------- HTTP helpers ----------

def polite_get(session, url, retries=3, timeout=30):
    for k in range(retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception:
            if k == retries - 1:
                raise
            time.sleep(1.1 * (k + 1))

def download_image(session, url):
    return polite_get(session, url).content

# ---------- Image scaling (no B/W conversion) ----------

def resize_media_scale(data, media_type, scale=0.75):
    """Resize any image to a fixed scale (keep color, keep format)."""
    try:
        im = Image.open(io.BytesIO(data))
        w, h = im.size
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        im = im.convert("RGB" if media_type == "image/jpeg" else "P")
        im = im.resize((new_w, new_h), Image.LANCZOS)
        buf = io.BytesIO()
        if media_type == "image/jpeg":
            im.save(buf, format="JPEG", quality=85, optimize=True)
        else:
            # For GIFs, converting to 'P' helps keep file size small
            im.save(buf, format="GIF", optimize=True)
        return buf.getvalue()
    except Exception:
        return data

# ---------- Extraction ----------

def extract_shloka_content(html_text, page_url, session, shloka_num):
    """
    Returns:
      sanskrit_html (str, with <br /> kept, normalized & compact),
      english_html  (str, with <br /> kept, normalized & compact),
      illustration: (filename, bytes, media_type) or None,
      sanskrit_imgs: list[(filename, bytes, media_type)]
    """
    soup = BeautifulSoup(html_text, "lxml")

    # Unwrap MP3 anchors so inner <img> survive
    for a in soup.find_all("a", href=True):
        if a["href"].lower().endswith(".mp3"):
            a.replace_with(*a.contents)

    # Remove only the exact click-to-audio text
    for t in soup.find_all(string=True):
        if "(Click on the above sloka to start the audio)" in (t or ""):
            t.extract()

    scope = soup.find("table", attrs={"width": re.compile(r'^580$', re.I)}) or soup

    def node_is_color(node, want):
        c = ((node.get('color') or '') + ' ' + (node.get('style') or '')).lower()
        if want == 'red':
            return any(x in c for x in ['#ff0000', 'rgb(255,0,0)', 'red'])
        if want == 'blue':
            return any(x in c for x in ['#000080', 'rgb(0,0,128)', 'navy', '#00008b', 'blue'])
        return False

    def as_html_with_br(n):
        raw = n.decode_contents(formatter="html")
        raw = re.sub(r'<\s*br\s*/?\s*>', '<br />', raw, flags=re.I)      # normalize <br>
        raw = re.sub(r'(?:<br\s*/>\s*){2,}', '<br />', raw, flags=re.I)  # collapse multiples
        return raw.strip()

    # Sanskrit transliteration blocks (red)
    red_blocks = scope.find_all(lambda tag: tag.name in ('font','span','p','div') and node_is_color(tag, 'red'))
    red_html_pieces = [as_html_with_br(blk) for blk in red_blocks if blk.get_text(" ", strip=True)]
    if red_html_pieces:
        sanskrit_html = '<br />'.join(red_html_pieces)
        sanskrit_html = re.sub(r'</?(?:font|span|div|p)[^>]*>', '', sanskrit_html).strip()
    else:
        cands = scope.find_all(lambda tag: tag.name in ('font','div','p') and
                               (('size' in tag.attrs and str(tag.get('size')) in ('3','4','5')) or node_is_color(tag, 'red')))
        if cands:
            best = max(cands, key=lambda t: len(t.get_text(" ", strip=True)))
            sanskrit_html = re.sub(r'</?(?:font|span|div|p)[^>]*>', '', as_html_with_br(best)).strip()
        else:
            sanskrit_html = ""

    # English (blue) with fallback
    blue_blk = scope.find(lambda tag: tag.name in ('font','span','p','div') and node_is_color(tag, 'blue'))
    if blue_blk:
        english_html = re.sub(r'</?(?:font|span|div|p)[^>]*>', '', as_html_with_br(blue_blk)).strip()
    else:
        paras = [p for p in scope.find_all('p') if p.find('img') is None]
        if paras:
            best = max(paras, key=lambda t: len(t.get_text(" ", strip=True)))
            english_html = re.sub(r'</?(?:font|span|div|p)[^>]*>', '', as_html_with_br(best)).strip()
        else:
            english_html = ""

    # Illustration preferred bhsNNi.(jpg|gif); else first jpg/gif on page
    ill_tag = scope.find('img', src=re.compile(rf"bhs{shloka_num:02d}i\.(?:jpg|jpeg|gif)$", re.I))
    if not ill_tag:
        ill_tag = scope.find('img', src=re.compile(r"\.(?:jpg|jpeg|gif)$", re.I))
    illustration = None
    if ill_tag and ill_tag.get('src'):
        ill_url = urljoin(page_url, ill_tag['src'])
        try:
            data = download_image(session, ill_url)
            if re.search(r"\.(jpe?g)$", ill_url, re.I):
                mt, ext = "image/jpeg", ".jpg"
            else:
                mt, ext = "image/gif", ".gif"
            data = resize_media_scale(data, mt, scale=0.75)  # 75% color
            illustration = (f"illustration_{shloka_num:02d}{ext}", data, mt)
        except Exception:
            illustration = None

    # Sanskrit text images: bhsNNt*.gif|jpg (keep ORIGINAL color; just scale 75%)
    t_pattern = re.compile(rf"bhs{shloka_num:02d}t[a-z0-9]*\.(?:gif|jpg|jpeg)$", re.I)
    sanskrit_imgs, seen = [], set()
    for img in scope.find_all('img', src=True):
        src = img['src']
        if t_pattern.search(src):
            full = urljoin(page_url, src)
            if full in seen:
                continue
            seen.add(full)
            try:
                bytes_in = download_image(session, full)
                if re.search(r"\.(jpe?g)$", full, re.I):
                    mt, ext = "image/jpeg", ".jpg"
                else:
                    mt, ext = "image/gif", ".gif"
                bytes_out = resize_media_scale(bytes_in, mt, scale=0.75)
                idx = len(sanskrit_imgs) + 1
                sanskrit_imgs.append((f"sanskrit_{shloka_num:02d}_{idx}{ext}", bytes_out, mt))
            except Exception:
                pass

    # Normalize again just in case
    if sanskrit_html:
        sanskrit_html = re.sub(r'(?:<br\s*/>\s*){2,}', '<br />', sanskrit_html, flags=re.I).strip()
    if english_html:
        english_html = re.sub(r'(?:<br\s*/>\s*){2,}', '<br />', english_html, flags=re.I).strip()

    return sanskrit_html, english_html, illustration, sanskrit_imgs

# ---------- XHTML builders ----------

def xhtml_chapter(shloka_num, sanskrit_html, english_html, illustration_name, sanskrit_img_names):
    sig = SHLOKA_SIGNIFICANCE.get(shloka_num, "")
    parts = []
    if sig:
        parts.append(f'<div class="significance"><p><strong>Special significance:</strong> {sig}</p></div>')
    if illustration_name:
        parts.append(f'<div class="image-container illustration"><img src="{illustration_name}" alt="Shloka {shloka_num} illustration" /></div>')
    parts.append('<div class="sanskrit"><h2>Sanskrit Text</h2>')
    for nm in sanskrit_img_names:
        parts.append(f'<img class="sanskrit-gif" src="{nm}" alt="Shloka {shloka_num} Sanskrit image" />')
    # Force italics via <em> to handle strict readers
    sanskrit_render = f'<em>{sanskrit_html or "Content not available"}</em>'
    parts.append(f'<p class="sanskrit-text">{sanskrit_render}</p></div>')
    parts.append('<div class="translation"><h2>English Translation</h2>')
    parts.append(f'<p class="translation-text">{(english_html or "Translation not available")}</p></div>')
    title = f"Shloka {shloka_num:02d}"
    return HTML_HEAD.replace("{title}", title).replace("{h1}", title) + "".join(parts) + HTML_TAIL

def xhtml_index():
    items = []
    for i in range(1, 49):
        extra = SHLOKA_SIGNIFICANCE.get(i)
        if extra:
            items.append(f'<li><a href="shloka_{i:02d}.xhtml">Shloka {i}</a>: <span class="smallnote">{extra}</span></li>')
        else:
            items.append(f'<li><a href="shloka_{i:02d}.xhtml">Shloka {i}</a></li>')
    body = '<p>Select a Shloka:</p>\n<ul>\n' + "\n".join(items) + "\n</ul>"
    return HTML_HEAD.replace("{title}", "Index").replace("{h1}", f"{BOOK_TITLE} — Index") + body + HTML_TAIL

def xhtml_title():
    body = f"<p><em>Author:</em> {BOOK_AUTHOR}</p><p>48 Sacred Verses</p>"
    return HTML_HEAD.replace("{title}", "Title").replace("{h1}", BOOK_TITLE) + body + HTML_TAIL

# ---------- Main ----------

def main():
    book = epub.EpubBook()
    book.set_identifier(str(uuid.uuid4()))
    book.set_title(BOOK_TITLE)
    book.set_language("en")
    book.add_author(BOOK_AUTHOR)

    css_item = epub.EpubItem(uid="style", file_name="style.css", media_type="text/css", content=CSS.encode("utf-8"))
    book.add_item(css_item)

    title_pg = epub.EpubHtml(title="Title", file_name="title.xhtml", lang="en")
    title_pg.content = xhtml_title().encode("utf-8")
    book.add_item(title_pg)

    index_pg = epub.EpubHtml(title="Index", file_name="index.xhtml", lang="en")
    index_pg.content = xhtml_index().encode("utf-8")
    book.add_item(index_pg)

    session = requests.Session()
    session.headers.update(HEADERS)

    # Overrides
    ENGLISH_OVERRIDE_6 = (
        "O embodiment of pure wisdom! Though I possess little knowledge and am a "
        "laughingstock to the wise, my devotion moves me to sing your praise—just as "
        "the mango buds of spring impel the cuckoo to pour out its sweet song."
    )
    SANSKRIT_OVERRIDE_6 = (
        "alpashrutam shrutavatam parihasadham<br />"
        "tvad bhaktireva mukharikurute balanmam<br />"
        "yatkokilah kila madhau madhuram virauti<br />"
        "tachcharuchuta - kalikanikaraikahetu"
    )
    SANSKRIT_OVERRIDE_7 = (
        "tvatsanstavena bhavasantati - sannibaddham<br />"
        "papam kshanat kshayamupaiti sharira bhajam<br />"
        "akranta - lokamalinilamasheshamashu<br />"
        "suryanshubhinnamiva sharvaramandhakaram"
    )

    chapters = []
    images_added = 0

    print("Fetching shlokas…\n")
    for i in range(1, 49):
        url = CH_URL.format(num=i)
        print(f"Shloka {i:02d}: {url}")
        try:
            r = polite_get(session, url, timeout=30)
            try:
                html_text = r.content.decode("cp1252")
            except UnicodeDecodeError:
                html_text = r.text

            sanskrit_html, english_html, illustration, sanskrit_imgs = extract_shloka_content(
                html_text, url, session, i
            )

            # Apply overrides
            if i == 6:
                english_html = ENGLISH_OVERRIDE_6
                sanskrit_html = SANSKRIT_OVERRIDE_6
            elif i == 7:
                sanskrit_html = SANSKRIT_OVERRIDE_7

            ill_name = illustration[0] if illustration else None
            san_names = [nm for (nm, _b, _mt) in sanskrit_imgs]

            ch = epub.EpubHtml(title=f"Shloka {i}", file_name=f"shloka_{i:02d}.xhtml", lang="en")
            ch.content = xhtml_chapter(i, sanskrit_html, english_html, ill_name, san_names).encode("utf-8")
            book.add_item(ch)
            chapters.append(ch)

            if illustration:
                nm, data, mt = illustration
                book.add_item(epub.EpubItem(uid=f"img_ill_{i:02d}", file_name=nm, media_type=mt, content=data))
                images_added += 1
            for idx, (nm, data, mt) in enumerate(sanskrit_imgs, 1):
                book.add_item(epub.EpubItem(uid=f"img_san_{i:02d}_{idx}", file_name=nm, media_type=mt, content=data))
                images_added += 1

            time.sleep(0.2)
        except Exception as e:
            print(f"  ! Error: {e}")
            traceback.print_exc()

    if not chapters:
        raise RuntimeError("No chapters were added. Aborting.")

    book.toc = (
        epub.Link('title.xhtml', 'Title', 'title'),
        epub.Link('index.xhtml', 'Index', 'index'),
        *chapters
    )
    book.add_item(epub.EpubNcx())
    book.spine = [title_pg, index_pg] + chapters
    epub.write_epub(OUTPUT_FILE, book, options={'epub3_pages': False})

    print("\n==========================================")
    print(f"✓ EPUB created: {OUTPUT_FILE}")
    print(f"✓ Chapters: {len(chapters)} (+ title & index)")
    print(f"✓ Images embedded (Sanskrit=color @ 75%, Illustrations=color @ 75%): {images_added}")
    print("✓ Shloka 6: Sanskrit + English overrides applied")
    print("✓ Shloka 7: Sanskrit override applied")
    print("✓ Transliteration: italic + tight line spacing")
    print("==========================================\n")

if __name__ == "__main__":
    main()
