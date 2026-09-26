#!/usr/bin/env python3
"""Fetch ChordsVault's public contributor catalogue and generate a standalone HTML cloud.
Python 3.9+ and Pillow (python3 -m pip install Pillow). Run with --help for options.
"""
import argparse
import datetime as dt
import html
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SOURCE = 'https://www.chordsvault.com/en/contributors'
API = 'https://www.chordsvault.com/api/songs/contributors'


def get_contributors():
    """Download the complete, unpaginated public contributors list."""
    for attempt in range(3):
        try:
            request = Request(API, headers={'Accept': 'application/json',
                                           'User-Agent': 'ChordsVaultContributorCloud/1.0'})
            with urlopen(request, timeout=40) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def fetch_contributors(fetch=get_contributors):
    """Validate every entry; preserve distinct accounts with the same name."""
    data = fetch()
    if not isinstance(data, list) or not data:
        raise ValueError('Unexpected contributor API response: expected a nonempty list.')
    rows, seen = [], set()
    for item in data:
        if not isinstance(item, dict):
            raise ValueError('Invalid contributor entry.')
        name, user_id, count = item.get('displayName'), item.get('userId'), item.get('songCount')
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Contributor has no valid display name.')
        if type(user_id) is not int or user_id < 1 or user_id in seen:
            raise ValueError('Missing, invalid or duplicate contributor ID.')
        if type(count) is not int or count < 1:
            raise ValueError('Invalid song count for ' + name)
        seen.add(user_id)
        rows.append({'name': name, 'userId': user_id, 'songCount': count,
                     'url': 'https://www.chordsvault.com/en/songs?' +
                            urlencode({'contributorIds': user_id})})
    print(f'Fetched {len(rows)} contributors', file=sys.stderr)
    return sorted(rows, key=lambda row: (-row['songCount'], row['name'], row['userId']))


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ChordsVault · Songs by contributor</title>
<meta name="description" content="ChordsVault contributors sized by song count, with links to their songs.">
<style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f7f4ed;color:#183e55;font:16px/1.5 Arial,sans-serif}main{max-width:1800px;margin:auto}header{padding:28px 3% 8px}.brand{color:#92633b;font-weight:bold;letter-spacing:.08em;font-size:14px}h1{font-size:clamp(32px,4vw,48px);margin:4px 0 8px;line-height:1.1}p{margin:6px 0}a{color:#155f68;text-underline-offset:3px}.metadata,footer{color:#526570;font-size:14px}.cloud{overflow:auto;padding:4px 0}.cloud svg{display:block;width:100%;min-width:1300px;height:auto}svg a{cursor:pointer}svg a,svg a:hover text,svg a:focus text{text-decoration:none}.hover-highlight{fill:transparent}svg a:hover .hover-highlight,svg a:focus .hover-highlight{fill:#ffe680}a:hover,a:focus-visible{text-decoration:none;background-color:#ffe680}svg a:focus{outline:2px solid #a43b23;outline-offset:3px}footer{padding:12px 3% 24px;border-top:1px solid #d9d1c4}.fallback{padding:0 3% 24px}.fallback li{padding:4px 0}#status{padding:12px 3%}.cloud:empty{display:none}@media print{header,footer{break-inside:avoid}.cloud{overflow:visible}.cloud svg{min-width:0}}
main{max-width:1100px}.cloud svg{width:auto;min-width:0;max-width:none;margin:auto}@media print{.cloud svg{width:100%;min-width:0}}</style></head><body><main>
<header><div class="brand">CHORDSVAULT</div><h1>Songs by contributor</h1>
<p>__COUNT__ catalogue entries · Larger names indicate more songs.</p>
<p>Click a contributor to open their songs. Hover or focus on a name for its song count.</p>
<p class="metadata">Updated __DATE__ · <a href="https://www.chordsvault.com/en/contributors" target="_blank" rel="noopener noreferrer">Source catalogue ↗</a></p></header>
<div class="cloud" id="cloud" role="region" aria-label="Contributor word cloud" tabindex="0">__SVG__</div>
<div class="fallback" id="fallback"><details><summary>Contributor list and song counts</summary><ul>__LIST__</ul></details></div>
<footer>Font size uses a square-root scale from 12 to 116 px: round(12 + 104 × (√songs − 1) / max(1, √highest count − 1)). Display names and separate contributor accounts are preserved.<br>On smaller screens, scroll across the cloud or use your browser’s zoom. This page is a snapshot; run the rebuild script to refresh it.</footer>
</main><script type="application/json" id="contributor-data">__DATA__</script></body></html>'''

def cloud_layout(rows, font_path=None):
    """Measure and position every contributor before writing the HTML."""
    try:
        from PIL import ImageFont
    except ImportError:
        raise ValueError('Pillow is required: install it with python3 -m pip install Pillow') from None
    if font_path is None:
        candidates = [
            Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
            Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/arialbd.ttf',
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
            Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf'),
        ]
        font_path = next((path for path in candidates if path.is_file()), None)
        if font_path is None:
            raise ValueError('No suitable font found. Pass --font /path/to/font.ttf')
    colors = ['#155f68', '#277b83', '#183e55', '#92633b', '#b85c39', '#5c7180']
    words = []
    largest = max((row['songCount'] for row in rows), default=1)
    for i, row in enumerate(rows):
        size = round(12 + 104 * (math.sqrt(row['songCount']) - 1) /
                     max(1, math.sqrt(largest) - 1))
        font = ImageFont.truetype(str(font_path), size)
        left, top, right, bottom = font.getbbox(row['name'], anchor='ls')
        advance = float(font.getlength(row['name']))
        words.append(dict(row, size=size, ascent=-top, left=max(0, -left),
                          w=math.ceil(max(advance, right)-min(0, left))+10,
                          h=bottom-top+10, advance=advance, inset=5, vertical_inset=5,
                          color=colors[i % len(colors)]))
        words[-1]['vertical_inset'] = 5 * 1.06
        words[-1]['h'] = bottom - top + 10 * 1.06
        # Keep placement boxes unchanged; center the narrower glyphs inside
        # them so the saved width becomes additional horizontal padding.
        words[-1]['advance'] = advance * .94
        words[-1]['inset'] += (advance - words[-1]['advance']) / 2
        words[-1]['left'] *= .94
    if not words:
        raise ValueError('Cannot generate an empty cloud.')
    # Center-out spiral, bounded font sizes, and tight margins match the
    # initial preview while preserving the existing font and palette.
    width = 4 * math.ceil(max(960, max(word['w'] + 20 for word in words)) / 4)
    height = width * 3 // 4
    for _ in range(12):
        placed = []
        for i, word in enumerate(words):
            for attempt in range(24000):
                theta = attempt * .17 + i * .83
                radius = 1.8 * math.sqrt(attempt) * width / 736
                x = round(width / 2 + math.cos(theta) * radius * 1.35 - word['w'] / 2)
                y = round(height / 2 + math.sin(theta) * radius * height / width * 1.35 - word['h'] / 2)
                if x < 5 or y < 5 or x + word['w'] > width - 5 or y + word['h'] > height - 5:
                    continue
                if any(x < other['x'] + other['w'] and x + word['w'] > other['x']
                       and y < other['y'] + other['h'] and y + word['h'] > other['y']
                       for other in placed):
                    continue
                placed.append(dict(word, x=x, y=y))
                break
            else:
                break
        if len(placed) == len(words):
            return placed, (0, 0, width, height)
        width += 80
        height = width * 3 // 4
    raise ValueError('Unable to fit all contributors in the compact cloud.')


def render_svg(rows, font_path=None):
    placed, view = cloud_layout(rows, font_path)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" '
             'viewBox="{}" width="{}" height="{}" '
             'aria-label="{} contributors sized by song count" '
             'font-family="Arial, DejaVu Sans, sans-serif" font-weight="700">'.format(
                 ' '.join(f'{n:.3f}' for n in view), view[2], round(view[3], 3), len(rows))]
    for word in placed:
        label = html.escape(f"{word['name']}: {word['songCount']} songs", quote=True)
        highlight = ('<rect class="hover-highlight" x="{}" y="{}" width="{}" height="{}" rx="3"/>'.format(
            word['x'], word['y'], word['w'], word['h']))
        parts.append('<a href="{}" target="_blank" rel="noopener noreferrer" tabindex="0" aria-label="{}">'
                     '<title>{}</title>{}<text x="{}" y="{}" font-size="{}" fill="{}" '
                     'textLength="{:.3f}" lengthAdjust="spacingAndGlyphs">{}</text></a>'.format(
                         html.escape(word['url'], quote=True), label, label, highlight,
                         word['x']+word['inset']+word['left'], word['y']+word['vertical_inset']+word['ascent'],
                         word['size'], word['color'], word['advance'], html.escape(word['name'])))
    parts.append('</svg>')
    return '\n'.join(parts)


def render_html(rows, timestamp, font_path=None):
    # Prevent source names from closing the JSON script element or injecting markup.
    payload = json.dumps(rows, ensure_ascii=False).replace('&', r'\u0026').replace('<', r'\u003c').replace('>', r'\u003e')
    listing = '\n'.join('<li><a href="{}" target="_blank" rel="noopener noreferrer">{}</a> — {} songs</li>'.format(
        html.escape(r['url'], quote=True), html.escape(r['name']), r['songCount']) for r in rows)
    # Replace template markers once, so source data cannot introduce new markers.
    import re
    values = {'COUNT': str(len(rows)), 'DATE': html.escape(timestamp), 'LIST': listing, 'DATA': payload, 'SVG': render_svg(rows, font_path)}
    return re.sub(r'__(COUNT|DATE|LIST|DATA|SVG)__', lambda match: values[match[1]], TEMPLATE)


def atomic_write(path, content):
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.'+path.name+'.', delete=False) as output:
            name = output.name
            output.write(content)
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        help='HTML output path (default: chordsvault-contributors-cloud.html in project root)')
    parser.add_argument('--data-output', type=Path, help='Optional JSON snapshot path')
    parser.add_argument('--font', type=Path, help='Optional TrueType/OpenType font file with the required characters')
    args = parser.parse_args()
    if args.output is None:
        args.output = Path(__file__).resolve().parent.parent / 'chordsvault-contributors-cloud.html'
    try:
        if args.data_output and args.output.resolve() == args.data_output.resolve():
            raise ValueError('HTML and JSON outputs must use different paths.')
        rows = fetch_contributors()
        timestamp = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        page = render_html(rows, timestamp, args.font)
        if args.data_output:
            atomic_write(args.data_output, json.dumps({'source': SOURCE, 'api': API,
                         'retrieved': timestamp, 'entries': rows}, ensure_ascii=False, indent=2))
        path = atomic_write(args.output, page)
        print(f'Created {path} ({len(rows)} contributors). Open this file in your browser.')
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f'Rebuild failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
