#!/usr/bin/env python3
"""Builds the animated SVGs in assets/ that the profile README shows.

Edit the copy in main() at the bottom, then run:
    python3 tools/build_assets.py

Everything is plain SVG + SMIL/CSS animation, so GitHub renders it as-is.
Only monospace system fonts are used, which keeps widths predictable.
"""
import math
import random
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

ASSETS = Path(__file__).resolve().parent.parent / "assets"

FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
BG = "#07090d"
PANEL = "#0b0f15"
EDGE = "#262e3a"
GRIDLINE = "#121922"
INK = "#e6edf3"
BODY = "#b4bec9"
DIM = "#6e7781"
LIMB = "#c9d1d9"
FILL = "#121a24"
GREEN = "#a3ff12"
CYAN = "#22d3ee"
MAGENTA = "#ff2bd6"
AMBER = "#ffc400"
ORANGE = "#ff8a3d"
BLUE = "#4d7cff"
RED = "#ff4d5e"

BASE_CSS = (
    "text{font-family:%s}.b{font-weight:700}"
    ".blink{animation:blink 1.2s steps(1) infinite}"
    "@keyframes blink{50%%{opacity:0}}" % FONT
)


def esc(s):
    return escape(s, {'"': "&quot;"})


def svg(w, h, label, body, css="", defs=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">\n'
        f"<title>{esc(label)}</title>\n<style>{BASE_CSS}{css}</style>\n"
        f"<defs>{defs}</defs>\n{body}\n</svg>\n"
    )


def write(name, content):
    ASSETS.mkdir(exist_ok=True)
    path = ASSETS / f"{name}.svg"
    path.write_text(content)
    print(f"{path.relative_to(ASSETS.parent)}  {len(content) / 1024:.1f} KB")


# --- SMIL helpers --------------------------------------------------------------

def rot(angles, cx, cy, dur, key_times=None):
    vals = ";".join(f"{a} {cx} {cy}" for a in angles)
    kt = f' keyTimes="{key_times}"' if key_times else ""
    return (f'<animateTransform attributeName="transform" type="rotate" values="{vals}"{kt} '
            f'dur="{dur}s" repeatCount="indefinite"/>')


def shift(points, dur, key_times=None):
    vals = ";".join(f"{x} {y}" for x, y in points)
    kt = f' keyTimes="{key_times}"' if key_times else ""
    return (f'<animateTransform attributeName="transform" type="translate" values="{vals}"{kt} '
            f'dur="{dur}s" repeatCount="indefinite"/>')


def window(start, end, dur):
    """Opacity 1 between fractions start and end of the cycle, 0 otherwise."""
    return (f'<animate attributeName="opacity" values="0;1;0" keyTimes="0;{start:.3f};{end:.3f}" '
            f'calcMode="discrete" dur="{dur}s" repeatCount="indefinite"/>')


def march(dash_period, dur, reverse=False):
    vals = f"0;{dash_period}" if reverse else f"{dash_period};0"
    return (f'<animate attributeName="stroke-dashoffset" values="{vals}" dur="{dur}s" '
            f'repeatCount="indefinite"/>')


def travel(path, start, end, dur, rotate=False):
    r = ' rotate="auto"' if rotate else ""
    return (f'<animateMotion path="{path}" keyPoints="0;0;1;1" keyTimes="0;{start:.3f};{end:.3f};1" '
            f'calcMode="linear" dur="{dur}s" repeatCount="indefinite"{r}/>')


def poly_len(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def bezier_len(p0, c1, c2, p1, steps=40):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        pts.append(tuple(mt**3 * a + 3 * mt * mt * t * b + 3 * mt * t * t * c + t**3 * d
                         for a, b, c, d in zip(p0, c1, c2, p1)))
    return pts


def closed_spline(points):
    """Catmull-Rom through points as a closed cubic path; returns (d, samples)."""
    n = len(points)
    d = f"M{points[0][0]},{points[0][1]}"
    samples = []
    for i in range(n):
        p0, p1, p2, p3 = (points[(i + k) % n] for k in (-1, 0, 1, 2))
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]},{p2[1]}"
        seg = bezier_len(p1, c1, c2, p2)
        samples.extend(seg if not samples else seg[1:])
    return d, samples


# --- card chrome ---------------------------------------------------------------

GRID_DEF = (f'<pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse">'
            f'<path d="M22 0H0V22" fill="none" stroke="{GRIDLINE}"/></pattern>')


def frame(w, h):
    return (f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="16" fill="{PANEL}" '
            f'stroke="{EDGE}" stroke-width="2"/>')


def header(w, accent, tag, status):
    cw = len(status) * 7.8 + 36
    x = w - 24 - cw
    return (
        f'<text x="24" y="36" class="b" font-size="13" letter-spacing="2" fill="{accent}">{esc(tag)}</text>'
        f'<rect x="{x:.1f}" y="18" width="{cw:.1f}" height="26" rx="13" fill="{accent}" '
        f'fill-opacity=".1" stroke="{accent}" stroke-opacity=".6"/>'
        f'<circle class="blink" cx="{x + 15:.1f}" cy="31" r="4" fill="{accent}"/>'
        f'<text x="{x + 27:.1f}" y="35.5" class="b" font-size="13" fill="{accent}">{esc(status)}</text>'
    )


def footer(x, y, accent, text, size):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{DIM}">'
            f'<tspan fill="{accent}">▸ </tspan>{esc(text)}</text>')


