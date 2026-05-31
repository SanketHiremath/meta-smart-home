# Smart Home Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite smart.py from a static mockup into a live-data dark-mode dashboard that pulls humidity/weather from Open-Meteo and real WiFi status from the board.

**Architecture:** Single Python file (`smart.py`) built in three layers — pure data functions at the top (testable without GTK), GTK widgets in the middle, `SmartHomeApp` wiring at the bottom. A daemon thread fetches Open-Meteo every 20 minutes and delivers results via `GLib.idle_add`; WiFi is read via subprocess on the 30-second clock tick.

**Tech Stack:** Python 3, GTK3/PyGObject, Cairo, PangoCairo, `urllib.request`, `threading`, `subprocess`, `GLib`, pytest

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `recipes-apps/my-gtk-app/files/smart.py` | Rewrite | Full dashboard — data layer + GTK widgets + app wiring |
| `recipes-apps/my-gtk-app/files/test_smart.py` | Create | Unit tests for pure data functions (dev-only, not deployed) |
| `recipes-apps/my-gtk-app/my-gtk-app.bb` | Modify | Bump `PR` after rewrite |

All commands run from `/home/sanky/Projects/yocto_proj/` unless noted.

---

## Task 1: Scaffold smart.py — imports, kiosk detection, palette

**Files:**
- Rewrite: `meta-smart-home/recipes-apps/my-gtk-app/files/smart.py`

- [ ] **Step 1: Overwrite smart.py with the new scaffold**

```python
#!/usr/bin/env python3
"""Smart Home Dashboard — STM32MP157D-DK1 · 800×480 · Wayland/Weston"""

import math, sys, platform, argparse, threading, datetime, json, re, subprocess
from dataclasses import dataclass, field
from urllib import request as _urllib_request

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo
import cairo

# ── Kiosk detection ────────────────────────────────────────────────────────────
def _detect_kiosk():
    import os
    if platform.system() == "Windows":
        return False
    if platform.system() == "Linux" and not os.environ.get("DISPLAY", ""):
        return True
    return False

KIOSK = False       # overridden in __main__ block
IS_WINDOWS = platform.system() == "Windows"

# ── Palette (dark mode — Option C) ────────────────────────────────────────────
BG             = (0.129, 0.114, 0.094)   # #211d18  window bg
CARD_DARK      = (0.165, 0.145, 0.125)   # #2a2520  hero/music/tiles
ACCENT         = (0.180, 0.769, 0.714)   # #2ec4b6  teal accent
T_LIGHT        = (0.961, 0.949, 0.933)   # #f5f2ee  primary text
T_MID          = (0.541, 0.502, 0.439)   # #8a8070  secondary text
T_DIM          = (0.416, 0.392, 0.376)   # #6a6460  timestamps/tertiary
TILE_WEATHER   = (0.118, 0.165, 0.118)   # #1e2a1e  temperature tile
TILE_FEELSLIKE = (0.165, 0.118, 0.102)   # #2a1e1a  feels-like tile
TILE_UV        = (0.165, 0.145, 0.063)   # #2a2510  UV index tile
TILE_WIFI      = (0.102, 0.125, 0.125)   # #1a2020  WiFi tile
NAV_BG         = (0.102, 0.086, 0.063)   # #1a1610  bottom nav
PAD            = 6                        # grid gap px
```

- [ ] **Step 2: Syntax check**

```bash
python3 -m py_compile meta-smart-home/recipes-apps/my-gtk-app/files/smart.py && echo OK
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git -C meta-smart-home add recipes-apps/my-gtk-app/files/smart.py
git -C meta-smart-home commit -m "feat: scaffold dark-mode smart.py — imports + palette"
```

---

## Task 2: Pure data functions + test file

**Files:**
- Append: `meta-smart-home/recipes-apps/my-gtk-app/files/smart.py`
- Create: `meta-smart-home/recipes-apps/my-gtk-app/files/test_smart.py`

- [ ] **Step 1: Create test_smart.py with GTK mocks**

```python
# test_smart.py — dev-only, NOT deployed to board (not in SRC_URI)
import sys, os, json
from unittest.mock import MagicMock, patch
import importlib.util

# Mock all GTK/Cairo dependencies before importing smart.py
for _mod in ["gi", "gi.repository", "gi.repository.Gtk", "gi.repository.Gdk",
             "gi.repository.GLib", "gi.repository.Pango",
             "gi.repository.PangoCairo", "cairo"]:
    sys.modules[_mod] = MagicMock()
_gi = MagicMock()
_gi.require_version = MagicMock()
sys.modules["gi"] = _gi

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "smart", os.path.join(_here, "smart.py"))
smart = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(smart)
```

- [ ] **Step 2: Run test file — confirm it loads without error**

```bash
cd meta-smart-home/recipes-apps/my-gtk-app/files && python3 -m pytest test_smart.py -v
```
Expected: `no tests ran` (0 collected, no errors)

- [ ] **Step 3: Append WMO lookup + parse functions to smart.py**

