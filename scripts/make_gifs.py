"""Render the README animations from recorded, real model output.

Usage:
  uv run --no-project --with pillow --with arabic-reshaper --with python-bidi \
      python scripts/make_gifs.py [path/to/eval-results.json]

Inputs: docs/demo/conversations.json (from scripts/capture_demo.py) and an eval results file
(defaults to the newest Gemini run in evals/results/, copied to docs/demo/eval_results.json).
Outputs: docs/demo/*.gif. The helpers are loaded with `uv run --with`, not project dependencies.
"""

import json
import re
import shutil
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "docs" / "demo"

WIDTH, HEIGHT = 900, 560
HEADER_H = 56
PAD = 22
BUBBLE_MAX_W = 600

COLORS = {
    "bg": (15, 23, 42),
    "header": (30, 41, 59),
    "title": (241, 245, 249),
    "muted": (148, 163, 184),
    "user": (37, 99, 235),
    "agent": (51, 65, 85),
    "text": (241, 245, 249),
    "tool": (20, 83, 45),
    "tool_text": (187, 247, 208),
    "warn": (120, 53, 15),
    "warn_text": (254, 215, 170),
    "ok": (22, 101, 52),
    "pass": (74, 222, 128),
    "fail": (248, 113, 113),
    "accent": (250, 204, 21),
}

_FONT_DIRS = [
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/Library/Fonts"),
]
_UI_FONTS = ["segoeui.ttf", "tahoma.ttf", "DejaVuSans.ttf", "Arial.ttf"]
_UI_BOLD_FONTS = ["segoeuib.ttf", "tahomabd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"]
_MONO_FONTS = ["consola.ttf", "DejaVuSansMono.ttf", "Menlo.ttc"]

# Arabic block plus the presentation forms that shaping turns letters into.
_ARABIC = re.compile(
    f"[{chr(0x0600)}-{chr(0x06FF)}{chr(0xFB50)}-{chr(0xFDFF)}{chr(0xFE70)}-{chr(0xFEFF)}]"
)
_LATIN = re.compile(r"[A-Za-z]")


