# LeadLight

Use `uv run python image_grade_to_3mf.py /path/to/image.png --layer-height 0.2mm --base-layers 4 --size 100x100 --resolution 0.4mm --lead-thickness 0.4mm --lead-height 0.2mm --plate-size 270x270` to convert an image into segmented color zones plus black separator lines, export the result as a multi-object `.3mf`, and open it in Snapmaker Orca.

Use `--lead-source generate` for the normal synthetic lead, or `--lead-source detect` when the source image already contains stained-glass lead that should guide the top black layer. In `detect` mode, LeadLight now uses a hybrid pipeline: it detects only confident lead anchors, generates pane regions in the remaining space, merges tiny panes into their closest-color neighbor, reduces the pane colors down to the requested palette size, and removes generated lead between panes that collapse to the same reduced color.

The GUI now leaves picture size blank until you choose an image, then auto-fills it so the source image's long side becomes `100 mm` and the short side follows the original aspect ratio. A slider under picture size lets you scale that long side up or down while preserving the same ratio.

To use the LeadLight desktop GUI, run `uv run python image_grade_to_3mf_gui.py`. The GUI keeps the CLI/exporter intact and wraps it with image selection, material TD editing, live run logs, and preview panes. The Materials panel now also includes a `DB` button on each slot row so you can pick measured filaments directly from the local `filamentDB`.
Use the Materials `Settings` button to point LeadLight at the correct `filaments.tsv` on each machine. That path is saved locally per computer, so it can follow different local layouts without changing the repo.
The GUI stage viewer now shows intermediate refinement states instead of a generic progress bar, and you can step backward and forward through those stages with `-` and `+`. The bottom action row now uses explicit `Generate`, `Reveal`, and `Open` buttons, with `Open` handing the latest generated `3mf` to Snapmaker Orca on demand.

For detector tuning without disturbing the main app, run `uv run python lead_detect_batch_preview.py` to build a contact sheet for `~/Desktop/A.png` through `~/Desktop/F.png` showing step 1 (`resized_source`) next to step 2 (`detected_lead_raw`).

For a more robust alternate experiment, run `uv run python glass_interior_growth_lab.py /path/to/image.png`. That lab uses a smoothed analysis image to grow likely glass interiors first, then derives lead from the leftover boundaries. The current promising settings for the `F.png` stained-glass test are around `--analysis-blur-px 1.4 --lead-luma-threshold 30 --hard-lead-chroma-max 26 --neutral-chroma-max 18 --neutral-edge-threshold 14`.

There is also a hybrid experiment at `uv run python glass_hybrid_anchor_lab.py /path/to/image.png`. That one detects only confident lead anchors, generates the remaining pane regions from color clustering, merges tiny panes into the closest-color touching neighbor, then shows a before/after palette reduction preview so the final result can be evaluated against the `8..10` color constraint. In the reduced preview, generated lead between panes that collapse to the same reduced color is removed automatically, while the detected anchor lead stays intact. The current promising baseline uses the script defaults, or a slightly tighter anchor set such as `--anchor-luma 36 --anchor-chroma 24 --neutral-chroma 13 --neutral-contrast 22 --neutral-support-max 5`.

For Snorca Full Spectrum debugging, `uv run python snorca_mixed_filament_diagnostic.py --open` creates a tiny test `3mf` with a few large panes assigned to explicit recipe slots such as `6`, `8`, and `12`. That is useful for checking whether the object list badges match the actual mixed-filament definitions or whether SnorcaFS is only miscoloring the UI.

There are also launcher scripts at `/Users/ecohen/Codex/imageTo3MF/launch_leadlight_gui.sh` and `/Users/ecohen/Codex/imageTo3MF/launch_leadlight_gui.command`.

For a no-Terminal macOS launcher, build the local app bundle with `/Users/ecohen/Codex/imageTo3MF/build_leadlight_app.sh`. That creates `/Users/ecohen/Codex/imageTo3MF/dist/LeadLight.app`.

If you switch computers, `git pull` in `/Users/ecohen/Codex` first, then rerun `/Users/ecohen/Codex/imageTo3MF/build_leadlight_app.sh` on that machine so the local bundle matches the latest code.

If no image path is passed, the script opens a file picker on macOS.

If a hand-painted Snapmaker Orca project `.3mf` is present in the output folder, the script reuses its saved object-to-color assignments automatically.

If `--description` is supplied, the default output names use a lowercase filename-safe version of that description. If no description is supplied, the script now tries to infer one locally from the image contents on macOS. For generic source names like `image2.png`, that inferred slug becomes the filename base directly.

By default the generated model is `100 x 100 mm`, uses a `0.8 mm` full-color base body built from `4 x 0.2 mm` base layers plus a `0.2 mm` lead layer on top, uses a `0.4 mm` XY working resolution, sets the black separator thickness to `0.4 mm`, and centers the result on a `270 x 270 mm` plate. The base image now exports as one object per nuance, with each nuance assigned to the closest fitted Snapmaker palette recipe, and the Snapmaker export is written as a single assembled project.

The Snapmaker project writer currently forces the filament palette in the exported `3mf` to cyan, magenta, yellow, white, and black (`CMYWK`), maps the `Lead` part to slot `5`, and writes a per-layer `M600` pause just before the final lead layer so that black can be loaded at that moment.

When writing the Snapmaker project settings, the exporter now normalizes the print profile block to match Snorca's saved `0.20 Standard @Snapmaker U1 (0.4 nozzle)` state, which avoids the Spiral Lifting / Z-hop warning path you saw on generated files.

You can override any of the five available materials with repeatable `--material SLOT:#RRGGBB@TD` flags such as `--material cyan:#88FFFF@6.2 --material 4:#F8F8F8@9.0`. If no `--material` flags are passed, the script assumes the default `CMYWK` palette and default TD values. The current palette fitting and preview path use a simple TD-aware stack simulation rather than plain RGB averaging.