```python

# ── WMO weather code → condition string ────────────────────────────────────────
_WMO = {
    0: "Clear Sky",
    1: "Partly Cloudy", 2: "Partly Cloudy", 3: "Partly Cloudy",
    45: "Foggy", 48: "Foggy",
    51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
    56: "Freezing Drizzle", 57: "Freezing Drizzle",
    61: "Rain", 63: "Rain", 65: "Heavy Rain",
    66: "Freezing Rain", 67: "Freezing Rain",
    71: "Snow", 73: "Snow", 75: "Heavy Snow", 77: "Snow Grains",
    80: "Rain Showers", 81: "Rain Showers", 82: "Heavy Showers",
    85: "Snow Showers", 86: "Snow Showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ Hail", 99: "Thunderstorm w/ Hail",
}

def wmo_condition(code):
    return _WMO.get(code, "Unknown")


@dataclass
class WeatherData:
    humidity:    int
    temperature: float   # °F
    feels_like:  float   # °F
    uv_index:    float
    condition:   str
    fetched_at:  str     # "HH:MM"
    cached:      bool = False


def parse_weather_response(raw):
    """Parse an Open-Meteo /v1/forecast JSON dict into WeatherData."""
    c = raw["current"]
    return WeatherData(
        humidity    = int(c["relativehumidity_2m"]),
        temperature = float(c["temperature_2m"]),
        feels_like  = float(c["apparent_temperature"]),
        uv_index    = float(c["uv_index"]),
        condition   = wmo_condition(int(c["weathercode"])),
        fetched_at  = datetime.datetime.now().strftime("%H:%M"),
    )


def parse_signal_bars(proc_line):
    """Parse a /proc/net/wireless data line → 1–4 bars (0 on bad input)."""
    try:
        parts = proc_line.split()
        dbm = float(parts[3].rstrip("."))
        if dbm >= -55: return 4
        if dbm >= -65: return 3
        if dbm >= -75: return 2
        return 1
    except (IndexError, ValueError):
        return 0


def parse_ssid_from_wpa_cli(output):
    """Extract SSID from wpa_cli status output."""
    for line in output.splitlines():
        if line.startswith("ssid="):
            return line.split("=", 1)[1].strip()
    return "No signal"


def parse_ip_from_addr(output):
    """Extract first IPv4 address from `ip addr show` output."""
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", output)
    return m.group(1) if m else ""
```

- [ ] **Step 4: Write tests for all parse functions in test_smart.py**

Append to `test_smart.py`:

```python

def test_wmo_condition_known():
    assert smart.wmo_condition(0)  == "Clear Sky"
    assert smart.wmo_condition(1)  == "Partly Cloudy"
    assert smart.wmo_condition(3)  == "Partly Cloudy"
    assert smart.wmo_condition(45) == "Foggy"
    assert smart.wmo_condition(61) == "Rain"
    assert smart.wmo_condition(71) == "Snow"
    assert smart.wmo_condition(80) == "Rain Showers"
    assert smart.wmo_condition(95) == "Thunderstorm"

def test_wmo_condition_unknown():
    assert smart.wmo_condition(999) == "Unknown"

def test_parse_weather_response():
    raw = {"current": {
        "relativehumidity_2m": 62,
        "temperature_2m": 58.1,
        "apparent_temperature": 52.3,
        "uv_index": 2.8,
        "weathercode": 1,
    }}
    d = smart.parse_weather_response(raw)
    assert d.humidity    == 62
    assert d.temperature == 58.1
    assert d.feels_like  == 52.3
    assert d.uv_index    == 2.8
    assert d.condition   == "Partly Cloudy"
    assert d.cached      == False

def test_parse_signal_bars():
    assert smart.parse_signal_bars(" wlan0: 0000   60.  -52.  -256.") == 4  # >= -55
    assert smart.parse_signal_bars(" wlan0: 0000   45.  -60.  -256.") == 3  # >= -65
    assert smart.parse_signal_bars(" wlan0: 0000   25.  -70.  -256.") == 2  # >= -75
    assert smart.parse_signal_bars(" wlan0: 0000   10.  -80.  -256.") == 1  # <  -75

def test_parse_signal_bars_bad_input():
    assert smart.parse_signal_bars("garbage") == 0

def test_parse_ssid_found():
    out = "bssid=aa:bb:cc:dd:ee:ff\nssid=Free-Wifi\nid=0\n"
    assert smart.parse_ssid_from_wpa_cli(out) == "Free-Wifi"

def test_parse_ssid_not_found():
    assert smart.parse_ssid_from_wpa_cli("wpa_state=DISCONNECTED\n") == "No signal"

def test_parse_ip_found():
    out = "3: wlan0: <BROADCAST>\n    inet 192.168.0.142/24 brd 192.168.0.255\n"
    assert smart.parse_ip_from_addr(out) == "192.168.0.142"

def test_parse_ip_not_found():
    assert smart.parse_ip_from_addr("no address here") == ""
```

- [ ] **Step 5: Run tests**

```bash
cd meta-smart-home/recipes-apps/my-gtk-app/files && python3 -m pytest test_smart.py -v
```
Expected: 11 tests collected, all PASS

- [ ] **Step 6: Commit**

