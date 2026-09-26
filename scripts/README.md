# Rebuild the ChordsVault word cloud

Requires **Python 3.9 or newer** and **Pillow** for font measurement. No API keys or account are needed.

One-time setup (run in this folder):

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install Pillow
```

Activate this environment before running the script on later occasions. On Windows,
use `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

## Run

Open a terminal in this folder and run:

```sh
python3 rebuild_word_cloud.py
```

On Windows, use `py -3` in place of `python3`.

The script downloads the current public artist catalogue and replaces
`chordsvault-word-cloud.html` in the project root with the command above.
Without `--output`, the default file is written in the parent of the `scripts` folder. Open that file in a browser.
Run the same command whenever you want fresh data, then reload the HTML page.

To choose a destination and also save the downloaded counts:

```sh
python3 rebuild_word_cloud.py --output ./updated-cloud.html --data-output ./counts.json
```

Paths containing spaces must be quoted. The script can be run from any folder;
its default HTML output always goes in the parent of the `scripts` folder.

## What it does

- Reads `https://www.chordsvault.com/api/artists`, the public data endpoint used by
  `https://www.chordsvault.com/ru/artists`.
- Follows pagination using the server's actual page size; there is no fixed artist count.
- Preserves catalogue names, separate entries, and artist slugs. Each cloud link
  uses `https://www.chordsvault.com/ru/artists/` plus the URL-encoded source slug.
- Sizes names by the square root of their song count, retaining the original palette.
- Computes the complete layout in Python and embeds a static SVG in a single HTML
  file. The cloud is visible without JavaScript, including in Finder Quick Look.
  Every artist also appears in an accessible HTML list.
- Expands the cloud canvas if needed to fit all artists. The layout is fixed at generation time; counts and links are preserved.
- Keeps artist labels inside an oval boundary, leaving the corners clear.
- Includes the retrieval time in UTC. Reopening the page does not contact the API.
- Checks for missing pages, duplicate artist identifiers and changing catalogue totals.
  A failed download leaves the existing HTML untouched. Retry if the catalogue changed.

An internet connection is needed to rebuild the page or follow artist links.
The generated cloud works offline and does not require JavaScript. Both the cloud
and the artist list contain normal clickable links. The reduced vertical margins
are preserved. Use `--font /path/to/font.ttf` to select a font if automatic font
detection cannot find Arial Bold, DejaVu Sans Bold, or Liberation Sans Bold.

## Contributors word cloud

Using the same Python environment, run from this folder:

```sh
python3 rebuild_contributors_word_cloud.py --data-output contributor-song-counts.json
```

This creates `../chordsvault-contributors-cloud.html` by default,
using the compact layout and the artist cloud’s palette and bold font. It reads the complete public list from
`https://www.chordsvault.com/api/songs/contributors`, the endpoint used by
`https://www.chordsvault.com/en/contributors`.

Display names are preserved. Accounts are identified by `userId`, so duplicate
display names remain separate. Links filter songs by contributor ID. The script
rejects empty responses, invalid counts, and duplicate IDs before replacing the
HTML. The endpoint currently returns an unpaginated array; a changed response
format fails explicitly. Supported options are `--output`, `--data-output`, and
`--font`. The generated file works offline without JavaScript. Run the command
again to refresh the counts.

The script generates only the compact layout, with 12–116 px square-root sizing.
All contributor names and song links are retained.
Hovered or focused names have a yellow background highlight without an underline.
The compact canvas uses a 4:3 landscape ratio, expanding both dimensions together
when needed to fit every name while retaining the font sizes.
Compact titles use 94% of their measured horizontal text length. Each title
stays centered in its original placement box, turning the saved width into
extra horizontal padding without changing the overall cloud dimensions.
Vertical padding is 5.3 px above and below each compact title (6% more than 5 px).
The compact font size in pixels is
`round(12 + 104 * (sqrt(songCount) - 1) / max(1, sqrt(highestCount) - 1))`.
One-song contributors use 12 px, while the highest count uses 116 px (when
the highest count is at least four). This increases the visual contrast
between occasional and prolific contributors.

## Light and dark themes

Both clouds include one theme toggle in the header: 🌙 on a light background
in light mode, and ☀️ on a dark background in dark mode. Clicking it switches
to the opposite theme. The initial theme follows
the system appearance unless a choice was previously saved. Your choice is
saved in browser storage when available; storage restrictions do not prevent
switching themes. Dark mode uses lighter text colors and retains the yellow
link highlights. Printing uses the light palette. The clouds remain readable
without JavaScript; only the theme controls require JavaScript.

## Hosted page

This script regenerates a local HTML file. It does **not** modify or redeploy the
previously hosted Sites page. To update a website, upload/publish the regenerated
HTML using that website's hosting workflow (often as `index.html`).

## Troubleshooting

- `python3: command not found`: install Python 3.9+ or use an existing Python installation.
- Certificate verification errors: repair your Python installation's trusted certificates.
  For Python installed with the macOS python.org installer, use its bundled
  **Install Certificates.command**. Do not disable certificate verification.
- Network, rate-limit, or server errors: try again later. Transient errors are retried
  up to three times per page.
- `Unexpected artist API response`: ChordsVault may have changed its API. The script
  fails explicitly instead of generating an incomplete cloud.
