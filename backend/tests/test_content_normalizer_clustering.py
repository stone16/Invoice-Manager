from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "backend"))

from app.services.content_normalizer.models import BoundingBox  # noqa: E402
from app.services.content_normalizer.clustering.dbscan_algorithm import (  # noqa: E402
    calculate_adaptive_eps,
    cluster_rows,
    identify_sections,
    cluster_into_coordinates,
)


def _bbox(x0: float, y0: float, x1: float, y1: float, text: str) -> BoundingBox:
    return BoundingBox(
        id="",
        raw_value=text,
        top_left_x=x0,
        top_left_y=y0,
        bottom_right_x=x1,
        bottom_right_y=y1,
    )


def test_cluster_rows_groups_by_y_coordinate():
    boxes = [
        _bbox(0, 10, 10, 20, "A"),
        _bbox(15, 12, 25, 22, "B"),
        _bbox(0, 50, 10, 60, "C"),
        _bbox(15, 52, 25, 62, "D"),
    ]

    rows = cluster_rows(boxes, eps=5, min_samples=1)
    assert len(rows) == 2
    assert {box.raw_value for box in rows[0]} == {"A", "B"}
    assert {box.raw_value for box in rows[1]} == {"C", "D"}


def test_calculate_adaptive_eps_increases_with_gaps():
    y_coords = [10, 12, 50, 52]
    heights = [10, 10, 10, 10]
    eps = calculate_adaptive_eps(y_coords, heights)
    assert eps >= 5


def test_identify_sections_splits_on_column_structure_change():
    rows = [
        [_bbox(0, 10, 10, 20, "A"), _bbox(40, 10, 50, 20, "B")],
        [_bbox(0, 30, 10, 40, "C"), _bbox(40, 30, 50, 40, "D")],
        [_bbox(0, 60, 10, 70, "E")],
    ]

    sections = identify_sections(rows)
    assert len(sections) == 2
    assert len(sections[0]) == 2
    assert len(sections[1]) == 1


def test_cluster_into_coordinates_assigns_row_col_idx():
    boxes = [
        _bbox(0, 10, 10, 20, "A"),
        _bbox(40, 10, 50, 20, "B"),
        _bbox(0, 40, 10, 50, "C"),
        _bbox(40, 40, 50, 50, "D"),
    ]

    clustered = cluster_into_coordinates(boxes, eps=5)
    by_text = {box.raw_value: box for box in clustered}

    assert by_text["A"].row == 1
    assert by_text["B"].row == 1
    assert by_text["C"].row == 2
    assert by_text["D"].row == 2
    assert by_text["A"].col == 1
    assert by_text["B"].col == 2
    assert by_text["C"].col == 1
    assert by_text["D"].col == 2
    assert all(box.idx is not None for box in clustered)