```bash
git -C meta-smart-home add recipes-apps/my-gtk-app/files/smart.py \
                            recipes-apps/my-gtk-app/files/test_smart.py
git -C meta-smart-home commit -m "feat: add WMO lookup, weather/wifi parsers with tests"
```

---

## Task 3: WeatherFetcher + WiFi reader

**Files:**
- Append: `meta-smart-home/recipes-apps/my-gtk-app/files/smart.py`
- Append: `meta-smart-home/recipes-apps/my-gtk-app/files/test_smart.py`

- [ ] **Step 1: Write failing tests for WeatherFetcher**

Append to `test_smart.py`:

```python

def test_weather_fetcher_success():
    raw = {"current": {
        "relativehumidity_2m": 55,
        "temperature_2m": 62.0,
        "apparent_temperature": 57.0,
        "uv_index": 3.1,
        "weathercode": 0,
    }}
    results = []

    fetcher = smart.WeatherFetcher(lambda d: results.append(d))

    with patch("smart._urllib_request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(raw).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = mock_resp
        with patch.object(smart.GLib, "idle_add", side_effect=lambda fn, arg: fn(arg)):
            fetcher._fetch()

    assert len(results) == 1
    assert results[0].humidity  == 55
    assert results[0].condition == "Clear Sky"
    assert results[0].cached    == False


def test_weather_fetcher_network_error_no_cache():
    results = []
    fetcher = smart.WeatherFetcher(lambda d: results.append(d))

    with patch("smart._urllib_request.urlopen", side_effect=OSError("no network")):
        with patch.object(smart.GLib, "idle_add", side_effect=lambda fn, arg: fn(arg)):
            fetcher._fetch()

    assert results == [None]


def test_weather_fetcher_network_error_uses_cache():
    raw = {"current": {
        "relativehumidity_2m": 70, "temperature_2m": 50.0,
        "apparent_temperature": 45.0, "uv_index": 1.0, "weathercode": 3,
    }}
    results = []
    fetcher = smart.WeatherFetcher(lambda d: results.append(d))

    # First fetch succeeds — populates cache
    with patch("smart._urllib_request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(raw).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = mock_resp
        with patch.object(smart.GLib, "idle_add", side_effect=lambda fn, arg: fn(arg)):
            fetcher._fetch()

    # Second fetch fails — should return cached data
    with patch("smart._urllib_request.urlopen", side_effect=OSError("no network")):
        with patch.object(smart.GLib, "idle_add", side_effect=lambda fn, arg: fn(arg)):
            fetcher._fetch()

    assert len(results) == 2
    assert results[1].cached   == True
    assert results[1].humidity == 70
```

- [ ] **Step 2: Run — confirm tests FAIL**

```bash
cd meta-smart-home/recipes-apps/my-gtk-app/files && python3 -m pytest test_smart.py::test_weather_fetcher_success -v
```
Expected: `AttributeError: module 'smart' has no attribute 'WeatherFetcher'`

- [ ] **Step 3: Append WeatherFetcher + WiFi reader to smart.py**

```python

# ── Open-Meteo endpoint ────────────────────────────────────────────────────────
_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=39.7684&longitude=-86.1581"
    "&current=relativehumidity_2m,temperature_2m,apparent_temperature"
    ",uv_index,weathercode"
    "&temperature_unit=fahrenheit"
    "&timezone=America%2FIndiana%2FIndianapolis"
)


class WeatherFetcher:
    def __init__(self, callback):
        self._callback = callback   # callable(WeatherData | None)
        self._last = None

    def fetch_async(self):
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        try:
            with _urllib_request.urlopen(_METEO_URL, timeout=10) as resp:
                raw = json.loads(resp.read())
            data = parse_weather_response(raw)
            self._last = data
            GLib.idle_add(self._callback, data)
        except Exception:
            if self._last is not None:
                cached = WeatherData(
                    humidity    = self._last.humidity,
                    temperature = self._last.temperature,
                    feels_like  = self._last.feels_like,
                    uv_index    = self._last.uv_index,
                    condition   = self._last.condition,
                    fetched_at  = self._last.fetched_at,
                    cached      = True,
                )
                GLib.idle_add(self._callback, cached)
            else:
                GLib.idle_add(self._callback, None)


# ── WiFi reader ────────────────────────────────────────────────────────────────
def read_wifi_status():
    """Returns (ssid, bars 0-4, ip)."""
    return _wifi_ssid(), _wifi_bars(), _wifi_ip()


def _wifi_ssid():
    try:
        out = subprocess.check_output(
            ["wpa_cli", "-i", "wlan0", "status"],
            stderr=subprocess.DEVNULL, timeout=3, text=True,
        )
        return parse_ssid_from_wpa_cli(out)
    except Exception:
        return "No signal"


def _wifi_bars():
    try:
        with open("/proc/net/wireless") as f:
            for line in f:
                if "wlan0" in line or "wlu1u3" in line:
                    return parse_signal_bars(line)
    except Exception:
        pass
    return 0


def _wifi_ip():
    try:
        out = subprocess.check_output(
            ["ip", "addr", "show", "wlan0"],
            stderr=subprocess.DEVNULL, timeout=3, text=True,
        )
        return parse_ip_from_addr(out)
    except Exception:
        return ""
```

