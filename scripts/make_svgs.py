"""Builds the profile README's hero card, link buttons and editor card, in light and dark.

Usage: python -I make_svgs.py <out_dir> <inter_variable_woff2> <cascadia_mono_ttf> <logo_dir> <leetcode_svg>

Fonts are instanced from the variable files and subset to the glyphs each SVG uses, then
embedded as WOFF2 data URIs, so the text looks the same on every OS and every width is
measured from the real font.
"""
import base64
import io
import re
import sys
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

OUT, INTER, CASCADIA, LOGOS, LEETCODE = sys.argv[1:6]

# --------------------------------------------------------------------------- fonts
_static = {}


def static_font(path, wght):
    key = (path, wght)
    if key not in _static:
        font = instancer.instantiateVariableFont(TTFont(path), {"wght": wght})
        buf = io.BytesIO()
        font.flavor = None
        font.save(buf)
        _static[key] = buf.getvalue()
    return TTFont(io.BytesIO(_static[key]))


def measure(path, wght, text, size, spacing=0.0):
    font = static_font(path, wght)
    cmap, hmtx, upm = font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm
    width = 0
    for ch in text:
        glyph = cmap.get(ord(ch))
        if glyph is None:
            raise SystemExit(f"missing glyph {ch!r} in {path} @ {wght}")
        width += hmtx[glyph][0]
    return width * size / upm + spacing * len(text)


def font_face(path, wght, family, text):
    font = static_font(path, wght)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt", "ss01", "cv11", "tnum"]
    opts.notdef_outline = True
    opts.name_IDs = [0, 1, 2, 13, 14]
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(set(text + " "))))
    sub.subset(font)
    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return (
        f"@font-face{{font-family:'{family}';font-weight:{wght};"
        f"src:url(data:font/woff2;base64,{data}) format('woff2');}}"
    )


def data_uri(path, mime):
    with open(path, "rb") as fh:
        return f"data:{mime};base64," + base64.b64encode(fh.read()).decode()


def x(s):
    return escape(s, {'"': "&quot;"})


# --------------------------------------------------------------------------- themes
THEMES = {
    "dark": dict(
        card="#0B1120", card2="#111827", border="#1E293B", heading="#F8FAFC", text="#CBD5E1",
        muted="#94A3B8", faint="#64748B", indigo="#818CF8", grid="#94A3B8", gridOp=0.075,
        glow1="#6366F1", glow1Op=0.34, glow2="#8B5CF6", glow2Op=0.22, chip="#0F172A",
        chipBorder="#243047", green="#34D399", greenBg="#34D399", greenBgOp=0.10,
        grad=("#818CF8", "#8B5CF6", "#C4B5FD"), shadow="#000000", shadowOp=0.0,
        # buttons sit on GitHub's own page colours
        btn="#151B23", btnBorder="#30363D", btnText="#E6EDF3", btnMuted="#7D8590", tintOp=0.16,
        brand=dict(portfolio="#818CF8", resume="#A78BFA", linkedin="#4C9AFF", leetcode="#FFA116", email="#FF6B5E"),
        # editor
        ed="#0D1117", edBar="#161B22", edBorder="#30363D", edTab="#0D1117", gutter="#3D4654",
        kw="#C4B5FD", name="#93C5FD", prop="#A5B4FC", str="#86EFAC", punc="#8B949E", status="#4F46E5",
        statusText="#E0E7FF", mini="#30363D",
    ),
    "light": dict(
        card="#F8FAFC", card2="#FFFFFF", border="#D8DEE8", heading="#0F172A", text="#334155",
        muted="#64748B", faint="#94A3B8", indigo="#4F46E5", grid="#0F172A", gridOp=0.055,
        glow1="#818CF8", glow1Op=0.30, glow2="#C4B5FD", glow2Op=0.40, chip="#FFFFFF",
        chipBorder="#E2E8F0", green="#047857", greenBg="#10B981", greenBgOp=0.10,
        grad=("#4F46E5", "#7C3AED", "#8B5CF6"), shadow="#0F172A", shadowOp=0.05,
        btn="#F6F8FA", btnBorder="#D0D7DE", btnText="#1F2328", btnMuted="#59636E", tintOp=0.12,
        brand=dict(portfolio="#4F46E5", resume="#7C3AED", linkedin="#0A66C2", leetcode="#E08A00", email="#D93025"),
        ed="#FFFFFF", edBar="#F6F8FA", edBorder="#D0D7DE", edTab="#FFFFFF", gutter="#A0A8B3",
        kw="#7C3AED", name="#2563EB", prop="#4F46E5", str="#15803D", punc="#6E7781", status="#4F46E5",
        statusText="#FFFFFF", mini="#D8DEE4",
    ),
}

