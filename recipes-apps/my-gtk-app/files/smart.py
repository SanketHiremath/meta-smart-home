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