def _font(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    for directory in _FONT_DIRS:
        for name in names:
            path = directory / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    raise SystemExit(f"None of these fonts were found: {', '.join(names)}")


FONT = _font(_UI_FONTS, 19)
FONT_SMALL = _font(_UI_FONTS, 14)
FONT_BOLD = _font(_UI_BOLD_FONTS, 20)
MONO = _font(_MONO_FONTS, 16)
MONO_SMALL = _font(_MONO_FONTS, 15)
CHIP_UI = _font(_UI_FONTS, 15)


def is_rtl(text: str) -> bool:
    return len(_ARABIC.findall(text)) > len(_LATIN.findall(text))


def shape(text: str) -> str:
    """Join Arabic letters and order the line for display; Latin text passes through."""
    return get_display(arabic_reshaper.reshape(text)) if _ARABIC.search(text) else text


def text_width(text: str, font: ImageFont.FreeTypeFont) -> float:
    return font.getlength(shape(text))


def wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap in logical order, then shape each line, so right-to-left lines break correctly."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and text_width(candidate, font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return [shape(line) for line in lines]


@dataclass(frozen=True)
class Item:
    kind: str  # user | agent | tool | note | typing
    text: str
    meta: str = ""


def _item_height(item: Item) -> int:
    if item.kind in ("tool", "note"):
        return 34
    if item.kind == "typing":
        return 44
    lines = wrap(item.text, FONT, BUBBLE_MAX_W - 2 * 16)
    return len(lines) * 27 + 24 + (20 if item.meta else 0)


def _draw_item(draw: ImageDraw.ImageDraw, item: Item, y: int, frame_no: int) -> None:
    if item.kind == "typing":
        x = PAD
        draw.rounded_rectangle([x, y, x + 84, y + 38], radius=18, fill=COLORS["agent"])
        for i in range(3):
            lift = 4 if (frame_no + i) % 3 == 0 else 0
            cx = x + 24 + i * 18
            draw.ellipse(
                [cx - 5, y + 19 - 5 - lift, cx + 5, y + 19 + 5 - lift], fill=COLORS["muted"]
            )
        return

    if item.kind in ("tool", "note"):
        background = COLORS["tool"] if item.kind == "tool" else COLORS["ok"]
        if item.meta == "error":
            background = COLORS["warn"]
        color = COLORS["warn_text"] if item.meta == "error" else COLORS["tool_text"]
        # The monospace font has no Arabic letters, so Arabic argument values need the UI font.
        font = CHIP_UI if _ARABIC.search(item.text) else MONO_SMALL
        label = item.text
        width = int(font.getlength(label)) + 28
        draw.rounded_rectangle([PAD, y, PAD + width, y + 28], radius=8, fill=background)
        draw.text((PAD + 14, y + 5), label, font=font, fill=color)
        return

    lines = wrap(item.text, FONT, BUBBLE_MAX_W - 2 * 16)
    inner_w = max(int(FONT.getlength(line)) for line in lines) if lines else 40
    if item.meta:
        inner_w = max(inner_w, int(FONT_SMALL.getlength(item.meta)))
    bubble_w = inner_w + 2 * 16
    bubble_h = len(lines) * 27 + 20 + (20 if item.meta else 0)
    is_user = item.kind == "user"
    x = WIDTH - PAD - bubble_w if is_user else PAD
    fill = COLORS["user"] if is_user else COLORS["agent"]
    draw.rounded_rectangle([x, y, x + bubble_w, y + bubble_h], radius=16, fill=fill)
    rtl = is_rtl(item.text)
    for i, line in enumerate(lines):
        line_w = FONT.getlength(line)
        tx = x + bubble_w - 16 - line_w if rtl else x + 16
        draw.text((tx, y + 9 + i * 27), line, font=FONT, fill=COLORS["text"])
    if item.meta:
        draw.text((x + 16, y + bubble_h - 26), item.meta, font=FONT_SMALL, fill=(203, 213, 225))


def render_chat_frame(title: str, subtitle: str, items: list[Item], frame_no: int) -> Image.Image:
    heights = [_item_height(item) for item in items]
    content_h = sum(heights) + 14 * len(items) + PAD
    canvas = Image.new("RGB", (WIDTH, max(content_h, HEIGHT - HEADER_H)), COLORS["bg"])
    draw = ImageDraw.Draw(canvas)
    y = PAD
    for item, height in zip(items, heights, strict=True):
        _draw_item(draw, item, y, frame_no)
        y += height + 14

    frame = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg"])
    # Keep the newest message in view, like a chat window that scrolls.
    offset = max(0, content_h - (HEIGHT - HEADER_H))
    frame.paste(canvas.crop((0, offset, WIDTH, offset + HEIGHT - HEADER_H)), (0, HEADER_H))
    header = ImageDraw.Draw(frame)
    header.rectangle([0, 0, WIDTH, HEADER_H], fill=COLORS["header"])
    header.text((PAD, 9), title, font=FONT_BOLD, fill=COLORS["title"])
    header.text((PAD, 33), subtitle, font=FONT_SMALL, fill=COLORS["muted"])
    return frame


def _format_args(arguments: dict) -> str:
    # Hide unset filters and the default page size so the chip shows what the model chose.
    shown = {
        k: v for k, v in arguments.items() if v not in (None, "") and not (k == "limit" and v == 5)
    }
    text = ", ".join(f"{k}={shape(str(v))}" for k, v in shown.items())
    return text if len(text) <= 70 else text[:67] + "..."


def _reveal_steps(text: str, steps: int = 5) -> Iterator[str]:
    words = text.split()
    for i in range(1, steps + 1):
        yield " ".join(words[: max(1, round(len(words) * i / steps))])


def chat_frames(scenario: dict, model: str) -> Iterator[tuple[Image.Image, int]]:
    title = scenario["title"]
    subtitle = f"Recorded live through the API  ·  model: {model}"
    items: list[Item] = []
    frame_no = 0

    def frame(ms: int, extra: list[Item] | None = None) -> tuple[Image.Image, int]:
        nonlocal frame_no
        frame_no += 1
        return render_chat_frame(title, subtitle, items + (extra or []), frame_no), ms

    yield frame(600)
    for turn in scenario["turns"]:
        items.append(Item("user", turn["user"]))
        yield frame(900)
        for _ in range(3):
            yield frame(220, [Item("typing", "")])
        for call in turn["tool_calls"]:
            label = f"tool -> {call['name']}({_format_args(call['input'])})"
            items.append(Item("tool", label, "error" if call["is_error"] else ""))
            yield frame(700)
        meta = f"{turn['latency_ms'] / 1000:.1f} s"
        for partial in _reveal_steps(turn["reply"]):
            yield frame(160, [Item("agent", partial, meta)])
        items.append(Item("agent", turn["reply"], meta))
        if turn.get("pending_draft"):
            items.append(Item("note", f"Draft {turn['pending_draft']} shown with a Confirm button"))
            yield frame(900)
        if turn.get("confirmed"):
            items.append(
                Item("note", f"User pressed Confirm -> request {turn['confirmed']} submitted")
            )
        yield frame(2600)
    yield frame(3000)


def eval_frames(results: dict, model: str) -> Iterator[tuple[Image.Image, int]]:
    cases = results["cases"]
    summary = results["summary"]
    lines: list[tuple[str, tuple[int, int, int]]] = [
        (f"$ uv run python evals/run_eval.py --provider gemini --model {model}", COLORS["muted"]),
        ("", COLORS["text"]),
    ]
    rows = HEIGHT // 22 - 6

    def render() -> Image.Image:
        image = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg"])
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, WIDTH, 32], fill=COLORS["header"])
        for i, color in enumerate(((248, 113, 113), (250, 204, 21), (74, 222, 128))):
            draw.ellipse([14 + i * 20, 10, 26 + i * 20, 22], fill=color)
        draw.text(
            (80, 7), "golden set: 31 cases, 5 languages", font=FONT_SMALL, fill=COLORS["muted"]
        )
        for i, (text, color) in enumerate(lines[-rows:]):
            draw.text((PAD, 44 + i * 22), text, font=MONO, fill=color)
        return image

    yield render(), 800
    for case in cases:
        passed = case["passed"]
        style = "style ok" if case["style_ok"] else "style: check"
        called = ", ".join(case["called"]) or "no tool called"
        mark = "PASS" if passed else "FAIL"
        seconds = case["latency_ms"] / 1000
        text = f"{mark}  {case['case_id']:<34}{seconds:>5.1f} s  {called[:22]:<22} {style}"
        lines.append((text, COLORS["pass"] if passed else COLORS["fail"]))
        yield render(), 140
    lines.append(("", COLORS["text"]))
    lines.append(
        (f"{summary['passed']}/{summary['cases']} passed  |  model={model}", COLORS["accent"])
    )
    p50 = summary["latency_ms_p50"] / 1000
    p95 = summary["latency_ms_p95"] / 1000
    lines.append(
        (
            f"style ok: {summary['style_ok']:.0%}   latency p50={p50:.1f} s  p95={p95:.1f} s",
            COLORS["accent"],
        )
    )
    yield render(), 4500


