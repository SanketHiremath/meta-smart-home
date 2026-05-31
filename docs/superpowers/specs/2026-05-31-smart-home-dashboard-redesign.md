# Smart Home Dashboard Redesign

**Date:** 2026-05-31  
**Target:** STM32MP157D-DK1 · 800×480 · OpenSTLinux / Weston / Wayland  
**File:** `meta-smart-home/recipes-apps/my-gtk-app/files/smart.py`

---

## Goals

Redesign the existing GTK3 dashboard from a static mockup into a live-data application:

1. Replace the thermostat hero with a **humidity hero** card fed by the Open-Meteo API.
2. Replace kettle/vacuum tiles with **feels-like temperature** and **UV index** tiles from the same API.
3. Show **real WiFi status** (SSID, signal strength, IP) in the WiFi tile.
4. Switch the overall visual theme to **Option C — Dark Mode Hero** (dark `#211d18` background, teal `#2ec4b6` accent).
5. Keep the music strip and bottom navigation as static UI elements.

---

## Layout (800×480)

```
┌─────────────────────────────────────────────────────────────┐
│ Header: "Smart Home"          📍 Indianapolis, IN    21:45  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  HERO: Humidity  ╭──────╮  62% RH                          │
│  ring dial       │  62  │  Indianapolis, Indiana            │
│  (72×72 px)      │  %RH │  ● Comfortable  · Updated 21:40  │
│                  ╰──────╯  Partly Cloudy  · Live every 20m  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Music strip (static): album art · track name · ⏮ ▶ ⏭     │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ 🌡 Temp      │ 🌬 Feels Like│ ☀ UV Index   │ ▲ WiFi        │
│  58°F        │  52°F        │  2.8  [bar]  │ Free-Wifi     │
│  Live        │  Live        │  Low         │ ▲▲▲  .142     │
├──────────────┴──────────────┴──────────────┴────────────────┤
│  ⌂ Home   ⚡ Energy   🌡 Climate   ✉ Alerts   ⚙ Settings   │
└─────────────────────────────────────────────────────────────┘
```

---

## Color Palette

| Token         | Hex       | Usage                          |
|---------------|-----------|--------------------------------|
| `BG`          | `#211d18` | Window background              |
| `CARD_DARK`   | `#2a2520` | Hero / music / tile surfaces   |
| `ACCENT`      | `#2ec4b6` | Ring arc, chips, WiFi, nav dot |
| `T_LIGHT`     | `#f5f2ee` | Primary text                   |
| `T_MID`       | `#8a8070` | Secondary text                 |
| `T_DIM`       | `#6a6460` | Tertiary / timestamps          |
| `TILE_WEATHER`   | `#1e2a1e` | Temperature tile bg         |
| `TILE_FEELSLIKE` | `#2a1e1a` | Feels-like tile bg          |
| `TILE_UV`        | `#2a2510` | UV index tile bg            |
| `TILE_WIFI`      | `#1a2020` | WiFi tile bg                |

---

## Data Sources

### Open-Meteo (no API key)

**Endpoint:**
```
https://api.open-meteo.com/v1/forecast
  ?latitude=39.7684
  &longitude=-86.1581
  &current=relativehumidity_2m,temperature_2m,apparent_temperature,uv_index,weathercode
  &temperature_unit=fahrenheit
  &timezone=America%2FIndiana%2FIndianapolis
```

**Fields consumed:**

| Field                  | Widget            |
|------------------------|-------------------|
| `relativehumidity_2m`  | Hero ring value   |
| `temperature_2m`       | Temperature tile  |
| `apparent_temperature` | Feels-like tile   |
| `uv_index`             | UV index tile     |
| `weathercode`          | Hero conditions label (mapped via WMO code table) |

**Poll interval:** 20 minutes (`GLib.timeout_add_seconds(1200, _fetch_weather)`)

**Threading:** fetch runs in a `threading.Thread` so the GTK main loop never blocks. Result is passed back to the main thread via `GLib.idle_add`.

**Error handling:** on network failure, retain last known values and append " (cached)" to the timestamp label.

