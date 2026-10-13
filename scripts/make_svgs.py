"""Builds every image in the profile README, in light and dark, and the README itself.

Usage (from the repo root): python -I scripts/make_svgs.py . scripts/media <inter_variable_woff2> <cascadia_mono_ttf>
(Inter: @fontsource-variable/inter, files/inter-latin-wght-normal.woff2. Cascadia Mono: CascadiaMono.ttf, OFL.)

<media_dir> holds what gets embedded: logo-*.png (96 px), shot-*.webp (project screenshots,
16:10) and icons/*.svg (Simple Icons, one path each). Fonts are instanced from the variable
files, subset to the glyphs each SVG uses and embedded as WOFF2, so text looks the same on
every OS and every width is measured from the real font. The numbers in the copy (629 tests,
36 tables...) are plain text below: edit them here and rerun.
"""
import base64
import io
import os
import re
import sys
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

REPO, MEDIA, INTER, CASCADIA = sys.argv[1:5]
ASSETS = os.path.join(REPO, "assets")
RAW = "https://raw.githubusercontent.com/Sanjaycodes019/Sanjaycodes019/main/assets"
SITE = "https://guptasanjay.com.np"

# =========================================================================== fonts
_static, _metrics = {}, {}


def static_font(path, wght):
    key = (path, wght)
    if key not in _static:
        font = instancer.instantiateVariableFont(TTFont(path), {"wght": wght})
        font.flavor = None
        buf = io.BytesIO()
        font.save(buf)
        _static[key] = buf.getvalue()
    return TTFont(io.BytesIO(_static[key]))


def measure(text, size, wght=500, spacing=0.0, path=None):
    path = path or INTER
    key = (path, wght)
    if key not in _metrics:
        font = static_font(path, wght)
        _metrics[key] = (font.getBestCmap(), {g: m[0] for g, m in font["hmtx"].metrics.items()}, font["head"].unitsPerEm)
    cmap, adv, upm = _metrics[key]
    width = 0
    for ch in text:
        glyph = cmap.get(ord(ch))
        if glyph is None:
            raise SystemExit(f"missing glyph {ch!r} ({os.path.basename(path)} {wght})")
        width += adv[glyph]
    return width * size / upm + spacing * len(text)


def font_face(path, wght, family, text):
    font = static_font(path, wght)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt"]
    opts.notdef_outline = True
    opts.name_IDs = [0, 1, 2, 13, 14]
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(set(text + " "))))
    sub.subset(font)
    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';font-weight:{wght};src:url(data:font/woff2;base64,{data}) format('woff2');}}"


def esc(s):
    return escape(s, {'"': "&quot;"})


def wrap(s, size, wght, maxw):
    lines, cur = [], ""
    for word in s.split(" "):
        cand = f"{cur} {word}".strip()
        if not cur or measure(cand, size, wght) <= maxw:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def truncate(s, size, wght, maxw):
    if measure(s, size, wght) <= maxw:
        return s
    while s and measure(s.rstrip(" ,·:") + "…", size, wght) > maxw:
        s = s[:-1]
    return s.rstrip(" ,·:") + "…"


def data_uri(path, mime):
    with open(path, "rb") as fh:
        return f"data:{mime};base64," + base64.b64encode(fh.read()).decode()


SANS = "'InterEmbed', 'Inter', 'Segoe UI', -apple-system, Helvetica, Arial, sans-serif"
MONO = "'CascadiaEmbed', 'Cascadia Mono', ui-monospace, SFMono-Regular, Consolas, Menlo, monospace"


class Doc:
    """One SVG: collects the text it draws per font weight, so only those glyphs get embedded."""

    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.used, self.defs, self.parts, self.css = {}, [], [], []
        self._id = 0

    def uid(self, prefix):
        self._id += 1
        return f"{prefix}{self._id}"

    def text(self, x, y, s, size, wght, fill, anchor=None, spacing=None, mono=False, extra=""):
        fam = "mono" if mono else "sans"
        self.used.setdefault((fam, wght), []).append(s)
        attrs = f' text-anchor="{anchor}"' if anchor else ""
        attrs += f' letter-spacing="{spacing}"' if spacing is not None else ""
        attrs += ' class="m"' if mono else ""
        return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{wght}" fill="{fill}"{attrs}{extra}>{esc(s)}</text>'

    def spans(self, x, y, size, pieces, extra=""):
        """pieces: (text, wght, fill) drawn as one line of tspans."""
        out = []
        for s, wght, fill in pieces:
            self.used.setdefault(("sans", wght), []).append(s)
            out.append(f'<tspan font-weight="{wght}" fill="{fill}">{esc(s)}</tspan>')
        return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}"{extra} xml:space="preserve">{"".join(out)}</text>'

    def add(self, *parts):
        self.parts.extend(parts)

    def render(self):
        faces = []
        for (fam, wght), texts in sorted(self.used.items()):
            path, name = (CASCADIA, "CascadiaEmbed") if fam == "mono" else (INTER, "InterEmbed")
            faces.append(font_face(path, wght, name, "".join(texts)))
        css = "".join(faces) + f"text{{font-family:{SANS};}}.m{{font-family:{MONO};white-space:pre;}}" + "".join(self.css)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h:.0f}" viewBox="0 0 {self.w} {self.h:.0f}" role="img" aria-label="{esc(self.title)}">'
            f"<title>{esc(self.title)}</title><defs>{''.join(self.defs)}</defs><style>{css}</style>{''.join(self.parts)}</svg>"
        )


# =========================================================================== themes
THEMES = {
    "dark": dict(
        card="#0B1120", card2="#111827", border="#1E293B", heading="#F8FAFC", text="#CBD5E1",
        muted="#94A3B8", faint="#64748B", indigo="#818CF8", grid="#94A3B8", gridOp=0.075,
        glow1="#6366F1", glow1Op=0.34, glow2="#8B5CF6", glow2Op=0.22, chip="#0F172A",
        chipBorder="#243047", green="#34D399", amber="#FBBF24", greenBgOp=0.10,
        grad=("#818CF8", "#8B5CF6", "#C4B5FD"), tile="#161B26", tileBorder="#273244",
        btn="#151B23", btnBorder="#30363D", btnText="#E6EDF3", btnMuted="#7D8590", tintOp=0.16,
        ed="#0D1117", edBar="#161B22", edBorder="#30363D", edTab="#0D1117", gutter="#3D4654",
        kw="#C4B5FD", name="#93C5FD", prop="#A5B4FC", str="#86EFAC", punc="#8B949E", status="#4F46E5",
        statusText="#E0E7FF", mini="#30363D", line="#1E293B", darkGlyph="#E6EDF3",
    ),
    "light": dict(
        card="#F8FAFC", card2="#FFFFFF", border="#D8DEE8", heading="#0F172A", text="#334155",
        muted="#64748B", faint="#94A3B8", indigo="#4F46E5", grid="#0F172A", gridOp=0.055,
        glow1="#818CF8", glow1Op=0.30, glow2="#C4B5FD", glow2Op=0.40, chip="#FFFFFF",
        chipBorder="#E2E8F0", green="#047857", amber="#B45309", greenBgOp=0.10,
        grad=("#4F46E5", "#7C3AED", "#8B5CF6"), tile="#FFFFFF", tileBorder="#E2E8F0",
        btn="#F6F8FA", btnBorder="#D0D7DE", btnText="#1F2328", btnMuted="#59636E", tintOp=0.12,
        ed="#FFFFFF", edBar="#F6F8FA", edBorder="#D0D7DE", edTab="#FFFFFF", gutter="#A0A8B3",
        kw="#7C3AED", name="#2563EB", prop="#4F46E5", str="#15803D", punc="#6E7781", status="#4F46E5",
        statusText="#FFFFFF", mini="#D8DEE4", line="#E2E8F0", darkGlyph=None,
    ),
}