SANS = "'InterEmbed', 'Inter', 'Segoe UI', -apple-system, Helvetica, Arial, sans-serif"
MONO = "'CascadiaEmbed', 'Cascadia Mono', ui-monospace, SFMono-Regular, Consolas, Menlo, monospace"

# --------------------------------------------------------------------------- hero
W, H = 1000, 432
PAD = 48

DOMAIN = ("guptasanjay", ".com.np")
STATUS = "Open to internships · until Jan 2027"
EYEBROW = "FULL-STACK SOFTWARE ENGINEER"
FIRST, LAST = "Sanjay", "Gupta"
PHRASES = [
    "Tech Lead at Duleko · web + Android on Google Play",
    "Building FLITO · freight matching for Nepal",
    "629 automated tests · business rules in Postgres",
    "Joining EPAM Systems · January 2027",
]
CHIPS = [
    ("duleko", "Tech Lead at ", "Duleko"),
    ("flito", "Building ", "FLITO"),
    ("epam", "Joining ", "EPAM · Jan 2027"),
]
STATS = [
    ("629", "automated tests", "FLITO · Jest + CI"),
    ("36", "tables under RLS", "Duleko · PostgreSQL"),
    ("300+", "DSA problems", "LeetCode + GfG"),
]


def hero(theme_name):
    t = THEMES[theme_name]
    used = {500: "", 600: "", 700: "", 800: ""}

    def take(wght, s):
        used[wght] += s
        return s

    parts = []
    # card + background --------------------------------------------------------
    g1, g2, g3 = t["grad"]
    defs = f"""
  <clipPath id="card"><rect width="{W}" height="{H}" rx="24"/></clipPath>
  <linearGradient id="hair" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{t['border']}"/><stop offset="0.5" stop-color="#6366F1" stop-opacity="0.85"/><stop offset="1" stop-color="{t['border']}"/>
  </linearGradient>
  <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#6366F1"/><stop offset="1" stop-color="#A78BFA"/></linearGradient>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
    <path d="M32 0H0V32" fill="none" stroke="{t['grid']}" stroke-opacity="{t['gridOp']}" stroke-width="1"/>
  </pattern>
  <radialGradient id="fade" cx="0.42" cy="0.38" r="0.75">
    <stop offset="0" stop-color="#fff"/><stop offset="0.7" stop-color="#fff" stop-opacity="0.55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </radialGradient>
  <mask id="gridMask"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>
  <filter id="blur" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="64"/></filter>
"""
    parts.append(f'<g clip-path="url(#card)">')
    parts.append(f'<rect width="{W}" height="{H}" fill="{t["card"]}"/>')
    parts.append(f'<rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#gridMask)"/>')
    parts.append(
        f'<g filter="url(#blur)"><circle class="glow1" cx="840" cy="40" r="230" fill="{t["glow1"]}" fill-opacity="{t["glow1Op"]}"/>'
        f'<circle class="glow2" cx="110" cy="450" r="200" fill="{t["glow2"]}" fill-opacity="{t["glow2Op"]}"/></g>'
    )

    # top row: monogram + domain, status pill --------------------------------
    parts.append(
        f'<rect x="{PAD}" y="42" width="46" height="46" rx="13" fill="{t["chip"]}" stroke="{t["chipBorder"]}" stroke-width="1.5"/>'
        f'<text x="{PAD + 23}" y="71.5" text-anchor="middle" font-size="17" font-weight="800" fill="{t["heading"]}">{take(800, "SG")}</text>'
    )
    dx = PAD + 62
    parts.append(
        f'<text x="{dx}" y="72" font-size="19"><tspan font-weight="700" fill="{t["heading"]}">{take(700, DOMAIN[0])}</tspan>'
        f'<tspan font-weight="500" fill="{t["muted"]}">{take(500, DOMAIN[1])}</tspan></text>'
    )
    sw = measure(INTER, 600, take(600, STATUS), 15)
    pill_w = 16 + 10 + 10 + sw + 18
    px = W - PAD - pill_w
    parts.append(
        f'<rect x="{px:.1f}" y="47" width="{pill_w:.1f}" height="36" rx="18" fill="{t["greenBg"]}" fill-opacity="{t["greenBgOp"]}" stroke="{t["green"]}" stroke-opacity="0.35"/>'
        f'<circle class="ping" cx="{px + 21:.1f}" cy="65" r="5" fill="{t["green"]}"/>'
        f'<circle cx="{px + 21:.1f}" cy="65" r="5" fill="{t["green"]}"/>'
        f'<text x="{px + 36:.1f}" y="70.2" font-size="15" font-weight="600" fill="{t["green"]}">{x(STATUS)}</text>'
    )

    # eyebrow ------------------------------------------------------------------
    parts.append(
        f'<rect x="{PAD}" y="146" width="32" height="3" rx="1.5" fill="url(#bar)"/>'
        f'<text x="{PAD + 44}" y="153" font-size="16.5" font-weight="700" letter-spacing="2.6" fill="{t["indigo"]}">{take(700, EYEBROW)}</text>'
    )

    # name ---------------------------------------------------------------------
    size, spacing, maxw = 92, -2.4, 600
    full = FIRST + " " + LAST
    take(800, full)
    while measure(INTER, 800, full, size, spacing) > maxw:
        size -= 1
        spacing = -2.4 * size / 92
    first_w = measure(INTER, 800, FIRST + " ", size, spacing)
    last_w = measure(INTER, 800, LAST, size, spacing)
    lx = PAD - 3
    defs += (
        f'<linearGradient id="name" gradientUnits="userSpaceOnUse" x1="{lx + first_w:.1f}" y1="0" x2="{lx + first_w + last_w:.1f}" y2="0">'
        f'<stop offset="0" stop-color="{g1}"/><stop offset="0.6" stop-color="{g2}"/><stop offset="1" stop-color="{g3}"/></linearGradient>'
    )
    parts.append(
        f'<text x="{lx}" y="240" font-size="{size}" font-weight="800" letter-spacing="{spacing:.2f}">'
        f'<tspan fill="{t["heading"]}">{FIRST} </tspan><tspan fill="url(#name)">{LAST}</tspan></text>'
    )

    # typing line --------------------------------------------------------------
    ty, tsize = 294, 23
    parts.append(f'<text x="{PAD}" y="{ty}" font-size="{tsize}" font-weight="700" fill="{t["indigo"]}">{take(700, "›")}</text>')
    tx = PAD + 24
    css_typing = []
    n = len(PHRASES)
    slot = 100 / n
    caret_frames = []
    for i, phrase in enumerate(PHRASES):
        take(500, phrase)
        pw = measure(INTER, 500, phrase, tsize)
        s = i * slot
        type_end = s + slot * 0.36
        hold_end = s + slot * 0.94
        defs += f'<clipPath id="c{i}"><rect class="r{i}" x="{tx}" y="{ty - 24}" width="{pw + 2:.1f}" height="34"/></clipPath>'
        parts.append(
            f'<text class="p p{i}" clip-path="url(#c{i})" x="{tx}" y="{ty}" font-size="{tsize}" font-weight="500" fill="{t["text"]}">{x(phrase)}</text>'
        )
        steps = len(phrase)
        eps = 0.01
        vis = (
            f"@keyframes v{i}{{0%{{opacity:{1 if i == 0 else 0}}}"
            + (f"{s - eps:.2f}%{{opacity:0}}{s:.2f}%{{opacity:1}}" if i else "")
            + f"{hold_end:.2f}%{{opacity:1}}{s + slot - eps:.2f}%,100%{{opacity:0}}}}"
        )
        rev = (
            f"@keyframes w{i}{{0%,{s:.2f}%{{transform:scaleX(0);animation-timing-function:steps({steps},end)}}"
            f"{type_end:.2f}%,100%{{transform:scaleX(1)}}}}"
        )
        css_typing.append(vis + rev + f".p{i}{{animation:v{i} 18s infinite}}.r{i}{{animation:w{i} 18s infinite}}")
        caret_frames.append(
            f"{s:.2f}%{{transform:translateX(0);animation-timing-function:steps({steps},end)}}"
            f"{type_end:.2f}%{{transform:translateX({pw + 3:.1f}px)}}"
            f"{s + slot - eps:.2f}%{{transform:translateX({pw + 3:.1f}px)}}"
        )
    parts.append(f'<g class="caretMove"><rect class="caret" x="{tx}" y="{ty - 20}" width="2.6" height="25" rx="1.3" fill="{t["indigo"]}"/></g>')

    # stats column -------------------------------------------------------------
    sx, sw_tile, sy, sh, gap = 700, 252, 116, 64, 11
    for i, (num, label, source) in enumerate(STATS):
        y = sy + i * (sh + gap)
        take(800, num)
        nw = measure(INTER, 800, num, 28, -0.5)
        room = sw_tile - 18 - nw - 10 - 14
        for txt, wt, fz in ((label, 600, 16.5), (source, 500, 13.5)):
            if measure(INTER, wt, txt, fz) > room:
                raise SystemExit(f'stat text too wide: {txt!r}')
        parts.append(
            f'<rect x="{sx}" y="{y}" width="{sw_tile}" height="{sh}" rx="14" fill="{t["card2"]}" fill-opacity="0.78" stroke="{t["chipBorder"]}" stroke-width="1.2"/>'
            f'<text x="{sx + 18}" y="{y + 42}" font-size="28" font-weight="800" letter-spacing="-0.5" fill="{t["heading"]}">{x(num)}</text>'
            f'<text x="{sx + 28 + nw:.1f}" y="{y + 28}" font-size="16.5" font-weight="600" fill="{t["text"]}">{take(600, label)}</text>'
            f'<text x="{sx + 28 + nw:.1f}" y="{y + 48}" font-size="13.5" font-weight="500" fill="{t["faint"]}">{x(take(500, source))}</text>'
        )

    # chips --------------------------------------------------------------------
    cx, cy, ch = PAD, 340, 48
    chip_logo = {k: data_uri(f"{LOGOS}/logo-{k}.png", "image/png") for k, _, _ in CHIPS}
    for key, pre, bold in CHIPS:
        take(500, pre)
        take(700, bold)
        w_pre = measure(INTER, 500, pre, 17)
        w_bold = measure(INTER, 700, bold, 17)
        cw = 9 + 30 + 11 + w_pre + w_bold + 18
        defs += f'<clipPath id="l{key}"><rect x="{cx + 9}" y="{cy + 9}" width="30" height="30" rx="8"/></clipPath>'
        parts.append(
            f'<rect x="{cx:.1f}" y="{cy}" width="{cw:.1f}" height="{ch}" rx="{ch / 2}" fill="{t["chip"]}" fill-opacity="0.9" stroke="{t["chipBorder"]}" stroke-width="1.2"/>'
            f'<image href="{chip_logo[key]}" x="{cx + 9:.1f}" y="{cy + 9}" width="30" height="30" clip-path="url(#l{key})"/>'
            f'<rect x="{cx + 9:.1f}" y="{cy + 9}" width="30" height="30" rx="8" fill="none" stroke="{t["chipBorder"]}"/>'
            f'<text x="{cx + 50:.1f}" y="{cy + 30}" font-size="17"><tspan font-weight="500" fill="{t["muted"]}">{x(pre)}</tspan>'
            f'<tspan font-weight="700" fill="{t["heading"]}">{x(bold)}</tspan></text>'
        )
        cx += cw + 12
    if cx - 12 > W - PAD:
        raise SystemExit(f'chips too wide: end at {cx - 12:.0f}')

    parts.append("</g>")
    parts.append(f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="23.25" fill="none" stroke="url(#hair)" stroke-width="1.5"/>')

    faces = "".join(font_face(INTER, w, "InterEmbed", s) for w, s in used.items() if s)
    css = (
        faces
        + f"text{{font-family:{SANS};}}"
        + ".glow1{animation:drift1 14s ease-in-out infinite alternate}.glow2{animation:drift2 18s ease-in-out infinite alternate}"
        + "@keyframes drift1{to{transform:translate(-90px,40px)}}@keyframes drift2{to{transform:translate(110px,-30px)}}"
        + ".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.2s cubic-bezier(0,0,.2,1) infinite}"
        + "@keyframes ping{0%{transform:scale(1);opacity:.7}80%,100%{transform:scale(2.6);opacity:0}}"
        + "[class^=r]{transform-box:fill-box;transform-origin:left center}"
        + "".join(css_typing)
        + ".caretMove{animation:cm 18s infinite}@keyframes cm{" + "".join(caret_frames) + "}"
        + ".caret{animation:blink 1s steps(2,start) infinite}@keyframes blink{to{visibility:hidden}}"
        + "@media (prefers-reduced-motion:reduce){*{animation:none!important}.p{opacity:0}.p0{opacity:1}"
        + f".caretMove{{transform:translateX({measure(INTER, 500, PHRASES[0], tsize) + 3:.1f}px)}}}}"
    )
    title = "Sanjay Gupta, Full-Stack Software Engineer: Tech Lead at Duleko, building FLITO, joining EPAM Systems in January 2027"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{x(title)}">'
        f"<title>{x(title)}</title><defs>{defs}</defs><style>{css}</style>"
        + "".join(parts)
        + "</svg>"
    )


