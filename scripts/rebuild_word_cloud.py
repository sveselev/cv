#!/usr/bin/env python3
"""Fetch ChordsVault's public artist catalogue and generate a standalone HTML cloud.
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
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

SOURCE = 'https://www.chordsvault.com/ru/artists'
API = 'https://www.chordsvault.com/api/artists'


def get_page(page, limit):
    url = API + '?' + urlencode({'page': page, 'limit': limit})
    for attempt in range(3):
        try:
            request = Request(url, headers={'Accept': 'application/json',
                                           'User-Agent': 'ChordsVaultWordCloud/1.0'})
            with urlopen(request, timeout=40) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def fetch_artists(fetch=get_page):
    """Follow the API's effective page size; fail rather than save partial data."""
    rows, seen = [], set()
    total = None
    page, limit = 1, 500
    while True:
        data = fetch(page, limit)
        if not isinstance(data, dict) or not isinstance(data.get('items'), list):
            raise ValueError('Unexpected artist API response: missing items list.')
        current_total = data.get('total')
        if type(current_total) is not int or current_total < 1:
            raise ValueError('The API returned an invalid or empty catalogue total.')
        if total is None:
            total = current_total
            limit = data.get('limit')
            if type(limit) is not int or limit < 1:
                raise ValueError('The API returned an invalid page size.')
        if current_total != total or data.get('limit') != limit:
            raise ValueError('Catalogue or pagination changed during download. Run again.')
        if data.get('page') != page:
            raise ValueError('The API returned an unexpected page number.')
        expected = min(limit, total - len(rows))
        if len(data['items']) != expected:
            raise ValueError('Incomplete catalogue page; existing HTML was not replaced.')
        for item in data['items']:
            name, slug, count = item.get('name'), item.get('slug'), item.get('songCount')
            if not isinstance(name, str) or not name.strip():
                raise ValueError('Artist has no valid name.')
            if not isinstance(slug, str) or not slug or slug in seen:
                raise ValueError('Missing or duplicate artist slug; run again.')
            if type(count) is not int or count < 1:
                raise ValueError('Invalid song count for ' + name)
            seen.add(slug)
            rows.append({'name': name, 'slug': slug, 'songCount': count,
                         'url': SOURCE + '/' + quote(slug, safe='')})
        print(f'Fetched {len(rows)} / {total} artists', file=sys.stderr)
        if len(rows) == total:
            break
        page += 1
    return sorted(rows, key=lambda row: (-row['songCount'], row['name']))


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ChordsVault · Songs by artist</title>
<meta name="description" content="ChordsVault artists sized by song count, with links to their songs.">
<script>
(() => {
  let theme;
  try { theme = localStorage.getItem('chordsvault-cloud-theme'); } catch (_) {}
  if (theme !== 'light' && theme !== 'dark') theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  document.documentElement.dataset.theme = theme;
})();
</script>
<style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f7f4ed;color:#183e55;font:16px/1.5 Arial,sans-serif}main{max-width:1800px;margin:auto}header{padding:28px 3% 8px}.brand{color:#92633b;font-weight:bold;letter-spacing:.08em;font-size:14px}h1{font-size:clamp(32px,4vw,48px);margin:4px 0 8px;line-height:1.1}p{margin:6px 0}a{color:#155f68;text-underline-offset:3px}.metadata,footer{color:#526570;font-size:14px}.cloud{overflow:auto;padding:4px 0}.cloud svg{display:block;width:100%;min-width:1300px;height:auto}svg a{cursor:pointer}svg a,svg a:hover text,svg a:focus text{text-decoration:none}.hover-highlight{fill:transparent}svg a:hover .hover-highlight,svg a:focus .hover-highlight{fill:#ffe680}a:hover,a:focus-visible{text-decoration:none;background-color:#ffe680}svg a:focus{outline:2px solid #a43b23;outline-offset:3px}footer{padding:12px 3% 24px;border-top:1px solid #d9d1c4}.fallback{padding:0 3% 24px}.fallback li{padding:4px 0}#status{padding:12px 3%}.cloud:empty{display:none}@media print{header,footer{break-inside:avoid}.cloud{overflow:visible}.cloud svg{min-width:0}}