def card_bg(doc, t, rx=22, glow=None, grid=False):
    """Rounded card with the indigo hairline; optional grid and a soft corner glow."""
    w, h = doc.w, doc.h
    clip, hair, blur = doc.uid("clip"), doc.uid("hair"), doc.uid("blur")
    doc.defs.append(
        f'<clipPath id="{clip}"><rect width="{w}" height="{h:.0f}" rx="{rx}"/></clipPath>'
        f'<linearGradient id="{hair}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["border"]}"/>'
        f'<stop offset="0.5" stop-color="#6366F1" stop-opacity="0.7"/><stop offset="1" stop-color="{t["border"]}"/></linearGradient>'
        f'<filter id="{blur}" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="60"/></filter>'
    )
    doc.add(f'<g clip-path="url(#{clip})"><rect width="{w}" height="{h:.0f}" fill="{t["card"]}"/>')
    if grid:
        pat, fade, mask = doc.uid("grid"), doc.uid("fade"), doc.uid("mask")
        doc.defs.append(
            f'<pattern id="{pat}" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{t["grid"]}" stroke-opacity="{t["gridOp"]}"/></pattern>'
            f'<radialGradient id="{fade}" cx="0.45" cy="0.4" r="0.75"><stop offset="0" stop-color="#fff"/><stop offset="0.7" stop-color="#fff" stop-opacity="0.5"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
            f'<mask id="{mask}"><rect width="{w}" height="{h:.0f}" fill="url(#{fade})"/></mask>'
        )
        doc.add(f'<rect width="{w}" height="{h:.0f}" fill="url(#{pat})" mask="url(#{mask})"/>')
    if glow:
        cx, cy, r, color, op = glow
        doc.add(f'<circle class="glow" cx="{cx}" cy="{cy}" r="{r}" fill="{color}" fill-opacity="{op}" filter="url(#{blur})"/>')
    return hair, rx


def card_end(doc, hair, rx):
    doc.add("</g>", f'<rect x="0.75" y="0.75" width="{doc.w - 1.5}" height="{doc.h - 1.5:.1f}" rx="{rx - 0.75}" fill="none" stroke="url(#{hair})" stroke-width="1.5"/>')


def logo(doc, key, x, y, size, t, rx=None):
    rx = rx if rx is not None else size * 0.27
    clip = doc.uid("lg")
    doc.defs.append(f'<clipPath id="{clip}"><rect x="{x}" y="{y}" width="{size}" height="{size}" rx="{rx}"/></clipPath>')
    uri = data_uri(os.path.join(MEDIA, f"logo-{key}.png"), "image/png")
    return (
        f'<image href="{uri}" x="{x}" y="{y}" width="{size}" height="{size}" clip-path="url(#{clip})"/>'
        f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="{rx}" fill="none" stroke="{t["chipBorder"]}"/>'
    )


def chip_row(doc, x, y, items, t, size=13.5, maxw=10_000, gap=8, h=28):
    """Tech chips that wrap onto new rows; returns the y below the last row."""
    cx, cy = x, y
    for label in items:
        w = measure(label, size, 600) + 24
        if cx + w > x + maxw and cx > x:
            cx, cy = x, cy + h + gap
        doc.add(
            f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{t["chip"]}" stroke="{t["chipBorder"]}"/>',
            doc.text(cx + 12, cy + h / 2 + size * 0.36, label, size, 600, t["text"]),
        )
        cx += w + gap
    return cy + h


# =========================================================================== icons
STROKE = 'fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
SIMPLE = {}
for name in os.listdir(os.path.join(MEDIA, "icons")):
    with open(os.path.join(MEDIA, "icons", name), encoding="utf-8") as fh:
        SIMPLE[name[:-4]] = re.search(r'd="([^"]+)"', fh.read()).group(1)
# Simple Icons brand colours (badges swap the darkest ones for a neutral, so they live here).
BRAND = {
    "typescript": "#3178C6", "javascript": "#F7DF1E", "cplusplus": "#00599C", "python": "#3776AB",
    "react": "#61DAFB", "tailwindcss": "#06B6D4", "redux": "#764ABC", "vite": "#9135FF", "mui": "#007FFF",
    "reactquery": "#FF4154", "expo": "#000020", "capacitor": "#119EFF", "android": "#3DDC84",
    "nodedotjs": "#5FA04E", "express": "#000000", "supabase": "#3FCF8E", "fastapi": "#009688",
    "socketdotio": "#010101", "postgresql": "#4169E1", "mongodb": "#47A248", "mysql": "#4479A1",
    "jest": "#C21325", "githubactions": "#2088FF", "docker": "#2496ED", "vercel": "#000000",
    "render": "#000000", "sentry": "#362D59", "postman": "#FF6C37", "git": "#F03C2E", "github": "#181717",
}


def brand_color(key, t):
    c = BRAND[key]
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    if t["darkGlyph"] and 0.2126 * r + 0.7152 * g + 0.0722 * b < 70:
        return t["darkGlyph"]
    return c


LINKEDIN_PATH = (
    "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046"
    "c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 1 1 0-4.125 2.062 2.062 0 0 1 0 4.125z"
    "M7.119 20.452H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271"
    "V1.729C24 .774 23.2 0 22.222 0h.003z"
)
# Lucide-style line icons (ISC), 24x24.
LINE = {
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.6 3.9 5.6 3.9 9s-1.3 6.4-3.9 9c-2.6-2.6-3.9-5.6-3.9-9S9.4 5.6 12 3z"/>',
    "doc": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m4 7 8 6 8-6"/>',
    "book": '<path d="M2 4h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2zM22 4h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7z"/>',
    "pen": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "rss": '<path d="M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/>',
    "play": '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="m10 9 5 3-5 3z"/>',
    "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22M18 2H6v7a6 6 0 0 0 12 0z"/>',
    "medal": '<path d="M7.2 2h9.6l-3.3 7.2h-3z"/><circle cx="12" cy="15.5" r="6"/><path d="M12 13v5"/>',
    "rocket": '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09zM12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2zM9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    "code": '<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
    "sigma": '<path d="M18 7V4H6l6 8-6 8h12v-3"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "arrow": '<path d="M7 17 17 7M9 7h8v8"/>',
    "pin": '<path d="M12 21s-7-6.1-7-11.5a7 7 0 0 1 14 0C19 14.9 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    "cap": '<path d="M22 9 12 4 2 9l10 5 10-5z"/><path d="M6 11v5c0 1.7 2.7 3 6 3s6-1.3 6-3v-5"/>',
    "bag": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 13h18"/>',
}


def icon(kind, key, c, x, y, size):
    s = size / 24
    if kind == "line":
        return f'<g transform="translate({x:.1f} {y:.1f}) scale({s:.4f})" {STROKE.format(c=c)}>{LINE[key]}</g>'
    path = LINKEDIN_PATH if key == "linkedin" else SIMPLE[key]
    return f'<g transform="translate({x:.1f} {y:.1f}) scale({s:.4f})"><path fill="{c}" d="{path}"/></g>'


# =========================================================================== hero
HERO_W, HERO_H, PAD = 1000, 432, 48
STATUS = "Open to internships · until Jan 2027"
PHRASES = [
    "Tech Lead at Duleko · web + Android on Google Play",
    "Building FLITO · freight matching for Nepal",
    "629 automated tests · business rules in Postgres",
    "Joining EPAM Systems · January 2027",
]
HERO_CHIPS = [("duleko", "Tech Lead at ", "Duleko"), ("flito", "Building ", "FLITO"), ("epam", "Joining ", "EPAM · Jan 2027")]
HERO_STATS = [
    ("629", "automated tests", "FLITO · Jest + CI"),
    ("36", "tables under RLS", "Duleko · PostgreSQL"),
    ("300+", "DSA problems", "LeetCode + GfG"),
]


