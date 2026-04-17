#!/bin/sh
# Compute the correct XDG_RUNTIME_DIR for the weston user.
# weston.socket uses %t/wayland-0 which resolves to /run/user/<uid>/wayland-0.
WESTON_UID=$(id -u weston)
export XDG_RUNTIME_DIR=/run/user/$WESTON_UID
export WAYLAND_DISPLAY=wayland-0
export GDK_BACKEND=wayland

# Wait up to 30 s for Weston to create its socket before launching.
i=0
while [ $i -lt 30 ]; do
    [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ] && break
    sleep 1
    i=$((i + 1))
done

exec /usr/bin/python3 /opt/my-gtk-app/my_app.py
