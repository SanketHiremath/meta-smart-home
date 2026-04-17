#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

win = Gtk.Window(title="Smart Home")
win.fullscreen()
win.connect("destroy", Gtk.main_quit)

lbl = Gtk.Label(label="Hello World")
win.add(lbl)

win.show_all()
Gtk.main()
