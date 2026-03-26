#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import image_grade_to_3mf as engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prototype stained-glass segmentation by growing glass interiors and deriving lead from the leftover boundaries."
    )
    parser.add_argument("image", help="Source image path.")
    parser.add_argument(
        "--long-side-mm",
        type=float,
        default=200.0,
        help="Virtual long side size used to derive the working grid. (default: 200)",
    )
    parser.add_argument(
        "--resolution",
        type=engine.parse_mm_value,
        default=engine.DEFAULT_RESOLUTION_MM,
        help="Working resolution in mm. (default: 0.4mm)",
    )
    parser.add_argument(
        "--analysis-blur-px",
        type=float,
        default=1.4,
        help="Gaussian blur radius in pixels used only for glass detection/growth. (default: 1.4)",
    )
    parser.add_argument(
        "--lead-luma-threshold",
        type=float,
        default=48.0,
        help="Very dark pixels at or below this luma remain hard barriers. (default: 48)",
    )
    parser.add_argument(
        "--hard-lead-chroma-max",
        type=float,
        default=26.0,
        help="Maximum chroma for a very dark pixel to count as true black lead. (default: 26)",
    )
    parser.add_argument(
        "--edge-threshold",
        type=float,
        default=22.0,
        help="Pixels at or above this local contrast are treated as hard growth barriers. (default: 22)",
    )
    parser.add_argument(
        "--seed-edge-threshold",
        type=float,
        default=10.0,
        help="Maximum local contrast for interior seed pixels. (default: 10)",
    )
    parser.add_argument(
        "--neutral-chroma-max",
        type=float,
        default=22.0,
        help="Low-chroma pixels at moderate brightness are excluded from glass seeds. (default: 22)",
    )
    parser.add_argument(
        "--neutral-luma-max",
        type=float,
        default=235.0,
        help="Upper luma bound for low-chroma pixels excluded from seeds. (default: 235)",
    )
    parser.add_argument(
        "--neutral-edge-threshold",
        type=float,
        default=14.0,
        help="Minimum local contrast for neutral highlighted lead pixels. (default: 14)",
    )
    parser.add_argument(
        "--neutral-darkness-delta",
        type=float,
        default=3.0,
        help="How much darker than the local 3x3 mean a neutral highlighted lead pixel should be. (default: 3)",
    )
    parser.add_argument(
        "--neutral-support-min",
        type=int,
        default=2,
        help="Minimum 3x3 support count for a neutral highlighted lead candidate. (default: 2)",
    )
    parser.add_argument(
        "--neutral-support-max",
        type=int,
        default=6,
        help="Maximum 3x3 support count for a neutral highlighted lead candidate; lower values favor thinner lines. (default: 6)",
    )
    parser.add_argument(
        "--grow-color-distance",
        type=float,
        default=26.0,
        help="Maximum Lab distance from a region mean when growing a piece. (default: 26)",
    )
    parser.add_argument(
        "--min-piece-pixels",
        type=int,
        default=18,
        help="Minimum seed component size to keep as a piece. (default: 18)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/glass_interior_growth_lab.png"),
        help="Output PNG path. (default: /tmp/glass_interior_growth_lab.png)",
    )
    return parser.parse_args()


def compute_model_size(image_path: Path, long_side_mm: float) -> tuple[float, float]:
    with Image.open(image_path) as image:
        width_px, height_px = image.size
    scale = long_side_mm / float(max(width_px, height_px))
    return width_px * scale, height_px * scale


def local_contrast_map(rgb_image: np.ndarray) -> np.ndarray:
    rgb = rgb_image.astype(np.float32)
    luma = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    contrast = np.zeros_like(luma)
    contrast[:-1, :] = np.maximum(contrast[:-1, :], np.abs(luma[:-1, :] - luma[1:, :]))
    contrast[1:, :] = np.maximum(contrast[1:, :], np.abs(luma[1:, :] - luma[:-1, :]))
    contrast[:, :-1] = np.maximum(contrast[:, :-1], np.abs(luma[:, :-1] - luma[:, 1:]))
    contrast[:, 1:] = np.maximum(contrast[:, 1:], np.abs(luma[:, 1:] - luma[:, :-1]))
    return contrast