def illus_area(x, y, w, h, illus):
    return (f'<clipPath id="ia"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/></clipPath>',
            f'<g clip-path="url(#ia)"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#grid)"/>'
            f'<g transform="translate({x} {y})">{illus}</g></g>'
            f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="10" fill="none" stroke="{EDGE}"/>')


def grid_card(slug, accent, tag, status, title, desc, foot, illus, defs="", css=""):
    """Half-width card: 536x146 illustration on top, copy below."""
    w, h = 560, 372
    assert len(title) <= 33, title
    lines = textwrap.wrap(desc, 48, break_on_hyphens=False)
    assert len(lines) <= 3, (slug, lines)
    clip, area = illus_area(12, 52, 536, 146, illus)
    body = [frame(w, h), header(w, accent, tag, status), area,
            f'<text x="24" y="238" class="b" font-size="25" fill="{INK}">{esc(title)}</text>']
    body += [f'<text x="24" y="{268 + 24 * i}" font-size="17" fill="{BODY}">{esc(ln)}</text>'
             for i, ln in enumerate(lines)]
    body.append(footer(24, 350, accent, foot, 13))
    write(slug, svg(w, h, f"{title}: {desc}", "\n".join(body), css, GRID_DEF + clip + defs))


def feature_card(slug, accent, tag, status, title, desc, foot, illus, defs="", css=""):
    """Full-width card: 556x296 illustration left, copy right."""
    w, h = 1120, 360
    tlines = textwrap.wrap(title, 27, break_on_hyphens=False)
    assert len(tlines) <= 2, tlines
    dlines = textwrap.wrap(desc, 44, break_on_hyphens=False)
    assert len(dlines) <= 5, (slug, dlines)
    clip, area = illus_area(12, 52, 556, 296, illus)
    body = [frame(w, h), header(w, accent, tag, status), area]
    body += [f'<text x="600" y="{104 + 38 * i}" class="b" font-size="30" fill="{INK}">{esc(t)}</text>'
             for i, t in enumerate(tlines)]
    y0 = 104 + 38 * len(tlines) + 14
    body += [f'<text x="600" y="{y0 + 26 * i}" font-size="18" fill="{BODY}">{esc(ln)}</text>'
             for i, ln in enumerate(dlines)]
    body.append(footer(600, 334, accent, foot, 14))
    write(slug, svg(w, h, f"{title} {desc}", "\n".join(body), css, GRID_DEF + clip + defs))


# --- illustrations ---------------------------------------------------------------

def illus_telekinex():
    rnd = random.Random(4)
    out, defs = [], []
    px, py, pw, ph = 10, 18, 282, 260
    out.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="8" fill="{BG}" stroke="#1f2833"/>')
    out.append(f'<text x="{px + 12}" y="{py + 22}" font-size="11" letter-spacing="1" fill="{DIM}">'
               f'EEG · 4 CH · LIVE</text>')
    wx, ww = 52, 228
    defs.append(f'<clipPath id="eeg"><rect x="{wx}" y="{py}" width="{ww}" height="{ph}"/></clipPath>')
    for name, yc in zip(["C3", "Cz", "C4", "Pz"], [78, 130, 182, 234]):
        comps = [(rnd.choice([2, 3, 4, 5, 6, 7, 9, 11, 13, 17, 19, 23]), rnd.uniform(.2, 1),
                  rnd.uniform(0, 6.28)) for _ in range(5)]
        norm = sum(a for _, a, _ in comps)
        pts = " ".join(
            f"{wx + k},{yc + 18 * sum(a * math.sin(2 * math.pi * n * k / ww + p) for n, a, p in comps) / norm:.1f}"
            for k in range(0, 2 * ww + 1, 3))
        out.append(f'<text x="{px + 12}" y="{yc + 4}" font-size="11" fill="{DIM}">{name}</text>')
        out.append(f'<line x1="{wx}" y1="{yc}" x2="{wx + ww}" y2="{yc}" stroke="#141c26"/>')
        out.append(f'<g clip-path="url(#eeg)"><polyline points="{pts}" fill="none" stroke="{CYAN}" '
                   f'stroke-width="1.6" stroke-linejoin="round">'
                   f'<animateTransform attributeName="transform" type="translate" from="0 0" '
                   f'to="-{ww} 0" dur="3s" repeatCount="indefinite"/></polyline></g>')
    out.append(f'<line x1="{wx + ww}" y1="{py + 30}" x2="{wx + ww}" y2="{py + ph - 8}" '
               f'stroke="{MAGENTA}" stroke-width="2"/>')

    # signal flow into the decoder and out to the robot
    for x1, x2 in ((292, 318), (418, 452)):
        out.append(f'<line x1="{x1}" y1="148" x2="{x2}" y2="148" stroke="{MAGENTA}" stroke-width="2" '
                   f'stroke-dasharray="3 5">{march(16, .5)}</line>')
    out.append(f'<rect x="318" y="116" width="100" height="64" rx="10" fill="{FILL}" stroke="{MAGENTA}" '
               f'stroke-width="2"/>')
    out.append(f'<text x="368" y="144" text-anchor="middle" class="b" font-size="14" fill="{INK}">EEGNet</text>')
    out.append(f'<text x="368" y="163" text-anchor="middle" font-size="11" fill="{DIM}">12.6K params</text>')
    out.append(f'<text x="368" y="210" text-anchor="middle" font-size="11" fill="{DIM}">decoded</text>')
    classes = ["RIGHT FIST", "LEFT FIST", "BOTH FISTS", "TONGUE TAP", "RELAX"]
    for i, c in enumerate(classes):
        out.append(f'<text x="368" y="230" text-anchor="middle" class="b" font-size="13" fill="{MAGENTA}" '
                   f'opacity="0">▸ {c}{window(i / 5, (i + 1) / 5, 7.5)}</text>')

    # Unitree G1, front view, walking in place
    ground = 262
    out.append(f'<line x1="430" y1="{ground}" x2="556" y2="{ground}" stroke="#2a3442" stroke-width="2" '
               f'stroke-dasharray="10 8">{march(18, .6, reverse=True)}</line>')
    limb = f'stroke="{LIMB}" stroke-linecap="round"'
    out.append(f'<g>{shift([(0, 0), (0, -3), (0, 0)], .6)}'
               f'<g>{rot([16, -16, 16], 482, 132, 1.2)}<line x1="482" y1="132" x2="478" y2="182" {limb} stroke-width="7"/></g>'
               f'<g>{rot([18, -18, 18], 493, 186, 1.2)}<line x1="493" y1="186" x2="493" y2="256" {limb} stroke-width="9"/></g>'
               f'<g>{rot([-18, 18, -18], 507, 186, 1.2)}<line x1="507" y1="186" x2="507" y2="256" {limb} stroke-width="9"/></g>'
               f'<rect x="484" y="124" width="32" height="66" rx="9" fill="{FILL}" stroke="{LIMB}" stroke-width="2.5"/>'
               f'<circle class="blink" cx="500" cy="146" r="4" fill="{MAGENTA}"/>'
               f'<g>{rot([-16, 16, -16], 518, 132, 1.2)}<line x1="518" y1="132" x2="522" y2="182" {limb} stroke-width="7"/></g>'
               f'<line x1="500" y1="118" x2="500" y2="124" {limb} stroke-width="5"/>'
               f'<circle cx="500" cy="104" r="16" fill="{FILL}" stroke="{LIMB}" stroke-width="2.5"/>'
               f'<rect x="489" y="99" width="22" height="8" rx="4" fill="{CYAN}"/></g>')
    out.append(f'<text x="500" y="76" text-anchor="middle" class="b" font-size="11" letter-spacing="1" '
               f'fill="{DIM}">UNITREE G1</text>')
    return "".join(out), "".join(defs)


def node(cx, cy, label, accent):
    return (f'<rect x="{cx - 86}" y="{cy - 20}" width="172" height="40" rx="10" fill="{FILL}" stroke="#2f3a48"/>'
            f'<rect x="{cx - 74}" y="{cy - 8}" width="22" height="16" rx="4" fill="none" stroke="{accent}" stroke-width="2"/>'
            f'<circle cx="{cx - 67}" cy="{cy}" r="2" fill="{accent}"/><circle cx="{cx - 59}" cy="{cy}" r="2" fill="{accent}"/>'
            f'<text x="{cx - 44}" y="{cy + 4.5}" font-size="13" fill="{INK}">{label}</text>')


def illus_agora():
    out = []
    dur = 4
    reg = (278, 138)
    nodes = [(98, 50, "tripplanner-7", AMBER), (458, 50, "vision-oracle-3", CYAN),
             (98, 214, "market-monitor", CYAN), (458, 214, "dataset-seller", CYAN)]
    for cx, cy, _, _ in nodes:
        sx = cx + (86 if cx < reg[0] else -86)
        out.append(f'<line x1="{sx}" y1="{cy}" x2="{reg[0]}" y2="{reg[1]}" stroke="#2a3442" '
                   f'stroke-width="1.5" stroke-dasharray="4 6">{march(20, 2)}</line>')
    out.append(f'<circle cx="{reg[0]}" cy="{reg[1]}" r="36" fill="{FILL}" stroke="{AMBER}" stroke-width="2"/>'
               f'<circle cx="{reg[0]}" cy="{reg[1]}" r="28" fill="none" stroke="{AMBER}" stroke-opacity=".5" '
               f'stroke-dasharray="3 5">{rot([0, 360], reg[0], reg[1], 8)}</circle>'
               f'<text x="{reg[0]}" y="{reg[1] + 4}" text-anchor="middle" class="b" font-size="10" '
               f'letter-spacing="1" fill="{AMBER}">REGISTRY</text>')
    for cx, cy, label, accent in nodes:
        out.append(node(cx, cy, label, accent))
    out.append(f'<text x="98" y="88" text-anchor="middle" font-size="10" fill="{DIM}">buyer agent</text>'
               f'<text x="458" y="88" text-anchor="middle" font-size="10" fill="{DIM}">seller agent</text>')

    fwd, back = "M186,42 Q278,0 370,42", "M370,60 Q278,104 186,60"
    for d in (fwd, back):
        out.append(f'<path d="{d}" fill="none" stroke="#2a3442" stroke-width="1.5"/>')
    bolt = f'<path d="M2,-10 L-6,1 L-1,1 L-3,10 L6,-2 L1,-2 Z" fill="{AMBER}"/>'
    packets = [  # (path, start, end, glyph)
        (fwd, .00, .20, f'<circle r="4" fill="{INK}"/><text x="8" y="-6" font-size="10" fill="{INK}">POST</text>'),
        (back, .22, .40, f'<circle r="4" fill="{RED}"/><text x="8" y="14" font-size="10" fill="{RED}">402</text>'),
        (fwd, .42, .65, bolt + f'<text x="9" y="-6" class="b" font-size="11" fill="{AMBER}">240 sat</text>'),
        (back, .67, .87, f'<rect x="-4" y="-4" width="8" height="8" fill="{CYAN}"/>'
                         f'<text x="8" y="14" font-size="10" fill="{CYAN}">200 OK</text>'),
        ("M440,72 L300,116", .88, .99, f'<circle r="3" fill="{AMBER}"/>'),
    ]
    for path, a, b, glyph in packets:
        out.append(f'<g opacity="0">{window(a, b, dur)}{travel(path, a, b, dur)}{glyph}</g>')

    steps = [("POST /listing-verify", .00, .22), ("402 + invoice", .22, .42),
             ("pay 240 sat", .42, .67), ("200 OK + proof", .67, 1.0)]
    widths = [len(s) * 7.2 + 18 for s, _, _ in steps]
    x = (556 - sum(widths) - 18 * 3) / 2
    for (label, a, b), wdt in zip(steps, widths):
        color = AMBER if "sat" in label else INK
        out.append(f'<g opacity=".3"><animate attributeName="opacity" values=".3;1;.3" '
                   f'keyTimes="0;{a:.2f};{b:.2f}" calcMode="discrete" dur="{dur}s" repeatCount="indefinite"/>'
                   f'<rect x="{x:.1f}" y="262" width="{wdt:.1f}" height="24" rx="6" fill="{FILL}" stroke="{color}"/>'
                   f'<text x="{x + 9:.1f}" y="278" font-size="12" fill="{color}">{label}</text></g>')
        x += wdt
        if label != steps[-1][0]:
            out.append(f'<text x="{x + 4:.1f}" y="278" font-size="12" fill="{DIM}">→</text>')
        x += 18
    return "".join(out), ""


def robot_head(cx, cy, color, name, talk, dur, blink_dur):
    a, b = talk
    out = [f'<line x1="{cx}" y1="{cy - 28}" x2="{cx}" y2="{cy - 42}" stroke="{color}" stroke-width="2"/>',
           f'<circle cx="{cx}" cy="{cy - 44}" r="4" fill="{color}"/>',
           f'<rect x="{cx - 36}" y="{cy - 28}" width="72" height="54" rx="14" fill="{FILL}" stroke="{color}" stroke-width="2"/>']
    for ex in (cx - 15, cx + 15):
        out.append(f'<ellipse cx="{ex}" cy="{cy - 6}" rx="6" ry="6" fill="{color}">'
                   f'<animate attributeName="ry" values="6;6;.8;6" keyTimes="0;.9;.95;1" dur="{blink_dur}s" '
                   f'repeatCount="indefinite"/></ellipse>')
    # idle mouth, swapped for bouncing bars while this robot talks
    out.append(f'<line x1="{cx - 18}" y1="{cy + 12}" x2="{cx + 18}" y2="{cy + 12}" stroke="{color}" '
               f'stroke-width="2"><animate attributeName="opacity" values="1;0;1" keyTimes="0;{a};{b}" '
               f'calcMode="discrete" dur="{dur}s" repeatCount="indefinite"/></line>')
    bars = []
    for i in range(5):
        hs = [2, 10, 4, 12, 6, 2] if i % 2 else [8, 3, 12, 5, 10, 8]
        hv = ";".join(str(v) for v in hs)
        yv = ";".join(f"{cy + 12 - v / 2}" for v in hs)
        bars.append(f'<rect x="{cx - 20 + i * 9}" width="5" rx="1.5" fill="{color}">'
                    f'<animate attributeName="height" values="{hv}" dur=".6s" repeatCount="indefinite"/>'
                    f'<animate attributeName="y" values="{yv}" dur=".6s" repeatCount="indefinite"/></rect>')
    out.append(f'<g opacity="0">{window(a, b, dur)}{"".join(bars)}</g>')
    out.append(f'<text x="{cx}" y="{cy + 48}" text-anchor="middle" class="b" font-size="12" '
               f'letter-spacing="1" fill="{color}">{name}</text>')
    return "".join(out)


def radio_arcs(x, y, direction, color, talk, dur):
    arcs = []
    for k in (1, 2, 3):
        r = 9 * k
        sx = x + direction * r * math.cos(math.pi / 4)
        y1, y2 = y - r * math.sin(math.pi / 4), y + r * math.sin(math.pi / 4)
        sweep = 1 if direction > 0 else 0
        arcs.append(f'<path d="M{sx:.1f},{y1:.1f} A{r} {r} 0 0 {sweep} {sx:.1f},{y2:.1f}" fill="none" '
                    f'stroke="{color}" stroke-width="2"><animate attributeName="opacity" values=".15;1;.15" '
                    f'dur=".9s" begin="{k * .3:.1f}s" repeatCount="indefinite"/></path>')
    return f'<g opacity="0">{window(*talk, dur)}{"".join(arcs)}</g>'


def bubble(x, y, w, text, color, tail_left, shown, dur):
    if tail_left:
        tail = f'M{x + 2},{y + 12} L{x - 12},{y + 22} L{x + 2},{y + 24} Z'
    else:
        tail = f'M{x + w - 2},{y + 12} L{x + w + 12},{y + 22} L{x + w - 2},{y + 24} Z'
    return (f'<g opacity="0">{window(*shown, dur)}'
            f'<path d="{tail}" fill="{FILL}" stroke="{color}" stroke-width="1.5"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="32" rx="10" fill="{FILL}" stroke="{color}" stroke-width="1.5"/>'
            f'<text x="{x + 14}" y="{y + 21}" font-size="13" fill="{INK}">{esc(text)}</text></g>')


def illus_telephone():
    dur = 6
    alpha, charlie = (.05, .45), (.5, .9)
    out = [robot_head(70, 70, CYAN, "ALPHA", alpha, dur, 3.7),
           robot_head(466, 70, MAGENTA, "CHARLIE", charlie, dur, 4.3),
           radio_arcs(78, 26, 1, CYAN, alpha, dur),
           radio_arcs(458, 26, -1, MAGENTA, charlie, dur),
           bubble(124, 24, 204, "sector 4 clear. over.", CYAN, True, (.05, .92), dur),
           bubble(212, 76, 204, "copy. patrol speed x2.", MAGENTA, False, (.5, .92), dur)]
    return "".join(out), ""


def dog(walk=.5):
    """Side-view robot dog, feet on y=0, facing right."""
    leg = f'stroke="{LIMB}" stroke-width="5" stroke-linecap="round"'
    out = []
    for i, lx in enumerate((-26, -14, 16, 28)):
        swing = [16, -16, 16] if i % 2 else [-16, 16, -16]
        out.append(f'<g>{rot(swing, lx, -20, walk)}<line x1="{lx}" y1="-20" x2="{lx}" y2="0" {leg}/></g>')
    out.append(f'<g>{rot([-15, 15, -15], -38, -36, .4)}<line x1="-38" y1="-36" x2="-50" y2="-48" {leg}/></g>')
    out.append(f'<rect x="-38" y="-40" width="74" height="24" rx="11" fill="{FILL}" stroke="{LIMB}" stroke-width="2"/>'
               f'<rect x="30" y="-54" width="28" height="22" rx="7" fill="{FILL}" stroke="{LIMB}" stroke-width="2"/>'
               f'<path d="M34,-54 L38,-63 L44,-54" fill="none" stroke="{LIMB}" stroke-width="2"/>'
               f'<circle cx="49" cy="-45" r="2.5" fill="{GREEN}"/>')
    return "".join(out)


def illus_point():
    out, dur = [], 5
    out.append(f'<line x1="0" y1="128" x2="536" y2="128" stroke="#2a3442" stroke-width="2" stroke-dasharray="6 6"/>')
    hand = f'fill="{FILL}" stroke="{GREEN}" stroke-width="2"'
    out.append(f'<g transform="translate(20 44) rotate(10)">'
               f'<rect x="-30" y="10" width="42" height="30" rx="8" {hand}/>'
               f'<rect x="4" y="4" width="40" height="40" rx="12" {hand}/>'
               f'<rect x="36" y="6" width="46" height="13" rx="6.5" {hand}/>'
               f'<rect x="14" y="-3" width="26" height="11" rx="5.5" {hand}/>'
               f'<path d="M44,25 h-8 M44,33 h-8" stroke="{GREEN}" stroke-width="2"/></g>')
    out.append(f'<path d="M110,66 Q300,30 460,118" fill="none" stroke="{GREEN}" stroke-opacity=".7" '
               f'stroke-width="2" stroke-dasharray="6 7">{march(26, .8)}</path>')
    out.append(f'<ellipse cx="472" cy="128" rx="20" ry="5" fill="{GREEN}" fill-opacity=".15" stroke="{GREEN}"/>'
               f'<ellipse cx="472" cy="128" rx="20" ry="5" fill="none" stroke="{GREEN}">'
               f'<animate attributeName="rx" values="20;36" dur="1.5s" repeatCount="indefinite"/>'
               f'<animate attributeName="ry" values="5;10" dur="1.5s" repeatCount="indefinite"/>'
               f'<animate attributeName="opacity" values="1;0" dur="1.5s" repeatCount="indefinite"/></ellipse>')
    out.append(f'<g>{shift([(0, 0), (0, 0), (46, 0)], dur, "0;.8;1")}'
               f'<animate attributeName="opacity" values="1;1;0" keyTimes="0;.85;1" dur="{dur}s" repeatCount="indefinite"/>'
               f'<circle cx="498" cy="121" r="7" fill="{INK}"/>'
               f'<path d="M498,117 l3,2.5 -1.2,3.5 h-3.6 l-1.2,-3.5 Z" fill="{BG}"/></g>')
    out.append(f'<g>{shift([(150, 128), (414, 128), (414, 128)], dur, "0;.8;1")}'
               f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.08;.9;1" dur="{dur}s" repeatCount="indefinite"/>'
               f'{dog()}</g>')
    return "".join(out), ""


def illus_escape():
    cols, rows, cs = 13, 4, 30
    ox, oy = 73, 13
    rnd = random.Random(11)
    seen, stack, open_ = {(0, 0)}, [(0, 0)], set()
    while stack:
        c, r = stack[-1]
        nbrs = [(c + dc, r + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if 0 <= c + dc < cols and 0 <= r + dr < rows and (c + dc, r + dr) not in seen]
        if nbrs:
            nxt = rnd.choice(nbrs)
            open_.add(frozenset([(c, r), nxt]))
            seen.add(nxt)
            stack.append(nxt)
        else:
            stack.pop()
    r_in, r_out = 1, 2
    walls = []
    for c in range(cols):
        for r in range(rows):
            x, y = ox + c * cs, oy + r * cs
            if c < cols - 1 and frozenset([(c, r), (c + 1, r)]) not in open_:
                walls.append((x + cs, y, x + cs, y + cs))
            if r < rows - 1 and frozenset([(c, r), (c, r + 1)]) not in open_:
                walls.append((x, y + cs, x + cs, y + cs))
    for c in range(cols):
        walls.append((ox + c * cs, oy, ox + (c + 1) * cs, oy))
        walls.append((ox + c * cs, oy + rows * cs, ox + (c + 1) * cs, oy + rows * cs))
    for r in range(rows):
        if r != r_in:
            walls.append((ox, oy + r * cs, ox, oy + (r + 1) * cs))
        if r != r_out:
            walls.append((ox + cols * cs, oy + r * cs, ox + cols * cs, oy + (r + 1) * cs))

    # breadth-first search for the way out
    start, goal = (0, r_in), (cols - 1, r_out)
    prev, queue = {start: None}, [start]
    while queue:
        cur = queue.pop(0)
        if cur == goal:
            break
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (cur[0] + dc, cur[1] + dr)
            if n not in prev and frozenset([cur, n]) in open_:
                prev[n] = cur
                queue.append(n)
    cells, cur = [], goal
    while cur:
        cells.append(cur)
        cur = prev[cur]
    cells.reverse()
    pts = [(ox - 18, oy + r_in * cs + cs / 2)]
    pts += [(ox + c * cs + cs / 2, oy + r * cs + cs / 2) for c, r in cells]
    pts.append((ox + cols * cs + 18, oy + r_out * cs + cs / 2))
    d = "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    length = poly_len(pts)

    dur = 9
    out = ["".join(f'<line x1="{a}" y1="{b}" x2="{c}" y2="{e}" stroke="#3a4656" stroke-width="3" '
                   f'stroke-linecap="round"/>' for a, b, c, e in walls)]
    out.append(f'<path d="{d}" fill="none" stroke="{AMBER}" stroke-opacity=".55" stroke-width="2.5" '
               f'stroke-dasharray="{length:.0f}" stroke-dashoffset="{length:.0f}">'
               f'<animate attributeName="stroke-dashoffset" values="{length:.0f};0;0" keyTimes="0;.85;1" '
               f'dur="{dur}s" repeatCount="indefinite"/></path>')
    ex, ey = ox + cols * cs + 8, oy + r_out * cs + cs / 2
    out.append(f'<text class="blink b" x="{ex}" y="{ey - 12:.0f}" font-size="11" fill="{GREEN}">EXIT</text>')
    out.append(f'<g>{travel(d, 0, .85, dur, rotate=True)}'
               f'<path d="M0,0 L32,-15 A35 35 0 0 1 32,15 Z" fill="{AMBER}" fill-opacity=".2"/>'
               f'<circle r="9" fill="{AMBER}" opacity=".35" filter="url(#glow)"/>'
               f'<circle r="5" fill="{AMBER}"/></g>')
    defs = '<filter id="glow" x="-1" y="-1" width="3" height="3"><feGaussianBlur stdDeviation="3"/></filter>'
    return "".join(out), defs


def illus_animator():
    out = []
    defs = (f'<linearGradient id="spot" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="#fff" stop-opacity=".22"/>'
            f'<stop offset="1" stop-color="#fff" stop-opacity=".02"/></linearGradient>')
    out.append(f'<polygon points="222,0 262,0 352,140 132,140" fill="url(#spot)">'
               f'<animate attributeName="opacity" values="1;.75;1;.9;1" dur="2.3s" repeatCount="indefinite"/></polygon>')
    out.append(f'<ellipse cx="242" cy="134" rx="112" ry="9" fill="{MAGENTA}" fill-opacity=".2"/>')
    star = "M0,-7 L1.6,-1.6 L7,0 L1.6,1.6 L0,7 L-1.6,1.6 L-7,0 L-1.6,-1.6 Z"
    for i, (sx, sy) in enumerate(((150, 40), (346, 28), (378, 96), (118, 100), (300, 64))):
        out.append(f'<g transform="translate({sx} {sy})"><path d="{star}" fill="{AMBER}">'
                   f'<animateTransform attributeName="transform" type="scale" values="0;1.2;0;0" '
                   f'keyTimes="0;.15;.3;1" dur="2.5s" begin="{i * .5}s" repeatCount="indefinite"/></path></g>')

    # the dog itself, a little bigger than the Go2 one and with a face
    near = f'stroke="{INK}" stroke-width="6" stroke-linecap="round"'
    far = f'stroke="#7d8896" stroke-width="6" stroke-linecap="round"'
    g = [f'<g>{rot([-14, 18, -14], -46, -50, .45)}<path d="M-46,-50 Q-66,-60 -70,-80" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/></g>']
    for lx, swing, style in ((-30, [14, -14, 14], far), (20, [-14, 14, -14], far),
                             (-40, [-14, 14, -14], near), (28, [14, -14, 14], near)):
        g.append(f'<g>{rot(swing, lx, -26, .6)}<line x1="{lx}" y1="-26" x2="{lx}" y2="0" {style}/></g>')
        if style == far and lx == 20:
            g.append(f'<rect x="-50" y="-62" width="88" height="40" rx="18" fill="{FILL}" stroke="{INK}" stroke-width="2.5"/>')
    head = [f'<g>{rot([0, 0, -18, 0, 0], 53, -91, 3, "0;.6;.68;.76;1")}'
            f'<path d="M44,-91 L52,-114 L62,-92 Z" fill="{FILL}" stroke="{INK}" stroke-width="2.5"/></g>',
            f'<rect x="30" y="-96" width="54" height="44" rx="16" fill="{FILL}" stroke="{INK}" stroke-width="2.5"/>',
            f'<g transform="translate(64 -77)"><g>'
            f'<animateTransform attributeName="transform" type="scale" values="1 1;1 1;1 .1;1 1" '
            f'keyTimes="0;.9;.95;1" dur="3.4s" repeatCount="indefinite"/>'
            f'<ellipse rx="9" ry="10" fill="{INK}"/><circle cx="3" cy="1" r="4.5" fill="{BG}"/>'
            f'<circle cx="5" cy="-2" r="1.5" fill="{INK}"/></g></g>',
            f'<circle cx="84" cy="-70" r="3.5" fill="{MAGENTA}"/>',
            f'<path d="M70,-60 Q76,-55 82,-60" fill="none" stroke="{INK}" stroke-width="2"/>',
            f'<ellipse cx="52" cy="-63" rx="5" ry="3" fill="{MAGENTA}" fill-opacity=".45"/>']
    g.append(f'<g>{rot([-4, 4, -4], 40, -60, 2)}{"".join(head)}</g>')
    out.append(f'<g transform="translate(222 132)"><g>{shift([(0, 0), (0, -2), (0, 0)], .3)}{"".join(g)}</g></g>')

    # marquee
    out.append(f'<rect x="408" y="14" width="114" height="36" rx="6" fill="{FILL}" stroke="{MAGENTA}" stroke-width="2"/>'
               f'<text x="465" y="38" text-anchor="middle" class="b" font-size="15" letter-spacing="1" fill="{INK}">THE SHOW</text>')
    for row_y in (14, 50):
        for i in range(10):
            delay = "0s" if i % 2 else ".35s"
            out.append(f'<circle cx="{414 + i * 11.5:.1f}" cy="{row_y}" r="2.2" fill="{AMBER}">'
                       f'<animate attributeName="opacity" values="1;.15;1" dur=".7s" begin="{delay}" '
                       f'repeatCount="indefinite"/></circle>')
    return "".join(out), defs


def illus_r1():
    rnd = random.Random(3)
    out = []
    defs = (f'<linearGradient id="vu" x1="228" y1="0" x2="508" y2="0" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{ORANGE}"/><stop offset="1" stop-color="{AMBER}"/></linearGradient>')
    limb = f'stroke="{LIMB}" stroke-width="8" stroke-linecap="round" fill="none"'
    out.append(f'<polyline points="76,68 60,118 62,150" {limb}/>')
    out.append(f'<path d="M74,62 H146 L136,150 H84 Z" fill="{FILL}" stroke="{ORANGE}" stroke-width="2"/>')
    for i in range(3):
        for j in range(3):
            out.append(f'<circle cx="{100 + i * 10}" cy="{90 + j * 10}" r="2.4" fill="{ORANGE}">'
                       f'<animate attributeName="opacity" values="1;.25;1" dur="{.4 + .1 * ((i + j) % 3):.1f}s" '
                       f'repeatCount="indefinite"/></circle>')
    out.append(f'<line x1="144" y1="68" x2="170" y2="46" {limb}/>'
               f'<g>{rot([-20, 14, -20], 170, 46, 1.1)}<line x1="170" y1="46" x2="178" y2="20" {limb}/>'
               f'<circle cx="179" cy="16" r="6" fill="{FILL}" stroke="{LIMB}" stroke-width="2.5"/></g>')
    out.append(f'<rect x="104" y="52" width="12" height="10" fill="{FILL}" stroke="{ORANGE}" stroke-width="2"/>'
               f'<rect x="88" y="14" width="44" height="40" rx="15" fill="{FILL}" stroke="{ORANGE}" stroke-width="2"/>'
               f'<rect x="95" y="27" width="30" height="10" rx="5" fill="{ORANGE}"/>'
               f'<rect x="97" y="29" width="6" height="6" rx="3" fill="#fff" opacity=".8">'
               f'{shift([(0, 0), (16, 0), (0, 0)], 2.2)}</rect>')
    for i in range(28):
        hs = [rnd.choice([6, 10, 16, 24, 34, 46, 60, 72]) for _ in range(5)]
        hs.append(hs[0])
        hv = ";".join(str(v) for v in hs)
        yv = ";".join(str(62 - v / 2) for v in hs)
        d = rnd.uniform(.9, 1.6)
        out.append(f'<rect x="{228 + i * 10}" width="6" rx="2" fill="url(#vu)">'
                   f'<animate attributeName="height" values="{hv}" dur="{d:.2f}s" repeatCount="indefinite"/>'
                   f'<animate attributeName="y" values="{yv}" dur="{d:.2f}s" repeatCount="indefinite"/></rect>')
    out.append(f'<text x="228" y="128" font-size="12" fill="{DIM}">onboard speaker '
               f'<tspan fill="{ORANGE}">▸</tspan> claude-haiku-4-5</text>')
    return "".join(out), defs


def illus_drone():
    rnd = random.Random(8)
    out, dur = [], 7
    for layer, (lo, hi, fill, stroke) in enumerate(((50, 110, "#0c121a", "#151d28"), (26, 80, "#0f1620", "#1f2a38"))):
        x = -10 + layer * 14
        while x < 546:
            w = rnd.randint(26, 54)
            h = rnd.randint(lo, hi)
            out.append(f'<rect x="{x}" y="{146 - h}" width="{w - 4}" height="{h + 4}" fill="{fill}" stroke="{stroke}"/>')
            if layer:
                for wx in range(x + 6, x + w - 10, 9):
                    for wy in range(146 - h + 8, 140, 11):
                        r = rnd.random()
                        if r < .3:
                            blink = (f'<animate attributeName="opacity" values=".8;.1;.8" dur="{rnd.uniform(2, 5):.1f}s" '
                                     f'repeatCount="indefinite"/>' if r < .06 else "")
                            out.append(f'<rect x="{wx}" y="{wy}" width="3" height="4" fill="{AMBER}" opacity=".7">{blink}</rect>')
            x += w
    pts = [(20 + i * 4, 54 - 30 * (1 - math.exp(-i / 9)) + rnd.uniform(-3, 3)) for i in range(30)]
    length = poly_len(pts)
    out.append(f'<rect x="12" y="10" width="138" height="54" rx="6" fill="{BG}" fill-opacity=".9" stroke="#1f2833"/>'
               f'<text x="20" y="25" font-size="10" fill="{DIM}">reward</text>'
               f'<polyline points="{" ".join(f"{x:.0f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{CYAN}" '
               f'stroke-width="1.6" stroke-dasharray="{length:.0f}" stroke-dashoffset="{length:.0f}">'
               f'<animate attributeName="stroke-dashoffset" values="{length:.0f};0;0" keyTimes="0;.9;1" '
               f'dur="{dur}s" repeatCount="indefinite"/></polyline>')
    rotor = (f'<animate attributeName="rx" values="12;3;12" dur=".14s" repeatCount="indefinite"/>')
    out.append(f'<g><animateMotion path="M-40,70 C60,24 150,92 250,52 S420,18 480,58 S560,70 600,46" '
               f'dur="{dur}s" repeatCount="indefinite"/>'
               f'<line x1="-12" y1="-4" x2="-26" y2="-9" stroke="{CYAN}" stroke-width="2"/>'
               f'<line x1="12" y1="-4" x2="26" y2="-9" stroke="{CYAN}" stroke-width="2"/>'
               f'<ellipse cx="-26" cy="-11" rx="12" ry="2.4" fill="{CYAN}" opacity=".6">{rotor}</ellipse>'
               f'<ellipse cx="26" cy="-11" rx="12" ry="2.4" fill="{CYAN}" opacity=".6">{rotor}</ellipse>'
               f'<rect x="-14" y="-6" width="28" height="11" rx="4" fill="{FILL}" stroke="{CYAN}" stroke-width="2"/>'
               f'<circle class="blink" cx="0" cy="8" r="2" fill="{RED}"/></g>')
    return "".join(out), ""


def illus_lidar():
    rnd = random.Random(21)
    route = [(64, 96), (128, 42), (236, 66), (350, 30), (466, 60), (474, 110), (362, 122), (252, 98), (142, 126)]
    d, samples = closed_spline(route)
    length = poly_len(samples)
    trees = []
    for _ in range(4000):
        if len(trees) >= 16:
            break
        r = rnd.uniform(9, 17)
        c = (rnd.uniform(14, 522), rnd.uniform(12, 136))
        if min(math.dist(c, s) for s in samples) < r + 10:
            continue
        if any(math.dist(c, t) < r + tr + 5 for t, tr in trees):
            continue
        trees.append((c, r))
    out = []
    for _ in range(110):
        out.append(f'<circle cx="{rnd.uniform(0, 536):.0f}" cy="{rnd.uniform(0, 146):.0f}" r=".8" fill="#2c3b30"/>')
    greens = ["#a3ff12", "#7be04a", "#4fc36a", "#2fa36b", "#3fd6a0"]
    for (cx, cy), r in trees:
        for _ in range(int(r * 2.6)):
            a = rnd.uniform(0, 2 * math.pi)
            rr = r * (0.45 + 0.55 * math.sqrt(rnd.random()))
            out.append(f'<circle cx="{cx + rr * math.cos(a):.1f}" cy="{cy + rr * math.sin(a):.1f}" '
                       f'r="{rnd.uniform(.8, 1.6):.1f}" fill="{rnd.choice(greens)}" opacity=".85"/>')
    dur = 7
    out.append(f'<path d="{d} Z" fill="none" stroke="#24313b" stroke-width="2" stroke-dasharray="3 5"/>')
    out.append(f'<path d="{d} Z" fill="none" stroke="{GREEN}" stroke-width="2.5" '
               f'stroke-dasharray="{length:.0f} {length:.0f}" stroke-dashoffset="{length:.0f}">'
               f'<animate attributeName="stroke-dashoffset" values="{length:.0f};0;0" keyTimes="0;.8;1" '
               f'dur="{dur}s" repeatCount="indefinite"/></path>')
    sx, sy = route[0]
    out.append(f'<circle cx="{sx}" cy="{sy}" r="10" fill="none" stroke="{GREEN}" stroke-width="2" opacity="0">'
               f'{window(.8, 1, dur)}<animate attributeName="r" values="8;24" dur=".7s" repeatCount="indefinite"/></circle>')
    out.append(f'<g opacity="0">{window(.8, 1, dur)}<rect x="12" y="10" width="124" height="24" rx="6" '
               f'fill="{BG}" stroke="{GREEN}"/><text x="22" y="26" class="b" font-size="12" fill="{GREEN}">'
               f'LOOP CLOSED ✓</text></g>')
    out.append(f'<g>{travel(d + " Z", 0, .8, dur)}'
               f'<g>{rot([0, 360], 0, 0, .9)}<path d="M0,0 L38,-6 L38,6 Z" fill="{GREEN}" opacity=".25"/></g>'
               f'<circle r="5" fill="{BG}" stroke="{GREEN}" stroke-width="2.5"/></g>')
    return "".join(out), ""


def illus_bluerov():
    out = []
    defs = ('<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#0b2a4a"/><stop offset="1" stop-color="#040b14"/></linearGradient>')
    out.append('<rect width="536" height="146" fill="url(#sea)"/>')
    for i, x in enumerate((90, 250, 400)):
        out.append(f'<polygon points="{x},0 {x + 30},0 {x + 90},146 {x + 40},146" fill="#fff" opacity=".04">'
                   f'<animate attributeName="opacity" values=".02;.07;.02" dur="{4 + i}s" repeatCount="indefinite"/></polygon>')
    for i, x in enumerate((30, 48, 500, 514)):
        out.append(f'<g>{rot([-8, 8, -8], x, 140, 3 + i * .4)}<path d="M{x},140 q-6,-14 0,-26 q6,-12 0,-24" '
                   f'fill="none" stroke="#1f6f5a" stroke-width="3" stroke-linecap="round"/></g>')
    out.append('<path d="M0,134 Q40,124 80,132 T160,130 T240,134 T320,128 T400,133 T480,129 T560,132 V146 H0 Z" '
               'fill="#0a1622" stroke="#1b3046"/>')
    out.append(f'<g>{shift([(560, 30), (-40, 30)], 16)}'
               f'<path d="M0,0 Q8,-6 16,0 Q8,6 0,0 Z M15,0 L22,-5 L22,5 Z" fill="{AMBER}" opacity=".75"/></g>')
    for i in range(6):
        x0 = 204 + (i % 2) * 6
        out.append(f'<circle cx="{x0}" cy="60" r="{2 + (i % 3) * .7:.1f}" fill="none" stroke="#9cc3ff" opacity="0">'
                   f'<animate attributeName="cy" values="60;-6" dur="3s" begin="{i * .5}s" repeatCount="indefinite"/>'
                   f'<animate attributeName="cx" values="{x0};{x0 + 4};{x0 - 3};{x0 + 2}" dur="3s" begin="{i * .5}s" repeatCount="indefinite"/>'
                   f'<animate attributeName="opacity" values=".8;0" dur="3s" begin="{i * .5}s" repeatCount="indefinite"/></circle>')
    beams = "".join(f'<line x1="{a}" y1="22" x2="{b}" y2="{c}" stroke="{CYAN}" stroke-opacity=".55" '
                    f'stroke-width="1.5" stroke-dasharray="3 4">{march(14, .5)}</line>'
                    for a, b, c in ((-4, -54, 72), (-1, -20, 76), (1, 20, 76), (4, 54, 72)))
    prop = '<animate attributeName="ry" values="9;2;9" dur=".2s" repeatCount="indefinite"/>'
    rov = (f'{beams}'
           f'<ellipse rx="100" ry="44" fill="{AMBER}" fill-opacity=".04" stroke="{AMBER}" stroke-dasharray="5 5" stroke-opacity=".8">'
           f'<animate attributeName="rx" values="100;56;56" keyTimes="0;.8;1" dur="5s" repeatCount="indefinite"/>'
           f'<animate attributeName="ry" values="44;26;26" keyTimes="0;.8;1" dur="5s" repeatCount="indefinite"/></ellipse>'
           f'<rect x="-44" y="-28" width="36" height="11" rx="3" fill="#16243a" stroke="{BLUE}" stroke-width="1.5"/>'
           f'<rect x="8" y="-28" width="36" height="11" rx="3" fill="#16243a" stroke="{BLUE}" stroke-width="1.5"/>'
           f'<rect x="-62" y="-10" width="12" height="18" rx="3" fill="{FILL}" stroke="{BLUE}" stroke-width="1.5"/>'
           f'<ellipse cx="-64" cy="-1" rx="2" ry="9" fill="{BLUE}" opacity=".7">{prop}</ellipse>'
           f'<rect x="-50" y="-18" width="100" height="34" rx="6" fill="{FILL}" stroke="{BLUE}" stroke-width="2"/>'
           f'<circle cx="38" cy="-2" r="8" fill="{CYAN}" fill-opacity=".25" stroke="{CYAN}" stroke-width="1.5"/>'
           f'<circle cx="40" cy="-2" r="2.5" fill="{CYAN}"/>'
           f'<circle cx="26" cy="9" r="2.5" fill="{AMBER}"/><circle cx="46" cy="9" r="2.5" fill="{AMBER}"/>'
           f'<rect x="-8" y="16" width="16" height="6" rx="1" fill="{CYAN}"/>')
    out.append(f'<g>{shift([(268, 58), (268, 52), (268, 58)], 3.2)}{rov}</g>')
    out.append(f'<text x="420" y="22" font-size="11" fill="{AMBER}">uncertainty ↓</text>')
    return "".join(out), defs


# --- hero + log -------------------------------------------------------------------

def hero():
    w, h = 1120, 404
    rnd = random.Random(5)
    out = [f'<rect width="{w}" height="{h}" fill="{BG}"/>', f'<rect width="{w}" height="{h}" fill="url(#grid)"/>']

    # hazard tape
    stripes = "".join(f'<polygon points="{x},0 {x + 14},0 {x - 16},30 {x - 30},30" fill="{AMBER}"/>'
                      for x in range(-56, w + 60, 28))
    out.append(f'<rect width="{w}" height="30" fill="#111"/>'
               f'<g>{shift([(0, 0), (28, 0)], 1.2)}{stripes}</g>'
               f'<rect x="330" y="4" width="460" height="22" rx="4" fill="{BG}"/>'
               f'<text x="560" y="20" text-anchor="middle" class="b" font-size="13" letter-spacing="2" '
               f'fill="{AMBER}">ACTIVE ROBOTICS LAB · ROBOTS MAY BE LOOSE</text>')

    # name with an RGB split that glitches every few seconds
    name = "".join(f'<text x="44" y="{y}" class="b" font-size="78" letter-spacing="2">{t}</text>'
                   for t, y in (("MOURAD", 160), ("OUAZGHIRE", 238)))
    out.append(f'<text x="48" y="86" font-size="16" fill="{DIM}">// hello world, this is</text>'
               f'<g class="gc" fill="{CYAN}" opacity=".9">{name}</g>'
               f'<g class="gm" fill="{MAGENTA}" opacity=".9">{name}</g>'
               f'<g fill="{INK}">{name}</g>')
    out.append(f'<text x="48" y="282" font-size="19" fill="#c9d1d9">'
               f'I build robots and AI agents that do things nobody asked for.</text>')

    # typing prompt
    phrases = ["moving a humanoid with brain waves",
               "letting AI agents pay each other in bitcoin",
               "teaching a robot dog to follow my finger",
               "giving a robot dog a tail. for THE SHOW."]
    T, cw, x0 = 16, 11.4, 86
    out.append(f'<rect x="44" y="300" width="680" height="42" rx="10" fill="{PANEL}" stroke="#1f2833"/>'
               f'<text x="62" y="328" class="b" font-size="19" fill="{GREEN}">▸</text>')
    for i, p in enumerate(phrases):
        s, slot = i / len(phrases), 1 / len(phrases)
        n = len(p)
        vals = ["0 0"] + [f"{k * cw:.1f} 0" for k in range(n + 1)]
        times = ["0"] + [f"{s + slot * .55 * k / n:.4f}" for k in range(n + 1)]
        out.append(f'<g opacity="0">{window(s, s + slot, T)}'
                   f'<text x="{x0}" y="328" font-size="19" fill="{CYAN}">{esc(p)}</text>'
                   f'<g clip-path="url(#pill)"><g><animateTransform attributeName="transform" type="translate" '
                   f'values="{";".join(vals)}" keyTimes="{";".join(times)}" calcMode="discrete" dur="{T}s" '
                   f'repeatCount="indefinite"/>'
                   f'<rect class="blink" x="{x0}" y="310" width="11" height="24" fill="{GREEN}"/>'
                   f'<rect x="{x0 + 11}" y="302" width="660" height="38" fill="{PANEL}"/></g></g></g>')

    out.append(f'<text x="48" y="382" font-size="14" fill="#c9d1d9"><tspan class="b" fill="{AMBER}">'
               f'ROBOTS BOSSED AROUND ▸</tspan> Unitree G1 / Go2 / Go1 / R1 · Franka Panda · BlueROV2 · '
               f'MIA Hand · 1 drone</text>')

    # LiDAR scope: points light up as the beam sweeps past
    cx, cy, R, sweep = 912, 212, 136, 4
    for r in (34, 68, 102, 136):
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#123039"/>')
    out.append(f'<path d="M{cx - R},{cy} H{cx + R} M{cx},{cy - R} V{cy + R}" stroke="#123039"/>')
    pts = []
    for (x1, y1), (x2, y2) in (((-110, -88), (40, -88)), ((70, -88), (118, -88)), ((118, -88), (118, 30)),
                               ((118, 70), (118, 96)), ((-110, 96), (118, 96)), ((-110, -88), (-110, -20)),
                               ((-110, 20), (-110, 96)), ((-40, -88), (-40, -30)), ((30, 20), (80, 20))):
        steps = int(math.dist((x1, y1), (x2, y2)) / 6)
        for k in range(steps + 1):
            t = k / max(steps, 1)
            pts.append((x1 + (x2 - x1) * t + rnd.uniform(-1.5, 1.5), y1 + (y2 - y1) * t + rnd.uniform(-1.5, 1.5)))
    for ox, oy, rr in ((-60, 40, 12), (55, -40, 9), (-20, 60, 7), (80, 60, 10)):
        for _ in range(16):
            a = rnd.uniform(0, 2 * math.pi)
            pts.append((ox + rr * math.cos(a), oy + rr * math.sin(a)))
    for px, py in pts:
        if math.hypot(px, py) > R - 4:
            continue
        ang = math.degrees(math.atan2(py, px)) % 360
        begin = ang / 360 * sweep
        out.append(f'<circle cx="{cx + px:.1f}" cy="{cy + py:.1f}" r="1.9" fill="{CYAN}" opacity=".12">'
                   f'<animate attributeName="opacity" values="1;.12;.12" keyTimes="0;.7;1" dur="{sweep}s" '
                   f'begin="{begin:.2f}s" repeatCount="indefinite"/></circle>')
    wedge = []
    for k in range(12):
        a1, a2 = math.radians(-4 * (k + 1)), math.radians(-4 * k)
        wedge.append(f'<path d="M{cx},{cy} L{cx + R * math.cos(a1):.1f},{cy + R * math.sin(a1):.1f} '
                     f'A{R} {R} 0 0 1 {cx + R * math.cos(a2):.1f},{cy + R * math.sin(a2):.1f} Z" '
                     f'fill="{CYAN}" opacity="{.28 * (1 - k / 12):.3f}"/>')
    out.append(f'<g>{rot([0, 360], cx, cy, sweep)}{"".join(wedge)}'
               f'<line x1="{cx}" y1="{cy}" x2="{cx + R}" y2="{cy}" stroke="{CYAN}" stroke-width="2"/></g>')
    out.append(f'<path d="M{cx - 7},{cy + 7} L{cx},{cy - 9} L{cx + 7},{cy + 7} Z" fill="{GREEN}"/>')
    out.append(f'<circle class="blink" cx="{cx + R - 124}" cy="66" r="4" fill="{RED}"/>'
               f'<text x="{cx + R}" y="70" text-anchor="end" class="b" font-size="12" letter-spacing="2" '
               f'fill="{CYAN}">LIDAR · LIVE</text>')
    out.append(f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="18" fill="none" stroke="{EDGE}" stroke-width="2"/>')

    css = (".gc{animation:gc 5s steps(1) infinite;transform:translate(-2px,0)}"
           ".gm{animation:gm 5s steps(1) infinite;transform:translate(2px,0)}"
           "@keyframes gc{0%,84%,100%{transform:translate(-2px,0)}86%{transform:translate(-7px,2px)}"
           "89%{transform:translate(4px,-2px)}92%{transform:translate(-3px,0)}}"
           "@keyframes gm{0%,84%,100%{transform:translate(2px,0)}86%{transform:translate(6px,-2px)}"
           "89%{transform:translate(-5px,1px)}92%{transform:translate(3px,0)}}")
    defs = (GRID_DEF + f'<clipPath id="round"><rect width="{w}" height="{h}" rx="18"/></clipPath>'
            f'<clipPath id="pill"><rect x="45" y="301" width="678" height="40" rx="9"/></clipPath>')
    body = f'<g clip-path="url(#round)">{"".join(out)}</g>'
    write("hero", svg(w, h, "Mourad Ouazghire: I build robots and AI agents that do things nobody asked for.",
                      body, css, defs))


def lab_log(commits):
    w = 1120
    top, step = 122, 32
    h = top + step * len(commits) + 52
    out = [frame(w, h),
           f'<path d="M1,17 Q1,1 17,1 H{w - 17} Q{w - 1},1 {w - 1},17 V44 H1 Z" fill="#0e131b"/>',
           f'<line x1="1" y1="44" x2="{w - 1}" y2="44" stroke="{EDGE}"/>']
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        out.append(f'<circle cx="{26 + i * 20}" cy="23" r="6" fill="{c}"/>')
    out.append(f'<text x="{w / 2}" y="28" text-anchor="middle" font-size="13" fill="{DIM}">mourad@lab: ~/robots</text>')

    def prompt(y, cmd=""):
        return (f'<text x="32" y="{y}" font-size="18"><tspan fill="{GREEN}">mourad@lab</tspan>'
                f'<tspan fill="{DIM}">:</tspan><tspan fill="{BLUE}">~/robots</tspan>'
                f'<tspan fill="{INK}"> $ {esc(cmd)}</tspan></text>')

    out.append(prompt(84, "git log --all --oneline --author=mourad | sort --by=chaos"))
    for i, (sha, msg) in enumerate(commits):
        head, sep, rest = msg.partition(":")
        if sep and head.startswith(("fix", "feat")):
            color = RED if head.startswith("fix") else GREEN
            text = f'<tspan fill="{color}">{esc(head)}:</tspan><tspan fill="{INK}">{esc(rest)}</tspan>'
        else:
            text = f'<tspan fill="{INK}">{esc(msg)}</tspan>'
        out.append(f'<text class="ln" style="animation-delay:{.4 + i * .45:.2f}s" x="32" y="{top + i * step}" '
                   f'font-size="18"><tspan fill="{AMBER}">{sha}</tspan> {text}</text>')
    y = top + step * len(commits) + 14
    delay = .4 + len(commits) * .45
    prompt_w = len("mourad@lab:~/robots $ ") * 10.8
    out.append(f'<g class="ln" style="animation-delay:{delay:.2f}s">{prompt(y)}'
               f'<rect class="blink" x="{32 + prompt_w:.0f}" y="{y - 16}" width="11" height="21" fill="{GREEN}"/></g>')
    css = ".ln{opacity:0;animation:in .35s ease-out forwards}@keyframes in{to{opacity:1}}"
    write("lab-log", svg(w, h, "Real commit messages: " + " / ".join(m for _, m in commits), "".join(out), css))


def main():
    hero()

    illus, defs = illus_telekinex()
    feature_card(
        "exp-telekinex", MAGENTA, "EXP-01 · HACKATHON · 18 H", "MIND-CONTROLLED",
        "Moved a humanoid robot with my brain.",
        "Non-invasive EEG → a 12.6K-param EEGNet → a Unitree G1 humanoid in MuJoCo, doing "
        "pick-and-place on a factory floor. Voice and WASD as backup, because brains get tired.",
        "PyTorch · ONNX · MuJoCo · FastAPI · WebSockets", illus, defs)

    illus, defs = illus_agora()
    feature_card(
        "exp-agora", AMBER, "EXP-02 · HACK-NATION · WITH GEOSHUA", "240 SAT / CALL",
        "AI agents that hire & pay each other in bitcoin.",
        "Agent hits a paywall → gets a Lightning invoice → pays → gets the goods. No accounts, "
        "no API keys, no humans. Ships an MCP server so Claude can go shopping with a budget "
        "and a kill-switch.",
        "L402 · Lightning (NWC) · Ed25519 · Next.js · MCP", illus, defs)

    cards = [
        ("exp-telephone", CYAN, "EXP-03 · DIMOS", "ON AIR", "Robot Telephone",
         "Two robots patrol and gossip over a live radio feed while I read their chat bubbles.",
         "DimOS · MuJoCo · Claude Haiku", illus_telephone),
        ("exp-point", GREEN, "EXP-04 · UNITREE GO2", "GOOD BOY", "Go Where I Point",
         "Point at a spot, the robot dog walks there. Also taught it football, a key-finder "
         "patrol and VR teleop moves.",
         "Unitree Go2 · DimOS · Quest teleop", illus_point),
        ("exp-escape", AMBER, "EXP-05 · UNITREE G1", "ESCAPING…", "Humanoid Escape Room",
         "Locked a G1 humanoid in a maze with nothing but a depth camera, plus a web dashboard "
         "to watch it try.",
         "Unitree G1 · MuJoCo · depth-based navigation", illus_escape),
        ("exp-animator", MAGENTA, "EXP-06 · ANIMATOR", "THE SHOW", "Robot Dog, Disney Edition",
         "Gave a robot dog eyes, ears, a tail and a foot-synced walk. The commit message just "
         "says 'THE SHOW'.",
         "MuJoCo · procedural animation · gait sync", illus_animator),
        ("exp-r1", ORANGE, "EXP-07 · UNITREE R1", "TALKS BACK", "A Humanoid That Talks Back",
         "Wired an LLM agent into a Unitree R1: it answers through its own onboard speaker and "
         "gestures with its arms.",
         "Unitree R1 · claude-haiku-4-5 · speech", illus_r1),
        ("exp-drone", CYAN, "EXP-08 · REINFORCEMENT LEARNING", "REWARD ↑", "Drone vs. Fake City",
         "Built a MuJoCo city plus a Gymnasium RL pipeline to teach a drone to fly through it.",
         "MuJoCo · Gymnasium · RL", illus_drone),
        ("exp-lidar", GREEN, "EXP-09 · PUBLISHED", "LOOP CLOSED", "LiDAR in a Botanic Garden",
         "Benchmarked LiDAR odometry and loop closure across an Australian botanic garden → "
         "main-author paper at ACRA 2024.",
         "ROS · LIO-SAM · FAST-LIO · COIN-LIO", illus_lidar),
        ("exp-bluerov", BLUE, "EXP-10 · UNDERWATER", "SUBMERGED", "Kalman Filter, but Underwater",
         "Kept a BlueROV2 from getting lost underwater: Doppler velocity log + Kalman filter → "
         "ROS odometry.",
         "ROS Noetic · DVL · FilterPy", illus_bluerov),
    ]
    for slug, accent, tag, status, title, desc, foot, draw in cards:
        illus, defs = draw()
        grid_card(slug, accent, tag, status, title, desc, foot, illus, defs)

    lab_log([
        ("57aef74", "fix: override mujoco_steps_per_frame=7 — Go1 policy needs it to stay upright"),
        ("6bf0bb6", "fix: use claude-3-haiku model (API key only has haiku access)"),
        ("aa725b0", "fix: double robot movement speed for visible patrol demo"),
        ("4cb720e", "feat: ping pong fleet setup"),
        ("3cbfd07", "feat: G1 humanoid escape room with web dashboard and depth-based navigation"),
        ("105bacc", 'feat(go2): hand-gesture control ("go where I point") skill + blueprint'),
        ("c51353d", "feat(hermes): add Hermes integration with RAM safeguards"),
        ("20327df", "feat(animator): Disney-grade upgrade — eyes, ears, tail, foot-sync gait, THE SHOW"),
        ("912881e", "innit"),
    ])


if __name__ == "__main__":
    main()
