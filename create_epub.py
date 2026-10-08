# build_bhaktamara_epub_epub2.py
# -*- coding: utf-8 -*-
"""
Bhaktamara Stotra (EPUB 3 + NCX)

This version:
- English translation from translation_english.txt (made from the Sanskrit, with
  notes on wordplay); the jainworld.com rendering is kept as a commentary.
- Sanskrit as inline Unicode Devanagari (sanskrit_devanagari.txt), set in an
  embedded Noto Serif Devanagari font, instead of the source site's text images.
- Illustrations also scaled to 75% (color preserved).
- Transliteration forced italic for ALL shlokas.
- Tight line spacing; normalized <br />.
- Shloka 6 (Sanskrit + English) and Shloka 7 (Sanskrit) overrides included.
- Typo fixes from TEXT_FIXES applied to source text.
- Contents page + nav/NCX TOC listing each verse by its opening line.
- EPUB 3 (ebooklib) with NCX so EPUB 2 readers still get a TOC.
"""

import io
import os
import re
import time
import uuid
import traceback
import zipfile
from html import escape
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from PIL import Image

BOOK_TITLE  = "Bhaktamara Stotra"
BOOK_AUTHOR = "Acharya Manatunga"
OUTPUT_FILE = "Bhaktamara_Stotra.epub"

HERE = os.path.dirname(os.path.abspath(__file__))
DEVANAGARI_FILE = os.path.join(HERE, "sanskrit_devanagari.txt")
TRANSLATION_FILE = os.path.join(HERE, "translation_english.txt")
FONT_FILE = os.path.join(HERE, "fonts", "NotoSerifDevanagari-Regular.ttf")

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