def luma_from_rgb(rgb_image: np.ndarray) -> np.ndarray:
    rgb = rgb_image.astype(np.float32)
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def build_seed_mask(
    rgb_image: np.ndarray,
    hard_lead_rgb_image: np.ndarray,
    contrast: np.ndarray,
    lead_luma_threshold: float,
    hard_lead_chroma_max: float,
    seed_edge_threshold: float,
    neutral_chroma_max: float,
    neutral_luma_max: float,
    neutral_edge_threshold: float,
    neutral_darkness_delta: float,
    neutral_support_min: int,
    neutral_support_max: int,
) -> tuple[np.ndarray, np.ndarray]:
    rgb = rgb_image.astype(np.float32)
    luma = luma_from_rgb(rgb_image)
    hard_luma = luma_from_rgb(hard_lead_rgb_image)
    lab = engine.srgb_to_lab(rgb_image)
    chroma = np.sqrt(np.square(lab[..., 1]) + np.square(lab[..., 2]))
    original_lab = engine.srgb_to_lab(hard_lead_rgb_image)
    original_chroma = np.sqrt(np.square(original_lab[..., 1]) + np.square(original_lab[..., 2]))
    original_contrast = local_contrast_map(hard_lead_rgb_image)
    local_darkness_delta = np.maximum(
        engine.mean_filter_3x3(luma) - luma,
        engine.mean_filter_3x3(hard_luma) - hard_luma,
    )
    combined_contrast = np.maximum(contrast, original_contrast)
    combined_chroma = np.minimum(chroma, original_chroma)

    hard_lead = (hard_luma <= lead_luma_threshold) & (original_chroma <= hard_lead_chroma_max)
    neutral_candidates = (
        (combined_chroma <= neutral_chroma_max)
        & (luma <= neutral_luma_max)
        & (combined_contrast >= neutral_edge_threshold)
        & (local_darkness_delta >= neutral_darkness_delta)
    )
    neutral_support = engine.sum_filter_3x3(neutral_candidates.astype(np.uint8))
    neutral_barrier = neutral_candidates & (neutral_support >= neutral_support_min) & (neutral_support <= neutral_support_max)
    barrier = hard_lead | neutral_barrier

    seed_mask = (~barrier) & (contrast <= seed_edge_threshold)
    return seed_mask, barrier


def region_grow_labels(
    seed_labels: np.ndarray,
    barrier: np.ndarray,
    lab_image: np.ndarray,
    grow_color_distance: float,
) -> np.ndarray:
    labels = seed_labels.copy()
    component_count = int(seed_labels.max()) + 1 if np.any(seed_labels >= 0) else 0
    if component_count == 0:
        return labels

    sums = np.zeros((component_count, 3), dtype=np.float64)
    counts = np.zeros(component_count, dtype=np.int32)
    valid = labels >= 0
    np.add.at(sums, labels[valid], lab_image[valid].astype(np.float64))
    np.add.at(counts, labels[valid], 1)

    queue: deque[tuple[int, int]] = deque()
    height, width = labels.shape
    for y in range(height):
        for x in range(width):
            if labels[y, x] >= 0:
                queue.append((y, x))

    while queue:
        y, x = queue.popleft()
        label = labels[y, x]
        mean = sums[label] / max(counts[label], 1)
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if ny < 0 or nx < 0 or ny >= height or nx >= width:
                continue
            if barrier[ny, nx] or labels[ny, nx] >= 0:
                continue
            distance = float(np.linalg.norm(lab_image[ny, nx].astype(np.float64) - mean))
            if distance > grow_color_distance:
                continue
            labels[ny, nx] = label
            sums[label] += lab_image[ny, nx]
            counts[label] += 1
            queue.append((ny, nx))
    return labels


def fill_unassigned_from_neighbors(labels: np.ndarray, barrier: np.ndarray) -> np.ndarray:
    filled = labels.copy()
    height, width = filled.shape
    changed = True
    while changed:
        changed = False
        updates: list[tuple[int, int, int]] = []
        for y in range(height):
            for x in range(width):
                if barrier[y, x] or filled[y, x] >= 0:
                    continue
                neighbors = []
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < height and 0 <= nx < width and filled[ny, nx] >= 0:
                        neighbors.append(int(filled[ny, nx]))
                if not neighbors:
                    continue
                values, counts = np.unique(np.asarray(neighbors, dtype=np.int32), return_counts=True)
                updates.append((y, x, int(values[np.argmax(counts)])))
        if updates:
            changed = True
            for y, x, label in updates:
                filled[y, x] = label
    return filled


def relabel_components(mask: np.ndarray, min_piece_pixels: int) -> np.ndarray:
    labels, sizes = engine.connected_components(mask)
    if len(sizes) == 0:
        return np.full(mask.shape, -1, dtype=np.int32)
    keep = sizes >= min_piece_pixels
    filtered_mask = np.zeros(mask.shape, dtype=bool)
    valid = labels >= 0
    filtered_mask[valid] = keep[labels[valid]]

    final_mask = filtered_mask
    final_labels, _ = engine.connected_components(final_mask)
    return final_labels


def labels_to_mean_colors(labels: np.ndarray, rgb_image: np.ndarray) -> np.ndarray:
    if not np.any(labels >= 0):
        return np.zeros((0, 3), dtype=np.uint8)
    lab_means, rgb_means, _counts = engine.component_color_means(labels, engine.srgb_to_lab(rgb_image), rgb_image)
    _ = lab_means
    return rgb_means


def build_lead_mask_from_labels(labels: np.ndarray, barrier: np.ndarray) -> np.ndarray:
    lines = barrier.copy()
    height, width = labels.shape
    for y in range(height):
        for x in range(width):
            here = labels[y, x]
            if here < 0:
                continue
            if x + 1 < width and labels[y, x + 1] >= 0 and labels[y, x + 1] != here:
                lines[y, x] = True
                lines[y, x + 1] = True
            if y + 1 < height and labels[y + 1, x] >= 0 and labels[y + 1, x] != here:
                lines[y, x] = True
                lines[y + 1, x] = True
    return lines