def hero(theme):
    t = THEMES[theme]
    doc = Doc(HERO_W, HERO_H, "Sanjay Gupta, Full-Stack Software Engineer: Tech Lead at Duleko, building FLITO, joining EPAM Systems in January 2027")
    hair, rx = card_bg(doc, t, rx=24, grid=True)
    blur = doc.uid("hb")
    doc.defs.append(f'<filter id="{blur}" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="64"/></filter>')
    doc.add(
        f'<g filter="url(#{blur})"><circle class="g1" cx="840" cy="40" r="230" fill="{t["glow1"]}" fill-opacity="{t["glow1Op"]}"/>'
        f'<circle class="g2" cx="110" cy="450" r="200" fill="{t["glow2"]}" fill-opacity="{t["glow2Op"]}"/></g>'
    )
    # monogram + domain, status pill
    doc.add(
        f'<rect x="{PAD}" y="42" width="46" height="46" rx="13" fill="{t["chip"]}" stroke="{t["chipBorder"]}" stroke-width="1.5"/>',
        doc.text(PAD + 23, 71.5, "SG", 17, 800, t["heading"], anchor="middle"),
        doc.spans(PAD + 62, 72, 19, [("guptasanjay", 700, t["heading"]), (".com.np", 500, t["muted"])]),
    )
    pill_w = 16 + 10 + 10 + measure(STATUS, 15, 600) + 18
    px = HERO_W - PAD - pill_w
    doc.add(
        f'<rect x="{px:.1f}" y="47" width="{pill_w:.1f}" height="36" rx="18" fill="{t["green"]}" fill-opacity="{t["greenBgOp"]}" stroke="{t["green"]}" stroke-opacity="0.35"/>'
        f'<circle class="ping" cx="{px + 21:.1f}" cy="65" r="5" fill="{t["green"]}"/><circle cx="{px + 21:.1f}" cy="65" r="5" fill="{t["green"]}"/>',
        doc.text(px + 36, 70.2, STATUS, 15, 600, t["green"]),
    )
    # eyebrow + name
    bar = doc.uid("bar")
    doc.defs.append(f'<linearGradient id="{bar}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#6366F1"/><stop offset="1" stop-color="#A78BFA"/></linearGradient>')
    doc.add(
        f'<rect x="{PAD}" y="146" width="32" height="3" rx="1.5" fill="url(#{bar})"/>',
        doc.text(PAD + 44, 153, "FULL-STACK SOFTWARE ENGINEER", 16.5, 700, t["indigo"], spacing=2.6),
    )
    size, spacing = 92, -2.4
    while measure("Sanjay Gupta", size, 800, spacing) > 600:
        size -= 1
        spacing = -2.4 * size / 92
    first_w = measure("Sanjay ", size, 800, spacing)
    last_w = measure("Gupta", size, 800, spacing)
    lx = PAD - 3
    g1, g2, g3 = t["grad"]
    name = doc.uid("name")
    doc.defs.append(
        f'<linearGradient id="{name}" gradientUnits="userSpaceOnUse" x1="{lx + first_w:.1f}" y1="0" x2="{lx + first_w + last_w:.1f}" y2="0">'
        f'<stop offset="0" stop-color="{g1}"/><stop offset="0.6" stop-color="{g2}"/><stop offset="1" stop-color="{g3}"/></linearGradient>'
    )
    doc.add(doc.spans(lx, 240, size, [("Sanjay ", 800, t["heading"]), ("Gupta", 800, f"url(#{name})")], extra=f' letter-spacing="{spacing:.2f}"'))
    # typing line
    ty, tsize, tx = 294, 23, PAD + 24
    doc.add(doc.text(PAD, ty, "›", tsize, 700, t["indigo"]))
    n, slot = len(PHRASES), 100 / len(PHRASES)
    caret = []
    for i, phrase in enumerate(PHRASES):
        pw = measure(phrase, tsize, 500)
        s, type_end, hold_end, eps, steps = i * slot, i * slot + slot * 0.36, i * slot + slot * 0.94, 0.01, len(phrase)
        doc.defs.append(f'<clipPath id="c{i}"><rect class="r{i}" x="{tx}" y="{ty - 24}" width="{pw + 2:.1f}" height="34"/></clipPath>')
        doc.add(doc.text(tx, ty, phrase, tsize, 500, t["text"], extra=f' class="p p{i}" clip-path="url(#c{i})"'))
        doc.css.append(
            f"@keyframes v{i}{{0%{{opacity:{1 if i == 0 else 0}}}"
            + (f"{s - eps:.2f}%{{opacity:0}}{s:.2f}%{{opacity:1}}" if i else "")
            + f"{hold_end:.2f}%{{opacity:1}}{s + slot - eps:.2f}%,100%{{opacity:0}}}}"
            f"@keyframes w{i}{{0%,{s:.2f}%{{transform:scaleX(0);animation-timing-function:steps({steps},end)}}{type_end:.2f}%,100%{{transform:scaleX(1)}}}}"
            f".p{i}{{animation:v{i} 18s infinite}}.r{i}{{animation:w{i} 18s infinite;transform-box:fill-box;transform-origin:left center}}"
        )
        caret.append(
            f"{s:.2f}%{{transform:translateX(0);animation-timing-function:steps({steps},end)}}"
            f"{type_end:.2f}%{{transform:translateX({pw + 3:.1f}px)}}{s + slot - eps:.2f}%{{transform:translateX({pw + 3:.1f}px)}}"
        )
    doc.add(f'<g class="cm"><rect class="caret" x="{tx}" y="{ty - 20}" width="2.6" height="25" rx="1.3" fill="{t["indigo"]}"/></g>')
    # stats
    sx, sw, sy, sh, gap = 700, 252, 116, 64, 11
    for i, (num, label, source) in enumerate(HERO_STATS):
        y = sy + i * (sh + gap)
        nw = measure(num, 28, 800, -0.5)
        room = sw - 18 - nw - 10 - 14
        for txt, wt, fz in ((label, 600, 16.5), (source, 500, 13.5)):
            if measure(txt, fz, wt) > room:
                raise SystemExit(f"hero stat too wide: {txt!r}")
        doc.add(
            f'<rect x="{sx}" y="{y}" width="{sw}" height="{sh}" rx="14" fill="{t["card2"]}" fill-opacity="0.78" stroke="{t["chipBorder"]}" stroke-width="1.2"/>',
            doc.text(sx + 18, y + 42, num, 28, 800, t["heading"], spacing=-0.5),
            doc.text(sx + 28 + nw, y + 28, label, 16.5, 600, t["text"]),
            doc.text(sx + 28 + nw, y + 48, source, 13.5, 500, t["faint"]),
        )
    # chips
    cx, cy, ch = PAD, 340, 48
    for key, pre, bold in HERO_CHIPS:
        cw = 9 + 30 + 11 + measure(pre, 17, 500) + measure(bold, 17, 700) + 18
        doc.add(
            f'<rect x="{cx:.1f}" y="{cy}" width="{cw:.1f}" height="{ch}" rx="{ch / 2}" fill="{t["chip"]}" fill-opacity="0.9" stroke="{t["chipBorder"]}" stroke-width="1.2"/>',
            logo(doc, key, cx + 9, cy + 9, 30, t, rx=8),
            doc.spans(cx + 50, cy + 30, 17, [(pre, 500, t["muted"]), (bold, 700, t["heading"])]),
        )
        cx += cw + 12
    if cx - 12 > HERO_W - PAD:
        raise SystemExit("hero chips too wide")
    card_end(doc, hair, rx)
    first = measure(PHRASES[0], tsize, 500) + 3
    doc.css.append(
        ".g1{animation:d1 14s ease-in-out infinite alternate}.g2{animation:d2 18s ease-in-out infinite alternate}"
        "@keyframes d1{to{transform:translate(-90px,40px)}}@keyframes d2{to{transform:translate(110px,-30px)}}"
        ".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.2s cubic-bezier(0,0,.2,1) infinite}"
        "@keyframes ping{0%{transform:scale(1);opacity:.7}80%,100%{transform:scale(2.6);opacity:0}}"
        ".cm{animation:cm 18s infinite}@keyframes cm{" + "".join(caret) + "}"
        ".caret{animation:blink 1s steps(2,start) infinite}@keyframes blink{to{visibility:hidden}}"
        f"@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.p{{opacity:0}}.p0{{opacity:1}}.cm{{transform:translateX({first:.1f}px)}}}}"
    )
    return doc.render()


# =========================================================================== section headers
SECTIONS = {
    "about": ("01", "ABOUT", "About me"),
    "now": ("02", "RIGHT NOW", "What I'm working on"),
    "projects": ("03", "PROJECTS", "Featured projects"),
    "stack": ("04", "STACK", "Tools I ship with"),
    "wins": ("05", "ACHIEVEMENTS", "Wins & milestones"),
    "writing": ("06", "WRITING", "Latest from the blog"),
    "activity": ("07", "ACTIVITY", "On GitHub"),
}


def section(theme, key):
    t = THEMES[theme]
    num, eyebrow, title = SECTIONS[key]
    doc = Doc(1000, 96, f"{num} · {title}")
    pw = measure(num, 13, 700) + 22
    tw = measure(title, 36, 800, -0.8)
    line = doc.uid("ln")
    doc.defs.append(f'<linearGradient id="{line}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#6366F1" stop-opacity="0.75"/><stop offset="1" stop-color="#6366F1" stop-opacity="0"/></linearGradient>')
    doc.add(
        f'<rect x="1" y="6" width="{pw:.1f}" height="26" rx="13" fill="#6366F1" fill-opacity="{t["tintOp"]}" stroke="#6366F1" stroke-opacity="0.35"/>',
        doc.text(1 + pw / 2, 23.6, num, 13, 700, t["indigo"], anchor="middle"),
        doc.text(pw + 14, 24, eyebrow, 13.5, 700, t["indigo"], spacing=2.4),
        doc.text(1, 78, title, 36, 800, t["heading"], spacing=-0.8),
        f'<rect x="{tw + 24:.1f}" y="65" width="{1000 - tw - 24:.1f}" height="2" rx="1" fill="url(#{line})"/>',
    )
    return doc.render()


