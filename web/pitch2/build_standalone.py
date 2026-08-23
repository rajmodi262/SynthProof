"""Builds the pitch deck as ONE self-contained HTML file.

The result is a single file you can double-click, email, or carry on a pendrive. It needs no
Node, no dev server, and no internet: the JavaScript, the stylesheet, every font, and every
committed number live inside the page.

Opening a page from disk is stricter than serving it, and two rules shape this build:

  * A page loaded over file:// has an opaque origin, so it cannot FETCH anything. Every
    `src=` and `href=` therefore has to be inlined or turned into a data: URI — including
    the woff2 fonts, which is what SYNTHPROOF_INLINE_ALL=1 arranges.
  * Module scripts are subject to CORS. Rather than depend on how a given browser classifies
    an inline module on an opaque origin, the standalone build is emitted as a classic IIFE
    and inlined as a plain `<script>`. A classic inline script has no CORS question at all.

Run from the repository root:

    python web/pitch2/build_standalone.py

Writes `SynthProof-Pitch-Cinematic.html` beside the SynthProof folder. The normal served build in
`synthproof/api/pitch/` is rebuilt as a side effect; re-run a plain `vite build` if you want
the module version back there.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB = HERE.parent
REPO = WEB.parent
# The "outermost folder": the directory CONTAINING the repo, beside Start Pitch Deck.bat.
OUT = REPO.parent / "SynthProof-Pitch-Cinematic.html"
DIST = REPO / "synthproof" / "api" / "pitch2"


def run_build() -> None:
    env = {**os.environ, "SYNTHPROOF_INLINE_ALL": "1"}
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx is None:
        sys.exit("npx not found on PATH. Install Node.js and try again.")
    proc = subprocess.run(
        [npx, "vite", "build", "--config", "pitch2/vite.config.ts"],
        cwd=WEB,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        sys.exit("vite build failed")


def inline() -> str:
    html = (DIST / "index.html").read_text(encoding="utf-8")

    def asset(src: str) -> str:
        # Vite emits root-absolute hrefs like "/assets/index-xxxx.js".
        return (DIST / src.lstrip("/")).read_text(encoding="utf-8")

    # Stylesheet -> <style>, if one was emitted. The IIFE build injects its CSS from inside
    # the bundle rather than emitting a file, so finding zero links here is expected.
    def sub_css(m: "re.Match[str]") -> str:
        return "<style>\n" + asset(m.group(1)) + "\n</style>"

    html, _ = re.subn(r'<link[^>]*rel="stylesheet"[^>]*href="([^"]+)"[^>]*>', sub_css, html)

    # Script -> inline CLASSIC script.
    #
    # Vite stamps type="module" on the entry tag even when rollup is emitting an IIFE, so the
    # attribute is dropped here on purpose: the bundle has no import/export and runs fine as
    # a classic script, which is the form with no CORS question when opened from disk.
    #
    # `</script>` inside a string literal in the bundle would close the tag early, so that
    # sequence is the one thing that must be escaped.
    #
    # The tag is also RELOCATED to the end of <body>. `type="module"` implies defer, so the
    # original tag could sit in <head> and still run after the DOM existed. A classic script
    # has no such implication and executes the moment it is parsed — in <head> that is before
    # `<div id="pitch-root">` exists, and React dies with "target container is not a DOM
    # element". Inlining in place produced exactly that, and a blank deck.
    captured: list[str] = []

    def take_js(m: "re.Match[str]") -> str:
        code = asset(m.group(1)).replace("</script>", "<\\/script>")
        captured.append("<script>\n" + code + "\n</script>")
        return ""

    html, n_js = re.subn(r'<script[^>]*src="([^"]+)"[^>]*></script>', take_js, html)
    if n_js != 1:
        sys.exit(f"expected exactly one script to inline, found {n_js}")

    if "</body>" not in html:
        sys.exit("no </body> to place the script before")
    html = html.replace("</body>", f"  {captured[0]}\n  </body>", 1)

    if 'type="module"' in html:
        sys.exit(
            "a module script survived into the standalone build; it must be a classic script "
            "or a double-clicked file:// page may refuse to run it"
        )

    # The stylesheet and fonts must have arrived by one route or the other. Checking beats
    # discovering an unstyled deck on the projector.
    for probe in (".pulse-svg", ".fy-stage", ".batt-fill", "@font-face", "data:font/woff2"):
        if probe not in html:
            sys.exit(f"standalone build is missing {probe!r} — stylesheet or fonts dropped")

    banner = (
        "<!--\n"
        "  SynthProof - pitch deck, single file.\n"
        "  Double-click to open. No internet, no server, no install needed.\n"
        "  Keys:  arrows / space = move   1-9,0 = jump   Esc = overview   N = speaker notes\n"
        "  Rebuild:  python web/pitch2/build_standalone.py\n"
        "-->\n"
    )
    return banner + html


def main() -> None:
    print("building (fonts inlined, classic script)...")
    run_build()
    html = inline()
    OUT.write_text(html, encoding="utf-8")

    size_mb = len(html.encode("utf-8")) / 1_048_576
    print(f"wrote {OUT}")
    print(f"  {size_mb:.2f} MB, fully self-contained")

    # A single surviving external reference would fail silently on the day.
    stray = re.findall(r'(?:src|href)="(?!data:|#)([^"]+)"', html)
    if stray:
        print(f"  WARNING: {len(stray)} external reference(s) remain: {stray[:5]}")
    else:
        print("  no external references — verified")


if __name__ == "__main__":
    main()
