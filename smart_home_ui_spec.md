# Smart Home Dashboard — UI Recreation Spec

A complete visual specification of a tablet-style Smart Home dashboard. This document is written so an LLM (or a developer) can recreate the interface pixel-for-pixel in HTML/CSS, React, Qt/QML, LVGL, or any other GUI toolkit, without needing to see the source image.

---

## 1. Canvas & Global Style

**Aspect ratio & orientation.** Landscape tablet, roughly 16:10 (e.g. 1280 × 800 or 1920 × 1200). The entire UI lives inside a rounded-rectangle device bezel with a thin white inner frame; the UI itself has no device chrome — it fills the screen edge-to-edge.

**Background.** Uniform off-white / warm paper color. Use `#F5F2EC` (warm cream) or `#F3F0EA`. There is no gradient, no pattern, no texture. All cards float on this single flat background.

**Design language.** Minimal, editorial, neo-skeuomorphic in places (soft shadows on device photos) but flat elsewhere. Lots of generous negative space. The aesthetic sits between Apple's Home app and a boutique product landing page.

**Typography.** A single elegant serif for headings and big numerical readouts (Cormorant Garamond, Playfair Display, or DM Serif Display all work). A neutral humanist sans-serif for labels and secondary text (Inter, SF Pro, or Söhne). Italic serif is used sparingly for device names and song titles.

- H1 ("Smart Home"): serif, ~64–72 px, regular weight, color `#1A1A1A`.
- Card titles (e.g. "Thermostat", "Current Weather"): sans-serif, ~18 px, medium weight, color `#2A2A2A`.
- Big value readouts (27°, 6°, 67°, 19%): serif, 48–64 px, regular weight.
- Micro-labels ("Cloudy", "Cooling Down", "Battery: Low", "Living room"): sans-serif, 12–13 px, regular, color `#6E6E6E`.
- Status bar text: sans-serif, 11 px, color `#8A8A8A`.

**Color palette (per tile).**

| Role                | Hex        | Notes                                      |
|---------------------|------------|--------------------------------------------|
| App background      | `#F5F2EC`  | Warm cream                                  |
| Thermostat tile     | `#EDEAE4`  | Slightly darker cream / stone               |
| Weather tile        | `#F1EBDA`  | Pale buttery beige                          |
| Smart Kettle tile   | `#E9C9B4`  | Muted peach / salmon                        |
| Vacuum tile         | `#C9A987`  | Warm tan / camel                            |
| Wi-Fi toggle tile   | `#E6E8DE`  | Very pale sage                              |
| Live camera tile    | full-bleed photo, no tint                   |
| Now Playing         | transparent (sits on app background)        |
| Primary ink         | `#1A1A1A`  | Headings & numerals                         |
| Secondary ink       | `#6E6E6E`  | Labels                                      |
| Accent green        | `#3FB950`  | Toggle-on, Spotify logo, Wi-Fi arc          |
| Accent red          | `#E4442B`  | "LIVE" badge                                |

**Corner radius.** Cards use a generous radius — 24 px on a 1280-wide canvas (about 1.8% of width). All tiles share the same radius for rhythm.

**Shadows.** Tiles themselves are flat (no drop shadow). Only photographic inserts inside tiles — the kettle, the vacuum robot, the Now Playing album art — carry a soft, low-contrast shadow (`0 8px 24px rgba(0,0,0,0.08)`).

---

## 2. Overall Layout

The screen is divided into three columns:

