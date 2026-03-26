#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import image_grade_to_3mf as engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prototype stained-glass segmentation using confident lead anchors plus generated pane regions."
    )
    parser.add_argument("image", help="Source image path.")
    parser.add_argument("--long-side-mm", type=float, default=200.0)
    parser.add_argument("--resolution", type=engine.parse_mm_value, default=engine.DEFAULT_RESOLUTION_MM)
    parser.add_argument("--analysis-blur-px", type=float, default=1.2)
    parser.add_argument("--clusters", type=int, default=14)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--smooth-passes", type=int, default=2)
    parser.add_argument("--anchor-luma", type=float, default=42.0)
    parser.add_argument("--anchor-chroma", type=float, default=28.0)
    parser.add_argument("--neutral-chroma", type=float, default=16.0)
    parser.add_argument("--neutral-luma", type=float, default=238.0)
    parser.add_argument("--neutral-contrast", type=float, default=18.0)
    parser.add_argument("--neutral-darkness-delta", type=float, default=3.0)
    parser.add_argument("--neutral-support-min", type=int, default=2)
    parser.add_argument("--neutral-support-max", type=int, default=6)
    parser.add_argument(
        "--max-anchor-pixels",
        type=int,
        default=2600,
        help="Largest connected anchor region allowed to remain lead; larger regions are demoted to glass. (default: 2600)",
    )
    parser.add_argument("--min-piece-pixels", type=int, default=18)
    parser.add_argument("--merge-distance", type=float, default=12.0)
    parser.add_argument(
        "--palette-colors",
        type=int,
        default=10,
        help="Number of final pane colors after palette reduction. (default: 10)",
    )
    parser.add_argument("--output", type=Path, default=Path("/tmp/glass_hybrid_anchor_lab.png"))
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


