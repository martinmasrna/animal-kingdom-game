"""The painted pieces of the stars prototype's open card face (Martin, 2026-11-15: "we can try D", Gwent's hand face):
in the hand and collection the painting fills the card, the strength banner hangs from its top-left corner and the level
sits in a painted star on its bottom-right; read in full, the name sits on a plank where the painting ends, the rules
on the panel below it. Every piece is cut from the frame painting the game's cards already use (design/card3,
card_frame[_compact]_thin.png) and tinted per rarity exactly as design/card3/bake.mjs tints today's frames; where a piece
meets the card's edge it runs straight off it, as there. Writes kit2/card_face_<piece>_<rarity>.webp at the frames' scale
(720 px = 20em).

    .venv/bin/python tools/stars/bake_card_face.py [--check]
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT.parents[1] / "design" / "card3"          # the workspace's design repo, beside the worktrees
if not SRC.exists():
    SRC = ROOT.parent / "design" / "card3"
KIT = ROOT / "animal_kingdom" / "web" / "static" / "kit2"
W = 720                                              # output width of a whole card (20em)
E = round(W * 14 / 720)                              # the edge strip that runs off the card (bake.mjs)

# bake.mjs's tints: (frame, panel) as CSS filter lists
TINTS = {"common": ([], []),
         "rare": ([("saturate", 0), ("brightness", 1.1), ("sepia", .35), ("hue-rotate", 180), ("saturate", 1.6)],
                  [("saturate", 0), ("brightness", 1.27), ("sepia", .25), ("hue-rotate", 180), ("saturate", 1.1)]),
         "legendary": ([("sepia", .6), ("saturate", 2.2), ("brightness", 1.08)], [("sepia", .6), ("saturate", 1.5), ("brightness", 1.16)])}


def matrix(op, v):
    """The Filter Effects spec's colour matrix for one CSS filter function."""
    if op == "brightness":
        return np.eye(3) * v
    if op == "saturate":
        s = v
        return np.array([[.213 + .787 * s, .715 - .715 * s, .072 - .072 * s],
                         [.213 - .213 * s, .715 + .285 * s, .072 - .072 * s],
                         [.213 - .213 * s, .715 - .715 * s, .072 + .928 * s]])
    if op == "sepia":
        a = 1 - v
        return np.array([[.393 + .607 * a, .769 - .769 * a, .189 - .189 * a],
                         [.349 - .349 * a, .686 + .314 * a, .168 - .168 * a],
                         [.272 - .272 * a, .534 - .534 * a, .131 + .869 * a]])
    if op == "hue-rotate":
        t = np.radians(v); c, s = np.cos(t), np.sin(t)
        return (np.array([[.213, .715, .072]] * 3) + c * np.array([[.787, -.715, -.072], [-.213, .285, -.072], [-.213, -.715, .928]])
                + s * np.array([[-.213, -.715, .928], [.143, .140, -.283], [-.787, .715, .072]]))
    raise ValueError(op)


def tint(rgba, ops):
    out = rgba.astype(float)
    for op, v in ops:   # each function clamps, as the browser applies them one after another
        out[..., :3] = (out[..., :3] @ matrix(op, v).T).clip(0, 255)
    return out.round().astype(np.uint8)


def load(name):
    im = Image.open(SRC / name).convert("RGBA")
    h = round(W * im.height / im.width)
    return np.asarray(im.resize((W, h), Image.LANCZOS)), h


def run_off(a, sides):
    """Each outer strip of width E on `sides` takes the wood just inside it, so the plank runs straight off the card."""
    a = a.copy()
    if "l" in sides: a[:, :E] = a[:, E:2 * E]
    if "r" in sides: a[:, -E:] = a[:, -2 * E:-E]
    if "t" in sides: a[:E] = a[E:2 * E]
    if "b" in sides: a[-E:] = a[-2 * E:-E]
    return a


def px(v_958):   # a measurement in the 958 px source, at the output scale
    return round(v_958 * W / 958)


def pieces(rarity):
    frame, panel = TINTS[rarity]
    comp, _ = load("card_frame_compact_thin.png")
    full, _ = load("card_frame_thin.png")
    # The strength banner, its own painted piece: up to its right bevel (source x 210), down past its foot (source 266).
    banner = tint(comp[:px(268), :px(210)], frame).copy()
    # Two flaws of the source painting, mended: a seam across the banner's wood (source row 56), mirrored over so the grain
    # runs on; and an older frame's left rail showing under the banner's foot (source x < 30, below y 262), cleared.
    s = px(56)
    for k in range(1, s - E + 1):
        banner[s - k] = banner[s + k]
    banner[px(262):, :px(30), 3] = 0
    # Its left strip runs off the card too, the copy following the foot's slant (measured: from x 30, y 258 up to the notch
    # at x 102, y 218) so the foot stays one clean edge, as bake.mjs does.
    dy = round(E * (258 - 218) / (102 - 30))
    banner = banner.copy(); banner[:E] = banner[E:2 * E]
    banner[:, :E] = 0
    banner[dy:, :E] = banner[:-dy, E:2 * E]
    banner[:dy, :E] = banner[:dy, E:2 * E]
    # The name plank: the band right of the banner's cast shadow (source x 226 on), drawn out along its grain to the
    # card's width; its top and bottom bevels are the band's own.
    band = comp[:px(151), px(226):]
    plank = np.asarray(Image.fromarray(band).resize((W, band.shape[0]), Image.LANCZOS))
    plank = run_off(tint(plank, frame), "lr")
    # The rules panel, as on today's full card.
    pan = run_off(tint(full[px(1007):], panel), "lrb")
    # The rim (Martin, 2026-11-15: "less is more, look how Gwent does it"): today's frame with its thin side and bottom
    # rails kept, and in place of the thick top band a top rail cut from the band's own lower edge (source rows 124-151,
    # its downward bevel), the rails running on beneath it. Its outer edges run off the card over a narrower strip (the
    # rails are 24 source px wide, so the usual strip would eat them).
    rim = tint(comp, frame).copy()
    tr = px(151) - px(124)
    rim[:tr] = rim[px(124):px(151)]
    gap = px(400) - tr
    rim[tr:px(400)] = rim[px(400):px(400) + gap]
    e = round(W * 6 / 720)
    rim[:, :e] = rim[:, e:2 * e]; rim[:, -e:] = rim[:, -2 * e:-e]; rim[:e] = rim[e:2 * e]; rim[-e:] = rim[-2 * e:-e]
    return {"banner": banner, "plank": plank, "panel": pan, "rim": rim}