- [ ] **Step 4: Run all tests**

```bash
cd meta-smart-home/recipes-apps/my-gtk-app/files && python3 -m pytest test_smart.py -v
```
Expected: 14 tests collected, all PASS

- [ ] **Step 5: Commit**

```bash
git -C meta-smart-home add recipes-apps/my-gtk-app/files/smart.py \
                            recipes-apps/my-gtk-app/files/test_smart.py
git -C meta-smart-home commit -m "feat: add WeatherFetcher and WiFi reader"
```

---

## Task 4: GTK helpers + Card base + HumidityHero widget

**Files:**
- Append: `meta-smart-home/recipes-apps/my-gtk-app/files/smart.py`

- [ ] **Step 1: Append GTK helpers + Card to smart.py**

```python

# ── GTK helpers ────────────────────────────────────────────────────────────────
def _rgba(r, g, b, a=1.0):
    c = Gdk.RGBA(); c.red = r; c.green = g; c.blue = b; c.alpha = a; return c

def _css(widget, data):
    p = Gtk.CssProvider()
    p.load_from_data(data.encode())
    widget.get_style_context().add_provider(
        p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

def lbl(text, size=11, bold=False, color=None, wrap=False, xalign=0.0):
    l = Gtk.Label(label=text)
    l.set_xalign(xalign)
    l.modify_font(Pango.FontDescription(
        "Sans {} {}".format("Bold" if bold else "Regular", size)))
    l.override_color(Gtk.StateFlags.NORMAL, _rgba(*(color or T_LIGHT)))
    if wrap:
        l.set_line_wrap(True)
        l.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    return l

def _vbox(mt=8, mb=8, ml=10, mr=10, sp=4):
    b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=sp)
    b.set_margin_top(mt); b.set_margin_bottom(mb)
    b.set_margin_start(ml); b.set_margin_end(mr)
    return b

def _hbox(sp=6):
    return Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=sp)


class Card(Gtk.DrawingArea):
    """Rounded dark rectangle with soft drop-shadow, used as Overlay base."""
    RADIUS = 12

    def __init__(self, bg=CARD_DARK):
        super().__init__()
        self._bg = bg
        self.connect("draw", self._draw)

    def _rrect(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x+w-r, y+r,   r, -math.pi/2,  0)
        cr.arc(x+w-r, y+h-r, r,  0,           math.pi/2)
        cr.arc(x+r,   y+h-r, r,  math.pi/2,   math.pi)
        cr.arc(x+r,   y+r,   r,  math.pi,    -math.pi/2)
        cr.close_path()

    def _draw(self, w, cr):
        W = w.get_allocated_width()
        H = w.get_allocated_height()
        r = self.RADIUS
        for i in range(4, 0, -1):
            cr.set_source_rgba(0, 0, 0, 0.03 * i)
            self._rrect(cr, 1, 1+i, W-2, H-3, r)
            cr.fill()
        cr.set_source_rgb(*self._bg)
        self._rrect(cr, 1, 1, W-2, H-3, r)
        cr.fill()


def overlay_card(bg=CARD_DARK, child=None):
    ov = Gtk.Overlay()
    ov.add(Card(bg))
    if child:
        ov.add_overlay(child)
        ov.set_overlay_pass_through(child, True)
    return ov
```

- [ ] **Step 2: Append HumidityHero to smart.py**