# =========================================================================== "right now" cards
NOW = [
    dict(key="duleko", status="NOW", tone="green", role="TECH LEAD", name="Duleko", period="2026 – present",
         text="A local skills marketplace for Nepal on the web and Google Play. I own the web app, the Android build, the database and every release.",
         cta="Read the case study", glow="#3B82F6", href=f"{SITE}/projects/duleko"),
    dict(key="flito", status="BUILDING", tone="amber", role="BUILDER", name="FLITO", period="Sept 2026 – present",
         text="Freight matching that gives Nepal's trucks paying loads on the trip home, on the web and Android, backed by 629 automated tests.",
         cta="Read the case study", glow="#F59E0B", href=f"{SITE}/projects/flito"),
    dict(key="epam", status="NEXT", tone="indigo", role="AI NATIVE SWE INTERN", name="EPAM Systems", period="From January 2027 · Hyderabad",
         text="Placed on campus after a coding round, a group discussion and a technical interview. Until then I'm open to internship roles.",
         cta="How the interview went", glow="#22D3EE", href=f"{SITE}/blog/epam-interview-experience-ai-native-intern"),
]
NOW_W = 330


def now_layout(item):
    return wrap(item["text"], 16, 500, NOW_W - 48)


NOW_H = 232 + max(len(now_layout(i)) for i in NOW) * 24 + 64


def now_card(theme, item):
    t = THEMES[theme]
    doc = Doc(NOW_W, NOW_H, f"{item['name']}, {item['period']}: {item['text']}")
    hair, rx = card_bg(doc, t, rx=22, glow=(NOW_W - 20, 10, 110, item["glow"], 0.22 if theme == "dark" else 0.18))
    tone = t[item["tone"]]
    doc.add(logo(doc, item["key"], 24, 24, 56, t, rx=15))
    sw = measure(item["status"], 11.5, 700, 1.4) + 30
    doc.add(
        f'<rect x="{NOW_W - 24 - sw:.1f}" y="38" width="{sw:.1f}" height="26" rx="13" fill="{tone}" fill-opacity="{t["greenBgOp"]}" stroke="{tone}" stroke-opacity="0.4"/>'
        f'<circle cx="{NOW_W - 24 - sw + 13:.1f}" cy="51" r="3.5" fill="{tone}"/>',
        doc.text(NOW_W - 24 - sw + 22, 55.2, item["status"], 11.5, 700, tone, spacing=1.4),
        doc.text(24, 116, item["role"], 12.5, 700, t["muted"], spacing=1.6),
        doc.text(24, 150, item["name"], 28, 800, t["heading"], spacing=-0.5),
        doc.text(24, 176, item["period"], 14.5, 500, t["faint"]),
        f'<rect x="24" y="198" width="{NOW_W - 48}" height="1" fill="{t["line"]}"/>',
    )
    y = 230
    for line in now_layout(item):
        doc.add(doc.text(24, y, line, 16, 500, t["text"]))
        y += 24
    fy = NOW_H - 32
    doc.add(
        doc.text(24, fy, item["cta"], 15, 700, t["indigo"]),
        icon("line", "arrow", t["indigo"], 24 + measure(item["cta"], 15, 700) + 6, fy - 13, 16),
    )
    card_end(doc, hair, rx)
    return doc.render()


# =========================================================================== project cards
PROJECTS = [
    dict(slug="flito", num="01", size="big", eyebrow="FULL-STACK · WEB + ANDROID", period="Sept 2026 – present",
         title="FLITO", subtitle="Freight matching platform for Nepal", url="flito.sanjay019.com.np",
         text="Gives Nepal's trucks paying loads on the trip home. Shippers post a load for up to 10 trucks, verified owners quote per truck, and drivers run each trip from a one-button job screen, in Nepali and English.",
         bullets=["Ranked truck matching; conditional updates stop racing acceptances double-booking a truck",
                  "Live trip map on Leaflet, OpenStreetMap and OSRM, with arrival times for a loaded truck",
                  "Payments recorded without holding money, PDF invoices, fees billed by Nepali month",
                  "Four ways to sign in, ID-verified owners and an append-only admin audit log"],
         metrics=[("629", "automated tests"), ("4", "user roles"), ("2", "platforms")],
         chips=["React Native", "Expo", "Redux Toolkit", "Node.js", "Express", "MongoDB", "Socket.io", "Jest", "Docker"],
         live="https://flito.sanjay019.com.np/", code="https://github.com/Sanjaycodes019/flito"),
    dict(slug="duleko", num="02", size="big", eyebrow="FULL-STACK · WEB + GOOGLE PLAY", period="2026 – present",
         title="Duleko", subtitle="Local skills marketplace for Nepal", url="duleko.com",
         text="Workers list their skills and a work area; people search, browse a private map, or post a job and choose from workers' offers. In English and Nepali, with Bikram Sambat dates, entirely on free tiers.",
         bullets=["Work lifecycle and job board enforced in Postgres: triggers, RPCs and RLS on every table",
                  "A privacy-first map: a work area picked once, ~1 km squares, only counts for guests",
                  "A verified badge that only an ID check can grant, photos behind 10-minute links",
                  "Mobile number + PIN sign-in, realtime chat and Android alerts with no Firebase"],
         metrics=[("36", "tables under RLS"), ("64", "migrations"), ("$0", "hosting cost")],
         chips=["React 19", "TypeScript", "TanStack Query", "Tailwind CSS", "Supabase", "PostgreSQL", "Capacitor", "Leaflet"],
         live="https://duleko.com", code="https://github.com/DulekoNepal/Duleko"),
    dict(slug="cargonepal", num="03", size="compact", eyebrow="MERN · LOGISTICS", period="Sept – Dec 2025",
         title="CargoNepal", subtitle="Logistics & truck booking platform", url="cargo-nepal-final.vercel.app",
         text="Customers search and book trucks, owners manage their fleet and admins verify users and vehicles: email OTP sign-up, conflict-checked bookings, live Socket.io updates, reviews and PDF invoices.",
         badges=["3 user roles", "15+ REST endpoints", "Live booking status"],
         chips=["Node.js", "Express", "MongoDB", "React", "Socket.io", "JWT", "Tailwind CSS"],
         live="https://cargo-nepal-final.vercel.app/", code="https://github.com/Sanjaycodes019/CargoNepal_Final"),
    dict(slug="safeher", num="04", size="compact", eyebrow="HACKATHON · 24 HOURS", period="Apr 2025",
         title="SafeHer", subtitle="Decentralized women's safety app", url="HackIndia Spark 5 demo",
         text="One tap sends an SOS with live location to emergency contacts, evidence is stored on IPFS and recorded on Ethereum so nobody can quietly alter it, and a locally hosted AI chatbot gives crisis guidance.",
         badges=["Top 15 of 150+ teams", "Team Lead", "Built in 24 hours"],
         chips=["React", "TypeScript", "Solidity", "IPFS", "Ethereum", "Supabase", "FastAPI", "Ollama"],
         live=None, code="https://github.com/Sanjaycodes019/HackIndia-Spark-5-2025-Gorkhe"),
    dict(slug="schedulix", num="05", size="compact", eyebrow="C++17 · DESKTOP", period="2025",
         title="Schedulix", subtitle="CPU scheduling simulator", url="Schedulix · SFML GUI",
         text="Simulates FCFS, SJF, SRTF, Round Robin and Priority scheduling, with a console build for quick runs and an SFML GUI that draws the Gantt chart and compares waiting and turnaround times.",
         badges=["5 algorithms", "Console + GUI", "Gantt charts"],
         chips=["C++17", "SFML", "CMake", "Windows API", "OOP"],
         live=None, code="https://github.com/Sanjaycodes019/Shedulix_Simulator_CPP"),
]


