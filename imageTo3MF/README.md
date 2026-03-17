# Image grading to 3MF

Use `uv run python image_grade_to_3mf.py /path/to/image.png --thickness 1mm --size 100x100 --resolution 0.25mm --lead-thickness 0.25mm --lead-height 0.3mm --plate-size 270x270` to convert an image into segmented color zones plus black separator lines, export the result as a multi-object `.3mf`, and open it in Snapmaker Orca.

If no image path is passed, the script opens a file picker on macOS.

If a hand-painted Snapmaker Orca project `.3mf` is present in the output folder, the script reuses its saved object-to-color assignments automatically.

If `--description` is supplied, the default output names use a lowercase filename-safe version of that description. If no description is supplied, the script now tries to infer one locally from the image contents on macOS. For generic source names like `image2.png`, that inferred slug becomes the filename base directly.

By default the generated model is `100 x 100 mm`, uses a `1 mm` full-color base body plus a `0.3 mm` lead cap on top, uses a `0.5 mm` XY working resolution, sets the black separator thickness to `0.25 mm`, and centers the result on a `270 x 270 mm` plate. The base image is now emitted as four stacked `0.25 mm` CMYW slices per nuance, and the Snapmaker export is written as a single assembled project.

The Snapmaker project writer currently forces the filament palette in the exported `3mf` to cyan, magenta, yellow, white, and black (`CMYWK`), maps the `Lead` part to slot `5`, and writes a per-layer `M600` pause just before the final lead layer so that black can be loaded at that moment.

You can override any of the five available materials with repeatable `--material SLOT:#RRGGBB@TD` flags such as `--material cyan:#88FFFF@6.2 --material 4:#F8F8F8@9.0`. If no `--material` flags are passed, the script assumes the default `CMYWK` palette and default TD values. The current palette fitting and preview path use a simple TD-aware stack simulation rather than plain RGB averaging.
