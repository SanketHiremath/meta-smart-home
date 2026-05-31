#!/usr/bin/env python3
"""Smart Home Dashboard — STM32MP157D-DK1 · 800×480 · Wayland/Weston"""

import math, sys, platform, argparse, threading, datetime, json, re, subprocess
from dataclasses import dataclass
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