# --------------------------------------------------------------------------- buttons
LINKEDIN_PATH = (
    "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046"
    "c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 1 1 0-4.125 2.062 2.062 0 0 1 0 4.125z"
    "M7.119 20.452H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271"
    "V1.729C24 .774 23.2 0 22.222 0h.003z"
)
LEETCODE_PATH = re.search(r'd="([^"]+)"', open(LEETCODE, encoding="utf-8").read()).group(1)

STROKE = 'fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
ICONS = {
    "portfolio": lambda c: f'<g {STROKE.format(c=c)}><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.6 3.9 5.6 3.9 9s-1.3 6.4-3.9 9c-2.6-2.6-3.9-5.6-3.9-9S9.4 5.6 12 3z"/></g>',
    "resume": lambda c: f'<g {STROKE.format(c=c)}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/></g>',
    "linkedin": lambda c: f'<path fill="{c}" d="{LINKEDIN_PATH}"/>',
    "leetcode": lambda c: f'<path fill="{c}" d="{LEETCODE_PATH}"/>',
    "email": lambda c: f'<g {STROKE.format(c=c)}><rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m4 7 8 6 8-6"/></g>',
}
BUTTONS = [
    ("portfolio", "Portfolio"),
    ("resume", "Resume"),
    ("linkedin", "LinkedIn"),
    ("leetcode", "LeetCode"),
    ("email", "Email"),
]