### WiFi Status (board read)

| Data point    | Source                              | Refresh    |
|---------------|-------------------------------------|------------|
| SSID          | `wpa_cli -i wlan0 status`           | 30 seconds |
| Signal (dBm)  | `/proc/net/wireless` (match `wlan0` or `wlu1u3`) | 30 seconds |
| IP address    | `ip addr show wlan0` (regex `inet`) | 30 seconds |

**Note:** The board interface is currently named `wlu1u3` (altname `wlan0`). After the next flash with the `10-wlan-rename.link` file it will be permanently `wlan0`. The WiFi reader must try `wlan0` first, then fall back to the first wireless interface found in `/proc/net/wireless`.

Signal strength mapped to 1–4 bar display:
- ≥ −55 dBm → 4 bars
- ≥ −65 dBm → 3 bars
- ≥ −75 dBm → 2 bars
- < −75 dBm → 1 bar

On read failure (interface down), WiFi tile shows "No signal".

### Clock

Updated every 30 seconds via existing `GLib.timeout_add_seconds(30, _tick)`, extended to also refresh WiFi data on the same tick.

---

## Components

### `WeatherFetcher`

A plain class (not a GTK widget) responsible for:
- Constructing the Open-Meteo URL
- Fetching via `urllib.request` (no third-party deps)
- Parsing the JSON response
- Calling a callback with a `WeatherData` dataclass on success, or `None` on failure

### `WeatherData` (dataclass)

```python
@dataclass
class WeatherData:
    humidity: int        # %
    temperature: float   # °F
    feels_like: float    # °F
    uv_index: float
    condition: str       # human-readable from WMO code
    fetched_at: str      # "HH:MM" string
```

### `HumidityHero` (Gtk.Overlay)

Replaces `ThermostatCard`. Draws the ring arc via Cairo (same technique as `DialWidget`). Exposes `update(data: WeatherData)` to refresh labels without rebuilding the widget.

### `WeatherTile` (Gtk.Overlay)

Reusable card for temperature, feels-like, and UV index tiles. Constructor takes `(label, color_bg, color_fg)`. Exposes `update(value: str, sub: str, chip: str)`.

### `WifiTile` (Gtk.Overlay)

Draws signal strength bars via Cairo. Exposes `update(ssid, bars, ip)`.

### `SmartHomeApp` (unchanged structure)

- On init: trigger first weather fetch immediately, schedule 20-minute repeats.
- `_tick()`: refresh clock + WiFi (every 30 s).
- `_on_weather(data)`: called via `GLib.idle_add` when fetch completes; updates hero + three weather tiles.

---

## WMO Weather Code → Condition String

A minimal lookup dict covering the codes Open-Meteo returns for `weathercode`:

| Codes     | String           |
|-----------|------------------|
| 0         | Clear Sky        |
| 1–3       | Partly Cloudy    |
| 45, 48    | Foggy            |
| 51–67     | Drizzle / Rain   |
| 71–77     | Snow             |
| 80–82     | Rain Showers     |
| 95–99     | Thunderstorm     |

---

## UV Index Gradient Bar

A `Gtk.DrawingArea` (height 4 px) filled with a left-to-right gradient:
- 0–2: green `#7ecb7e`
- 3–5: yellow `#e8c840`
- 6–7: orange `#e87040`
- 8+: red `#e05050`

Fill width = `(uv_index / 11) * bar_width`, clamped to bar width.

---

## Files Changed

| File | Change |
|------|--------|
| `recipes-apps/my-gtk-app/files/smart.py` | Full rewrite of UI and data layer |
| `recipes-apps/my-gtk-app/my-gtk-app.bb` | Bump `PR` |

No new recipe dependencies — `urllib.request` and `threading` are stdlib; `subprocess` already available.

---

## Out of Scope

- Bottom nav pages (Energy, Climate, Alerts, Settings) — navigation buttons remain non-functional stubs.
- Music playback — strip stays as a static UI element.
- Persistent caching across reboots.
- HTTPS certificate pinning.
