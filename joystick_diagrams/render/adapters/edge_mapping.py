"""Map draw.io model edges to the rendered stroke paths of files without cell ids.

draw.io renders every edge as a ``<path d="M … L …" fill="none"
pointer-events="stroke">`` followed by its arrowheads (``<path>``/``<ellipse>``
with ``pointer-events="all"``), interleaved with vertex shapes and labels in
model order. Edges that cannot be drawn (a self-loop, or a terminal point that
falls inside the cell it starts from) produce **no** path, so a plain positional
zip is off by one on 7 of 46 corpus files. The mapping therefore aligns the two
sequences by longest common subsequence where "equal" means *geometrically
plausible*: each rendered end sits where the model says it should, that is on
the (offset) terminal point for a free end, or on the border of the (offset)
terminal cell for an attached end.

The result lets the ordered adapter give every matched ``EdgeRef`` its rendered
``element`` (the stroke path) and ``markers`` so that themes colour the lines
and layout ops can move their ends. Unmatched edges keep ``element=None`` and
are simply not followed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from joystick_diagrams.render.adapters._common import (
    SVG,
    absolute_geometry,
    cell_origin,
    localname,
    rect_of,
)
from joystick_diagrams.render.drawio_model import MxCell

FREE_END_TOLERANCE_PX = 4.0
ATTACHED_END_TOLERANCE_PX = 6.0
MARKER_MAX_SIZE_PX = 24.0
MARKER_DISTANCE_PX = 12.0

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", re.IGNORECASE)
_COMMAND_RE = re.compile(
    r"[MLHVCSQTAZmlhvcsqtaz]|-?\d+(?:\.\d+)?(?:e-?\d+)?", re.IGNORECASE
)
_ARGS_PER_COMMAND = {
    "M": 2,
    "L": 2,
    "T": 2,
    "H": 1,
    "V": 1,
    "C": 6,
    "S": 4,
    "Q": 4,
    "A": 7,
    "Z": 0,
}

Point = tuple[float, float]


# ── Path geometry ──


@dataclass
class PathSegment:
    command: str  # upper-case absolute command letter
    args: list[float]


def parse_path(d: str | None) -> list[PathSegment]:
    """Tokenise an absolute-coordinate path (draw.io never emits relative commands)."""
    segments: list[PathSegment] = []
    tokens = _COMMAND_RE.findall(d or "")
    index = 0
    current: str | None = None
    while index < len(tokens):
        token = tokens[index]
        if token.isalpha():
            current = token.upper()
            index += 1
            if current == "Z":
                segments.append(PathSegment("Z", []))
            continue
        if current is None:
            index += 1
            continue
        count = _ARGS_PER_COMMAND.get(current, 2)
        args = [float(t) for t in tokens[index : index + count]]
        if len(args) < count:
            break
        segments.append(PathSegment(current, args))
        index += count
        if current == "M":
            current = "L"  # implicit line-to after a move-to
    return segments


def format_path(segments: list[PathSegment]) -> str:
    parts: list[str] = []
    for segment in segments:
        if segment.command == "Z":
            parts.append("Z")
            continue
        numbers = " ".join(f"{value:g}" for value in segment.args)
        parts.append(f"{segment.command} {numbers}")
    return " ".join(parts)


def _segment_end(segment: PathSegment, previous: Point | None) -> Point | None:
    args = segment.args
    if segment.command in ("M", "L", "T"):
        return (args[0], args[1])
    if segment.command in ("C", "S", "Q"):
        return (args[-2], args[-1])
    if segment.command == "A":
        return (args[5], args[6])
    if segment.command == "H" and previous is not None:
        return (args[0], previous[1])
    if segment.command == "V" and previous is not None:
        return (previous[0], args[0])
    return previous


def path_points(d: str | None) -> list[Point]:
    """The vertices a path visits (control points excluded), in order."""
    points: list[Point] = []
    previous: Point | None = None
    for segment in parse_path(d):
        end = _segment_end(segment, previous)
        if end is not None and segment.command != "Z":
            points.append(end)
            previous = end
    return points


def path_endpoints(d: str | None) -> tuple[Point, Point] | None:
    points = path_points(d)
    if len(points) < 2:
        return None
    return points[0], points[-1]


def translate_path_end(d: str | None, end: str, dx: float, dy: float) -> str:
    """Move the first (``"source"``) or last (``"target"``) vertex of a path."""
    segments = parse_path(d)
    drawable = [i for i, s in enumerate(segments) if s.command != "Z"]
    if not drawable:
        return d or ""
    index = drawable[0] if end == "source" else drawable[-1]
    segment = segments[index]
    if segment.command in ("M", "L", "T", "C", "S", "Q", "A"):
        segment.args[-2] += dx
        segment.args[-1] += dy
    elif segment.command == "H":
        segment.args[0] += dx
    elif segment.command == "V":
        segment.args[0] += dy
    return format_path(segments)


# ── Model-side expectations ──


def _float(value: str | None) -> float:
    try:
        return float(value) if value is not None else 0.0
    except ValueError:
        return 0.0


def terminal_points(cell: MxCell) -> dict[str, Point]:
    """``{"sourcePoint": (x, y), "targetPoint": (x, y)}`` as stored in the geometry."""
    geometry = cell.element.find("mxGeometry")
    if geometry is None:
        return {}
    return {
        point.get("as"): (_float(point.get("x")), _float(point.get("y")))
        for point in geometry.findall("mxPoint")
        if point.get("as") in ("sourcePoint", "targetPoint")
    }


DEFAULT_ARROW_SIZE = 6.0


def marker_allowance(edge: MxCell, end: str) -> float:
    """How far short of its terminal point a line may stop because of an arrowhead.

    draw.io draws ``classic`` arrows by default; ``endArrow=none`` means none.
    """
    style = edge.style_dict
    arrow_key, size_key = (
        ("startArrow", "startSize") if end == "source" else ("endArrow", "endSize")
    )
    arrow = style.get(arrow_key)
    if arrow is not None and arrow.lower() == "none":
        return 0.0
    try:
        size = float(style.get(size_key) or DEFAULT_ARROW_SIZE)
    except ValueError:
        size = DEFAULT_ARROW_SIZE
    return size + 2.0


@dataclass(frozen=True)
class EndSpec:
    """What the model says about one end of an edge."""

    terminal: MxCell | None  # attached cell, if any
    explicit: Point | None  # sourcePoint/targetPoint, relative to the edge's parent
    allowance: float  # arrowhead size the line may stop short by


def _end_is_plausible(
    rendered: Point,
    spec: EndSpec,
    offset: tuple[float, float],
    origin: tuple[float, float],
    cells: dict[str, MxCell],
) -> bool:
    """``offset`` is rendered-minus-page; ``origin`` the edge's parent group origin."""
    if spec.terminal is not None:
        bounds = absolute_geometry(spec.terminal, cells)
        if bounds is None:
            return True
        tolerance = ATTACHED_END_TOLERANCE_PX + spec.allowance
        return (
            bounds.translated(*offset).expanded(tolerance).distance_to_point(*rendered)
            == 0.0
        )
    if spec.explicit is not None:
        ex = spec.explicit[0] + origin[0] + offset[0]
        ey = spec.explicit[1] + origin[1] + offset[1]
        distance = ((ex - rendered[0]) ** 2 + (ey - rendered[1]) ** 2) ** 0.5
        return distance <= FREE_END_TOLERANCE_PX + spec.allowance
    return True