def browser_frame(doc, t, x0, y0, w, slug, url):
    bar, sh = 30, w * 0.625
    clip = doc.uid("shot")
    doc.defs.append(f'<clipPath id="{clip}"><path d="M{x0} {y0 + bar}H{x0 + w}V{y0 + bar + sh - 12}a12 12 0 0 1-12 12H{x0 + 12}a12 12 0 0 1-12-12z"/></clipPath>')
    uw = min(w - 150, measure(url, 11.5, 500) + 40)
    doc.add(
        f'<rect x="{x0}" y="{y0}" width="{w}" height="{bar + sh:.1f}" rx="12" fill="{t["chip"]}"/>',
        f'<circle cx="{x0 + 16}" cy="{y0 + 15}" r="4.5" fill="#FF5F57"/><circle cx="{x0 + 31}" cy="{y0 + 15}" r="4.5" fill="#FEBC2E"/><circle cx="{x0 + 46}" cy="{y0 + 15}" r="4.5" fill="#28C840"/>',
        f'<rect x="{x0 + (w - uw) / 2:.1f}" y="{y0 + 6}" width="{uw:.1f}" height="18" rx="9" fill="{t["card"]}" stroke="{t["chipBorder"]}"/>',
        doc.text(x0 + w / 2, y0 + 19, url, 11.5, 500, t["muted"], anchor="middle"),
        f'<image href="{data_uri(os.path.join(MEDIA, f"shot-{slug}.webp"), "image/webp")}" x="{x0}" y="{y0 + bar}" width="{w}" height="{sh:.1f}" preserveAspectRatio="xMidYMin slice" clip-path="url(#{clip})"/>',
        f'<rect x="{x0 + 0.5}" y="{y0 + 0.5}" width="{w - 1}" height="{bar + sh - 1:.1f}" rx="11.5" fill="none" stroke="{t["chipBorder"]}"/>',
        f'<path d="M{x0} {y0 + bar}H{x0 + w}" stroke="{t["chipBorder"]}"/>',
    )
    return y0 + bar + sh


def project_head(doc, t, p, x, y, w):
    nw = measure(p["num"], 12.5, 700) + 20
    doc.add(
        f'<rect x="{x}" y="{y}" width="{nw:.1f}" height="24" rx="12" fill="#6366F1" fill-opacity="{t["tintOp"]}" stroke="#6366F1" stroke-opacity="0.35"/>',
        doc.text(x + nw / 2, y + 16.4, p["num"], 12.5, 700, t["indigo"], anchor="middle"),
        doc.text(x + nw + 12, y + 16.8, p["eyebrow"], 12.5, 700, t["indigo"], spacing=1.8),
        logo(doc, p["slug"], x, y + 42, 48, t, rx=13),
        doc.text(x + 62, y + 76, p["title"], 32, 800, t["heading"], spacing=-0.6),
        doc.text(x + 62 + measure(p["title"], 32, 800, -0.6) + 12, y + 76, p["period"], 14, 500, t["faint"]),
        doc.text(x, y + 120, p["subtitle"], 17, 700, t["indigo"]),
    )
    yy = y + 152
    for line in wrap(p["text"], 15.5, 500, w):
        doc.add(doc.text(x, yy, line, 15.5, 500, t["text"]))
        yy += 23.5
    return yy


def project_card(theme, p):
    t = THEMES[theme]
    big = p["size"] == "big"
    W = 1000
    fx, fy, fw = 28, 28, 520 if big else 380
    rx_ = fx + fw + 32
    rw = W - rx_ - 30
    # measure the right column first so the card height fits it
    probe = Doc(W, 10, "")
    bottom = project_head(probe, t, p, rx_, 30, rw)
    if big:
        bottom += 6
        for b in p["bullets"]:
            bottom += len(wrap(b, 15, 500, rw - 26)) * 22 + 8
    else:
        bottom += 46
    bottom = chip_row(probe, rx_, bottom + 10, p["chips"], t, maxw=rw) + 30
    left_bottom = fy + 30 + fw * 0.625 + (16 + 76 if big else 0) + 28
    H = max(bottom, left_bottom)
    title = f"{p['title']}: {p['subtitle']}. {p['text']}"
    doc = Doc(W, H, title)
    hair, rx = card_bg(doc, t, rx=24, glow=(W - 60, 30, 160, "#6366F1", 0.20 if theme == "dark" else 0.16))
    shot_bottom = browser_frame(doc, t, fx, fy, fw, p["slug"], p["url"])
    if big:
        mw = (fw - 24) / 3
        for i, (num, label) in enumerate(p["metrics"]):
            mx = fx + i * (mw + 12)
            doc.add(
                f'<rect x="{mx:.1f}" y="{shot_bottom + 16:.1f}" width="{mw:.1f}" height="76" rx="14" fill="{t["card2"]}" stroke="{t["chipBorder"]}"/>',
                doc.text(mx + 18, shot_bottom + 52, num, 27, 800, t["heading"], spacing=-0.5),
                doc.text(mx + 18, shot_bottom + 74, label, 13.5, 600, t["muted"]),
            )
    yy = project_head(doc, t, p, rx_, 30, rw)
    if big:
        yy += 6
        for b in p["bullets"]:
            lines = wrap(b, 15, 500, rw - 26)
            doc.add(
                f'<circle cx="{rx_ + 8}" cy="{yy - 5}" r="8.5" fill="#6366F1" fill-opacity="{t["tintOp"]}"/>',
                icon("line", "check", t["indigo"], rx_ + 2.5, yy - 10.5, 11),
            )
            for line in lines:
                doc.add(doc.text(rx_ + 26, yy, line, 15, 500, t["text"]))
                yy += 22
            yy += 8
    else:
        bx = rx_
        for label in p["badges"]:
            bw = measure(label, 13.5, 700) + 34
            doc.add(
                f'<rect x="{bx:.1f}" y="{yy - 4:.1f}" width="{bw:.1f}" height="30" rx="15" fill="#6366F1" fill-opacity="{t["tintOp"]}" stroke="#6366F1" stroke-opacity="0.3"/>',
                icon("line", "check", t["indigo"], bx + 10, yy + 4, 13),
                doc.text(bx + 27, yy + 15.6, label, 13.5, 700, t["indigo"]),
            )
            bx += bw + 8
        yy += 46
    chip_row(doc, rx_, yy + 10, p["chips"], t, maxw=rw)
    card_end(doc, hair, rx)
    return doc.render()


# =========================================================================== stack
STACK = [
    ("Languages", [("typescript", "TypeScript"), ("javascript", "JavaScript"), ("cplusplus", "C++"), ("python", "Python")]),
    ("Frontend", [("react", "React"), ("tailwindcss", "Tailwind CSS"), ("reactquery", "TanStack Query"), ("redux", "Redux Toolkit"), ("vite", "Vite"), ("mui", "Material UI")]),
    ("Mobile", [("react", "React Native"), ("expo", "Expo"), ("capacitor", "Capacitor"), ("android", "Android")]),
    ("Backend", [("nodedotjs", "Node.js"), ("express", "Express"), ("supabase", "Supabase"), ("socketdotio", "Socket.io"), ("fastapi", "FastAPI")]),
    ("Data", [("postgresql", "PostgreSQL"), ("mongodb", "MongoDB"), ("mysql", "MySQL")]),
    ("Testing & DevOps", [("jest", "Jest"), ("githubactions", "GitHub Actions"), ("docker", "Docker"), ("vercel", "Vercel"), ("render", "Render"), ("sentry", "Sentry"), ("postman", "Postman"), ("git", "Git")]),
]
STACK_NOTES = {
    "Languages": "Typed first",
    "Frontend": "Web apps",
    "Mobile": "Android apps",
    "Backend": "APIs & realtime",
    "Data": "Rules in the DB",
    "Testing & DevOps": "CI on every push",
}


def stack(theme):
    t = THEMES[theme]
    row_h, top, item_w = 112, 22, 84
    H = top * 2 + row_h * len(STACK)
    doc = Doc(1000, H, "Tech stack: " + "; ".join(f"{c}: {', '.join(l for _, l in items)}" for c, items in STACK))
    hair, rx = card_bg(doc, t, rx=24, glow=(960, H - 20, 170, "#8B5CF6", 0.16 if theme == "dark" else 0.14))
    for r, (cat, items) in enumerate(STACK):
        y = top + r * row_h
        if r:
            doc.add(f'<rect x="28" y="{y}" width="944" height="1" fill="{t["line"]}"/>')
        doc.add(
            doc.text(32, y + 50, cat, 18, 800, t["heading"], spacing=-0.2),
            doc.text(32, y + 73, STACK_NOTES[cat], 13.5, 500, t["faint"]),
        )
        for i, (key, label) in enumerate(items):
            cx = 238 + i * item_w + item_w / 2
            c = brand_color(key, t)
            doc.add(
                f'<rect x="{cx - 24:.1f}" y="{y + 16}" width="48" height="48" rx="13" fill="{t["tile"]}" stroke="{t["tileBorder"]}"/>'
                f'<rect x="{cx - 24:.1f}" y="{y + 16}" width="48" height="48" rx="13" fill="{c}" fill-opacity="0.08"/>',
                icon("simple", key, c, cx - 13, y + 27, 26),
            )
            lines = [label] if measure(label, 12.5, 600) <= item_w - 4 else wrap(label, 12.5, 600, item_w - 4)
            for j, line in enumerate(lines):
                doc.add(doc.text(cx, y + 84 + j * 15, line, 12.5, 600, t["text"], anchor="middle"))
    card_end(doc, hair, rx)
    return doc.render()


