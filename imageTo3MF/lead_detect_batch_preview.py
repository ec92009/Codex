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
    font: ImageFont.ImageFont,
) -> Image.Image:
    width_mm, height_mm = compute_model_size(image_path, long_side_mm)
    grid_width = max(1, math.ceil(width_mm / resolution_mm))
    grid_height = max(1, math.ceil(height_mm / resolution_mm))

    rgb_image = engine.load_image_to_grid(image_path, grid_width, grid_height, blur_pixels=0.0)
    detected = engine.detect_image_lead_mask(rgb_image)
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

    font = ImageFont.load_default()
    tiles = [build_tile(path, args.long_side_mm, args.resolution, font) for path in images]
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

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
