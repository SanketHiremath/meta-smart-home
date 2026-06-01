#!/usr/bin/env python3
"""Smart Home Dashboard — STM32MP157D-DK1 · 800×480 · Wayland/Weston"""

import math, sys, platform, argparse, threading, datetime, json, re, subprocess
from dataclasses import dataclass, replace as _dc_replace
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


def _replace_weather(data, **kwargs):
    return _dc_replace(data, **kwargs)


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
        self._lock = threading.Lock()

    def fetch_async(self):
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        try:
            with _urllib_request.urlopen(_METEO_URL, timeout=10) as resp:
                raw = json.loads(resp.read())
            data = parse_weather_response(raw)
            with self._lock:
                self._last = data
            GLib.idle_add(self._callback, data)
        except Exception:
            with self._lock:
                last = self._last
            if last is not None:
                cached = _replace_weather(last, cached=True)
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
                # wlu1u3 is the RTL8188ETV USB dongle name before the rename link takes effect
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
