"""Conservative detection of page labels visible in page margins."""

import re
from dataclasses import dataclass

import pymupdf

_PAGE_LABEL_PATTERN = re.compile(
    r"^(?:page\s+)?(?P<label>\d{1,4}|[ivxlcdm]{1,12})"
    r"(?:\s*(?:/|of)\s*\d{1,4})?$",
    re.IGNORECASE,
)
_MARGIN_RATIO = 0.10
_EDGE_RATIO = 0.22
_LINE_TOLERANCE_RATIO = 0.004


@dataclass(frozen=True, slots=True)
class _LabelCandidate:
    value: str
    score: int
    distance_from_edge: float


def _label_from_text(text: str) -> str | None:
    stripped = text.strip()
    if (stripped.startswith("(") and stripped.endswith(")")) or (
        stripped.startswith("[") and stripped.endswith("]")
    ):
        return None
    cleaned = stripped.strip("-–—|·•")
    match = _PAGE_LABEL_PATTERN.fullmatch(cleaned)
    return match.group("label") if match else None


def _is_likely_year(label: str) -> bool:
    return label.isdigit() and 1900 <= int(label) <= 2099


def detect_visible_page_label(page: pymupdf.Page) -> str | None:
    """Return an unambiguous numeric or Roman label printed near a page edge.

    The detector only considers complete margin lines or numeric tokens at the
    far left/right of a margin line. This avoids treating arbitrary values in a
    financial table as page numbers.
    """

    words = page.get_text("words", sort=True)
    if not words:
        return None

    page_width = float(page.rect.width)
    page_height = float(page.rect.height)
    margin_words: list[tuple] = []

    for word in words:
        vertical_center = (float(word[1]) + float(word[3])) / 2
        in_top_margin = vertical_center <= page_height * _MARGIN_RATIO
        in_bottom_margin = vertical_center >= page_height * (1 - _MARGIN_RATIO)
        if in_top_margin or in_bottom_margin:
            margin_words.append(word)

    line_tolerance = max(2.0, page_height * _LINE_TOLERANCE_RATIO)
    visual_lines: list[list[tuple]] = []
    for word in sorted(
        margin_words,
        key=lambda item: ((float(item[1]) + float(item[3])) / 2, float(item[0])),
    ):
        vertical_center = (float(word[1]) + float(word[3])) / 2
        if not visual_lines:
            visual_lines.append([word])
            continue

        previous = visual_lines[-1]
        previous_center = sum((float(item[1]) + float(item[3])) / 2 for item in previous) / len(
            previous
        )
        if abs(vertical_center - previous_center) <= line_tolerance:
            previous.append(word)
        else:
            visual_lines.append([word])

    candidates: list[_LabelCandidate] = []
    for line_words in visual_lines:
        ordered = sorted(line_words, key=lambda item: float(item[0]))
        line_text = " ".join(str(item[4]) for item in ordered)
        line_label = _label_from_text(line_text)
        vertical_center = (float(ordered[0][1]) + float(ordered[0][3])) / 2
        edge_distance = min(vertical_center, page_height - vertical_center)

        if line_label is not None:
            candidates.append(_LabelCandidate(line_label, 4, edge_distance))
            continue

        boundary_labels: list[str] = []
        first_label = _label_from_text(str(ordered[0][4]))
        if first_label and float(ordered[0][0]) <= page_width * _EDGE_RATIO:
            boundary_labels.append(first_label)

        last_label = _label_from_text(str(ordered[-1][4]))
        if last_label and float(ordered[-1][2]) >= page_width * (1 - _EDGE_RATIO):
            if last_label not in boundary_labels:
                boundary_labels.append(last_label)

        boundary_labels = [label for label in boundary_labels if not _is_likely_year(label)]
        if boundary_labels:
            if len(boundary_labels) == 2:
                left, right = boundary_labels
                consecutive_spread = (
                    left.isdigit() and right.isdigit() and int(right) == int(left) + 1
                )
                if consecutive_spread:
                    candidates.append(_LabelCandidate(f"{left}–{right}", 3, edge_distance))
                continue
            candidates.append(_LabelCandidate(boundary_labels[0], 3, edge_distance))

    if not candidates:
        return None

    best_score = max(candidate.score for candidate in candidates)
    highest_scoring = [candidate for candidate in candidates if candidate.score == best_score]
    nearest_distance = min(candidate.distance_from_edge for candidate in highest_scoring)
    nearest = [
        candidate
        for candidate in highest_scoring
        if candidate.distance_from_edge == nearest_distance
    ]
    values = {candidate.value for candidate in nearest}
    return values.pop() if len(values) == 1 else None