:root{--page:#f7f4ed;--ink:#183e55;--muted:#526570;--brand:#92633b;--line:#d9d1c4;--link:#155f68;--focus:#a43b23;--word-1:#155f68;--word-2:#277b83;--word-3:#183e55;--word-4:#92633b;--word-5:#b85c39;--word-6:#5c7180}
:root[data-theme="dark"]{color-scheme:dark;--page:#17242d;--ink:#e9eef1;--muted:#afbec7;--brand:#dfb88f;--line:#3c505d;--link:#84d4cc;--focus:#ffe680;--word-1:#84d4cc;--word-2:#71bcc9;--word-3:#e0eaf2;--word-4:#dfb88f;--word-5:#efaa8d;--word-6:#a9c0d1}
body{background:var(--page);color:var(--ink)}.brand{color:var(--brand)}a{color:var(--link)}.metadata,footer{color:var(--muted)}footer{border-color:var(--line)}svg a:focus{outline-color:var(--focus)}
svg text[fill="#155f68"]{fill:var(--word-1)}svg text[fill="#277b83"]{fill:var(--word-2)}svg text[fill="#183e55"]{fill:var(--word-3)}svg text[fill="#92633b"]{fill:var(--word-4)}svg text[fill="#b85c39"]{fill:var(--word-5)}svg text[fill="#5c7180"]{fill:var(--word-6)}
svg a:hover text,svg a:focus text{fill:#183e55}a:hover,a:focus-visible{color:#183e55}
.header-top{display:flex;align-items:center;justify-content:space-between;gap:16px}.theme-switch{display:flex;gap:6px}.theme-switch[hidden]{display:none}.theme-switch button{font:16px/1 Arial,sans-serif;width:32px;height:32px;padding:0;border:1px solid var(--line);border-radius:8px;background:var(--page);color:var(--ink);cursor:pointer}.theme-switch button:hover{background:#eae5da}:root[data-theme="dark"] .theme-switch button:hover{background:#253641}.theme-switch button:focus-visible{outline:2px solid var(--focus);outline-offset:3px}
@media print{.theme-switch{display:none}:root[data-theme]{color-scheme:light;--page:#f7f4ed;--ink:#183e55;--muted:#526570;--brand:#92633b;--line:#d9d1c4;--link:#155f68;--word-1:#155f68;--word-2:#277b83;--word-3:#183e55;--word-4:#92633b;--word-5:#b85c39;--word-6:#5c7180}}
</style></head><body><main>
<header><div class="header-top"><div class="brand">CHORDSVAULT</div><div class="theme-switch" hidden><button type="button" aria-label="Switch to dark theme" title="Switch to dark theme">🌙</button></div></div><h1>Songs by artist</h1>
<p>__COUNT__ catalogue entries · Larger names indicate more songs.</p>
<p>Click an artist to open their songs. Hover or focus on a name for its song count.</p>
<p class="metadata">Updated __DATE__ · <a href="https://www.chordsvault.com/ru/artists" target="_blank" rel="noopener noreferrer">Source catalogue ↗</a></p></header>
<div class="cloud" id="cloud" role="region" aria-label="Artist word cloud" tabindex="0">__SVG__</div>
<div class="fallback" id="fallback"><details><summary>Artist list and song counts</summary><ul>__LIST__</ul></details></div>
<footer>Font size scales with the square root of song count. Names and separate catalogue entries are preserved.<br>On smaller screens, scroll across the cloud or use your browser’s zoom. This page is a snapshot; run the rebuild script to refresh it.</footer>
</main><script type="application/json" id="artist-data">__DATA__</script><script>
(() => {
  const controls = document.querySelector('.theme-switch');
  const button = controls.querySelector('button');
  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    const isDark = theme === 'dark';
    button.textContent = isDark ? '☀️' : '🌙';
    const label = isDark ? 'Switch to light theme' : 'Switch to dark theme';
    button.setAttribute('aria-label', label);
    button.setAttribute('title', label);
  }
  apply(document.documentElement.dataset.theme || 'light');
  controls.hidden = false;
  button.addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    apply(theme);
    try { localStorage.setItem('chordsvault-cloud-theme', theme); } catch (_) {}
  });
  window.addEventListener('storage', event => {
    if (event.key === 'chordsvault-cloud-theme' && (event.newValue === 'light' || event.newValue === 'dark')) apply(event.newValue);
  });
})();
</script></body></html>'''


def cloud_layout(rows, font_path=None):
    """Measure and position every artist before writing the HTML."""
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
    for i, row in enumerate(rows):
        size = round(17 * math.sqrt(row['songCount']))
        font = ImageFont.truetype(str(font_path), size)
        left, top, right, bottom = font.getbbox(row['name'], anchor='ls')
        advance = float(font.getlength(row['name']))
        words.append(dict(row, size=size, ascent=-top, left=max(0, -left),
                          w=math.ceil(max(advance, right)-min(0, left))+10,
                          h=bottom-top+10, advance=advance, color=colors[i % len(colors)]))
    if not words:
        raise ValueError('Cannot generate an empty cloud.')
    width = max(3600, max(word['w']+140 for word in words))
    area = sum(word['w']*word['h'] for word in words)
    height = max(2100, math.ceil(area/(width*.42)))
    for _ in range(10):
        seed = 25
        def random():
            nonlocal seed
            seed = (seed*1664525+1013904223) & 0xffffffff
            return seed/4294967296
        grid, placed = {}, []
        for word in words:
            for attempt in range(6000):
                spread = min(1, .5+attempt/900)
                x = round(width/2+(random()-.5)*(width-120-word['w'])*spread-word['w']/2)
                y = round(height/2+(random()-.5)*(height-80-word['h'])*spread-word['h']/2)
                if x < 40 or y < 30 or x+word['w'] > width-40 or y+word['h'] > height-30:
                    continue
                keys = [(gx, gy) for gx in range(x//96, (x+word['w'])//96+1)
                        for gy in range(y//96, (y+word['h'])//96+1)]
                if any(x < other['x']+other['w'] and x+word['w'] > other['x']
                       and y < other['y']+other['h'] and y+word['h'] > other['y']
                       for key in keys for other in grid.get(key, [])):
                    continue
                item = dict(word, x=x, y=y)
                placed.append(item)
                for key in keys:
                    grid.setdefault(key, []).append(item)
                break
            else:
                break
        if len(placed) == len(words):
            text_top = min(word['y']+5 for word in placed)
            text_bottom = max(word['y']+word['h']-5 for word in placed)
            view_top = text_top*2/3
            view_bottom = height-(height-text_bottom)*2/3
            return placed, (0, view_top, width, view_bottom-view_top)
        width, height = math.ceil(width*1.1), math.ceil(height*1.1)
    raise ValueError('Unable to fit all artists; previous HTML has not been replaced.')


def render_svg(rows, font_path=None):
    placed, view = cloud_layout(rows, font_path)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" '
             'viewBox="{}" width="{}" height="{}" '
             'aria-label="{} artists sized by song count" '
             'font-family="Arial, DejaVu Sans, sans-serif" font-weight="700">'.format(
                 ' '.join(f'{n:.3f}' for n in view), view[2], round(view[3], 3), len(rows))]
    for word in placed:
        label = html.escape(f"{word['name']}: {word['songCount']} songs", quote=True)
        highlight = '<rect class="hover-highlight" x="{}" y="{}" width="{}" height="{}" rx="3"/>'.format(
            word['x'], word['y'], word['w'], word['h'])
        parts.append('<a href="{}" target="_blank" rel="noopener noreferrer" tabindex="0" aria-label="{}">'
                     '<title>{}</title>{}<text x="{}" y="{}" font-size="{}" fill="{}" '
                     'textLength="{:.3f}" lengthAdjust="spacingAndGlyphs">{}</text></a>'.format(
                         html.escape(word['url'], quote=True), label, label, highlight,
                         word['x']+5+word['left'], word['y']+5+word['ascent'],
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
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent.parent / 'chordsvault-word-cloud.html',
                        help='HTML output path (default: parent of the scripts folder)')
    parser.add_argument('--data-output', type=Path, help='Optional JSON snapshot path')
    parser.add_argument('--font', type=Path, help='Optional TrueType/OpenType font file with the required characters')
    args = parser.parse_args()
    try:
        if args.data_output and args.output.resolve() == args.data_output.resolve():
            raise ValueError('HTML and JSON outputs must use different paths.')
        rows = fetch_artists()
        timestamp = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        page = render_html(rows, timestamp, args.font)
        if args.data_output:
            atomic_write(args.data_output, json.dumps({'source': SOURCE, 'api': API,
                         'retrieved': timestamp, 'entries': rows}, ensure_ascii=False, indent=2))
        path = atomic_write(args.output, page)
        print(f'Created {path} ({len(rows)} artists). Open this file in your browser.')
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f'Rebuild failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