# =========================================================================== achievements
WINS = [
    ("trophy", "Winner, regional round", "HackFest 2025 · SAP-sponsored hackathon", "200+", "teams in the field", "#F59E0B"),
    ("medal", "1st place", "University Prompt Engineering Competition 2025", "1st", "of all participants", "#A78BFA"),
    ("rocket", "Top 15 as Team Lead", "HackIndia Spark 5 · 24-hour national hackathon", "Top 15", "of 150+ teams", "#38BDF8"),
    ("code", "300+ DSA problems solved", "LeetCode and GeeksforGeeks · ongoing", "300+", "problems", "#34D399"),
    ("sigma", "Perfect score in Discrete Mathematics", "Masterclass by the Chancellor, Dr. Ashok K. Chitkara · 2024", "100", "out of 100", "#F472B6"),
]


def wins(theme):
    t = THEMES[theme]
    row_h, top = 92, 20
    H = top * 2 + row_h * len(WINS)
    doc = Doc(1000, H, "Achievements: " + "; ".join(f"{w[1]}, {w[2]}" for w in WINS))
    hair, rx = card_bg(doc, t, rx=24, glow=(40, 30, 150, "#F59E0B", 0.12 if theme == "dark" else 0.10))
    g1, g2, g3 = t["grad"]
    grad = doc.uid("wg")
    doc.defs.append(f'<linearGradient id="{grad}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{g1}"/><stop offset="1" stop-color="{g3}"/></linearGradient>')
    for r, (ic, title, event, value, label, color) in enumerate(WINS):
        y = top + r * row_h
        if r:
            doc.add(f'<rect x="28" y="{y}" width="944" height="1" fill="{t["line"]}"/>')
        doc.add(
            f'<rect x="32" y="{y + 18}" width="56" height="56" rx="16" fill="{color}" fill-opacity="{0.14 if theme == "dark" else 0.12}" stroke="{color}" stroke-opacity="0.35"/>',
            icon("line", ic, color, 46, y + 32, 28),
            doc.text(110, y + 42, title, 19, 700, t["heading"], spacing=-0.2),
            doc.text(110, y + 67, truncate(event, 15, 500, 640), 15, 500, t["muted"]),
            doc.text(968, y + 49, value, 30, 800, f"url(#{grad})", anchor="end", spacing=-0.6),
            doc.text(968, y + 70, label, 12.5, 600, t["faint"], anchor="end"),
        )
    card_end(doc, hair, rx)
    return doc.render()


# =========================================================================== writing rows
POSTS = [
    ("duleko-verified-badge-id-checks", "ID Checks Behind Duleko's Verified Badge",
     "How Duleko made its verified badge mean an ID was checked: photos in a private bucket, 10-minute links, and a badge only one Postgres function can grant.",
     "2026-10-13", "6 min read", ["PostgreSQL", "Security"], "duleko"),
    ("duleko-map-without-revealing-where-people-live", "Mapping People Without Revealing Where They Live",
     "How Duleko's map shows skilled people nearby without revealing where anyone lives: a work area picked once, ~1 km squares and counts for guests.",
     "2026-10-11", "7 min read", ["Privacy", "Maps"], "duleko"),
    ("flito-invoices-fees-nepali-calendar", "Billing by Nepali Month: FLITO's Invoices and Fees",
     "How FLITO records payments it never holds, bills truck owners by Nepali month, and numbers PDF invoices per Nepali fiscal year.",
     "2026-10-06", "8 min read", ["Payments", "System Design"], "flito"),
    ("duleko-android-notifications-without-firebase", "Android Notifications Without Firebase on Duleko",
     "Duleko's Android app shows chats and work requests in the notification bar with no push service, and keeps email inside Brevo's free tier.",
     "2026-10-06", "6 min read", ["Android", "PostgreSQL"], "duleko"),
    ("epam-interview-experience-ai-native-intern", "EPAM Interview Experience 2026: Rounds and Questions",
     "My EPAM campus placement: eligibility, the LRU cache coding round, the group discussion topic and the technical interview questions.",
     "2026-09-28", "8 min read", ["Interview", "Career"], "epam"),
]
MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()


def post_row(theme, post):
    slug, title, desc, date, rt, tags, proj = post
    t = THEMES[theme]
    doc = Doc(1000, 124, f"{title}: {desc}")
    hair, rx = card_bg(doc, t, rx=20)
    yr, mo, day = date.split("-")
    doc.add(
        f'<rect x="22" y="22" width="80" height="80" rx="18" fill="#6366F1" fill-opacity="{t["tintOp"]}" stroke="#6366F1" stroke-opacity="0.3"/>',
        doc.text(62, 66, str(int(day)), 30, 800, t["heading"], anchor="middle", spacing=-0.6),
        doc.text(62, 87, f"{MONTHS[int(mo) - 1]} {yr}", 11, 700, t["indigo"], anchor="middle", spacing=1),
    )
    tx, tw = 124, 700
    doc.add(
        doc.text(tx, 50, truncate(title, 20, 700, tw), 20, 700, t["heading"], spacing=-0.2),
        doc.text(tx, 76, truncate(desc, 14.5, 500, tw), 14.5, 500, t["muted"]),
    )
    cx = tx
    for label in [rt] + tags:
        w = measure(label, 12, 600) + 20
        doc.add(
            f'<rect x="{cx:.1f}" y="88" width="{w:.1f}" height="22" rx="11" fill="{t["chip"]}" stroke="{t["chipBorder"]}"/>',
            doc.text(cx + 10, 103, label, 12, 600, t["muted"]),
        )
        cx += w + 6
    doc.add(
        logo(doc, proj, 868, 44, 36, t, rx=10),
        f'<circle cx="952" cy="62" r="20" fill="#6366F1" fill-opacity="{t["tintOp"]}" stroke="#6366F1" stroke-opacity="0.35"/>',
        icon("line", "arrow", t["indigo"], 943, 53, 18),
    )
    card_end(doc, hair, rx)
    return doc.render()


# =========================================================================== footer
FOOTER_FACTS = [
    ("pin", ("FROM", "Siyari, Rupandehi, Nepal")),
    ("cap", ("STUDYING", "B.E. CSE · Chitkara · 2027")),
    ("bag", ("NEXT", "EPAM Systems · Jan 2027")),
]
def footer(theme):
    t = THEMES[theme]
    doc = Doc(1000, 300, "Let's build something together. Open to internship roles until I join EPAM Systems in January 2027. Email sahausanjay99@gmail.com")
    hair, rx = card_bg(doc, t, rx=24, grid=True, glow=(880, 40, 220, t["glow1"], t["glow1Op"]))
    blur = doc.uid("fb")
    doc.defs.append(f'<filter id="{blur}" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="60"/></filter>')
    doc.add(f'<circle class="glow" cx="140" cy="330" r="170" fill="{t["glow2"]}" fill-opacity="{t["glow2Op"]}" filter="url(#{blur})"/>')
    g1, g2, g3 = t["grad"]
    tg = doc.uid("tg")
    w1 = measure("Let's build something ", 42, 800, -1.1)
    w2 = measure("together.", 42, 800, -1.1)
    doc.defs.append(
        f'<linearGradient id="{tg}" gradientUnits="userSpaceOnUse" x1="{48 + w1:.1f}" y1="0" x2="{48 + w1 + w2:.1f}" y2="0">'
        f'<stop offset="0" stop-color="{g1}"/><stop offset="0.6" stop-color="{g2}"/><stop offset="1" stop-color="{g3}"/></linearGradient>'
    )
    bar = doc.uid("fbar")
    doc.defs.append(f'<linearGradient id="{bar}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#6366F1"/><stop offset="1" stop-color="#A78BFA"/></linearGradient>')
    doc.add(
        f'<rect x="48" y="62" width="32" height="3" rx="1.5" fill="url(#{bar})"/>',
        doc.text(92, 69, "LET'S TALK", 15, 700, t["indigo"], spacing=2.6),
        doc.spans(46, 128, 42, [("Let's build something ", 800, t["heading"]), ("together.", 800, f"url(#{tg})")], extra=' letter-spacing="-1.1"'),
        doc.text(48, 172, "Open to internship roles until I join EPAM Systems in January 2027.", 18, 500, t["text"]),
    )
    mail = "sahausanjay99@gmail.com"
    mw = measure(mail, 18, 600) + 62
    doc.add(
        f'<rect x="48" y="200" width="{mw:.1f}" height="50" rx="25" fill="{t["chip"]}" stroke="#6366F1" stroke-opacity="0.45" stroke-width="1.5"/>',
        icon("line", "mail", t["indigo"], 66, 213, 24),
        doc.text(100, 231.5, mail, 18, 600, t["heading"]),
        doc.spans(48 + mw + 22, 231.5, 16, [("or ", 500, t["muted"]), ("guptasanjay.com.np/contact", 600, t["indigo"])]),
    )
    doc.add(f'<rect x="676" y="56" width="1" height="188" fill="{t["line"]}"/>')
    for i, (ic, label) in enumerate(FOOTER_FACTS):
        fy = 92 + i * 62
        doc.add(
            f'<rect x="704" y="{fy - 26}" width="40" height="40" rx="12" fill="#6366F1" fill-opacity="{t["tintOp"]}" stroke="#6366F1" stroke-opacity="0.3"/>',
            icon("line", ic, t["indigo"], 714, fy - 16, 20),
            doc.text(758, fy - 9, label[0], 12, 700, t["faint"], spacing=1.4),
            doc.text(758, fy + 11, label[1], 15.5, 600, t["heading"]),
        )
    card_end(doc, hair, rx)
    doc.css.append(".glow{animation:fd 16s ease-in-out infinite alternate}@keyframes fd{to{transform:translate(-70px,30px)}}@media (prefers-reduced-motion:reduce){.glow{animation:none}}")
    return doc.render()