def build_anchor_mask(original_rgb: np.ndarray, analysis_rgb: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    original_lab = engine.srgb_to_lab(original_rgb)
    analysis_lab = engine.srgb_to_lab(analysis_rgb)
    original_luma = luma_from_rgb(original_rgb)
    analysis_luma = luma_from_rgb(analysis_rgb)
    original_chroma = np.sqrt(np.square(original_lab[..., 1]) + np.square(original_lab[..., 2]))
    analysis_chroma = np.sqrt(np.square(analysis_lab[..., 1]) + np.square(analysis_lab[..., 2]))
    contrast = np.maximum(local_contrast_map(original_rgb), local_contrast_map(analysis_rgb))
    local_darkness_delta = np.maximum(
        engine.mean_filter_3x3(original_luma) - original_luma,
        engine.mean_filter_3x3(analysis_luma) - analysis_luma,
    )

    dark_anchor = (original_luma <= args.anchor_luma) & (original_chroma <= args.anchor_chroma)
    neutral_candidates = (
        (np.minimum(original_chroma, analysis_chroma) <= args.neutral_chroma)
        & (analysis_luma <= args.neutral_luma)
        & (contrast >= args.neutral_contrast)
        & (local_darkness_delta >= args.neutral_darkness_delta)
    )
    support = engine.sum_filter_3x3(neutral_candidates.astype(np.uint8))
    neutral_anchor = neutral_candidates & (support >= args.neutral_support_min) & (support <= args.neutral_support_max)
    anchor_mask = dark_anchor | neutral_anchor
    components, sizes = engine.connected_components(anchor_mask)
    if len(sizes):
        oversized = sizes > args.max_anchor_pixels
        if np.any(oversized):
            valid = components >= 0
            anchor_mask[valid] = ~oversized[components[valid]] & anchor_mask[valid]
    return anchor_mask


def initial_cluster_labels(analysis_rgb: np.ndarray, anchor_mask: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    lab = engine.srgb_to_lab(analysis_rgb)
    valid_mask = ~anchor_mask
    flat_lab = lab[valid_mask]
    if flat_lab.size == 0:
        return np.full(anchor_mask.shape, -1, dtype=np.int32)
    clusters = max(2, min(args.clusters, len(flat_lab)))
    flat_labels, _centers = engine.kmeans(flat_lab.astype(np.float32), clusters=clusters, seed=args.seed)
    labels = np.full(anchor_mask.shape, -1, dtype=np.int32)
    labels[valid_mask] = flat_labels.astype(np.int32)
    labels = engine.majority_smooth_masked(labels, valid_mask, clusters, args.smooth_passes)
    return labels


def componentize(labels: np.ndarray, anchor_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    height, width = labels.shape
    comp_labels = np.full((height, width), -1, dtype=np.int32)
    comp_to_cluster: list[int] = []
    next_id = 0
    for cluster_id in sorted(int(v) for v in np.unique(labels[labels >= 0])):
        mask = (labels == cluster_id) & (~anchor_mask)
        components, sizes = engine.connected_components(mask)
        if len(sizes) == 0:
            continue
        for local_id, size in enumerate(sizes):
            comp_labels[components == local_id] = next_id
            comp_to_cluster.append(cluster_id)
            next_id += 1
    sizes = np.bincount(comp_labels[comp_labels >= 0], minlength=max(next_id, 1))
    return comp_labels, sizes.astype(np.int32), np.asarray(comp_to_cluster, dtype=np.int32)


def adjacency_pairs(labels: np.ndarray) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    height, width = labels.shape
    for y in range(height):
        for x in range(width - 1):
            a = int(labels[y, x])
            b = int(labels[y, x + 1])
            if a >= 0 and b >= 0 and a != b:
                pairs.add((min(a, b), max(a, b)))
    for y in range(height - 1):
        for x in range(width):
            a = int(labels[y, x])
            b = int(labels[y + 1, x])
            if a >= 0 and b >= 0 and a != b:
                pairs.add((min(a, b), max(a, b)))
    return pairs


def adjacency_map(labels: np.ndarray) -> dict[int, set[int]]:
    neighbors: dict[int, set[int]] = {}
    for a, b in adjacency_pairs(labels):
        neighbors.setdefault(a, set()).add(b)
        neighbors.setdefault(b, set()).add(a)
    return neighbors


def merge_small_and_similar_regions(
    labels: np.ndarray,
    anchor_mask: np.ndarray,
    analysis_rgb: np.ndarray,
    args: argparse.Namespace,
) -> np.ndarray:
    result = labels.copy()
    lab = engine.srgb_to_lab(analysis_rgb)
    for _ in range(24):
        changed = False
        valid = result >= 0
        if not np.any(valid):
            break
        lab_means, _rgb_means, counts = engine.component_color_means(result, lab, analysis_rgb)
        neighbors = adjacency_map(result)

        # First, let very small panes merge into the touching neighbor with the closest color.
        small_ids = [idx for idx, size in enumerate(counts) if 0 < size < args.min_piece_pixels]
        for region_id in sorted(small_ids, key=lambda idx: int(counts[idx])):
            touching = [n for n in neighbors.get(region_id, set()) if n < len(counts) and counts[n] > 0]
            if not touching:
                continue
            best_neighbor = min(
                touching,
                key=lambda n: float(np.linalg.norm(lab_means[region_id].astype(np.float32) - lab_means[n].astype(np.float32))),
            )
            result[result == region_id] = best_neighbor
            changed = True

        if changed:
            unique = sorted(int(v) for v in np.unique(result[result >= 0]))
            remap = {old: new for new, old in enumerate(unique)}
            for old, new in remap.items():
                if old != new:
                    result[result == old] = new
            continue

        # Then merge larger neighboring panes only when their colors are genuinely very close.
        for a, b in sorted(adjacency_pairs(result)):
            if a >= len(counts) or b >= len(counts) or counts[a] == 0 or counts[b] == 0:
                continue
            distance = float(np.linalg.norm(lab_means[a].astype(np.float32) - lab_means[b].astype(np.float32)))
            if distance <= args.merge_distance:
                keep, replace = (a, b) if counts[a] >= counts[b] else (b, a)
                result[result == replace] = keep
                changed = True
        if not changed:
            break

        # Compact ids
        unique = sorted(int(v) for v in np.unique(result[result >= 0]))
        remap = {old: new for new, old in enumerate(unique)}
        for old, new in remap.items():
            if old != new:
                result[result == old] = new
    return result


def boundary_from_labels(labels: np.ndarray, anchor_mask: np.ndarray) -> np.ndarray:
    lead = anchor_mask.copy()
    height, width = labels.shape
    for y in range(height):
        for x in range(width):
            here = labels[y, x]
            if here < 0:
                continue
            if x + 1 < width and labels[y, x + 1] >= 0 and labels[y, x + 1] != here:
                lead[y, x] = True
                lead[y, x + 1] = True
            if y + 1 < height and labels[y + 1, x] >= 0 and labels[y + 1, x] != here:
                lead[y, x] = True
                lead[y + 1, x] = True
    return lead


def reduce_pane_palette(
    labels: np.ndarray,
    original_rgb: np.ndarray,
    palette_colors: int,
    seed: int,
) -> np.ndarray:
    valid_ids = sorted(int(v) for v in np.unique(labels[labels >= 0]))
    if not valid_ids:
        return np.zeros((0, 3), dtype=np.uint8)

    lab_means, rgb_means, counts = engine.component_color_means(labels, engine.srgb_to_lab(original_rgb), original_rgb)
    active_lab = lab_means[valid_ids].astype(np.float32)
    active_rgb = rgb_means[valid_ids].astype(np.uint8)
    active_counts = counts[valid_ids].astype(np.float32)
    clusters = max(1, min(int(palette_colors), len(valid_ids)))
    if clusters >= len(valid_ids):
        reduced = np.zeros((max(valid_ids) + 1, 3), dtype=np.uint8)
        for region_id, color in zip(valid_ids, active_rgb):
            reduced[region_id] = color
        return reduced

    grouped_labels, grouped_centers = engine.weighted_kmeans(active_lab, active_counts, clusters=clusters, seed=seed)
    grouped_labels = grouped_labels.astype(np.int32)
    reduced_active = np.zeros((len(valid_ids), 3), dtype=np.uint8)
    for cluster_index in range(clusters):
        member_indices = np.where(grouped_labels == cluster_index)[0]
        if len(member_indices) == 0:
            continue
        weights = active_counts[member_indices][:, None]
        cluster_rgb = np.clip(np.round((active_rgb[member_indices].astype(np.float32) * weights).sum(axis=0) / max(weights.sum(), 1.0)), 0, 255).astype(np.uint8)
        reduced_active[member_indices] = cluster_rgb

    reduced = np.zeros((max(valid_ids) + 1, 3), dtype=np.uint8)
    for region_id, color in zip(valid_ids, reduced_active):
        reduced[region_id] = color
    return reduced


def build_sheet(
    image_path: Path,
    original_rgb: np.ndarray,
    lead_mask: np.ndarray,
    labels: np.ndarray,
    mean_colors_before: np.ndarray,
    mean_colors_after: np.ndarray,
    resolution_mm: float,
    args: argparse.Namespace,
) -> Image.Image:
    font = ImageFont.load_default()
    original = Image.fromarray(original_rgb).convert("RGB")
    before_preview = engine.build_preview(labels, mean_colors_before, lead_mask).convert("RGB")
    after_preview = engine.build_preview(labels, mean_colors_after, lead_mask).convert("RGB")
    preview_height = 260
    for image in (original, before_preview, after_preview):
        image.thumbnail((260, preview_height), Image.Resampling.NEAREST if image is not original else Image.Resampling.LANCZOS)

    padding = 16
    header_h = 72
    footer_h = 30
    gap = 12
    tile_width = original.width + before_preview.width + after_preview.width + gap * 2 + padding * 2
    tile_height = max(original.height, before_preview.height, after_preview.height) + header_h + footer_h + padding * 2
    sheet = Image.new("RGB", (tile_width, tile_height), "#fbf7f0")
    draw = ImageDraw.Draw(sheet)
    draw.rounded_rectangle((0, 0, tile_width - 1, tile_height - 1), radius=18, outline="#d0c3ae", width=2, fill="#fbf7f0")
    draw.text((padding, padding - 2), image_path.name, font=font, fill="#3f2d1d")
    draw.text((padding, padding + 22), f"anchors l<={args.anchor_luma:g} chroma<={args.anchor_chroma:g} neutral c<={args.neutral_chroma:g}@l<={args.neutral_luma:g}", font=font, fill="#745f49")
    draw.text((padding, padding + 44), f"clusters {args.clusters} smooth {args.smooth_passes} merge<={args.merge_distance:g} blur {args.analysis_blur_px:g}px max anchor {args.max_anchor_pixels} min piece {args.min_piece_pixels}", font=font, fill="#745f49")
    draw.text((padding, padding + 62), f"Original    Before reduction    After reduction ({args.palette_colors} colors)    grid {original_rgb.shape[1]}x{original_rgb.shape[0]} @ {engine.format_number(resolution_mm)} mm", font=font, fill="#745f49")
    y = padding + header_h
    x = padding
    for image in (original, before_preview, after_preview):
        sheet.paste(image, (x, y))
        x += image.width + gap
    return sheet


def main() -> int:
    args = parse_args()
    image_path = Path(args.image).expanduser()
    width_mm, height_mm = compute_model_size(image_path, args.long_side_mm)
    grid_width = max(1, math.ceil(width_mm / args.resolution))
    grid_height = max(1, math.ceil(height_mm / args.resolution))
    original_rgb = engine.load_image_to_grid(image_path, grid_width, grid_height, blur_pixels=0.0)
    analysis_rgb = engine.load_image_to_grid(image_path, grid_width, grid_height, blur_pixels=max(args.analysis_blur_px, 0.0))
    anchor_mask = build_anchor_mask(original_rgb, analysis_rgb, args)
    labels = initial_cluster_labels(analysis_rgb, anchor_mask, args)
    component_labels, _sizes, _cluster_map = componentize(labels, anchor_mask)
    merged_labels = merge_small_and_similar_regions(component_labels, anchor_mask, analysis_rgb, args)
    lead_mask = boundary_from_labels(merged_labels, anchor_mask)
    mean_colors_before = engine.component_color_means(merged_labels, engine.srgb_to_lab(original_rgb), original_rgb)[1]
    mean_colors_after = reduce_pane_palette(merged_labels, original_rgb, args.palette_colors, args.seed)
    sheet = build_sheet(image_path, original_rgb, lead_mask, merged_labels, mean_colors_before, mean_colors_after, args.resolution, args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