def button(key, label, theme_name):
    t = THEMES[theme_name]
    c = t["brand"][key]
    tw = measure(INTER, 600, label, 16)
    bh = 44
    bw = 8 + 28 + 11 + tw + 10 + 12 + 16
    ax = 8 + 28 + 11 + tw + 10
    css = font_face(INTER, 600, "InterEmbed", label) + f"text{{font-family:{SANS};}}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw:.1f}" height="{bh}" viewBox="0 0 {bw:.1f} {bh}" role="img" aria-label="{label}">'
        f"<title>{label}</title><style>{css}</style>"
        f'<rect x="0.75" y="0.75" width="{bw - 1.5:.1f}" height="{bh - 1.5}" rx="{(bh - 1.5) / 2}" fill="{t["btn"]}" stroke="{t["btnBorder"]}" stroke-width="1.5"/>'
        f'<rect x="8" y="8" width="28" height="28" rx="8" fill="{c}" fill-opacity="{t["tintOp"]}"/>'
        f'<g transform="translate(13 13) scale({18 / 24:.4f})">{ICONS[key](c)}</g>'
        f'<text x="47" y="27.6" font-size="16" font-weight="600" fill="{t["btnText"]}">{label}</text>'
        f'<g transform="translate({ax:.1f} 16) scale(0.5)" {STROKE.format(c=t["btnMuted"])}><path d="M7 17 17 7M9 7h8v8"/></g>'
        "</svg>"
    )