# =========================================================================== buttons
BUTTONS = {
    "portfolio": ("Portfolio", "line", "globe", "#818CF8", "#4F46E5"),
    "resume": ("Resume", "line", "doc", "#A78BFA", "#7C3AED"),
    "linkedin": ("LinkedIn", "simple", "linkedin", "#4C9AFF", "#0A66C2"),
    "leetcode": ("LeetCode", "simple", "leetcode", "#FFA116", "#E08A00"),
    "email": ("Email", "line", "mail", "#FF6B5E", "#D93025"),
    "live": ("Live app", "line", "play", "#818CF8", "#4F46E5"),
    "case": ("Case study", "line", "book", "#A78BFA", "#7C3AED"),
    "code": ("Source code", "simple", "github", "#E6EDF3", "#1F2328"),
    "posts": ("All posts", "line", "pen", "#818CF8", "#4F46E5"),
    "rss": ("RSS feed", "line", "rss", "#FB923C", "#C2410C"),
    "hackfest": ("HackFest 2025 story", "line", "trophy", "#FBBF24", "#B45309"),
    "hackindia": ("HackIndia Spark 5 story", "line", "rocket", "#38BDF8", "#0369A1"),
}


def button(theme, key):
    t = THEMES[theme]
    label, kind, ic, dark_c, light_c = BUTTONS[key]
    c = dark_c if theme == "dark" else light_c
    tw = measure(label, 16, 600)
    bh, bw = 44, 8 + 28 + 11 + tw + 10 + 12 + 16
    doc = Doc(round(bw, 1), bh, label)
    doc.add(
        f'<rect x="0.75" y="0.75" width="{bw - 1.5:.1f}" height="{bh - 1.5}" rx="{(bh - 1.5) / 2}" fill="{t["btn"]}" stroke="{t["btnBorder"]}" stroke-width="1.5"/>',
        f'<rect x="8" y="8" width="28" height="28" rx="8" fill="{c}" fill-opacity="{t["tintOp"]}"/>',
        icon(kind, ic, c, 13, 13, 18),
        doc.text(47, 27.6, label, 16, 600, t["btnText"]),
        icon("line", "arrow", t["btnMuted"], 47 + tw + 10, 16, 12),
    )
    return doc.render()


# =========================================================================== editor card
CODE = [
    [("const", "kw"), (" ", ""), ("sanjay", "name"), (" = {", "punc")],
    [("  role", "prop"), (": ", "punc"), ('"Full-Stack Software Engineer"', "str"), (",", "punc")],
    [("  platforms", "prop"), (": [", "punc"), ('"Web"', "str"), (", ", "punc"), ('"Android"', "str"), (", ", "punc"), ('"Backend"', "str"), ("],", "punc")],
    [("  now", "prop"), (": [", "punc"), ('"Tech Lead @ Duleko"', "str"), (", ", "punc"), ('"Builder @ FLITO"', "str"), ("],", "punc")],
    [("  next", "prop"), (": ", "punc"), ('"AI Native Software Engineering Intern @ EPAM"', "str"), (",", "punc")],
    [("  starts", "prop"), (": ", "punc"), ('"January 2027 · Hyderabad"', "str"), (",", "punc")],
    [("  education", "prop"), (": ", "punc"), ('"B.E. CSE · Chitkara University · 2027"', "str"), (",", "punc")],
    [("  from", "prop"), (": ", "punc"), ('"Siyari, Rupandehi, Nepal"', "str"), (",", "punc")],
    [("  principles", "prop"), (": [", "punc")],
    [("    ", ""), ('"business rules live in the database"', "str"), (",", "punc")],
    [("    ", ""), ('"privacy by design"', "str"), (",", "punc")],
    [("    ", ""), ('"tests run in CI on every push"', "str"), (",", "punc")],
    [("  ],", "punc")],
    [("}", "punc"), (" ", ""), ("as", "kw"), (" ", ""), ("const", "kw"), (";", "punc")],
]


def editor(theme):
    t = THEMES[theme]
    ew, bar, top, lh, fs = 1000, 48, 26, 36, 20.5
    code_x, gut_x, status_h = 92, 60, 34
    eh = bar + top + lh * len(CODE) + 18 + status_h
    doc = Doc(ew, eh, "sanjay.ts: role Full-Stack Software Engineer; now Tech Lead at Duleko and builder of FLITO; next AI Native Software Engineering Intern at EPAM Systems from January 2027; principles: business rules live in the database, privacy by design, tests run in CI on every push")
    clip = doc.uid("win")
    doc.defs.append(f'<clipPath id="{clip}"><rect width="{ew}" height="{eh}" rx="16"/></clipPath>')
    tab_label = "sanjay.ts"
    tab_w = 16 + 22 + 8 + measure(tab_label, 14, 600) + 18
    sb_y = eh - status_h
    doc.add(
        f'<g clip-path="url(#{clip})"><rect width="{ew}" height="{eh}" fill="{t["ed"]}"/><rect width="{ew}" height="{bar}" fill="{t["edBar"]}"/>',
        f'<path d="M0 {bar - 0.5}H{ew}" stroke="{t["edBorder"]}"/>',
        '<circle cx="24" cy="24" r="6.5" fill="#FF5F57"/><circle cx="46" cy="24" r="6.5" fill="#FEBC2E"/><circle cx="68" cy="24" r="6.5" fill="#28C840"/>',
        f'<path d="M96 {bar}V18a8 8 0 0 1 8-8h{tab_w - 16:.1f}a8 8 0 0 1 8 8V{bar}z" fill="{t["edTab"]}" stroke="{t["edBorder"]}"/>',
        f'<rect x="96" y="{bar - 1.5}" width="{tab_w:.1f}" height="3" fill="{t["edTab"]}"/><rect x="104" y="10" width="{tab_w - 16:.1f}" height="2" rx="1" fill="#6366F1"/>',
        '<rect x="112" y="21" width="22" height="16" rx="3.5" fill="#3178C6"/>',
        doc.text(123, 33, "TS", 10, 600, "#FFFFFF", anchor="middle"),
        doc.text(142, 34, tab_label, 14, 600, t["btnText"]),
        f'<path d="M{gut_x + 16} {bar}V{sb_y}" stroke="{t["edBorder"]}" stroke-opacity="0.6"/>',
    )
    for i, line in enumerate(CODE):
        y = bar + top + lh * i + 24
        out = []
        for tok, kind in line:
            doc.used.setdefault(("mono", 400), []).append(tok)
            out.append(f'<tspan fill="{t[kind]}">{esc(tok)}</tspan>' if kind else esc(tok))
        doc.add(
            doc.text(gut_x, y, str(i + 1), fs - 2, 400, t["gutter"], anchor="end", mono=True),
            f'<text x="{code_x}" y="{y}" font-size="{fs}" font-weight="400" fill="{t["punc"]}" class="m" xml:space="preserve">{"".join(out)}</text>',
        )
        text = "".join(tok for tok, _ in line)
        indent = len(text) - len(text.lstrip())
        doc.add(f'<rect x="{900 + indent * 1.2:.1f}" y="{bar + top + i * 7}" width="{max(4, len(text.strip()) * 1.15):.1f}" height="3" rx="1.5" fill="{t["mini"]}"/>')
    last = "".join(tok for tok, _ in CODE[-1])
    doc.add(f'<rect class="cursor" x="{code_x + measure(last, fs, 400, path=CASCADIA) + 2:.1f}" y="{bar + top + lh * (len(CODE) - 1) + 5}" width="2.4" height="24" fill="#6366F1"/>')
    doc.add(
        f'<rect x="0" y="{sb_y}" width="{ew}" height="{status_h}" fill="{t["status"]}"/>',
        f'<g transform="translate(18 {sb_y + 9}) scale(0.67)" {STROKE.format(c=t["statusText"])}><circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="8" r="2.5"/><path d="M6 8.5v7M18 10.5c0 4-4 4.5-9.5 6"/></g>',
    )
    sx = 42
    for label, wght in (("main", 600), ("0 problems", 500)):
        doc.add(doc.text(sx, sb_y + 22, label, 13, wght, t["statusText"]))
        sx += measure(label, 13, wght) + 22
    rx_ = ew - 18
    for label in ("Ln 14, Col 12", "UTF-8", "LF", "TypeScript"):
        doc.add(doc.text(rx_, sb_y + 22, label, 13, 500, t["statusText"], anchor="end"))
        rx_ -= measure(label, 13, 500) + 22
    doc.add("</g>", f'<rect x="0.75" y="0.75" width="{ew - 1.5}" height="{eh - 1.5}" rx="15.25" fill="none" stroke="{t["edBorder"]}" stroke-width="1.5"/>')
    doc.css.append(".cursor{animation:blink 1.1s steps(2,start) infinite}@keyframes blink{to{visibility:hidden}}@media (prefers-reduced-motion:reduce){.cursor{animation:none}}")
    return doc.render()