```python

class _RingArc(Gtk.DrawingArea):
    """Teal ring arc showing humidity %. Draws value text in the centre."""
    def __init__(self, value=62, size=80):
        super().__init__()
        self.value = value
        self.set_size_request(size, size)
        self.connect("draw", self._draw)

    def _draw(self, w, cr):
        W = w.get_allocated_width()
        H = w.get_allocated_height()
        cx, cy = W / 2, H / 2
        R  = min(W, H) / 2 - 8
        a0 = math.pi * 0.75
        a1 = math.pi * 2.25
        av = a0 + (self.value / 100.0) * (a1 - a0)

        cr.set_line_width(6)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        cr.set_source_rgba(0.25, 0.22, 0.20, 1)   # track
        cr.arc(cx, cy, R, a0, a1); cr.stroke()

        cr.set_source_rgb(*ACCENT)                  # filled arc
        cr.arc(cx, cy, R, a0, av); cr.stroke()

        layout = w.create_pango_layout(str(self.value))
        layout.set_font_description(Pango.FontDescription("Sans Bold 18"))
        lw, lh = layout.get_pixel_size()
        cr.set_source_rgb(*T_LIGHT)
        cr.move_to(cx - lw / 2, cy - lh / 2)
        PangoCairo.show_layout(cr, layout)


class HumidityHero(Gtk.Overlay):
    """Hero card — humidity ring arc + condition/timestamp labels."""

    def __init__(self):
        super().__init__()
        self._ring  = _RingArc(62)
        self._cond  = lbl("–––",              10, color=T_LIGHT)
        self._tag   = lbl("",                  9, color=ACCENT)
        self._stamp = lbl("Updating…",         8, color=T_DIM)

        outer = _hbox(12)
        outer.set_margin_start(14); outer.set_margin_end(14)
        outer.set_margin_top(8);    outer.set_margin_bottom(8)

        # Left — ring + "% RH" label
        ring_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        ring_col.set_valign(Gtk.Align.CENTER)
        pct = lbl("% RH", 8, color=ACCENT)
        pct.set_halign(Gtk.Align.CENTER)
        ring_col.pack_start(self._ring, False, False, 0)
        ring_col.pack_start(pct,        False, False, 0)
        outer.pack_start(ring_col, False, False, 0)

        # Right — title + location + condition + tag/stamp row
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        info.set_valign(Gtk.Align.CENTER)
        info.pack_start(lbl("Humidity", 14, bold=True, color=T_LIGHT), False, False, 0)
        info.pack_start(lbl("Indianapolis, IN", 9, color=T_DIM),       False, False, 0)
        info.pack_start(self._cond,                                      False, False, 0)
        row = _hbox(8)
        row.pack_start(self._tag,   False, False, 0)
        row.pack_start(self._stamp, False, False, 0)
        info.pack_start(row, False, False, 0)
        outer.pack_start(info, True, True, 0)

        self.add(Card(CARD_DARK))
        self.add_overlay(outer)
        self.set_overlay_pass_through(outer, True)

    def update(self, data):
        if data is None:
            self._stamp.set_text("Network error")
            return
        self._ring.value = data.humidity
        self._ring.queue_draw()
        self._cond.set_text(data.condition)
        suffix = "  (cached)" if data.cached else ""
        self._stamp.set_text("Updated {}{}".format(data.fetched_at, suffix))
        h = data.humidity
        if h < 30:
            tag, col = "● Dry",          (0.88, 0.75, 0.40)
        elif h < 60:
            tag, col = "● Comfortable",  ACCENT
        else:
            tag, col = "● Humid",        (0.88, 0.50, 0.40)
        self._tag.set_text(tag)
        self._tag.override_color(Gtk.StateFlags.NORMAL, _rgba(*col))
```

- [ ] **Step 3: Syntax check**

```bash
python3 -m py_compile meta-smart-home/recipes-apps/my-gtk-app/files/smart.py && echo OK
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git -C meta-smart-home add recipes-apps/my-gtk-app/files/smart.py
git -C meta-smart-home commit -m "feat: add Card base and HumidityHero widget"
```

---

## Task 5: WeatherTile + WifiTile widgets

**Files:**
- Append: `meta-smart-home/recipes-apps/my-gtk-app/files/smart.py`

- [ ] **Step 1: Append WeatherTile to smart.py**

```python

class WeatherTile(Gtk.Overlay):
    """Reusable data tile — temperature, feels-like, or UV index."""

    def __init__(self, icon, label, bg, fg):
        super().__init__()
        box = _vbox(mt=8, mb=8, ml=9, mr=9, sp=2)

        hdr = _hbox(4)
        hdr.pack_start(lbl("{} {}".format(icon, label), 8,
                           color=(fg[0], fg[1], fg[2], 0.55)), False, False, 0)
        self._chip = lbl("", 7, color=fg)
        self._chip.set_halign(Gtk.Align.END)
        hdr.pack_end(self._chip, False, False, 0)
        box.pack_start(hdr, False, False, 0)

        self._value = lbl("–", 22, bold=True, color=fg)
        box.pack_start(self._value, True, True, 0)

        self._sub = lbl("", 8, color=T_DIM)
        box.pack_start(self._sub, False, False, 0)

        self._uv_da    = Gtk.DrawingArea()
        self._uv_da.set_size_request(-1, 5)
        self._uv_da.connect("draw", self._draw_uv_bar)
        self._uv_val   = 0.0
        self._show_bar = False
        box.pack_start(self._uv_da, False, False, 0)

        self.add(Card(bg))
        self.add_overlay(box)
        self.set_overlay_pass_through(box, True)

    def _draw_uv_bar(self, w, cr):
        if not self._show_bar:
            return
        W = w.get_allocated_width()
        H = w.get_allocated_height()
        cr.set_source_rgba(0.25, 0.25, 0.25, 0.5)
        cr.rectangle(0, 1, W, H - 2); cr.fill()
        fill_w = min(W, int((self._uv_val / 11.0) * W))
        if fill_w > 0:
            grad = cairo.LinearGradient(0, 0, W, 0)
            grad.add_color_stop_rgb(0.00, 0.494, 0.796, 0.494)  # green
            grad.add_color_stop_rgb(0.36, 0.910, 0.784, 0.251)  # yellow
            grad.add_color_stop_rgb(0.64, 0.910, 0.439, 0.251)  # orange
            grad.add_color_stop_rgb(1.00, 0.878, 0.314, 0.314)  # red
            cr.set_source(grad)
            cr.rectangle(0, 1, fill_w, H - 2); cr.fill()

    def enable_uv_bar(self):
        self._show_bar = True

    def update(self, value, sub, chip, uv_val=0.0):
        self._value.set_text(value)
        self._sub.set_text(sub)
        self._chip.set_text(chip)
        self._uv_val = uv_val
        if self._show_bar:
            self._uv_da.queue_draw()
```

- [ ] **Step 2: Append WifiTile to smart.py**