def build_sheet(
    image_path: Path,
    rgb_image: np.ndarray,
    seed_mask: np.ndarray,
    lead_mask: np.ndarray,
    labels: np.ndarray,
    mean_colors: np.ndarray,
    resolution_mm: float,
    args: argparse.Namespace,
) -> Image.Image:
    font = ImageFont.load_default()
    original = Image.fromarray(rgb_image).convert("RGB")
    seed_preview = engine.mask_preview(~seed_mask).convert("RGB")
    glass_preview = engine.build_preview(labels, mean_colors, lead_mask).convert("RGB")

    preview_height = 260
    for image in (original, seed_preview, glass_preview):
        image.thumbnail((260, preview_height), Image.Resampling.NEAREST if image is not original else Image.Resampling.LANCZOS)

    padding = 16
    header_h = 72
    footer_h = 30
    gap = 12
    tile_width = original.width + seed_preview.width + glass_preview.width + gap * 2 + padding * 2
    tile_height = max(original.height, seed_preview.height, glass_preview.height) + header_h + footer_h + padding * 2

    sheet = Image.new("RGB", (tile_width, tile_height), "#fbf7f0")
    draw = ImageDraw.Draw(sheet)
    draw.rounded_rectangle((0, 0, tile_width - 1, tile_height - 1), radius=18, outline="#d0c3ae", width=2, fill="#fbf7f0")
    draw.text((padding, padding - 2), image_path.name, font=font, fill="#3f2d1d")
    draw.text(
        (padding, padding + 22),
        f"lead l<={args.lead_luma_threshold:g} hard chroma<={args.hard_lead_chroma_max:g} seed<={args.seed_edge_threshold:g} neutral chroma<={args.neutral_chroma_max:g}@l<={args.neutral_luma_max:g}",
        font=font,
        fill="#745f49",
    )
    draw.text(
        (padding, padding + 44),
        f"neutral edge>={args.neutral_edge_threshold:g} dark delta>={args.neutral_darkness_delta:g} support {args.neutral_support_min}-{args.neutral_support_max} grow dist<={args.grow_color_distance:g} blur {args.analysis_blur_px:g}px min piece {args.min_piece_pixels}",
        font=font,
        fill="#745f49",
    )
    draw.text((padding, padding + 62), f"Original    Seed/barrier view    Grown glass pieces    grid {rgb_image.shape[1]}x{rgb_image.shape[0]} @ {engine.format_number(resolution_mm)} mm", font=font, fill="#745f49")

    y = padding + header_h
    x = padding
    for image in (original, seed_preview, glass_preview):
        sheet.paste(image, (x, y))
        x += image.width + gap
    return sheet


def main() -> int:
    args = parse_args()
    image_path = Path(args.image).expanduser()
    if not image_path.exists():
        raise SystemExit(f"Image not found: {image_path}")

    width_mm, height_mm = compute_model_size(image_path, args.long_side_mm)
    grid_width = max(1, math.ceil(width_mm / args.resolution))
    grid_height = max(1, math.ceil(height_mm / args.resolution))
    rgb_image = engine.load_image_to_grid(image_path, grid_width, grid_height, blur_pixels=0.0)
    analysis_rgb = engine.load_image_to_grid(
        image_path,
        grid_width,
        grid_height,
        blur_pixels=max(args.analysis_blur_px, 0.0),
    )
    contrast = local_contrast_map(analysis_rgb)
    seed_mask, barrier = build_seed_mask(
        analysis_rgb,
        rgb_image,
        contrast,
        lead_luma_threshold=args.lead_luma_threshold,
        hard_lead_chroma_max=args.hard_lead_chroma_max,
        seed_edge_threshold=args.seed_edge_threshold,
        neutral_chroma_max=args.neutral_chroma_max,
        neutral_luma_max=args.neutral_luma_max,
        neutral_edge_threshold=args.neutral_edge_threshold,
        neutral_darkness_delta=args.neutral_darkness_delta,
        neutral_support_min=args.neutral_support_min,
        neutral_support_max=args.neutral_support_max,
    )
    seed_labels = relabel_components(seed_mask, args.min_piece_pixels)
    labels = region_grow_labels(seed_labels, barrier, engine.srgb_to_lab(analysis_rgb), args.grow_color_distance)
    labels = fill_unassigned_from_neighbors(labels, barrier)
    final_mask = labels >= 0
    final_labels = relabel_components(final_mask, args.min_piece_pixels)
    lead_mask = build_lead_mask_from_labels(final_labels, barrier)
    mean_colors = labels_to_mean_colors(final_labels, rgb_image)

    sheet = build_sheet(
        image_path,
        rgb_image,
        seed_mask,
        lead_mask,
        final_labels,
        mean_colors,
        args.resolution,
        args,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
