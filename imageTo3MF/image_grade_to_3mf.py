#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET
from xml.sax.saxutils import quoteattr

import lib3mf
import numpy as np
from PIL import Image, ImageFilter, ImageOps


DEFAULT_NUM_NUANCES = 10
DEFAULT_RESOLUTION_MM = 0.5
DEFAULT_LEAD_THICKNESS_MM = 0.25
DEFAULT_WIDTH_MM = 100.0
DEFAULT_HEIGHT_MM = 100.0
DEFAULT_THICKNESS_MM = 1.0
DEFAULT_LEAD_CAP_HEIGHT_MM = 0.3
DEFAULT_BLUR_MM = 0.0
DEFAULT_PLATE_WIDTH_MM = 270.0
DEFAULT_PLATE_HEIGHT_MM = 270.0
DEFAULT_SLICER_APP = "Snapmaker Orca"
SNAPMAKER_PROJECT_MARKER = "Metadata/model_settings.config"
SNAPMAKER_PROJECT_SETTINGS = "Metadata/project_settings.config"
SNAPMAKER_CUSTOM_GCODE_PER_LAYER = "Metadata/custom_gcode_per_layer.xml"
LEAD_OBJECT_NAME = "Lead"
ASSEMBLY_OBJECT_NAME = "Assembly"
LEAD_FILAMENT_SLOT = "5"
DEFAULT_BASE_FILAMENT_HEX = ["#00FFFF", "#FF00FF", "#FFFF00", "#FFFFFF", "#000000"]
DEFAULT_BASE_THICKNESS_LAYERS = 4
BASE_SLOT_SEQUENCE = ["1", "2", "3", "4"]
BASE_SLOT_RGB = {
    "1": (0, 255, 255),
    "2": (255, 0, 255),
    "3": (255, 255, 0),
    "4": (255, 255, 255),
    LEAD_FILAMENT_SLOT: (0, 0, 0),
}
BASE_SLOT_LABEL = {
    "1": "C",
    "2": "M",
    "3": "Y",
    "4": "W",
    LEAD_FILAMENT_SLOT: "K",
}
GENERIC_STEM_PATTERN = re.compile(
    r"^(image\d*|img[_-]?\d*|photo[_-]?\d*|picture[_-]?\d*|screenshot.*|scan[_-]?\d*|pasted.*)$",
    re.IGNORECASE,
)
GENERIC_VISION_LABELS = {
    "animal",
    "mammal",
    "vertebrate",
    "fauna",
    "pet",
    "art",
    "illustration",
}
VISION_SUBJECT_ALIASES = {
    "cat": "cat",
    "kitten": "cat",
    "feline": "cat",
    "tabby": "cat",
    "tiger": "cat",
    "dog": "dog",
    "puppy": "dog",
    "canine": "dog",
    "spaniel": "dog",
    "bird": "bird",
    "angel": "angel",
    "woman": "portrait",
    "girl": "portrait",
    "person": "portrait",
    "flower": "flower",
    "lily": "flower",
    "butterfly": "butterfly",
    "leaf": "leaf",
    "wallpaper": "abstract",
    "texture": "abstract",
    "pattern": "abstract",
    "abstract": "abstract",
}


@dataclass
class MeshObjectData:
    name: str
    color: Tuple[int, int, int]
    vertices: List[Tuple[float, float, float]]
    triangles: List[Tuple[int, int, int]]
    preferred_slot: Optional[str] = None


def parse_mm_value(raw: str) -> float:
    value = raw.strip().lower()
    if value.endswith("mm"):
        value = value[:-2].strip()
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def parse_mm_pair(raw: str) -> Tuple[float, float]:
    value = raw.strip().lower().replace(" ", "")
    parts = re.split(r"[x,]", value)
    if len(parts) != 2 or not all(parts):
        raise argparse.ArgumentTypeError("value must look like WIDTHxHEIGHT, for example 270x270")
    return tuple(parse_mm_value(part) for part in parts)  # type: ignore[return-value]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Turn an image into a Snapmaker-Orca-ready 3MF with 10 graded CMYW "
            "nuances, a black lead cap on slot 5, and an automatic pause before "
            "the lead layer."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    common = parser.add_argument_group("Common options")
    advanced = parser.add_argument_group("Advanced options")

    parser.add_argument(
        "input_image",
        nargs="?",
        help="Path to the source image. If omitted, a macOS file picker is used.",
    )
    common.add_argument(
        "-o",
        "--output",
        help="Output .3mf path.",
    )
    advanced.add_argument(
        "--preview",
        help="Optional preview PNG path.",
    )
    common.add_argument(
        "--description",
        help=(
            "Short name used in default output file names, for example "
            "'cartoon spaniel'."
        ),
    )
    advanced.add_argument(
        "--num-nuances",
        type=int,
        default=DEFAULT_NUM_NUANCES,
        help="Number of color nuance zones to produce.",
    )
    common.add_argument(
        "--thickness",
        type=parse_mm_value,
        default=DEFAULT_THICKNESS_MM,
        help="Base image thickness in mm. Accepts values like 3 or 3mm.",
    )
    common.add_argument(
        "--width",
        type=parse_mm_value,
        default=DEFAULT_WIDTH_MM,
        help="Model width in mm. Accepts values like 100 or 100mm.",
    )
    common.add_argument(
        "--height",
        type=parse_mm_value,
        default=DEFAULT_HEIGHT_MM,
        help="Model height in mm. Accepts values like 100 or 100mm.",
    )
    common.add_argument(
        "--resolution",
        type=parse_mm_value,
        default=DEFAULT_RESOLUTION_MM,
        help="Target XY cell size in mm. Accepts values like 0.25 or 0.25mm.",
    )
    common.add_argument(
        "--lead-height",
        "--lead-cap-height",
        dest="lead_cap_height",
        type=parse_mm_value,
        default=DEFAULT_LEAD_CAP_HEIGHT_MM,
        help="Lead overlay height in mm printed on top of the image body.",
    )
    advanced.add_argument(
        "--blur",
        type=parse_mm_value,
        default=DEFAULT_BLUR_MM,
        help="Gaussian blur radius in mm before color quantization.",
    )
    common.add_argument(
        "--plate-size",
        default=f"{format_number(DEFAULT_PLATE_WIDTH_MM)}x{format_number(DEFAULT_PLATE_HEIGHT_MM)}",
        help="Printer plate size as WIDTHxHEIGHT in mm, used to center the exported objects.",
    )
    common.add_argument(
        "--lead-thickness",
        dest="lead_thickness",
        type=parse_mm_value,
        default=DEFAULT_LEAD_THICKNESS_MM,
        help="Black separator thickness in mm.",
    )
    advanced.add_argument(
        "--plate-width",
        dest="plate_width_legacy",
        type=parse_mm_value,
        help=argparse.SUPPRESS,
    )
    advanced.add_argument(
        "--plate-height",
        dest="plate_height_legacy",
        type=parse_mm_value,
        help=argparse.SUPPRESS,
    )
    advanced.add_argument(
        "--line-width-mm",
        dest="lead_thickness",
        type=parse_mm_value,
        help=argparse.SUPPRESS,
    )
    advanced.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Random seed for color clustering.",
    )
    advanced.add_argument(
        "--smooth-passes",
        type=int,
        default=2,
        help="Label majority-filter passes before boundary extraction.",
    )
    common.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the generated 3MF in Snapmaker Orca.",
    )
    advanced.add_argument(
        "--template",
        "--snapmaker-template",
        dest="snapmaker_template",
        help=(
            "Path to a Snapmaker-Orca-style 3MF project whose color and printer "
            "metadata should be reused."
        ),
    )
    args = parser.parse_args()
    args.plate_width, args.plate_height = parse_mm_pair(args.plate_size)
    if args.plate_width_legacy is not None:
        args.plate_width = args.plate_width_legacy
    if args.plate_height_legacy is not None:
        args.plate_height = args.plate_height_legacy
    return args