# =========================================================================== README
W100, W32, H36 = 'width="100%"', 'width="32%"', 'height="36"'


def pic(name, attrs, alt):
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="{RAW}/{name}-dark.svg" />'
        f'<img {attrs} alt="{esc(alt)}" src="{RAW}/{name}-light.svg" /></picture>'
    )


def btn(key, href):
    return f'<a href="{href}">{pic("btn-" + key, H36, BUTTONS[key][0])}</a>'


def readme():
    def head(key):
        num, _, title = SECTIONS[key]
        return pic(f"section-{key}", 'width="100%"', f"{num} · {title}")

    projects = []
    for p in PROJECTS:
        links = []
        if p["live"]:
            links.append(btn("live", p["live"]))
        links += [btn("case", f"{SITE}/projects/{p['slug']}"), btn("code", p["code"])]
        projects.append(
            f'<a href="{SITE}/projects/{p["slug"]}">{pic("project-" + p["slug"], W100, p["title"] + ": " + p["subtitle"])}</a>\n\n'
            f'<p align="center">\n  ' + "\n  ".join(links) + "\n</p>\n"
        )
    posts = "\n\n".join(
        f'<a href="{SITE}/blog/{slug}">{pic("post-" + str(i + 1), W100, title)}</a>'
        for i, (slug, title, *_rest) in enumerate(POSTS)
    )
    now = "\n  ".join(f'<a href="{n["href"]}">{pic("now-" + n["key"], W32, n["name"] + ": " + n["text"])}</a>' for n in NOW)
    stats = (
        "https://streak-stats.demolab.com/?user=Sanjaycodes019&disable_animations=true&border_radius=16",
        "https://github-readme-stats.shion.dev/api/top-langs/?username=Sanjaycodes019&layout=compact&langs_count=8&disable_animations=true&border_radius=16",
    )
    streak_dark = stats[0] + "&background=0B1120&border=1E293B&stroke=243047&ring=6366f1&fire=8b5cf6&currStreakNum=F8FAFC&currStreakLabel=818cf8&sideNums=F8FAFC&sideLabels=818cf8&dates=94A3B8"
    streak_light = stats[0] + "&background=F8FAFC&border=D8DEE8&stroke=E2E8F0&ring=6366f1&fire=7c3aed&currStreakNum=0F172A&currStreakLabel=4f46e5&sideNums=0F172A&sideLabels=4f46e5&dates=64748B"
    langs_dark = stats[1] + "&bg_color=0B1120&border_color=1E293B&title_color=818cf8&text_color=CBD5E1"
    langs_light = stats[1] + "&bg_color=F8FAFC&border_color=D8DEE8&title_color=4f46e5&text_color=334155"
    return f"""<div align="center">

{pic("hero", 'width="100%"', "Sanjay Gupta, Full-Stack Software Engineer: Tech Lead at Duleko, building FLITO, joining EPAM Systems in January 2027")}

<p>
  {btn("portfolio", SITE)}
  {btn("resume", SITE + "/resume")}
  {btn("linkedin", "https://www.linkedin.com/in/sanjay1621/")}
  {btn("leetcode", "https://leetcode.com/Sanjaycodes09/")}
  {btn("email", "mailto:sahausanjay99@gmail.com")}
</p>

</div>

{head("about")}

I'm a full-stack software engineer from **Siyari, Rupandehi, Nepal**, finishing a B.E. in Computer Science Engineering at **Chitkara University** (CGPA 8.5, graduating August 2027). I build products for Nepal end to end, from React and React Native screens to Node.js and Supabase backends and PostgreSQL and MongoDB data models, and ship them to the web and to Android.

{pic("about", 'width="100%"', "sanjay.ts: role Full-Stack Software Engineer; now Tech Lead at Duleko and builder of FLITO; next AI Native Software Engineering Intern at EPAM Systems from January 2027")}

{head("now")}

<p align="center">
  {now}
</p>

{head("projects")}

{chr(10).join(projects)}
{head("stack")}

{pic("stack", 'width="100%"', "Tech stack: TypeScript, JavaScript, C++, Python; React, Tailwind CSS, TanStack Query, Redux Toolkit, Vite, Material UI; React Native, Expo, Capacitor, Android; Node.js, Express, Supabase, Socket.io, FastAPI; PostgreSQL, MongoDB, MySQL; Jest, GitHub Actions, Docker, Vercel, Render, Sentry, Postman, Git")}

{head("wins")}

{pic("wins", 'width="100%"', "Achievements: winner of the HackFest 2025 regional round, 1st place in the university Prompt Engineering Competition 2025, Top 15 of 150+ teams at HackIndia Spark 5, 300+ DSA problems solved, 100/100 in Discrete Mathematics")}

<p align="center">
  {btn("hackfest", SITE + "/stories/hackfest-2025")}
  {btn("hackindia", SITE + "/stories/hackindia-spark5")}
</p>

{head("writing")}

{posts}

<p align="center">
  {btn("posts", SITE + "/blog")}
  {btn("rss", SITE + "/feed.xml")}
</p>

{head("activity")}

<div align="center">
  <picture><source media="(prefers-color-scheme: dark)" srcset="{esc(streak_dark)}" /><img height="180" alt="Sanjay's GitHub contributions and streaks" src="{esc(streak_light)}" /></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="{esc(langs_dark)}" /><img height="180" alt="Sanjay's most used languages" src="{esc(langs_light)}" /></picture>
</div>

<br />

<a href="mailto:sahausanjay99@gmail.com">{pic("footer", 'width="100%"', "Let's build something together. Open to internship roles until I join EPAM Systems in January 2027. Email sahausanjay99@gmail.com")}</a>

<p align="center">
  {btn("email", "mailto:sahausanjay99@gmail.com")}
  {btn("linkedin", "https://www.linkedin.com/in/sanjay1621/")}
  {btn("portfolio", SITE)}
  {btn("resume", SITE + "/resume")}
</p>
"""


# =========================================================================== write
def main():
    os.makedirs(ASSETS, exist_ok=True)
    for theme in THEMES:
        files = {f"hero-{theme}.svg": hero(theme), f"about-{theme}.svg": editor(theme),
                 f"stack-{theme}.svg": stack(theme), f"wins-{theme}.svg": wins(theme), f"footer-{theme}.svg": footer(theme)}
        for key in SECTIONS:
            files[f"section-{key}-{theme}.svg"] = section(theme, key)
        for item in NOW:
            files[f"now-{item['key']}-{theme}.svg"] = now_card(theme, item)
        for p in PROJECTS:
            files[f"project-{p['slug']}-{theme}.svg"] = project_card(theme, p)
        for i, post in enumerate(POSTS):
            files[f"post-{i + 1}-{theme}.svg"] = post_row(theme, post)
        for key in BUTTONS:
            files[f"btn-{key}-{theme}.svg"] = button(theme, key)
        total = 0
        for name, svg in files.items():
            with open(os.path.join(ASSETS, name), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(svg)
            total += len(svg.encode())
        print(f"{theme}: {len(files)} files, {total / 1024:.0f} KB")
    with open(os.path.join(REPO, "README.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(readme())
    print("README.md written")


main()