```
┌─────────────┬──────────────────────────────────────────────────────────┐
│  SIDEBAR    │  STATUS BAR (time, date)                    ●●● Wi-Fi    │
│  (nav rail) │                                                          │
│             │  Smart Home   ← H1                                       │
│  ← Main     │                                                          │
│  Smart Home │  ┌─────────────────────┐   ┌──────────────────────────┐  │
│  EV Charging│  │                     │   │  ▶ Now Playing            │  │
│  Messages   │  │   Thermostat        │   │  (album art + controls)   │  │
│             │  │   (big dial, 27°)   │   │                          │  │
│             │  │                     │   └──────────────────────────┘  │
│             │  │                     │                                 │
│             │  └─────────────────────┘   ┌──────────┐  ┌────────────┐  │
│             │                            │  Smart   │  │  Vacuum     │  │
│             │  ┌─────────────────────┐   │  Kettle  │  │  Cleaner    │  │
│             │  │   Current Weather   │   │  67°     │  │  19%        │  │
│             │  │   6°/9° + cloud     │   └──────────┘  └────────────┘  │
│             │  │                     │                                 │
│             │  │                     │   ┌──────────┐  ┌────────────┐  │
│             │  │                     │   │ Wi-Fi On │  │ LIVE cam    │  │
│             │  └─────────────────────┘   └──────────┘  └────────────┘  │
└─────────────┴──────────────────────────────────────────────────────────┘
```

**Column widths (as fractions of total width):**
- Sidebar: ~12%
- Main content: ~88%, internally split roughly 50/50 between left column (Thermostat + Weather stacked) and right area (Now Playing on top, then a 2×2 grid of smaller tiles).

**Gaps.** Uniform 16–20 px gutters between tiles. Outer page padding ~40 px top/bottom, ~32 px left/right inside the main column.

---

## 3. Sidebar (Left Navigation Rail)

A vertical rail flush against the left edge, same cream background as the page (no divider, no tint). Icons and labels are aligned left with ~24 px left padding.

**Items (top to bottom, each ~44 px tall):**