def pick_image_with_tk() -> Optional[Path]:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.update()
        selected = filedialog.askopenfilename(
            title="Choose the source image",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
    except Exception:
        return None

    if not selected:
        return None
    return Path(selected).expanduser().resolve()


def resolve_input_path(value: Optional[str]) -> Path:
    if value:
        path = Path(value).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Input image not found: {path}")
        return path

    picked = pick_image_with_tk()
    if picked is None:
        raise FileNotFoundError(
            "No input image path was given and no file was selected."
        )
    return picked


def sanitize_filename_bit(value: str) -> str:
    sanitized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    sanitized = sanitized.strip("_")
    return sanitized[:48].rstrip("_")


def is_generic_stem(stem: str) -> bool:
    return bool(GENERIC_STEM_PATTERN.match(stem.strip()))


def dominant_color_name(path: Path) -> Optional[str]:
    named_colors = {
        "red": (220, 50, 47),
        "orange": (243, 119, 32),
        "yellow": (250, 220, 40),
        "green": (46, 204, 113),
        "cyan": (0, 200, 220),
        "blue": (52, 120, 246),
        "purple": (155, 89, 182),
        "pink": (241, 127, 180),
        "brown": (150, 96, 52),
        "gold": (212, 175, 55),
        "black": (25, 25, 25),
        "gray": (150, 150, 150),
        "white": (245, 245, 245),
    }
    with Image.open(path) as image:
        rgb = image.convert("RGB").resize((96, 96), Image.Resampling.LANCZOS)
        quantized = rgb.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
        palette = quantized.getpalette()
        colors = sorted(quantized.getcolors() or [], reverse=True)

    best_rgb: Optional[Tuple[int, int, int]] = None
    fallback_rgb: Optional[Tuple[int, int, int]] = None
    for _count, palette_index in colors:
        base = palette_index * 3
        sample = tuple(palette[base:base + 3])
        if len(sample) != 3:
            continue
        r, g, b = sample
        if fallback_rgb is None:
            fallback_rgb = (r, g, b)
        if max(r, g, b) > 245 and min(r, g, b) > 230:
            continue
        if max(r, g, b) - min(r, g, b) < 18 and max(r, g, b) > 210:
            continue
        best_rgb = (r, g, b)
        break

    target = best_rgb or fallback_rgb
    if target is None:
        return None
    return min(
        named_colors.items(),
        key=lambda item: sum((target[i] - item[1][i]) ** 2 for i in range(3)),
    )[0]


def classify_image_labels_mac(path: Path) -> List[str]:
    if sys.platform != "darwin":
        return []

    swift_code = r"""
import Foundation
import Vision

let imagePath = CommandLine.arguments[1]
let url = URL(fileURLWithPath: imagePath)
let request = VNClassifyImageRequest()
let handler = VNImageRequestHandler(url: url)
try handler.perform([request])
let results = request.results ?? []
for observation in results.prefix(12) {
    print("\(observation.identifier)|\(observation.confidence)")
}
"""
    try:
        result = subprocess.run(
            ["swift", "-e", swift_code, str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    labels: List[str] = []
    for line in result.stdout.splitlines():
        if "|" not in line:
            continue
        identifier, _confidence = line.split("|", 1)
        label = sanitize_filename_bit(identifier)
        if label:
            labels.append(label)
    return labels


def infer_subject_name(path: Path) -> Optional[str]:
    labels = classify_image_labels_mac(path)
    for label in labels:
        if label in VISION_SUBJECT_ALIASES:
            subject = VISION_SUBJECT_ALIASES[label]
            if subject not in GENERIC_VISION_LABELS:
                return subject
        if label not in GENERIC_VISION_LABELS:
            return label
    return None


def infer_description_slug(path: Path) -> Optional[str]:
    color = dominant_color_name(path)
    subject = infer_subject_name(path)
    tokens: List[str] = []
    if color and color not in {"white", "gray", "black"}:
        tokens.append(color)
    if subject:
        tokens.append(subject)
    elif color:
        tokens.append(color)
    if not tokens:
        return None
    return sanitize_filename_bit("_".join(tokens))


def default_output_paths(
    input_path: Path,
    output_arg: Optional[str],
    preview_arg: Optional[str],
    description_arg: Optional[str],
) -> Tuple[Path, Path]:
    out_dir = Path("out").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    description_bit = ""
    if description_arg:
        sanitized = sanitize_filename_bit(description_arg)
        if sanitized:
            description_bit = sanitized
    base_name = stem
    if description_bit:
        base_name = description_bit if is_generic_stem(stem) else f"{stem}_{description_bit}"
    output_path = (
        Path(output_arg).expanduser().resolve()
        if output_arg
        else out_dir / f"{base_name}_graded.3mf"
    )
    preview_path = (
        Path(preview_arg).expanduser().resolve()
        if preview_arg
        else out_dir / f"{base_name}_preview.png"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path, preview_path


def load_image_to_grid(
    path: Path,
    grid_width: int,
    grid_height: int,
    blur_pixels: float = 0.0,
) -> np.ndarray:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        fitted = ImageOps.fit(
            rgb,
            (grid_width, grid_height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        if blur_pixels > 0:
            fitted = fitted.filter(ImageFilter.GaussianBlur(radius=blur_pixels))
    return np.asarray(fitted, dtype=np.uint8)


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    srgb = rgb.astype(np.float32) / 255.0
    linear = np.where(
        srgb <= 0.04045,
        srgb / 12.92,
        ((srgb + 0.055) / 1.055) ** 2.4,
    )

    xyz = np.empty_like(linear, dtype=np.float32)
    xyz[..., 0] = (
        0.4124564 * linear[..., 0]
        + 0.3575761 * linear[..., 1]
        + 0.1804375 * linear[..., 2]
    )
    xyz[..., 1] = (
        0.2126729 * linear[..., 0]
        + 0.7151522 * linear[..., 1]
        + 0.0721750 * linear[..., 2]
    )
    xyz[..., 2] = (
        0.0193339 * linear[..., 0]
        + 0.1191920 * linear[..., 1]
        + 0.9503041 * linear[..., 2]
    )

    white = np.array([0.95047, 1.0, 1.08883], dtype=np.float32)
    scaled = xyz / white
    epsilon = 216 / 24389
    kappa = 24389 / 27

    f = np.where(
        scaled > epsilon,
        np.cbrt(scaled),
        (kappa * scaled + 16) / 116,
    )

    lab = np.empty_like(xyz, dtype=np.float32)
    lab[..., 0] = 116 * f[..., 1] - 16
    lab[..., 1] = 500 * (f[..., 0] - f[..., 1])
    lab[..., 2] = 200 * (f[..., 1] - f[..., 2])
    return lab


def kmeans_pp(data: np.ndarray, clusters: int, rng: np.random.Generator) -> np.ndarray:
    centers = np.empty((clusters, data.shape[1]), dtype=np.float32)
    first_index = int(rng.integers(0, len(data)))
    centers[0] = data[first_index]
    closest_sq = np.sum((data - centers[0]) ** 2, axis=1)

    for index in range(1, clusters):
        total = float(closest_sq.sum())
        if total <= 1e-12:
            centers[index:] = data[int(rng.integers(0, len(data)))]
            break
        probabilities = closest_sq / total
        chosen = int(rng.choice(len(data), p=probabilities))
        centers[index] = data[chosen]
        new_dist_sq = np.sum((data - centers[index]) ** 2, axis=1)
        closest_sq = np.minimum(closest_sq, new_dist_sq)
    return centers


def kmeans(data: np.ndarray, clusters: int, seed: int, iterations: int = 25) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    centers = kmeans_pp(data, clusters, rng)

    for _ in range(iterations):
        distances = np.sum((data[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        labels = np.argmin(distances, axis=1)

        new_centers = centers.copy()
        for cluster_index in range(clusters):
            members = data[labels == cluster_index]
            if len(members) == 0:
                new_centers[cluster_index] = data[int(rng.integers(0, len(data)))]
            else:
                new_centers[cluster_index] = members.mean(axis=0)
        if np.allclose(new_centers, centers, atol=1e-3):
            centers = new_centers
            break
        centers = new_centers

    distances = np.sum((data[:, None, :] - centers[None, :, :]) ** 2, axis=2)
    labels = np.argmin(distances, axis=1)
    return labels, centers


def reorder_by_lightness(labels: np.ndarray, lab_centers: np.ndarray, rgb_pixels: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    order = np.argsort(lab_centers[:, 0])
    remap = np.empty(len(order), dtype=np.int32)
    remap[order] = np.arange(len(order))
    sorted_labels = remap[labels]
    sorted_rgb = np.zeros((len(order), 3), dtype=np.uint8)
    sorted_lab = lab_centers[order]

    for new_index, old_index in enumerate(order):
        members = rgb_pixels[labels == old_index]
        if len(members) == 0:
            rgb = np.clip(sorted_lab[new_index, 0], 0, 255)
            sorted_rgb[new_index] = [rgb, rgb, rgb]
        else:
            sorted_rgb[new_index] = np.round(members.mean(axis=0)).astype(np.uint8)
    return sorted_labels, sorted_lab, sorted_rgb


def majority_smooth(labels: np.ndarray, num_classes: int, passes: int) -> np.ndarray:
    if passes <= 0:
        return labels

    result = labels.copy()
    height, width = result.shape
    for _ in range(passes):
        counts = np.zeros((num_classes, height, width), dtype=np.uint16)
        padded = np.pad(result, 1, mode="edge")
        for dy in range(3):
            for dx in range(3):
                neighborhood = padded[dy : dy + height, dx : dx + width]
                for class_index in range(num_classes):
                    counts[class_index] += (neighborhood == class_index)
        result = np.argmax(counts, axis=0).astype(np.int32)
    return result


def boundary_mask(labels: np.ndarray, radius_pixels: int) -> np.ndarray:
    diff = np.zeros_like(labels, dtype=bool)
    diff[:-1, :] |= labels[:-1, :] != labels[1:, :]
    diff[1:, :] |= labels[:-1, :] != labels[1:, :]
    diff[:, :-1] |= labels[:, :-1] != labels[:, 1:]
    diff[:, 1:] |= labels[:, :-1] != labels[:, 1:]

    if radius_pixels <= 0:
        return diff

    dilated = diff
    height, width = diff.shape
    for _ in range(radius_pixels):
        padded = np.pad(dilated, 1, mode="constant")
        grown = np.zeros_like(dilated)
        for dy in range(3):
            for dx in range(3):
                grown |= padded[dy : dy + height, dx : dx + width]
        dilated = grown
    return dilated


def rgb_to_lab_color(color: Tuple[int, int, int]) -> np.ndarray:
    rgb = np.asarray([[list(color)]], dtype=np.uint8)
    return srgb_to_lab(rgb)[0, 0]


def enumerate_layer_count_vectors(total_layers: int, buckets: int) -> List[Tuple[int, ...]]:
    if buckets == 1:
        return [(total_layers,)]
    vectors: List[Tuple[int, ...]] = []
    for first in range(total_layers + 1):
        for rest in enumerate_layer_count_vectors(total_layers - first, buckets - 1):
            vectors.append((first,) + rest)
    return vectors


def expand_layer_slots(counts: Tuple[int, int, int, int]) -> List[str]:
    slots: List[str] = []
    for slot, count in zip(BASE_SLOT_SEQUENCE, counts):
        slots.extend([slot] * count)
    return slots


def mixed_rgb_from_slots(slots: Sequence[str]) -> Tuple[int, int, int]:
    colors = np.asarray([BASE_SLOT_RGB[slot] for slot in slots], dtype=np.float32)
    mixed = np.round(colors.mean(axis=0)).astype(np.uint8)
    return int(mixed[0]), int(mixed[1]), int(mixed[2])


def build_palette_recipes(
    region_colors: np.ndarray,
    layer_count: int,
) -> List[Tuple[List[str], Tuple[int, int, int]]]:
    candidates: List[Tuple[List[str], Tuple[int, int, int], np.ndarray]] = []
    for counts in enumerate_layer_count_vectors(layer_count, 4):
        slots = expand_layer_slots(counts)
        mixed_rgb = mixed_rgb_from_slots(slots)
        mixed_lab = rgb_to_lab_color(mixed_rgb)
        candidates.append((slots, mixed_rgb, mixed_lab))

    used_indices: set[int] = set()
    assignments: List[Tuple[List[str], Tuple[int, int, int]]] = []
    for region_color in region_colors:
        target_lab = rgb_to_lab_color((int(region_color[0]), int(region_color[1]), int(region_color[2])))
        best_index = None
        best_distance = None
        for candidate_index, (_slots, _rgb, candidate_lab) in enumerate(candidates):
            if candidate_index in used_indices:
                continue
            distance = float(np.sum((target_lab - candidate_lab) ** 2))
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_index = candidate_index
        if best_index is None:
            raise RuntimeError("Failed to assign a unique CMYW palette recipe")
        used_indices.add(best_index)
        slots, mixed_rgb, _lab = candidates[best_index]
        assignments.append((slots, mixed_rgb))
    return assignments


def build_preview(labels: np.ndarray, mean_colors: np.ndarray, lines: np.ndarray) -> Image.Image:
    preview = mean_colors[labels].astype(np.uint8)
    preview[lines] = np.array([0, 0, 0], dtype=np.uint8)
    return Image.fromarray(preview)


def make_position(x: float, y: float, z: float) -> lib3mf.Position:
    position = lib3mf.Position()
    position.Coordinates[:] = [x, y, z]
    return position


def make_triangle(a: int, b: int, c: int) -> lib3mf.Triangle:
    triangle = lib3mf.Triangle()
    triangle.Indices[:] = [a, b, c]
    return triangle


def identity_transform() -> lib3mf.Transform:
    transform = lib3mf.Transform()
    transform.Fields[0][:] = [1.0, 0.0, 0.0]
    transform.Fields[1][:] = [0.0, 1.0, 0.0]
    transform.Fields[2][:] = [0.0, 0.0, 1.0]
    transform.Fields[3][:] = [0.0, 0.0, 0.0]
    return transform


def mesh_from_mask(
    mask: np.ndarray,
    width_mm: float,
    height_mm: float,
    z_bottom_mm: float,
    z_top_mm: float,
) -> Tuple[List[Tuple[float, float, float]], List[Tuple[int, int, int]]]:
    height, width = mask.shape
    pixel_w = width_mm / width
    pixel_h = height_mm / height

    vertices: List[Tuple[float, float, float]] = []
    triangles: List[Tuple[int, int, int]] = []
    vertex_index: Dict[Tuple[int, int, int], int] = {}

    def get_vertex(gx: int, gy: int, gz: int) -> int:
        key = (gx, gy, gz)
        existing = vertex_index.get(key)
        if existing is not None:
            return existing

        x = gx * pixel_w
        y = height_mm - gy * pixel_h
        z = z_top_mm if gz else z_bottom_mm
        vertex_index[key] = len(vertices)
        vertices.append((x, y, z))
        return vertex_index[key]

    for y in range(height):
        for x in range(width):
            if not mask[y, x]:
                continue

            v000 = get_vertex(x, y + 1, 0)
            v100 = get_vertex(x + 1, y + 1, 0)
            v110 = get_vertex(x + 1, y, 0)
            v010 = get_vertex(x, y, 0)
            v001 = get_vertex(x, y + 1, 1)
            v101 = get_vertex(x + 1, y + 1, 1)
            v111 = get_vertex(x + 1, y, 1)
            v011 = get_vertex(x, y, 1)

            triangles.append((v001, v101, v111))
            triangles.append((v001, v111, v011))
            triangles.append((v000, v110, v100))
            triangles.append((v000, v010, v110))

            if x == 0 or not mask[y, x - 1]:
                triangles.append((v000, v001, v011))
                triangles.append((v000, v011, v010))
            if x == width - 1 or not mask[y, x + 1]:
                triangles.append((v100, v110, v111))
                triangles.append((v100, v111, v101))
            if y == 0 or not mask[y - 1, x]:
                triangles.append((v010, v011, v111))
                triangles.append((v010, v111, v110))
            if y == height - 1 or not mask[y + 1, x]:
                triangles.append((v000, v100, v101))
                triangles.append((v000, v101, v001))

    return vertices, triangles


def convert_mesh_to_lib3mf(
    vertices: Sequence[Tuple[float, float, float]],
    triangles: Sequence[Tuple[int, int, int]],
) -> Tuple[List[lib3mf.Position], List[lib3mf.Triangle]]:
    lib_vertices = [make_position(x, y, z) for x, y, z in vertices]
    lib_triangles = [make_triangle(a, b, c) for a, b, c in triangles]
    return lib_vertices, lib_triangles


def add_colored_mesh_object(
    model: lib3mf.Model,
    color_group: lib3mf.ColorGroup,
    mesh_object: MeshObjectData,
) -> Optional[lib3mf.MeshObject]:
    if not mesh_object.triangles:
        return None

    vertices, triangles = convert_mesh_to_lib3mf(mesh_object.vertices, mesh_object.triangles)
    mesh = model.AddMeshObject()
    mesh.SetName(mesh_object.name)
    mesh.SetGeometry(vertices, triangles)
    color_index = color_group.AddColor(
        lib3mf.Color(int(mesh_object.color[0]), int(mesh_object.color[1]), int(mesh_object.color[2]), 255)
    )
    mesh.SetObjectLevelProperty(color_group.GetResourceID(), color_index)
    return mesh


def build_mesh_objects(
    region_masks: List[np.ndarray],
    palette_recipes: List[Tuple[List[str], Tuple[int, int, int]]],
    lines_mask: np.ndarray,
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
    lead_cap_height_mm: float,
) -> List[MeshObjectData]:
    objects: List[MeshObjectData] = []

    if lead_cap_height_mm > 0:
        line_vertices, line_triangles = mesh_from_mask(
            lines_mask,
            width_mm=width_mm,
            height_mm=height_mm,
            z_bottom_mm=thickness_mm,
            z_top_mm=thickness_mm + lead_cap_height_mm,
        )
    else:
        line_vertices, line_triangles = [], []

    if line_triangles:
        objects.append(
            MeshObjectData(
                name=LEAD_OBJECT_NAME,
                color=(0, 0, 0),
                vertices=line_vertices,
                triangles=line_triangles,
                preferred_slot=LEAD_FILAMENT_SLOT,
            )
        )

    slice_height_mm = thickness_mm / DEFAULT_BASE_THICKNESS_LAYERS
    for nuance_index, (mask, recipe) in enumerate(zip(region_masks, palette_recipes), start=1):
        layer_slots, mixed_color = recipe
        for layer_index, slot in enumerate(layer_slots, start=1):
            z_bottom_mm = slice_height_mm * (layer_index - 1)
            z_top_mm = slice_height_mm * layer_index
            vertices, triangles = mesh_from_mask(
                mask,
                width_mm=width_mm,
                height_mm=height_mm,
                z_bottom_mm=z_bottom_mm,
                z_top_mm=z_top_mm,
            )
            if not triangles:
                continue
            objects.append(
                MeshObjectData(
                    name=f"Color {nuance_index + 1} - Nuance {nuance_index:02d} - {BASE_SLOT_LABEL[slot]}{layer_index}",
                    color=BASE_SLOT_RGB[slot],
                    vertices=vertices,
                    triangles=triangles,
                    preferred_slot=slot,
                )
            )
    return objects


def write_plain_3mf(output_path: Path, mesh_objects: Sequence[MeshObjectData]) -> List[str]:
    wrapper = lib3mf.get_wrapper()
    model = wrapper.CreateModel()
    model.SetUnit(lib3mf.ModelUnit.MilliMeter)
    model.SetLanguage("en-US")
    color_group = model.AddColorGroup()

    object_names: List[str] = []

    for mesh_object in mesh_objects:
        mesh = add_colored_mesh_object(model=model, color_group=color_group, mesh_object=mesh_object)
        if mesh is None:
            continue
        model.AddBuildItem(mesh, identity_transform())
        object_names.append(mesh_object.name)

    writer = model.QueryWriter("3mf")
    writer.WriteToFile(str(output_path))
    return object_names


def find_snapmaker_template(explicit_value: Optional[str], output_path: Path) -> Optional[Path]:
    candidates: List[Path] = []
    if explicit_value:
        candidates.append(Path(explicit_value).expanduser().resolve())
    for base in [output_path.parent, Path.cwd()]:
        if not base.exists():
            continue
        candidates.extend(sorted(base.glob("*.3mf"), key=lambda item: item.stat().st_mtime, reverse=True))

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or candidate == output_path or not candidate.exists():
            continue
        seen.add(candidate)
        try:
            with zipfile.ZipFile(candidate) as zf:
                if SNAPMAKER_PROJECT_MARKER in zf.namelist():
                    return candidate
        except zipfile.BadZipFile:
            continue
    return None


def format_number(value: float) -> str:
    rounded = round(float(value), 6)
    if abs(rounded - int(rounded)) < 1e-6:
        return str(int(rounded))
    return f"{rounded:.6f}".rstrip("0").rstrip(".")


def shifted_vertices(
    vertices: Sequence[Tuple[float, float, float]],
    dx: float,
    dy: float,
    dz: float,
) -> List[Tuple[float, float, float]]:
    return [(x + dx, y + dy, z + dz) for x, y, z in vertices]


def mesh_center_xy(vertices: Sequence[Tuple[float, float, float]]) -> Tuple[float, float]:
    xs = [vertex[0] for vertex in vertices]
    ys = [vertex[1] for vertex in vertices]
    return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)


def mesh_center_xyz(vertices: Sequence[Tuple[float, float, float]]) -> Tuple[float, float, float]:
    xs = [vertex[0] for vertex in vertices]
    ys = [vertex[1] for vertex in vertices]
    zs = [vertex[2] for vertex in vertices]
    return (
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        (min(zs) + max(zs)) / 2.0,
    )


def parse_template_extruders(template_path: Path) -> Dict[str, str]:
    with zipfile.ZipFile(template_path) as zf:
        raw = zf.read(SNAPMAKER_PROJECT_MARKER).decode("utf-8", errors="ignore")

    assignments: Dict[str, str] = {}
    root = ET.fromstring(raw)
    for object_node in root.findall("object"):
        name = None
        extruder = None
        for metadata_node in object_node.findall("metadata"):
            key = metadata_node.attrib.get("key")
            value = metadata_node.attrib.get("value")
            if key == "name":
                name = value
            elif key == "extruder":
                extruder = value
        if name and extruder:
            assignments[name] = extruder

        for part_node in object_node.findall("part"):
            part_name = None
            part_extruder = None
            for metadata_node in part_node.findall("metadata"):
                key = metadata_node.attrib.get("key")
                value = metadata_node.attrib.get("value")
                if key == "name":
                    part_name = value
                elif key == "extruder":
                    part_extruder = value
            if part_name and part_extruder:
                assignments[part_name] = part_extruder
    return assignments


def build_color_slot_assignments(
    mesh_objects: Sequence[MeshObjectData],
    template_assignments: Dict[str, str],
) -> Dict[str, str]:
    assignments: Dict[str, str] = {}
    fallback_slots = iter(["1", "2", "3", "4", "6", "7", "8", "9", "10", "11", "12", "13"])
    for mesh_object in mesh_objects:
        if mesh_object.preferred_slot is not None:
            assignments[mesh_object.name] = mesh_object.preferred_slot
            continue
        if mesh_object.name == LEAD_OBJECT_NAME:
            assignments[mesh_object.name] = LEAD_FILAMENT_SLOT
            continue

        template_value = template_assignments.get(mesh_object.name)
        if template_value is not None and template_value != LEAD_FILAMENT_SLOT:
            assignments[mesh_object.name] = template_value
        else:
            assignments[mesh_object.name] = next(fallback_slots)
    return assignments


def child_model_filename(index: int, name: str) -> str:
    return f"3D/Objects/{name}_{index}.model"


def assembly_model_filename(mesh_objects: Sequence[MeshObjectData]) -> str:
    return f"3D/Objects/{ASSEMBLY_OBJECT_NAME}_{len(mesh_objects) + 1}.model"


def build_snapmaker_child_model(mesh_object: MeshObjectData, object_id: int = 1) -> str:
    vertices_xml = "\n".join(
        f'     <vertex x="{format_number(x)}" y="{format_number(y)}" z="{format_number(z)}"/>'
        for x, y, z in mesh_object.vertices
    )
    triangles_xml = "\n".join(
        f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>'
        for a, b, c in mesh_object.triangles
    )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
        'requiredextensions="p">\n'
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
        ' <resources>\n'
        f'  <object id="{object_id}" p:UUID="{uuid.uuid4()}" type="model">\n'
        '   <mesh>\n'
        '    <vertices>\n'
        f'{vertices_xml}\n'
        '    </vertices>\n'
        '    <triangles>\n'
        f'{triangles_xml}\n'
        '    </triangles>\n'
        '   </mesh>\n'
        '  </object>\n'
        ' </resources>\n'
        f' <build p:UUID="{uuid.uuid4()}">\n'
        f'  <item objectid="{object_id}" printable="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n'
        ' </build>\n'
        '</model>\n'
    )


def build_snapmaker_assembly_model(mesh_objects: Sequence[MeshObjectData]) -> str:
    object_chunks: List[str] = []
    for index, mesh_object in enumerate(mesh_objects, start=1):
        vertices_xml = "\n".join(
            f'     <vertex x="{format_number(x)}" y="{format_number(y)}" z="{format_number(z)}"/>'
            for x, y, z in mesh_object.vertices
        )
        triangles_xml = "\n".join(
            f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>'
            for a, b, c in mesh_object.triangles
        )
        object_chunks.append(
            f'  <object id="{index}" p:UUID="{uuid.uuid4()}" type="model">\n'
            '   <mesh>\n'
            '    <vertices>\n'
            f'{vertices_xml}\n'
            '    </vertices>\n'
            '    <triangles>\n'
            f'{triangles_xml}\n'
            '    </triangles>\n'
            '   </mesh>\n'
            '  </object>'
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
        'requiredextensions="p">\n'
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
        ' <resources>\n'
        f'{"\n".join(object_chunks)}\n'
        ' </resources>\n'
        f' <build p:UUID="{uuid.uuid4()}">\n'
        f'  <item objectid="1" printable="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n'
        ' </build>\n'
        '</model>\n'
    )


def build_snapmaker_root_model(
    mesh_objects: Sequence[MeshObjectData],
    plate_width_mm: float,
    plate_height_mm: float,
    thickness_mm: float,
) -> str:
    assembly_object_id = len(mesh_objects) + 1
    assembly_path = "/" + assembly_model_filename(mesh_objects)
    build_transform = (
        f'1 0 0 0 1 0 0 0 1 '
        f'{format_number(plate_width_mm / 2.0)} {format_number(plate_height_mm / 2.0)} {format_number(thickness_mm / 2.0)}'
    )
    component_lines = []
    for index, _mesh_object in enumerate(mesh_objects, start=1):
        component_lines.append(
            f'    <component p:path={quoteattr(assembly_path)} objectid="{index}" '
            f'p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
        'requiredextensions="p">\n'
        ' <metadata name="Application">BambuStudio-2.2.4</metadata>\n'
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
        ' <metadata name="Title"></metadata>\n'
        ' <resources>\n'
        f'  <object id="{assembly_object_id}" p:UUID="{uuid.uuid4()}" type="model">\n'
        '   <components>\n'
        f'{"\n".join(component_lines)}\n'
        '   </components>\n'
        '  </object>\n'
        ' </resources>\n'
        f' <build p:UUID="{uuid.uuid4()}">\n'
        f'  <item objectid="{assembly_object_id}" p:UUID="{uuid.uuid4()}" transform="{build_transform}" printable="1"/>\n'
        ' </build>\n'
        '</model>\n'
    )


def build_snapmaker_relationships(mesh_objects: Sequence[MeshObjectData]) -> str:
    relationships = (
        f' <Relationship Target={quoteattr("/" + assembly_model_filename(mesh_objects))} '
        'Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        f'{relationships}\n'
        '</Relationships>\n'
    )


def build_model_settings(
    mesh_objects: Sequence[MeshObjectData],
    extruder_assignments: Dict[str, str],
    output_path: Path,
    plate_width_mm: float,
    plate_height_mm: float,
    thickness_mm: float,
) -> str:
    assembly_object_id = len(mesh_objects) + 1
    build_transform = (
        f'1 0 0 0 1 0 0 0 1 '
        f'{format_number(plate_width_mm / 2.0)} {format_number(plate_height_mm / 2.0)} {format_number(thickness_mm / 2.0)}'
    )
    part_chunks: List[str] = []
    for index, mesh_object in enumerate(mesh_objects, start=1):
        center_x, center_y, center_z = mesh_center_xyz(mesh_object.vertices)
        extruder = extruder_assignments.get(mesh_object.name, str(index))
        part_chunks.append(
            f'    <part id="{index}" subtype="normal_part">\n'
            f'      <metadata key="name" value={quoteattr(mesh_object.name)}/>\n'
            '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
            f'      <metadata key="source_file" value={quoteattr(str(output_path))}/>\n'
            f'      <metadata key="source_object_id" value={quoteattr(str(index - 1))}/>\n'
            '      <metadata key="source_volume_id" value="0"/>\n'
            f'      <metadata key="source_offset_x" value={quoteattr(format_number(center_x))}/>\n'
            f'      <metadata key="source_offset_y" value={quoteattr(format_number(center_y))}/>\n'
            f'      <metadata key="source_offset_z" value={quoteattr(format_number(center_z))}/>\n'
            f'      <metadata key="extruder" value={quoteattr(extruder)}/>\n'
            '      <mesh_stat edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n'
            '    </part>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<config>\n'
        f'  <object id="{assembly_object_id}">\n'
        f'    <metadata key="name" value={quoteattr(ASSEMBLY_OBJECT_NAME)}/>\n'
        '    <metadata key="extruder" value="1"/>\n'
        f'{"\n".join(part_chunks)}\n'
        '  </object>\n'
        '  <plate>\n'
        '    <metadata key="plater_id" value="1"/>\n'
        '    <metadata key="plater_name" value=""/>\n'
        '    <metadata key="locked" value="false"/>\n'
        '    <metadata key="filament_map_mode" value="Auto For Flush"/>\n'
        f'    <metadata key="filament_maps" value={quoteattr(" ".join(["1"] * len(DEFAULT_BASE_FILAMENT_HEX)))}/>\n'
        '    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>\n'
        '    <metadata key="thumbnail_no_light_file" value="Metadata/plate_no_light_1.png"/>\n'
        '    <metadata key="top_file" value="Metadata/top_1.png"/>\n'
        '    <metadata key="pick_file" value="Metadata/pick_1.png"/>\n'
        '    <model_instance>\n'
        f'      <metadata key="object_id" value="{assembly_object_id}"/>\n'
        '      <metadata key="instance_id" value="0"/>\n'
        f'      <metadata key="identify_id" value="{100 + assembly_object_id}"/>\n'
        '    </model_instance>\n'
        '  </plate>\n'
        '  <assemble>\n'
        f'   <assemble_item object_id="{assembly_object_id}" instance_id="0" transform="{build_transform}" offset="0 0 0" />\n'
        '  </assemble>\n'
        '</config>\n'
    )


def build_project_settings_with_base_colors(template_zip: zipfile.ZipFile, thickness_mm: float) -> str:
    raw = template_zip.read(SNAPMAKER_PROJECT_SETTINGS).decode("utf-8", errors="ignore")
    settings = json.loads(raw)
    settings["filament_colour"] = list(DEFAULT_BASE_FILAMENT_HEX)
    settings["extruder_colour"] = list(DEFAULT_BASE_FILAMENT_HEX[:4])
    settings["default_filament_colour"] = [""] * len(DEFAULT_BASE_FILAMENT_HEX)
    layer_height = thickness_mm / DEFAULT_BASE_THICKNESS_LAYERS
    settings["first_layer_print_height"] = format_number(layer_height)
    settings["layer_height"] = format_number(layer_height)
    mixed_filament_entries = [
        "1,5,1,0,50,0,g,w,m2,d0,o1,u72",
        "2,5,1,0,50,0,g,w,m2,d0,o1,u73",
        "3,5,1,0,50,0,g,w,m2,d0,o1,u74",
        "4,5,1,0,50,0,g,w,m2,d0,o1,u75",
    ]
    existing_mixed = settings.get("mixed_filament_definitions")
    if isinstance(existing_mixed, str):
        existing_entries = [entry for entry in existing_mixed.split(";") if entry]
        for entry in mixed_filament_entries:
            if entry not in existing_entries:
                existing_entries.append(entry)
        settings["mixed_filament_definitions"] = ";".join(existing_entries)
    return json.dumps(settings, indent=4, ensure_ascii=True) + "\n"


def build_custom_gcode_per_layer(
    base_thickness_mm: float,
    extruder_assignments: Dict[str, str],
) -> str:
    pause_extruder = next(
        (
            value
            for name, value in extruder_assignments.items()
            if name != LEAD_OBJECT_NAME and value != LEAD_FILAMENT_SLOT
        ),
        "1",
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<custom_gcodes_per_layer>\n'
        '<plate>\n'
        '<plate_info id="1"/>\n'
        f'<layer top_z="{format_number(base_thickness_mm)}" type="1" extruder="{pause_extruder}" color="" extra="" gcode="M600"/>\n'
        '<mode value="MultiAsSingle"/>\n'
        '</plate>\n'
        '</custom_gcodes_per_layer>\n'
    )


def write_snapmaker_project_3mf(
    output_path: Path,
    mesh_objects: Sequence[MeshObjectData],
    template_path: Path,
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
    plate_width_mm: float,
    plate_height_mm: float,
) -> List[str]:
    extruder_assignments = build_color_slot_assignments(
        mesh_objects,
        parse_template_extruders(template_path),
    )
    centered_meshes = [
        MeshObjectData(
            name=mesh_object.name,
            color=mesh_object.color,
            vertices=shifted_vertices(
                mesh_object.vertices,
                dx=-(width_mm / 2.0),
                dy=-(height_mm / 2.0),
                dz=-(thickness_mm / 2.0),
            ),
            triangles=mesh_object.triangles,
        )
        for mesh_object in mesh_objects
    ]

    overridden_files = {
        "3D/3dmodel.model",
        "3D/_rels/3dmodel.model.rels",
        SNAPMAKER_PROJECT_MARKER,
        SNAPMAKER_PROJECT_SETTINGS,
        SNAPMAKER_CUSTOM_GCODE_PER_LAYER,
    }

    with zipfile.ZipFile(template_path) as template_zip, zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as output_zip:
        for info in template_zip.infolist():
            if info.filename in overridden_files or info.filename.startswith("3D/Objects/"):
                continue
            output_zip.writestr(info, template_zip.read(info.filename))

        output_zip.writestr(
            "3D/3dmodel.model",
            build_snapmaker_root_model(
                centered_meshes,
                plate_width_mm=plate_width_mm,
                plate_height_mm=plate_height_mm,
                thickness_mm=thickness_mm,
            ),
        )
        output_zip.writestr("3D/_rels/3dmodel.model.rels", build_snapmaker_relationships(centered_meshes))
        output_zip.writestr(
            SNAPMAKER_PROJECT_MARKER,
            build_model_settings(
                mesh_objects,
                extruder_assignments,
                output_path=output_path,
                plate_width_mm=plate_width_mm,
                plate_height_mm=plate_height_mm,
                thickness_mm=thickness_mm,
            ),
        )
        output_zip.writestr(
            SNAPMAKER_PROJECT_SETTINGS,
            build_project_settings_with_base_colors(template_zip, thickness_mm=thickness_mm),
        )
        output_zip.writestr(
            SNAPMAKER_CUSTOM_GCODE_PER_LAYER,
            build_custom_gcode_per_layer(
                base_thickness_mm=thickness_mm,
                extruder_assignments=extruder_assignments,
            ),
        )
        output_zip.writestr(
            assembly_model_filename(centered_meshes),
            build_snapmaker_assembly_model(centered_meshes),
        )

    return [mesh_object.name for mesh_object in mesh_objects]


def open_in_orca_slicer(path: Path) -> bool:
    if sys.platform != "darwin":
        return False

    result = subprocess.run(
        ["open", "-a", DEFAULT_SLICER_APP, str(path)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main() -> int:
    args = parse_args()
    input_path = resolve_input_path(args.input_image)
    description_slug = sanitize_filename_bit(args.description) if args.description else infer_description_slug(input_path)
    output_path, preview_path = default_output_paths(
        input_path,
        args.output,
        args.preview,
        description_slug,
    )

    if args.num_nuances < 2:
        raise ValueError("num-nuances must be at least 2")
    if (
        args.width <= 0
        or args.height <= 0
        or args.thickness <= 0
        or args.lead_cap_height < 0
        or args.resolution <= 0
        or args.plate_width <= 0
        or args.plate_height <= 0
    ):
        raise ValueError(
            "width, height, thickness, resolution, plate-width, and plate-height must be positive; "
            "lead-cap-height must be non-negative"
        )

    grid_width = max(1, math.ceil(args.width / args.resolution))
    grid_height = max(1, math.ceil(args.height / args.resolution))
    actual_resolution_x = args.width / grid_width
    actual_resolution_y = args.height / grid_height
    blur_pixels = args.blur / min(actual_resolution_x, actual_resolution_y)

    rgb_image = load_image_to_grid(
        input_path,
        grid_width,
        grid_height,
        blur_pixels=blur_pixels,
    )
    flat_rgb = rgb_image.reshape(-1, 3)
    flat_lab = srgb_to_lab(rgb_image).reshape(-1, 3)

    raw_labels, lab_centers = kmeans(flat_lab, clusters=args.num_nuances, seed=args.seed)
    labels, _, region_colors = reorder_by_lightness(raw_labels, lab_centers, flat_rgb)
    labels = labels.reshape(grid_height, grid_width)
    labels = majority_smooth(labels, num_classes=args.num_nuances, passes=args.smooth_passes)

    cell_size_for_lines = min(actual_resolution_x, actual_resolution_y)
    line_radius_pixels = max(0, math.ceil(args.lead_thickness / cell_size_for_lines) - 1)
    lines = boundary_mask(labels, radius_pixels=line_radius_pixels)

    region_masks = []
    for nuance_index in range(args.num_nuances):
        region_masks.append(labels == nuance_index)

    palette_recipes = build_palette_recipes(
        region_colors=region_colors,
        layer_count=DEFAULT_BASE_THICKNESS_LAYERS,
    )
    preview_colors = np.asarray([recipe_color for _slots, recipe_color in palette_recipes], dtype=np.uint8)
    preview = build_preview(labels, preview_colors, lines)
    preview.save(preview_path)

    mesh_objects = build_mesh_objects(
        region_masks=region_masks,
        palette_recipes=palette_recipes,
        lines_mask=lines,
        width_mm=args.width,
        height_mm=args.height,
        thickness_mm=args.thickness,
        lead_cap_height_mm=args.lead_cap_height,
    )
    template_path = find_snapmaker_template(args.snapmaker_template, output_path=output_path)

    if template_path is not None:
        built_object_names = write_snapmaker_project_3mf(
            output_path=output_path,
            mesh_objects=mesh_objects,
            template_path=template_path,
            width_mm=args.width,
            height_mm=args.height,
            thickness_mm=args.thickness,
            plate_width_mm=args.plate_width,
            plate_height_mm=args.plate_height,
        )
    else:
        built_object_names = write_plain_3mf(output_path=output_path, mesh_objects=mesh_objects)

    opened = False
    if not args.no_open:
        opened = open_in_orca_slicer(output_path)

    print(f"Input image: {input_path}")
    print(f"Preview PNG: {preview_path}")
    print(f"3MF output:  {output_path}")
    if description_slug:
        print(f"Name slug:   {description_slug}")
    print(f"Plate size:  {args.width:.2f} x {args.height:.2f} mm")
    print(f"Bed center:  {args.plate_width / 2.0:.2f} x {args.plate_height / 2.0:.2f} mm")
    print(f"Thickness:   {args.thickness:.2f} mm base")
    print(f"Lead width:  {args.lead_thickness:.2f} mm")
    print(f"Lead cap:    {args.lead_cap_height:.2f} mm")
    print(f"Total z:     {args.thickness + args.lead_cap_height:.2f} mm")
    print(f"Base layers: {DEFAULT_BASE_THICKNESS_LAYERS} x {args.thickness / DEFAULT_BASE_THICKNESS_LAYERS:.3f} mm")
    print(f"Blur:        {args.blur:.2f} mm")
    print(f"Resolution:  {args.resolution:.3f} mm target")
    print(f"Grid size:   {grid_width} x {grid_height}")
    print(f"Cell size:   {actual_resolution_x:.3f} x {actual_resolution_y:.3f} mm")
    print(f"Objects:     {len(built_object_names)}")
    if template_path is not None:
        print(f"Template:    {template_path}")
    for name in built_object_names:
        print(f"  - {name}")
    for nuance_index, (slots, mixed_color) in enumerate(palette_recipes, start=1):
        slot_label = "".join(BASE_SLOT_LABEL[slot] for slot in slots)
        print(
            f"  Palette {nuance_index:02d}: {slot_label} -> "
            f"rgb({mixed_color[0]},{mixed_color[1]},{mixed_color[2]})"
        )

    if args.num_nuances == 10:
        print(
            "Note: each nuance is now built from 4 stacked CMYW slices, "
            "plus the black lead cap on slot 5."
        )
    if not args.no_open and not opened:
        print(
            f"{DEFAULT_SLICER_APP} was not opened automatically. "
            "Open the 3MF manually if the app is installed under a different name."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
