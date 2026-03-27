#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import image_grade_to_3mf as engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a tiny Snapmaker/Snorca diagnostic 3MF to verify mixed-filament slot display behavior."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / "Codex" / "imageTo3MF" / "out" / "snorca_mixed_filament_blatant_diagnostic.3mf",
        help="Output 3MF path.",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=Path.home() / "Codex" / "imageTo3MF" / "out" / "270sample_input_graded.3mf",
        help="Snapmaker/Snorca template 3MF to wrap the model in.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated 3MF in Snapmaker Orca after export.",
    )
    return parser.parse_args()


def rectangle_mask(width: int, height: int, x0: int, y0: int, x1: int, y1: int):
    import numpy as np

    mask = np.zeros((height, width), dtype=bool)
    mask[y0:y1, x0:x1] = True
    return mask


def main() -> int:
    args = parse_args()
    material_profiles = engine.default_material_profiles()

    width_mm = 168.0
    height_mm = 80.0
    plate_width_mm = 270.0
    plate_height_mm = 270.0
    thickness_mm = 0.8
    base_layer_height_mm = 0.2

    grid_w = 168
    grid_h = 80
    import numpy as np

    # Seven tall panes, one for each mixed slot from 6 through 12.
    lines_mask = np.zeros((grid_h, grid_w), dtype=bool)
    for x in (23, 47, 71, 95, 119, 143):
        lines_mask[:, x : x + 2] = True
    lines_mask[:2, :] = True
    lines_mask[-2:, :] = True
    lines_mask[:, :2] = True
    lines_mask[:, -2:] = True

    masks = [
        rectangle_mask(grid_w, grid_h, 2, 2, 23, grid_h - 2),
        rectangle_mask(grid_w, grid_h, 25, 2, 47, grid_h - 2),
        rectangle_mask(grid_w, grid_h, 49, 2, 71, grid_h - 2),
        rectangle_mask(grid_w, grid_h, 73, 2, 95, grid_h - 2),
        rectangle_mask(grid_w, grid_h, 97, 2, 119, grid_h - 2),
        rectangle_mask(grid_w, grid_h, 121, 2, 143, grid_h - 2),
        rectangle_mask(grid_w, grid_h, 145, 2, grid_w - 2, grid_h - 2),
    ]

    # Explicit recipes for every mixed slot from 6 through 12.
    recipes = [
        engine.PaletteRecipe(
            layer_slots=["1", "2", "1", "2"],
            mixed_color=engine.simulate_stack_rgb(
                ["1", "2", "1", "2"], material_profiles, layer_height_mm=base_layer_height_mm
            ),
            display_slot="6",
            definition=engine.build_mixed_filament_definition("1", "2", 50, "6"),
        ),
        engine.PaletteRecipe(
            layer_slots=["1", "3", "1", "3"],
            mixed_color=engine.simulate_stack_rgb(
                ["1", "3", "1", "3"], material_profiles, layer_height_mm=base_layer_height_mm
            ),
            display_slot="7",
            definition=engine.build_mixed_filament_definition("1", "3", 50, "7"),
        ),
        engine.PaletteRecipe(
            layer_slots=["1", "4", "1", "4"],
            mixed_color=engine.simulate_stack_rgb(
                ["1", "4", "1", "4"], material_profiles, layer_height_mm=base_layer_height_mm
            ),
            display_slot="8",
            definition=engine.build_mixed_filament_definition("1", "4", 50, "8"),
        ),
        engine.PaletteRecipe(
            layer_slots=["2", "3", "2", "3"],
            mixed_color=engine.simulate_stack_rgb(
                ["2", "3", "2", "3"], material_profiles, layer_height_mm=base_layer_height_mm
            ),
            display_slot="9",
            definition=engine.build_mixed_filament_definition("2", "3", 50, "9"),
        ),
        engine.PaletteRecipe(
            layer_slots=["2", "4", "2", "4"],
            mixed_color=engine.simulate_stack_rgb(
                ["2", "4", "2", "4"], material_profiles, layer_height_mm=base_layer_height_mm
            ),
            display_slot="10",
            definition=engine.build_mixed_filament_definition("2", "4", 50, "10"),
        ),
        engine.PaletteRecipe(
            layer_slots=["3", "4", "3", "4"],
            mixed_color=engine.simulate_stack_rgb(
                ["3", "4", "3", "4"], material_profiles, layer_height_mm=base_layer_height_mm
            ),
            display_slot="11",
            definition=engine.build_mixed_filament_definition("3", "4", 50, "11"),
        ),
        engine.PaletteRecipe(
            layer_slots=["4", "5", "4", "5"],
            mixed_color=engine.simulate_stack_rgb(
                ["4", "5", "4", "5"], material_profiles, layer_height_mm=base_layer_height_mm
            ),
            display_slot="12",
            definition=engine.build_mixed_filament_definition("4", "5", 50, "12"),
        ),
    ]

    mesh_objects = []
    lead_vertices, lead_triangles = engine.mesh_from_mask(
        lines_mask,
        width_mm=width_mm,
        height_mm=height_mm,
        z_bottom_mm=thickness_mm,
        z_top_mm=thickness_mm + 0.2 + engine.LEAD_TOP_Z_EPSILON_MM,
    )
    mesh_objects.append(
        engine.MeshObjectData(
            name=engine.LEAD_OBJECT_NAME,
            color=material_profiles[engine.LEAD_FILAMENT_SLOT].rgb,
            vertices=lead_vertices,
            triangles=lead_triangles,
            preferred_slot=engine.LEAD_FILAMENT_SLOT,
        )
    )

    names = [
        "Color 2 - Slot 6 (F1+F2)",
        "Color 3 - Slot 7 (F1+F3)",
        "Color 4 - Slot 8 (F1+F4)",
        "Color 5 - Slot 9 (F2+F3)",
        "Color 6 - Slot 10 (F2+F4)",
        "Color 7 - Slot 11 (F3+F4)",
        "Color 8 - Slot 12 (F4+F5)",
    ]
    for name, mask, recipe in zip(names, masks, recipes):
        vertices, triangles = engine.mesh_from_mask(
            mask,
            width_mm=width_mm,
            height_mm=height_mm,
            z_bottom_mm=0.0,
            z_top_mm=thickness_mm,
        )
        mesh_objects.append(
            engine.MeshObjectData(
                name=name,
                color=recipe.mixed_color,
                vertices=vertices,
                triangles=triangles,
                preferred_slot=recipe.display_slot,
            )
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    engine.write_snapmaker_project_3mf(
        output_path=args.output,
        mesh_objects=mesh_objects,
        template_path=args.template,
        width_mm=width_mm,
        height_mm=height_mm,
        thickness_mm=thickness_mm,
        base_layer_height_mm=base_layer_height_mm,
        plate_width_mm=plate_width_mm,
        plate_height_mm=plate_height_mm,
        material_profiles=material_profiles,
        palette_recipes=recipes,
    )

    print(f"3MF output:  {args.output}")
    for name, recipe in zip(names, recipes):
        print(f"{name} -> display slot {recipe.display_slot}, color {recipe.mixed_color}, definition {recipe.definition}")
    if args.open:
        opened = engine.open_in_orca_slicer(args.output)
        print(f"Opened in Snapmaker Orca: {'yes' if opened else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