def end_specs(edge: MxCell, cells: dict[str, MxCell]) -> tuple[EndSpec, EndSpec]:
    points = terminal_points(edge)
    return (
        EndSpec(
            cells.get(edge.source or ""),
            points.get("sourcePoint"),
            marker_allowance(edge, "source"),
        ),
        EndSpec(
            cells.get(edge.target or ""),
            points.get("targetPoint"),
            marker_allowance(edge, "target"),
        ),
    )


def edge_matches_path(
    edge: MxCell, path: Any, offset: tuple[float, float], cells: dict[str, MxCell]
) -> bool:
    """Whether a rendered stroke path could be this edge (both ends plausible)."""
    ends = path_endpoints(path.get("d"))
    if ends is None:
        return False
    origin = cell_origin(
        edge, cells
    )  # explicit points are relative to the edge's parent
    source, target = end_specs(edge, cells)
    return _end_is_plausible(
        ends[0], source, offset, origin, cells
    ) and _end_is_plausible(ends[1], target, offset, origin, cells)


# ── Rendered side ──


def stroke_paths(root: Any) -> list[Any]:
    """Every bare stroke path (draw.io edge line) in document order."""
    return [
        path
        for path in root.iter(f"{SVG}path")
        if path.get("pointer-events") == "stroke"
    ]


