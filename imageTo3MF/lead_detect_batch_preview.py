#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import image_grade_to_3mf as engine


DEFAULT_DESKTOP_IMAGES = [Path.home() / "Desktop" / f"{letter}.png" for letter in "ABCDEF"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a 6-tile preview sheet showing LeadLight detect mode stages 1 and 2."
    )
    parser.add_argument(
        "images",
        nargs="*",
        help="Optional image paths. Defaults to ~/Desktop/A.png through ~/Desktop/F.png.",
    )
    parser.add_argument(
        "--long-side-mm",
        type=float,
        default=200.0,
        help="Virtual long side size used to derive the working grid for each image. (default: 200)",
    )
    parser.add_argument(
        "--resolution",
        type=engine.parse_mm_value,
        default=engine.DEFAULT_RESOLUTION_MM,
        help="Working resolution in mm. (default: 0.4mm)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / "Desktop" / "lead_detect_steps_1_2_sheet.png",
        help="Output PNG path. (default: ~/Desktop/lead_detect_steps_1_2_sheet.png)",
    )
    parser.add_argument("--strong-luma-cap", type=float, default=72.0, help="Cap for strong dark-pixel threshold.")
    parser.add_argument("--weak-luma-cap", type=float, default=92.0, help="Cap for weak dark-pixel threshold.")
    parser.add_argument("--strong-percentile", type=float, default=10.0, help="Image luma percentile used for strong seed pixels.")
    parser.add_argument("--weak-percentile", type=float, default=18.0, help="Image luma percentile used for weak expansion pixels.")
    parser.add_argument("--strong-contrast", type=float, default=18.0, help="Minimum local contrast for strong seed pixels.")
    parser.add_argument("--weak-contrast", type=float, default=12.0, help="Minimum local contrast for weak expansion pixels.")
    parser.add_argument("--strong-color-range", type=float, default=80.0, help="Maximum RGB range allowed for strong seed pixels.")
    parser.add_argument("--weak-color-range", type=float, default=110.0, help="Maximum RGB range allowed for weak expansion pixels.")
    parser.add_argument("--grow-passes", type=int, default=3, help="How many 1-pixel growth passes extend strong lead into weak lead.")
    parser.add_argument("--blue-dominance-max", type=float, default=999.0, help="Reject dark pixels whose blue channel exceeds red/green by more than this amount.")
    parser.add_argument("--red-dominance-max", type=float, default=999.0, help="Reject dark pixels whose red channel exceeds green/blue by more than this amount.")
    parser.add_argument("--neutral-edge-luma-cap", type=float, default=255.0, help="Optional lighter luma cap for neutral edge seeds.")
    parser.add_argument("--neutral-edge-contrast", type=float, default=999.0, help="Minimum contrast for neutral edge seeds.")
    parser.add_argument("--neutral-edge-color-range", type=float, default=999.0, help="Maximum color range for neutral edge seeds.")
    parser.add_argument("--separator-luma-cap", type=float, default=255.0, help="Luma cap for thin separator-edge seeds.")
    parser.add_argument("--separator-contrast", type=float, default=999.0, help="Minimum contrast for thin separator-edge seeds.")
    parser.add_argument("--separator-darkness-delta", type=float, default=999.0, help="How much darker than the local 3x3 mean a separator-edge seed must be.")
    parser.add_argument("--separator-color-range", type=float, default=999.0, help="Maximum color range for thin separator-edge seeds.")
    parser.add_argument("--ridge-luma-cap", type=float, default=255.0, help="Luma cap for directional ridge seeds.")
    parser.add_argument("--ridge-darkness-delta", type=float, default=999.0, help="How much darker than both flanks a directional ridge seed must be.")
    parser.add_argument("--ridge-side-color-diff", type=float, default=999.0, help="Minimum color difference between the two sides of a ridge.")
    parser.add_argument("--ridge-color-range", type=float, default=999.0, help="Maximum color range for directional ridge seeds.")
    parser.add_argument("--aux-support-min", type=int, default=0, help="Minimum 3x3 support count for separator/ridge helper pixels.")
    parser.add_argument("--aux-support-max", type=int, default=9, help="Maximum 3x3 support count for separator/ridge helper pixels.")
    return parser.parse_args()


def resolve_images(raw_images: list[str]) -> list[Path]:
    if raw_images:
        return [Path(value).expanduser() for value in raw_images]
    return DEFAULT_DESKTOP_IMAGES


def compute_model_size(image_path: Path, long_side_mm: float) -> tuple[float, float]:
    with Image.open(image_path) as image:
        width_px, height_px = image.size
    long_side_px = max(width_px, height_px)
    scale = long_side_mm / float(long_side_px)
    return width_px * scale, height_px * scale