# Typos in the source pages: shloka -> [(field, wrong, right)]
# Matched after whitespace is collapsed. Transliteration fixes were checked
# against the Devanagari in sanskrit_devanagari.txt.
TEXT_FIXES = {
    1:  [("english", "Thrthmkara", "Tirthankara"), ("english", "salutation salutations", "salutations")],
    3:  [("english", "impossible took", "impossible task"), ("english", "inspite", "in spite")],
    5:  [("english", "OApostle", "O Apostle"), ("english", "widdom", "wisdom"),
         ("english", "fraility", "frailty"), ("english", "own capacity.", "own capacity.)")],
    8:  [("sanskrit", "Matveti nath!", "Matveti natha!"), ("sanskrit", "muktaphal dyutim", "muktaphala dyutim")],
    9:  [("sanskrit", "vikasha bhanjt", "vikasha bhanji"), ("english", "your eulog,", "your eulogy,")],
    11: [("sanskrit", "uypayatijanasya", "upayati janasya")],
    15: [("english", "libid gestures", "libidinous gestures"),
         ("english", "great Sumeru mountain", "great Mandara mountain")],
    16: [("english", "does not effect it", "does not affect it")],
    17: [("sanskrit", "kadachidupayast", "kadachidupayasi"), ("english", "unabounding", "unbounded")],
    20: [("sanskrit", "Teiah sfuran", "Tejah sphuran"), ("sanskrit", "mcihattvam", "mahattvam")],
    21: [("sanskrit", "to-shameti", "toshameti")],
    22: [("sanskrit", "digianayati", "dig janayati")],
    24: [("sanskrit", "vibhumachintyq", "vibhumachintyam")],
    27: [("sanskrit", "sainshrito", "samshrito"), ("sanskrit", "jatagarvalh", "jatagarvaih"),
         ("sanskrit", "apikshitosil", "apikshitoasi"), ("english", "creeped", "crept")],
    31: [("sanskrit", "vivraddhashobham", "vivriddhashobham"), ("english", "0 Tirthankara", "O Tirthankara")],
    35: [("english", "0 Tirthankara", "O Tirthankara")],
    36: [("sanskrit", "puniakanti", "punjakanti")],
    38: [("english", "quietitude", "quietude"), ("english", "oppressive of the beings.", "oppressive of the beings.)")],
    39: [("sanskrit", "kumbhgaladujjvala", "kumbhagaladujjvala")],
    40: [("english", "conflagaration", "conflagration"), ("english", "laudition", "laudation")],
    44: [("english", "Abroad a ship", "Aboard a ship")],
    45: [("sanskrit", "Tvatpadapa,nkaja", "Tvatpadapankaja")],
    46: [("english", "0 Liberated", "O Liberated")],
    47: [("sanskrit", "bhlyeua", "bhiyeva")],
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
ol.contents { list-style:none; padding-left:0; } ol.contents li { margin:0 0 0.5rem 0; }
div.chapter { max-width:42rem; margin:0 auto; }
img { max-width:100%; height:auto; display:block; margin:0.4rem auto; }
.smallnote { font-size:0.95rem; color:#000; }

.significance { border:1px solid #000; padding:0.65rem; border-radius:4px; background:#fff; }
.sanskrit { border:1px solid #000; padding:0.65rem; border-radius:4px; background:#fff; }
.translation { border:1px solid #000; padding:0.65rem; border-radius:4px; background:#fff; }
.sanskrit-text { font-size:1.05rem; line-height:1.4; color:#000; text-align:center; font-style: italic; }
.translation-text { font-size:1.0rem; line-height:1.4; color:#000; text-align:justify; }
.translation-note { font-size:0.9rem; line-height:1.35; color:#000; font-style:italic; margin-top:0.4rem; }
.commentary { border:1px solid #000; padding:0.65rem; border-radius:4px; background:#fff; margin-top:0.6rem; }
@font-face { font-family:"Noto Serif Devanagari"; font-weight:normal; font-style:normal;
             src:url("fonts/NotoSerifDevanagari-Regular.ttf"); }
.devanagari { font-family:"Noto Serif Devanagari", serif; font-size:1.15rem; line-height:1.7;
              color:#000; text-align:center; font-style:normal; margin:0.3rem 0 0.7rem 0; }
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
      illustration: (filename, bytes, media_type) or None
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

    # Normalize again just in case
    if sanskrit_html:
        sanskrit_html = re.sub(r'(?:<br\s*/>\s*){2,}', '<br />', sanskrit_html, flags=re.I).strip()
    if english_html:
        english_html = re.sub(r'(?:<br\s*/>\s*){2,}', '<br />', english_html, flags=re.I).strip()

    return sanskrit_html, english_html, illustration

# ---------- Devanagari text ----------

def load_devanagari(path=DEVANAGARI_FILE):
    """Parse sanskrit_devanagari.txt -> {shloka: [4 lines]}; fail loudly if it's malformed."""
    digits = str.maketrans("०१२३४५६७८९", "0123456789")
    with open(path, encoding="utf-8") as f:
        text = "\n".join(l for l in f.read().splitlines() if not l.startswith("#"))
    verses = {}
    for block in text.strip().split("\n\n"):
        lines = [l.strip() for l in block.strip().splitlines()]
        m = re.search(r"॥\s*([०-९]+)\s*॥$", lines[-1])
        if len(lines) != 4 or not m:
            raise ValueError(f"Bad verse block in {path}:\n{block}")
        verses[int(m.group(1).translate(digits))] = lines
    if sorted(verses) != list(range(1, 49)):
        raise ValueError(f"{path} must contain verses 1-48, got {sorted(verses)}")
    return verses

def load_translations(path=TRANSLATION_FILE):
    """Parse translation_english.txt -> {shloka: (translation, note or "")}."""
    with open(path, encoding="utf-8") as f:
        text = "\n".join(l for l in f.read().splitlines() if not l.startswith("#") or l.startswith("## "))
    out = {}
    for m in re.finditer(r"^## (\d+)\n(.*?)(?=^## |\Z)", text, flags=re.S | re.M):
        lines = [l.strip() for l in m.group(2).strip().splitlines() if l.strip()]
        note = " ".join(l[len("Note:"):].strip() for l in lines if l.startswith("Note:"))
        body = " ".join(l for l in lines if not l.startswith("Note:"))
        if not body:
            raise ValueError(f"Verse {m.group(1)} has no translation in {path}")
        out[int(m.group(1))] = (body, note)
    if sorted(out) != list(range(1, 49)):
        raise ValueError(f"{path} must contain verses 1-48, got {sorted(out)}")
    return out

# ---------- XHTML builders ----------

def xhtml_chapter(shloka_num, devanagari_lines, sanskrit_html, translation, commentary_html, illustration_name):
    sig = SHLOKA_SIGNIFICANCE.get(shloka_num, "")
    parts = []
    if sig:
        parts.append(f'<div class="significance"><p><strong>Special significance:</strong> {sig}</p></div>')
    if illustration_name:
        parts.append(f'<div class="image-container illustration"><img src="{illustration_name}" alt="Shloka {shloka_num} illustration" /></div>')
    parts.append('<div class="sanskrit"><h2>Sanskrit Text</h2>')
    parts.append('<p class="devanagari" lang="sa" xml:lang="sa">' + "<br />".join(devanagari_lines) + '</p>')
    # Force italics via <em> to handle strict readers
    sanskrit_render = f'<em>{sanskrit_html or "Content not available"}</em>'
    parts.append(f'<p class="sanskrit-text">{sanskrit_render}</p></div>')
    text, note = translation
    parts.append('<div class="translation"><h2>English Translation</h2>')
    parts.append(f'<p class="translation-text">{escape(text)}</p>')
    if note:
        parts.append(f'<p class="translation-note">{escape(note)}</p>')
    parts.append('</div>')
    if commentary_html:
        parts.append('<div class="commentary"><h2>Commentary</h2>')
        parts.append(f'<p class="translation-text">{commentary_html}</p></div>')
    title = f"Shloka {shloka_num:02d}"
    return HTML_HEAD.replace("{title}", title).replace("{h1}", title) + "".join(parts) + HTML_TAIL

def first_line(sanskrit_html):
    """Opening line of the transliteration, as plain text (for the contents)."""
    line = re.split(r'<br\s*/?>', sanskrit_html or "", maxsplit=1)[0]
    line = re.sub(r'<[^>]+>', '', line)
    line = re.sub(r'\s+', ' ', line).strip()
    return line[:1].upper() + line[1:]

def xhtml_contents(first_lines):
    items = []
    for i in range(1, 49):
        opening = first_lines.get(i)
        if opening is None:
            continue
        sig = SHLOKA_SIGNIFICANCE.get(i)
        note = f'<br /><span class="smallnote">{sig}</span>' if sig else ""
        items.append(f'<li><a href="shloka_{i:02d}.xhtml">{i}. <em>{opening}</em></a>{note}</li>')
    body = '<ol class="contents">\n' + "\n".join(items) + "\n</ol>"
    return HTML_HEAD.replace("{title}", "Contents").replace("{h1}", "Contents") + body + HTML_TAIL

def xhtml_title():
    body = (f"<p><em>Author:</em> {BOOK_AUTHOR}</p><p>48 Sacred Verses</p>"
            '<p class="smallnote">Transliteration, commentary and illustrations: jainworld.com. '
            "English translation and notes made for this edition from the Sanskrit. "
            "Devanagari text after Ashok Sethi's edition (proofread by Yashwant Malaiya), "
            "set in Noto Serif Devanagari (SIL Open Font License).</p>")
    return HTML_HEAD.replace("{title}", "Title").replace("{h1}", BOOK_TITLE) + body + HTML_TAIL

# ---------- NCX post-processing ----------

def fix_ncx(path):
    """ebooklib omits NCX playOrder and writes dtb:depth=0; older readers need both.
    Number navPoints in document order (same target -> same playOrder) and set the depth."""
    with zipfile.ZipFile(path) as z:
        entries = [(info, z.read(info.filename)) for info in z.infolist()]

    def patch(ncx):
        order = {}
        def number(m):
            src = m.group(3)
            order.setdefault(src, len(order) + 1)
            return f'{m.group(1)} playOrder="{order[src]}"{m.group(2)}{src}'
        # A navPoint's own <content> comes right after its label, before any child navPoint
        ncx = re.sub(r'(<navPoint\b[^>]*?)(?:\s+playOrder="\d*")?(>\s*<navLabel>.*?</navLabel>\s*<content src=")([^"]+)',
                     number, ncx, flags=re.S)
        level = deepest = 0
        for tag in re.finditer(r'<(/?)navPoint\b', ncx):
            level += -1 if tag.group(1) else 1
            deepest = max(deepest, level)
        return re.sub(r'(<meta content=")\d+(" name="dtb:depth"/>)', rf'\g<1>{deepest}\2', ncx)

    with zipfile.ZipFile(path, "w") as z:
        for info, data in entries:
            if info.filename.endswith(".ncx"):
                data = patch(data.decode("utf-8")).encode("utf-8")
            z.writestr(info, data)

# ---------- Main ----------

def main():
    book = epub.EpubBook()
    book.set_identifier(str(uuid.uuid5(uuid.NAMESPACE_URL, CH_URL.format(num=1) + "#" + OUTPUT_FILE)))
    book.set_title(BOOK_TITLE)
    book.set_language("en")
    book.add_author(BOOK_AUTHOR)

    css_item = epub.EpubItem(uid="style", file_name="style.css", media_type="text/css", content=CSS.encode("utf-8"))
    book.add_item(css_item)
    with open(FONT_FILE, "rb") as f:
        book.add_item(epub.EpubItem(uid="font_deva", file_name="fonts/NotoSerifDevanagari-Regular.ttf",
                                    media_type="font/ttf", content=f.read()))
    devanagari = load_devanagari()
    translations = load_translations()

    title_pg = epub.EpubHtml(title="Title", file_name="title.xhtml", lang="en")
    title_pg.content = xhtml_title().encode("utf-8")
    title_pg.add_item(css_item)
    book.add_item(title_pg)

    contents_pg = epub.EpubHtml(title="Contents", file_name="index.xhtml", lang="en")
    contents_pg.add_item(css_item)
    book.add_item(contents_pg)
    first_lines = {}

    session = requests.Session()
    session.headers.update(HEADERS)

    # Overrides
    ENGLISH_OVERRIDE_6 = (
        "O embodiment of pure wisdom! Though I possess little knowledge and am a "
        "laughingstock to the wise, my devotion moves me to sing your praise—just as "
        "the mango buds of spring impel the cuckoo to pour out its sweet song."
    )
    SANSKRIT_OVERRIDE_6 = (
        "alpashrutam shrutavatam parihasadhama<br />"
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

            sanskrit_html, english_html, illustration = extract_shloka_content(
                html_text, url, session, i
            )

            # Apply overrides
            if i == 6:
                english_html = ENGLISH_OVERRIDE_6
                sanskrit_html = SANSKRIT_OVERRIDE_6
            elif i == 7:
                sanskrit_html = SANSKRIT_OVERRIDE_7

            sanskrit_html = re.sub(r"\s+", " ", sanskrit_html)
            english_html = re.sub(r"\s+", " ", english_html)
            for field, wrong, right in TEXT_FIXES.get(i, []):
                text = english_html if field == "english" else sanskrit_html
                if wrong not in text:
                    print(f"  ! TEXT_FIXES: '{wrong}' not found in {field} text (already fixed upstream?)")
                    continue
                text = text.replace(wrong, right)
                if field == "english":
                    english_html = text
                else:
                    sanskrit_html = text

            first_lines[i] = first_line(sanskrit_html)
            ill_name = illustration[0] if illustration else None

            ch = epub.EpubHtml(title=f"Shloka {i}: {first_lines[i]}", file_name=f"shloka_{i:02d}.xhtml", lang="en")
            ch.add_item(css_item)
            ch.content = xhtml_chapter(i, devanagari[i], sanskrit_html, translations[i], english_html, ill_name).encode("utf-8")
            book.add_item(ch)
            chapters.append(ch)

            if illustration:
                nm, data, mt = illustration
                book.add_item(epub.EpubItem(uid=f"img_ill_{i:02d}", file_name=nm, media_type=mt, content=data))
                images_added += 1

            time.sleep(0.2)
        except Exception as e:
            print(f"  ! Error: {e}")
            traceback.print_exc()

    if not chapters:
        raise RuntimeError("No chapters were added. Aborting.")

    contents_pg.content = xhtml_contents(first_lines).encode("utf-8")

    # Flat TOC: Apple Books hides entries nested under a section, so every shloka is top-level
    book.toc = (
        epub.Link('title.xhtml', 'Title', 'title'),
        epub.Link('index.xhtml', 'Contents', 'contents'),
        *chapters,
    )
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = [title_pg, contents_pg] + chapters
    epub.write_epub(OUTPUT_FILE, book, options={'epub3_pages': False})
    fix_ncx(OUTPUT_FILE)

    print("\n==========================================")
    print(f"✓ EPUB created: {OUTPUT_FILE}")
    print(f"✓ Chapters: {len(chapters)} (+ title & contents)")
    print(f"✓ Illustrations embedded (color @ 75%): {images_added}")
    print("✓ Sanskrit: inline Devanagari (embedded Noto Serif Devanagari)")
    print("✓ Shloka 6: Sanskrit + English overrides applied")
    print("✓ Shloka 7: Sanskrit override applied")
    print("✓ Transliteration: italic + tight line spacing")
    print("==========================================\n")

if __name__ == "__main__":
    main()