1. **← Main** — left-arrow glyph, label "Main". Acts as a back button.
2. **Smart Home** — a small rounded-square "house" or "grid" icon. This is the currently selected item but the selection is indicated only by context (it's the current page); no visible pill, underline, or bold weight. All nav items look visually identical.
3. **EV Charging** — a circular icon containing a lightning bolt / plug glyph.
4. **Messages** — a speech-bubble or stacked-rectangles icon.

**Styling.** Icons are thin-line, ~16 px, stroke `#2A2A2A`. Labels sit ~8 px to the right of each icon, sans-serif 13 px, color `#2A2A2A`. Line-height gives roughly 20 px vertical space between items.

There is no sidebar footer, no user avatar, no settings gear.

---

## 4. Status Bar

A single horizontal strip along the very top of the main content area. It contains only:

- **Left:** time and date, e.g. `9:41  Wed, 12 Jun 2024`. Sans-serif 11 px, color `#8A8A8A`, letter-spacing slightly loose. The time and date are separated by two spaces, no pipe.
- **Right:** a solid black Wi-Fi "fan" glyph (three arcs + dot), ~14 px, color `#1A1A1A`. No battery, no notifications, no other status icons.

The status bar has ~28 px of breathing room below it before the "Smart Home" H1 begins.

---

## 5. Page Heading

Single H1 reading **Smart Home**. Serif, ~64 px, regular weight (not bold), color `#1A1A1A`. Left-aligned with the main content column. No subtitle, no buttons beside it. Substantial whitespace below the heading (~32–40 px) before the first tile.

---

## 6. Tiles (detailed)

### 6.1 Thermostat (large, top-left)

**Dimensions.** Roughly 380 × 340 px (tall-ish square). Fills the top of the left main column.

**Background.** `#EDEAE4` (cream-stone), 24 px radius, no border.

**Header row.** Top-left of the tile, ~24 px inset from the edges:
- Small icon: three stacked wavy/zigzag lines representing a heat/airflow glyph, stroke `#2A2A2A`, ~16 px.
- Label "Thermostat", sans-serif 15–16 px, medium weight, `#2A2A2A`, 8 px to the right of the icon.

**Center dial.** A large circular gauge occupying the middle of the tile:
- An almost-full circle stroke (~270° arc, open at the bottom), stroke weight 12–14 px, color `#1A1A1A` (solid black).
- A tiny circle (~10 px diameter, filled white with a faint shadow) sits on the arc at the top-right, acting as the draggable setpoint handle. Its position implies the arc's "filled" portion goes from the bottom-left, all the way up and across the top, to the top-right — effectively the full arc is filled.
- Inside the dial, centered: the reading **`27°`** in serif, ~60–68 px, regular, color `#1A1A1A`. The degree symbol is a true superscript `°`, slightly elevated.
- No secondary label like "Target" or "Current" — just the number.

**Bottom row.** Inside the tile, bottom-left and bottom-right corners (~24 px inset):
- Bottom-left: a circular "−" (minus) button, 32 px diameter, white fill `#FFFFFF`, no border, thin black minus glyph centered.
- Bottom-right: a circular "+" button, identical styling, plus glyph.

No slider track, no presets, no schedule info.

### 6.2 Current Weather (large, bottom-left)

**Dimensions.** Same width as Thermostat (~380 px). Height ~240 px.

**Background.** `#F1EBDA` (pale butter), 24 px radius.

**Header row (top-left).**
- Small circular icon with a simple cloud/droplet outline inside, stroke `#2A2A2A`.
- Label "Current Weather", sans-serif 15–16 px, medium, `#2A2A2A`.

**Main readout (left side, below header).** Large serif number **`6°`** followed by **`/9°`** in the same line. The `6°` is the primary, larger (~60 px) weight; `/9°` is noticeably smaller (~28 px) and sits on the baseline next to it, separated by a slash. This communicates current / high (or current / feels-like).

**Sub-label.** Below the number, the word **`Cloudy`** in italic serif ~18 px or sans-serif 13 px, color `#6E6E6E`.

**Illustration (right side).** A soft, photorealistic 3D-rendered cloud with a warm sun glow peeking from behind its lower-right edge. The cloud is fluffy, white with warm yellow highlights on the bottom where the sun hits. It is cropped so roughly two-thirds of the cloud sits inside the tile and it slightly overflows the bottom-right corner, feeling almost "placed" on the tile. This is the one decorative, photographic element in the tile.

### 6.3 Now Playing (top-right, spans the right area)

This is **not a tile with a background color** — it sits directly on the page's cream background and reads as a rich, clean media control.

**Layout.** Horizontal, roughly 540 × 140 px. Two halves:
- **Left:** a rounded-rectangle album-art thumbnail, ~120 × 120 px, corner radius ~16 px. The art shows a person in warm tones (orange/peach palette). A small round green **Spotify** logo badge sits at the top-right corner of the album art, overlapping slightly, ~24 px diameter.
- **Right:** text + transport controls, stacked vertically.

**Text block (top).**
- Line 1: track context / playlist name: `Sentimental Value`, italic serif, ~16 px, color `#6E6E6E`. Right-aligned with the rest of the text block (or left-aligned — the reference uses left).
- Line 2: **`Hana Rani — Lighter and Lighter`**, serif, ~22 px, regular, `#1A1A1A`. Artist and track separated by an em dash with spaces.

**Transport row (bottom, 5 glyphs).** Thin-line icons, ~20 px, color `#1A1A1A`, evenly spaced:
1. **Shuffle** (two crossing arrows)
2. **Previous** (skip-back triangle with bar)
3. **Play** — the central button, a solid black filled circle ~52 px diameter with a small white triangular play glyph inside. This is visually the heaviest element in the row.
4. **Next** (skip-forward triangle with bar)
5. **Repeat** (two arrows forming a loop)

The central play button breaks the otherwise flat, line-icon aesthetic, anchoring the row.

### 6.4 Smart Kettle (middle, 2×2 grid, top-left of that grid)

**Dimensions.** ~220 × 220 px square.

**Background.** `#E9C9B4` (peach). 24 px radius.

**Header (top-left).**
- Line 1: **`Smart Kettle`**, sans-serif 15 px, medium, `#2A2A2A`.
- Line 2: **`MI Smart Kettle Pro`** (product model), italic serif, 12 px, `#6E6E6E`.

**Toggle (top-right).** A small pill-shape power toggle, currently in the **off / standby** state: dark pill (`#2A2A2A`) with a small circular indicator on the left side. ~36 × 18 px.

**Value.** Large serif **`67°`**, ~58 px, `#1A1A1A`, positioned roughly center-left of the tile.

**Sub-label.** Directly below the number, **`Cooling Down`**, sans-serif 12 px, `#6E6E6E`.

**Product photo.** A small, realistic photo of a white-and-silver electric kettle, sized ~90 × 90 px, placed at the bottom-right of the tile. It has a soft drop shadow. It slightly overlaps the tile's bottom-right corner area but stays within the rounded clip.

### 6.5 Vacuum Cleaner (middle, 2×2 grid, top-right of that grid)

**Dimensions.** ~260 × 220 px (slightly wider than the kettle tile).

**Background.** `#C9A987` (warm tan). 24 px radius.

**Header (top-left).**
- Line 1: **`Vacuum Cleaner`**, sans-serif 15 px, medium, `#2A2A2A`.
- Line 2: **`MI Robot Vacuum S20`**, italic serif, 12 px, `#6E6E6E`.

**Toggle (top-right).** Pill toggle in the **on** state: white pill (`#FFFFFF`) with the circular thumb on the right side. ~36 × 18 px.

**Value.** Large serif **`19%`**, ~56 px, `#1A1A1A`, center-left.

**Sub-label.** **`Battery: Low`**, sans-serif 12 px, `#6E6E6E`. The word "Low" is in a slightly darker/warmer tone than the rest, or optionally in red — in the reference it reads as standard secondary text.

**Product photo.** A top-down view of a circular black robot vacuum with a central camera/sensor disk, ~110 × 110 px, bottom-right of the tile, with a soft shadow. Partially clipped by the bottom edge so it feels embedded.

### 6.6 Wi-Fi / Living Room Toggle (middle, 2×2 grid, bottom-left)

**Dimensions.** ~220 × 160 px (shorter than the kettle tile above it).

**Background.** `#E6E8DE` (pale sage). 24 px radius.

**Header (top-left).**
- Line 1: **`On`**, sans-serif 14 px, medium, `#2A2A2A`.
- Line 2: **`Living room`**, sans-serif 12 px, `#6E6E6E`.

**Toggle (top-right).** Pill toggle in **on** state, **green fill** (`#3FB950`) with white circular thumb on the right. ~36 × 18 px.

**Wi-Fi glyph.** A large Wi-Fi "fan" icon (three arcs + dot) centered in the lower half of the tile, ~72 px wide, color `#8FB77A` (muted green). The arcs are thick and rounded.

### 6.7 Live Camera (middle, 2×2 grid, bottom-right)

**Dimensions.** Same as the Vacuum tile (~260 × 160 px).

**Background.** Full-bleed photograph — no tint, no color wash. The image shows an interior scene (looks like a sunlit living room with wood framing and greenery). 24 px radius, corners clipped.

**Badge.** Top-left corner, inset ~12 px: a small rounded-rectangle **`LIVE`** badge. Red background (`#E4442B`), white text, sans-serif 11 px, bold, uppercase, ~12 px padding. The corner radius of the badge is ~6 px.

No other overlay text, no timestamp, no controls. The photo itself communicates "live feed."

---

## 7. Icon Style Guide

All line icons share these traits:
- Stroke weight ~1.75 px at 16 px icon size.
- Round caps, round joins.
- No fills (except the play button and the Wi-Fi tile glyph, which are filled shapes).
- Color `#2A2A2A` for navigation and `#1A1A1A` for transport controls.

**Specific glyphs referenced:**
- **Back arrow (Main):** simple left-pointing arrow, ~14 px wide.
- **Smart Home icon:** a rounded square with a small inner shape (a stylized house or grid).
- **EV Charging icon:** a circle containing a lightning bolt or a plug-and-cord.
- **Messages icon:** two stacked rounded rectangles (suggesting chat bubbles).
- **Thermostat icon (in card header):** three short wavy horizontal lines stacked vertically.
- **Weather icon (in card header):** circle outline enclosing a small cloud+drop.
- **Status-bar Wi-Fi:** solid black fan, three concentric arcs + base dot.

---

## 8. Toggle Component Spec

Used in Smart Kettle, Vacuum, and Living Room tiles. Reusable:

- Shape: pill / stadium, width 36 px, height 18 px, fully rounded.
- **Off state:** track fill `#2A2A2A` (near-black), thumb (`#F5F2EC`, 14 px circle) at left, 2 px inset.
- **On (neutral) state:** track fill `#FFFFFF`, thumb `#2A2A2A` or `#F5F2EC` at right. Used on the Vacuum tile.
- **On (active accent) state:** track fill `#3FB950` (green), thumb white at right. Used on the Living Room tile.
- No text inside the toggle. No outline.

This three-mode toggle convention is deliberate: the neutral-on state is used for devices where "on" is just "currently running"; the green-on state is reserved for an explicit user-enabled connection like Wi-Fi.

---

## 9. Recreation Notes for an LLM

When generating code from this spec:

1. **Use a grid, not absolute positioning.** CSS Grid with 12 columns works well; map the sidebar to columns 1–1, the left main column to 2–6, and the right main column to 7–12. Use `grid-template-rows` to stack the Now Playing row above the 2×2 small-tile grid.
2. **Tiles are the unit.** Build a single `.tile` class with the corner radius, padding (24 px), and flex column layout. Vary only background color and content per instance.
3. **Honor the negative space.** The design reads "calm" because tiles are large, type is large, and empty space is deliberate. Do not shrink padding to fit more content.
4. **Serif for numbers, sans for labels.** This pairing is the single strongest personality trait of the UI. Applying a sans-serif everywhere ruins the editorial feel.
5. **Photos over illustrations.** The kettle, vacuum, cloud, and album art are all photographic or 3D-rendered with soft shadows. Do not substitute flat vector illustrations — the material contrast with the flat cards is the point.
6. **Restraint with color.** Only four tile colors appear (cream, butter, peach, tan, sage). Green and red are used once each as accents. Avoid adding any new hues.
7. **No borders.** The design uses color fills and radius, never strokes, to separate tiles.
8. **Mobile/narrow adaptation (if needed).** Collapse the sidebar into a bottom tab bar, stack the main column as a single vertical scroll, keep the Now Playing bar sticky-top, and let the 2×2 small-tile grid become 2 columns × N rows.

---

## 10. Suggested Asset List

If building from scratch, the following assets are needed:

- 1× cloud PNG with transparent background and warm sun highlight.
- 1× kettle product photo, white/silver, on transparent background.
- 1× robot vacuum top-down photo, black, on transparent background.
- 1× album-art image (portrait/person, warm palette).
- 1× interior photo for the Live camera tile.
- Spotify logo SVG (solid green circle variant).
- Custom or Material/Phosphor icon set for nav and transport glyphs.
- Two font files: a serif (Cormorant/Playfair/DM Serif) and a sans-serif (Inter/SF Pro).

---

## 11. Minimal HTML/CSS Starter (for reference)

```html
<div class="app">
  <aside class="sidebar">…</aside>
  <main>
    <header class="statusbar">…</header>
    <h1>Smart Home</h1>
    <section class="grid">
      <div class="tile thermostat">…</div>
      <div class="tile weather">…</div>
      <div class="nowplaying">…</div>
      <div class="tile kettle">…</div>
      <div class="tile vacuum">…</div>
      <div class="tile wifi">…</div>
      <div class="tile livecam">…</div>
    </section>
  </main>
</div>
```

```css
:root{
  --bg:#F5F2EC; --ink:#1A1A1A; --ink-2:#6E6E6E;
  --c-therm:#EDEAE4; --c-weather:#F1EBDA;
  --c-kettle:#E9C9B4; --c-vacuum:#C9A987;
  --c-wifi:#E6E8DE; --accent:#3FB950; --live:#E4442B;
  --r:24px;
}
body{background:var(--bg);font-family:Inter,system-ui;color:var(--ink);}
h1{font-family:"DM Serif Display",serif;font-size:4rem;font-weight:400;}
.tile{border-radius:var(--r);padding:24px;}
.thermostat{background:var(--c-therm);}
.weather{background:var(--c-weather);}
.kettle{background:var(--c-kettle);}
.vacuum{background:var(--c-vacuum);}
.wifi{background:var(--c-wifi);}
```

---

**End of spec.** A faithful recreation following every section above should be visually indistinguishable from the reference at tablet resolution. Deviations in the exact shade of cream or peach (±5% lightness) are acceptable; deviations in typography pairing, corner radius, or tile layout are not.
