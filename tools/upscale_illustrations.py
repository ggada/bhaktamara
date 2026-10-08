# -*- coding: utf-8 -*-
"""
Regenerate images/illustration_NN.jpg from the jainworld.com originals.

Each original (about 275x384) is enlarged 2x with Lanczos, then blended with
AI_STRENGTH of a Real-ESRGAN x4plus upscale (downsized to the same 2x size).
A low strength cleans up JPEG speckle and edges without the model redrawing
faces; at 50% and above it visibly changes the Jina's eyes (e.g. shloka 48).

Needs the Real-ESRGAN ncnn-vulkan binary and its models:
  https://github.com/xinntao/Real-ESRGAN/releases (realesrgan-ncnn-vulkan-*.zip)

Usage:
  python tools/upscale_illustrations.py --realesrgan /path/to/realesrgan-ncnn-vulkan
  python tools/upscale_illustrations.py --sr-dir existing_x4_pngs/   # reuse x4 output
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time

import requests
from PIL import Image

AI_STRENGTH = 0.20
JPEG_QUALITY = 85
BASE_URL = "https://jainworld.jainworld.com/bhs/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BhaktamaraEPUB/2.0)"}
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "images")


def fetch_originals(dest):
    session = requests.Session()
    session.headers.update(HEADERS)
    for i in range(1, 49):
        path = os.path.join(dest, f"bhs{i:02d}i.jpg")
        if os.path.exists(path):
            continue
        page = session.get(f"{BASE_URL}bhs{i:02d}.htm", timeout=30).text
        m = re.search(rf'src="(bhs{i:02d}i\.jpe?g)"', page, re.I)
        if not m:
            sys.exit(f"No JPEG illustration found on page {i}")
        with open(path, "wb") as f:
            f.write(session.get(BASE_URL + m.group(1), timeout=30).content)  # keep original bytes
        time.sleep(0.2)


def run_realesrgan(binary, src, dest):
    models = os.path.join(os.path.dirname(binary), "models")
    subprocess.run([binary, "-i", src, "-o", dest, "-n", "realesrgan-x4plus", "-s", "4",
                    "-m", models, "-f", "png"], check=True)


def blend(orig_dir, sr_dir, out_dir, strength):
    os.makedirs(out_dir, exist_ok=True)
    for i in range(1, 49):
        orig = Image.open(os.path.join(orig_dir, f"bhs{i:02d}i.jpg")).convert("RGB")
        size = (orig.width * 2, orig.height * 2)
        base = orig.resize(size, Image.LANCZOS)
        sr = Image.open(os.path.join(sr_dir, f"bhs{i:02d}i.png")).convert("RGB").resize(size, Image.LANCZOS)
        out = os.path.join(out_dir, f"illustration_{i:02d}.jpg")
        Image.blend(base, sr, strength).save(out, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        print(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--realesrgan", help="path to realesrgan-ncnn-vulkan")
    ap.add_argument("--originals", help="folder of bhsNNi.jpg originals (downloaded if missing)")
    ap.add_argument("--sr-dir", help="folder of existing x4 bhsNNi.png outputs (skips Real-ESRGAN)")
    ap.add_argument("--strength", type=float, default=AI_STRENGTH)
    args = ap.parse_args()
    if not args.sr_dir and not args.realesrgan:
        ap.error("pass --realesrgan or --sr-dir")

    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = args.originals or os.path.join(tmp, "orig")
        os.makedirs(orig_dir, exist_ok=True)
        fetch_originals(orig_dir)
        sr_dir = args.sr_dir
        if not sr_dir:
            sr_dir = os.path.join(tmp, "x4")
            os.makedirs(sr_dir)
            run_realesrgan(args.realesrgan, orig_dir, sr_dir)
        blend(orig_dir, sr_dir, OUT_DIR, args.strength)


if __name__ == "__main__":
    main()
