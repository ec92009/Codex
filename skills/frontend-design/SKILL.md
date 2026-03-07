---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, or applications. Generate creative, polished code that avoids generic AI aesthetics.
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about purpose, audience, or technical constraints.

## Design Thinking

Before coding, understand context and commit to a bold aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick a clear direction (brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful, editorial, brutalist/raw, art deco, soft/pastel, industrial/utilitarian, etc.)
- **Constraints**: Technical requirements (framework, performance, accessibility)
- **Differentiation**: What is unforgettable about this implementation?

**Critical**: Choose one conceptual direction and execute it with precision. Bold maximalism and refined minimalism can both work; intentionality matters most.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point of view
- Meticulously refined in details

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Use distinctive, characterful font pairings (display + body). Avoid default/generic choices.
- **Color & Theme**: Commit to cohesive palette using CSS variables. Prefer strong direction over timid palettes.
- **Motion**: Use purposeful animation and micro-interactions. Prioritize one or two high-impact moments.
- **Spatial Composition**: Use asymmetry, overlap, diagonal flow, grid breaks, or intentional negative space/density.
- **Backgrounds & Details**: Create atmosphere/depth (mesh gradients, textures, patterns, layers, shadows, borders, grain) that match the concept.

Avoid generic, repetitive AI-looking output patterns. Vary light/dark mode, typography, layout rhythm, and compositional choices by context.

**Important**: Match implementation complexity to design vision. Maximalist concepts need robust effect systems; minimalist concepts need restraint and precise craft.

## Scroll-Driven Website Design Guidelines

When used alongside `video-to-website` or `video-to-webpage`, apply these additional rules.

### Typography as Design
- Hero headings: **6rem minimum**, line-height 0.9–1.0, weight 700–800
- Section headings: **3rem minimum**, weight 600–700
- Marquee text: **10–15vw**, uppercase, letter-spaced
- Section labels: ~0.7rem uppercase with 0.15em+ tracking, muted (e.g., `001 / Features`)
- Use hierarchy via typography rather than containers

### No Cards, No Boxes
- Do not use glassmorphism/frosted cards for scroll-driven sections
- Put text directly on background; ensure readability via weight/contrast/shadow where needed
- Only acceptable “container” is generous section padding

### Color Zones
- Shift backgrounds between sections (light/dark/accent)
- Define variables (`--bg-light`, `--bg-dark`, `--bg-accent`, `--text-on-light`, `--text-on-dark`)
- Drive transitions via GSAP when appropriate

### Layout Variety
Include at least 3 patterns:
1. Centered
2. Left-aligned
3. Right-aligned
4. Full-width (marquee/stats)
5. Split layout

Avoid repeating the same pattern in consecutive sections.

### Animation Choreography
- Use different entrance animations across sections
- Stagger internals (about 0.08–0.12s)
- Sequence: label → heading → body → CTA
- Include at least one pinned section with internal animation
- Include at least one horizontally moving oversized text element

### Stats & Numbers
- Stats at **4rem+**
- Numbers must count up (GSAP), not appear static
- Units/suffix in separate smaller element
- Labels in muted uppercase/small caps

## Output format (required)

When delivering changes, include:
1. **Version** using `vX.Y` (X = day of month, Y = iteration counter for that day)
2. **Change summary**
3. **Files touched**
4. **Quick QA checks performed**
5. **Suggested next step**
