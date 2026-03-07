---
name: video-to-webpage
description: Turn a video into a premium scroll-driven web page experience with GSAP, Lenis smooth scroll, canvas frame rendering, and layered animation choreography.
---

# Video to Premium Scroll-Driven Website

Turn a video file into a scroll-driven animated website with animation variety and choreography (not one repeated effect).

## Input

User provides a video file path (MP4/MOV/etc.) and optionally:
- Theme/brand name
- Desired text sections + placement
- Color preferences
- Specific design direction

If missing, ask briefly or use sensible defaults.

## Premium Checklist (Non-Negotiable)

1. Lenis smooth scroll
2. 4+ animation types (never repeat consecutive entrance type)
3. Staggered reveals (label → heading → body → CTA)
4. No glassmorphism cards
5. Direction variety (left/right/up/scale/clip)
6. Dark overlay for stats (0.88–0.92 opacity)
7. Horizontal marquee text (12vw+)
8. Counter animations (count up from 0)
9. Massive typography (hero 12rem+, headings 4rem+, marquee 10vw+)
10. Final CTA persists (`data-persist="true"`)
11. Hero prominence + generous scroll (20%+ hero, 800vh+ for 6 sections)
12. Side-aligned text only (outer 40% zones), except stats overlay
13. Circle-wipe hero reveal from standalone 100vh hero
14. Frame speed 1.8–2.2 (complete by ~55% scroll)

## Workflow

### 1) Analyze video

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration,r_frame_rate,nb_frames -of csv=p=0 "<VIDEO_PATH>"
```

Decide:
- Target frames: 150–300
- Short <10s: near source fps, cap ~300
- Medium 10–30s: 10–15fps
- Long 30s+: 5–10fps
- Keep aspect ratio, cap width at 1920

### 2) Extract frames

```bash
mkdir -p frames
ffmpeg -i "<VIDEO_PATH>" -vf "fps=<CALCULATED_FPS>,scale=<WIDTH>:-1" -c:v libwebp -quality 80 "frames/frame_%04d.webp"
ls frames | wc -l
```

### 3) Scaffold

```
project-root/
  index.html
  css/style.css
  js/app.js
  frames/frame_0001.webp ...
```

Use vanilla HTML/CSS/JS + CDN libs.

### 4) Build `index.html`

Required order:
1. Loader (`#loader`, `.loader-brand`, `#loader-bar`, `#loader-percent`)
2. Fixed header (`.site-header` + nav)
3. Standalone hero (`.hero-standalone`, 100vh)
4. Canvas wrapper (`.canvas-wrap > canvas#canvas`)
5. Dark overlay (`#dark-overlay`)
6. Marquee (`.marquee-wrap > .marquee-text`)
7. Scroll container (`#scroll-container`, 800vh+)

Content sections must include `data-enter`, `data-leave`, `data-animation`.
Stats section uses `.stat-number[data-value][data-decimals]`.
Final CTA section must use `data-persist="true"`.

CDN order at end of body:
```html
<script src="https://cdn.jsdelivr.net/npm/lenis@1/dist/lenis.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/ScrollTrigger.min.js"></script>
<script src="js/app.js"></script>
```

### 5) Build `css/style.css`

Use frontend-design skill for visual direction. Enforce:
- Side text zones:
  - `.align-left { padding-left: 5vw; padding-right: 55vw; }`
  - `.align-right { padding-left: 55vw; padding-right: 5vw; }`
- Hero-first layout (100vh hero, canvas reveals via clip-path)
- Sections absolute-positioned by enter/leave midpoint
- Mobile <768px: collapse to centered text with dark backplates, ~550vh total
- Ensure readable contrast (`#666` minimum for body on light bg)

### 6) Build `js/app.js`

#### 6a) Lenis (mandatory)
```js
const lenis = new Lenis({
  duration: 1.2,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  smoothWheel: true
});
lenis.on("scroll", ScrollTrigger.update);
gsap.ticker.add((time) => lenis.raf(time * 1000));
gsap.ticker.lagSmoothing(0);
```

#### 6b) Preloader
Two-phase: first ~10 frames immediately, rest in background, progress visible.

#### 6c) Canvas render (padded cover)
Use `IMAGE_SCALE` ~0.82–0.90, fill bg with sampled edge color before draw.
Apply `devicePixelRatio` scaling.

#### 6d) Frame-scroll binding
Use `FRAME_SPEED` 1.8–2.2. Map scroll progress to frame index with acceleration cap.

#### 6e) Section animation system
Support multiple types: `fade-up`, `slide-left`, `slide-right`, `scale-up`, `rotate-in`, `stagger-up`, `clip-reveal`.
No consecutive same type. Honor `data-persist="true"`.

#### 6f) Counters
Animate `.stat-number` from 0 using `data-value` + decimal-aware snap.

#### 6g) Marquee
Animate `.marquee-text` xPercent with scrubbed ScrollTrigger.

#### 6h) Dark overlay
Fade in/out by range; hold around 0.9 during stats window.

#### 6i) Hero circle wipe
Fade hero out at start, reveal canvas via `clip-path: circle()` progression.

### 7) Test
1. Serve locally (`python -m http.server 8000` or equivalent)
2. Scroll full page and validate all checklist items
3. Confirm: smooth scroll, frame playback, varied entrances, stagger, marquee, counters, overlay, persistent CTA

## Anti-Patterns

- Pinned card cycling with too little scroll time
- Pure cover at 1.0 causing clipping
- Pure contain causing visible borders
- `FRAME_SPEED < 1.8`
- Hero with too little scroll range
- Consecutive same animation type
- Centered wide text grids over canvas
- Total scroll too short (<800vh for 6 sections)

## Troubleshooting

- Frames fail: serve over HTTP (not `file://`)
- Choppy: reduce frame count / adjust scrub
- White flash: hide loader only when all frames loaded
- Blur: ensure DPR scaling
- Lenis/GSAP mismatch: wire `lenis.on("scroll", ScrollTrigger.update)`
- Counter issues: verify `data-value` / decimal snap
- Mobile memory: cut frames (<150), resize to ~1280 width