# --------------------------------------------------------------------------- editor card
# (text, kind) tokens per line; kinds map to theme colours.
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


def editor(theme_name):
    t = THEMES[theme_name]
    ew, bar, top, lh, fs = 1000, 48, 26, 36, 20.5
    code_x, gut_x = 92, 60
    status_h = 34
    eh = bar + top + lh * len(CODE) + 18 + status_h
    mono_text = "".join(tok for line in CODE for tok, _ in line) + "0123456789"
    ui_text = "sanjay.tsTypeScriptmain0 problemsUTF-8Ln 14, Col 12LF"
    rows = []
    for i, line in enumerate(CODE):
        y = bar + top + lh * i + 24
        spans = "".join(
            f'<tspan fill="{t[kind]}">{x(tok)}</tspan>' if kind else x(tok) for tok, kind in line
        )
        rows.append(
            f'<text x="{gut_x}" y="{y}" text-anchor="end" font-size="{fs - 2}" fill="{t["gutter"]}" class="mono">{i + 1}</text>'
            f'<text x="{code_x}" y="{y}" font-size="{fs}" fill="{t["punc"]}" class="mono" xml:space="preserve">{spans}</text>'
        )
    last = "".join(tok for tok, _ in CODE[-1])
    caret_x = code_x + measure(CASCADIA, 400, last, fs) + 2
    caret_y = bar + top + lh * (len(CODE) - 1) + 24 - 19
    # minimap: one bar per line, length by character count
    mini = []
    for i, line in enumerate(CODE):
        text = "".join(tok for tok, _ in line)
        indent = len(text) - len(text.lstrip())
        mini.append(
            f'<rect x="{900 + indent * 1.2:.1f}" y="{bar + top + i * 7}" width="{max(4, len(text.strip()) * 1.15):.1f}" height="3" rx="1.5" fill="{t["mini"]}"/>'
        )
    tab_label = "sanjay.ts"
    tab_w = 16 + 22 + 8 + measure(INTER, 600, tab_label, 14) + 18
    status_items_l = [("main", 600), ("0 problems", 500)]
    status_items_r = ["Ln 14, Col 12", "UTF-8", "LF", "TypeScript"]
    sb_y = eh - status_h
    sb = [
        f'<path d="M0 {sb_y}H{ew}V{eh - 16}a16 16 0 0 1-16 16H16a16 16 0 0 1-16-16z" fill="{t["status"]}"/>',
        f'<g transform="translate(18 {sb_y + 9}) scale(0.67)" {STROKE.format(c=t["statusText"])}><circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="8" r="2.5"/><path d="M6 8.5v7M18 10.5c0 4-4 4.5-9.5 6"/></g>',
    ]
    sx = 42
    for label, wght in status_items_l:
        sb.append(f'<text x="{sx}" y="{sb_y + 22}" font-size="13" font-weight="{wght}" fill="{t["statusText"]}">{label}</text>')
        sx += measure(INTER, wght, label, 13) + 22
    rx_ = ew - 18
    for label in status_items_r:
        sb.append(f'<text x="{rx_}" y="{sb_y + 22}" font-size="13" font-weight="500" text-anchor="end" fill="{t["statusText"]}" fill-opacity="0.92">{label}</text>')
        rx_ -= measure(INTER, 500, label, 13) + 22
    css = (
        font_face(INTER, 600, "InterEmbed", ui_text)
        + font_face(INTER, 500, "InterEmbed", ui_text)
        + font_face(CASCADIA, 400, "CascadiaEmbed", mono_text)
        + f"text{{font-family:{SANS};}}.mono{{font-family:{MONO};white-space:pre;}}"
        + ".cursor{animation:blink 1.1s steps(2,start) infinite}@keyframes blink{to{visibility:hidden}}"
        + "@media (prefers-reduced-motion:reduce){.cursor{animation:none}}"
    )
    title = "sanjay.ts: role Full-Stack Software Engineer; now Tech Lead at Duleko and builder of FLITO; next AI Native Software Engineering Intern at EPAM Systems from January 2027"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ew}" height="{eh}" viewBox="0 0 {ew} {eh}" role="img" aria-label="{x(title)}">'
        f"<title>{x(title)}</title><style>{css}</style>"
        f'<defs><clipPath id="win"><rect width="{ew}" height="{eh}" rx="16"/></clipPath></defs>'
        f'<g clip-path="url(#win)">'
        f'<rect width="{ew}" height="{eh}" fill="{t["ed"]}"/>'
        f'<rect width="{ew}" height="{bar}" fill="{t["edBar"]}"/>'
        f'<path d="M0 {bar - 0.5}H{ew}" stroke="{t["edBorder"]}"/>'
        f'<circle cx="24" cy="24" r="6.5" fill="#FF5F57"/><circle cx="46" cy="24" r="6.5" fill="#FEBC2E"/><circle cx="68" cy="24" r="6.5" fill="#28C840"/>'
        f'<path d="M96 {bar}V18a8 8 0 0 1 8-8h{tab_w - 16:.1f}a8 8 0 0 1 8 8V{bar}z" fill="{t["edTab"]}" stroke="{t["edBorder"]}"/>'
        f'<rect x="96" y="{bar - 1.5}" width="{tab_w:.1f}" height="3" fill="{t["edTab"]}"/>'
        f'<rect x="104" y="10" width="{tab_w - 16:.1f}" height="2" rx="1" fill="#6366F1"/>'
        f'<rect x="112" y="21" width="22" height="16" rx="3.5" fill="#3178C6"/>'
        f'<text x="123" y="33" text-anchor="middle" font-size="10" font-weight="600" fill="#FFFFFF">TS</text>'
        f'<text x="142" y="34" font-size="14" font-weight="600" fill="{t["btnText"]}">{tab_label}</text>'
        f'<path d="M{gut_x + 16} {bar}V{sb_y}" stroke="{t["edBorder"]}" stroke-opacity="0.6"/>'
        + "".join(rows)
        + f'<rect class="cursor" x="{caret_x:.1f}" y="{caret_y}" width="2.4" height="24" fill="#6366F1"/>'
        + "".join(mini)
        + "".join(sb)
        + "</g>"
        f'<rect x="0.75" y="0.75" width="{ew - 1.5}" height="{eh - 1.5}" rx="15.25" fill="none" stroke="{t["edBorder"]}" stroke-width="1.5"/>'
        "</svg>"
    )


# --------------------------------------------------------------------------- write
for theme in THEMES:
    files = {f"hero-{theme}.svg": hero(theme), f"about-{theme}.svg": editor(theme)}
    for key, label in BUTTONS:
        files[f"btn-{key}-{theme}.svg"] = button(key, label, theme)
    for name, svg in files.items():
        with open(f"{OUT}/{name}", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)
        print(f"{name}: {len(svg.encode()) / 1024:.1f} KB")
