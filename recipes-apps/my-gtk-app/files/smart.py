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
