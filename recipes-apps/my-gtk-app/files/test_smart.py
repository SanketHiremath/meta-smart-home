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
