from __future__ import annotations

from bisect import bisect_left, bisect_right
from statistics import median
from typing import Dict, List, Sequence, Tuple

from app.services.content_normalizer.models import BoundingBox

_ROW_EPS_MULTIPLIER = 0.8
_ROW_EPS_GAP_RATIO = 0.35
_MIN_EPS = 1.0


def calculate_adaptive_eps(y_coords: Sequence[float], heights: Sequence[float]) -> float:
    """Compute adaptive epsilon for row clustering based on gaps and heights."""
    if not y_coords:
        return _MIN_EPS
    gaps = []
    sorted_coords = sorted(y_coords)
    for idx in range(len(sorted_coords) - 1):
        gaps.append(abs(sorted_coords[idx + 1] - sorted_coords[idx]))
    gap_median = median(gaps) if gaps else 0.0
    height_median = median(heights) if heights else 0.0
    base = max(height_median * _ROW_EPS_MULTIPLIER, gap_median * _ROW_EPS_GAP_RATIO)
    return max(_MIN_EPS, base)


def dbscan_1d(points: Sequence[float], eps: float, min_samples: int) -> List[int]:
    """Cluster 1D points with a simple DBSCAN implementation."""
    n = len(points)
    if n == 0:
        return []

    labels = [-1] * n
    sorted_indices = sorted(range(n), key=lambda i: points[i])
    sorted_points = [points[i] for i in sorted_indices]

    neighbors_cache: Dict[int, List[int]] = {}
    for sorted_idx, point in enumerate(sorted_points):
        left = bisect_left(sorted_points, point - eps)
        right = bisect_right(sorted_points, point + eps)
        neighbor_indices = [sorted_indices[i] for i in range(left, right)]
        neighbors_cache[sorted_indices[sorted_idx]] = neighbor_indices

    visited = [False] * n
    cluster_id = 0

    for i in range(n):
        if visited[i]:
            continue
        visited[i] = True
        neighbors = neighbors_cache.get(i, [])
        if len(neighbors) < min_samples:
            labels[i] = -1
            continue
        labels[i] = cluster_id
        seeds = [neighbor for neighbor in neighbors if neighbor != i]
        seeds_set = set(seeds)
        while seeds:
            current = seeds.pop()
            if not visited[current]:
                visited[current] = True
                current_neighbors = neighbors_cache.get(current, [])
                if len(current_neighbors) >= min_samples:
                    for neighbor in current_neighbors:
                        if neighbor not in seeds_set:
                            seeds.append(neighbor)
                            seeds_set.add(neighbor)
            if labels[current] == -1:
                labels[current] = cluster_id
        cluster_id += 1

    return labels


def cluster_rows(bboxes: Sequence[BoundingBox], eps: float, min_samples: int = 1) -> List[List[BoundingBox]]:
    """Cluster bounding boxes into rows using their y coordinates."""
    if not bboxes:
        return []
    y_coords = [bbox.top_left_y for bbox in bboxes]
    labels = dbscan_1d(y_coords, eps=eps, min_samples=min_samples)
    clusters: Dict[int, List[BoundingBox]] = {}
    for bbox, label in zip(bboxes, labels, strict=True):
        clusters.setdefault(label, []).append(bbox)
    sorted_clusters = sorted(
        clusters.values(),
        key=lambda cluster: min(item.top_left_y for item in cluster),
    )
    return sorted_clusters


def _cluster_columns(row: Sequence[BoundingBox], eps: float) -> List[List[BoundingBox]]:
    """Cluster a row of bounding boxes into columns by x coordinate."""
    x_coords = [bbox.top_left_x for bbox in row]
    labels = dbscan_1d(x_coords, eps=eps, min_samples=1)
    clusters: Dict[int, List[BoundingBox]] = {}
    for bbox, label in zip(row, labels, strict=True):
        clusters.setdefault(label, []).append(bbox)
    return sorted(
        clusters.values(),
        key=lambda cluster: min(item.top_left_x for item in cluster),
    )


def identify_sections(rows: Sequence[Sequence[BoundingBox]]) -> List[List[List[BoundingBox]]]:
    """Group rows into sections based on simple row signature heuristics."""
    sections: List[List[List[BoundingBox]]] = []
    current: List[List[BoundingBox]] = []
    last_signature: Tuple[int, ...] | None = None

    for row in rows:
        signature = (len(row),)
        if last_signature is None or signature == last_signature:
            current.append(list(row))
        else:
            sections.append(current)
            current = [list(row)]
        last_signature = signature

    if current:
        sections.append(current)
    return sections


def cluster_into_coordinates(
    bboxes: Sequence[BoundingBox],
    eps: float | None = None,
) -> List[BoundingBox]:
    """Assign row/column indices to bounding boxes based on clustering."""
    if not bboxes:
        return []

    heights = [bbox.bottom_right_y - bbox.top_left_y for bbox in bboxes]
    y_coords = [bbox.top_left_y for bbox in bboxes]
    row_eps = eps if eps is not None else calculate_adaptive_eps(y_coords, heights)

    rows = cluster_rows(bboxes, eps=row_eps, min_samples=1)
    sections = identify_sections(rows)

    updated_boxes: List[BoundingBox] = []
    row_index = 1
    for section in sections:
        for row in section:
            columns = _cluster_columns(row, eps=row_eps)
            for col_index, column in enumerate(columns, start=1):
                for idx, bbox in enumerate(column, start=1):
                    updated_boxes.append(
                        bbox.model_copy(
                            update={"row": row_index, "col": col_index, "idx": idx}
                        )
                    )
            row_index += 1

    return updated_boxes