def _is_marker_candidate(element: Any) -> bool:
    if localname(element) not in ("path", "ellipse", "circle", "polygon"):
        return False
    if element.get("pointer-events") == "stroke":
        return False
    bbox = rect_of(element)
    return bbox is not None and max(bbox.width, bbox.height) <= MARKER_MAX_SIZE_PX


def _near_an_end(element: Any, ends: tuple[Point, Point]) -> bool:
    bbox = rect_of(element)
    if bbox is None:
        return False
    return any(
        bbox.expanded(MARKER_DISTANCE_PX).distance_to_point(*end) == 0.0 for end in ends
    )


def collect_markers(path: Any) -> tuple[Any, ...]:
    """Arrowheads drawn right after a stroke path (siblings, until something else)."""
    ends = path_endpoints(path.get("d"))
    if ends is None:
        return ()
    markers: list[Any] = []
    sibling = path.getnext()
    while sibling is not None and isinstance(sibling.tag, str):
        if not _is_marker_candidate(sibling) or not _near_an_end(sibling, ends):
            break
        markers.append(sibling)
        sibling = sibling.getnext()
    return tuple(markers)


# ── Alignment ──


def _lcs_pairs(left: list[Any], right: list[Any], equal) -> list[tuple[int, int]]:
    """Order-preserving pairs (i, j) maximising the number of ``equal`` matches."""
    n, m = len(left), len(right)
    table = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if equal(left[i], right[j]):
                table[i][j] = table[i + 1][j + 1] + 1
            else:
                table[i][j] = max(table[i + 1][j], table[i][j + 1])
    pairs: list[tuple[int, int]] = []
    i = j = 0
    while i < n and j < m:
        if equal(left[i], right[j]) and table[i][j] == table[i + 1][j + 1] + 1:
            pairs.append((i, j))
            i += 1
            j += 1
        elif table[i + 1][j] >= table[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


@dataclass
class RenderedEdge:
    path: Any
    markers: tuple[Any, ...]


def map_edges_to_paths(
    root: Any,
    edges: list[MxCell],
    cells: dict[str, MxCell],
    offset: tuple[float, float] | None,
) -> dict[str, RenderedEdge]:
    """``edge id → rendered stroke path (+ markers)`` for an ordered-variant file."""
    paths = stroke_paths(root)
    if not paths or not edges:
        return {}
    shift = offset if offset is not None else (0.0, 0.0)

    def equal(edge: MxCell, path: Any) -> bool:
        return edge_matches_path(edge, path, shift, cells)

    mapping: dict[str, RenderedEdge] = {}
    matched_edges: set[int] = set()
    matched_paths: set[int] = set()
    for i, j in _lcs_pairs(edges, paths, equal):
        matched_edges.add(i)
        matched_paths.add(j)
        edge_id = edges[i].id
        if edge_id is not None:
            mapping[edge_id] = RenderedEdge(paths[j], collect_markers(paths[j]))
    # Second pass: an edge drawn out of model order (children of a group) is
    # matched to the single leftover path that fits it.
    leftover_paths = [j for j in range(len(paths)) if j not in matched_paths]
    for i, edge in enumerate(edges):
        if i in matched_edges or edge.id is None:
            continue
        fits = [j for j in leftover_paths if equal(edge, paths[j])]
        if len(fits) == 1:
            leftover_paths.remove(fits[0])
            mapping[edge.id] = RenderedEdge(
                paths[fits[0]], collect_markers(paths[fits[0]])
            )
    return mapping


__all__ = [
    "EndSpec",
    "PathSegment",
    "RenderedEdge",
    "collect_markers",
    "edge_matches_path",
    "end_specs",
    "format_path",
    "map_edges_to_paths",
    "parse_path",
    "path_endpoints",
    "path_points",
    "stroke_paths",
    "terminal_points",
    "translate_path_end",
]

if __name__ == "__main__":
    pass