def build_tile(
    image_path: Path,
    long_side_mm: float,
    resolution_mm: float,
    config: engine.LeadDetectionConfig,
    font: ImageFont.ImageFont,
) -> Image.Image:
    width_mm, height_mm = compute_model_size(image_path, long_side_mm)
    grid_width = max(1, math.ceil(width_mm / resolution_mm))
    grid_height = max(1, math.ceil(height_mm / resolution_mm))

    rgb_image = engine.load_image_to_grid(image_path, grid_width, grid_height, blur_pixels=0.0)
    detected = engine.detect_image_lead_mask(rgb_image, config=config)
    stage_1 = Image.fromarray(rgb_image).convert("RGB")
    stage_2 = engine.mask_preview(detected).convert("RGB")

    preview_height = 250
    stage_1.thumbnail((250, preview_height), Image.Resampling.LANCZOS)
    stage_2.thumbnail((250, preview_height), Image.Resampling.NEAREST)

    padding = 16
    header_h = 58
    footer_h = 24
    gap = 12
    tile_width = stage_1.width + stage_2.width + gap + 2 * padding
    tile_height = max(stage_1.height, stage_2.height) + header_h + footer_h + 2 * padding

    tile = Image.new("RGB", (tile_width, tile_height), "#fbf7f0")
    draw = ImageDraw.Draw(tile)
    draw.rounded_rectangle((0, 0, tile_width - 1, tile_height - 1), radius=18, outline="#d0c3ae", width=2, fill="#fbf7f0")

    label = image_path.stem
    draw.text((padding, padding - 2), f"{label}  |  {engine.format_number(width_mm)} x {engine.format_number(height_mm)} mm", font=font, fill="#3f2d1d")
    draw.text((padding, padding + 24), f"Step 1: resized source    Step 2: raw detected lead", font=font, fill="#745f49")

    y = padding + header_h
    tile.paste(stage_1, (padding, y))
    tile.paste(stage_2, (padding + stage_1.width + gap, y))
    draw.text((padding, tile_height - padding - footer_h + 2), f"grid {grid_width}x{grid_height} @ {engine.format_number(resolution_mm)} mm", font=font, fill="#8a7763")
    return tile


def main() -> int:
    args = parse_args()
    images = resolve_images(args.images)
    missing = [path for path in images if not path.exists()]
    if missing:
        missing_text = "\n".join(str(path) for path in missing)
        raise SystemExit(f"Missing images:\n{missing_text}")

    config = engine.LeadDetectionConfig(
        strong_luma_cap=args.strong_luma_cap,
        weak_luma_cap=args.weak_luma_cap,
        strong_percentile=args.strong_percentile,
        weak_percentile=args.weak_percentile,
        strong_contrast_min=args.strong_contrast,
        weak_contrast_min=args.weak_contrast,
        strong_color_range_max=args.strong_color_range,
        weak_color_range_max=args.weak_color_range,
        grow_passes=args.grow_passes,
        blue_dominance_max=args.blue_dominance_max,
        red_dominance_max=args.red_dominance_max,
        neutral_edge_luma_cap=args.neutral_edge_luma_cap,
        neutral_edge_contrast_min=args.neutral_edge_contrast,
        neutral_edge_color_range_max=args.neutral_edge_color_range,
        separator_luma_cap=args.separator_luma_cap,
        separator_contrast_min=args.separator_contrast,
        separator_darkness_delta_min=args.separator_darkness_delta,
        separator_color_range_max=args.separator_color_range,
        ridge_luma_cap=args.ridge_luma_cap,
        ridge_darkness_delta_min=args.ridge_darkness_delta,
        ridge_side_color_diff_min=args.ridge_side_color_diff,
        ridge_color_range_max=args.ridge_color_range,
        auxiliary_support_min=args.aux_support_min,
        auxiliary_support_max=args.aux_support_max,
    )

    font = ImageFont.load_default()
    tiles = [build_tile(path, args.long_side_mm, args.resolution, config, font) for path in images]
    columns = 2
    rows = math.ceil(len(tiles) / columns)
    gutter = 18
    sheet_width = max(tile.width for tile in tiles) * columns + gutter * (columns + 1)
    sheet_height = max(tile.height for tile in tiles) * rows + gutter * (rows + 1)
    sheet = Image.new("RGB", (sheet_width, sheet_height), "#efe6d8")

    tile_width = max(tile.width for tile in tiles)
    tile_height = max(tile.height for tile in tiles)
    for index, tile in enumerate(tiles):
        row = index // columns
        column = index % columns
        x = gutter + column * (tile_width + gutter)
        y = gutter + row * (tile_height + gutter)
        sheet.paste(tile, (x, y))

    draw = ImageDraw.Draw(sheet)
    summary = (
        f"strong p{args.strong_percentile:g}/l{args.strong_luma_cap:g}/c{args.strong_contrast:g}/r{args.strong_color_range:g}   "
        f"weak p{args.weak_percentile:g}/l{args.weak_luma_cap:g}/c{args.weak_contrast:g}/r{args.weak_color_range:g}   "
        f"grow {args.grow_passes}   blue<= {args.blue_dominance_max:g}   red<= {args.red_dominance_max:g}   "
        f"edge l{args.neutral_edge_luma_cap:g}/c{args.neutral_edge_contrast:g}/r{args.neutral_edge_color_range:g}   "
        f"sep l{args.separator_luma_cap:g}/c{args.separator_contrast:g}/d{args.separator_darkness_delta:g}/r{args.separator_color_range:g}   "
        f"ridge l{args.ridge_luma_cap:g}/d{args.ridge_darkness_delta:g}/sd{args.ridge_side_color_diff:g}/r{args.ridge_color_range:g}   "
        f"aux {args.aux_support_min:g}-{args.aux_support_max:g}"
    )
    draw.text((gutter, sheet_height - gutter + 2 - 18), summary, font=font, fill="#6f5b46")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