def save_gif(frames: Iterator[tuple[Image.Image, int]], path: Path) -> None:
    images, durations = [], []
    for image, ms in frames:
        images.append(image.quantize(colors=96, method=Image.Quantize.MEDIANCUT))
        durations.append(ms)
    images[0].save(
        path, save_all=True, append_images=images[1:], duration=durations, loop=0, optimize=True
    )
    print(
        f"wrote {path.relative_to(ROOT)}  ({len(images)} frames, {path.stat().st_size // 1024} KB)"
    )


def _latest_gemini_results() -> Path:
    runs = sorted((ROOT / "evals" / "results").glob("*-gemini-*.json"))
    if not runs:
        raise SystemExit("No Gemini eval results found; run evals/run_eval.py first.")
    return runs[-1]


def main(argv: list[str]) -> None:
    conversations = json.loads((DEMO_DIR / "conversations.json").read_text(encoding="utf-8"))
    model = conversations["model"]
    for scenario in conversations["scenarios"]:
        save_gif(chat_frames(scenario, model), DEMO_DIR / f"{scenario['id']}.gif")

    results_path = Path(argv[1]) if len(argv) > 1 else _latest_gemini_results()
    kept = DEMO_DIR / "eval_results.json"
    if results_path.resolve() != kept.resolve():
        shutil.copyfile(results_path, kept)
    results = json.loads(kept.read_text(encoding="utf-8"))
    save_gif(eval_frames(results, model), DEMO_DIR / "eval.gif")


if __name__ == "__main__":
    main(sys.argv)
