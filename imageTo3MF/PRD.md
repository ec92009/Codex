# Product Requirements Document

## Product
ImageTo3MF

## Summary
ImageTo3MF converts a source image into a printable multi-object 3MF project for stained-glass-style or layered color plate workflows. The product combines image segmentation, lead-line generation or detection, palette fitting against measured materials, and export into slicer-ready project files with object-level color or filament assignments.

The current product already supports a CLI, a desktop GUI, stage previews, material tuning, and project export. The next phase should focus on making the output consistently trustworthy in real slicers, especially around object-to-filament assignment, generated-vs-detected lead behavior, and repeatable launch/export workflows for non-technical users.

## Problem Statement
Turning a flat image into a clean, multi-color printable plate is still too manual.

Users currently need to:
- segment or simplify artwork by hand
- define or preserve lead lines manually
- guess material blends rather than use measured material behavior
- repair or reassign colors in slicers after export
- rely on fragile launcher or template behavior to get consistent results

This slows down iteration and makes the process unreliable, especially for users who want a desktop-tool experience rather than a scripting workflow.

## Goals
- Convert a source image into a clean printable 3MF with minimal manual cleanup.
- Support both generated lead and detected lead workflows.
- Produce exports that preserve intended color/material assignments in the target slicer.
- Make material tuning understandable and repeatable through the GUI.
- Provide a one-click desktop experience on macOS.
- Make output predictable enough for repeat use on the same printer/material setup.

## Non-Goals
- General-purpose CAD modeling.
- Advanced image editing or illustration.
- Full slicer replacement.
- Support for every slicer or every printer family in the first phase.
- Photorealistic color reproduction across arbitrary materials without calibration.

## Target Users
### Primary
- Maker/artist producing stained-glass-style color plates from images.
- Hobbyist using Snapmaker Orca or similar slicer workflows.
- User who prefers GUI workflows over direct CLI usage.

### Secondary
- Advanced user who wants scriptable batch conversion through CLI.
- User who wants to reuse hand-painted slicer assignments as templates.

## User Stories
- As a user, I want to choose an image and generate a printable 3MF without opening a terminal.
- As a user, I want lead lines to look clean whether they are generated or detected from the source art.
- As a user, I want the exported project to open with the intended part-to-material assignments already applied.
- As a user, I want to tune material colors and TD values and immediately use them in output generation.
- As a user, I want stage previews so I can understand whether segmentation or lead generation failed before printing.
- As a user, I want repeatable filenames, project naming, and output layout so generated files are easy to organize.

## Core Workflows
### Workflow 1: GUI-first generation
1. Launch the desktop app.
2. Select an image.
3. Review auto-filled size and settings.
4. Choose generated or detected lead.
5. Adjust material colors and TD values if needed.
6. Generate preview and final 3MF.
7. Open the project in the slicer with assignments preserved.

### Workflow 2: CLI batch generation
1. Call the CLI with image path and sizing/material options.
2. Generate stage previews and output files.
3. Reuse saved template assignments if available.
4. Open or inspect the final project in the slicer.

### Workflow 3: Template-guided export
1. User saves or hand-edits a working slicer project.
2. Product detects that project in the output folder.
3. Product reuses compatible material/extruder assignments on the next export.
4. User avoids repainting the project manually.

## Functional Requirements
### Input and preprocessing
- Accept common raster image formats.
- Support image selection via GUI and file-path input via CLI.
- Auto-fill output size based on image aspect ratio.
- Support blur/smoothing controls before color quantization.
- Support deterministic runs via seed.

### Lead handling
- Support `generate` mode for synthetic lead from region boundaries.
- Support `detect` mode for preserving dark lead already present in source imagery.
- Produce stage previews for raw lead, smoothed lead, filtered lead, and final preview.
- Allow lead thickness and lead height control.

### Region segmentation and palette fitting
- Support configurable nuance count.
- Segment source image into printable regions.
- Fit region colors against the available material palette using TD-aware simulation.
- Support material overrides for all available slots.
- Preserve a dedicated black lead path.

### Export
- Generate multi-object 3MF output.
- Export slicer-ready project metadata, not only generic geometry.
- Preserve stable object naming between runs when possible.
- Preserve part-to-material assignment where template reuse is intended.
- Write output files with predictable names.
- Support opening the output directly in the target slicer.

### GUI
- Provide image picker, settings controls, live logs, preview panes, and stage navigation.
- Support saving and loading material presets.
- Provide presets for default CMYWK and alternate material layouts.
- Surface generation status and failures clearly.

### macOS desktop experience
- Support `.app`, `.command`, and shell launchers.
- Launch reliably without requiring the user to understand Python or `uv`.
- Fail with a readable message when dependencies are missing.

## Reliability Requirements
- Generated 3MF projects must preserve intended material assignments in the target slicer.
- Generated projects must not silently collapse all parts onto one filament slot.
- Template reuse must be explicit and predictable.
- Output should be reproducible for the same inputs and settings.
- Exported projects should avoid slicer warnings caused by malformed or incomplete metadata where possible.

## Key Product Risks
- Slicer-specific 3MF metadata differences can cause color/slot assignments to fail even when geometry is correct.
- Generated lead may look visually strong while color assignment metadata is wrong, creating false confidence.
- Template reuse can hide bugs by partially masking assignment problems.
- Material simulation quality depends on measured TD values and can drift from real prints.
- Desktop launcher quality depends on local Python/`uv` installation paths.

## Design Principles
- Trustworthiness over cleverness: users should be able to understand what was generated and why.
- Visual feedback early: show intermediate stages, not only final output.
- Repeatability over magic: auto-detection is useful, but output mapping should stay inspectable.
- Default to good results for non-technical users.
- Keep advanced control available without burdening the basic workflow.

## Success Metrics
- User can go from image selection to slicer-opened project without manual terminal use.
- User no longer needs to repaint objects manually in the slicer in the common path.
- Lead generation produces acceptable output on first pass for typical stained-glass source images.
- Exported projects open without major metadata-related assignment failures in the target slicer.
- Users can save and reuse material presets successfully.

## Open Questions
- Which slicer formats and metadata conventions must be treated as first-class targets beyond Snapmaker Orca?
- Should template reuse remain automatic, or become opt-in to avoid hidden behavior?
- How should mixed/virtual filament slots be represented so slicers consistently honor them?
- Should the GUI expose an explicit assignment preview showing which part will map to which slot?
- Should the product support profile bundles per printer/material combination?

## Recommended Next Milestones
### Milestone 1: Export correctness
- Make project metadata generation deterministic and slicer-specific.
- Add validation for part-to-filament assignment before writing output.
- Add regression fixtures for generated and detected lead exports.

### Milestone 2: Workflow trust
- Add an export summary panel showing region count, lead mode, material slots, and expected slicer assignments.
- Make template reuse visible and optionally toggleable.
- Add warnings when output falls back to a potentially unsafe metadata path.

### Milestone 3: Product polish
- Improve desktop app packaging and dependency detection.
- Add project presets for common printer/material combinations.
- Add better previewing of simulated printed color versus source image.

## Appendix: Current State Snapshot
Current capabilities observed in the project:
- CLI exporter
- PyQt GUI
- Stage previews
- Generated and detected lead modes
- TD-aware material palette fitting
- Material preset editing
- Snapmaker-oriented 3MF project export
- macOS launcher scripts and app packaging path

Current priority gaps observed in use:
- Slicer color/material assignment reliability
- Mixed-slot/export metadata correctness
- More explicit user feedback around template reuse and final slot mapping