```python

class _SignalBars(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.bars = 0
        self.set_size_request(44, 16)
        self.connect("draw", self._draw)

    def _draw(self, w, cr):
        for i, h in enumerate([4, 7, 10, 14]):
            x = 2 + i * 10
            if i < self.bars:
                cr.set_source_rgb(*ACCENT)
            else:
                cr.set_source_rgba(*ACCENT, 0.2)
            cr.rectangle(x, 16 - h, 7, h)
            cr.fill()


class WifiTile(Gtk.Overlay):
    def __init__(self):
        super().__init__()
        box = _vbox(mt=8, mb=8, ml=9, mr=9, sp=2)

        hdr = _hbox(4)
        hdr.pack_start(lbl("▲ WiFi", 8,
                           color=(TILE_WIFI[0]+0.3, TILE_WIFI[1]+0.4, TILE_WIFI[2]+0.4, 0.7)),
                       False, False, 0)
        self._chip = lbl("On", 7, color=ACCENT)
        self._chip.set_halign(Gtk.Align.END)
        hdr.pack_end(self._chip, False, False, 0)
        box.pack_start(hdr, False, False, 0)

        self._ssid = lbl("–", 13, bold=True, color=ACCENT)
        box.pack_start(self._ssid, True, True, 0)

        self._bars = _SignalBars()
        box.pack_start(self._bars, False, False, 0)

        self._ip = lbl("", 8, color=T_DIM)
        box.pack_start(self._ip, False, False, 0)

        self.add(Card(TILE_WIFI))
        self.add_overlay(box)
        self.set_overlay_pass_through(box, True)

    def update(self, ssid, bars, ip):
        self._ssid.set_text(ssid)
        self._bars.bars = bars
        self._bars.queue_draw()
        self._ip.set_text(ip)
        self._chip.set_text("On" if bars > 0 else "Off")
```

- [ ] **Step 3: Syntax check**

```bash
python3 -m py_compile meta-smart-home/recipes-apps/my-gtk-app/files/smart.py && echo OK
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git -C meta-smart-home add recipes-apps/my-gtk-app/files/smart.py
git -C meta-smart-home commit -m "feat: add WeatherTile and WifiTile widgets"
```

---

## Task 6: Static UI — music strip + bottom nav

**Files:**
- Append: `meta-smart-home/recipes-apps/my-gtk-app/files/smart.py`

- [ ] **Step 1: Append make_music_strip() and make_bottom_nav() to smart.py**

```python

# ── Music strip (static) ───────────────────────────────────────────────────────
def make_music_strip():
    box = _hbox(10)
    box.set_margin_start(12); box.set_margin_end(12)
    box.set_margin_top(6);    box.set_margin_bottom(6)

    art = Gtk.DrawingArea()
    art.set_size_request(36, 36)
    def _draw_art(w, cr):
        cr.set_source_rgb(0.22, 0.28, 0.20); cr.arc(18, 18, 18, 0, 2*math.pi); cr.fill()
        cr.set_source_rgb(0.15, 0.20, 0.14); cr.arc(18, 18,  8, 0, 2*math.pi); cr.fill()
        cr.set_source_rgb(0.22, 0.28, 0.20); cr.arc(18, 18,  3, 0, 2*math.pi); cr.fill()
        cr.set_source_rgba(1, 1, 1, 0.10);   cr.arc(18, 18, 13, 0, 2*math.pi); cr.stroke()
    art.connect("draw", _draw_art)
    box.pack_start(art, False, False, 0)

    meta = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    meta.set_valign(Gtk.Align.CENTER)
    meta.pack_start(lbl("Sentimental Value", 8, color=T_DIM), False, False, 0)
    track = lbl("Hana Rani — Lighter and Lighter", 10, bold=True, wrap=True)
    track.set_max_width_chars(32)
    meta.pack_start(track, False, False, 0)
    prog = Gtk.DrawingArea(); prog.set_size_request(-1, 3)
    def _draw_prog(w, cr):
        W = w.get_allocated_width()
        cr.set_source_rgba(*T_DIM, 0.4); cr.rectangle(0, 0, W, 3); cr.fill()
        cr.set_source_rgb(*ACCENT);      cr.rectangle(0, 0, int(W*0.4), 3); cr.fill()
    prog.connect("draw", _draw_prog)
    meta.pack_start(prog, False, False, 2)
    box.pack_start(meta, True, True, 0)

    css_ctrl = """
        button { background:transparent; border:none; font-size:14px;
                 min-width:28px; min-height:28px; color:#8a8070; border-radius:50%; }
        button.play { background:#2ec4b6; color:#111; border-radius:50%; }
        button:hover { background:rgba(255,255,255,0.08); }
        button.play:hover { background:#3ad4c6; }
    """
    ctrl = _hbox(8)
    ctrl.set_valign(Gtk.Align.CENTER)
    for sym, cls in [("⏮", ""), ("▶", "play"), ("⏭", "")]:
        b = Gtk.Button(label=sym)
        _css(b, css_ctrl)
        if cls:
            b.get_style_context().add_class(cls)
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.set_sensitive(False)
        ctrl.pack_start(b, False, False, 0)
    box.pack_start(ctrl, False, False, 0)

    return overlay_card(CARD_DARK, box)


# ── Bottom navigation (static stubs) ──────────────────────────────────────────
def make_bottom_nav():
    bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    _css(bar, "* {{ background: rgb({},{},{}); }}".format(
        int(NAV_BG[0]*255), int(NAV_BG[1]*255), int(NAV_BG[2]*255)))

    for icon, name, active in [
        ("⌂", "Home",     True),
        ("⚡", "Energy",   False),
        ("🌡", "Climate",  False),
        ("✉",  "Alerts",   False),
        ("⚙",  "Settings", False),
    ]:
        col = ACCENT if active else T_DIM
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        inner.set_halign(Gtk.Align.CENTER)
        ic = Gtk.Label(label=icon)
        ic.modify_font(Pango.FontDescription("Sans 14"))
        ic.override_color(Gtk.StateFlags.NORMAL, _rgba(*col))
        nm = Gtk.Label(label=name)
        nm.modify_font(Pango.FontDescription("Sans 7"))
        nm.override_color(Gtk.StateFlags.NORMAL, _rgba(*col))
        inner.pack_start(ic, False, False, 0)
        inner.pack_start(nm, False, False, 0)
        btn = Gtk.Button()
        btn.add(inner)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_sensitive(False)
        _css(btn, """
            button { background:transparent; border:none; border-radius:8px;
                     padding:4px 6px; min-height:40px; }
        """)
        bar.pack_start(btn, True, True, 0)

    return bar
```