STAR = Path(__file__).parent / "star_master.png"     # the level's star, painted on magenta (Codex, 2026-11-15)
DISC = Path(__file__).parent / "disc_master.png"     # the strength's disc, its sibling (Codex, 2026-11-15)


def badge(src, rarity, em):
    """A badge: the painted driftwood piece keyed off its magenta, cropped, `em` wide, toned and tinted as the frame."""
    im = np.asarray(Image.open(src).convert("RGB")).astype(int)
    spill = (np.minimum(im[..., 0], im[..., 2]) - im[..., 1]).clip(0, 255)
    a = np.dstack([im.clip(0, 255), np.clip(255 - spill * 1.6, 0, 255)]).astype(np.uint8)
    m = a[..., 3] < 250                                   # despill the soft edge, as design/card3/key.py
    a[..., 0][m] = np.minimum(a[..., 0][m], a[..., 1][m] + 30); a[..., 2][m] = np.minimum(a[..., 2][m], a[..., 1][m])
    ys, xs = np.nonzero(a[..., 3] > 16)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    w = round(em * 36)
    a = np.asarray(Image.fromarray(a).resize((w, round(a.shape[0] * w / a.shape[1])), Image.LANCZOS))
    # The painting came out paler and warmer than the banner's wood: each channel scaled so its mean matches the banner's.
    comp, _ = load("card_frame_compact_thin.png")
    wood = comp[px(30):px(200), px(30):px(190), :3].reshape(-1, 3).mean(0)
    face = a[..., 3] > 250
    a = a.copy(); a[..., :3] = (a[..., :3] * (wood / a[face][:, :3].mean(0))).clip(0, 255).round().astype(np.uint8)
    return tint(a, TINTS[rarity][0])


def check():
    """Today's compact band, tinted here, against the baked frame the game ships: the tint must match."""
    comp, _ = load("card_frame_compact_thin.png")
    for r in TINTS:
        mine = tint(comp[40:100, 300:600], TINTS[r][0]).astype(int)
        shipped = np.asarray(Image.open(KIT / f"card_frame_{r}_compact.webp").convert("RGBA"))[40:100, 300:600].astype(int)
        print(f"{r}: mean |diff| {np.abs(mine[..., :3] - shipped[..., :3]).mean():.2f} of 255")


FULL_H = 1056                                        # 720 x 1056: the card's 20 x 29.34em
PLANK_Y, PANEL_Y = 644, 757                          # the plank and the panel, from the top (17.89em and 21.03em)
PAD = 12                                             # room round the tag for its shadow


def shadow_under(a, dx=2, dy=5, blur=5, alpha=.5):
    """The piece's own soft shadow, cast down and right as the light falls on the painted wood, under the piece."""
    from PIL import ImageFilter
    al = Image.fromarray(a[..., 3]).filter(ImageFilter.GaussianBlur(blur))
    sh = np.zeros_like(a); sh[..., 3] = 0
    m = np.asarray(al).astype(float) * alpha
    sh[dy:, dx:, 3] = m[:a.shape[0] - dy, :a.shape[1] - dx].round().astype(np.uint8)
    out = Image.fromarray(sh); out.alpha_composite(Image.fromarray(a))
    return np.asarray(out)


def canvas(*layers):
    c = Image.new("RGBA", (W, FULL_H))
    for a, (x, y) in layers:
        c.alpha_composite(Image.fromarray(a), (x, y))
    return np.asarray(c)


if __name__ == "__main__":
    if "--check" in sys.argv:
        check(); sys.exit()
    for r in TINTS:
        p = pieces(r)
        # No border (Martin, 2026-11-15): the full card's frame is only the plank and the panel; the compact card has none.
        full = canvas((p["panel"], (0, PANEL_Y)), (p["plank"], (0, PLANK_Y)))
        out = {f"card_face_star_{r}": shadow_under(np.pad(badge(STAR, r, 4), ((PAD, PAD), (PAD, PAD), (0, 0)))),
               f"card_face_disc_{r}": shadow_under(np.pad(badge(DISC, r, 5.33), ((PAD, PAD), (PAD, PAD), (0, 0)))),
               f"card_frame_{r}_open": shadow_under(full),
               f"card_face_plank_{r}": shadow_under(np.pad(p["plank"], ((0, PAD), (0, 0), (0, 0))))}
        for name, a in out.items():
            Image.fromarray(a).save(KIT / f"{name}.webp", quality=90, method=6)
            print(f"{name}.webp {a.shape[1]}x{a.shape[0]} = {a.shape[1] / 36:.2f}em x {a.shape[0] / 36:.2f}em")
