# Image grading to 3MF

Use `uv run python image_grade_to_3mf.py /path/to/image.png --thickness 1mm --width 100mm --height 100mm --resolution 0.25mm --lead-thickness 0.25mm --lead-cap-height 0.3mm --plate-width 270mm --plate-height 270mm` to convert an image into segmented color zones plus black separator lines, export the result as a multi-object `.3mf`, and open it in Snapmaker Orca.

If no image path is passed, the script opens a file picker on macOS.

If a hand-painted Snapmaker Orca project `.3mf` is present in the output folder, the script reuses its saved object-to-color assignments automatically. You can also point to one explicitly with `--snapmaker-template /path/to/template.3mf`.

By default the generated model is `100 x 100 mm`, uses a `1 mm` full-color base body plus a `0.3 mm` lead cap on top, uses a `0.5 mm` XY working resolution, sets the black separator thickness to `0.25 mm`, and centers the result on a `270 x 270 mm` plate. The Snapmaker export is written as a single assembled project containing the `Lead` part plus 10 nuance parts, while preserving per-part color assignments.