- [ ] **Step 2: Syntax check**

```bash
python3 -m py_compile meta-smart-home/recipes-apps/my-gtk-app/files/smart.py && echo OK
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git -C meta-smart-home add recipes-apps/my-gtk-app/files/smart.py
git -C meta-smart-home commit -m "feat: add music strip and bottom nav"
```

---

## Task 7: SmartHomeApp — layout, data scheduling, entry point

**Files:**
- Append: `meta-smart-home/recipes-apps/my-gtk-app/files/smart.py`

- [ ] **Step 1: Append SmartHomeApp + __main__ block to smart.py**

```python

# ── Main application window ────────────────────────────────────────────────────
class SmartHomeApp(Gtk.Window):

    def __init__(self):
        super().__init__(title="Smart Home")
        if KIOSK:
            self.set_decorated(False)
        else:
            self.set_default_size(800, 480)
            self.set_decorated(True)
            self.set_resizable(True)

        p = Gtk.CssProvider()
        p.load_from_data(
            "* {{ font-family: Sans; }} window {{ background-color: rgb({},{},{}); }}".format(
                int(BG[0]*255), int(BG[1]*255), int(BG[2]*255)
            ).encode()
        )
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event",
                     lambda w, e: Gtk.main_quit() if e.keyval == Gdk.KEY_Escape else None)

        self._build()
        if KIOSK:
            self.fullscreen()

        self._fetcher = WeatherFetcher(self._on_weather)
        self._fetcher.fetch_async()
        GLib.timeout_add_seconds(1200, self._poll_weather)  # every 20 min
        self._tick()
        GLib.timeout_add_seconds(30, self._tick)

    # ── Layout ──────────────────────────────────────────────────────────────
    def _build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.set_hexpand(True); root.set_vexpand(True)
        self.add(root)

        # Header
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hdr.set_margin_start(PAD*2); hdr.set_margin_end(PAD*2)
        hdr.set_margin_top(8);       hdr.set_margin_bottom(4)
        hdr.pack_start(lbl("Smart Home", 16, bold=True, color=T_LIGHT), True, True, 0)
        loc = lbl("📍 Indianapolis, IN", 9, color=ACCENT)
        _css(loc, "label {{ background: rgba({},{},{},0.12); border-radius:10px; padding:2px 8px; }}".format(
            int(ACCENT[0]*255), int(ACCENT[1]*255), int(ACCENT[2]*255)))
        self._clock_lbl = lbl("--:--", 11, color=T_MID)
        hdr.pack_end(self._clock_lbl, False, False, 0)
        hdr.pack_end(loc,             False, False, 8)
        root.pack_start(hdr, False, False, 0)

        # Hero
        self._hero = HumidityHero()
        self._hero.set_margin_start(PAD); self._hero.set_margin_end(PAD)
        self._hero.set_margin_bottom(PAD)
        root.pack_start(self._hero, False, False, 0)

        # Music strip
        music = make_music_strip()
        music.set_margin_start(PAD); music.set_margin_end(PAD)
        music.set_margin_bottom(PAD)
        root.pack_start(music, False, False, 0)

        # Tile grid
        grid = Gtk.Grid()
        grid.set_column_spacing(PAD)
        grid.set_margin_start(PAD); grid.set_margin_end(PAD)
        grid.set_margin_bottom(PAD)
        grid.set_column_homogeneous(True)
        grid.set_hexpand(True); grid.set_vexpand(True)

        self._tile_temp = WeatherTile("🌡", "Temperature", TILE_WEATHER,   (0.494, 0.796, 0.494))
        self._tile_feel = WeatherTile("🌬", "Feels Like",  TILE_FEELSLIKE, (0.878, 0.439, 0.314))
        self._tile_uv   = WeatherTile("☀",  "UV Index",    TILE_UV,        (0.910, 0.784, 0.251))
        self._tile_uv.enable_uv_bar()
        self._tile_wifi = WifiTile()

        for col, tile in enumerate([self._tile_temp, self._tile_feel,
                                     self._tile_uv,   self._tile_wifi]):
            tile.set_hexpand(True); tile.set_vexpand(True)
            grid.attach(tile, col, 0, 1, 1)

        root.pack_start(grid, True, True, 0)
        root.pack_start(make_bottom_nav(), False, False, 0)
        self.show_all()

    # ── Timers / callbacks ───────────────────────────────────────────────────
    def _tick(self):
        now = datetime.datetime.now()
        self._clock_lbl.set_text(now.strftime("%H:%M"))
        ssid, bars, ip = read_wifi_status()
        self._tile_wifi.update(ssid, bars, ip)
        return True

    def _poll_weather(self):
        self._fetcher.fetch_async()
        return True

    def _on_weather(self, data):
        self._hero.update(data)
        if data is None:
            return False
        self._tile_temp.update(
            value="{:.0f}°".format(data.temperature),
            sub="°F · Open-Meteo",
            chip="Live",
        )
        self._tile_feel.update(
            value="{:.0f}°".format(data.feels_like),
            sub="°F apparent",
            chip="Live",
        )
        uv = data.uv_index
        chip = ("Low" if uv < 3 else "Moderate" if uv < 6 else
                "High" if uv < 8 else "Very High")
        self._tile_uv.update(
            value="{:.1f}".format(uv),
            sub="Scale 0–11+",
            chip=chip,
            uv_val=uv,
        )
        return False  # GLib.idle_add one-shot


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description="Smart Home Dashboard")
    _group  = _parser.add_mutually_exclusive_group()
    _group.add_argument("--kiosk",    action="store_true",
                        help="Fullscreen, no decorations (auto on Weston)")
    _group.add_argument("--windowed", action="store_true",
                        help="Force windowed mode")
    _args = _parser.parse_args()

    if _args.kiosk:       KIOSK = True
    elif _args.windowed:  KIOSK = False
    else:                 KIOSK = _detect_kiosk()

    print("[smart_home] platform={}  kiosk={}".format(platform.system(), KIOSK))
    SmartHomeApp()
    Gtk.main()
```

