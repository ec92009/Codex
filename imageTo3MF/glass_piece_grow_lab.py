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
        description="Prototype glass-piece segmentation by growing pieces until they hit dark lead."
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
        "--lead-threshold",
        type=float,
        default=55.0,
        help="Pixels at or below this luminance are treated as lead. (default: 55)",
    )
    parser.add_argument(
        "--neutral-chroma-max",
        type=float,
        default=18.0,
        help="Pixels at or below this Lab chroma are also treated as lead-like even if brighter. (default: 18)",
    )
    parser.add_argument(
        "--neutral-luma-cap",
        type=float,
        default=235.0,
        help="Upper luma cap for neutral lead-like pixels. (default: 235)",
    )
    parser.add_argument(
        "--lead-grow",
        type=int,
        default=1,
        help="Extra 1-pixel dilations applied to the detected lead mask. (default: 1)",
    )
    parser.add_argument(
        "--min-piece-pixels",
        type=int,
        default=12,
        help="Minimum component size to keep as a glass piece. Smaller pieces are turned into lead. (default: 12)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/glass_piece_grow_lab.png"),
        help="Output PNG path. (default: /tmp/glass_piece_grow_lab.png)",
    )
    return parser.parse_args()


def compute_model_size(image_path: Path, long_side_mm: float) -> tuple[float, float]:
    with Image.open(image_path) as image:
        width_px, height_px = image.size
    long_side_px = max(width_px, height_px)
    scale = long_side_mm / float(long_side_px)
    return width_px * scale, height_px * scale


def luma_image(rgb_image: np.ndarray) -> np.ndarray:
    rgb = rgb_image.astype(np.float32)
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def glass_piece_labels(
    rgb_image: np.ndarray,
    lead_threshold: float,
    neutral_chroma_max: float,
    neutral_luma_cap: float,
    lead_grow: int,
    min_piece_pixels: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    luma = luma_image(rgb_image)
    lab = engine.srgb_to_lab(rgb_image)
    chroma = np.sqrt(np.square(lab[..., 1]) + np.square(lab[..., 2]))
    dark_lead = luma <= lead_threshold
    neutral_lead = (chroma <= neutral_chroma_max) & (luma <= neutral_luma_cap)
    lead_mask = dark_lead | neutral_lead
    if lead_grow > 0:
        lead_mask = engine.dilate_mask(lead_mask, lead_grow)

    glass_mask = ~lead_mask
    component_labels, component_sizes = engine.connected_components(glass_mask)
    if len(component_sizes) == 0:
        empty_labels = np.full(glass_mask.shape, -1, dtype=np.int32)
        return empty_labels, np.zeros((0, 3), dtype=np.uint8), lead_mask

    keep = component_sizes >= min_piece_pixels
    filtered_glass_mask = np.zeros_like(glass_mask, dtype=bool)
    valid = component_labels >= 0
    filtered_glass_mask[valid] = keep[component_labels[valid]]
    lead_mask = ~filtered_glass_mask

    component_labels, _component_sizes = engine.connected_components(filtered_glass_mask)
    _lab_means, rgb_means, _counts = engine.component_color_means(
        component_labels,
        lab,
        rgb_image,
    )
    return component_labels, rgb_means, lead_mask


def build_sheet(
    image_path: Path,
    rgb_image: np.ndarray,
    lead_mask: np.ndarray,
    labels: np.ndarray,
    mean_colors: np.ndarray,
    resolution_mm: float,
    font: ImageFont.ImageFont,
    lead_threshold: float,
    neutral_chroma_max: float,
    neutral_luma_cap: float,
    lead_grow: int,
    min_piece_pixels: int,
) -> Image.Image:
    original = Image.fromarray(rgb_image).convert("RGB")
    lead_preview = engine.mask_preview(lead_mask).convert("RGB")
    piece_preview = engine.build_preview(labels, mean_colors, lead_mask).convert("RGB")

    preview_height = 260
    for image in (original, lead_preview, piece_preview):
        image.thumbnail((260, preview_height), Image.Resampling.NEAREST if image is not original else Image.Resampling.LANCZOS)

    padding = 16
    header_h = 72
    footer_h = 30
    gap = 12
    tile_width = original.width + lead_preview.width + piece_preview.width + gap * 2 + padding * 2
    tile_height = max(original.height, lead_preview.height, piece_preview.height) + header_h + footer_h + padding * 2

    sheet = Image.new("RGB", (tile_width, tile_height), "#fbf7f0")
    draw = ImageDraw.Draw(sheet)
    draw.rounded_rectangle((0, 0, tile_width - 1, tile_height - 1), radius=18, outline="#d0c3ae", width=2, fill="#fbf7f0")
    draw.text((padding, padding - 2), f"{image_path.name}", font=font, fill="#3f2d1d")
    draw.text(
        (padding, padding + 22),
        f"Lead luma {lead_threshold:g}   neutral chroma {neutral_chroma_max:g} @ luma<={neutral_luma_cap:g}   grow {lead_grow}   min piece {min_piece_pixels}",
        font=font,
        fill="#745f49",
    )
    draw.text(
        (padding, padding + 44),
        f"Original    Lead mask    Piece-average glass    grid {rgb_image.shape[1]}x{rgb_image.shape[0]} @ {engine.format_number(resolution_mm)} mm",
        font=font,
        fill="#745f49",
    )

    y = padding + header_h
    x = padding
    for image in (original, lead_preview, piece_preview):
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
    labels, mean_colors, lead_mask = glass_piece_labels(
        rgb_image,
        lead_threshold=args.lead_threshold,
        neutral_chroma_max=args.neutral_chroma_max,
        neutral_luma_cap=args.neutral_luma_cap,
        lead_grow=args.lead_grow,
        min_piece_pixels=args.min_piece_pixels,
    )

    font = ImageFont.load_default()
    sheet = build_sheet(
        image_path,
        rgb_image,
        lead_mask,
        labels,
        mean_colors,
        args.resolution,
        font,
        args.lead_threshold,
        args.neutral_chroma_max,
        args.neutral_luma_cap,
        args.lead_grow,
        args.min_piece_pixels,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
