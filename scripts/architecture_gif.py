"""Animated architecture diagram: one request travelling through the system.

Rendered by scripts/make_gifs.py, which provides the fonts, colours and Arabic shaping.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 960, 600
TITLE_H = 50
CAPTION_TOP = 532

Point = tuple[int, int]


@dataclass(frozen=True)
class Node:
    key: str
    label: str
    sub: str
    center: Point
    size: Point
    shape: str  # pill | box | hexagon | cylinder


NODES = {
    n.key: n
    for n in (
        Node("user", "Investor", "Derja · FR · AR · EN", (115, 280), (170, 74), "pill"),
        Node("agent", "Agent loop", "agent.py", (365, 280), (170, 74), "box"),
        Node("gemini", "Gemini 3.5 Flash-Lite", "main model", (590, 125), (220, 84), "hexagon"),
        Node("groq", "Groq gpt-oss-120b", "fallback", (855, 125), (180, 84), "hexagon"),
        Node("tools", "Tools", "6 validated tools", (640, 280), (170, 74), "box"),
        Node(
            "store",
            "Knowledge store",
            "zones · lots · procedures",
            (520, 430),
            (200, 80),
            "cylinder",
        ),
        Node("office", "Back office", "drafts · requests · tickets", (800, 430), (200, 74), "box"),
    )
}


def _edge_points(a: str, b: str) -> list[Point]:
    """Polyline between two node borders; the Confirm path routes under the diagram."""
    if (a, b) in (("user", "office"), ("office", "user")):
        user, office = NODES["user"], NODES["office"]
        start = (user.center[0], user.center[1] + user.size[1] // 2)
        end = (office.center[0], office.center[1] + office.size[1] // 2)
        route = [start, (start[0], 505), (end[0], 505), end]
        return route if a == "user" else route[::-1]
    na, nb = NODES[a], NODES[b]
    return [_border_point(na, nb.center), _border_point(nb, na.center)]


def _border_point(node: Node, toward: Point) -> Point:
    cx, cy = node.center
    dx, dy = toward[0] - cx, toward[1] - cy
    half_w, half_h = node.size[0] / 2, node.size[1] / 2
    scale = min(half_w / abs(dx) if dx else float("inf"), half_h / abs(dy) if dy else float("inf"))
    return (round(cx + dx * scale), round(cy + dy * scale))


EDGES: list[tuple[str, str, str, bool]] = [
    ("user", "agent", "POST /chat", False),
    ("agent", "gemini", "conversation + tools", False),
    ("gemini", "groq", "rate limit / outage", True),
    ("agent", "tools", "tool calls", False),
    ("tools", "store", "", False),
    ("tools", "office", "", False),
    ("user", "office", "Confirm button  ·  POST /requests/{id}/confirm", False),
]


@dataclass(frozen=True)
class Step:
    caption: str
    hops: list[tuple[str, str]]
    packet: str = "default"  # default | warn | ok
    down: str | None = None  # node drawn as unavailable during the step


STEPS = [
    Step("1  The investor asks in Derja:  نحب نحل معمل نسيج في القيروان", [("user", "agent")]),
    Step(
        "2  The agent adds a language hint and sends the conversation and tool list to Gemini",
        [("agent", "gemini")],
    ),
    Step(
        "3  Gemini asks for a tool:  search_lots(governorate=Kairouan, sector=textile)",
        [("gemini", "agent")],
    ),
    Step(
        "4  The agent runs the tool, which validates the input and queries the store",
        [("agent", "tools"), ("tools", "store")],
    ),
    Step(
        "5  Two matching lots come back as the tool result",
        [("store", "tools"), ("tools", "agent")],
    ),
    Step(
        "6  Gemini writes the answer from the tool result, in Derja",
        [("agent", "gemini"), ("gemini", "agent")],
    ),
    Step(
        "7  The reply is cleaned for speech and sent back, in about 2 seconds",
        [("agent", "user")],
        packet="ok",
    ),
    Step(
        "If Gemini is rate-limited or down, the same call goes to Groq for the next 60 s",
        [("agent", "gemini"), ("gemini", "groq")],
        packet="warn",
        down="gemini",
    ),
    Step(
        "Booking: prefill_request only creates draft DRAFT-0001; the agent cannot submit it",
        [("agent", "tools"), ("tools", "office")],
    ),
    Step(
        "Only the user's Confirm button submits the request  ->  tracking number DEMO-0001",
        [("user", "office")],
        packet="ok",
    ),
]


@dataclass(frozen=True)
class Style:
    colors: dict[str, tuple[int, int, int]]
    font: ImageFont.FreeTypeFont
    font_small: ImageFont.FreeTypeFont
    font_bold: ImageFont.FreeTypeFont
    font_caption: ImageFont.FreeTypeFont
    shape_text: object  # callable(str) -> str for Arabic display


def _hexagon(center: Point, size: Point) -> list[Point]:
    cx, cy = center
    w, h = size[0] / 2, size[1] / 2
    inset = h * 0.6
    return [
        (round(cx - w), cy),
        (round(cx - w + inset), round(cy - h)),
        (round(cx + w - inset), round(cy - h)),
        (round(cx + w), cy),
        (round(cx + w - inset), round(cy + h)),
        (round(cx - w + inset), round(cy + h)),
    ]


def _draw_node(
    draw: ImageDraw.ImageDraw, node: Node, style: Style, active: bool, down: bool
) -> None:
    c = style.colors
    fill = (30, 58, 138) if active else c["header"]
    outline = c["accent"] if active else (71, 85, 105)
    if down:
        fill, outline = (69, 26, 26), c["fail"]
    cx, cy = node.center
    w, h = node.size[0] // 2, node.size[1] // 2
    box = [cx - w, cy - h, cx + w, cy + h]
    width = 3 if active or down else 2
    if node.shape == "pill":
        draw.rounded_rectangle(box, radius=h, fill=fill, outline=outline, width=width)
    elif node.shape == "box":
        draw.rounded_rectangle(box, radius=12, fill=fill, outline=outline, width=width)
    elif node.shape == "hexagon":
        draw.polygon(_hexagon(node.center, node.size), fill=fill, outline=outline, width=width)
    else:  # cylinder
        lid = 14
        draw.rectangle([cx - w, cy - h + lid, cx + w, cy + h - lid], fill=fill)
        draw.line([cx - w, cy - h + lid, cx - w, cy + h - lid], fill=outline, width=width)
        draw.line([cx + w, cy - h + lid, cx + w, cy + h - lid], fill=outline, width=width)
        draw.ellipse(
            [cx - w, cy + h - 2 * lid, cx + w, cy + h], fill=fill, outline=outline, width=width
        )
        draw.rectangle([cx - w + width, cy, cx + w - width, cy + h - lid], fill=fill)
        draw.ellipse(
            [cx - w, cy - h, cx + w, cy - h + 2 * lid], fill=fill, outline=outline, width=width
        )
    label_color = c["fail"] if down else c["title"]
    _centered(draw, node.label, (cx, cy - 10), style.font_bold, label_color)
    _centered(draw, node.sub, (cx, cy + 13), style.font_small, c["muted"])


def _centered(
    draw: ImageDraw.ImageDraw, text: str, at: Point, font: ImageFont.FreeTypeFont, fill
) -> None:
    draw.text(at, text, font=font, fill=fill, anchor="mm")


def _dashed(draw: ImageDraw.ImageDraw, a: Point, b: Point, fill, width: int) -> None:
    length = max(1.0, ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5)
    steps = int(length // 12)
    for i in range(0, steps, 2):
        t0, t1 = i / steps, min(1.0, (i + 1) / steps)
        p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
        p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
        draw.line([p0, p1], fill=fill, width=width)


def _arrow_head(draw: ImageDraw.ImageDraw, a: Point, b: Point, fill) -> None:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = max(1.0, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length
    size = 10
    left = (b[0] - ux * size - uy * size * 0.6, b[1] - uy * size + ux * size * 0.6)
    right = (b[0] - ux * size + uy * size * 0.6, b[1] - uy * size - ux * size * 0.6)
    draw.polygon([b, left, right], fill=fill)


def _draw_edges(draw: ImageDraw.ImageDraw, style: Style, active: set[frozenset[str]]) -> None:
    c = style.colors
    for a, b, label, dashed in EDGES:
        points = _edge_points(a, b)
        is_active = frozenset((a, b)) in active
        color = c["accent"] if is_active else (100, 116, 139)
        width = 3 if is_active else 2
        for p0, p1 in zip(points, points[1:], strict=False):
            if dashed:
                _dashed(draw, p0, p1, color, width)
            else:
                draw.line([p0, p1], fill=color, width=width)
        _arrow_head(draw, points[-2], points[-1], color)
        if label:
            if len(points) > 2:
                mid = ((points[1][0] + points[2][0]) // 2, points[1][1])
            else:
                mid = ((points[0][0] + points[1][0]) // 2, (points[0][1] + points[1][1]) // 2)
                # A label longer than its edge would cover the line: put it above instead.
                span = abs(points[1][0] - points[0][0])
                if points[0][1] == points[1][1] and style.font_small.getlength(label) > span - 16:
                    mid = (mid[0], mid[1] - 52)
            box = draw.textbbox(mid, label, font=style.font_small, anchor="mm")
            draw.rectangle([box[0] - 6, box[1] - 3, box[2] + 6, box[3] + 3], fill=c["bg"])
            draw.text(mid, label, font=style.font_small, fill=c["muted"], anchor="mm")


def _point_along(points: list[Point], t: float) -> Point:
    lengths = [
        ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        for a, b in zip(points, points[1:], strict=False)
    ]
    target = t * sum(lengths)
    for (a, b), seg in zip(zip(points, points[1:], strict=False), lengths, strict=False):
        if target <= seg or seg == 0:
            f = target / seg if seg else 0
            return (round(a[0] + (b[0] - a[0]) * f), round(a[1] + (b[1] - a[1]) * f))
        target -= seg
    return points[-1]


def _frame(
    style: Style, step: Step, index: int, packet: Point | None, lit: set[str]
) -> Image.Image:
    c = style.colors
    image = Image.new("RGB", (WIDTH, HEIGHT), c["bg"])
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, WIDTH, TITLE_H], fill=c["header"])
    draw.text((22, 25), "How a request flows", font=style.font_bold, fill=c["title"], anchor="lm")
    draw.text(
        (WIDTH - 22, 25),
        f"step {index + 1} / {len(STEPS)}",
        font=style.font_small,
        fill=c["muted"],
        anchor="rm",
    )
    active = {frozenset(hop) for hop in step.hops}
    _draw_edges(draw, style, active)
    for node in NODES.values():
        _draw_node(draw, node, style, node.key in lit, node.key == step.down)
    if packet:
        color = {"warn": c["fail"], "ok": c["pass"]}.get(step.packet, c["accent"])
        x, y = packet
        draw.ellipse([x - 13, y - 13, x + 13, y + 13], fill=(*color[:3],), outline=c["bg"], width=0)
        draw.ellipse([x - 7, y - 7, x + 7, y + 7], fill=c["title"])
    draw.rectangle([0, CAPTION_TOP, WIDTH, HEIGHT], fill=c["header"])
    caption = style.shape_text(step.caption)  # type: ignore[operator]
    draw.text(
        (22, (CAPTION_TOP + HEIGHT) // 2),
        caption,
        font=style.font_caption,
        fill=c["title"],
        anchor="lm",
    )
    return image


def architecture_frames(style: Style) -> Iterator[tuple[Image.Image, int]]:
    travel_frames = 9
    for index, step in enumerate(STEPS):
        lit: set[str] = set()
        for a, b in step.hops:
            lit.add(a)
            points = _edge_points(a, b)
            for i in range(travel_frames + 1):
                yield _frame(style, step, index, _point_along(points, i / travel_frames), lit), 55
            lit.add(b)
        yield _frame(style, step, index, None, lit), 1700