- [ ] **Step 2: Syntax check**

```bash
python3 -m py_compile meta-smart-home/recipes-apps/my-gtk-app/files/smart.py && echo OK
```
Expected: `OK`

- [ ] **Step 3: Run all unit tests**

```bash
cd meta-smart-home/recipes-apps/my-gtk-app/files && python3 -m pytest test_smart.py -v
```
Expected: 14 tests collected, all PASS

- [ ] **Step 4: Visual test — run app on the host**

If GTK3 is not installed: `sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0`

```bash
python3 meta-smart-home/recipes-apps/my-gtk-app/files/smart.py --windowed
```

Expected:
- Window opens at 800×480, dark `#211d18` background
- Humidity hero visible (ring shows `62`, "Updating…" stamp)
- After a few seconds the ring updates with live Indianapolis humidity
- Temperature, feels-like, UV tiles update with real data
- WiFi tile shows "No signal" / 0 bars (running on host, not board)
- Music strip visible with progress bar
- Bottom nav visible with Home highlighted in teal
- Close with Escape or window X

- [ ] **Step 5: Commit**

```bash
git -C meta-smart-home add recipes-apps/my-gtk-app/files/smart.py
git -C meta-smart-home commit -m "feat: add SmartHomeApp — layout, data scheduling, entry point"
```

---

## Task 8: Bump PR + build

**Files:**
- Modify: `meta-smart-home/recipes-apps/my-gtk-app/my-gtk-app.bb`

- [ ] **Step 1: Bump PR**

In `meta-smart-home/recipes-apps/my-gtk-app/my-gtk-app.bb`, change:

```
PR = "r14"
```
to:
```
PR = "r15"
```

- [ ] **Step 2: Confirm test_smart.py is NOT in SRC_URI**

Verify `my-gtk-app.bb` SRC_URI lists only these three files:

```
file://smart.py
file://launch-my-gtk-app.sh
file://my-gtk-app.service
```

- [ ] **Step 3: Commit**

```bash
git -C meta-smart-home add recipes-apps/my-gtk-app/my-gtk-app.bb
git -C meta-smart-home commit -m "chore: bump PR to r15 for live-data dashboard"
```

- [ ] **Step 4: Clean build**

```bash
. ./poky/oe-init-build-env build-stm32mp1
bitbake -c cleansstate my-gtk-app && bitbake my-gtk-app
```
Expected: recipe builds cleanly, no missing file errors.

- [ ] **Step 5: Verify on board after flash**

```bash
# On the board via SSH (192.168.0.142):
journalctl -u my-gtk-app.service --no-pager | tail -5
```
Expected log line: `[smart_home] platform=Linux  kiosk=True`

Dashboard should appear on the HDMI display within ~10 seconds of boot, showing live humidity and weather data for Indianapolis once the WiFi connects.
