#!/usr/bin/env python3
"""Native GTK fixture driver, also runnable against installed ARM64 runtime.

Run under Xvfb locally; in the installed VM use the service X display. Only an
explicit regular-file fixture is admitted. Native key events and button activation
exercise the dialog; target bytes, not screenshots, determine the result.
"""
import argparse
import ctypes
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import sys
import time
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--runtime', type=Path, default=Path(__file__).resolve().parents[1]/'runtime')
p.add_argument('--work', type=Path, required=True)
p.add_argument('--source', type=Path)
p.add_argument('--target', type=Path)
a = p.parse_args()
sys.path.insert(0, str(a.runtime))
from sv08_sd_reimage import Session, FileFixtureAdmission
from sv08_sd_reimage_ui import ReimageWindow
from gi.repository import Gtk, Gdk, GLib
if a.work.exists(): raise ValueError('Fresh disposable work required')
a.work.mkdir(parents=True)
source, target = a.source or a.work/'source', a.target or a.work/'target'
data = b'installed attended SD fixture\n'*4096
if a.source:
    assert source.read_bytes() == data, 'Prepared fixture source differs'
else: source.write_bytes(data)
if a.target:
    assert target.is_file() and target.stat().st_size == len(data)+512
else: target.write_bytes(b'x'*(len(data)+512))
old = target.read_bytes()
cfg = dict(source=str(source), target=str(target), size=len(data), sha256=hashlib.sha256(data).hexdigest())
results = []


def pump_until(condition):
    deadline = time.monotonic()+10
    while not condition():
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        if time.monotonic() > deadline: raise AssertionError('GTK deadline exceeded')
        time.sleep(.01)


def journey(answer, keyboard=False, refused=False):
    def factory():
        return Session(dict(cfg, sha256='0'*64) if refused else cfg, FileFixtureAdmission())
    window = ReimageWindow(factory); window.set_title('SV08 · Explicit disposable file fixture'); window.show_all()
    def respond():
        if not getattr(window, 'dialog', None): return True
        dialog = window.dialog
        if keyboard:
            widget = dialog.get_widget_for_response(Gtk.ResponseType.YES if answer == 'yes' else Gtk.ResponseType.NO)
            widget.grab_focus()
            # XTest injects actual keyboard events into the installed X display.
            x = ctypes.CDLL(ctypes.util.find_library('X11'))
            xt = ctypes.CDLL(ctypes.util.find_library('Xtst'))
            x.XOpenDisplay.restype = ctypes.c_void_p
            display = x.XOpenDisplay(None)
            if not display: raise AssertionError('No X display')
            x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            code = x.XKeysymToKeycode(display, Gdk.KEY_Escape if answer == 'escape' else Gdk.KEY_Return)
            xt.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
            xt.XTestFakeKeyEvent(display, code, 1, 0)
            xt.XTestFakeKeyEvent(display, code, 0, 0)
            x.XFlush.argtypes = [ctypes.c_void_p]; x.XFlush(display)
            x.XCloseDisplay.argtypes = [ctypes.c_void_p]; x.XCloseDisplay(display)
        elif answer == 'close': dialog.response(Gtk.ResponseType.DELETE_EVENT)
        else:
            widget = dialog.get_widget_for_response(Gtk.ResponseType.YES if answer == 'yes' else Gtk.ResponseType.NO)
            x = ctypes.CDLL(ctypes.util.find_library('X11'))
            xt = ctypes.CDLL(ctypes.util.find_library('Xtst'))
            x.XOpenDisplay.restype = ctypes.c_void_p
            display = x.XOpenDisplay(None)
            coords = widget.translate_coordinates(dialog, widget.get_allocated_width()//2, widget.get_allocated_height()//2)
            origin = dialog.get_window().get_origin()
            xt.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
            xt.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
            xt.XTestFakeMotionEvent(display, -1, origin[-2]+coords[0], origin[-1]+coords[1], 0)
            xt.XTestFakeButtonEvent(display, 1, 1, 0); xt.XTestFakeButtonEvent(display, 1, 0, 0)
            x.XFlush.argtypes = [ctypes.c_void_p]; x.XFlush(display)
            x.XCloseDisplay.argtypes = [ctypes.c_void_p]; x.XCloseDisplay(display)
        return False
    if not refused: GLib.timeout_add(20, respond)
    def deadline():
        if getattr(window, 'dialog', None): window.dialog.response(Gtk.ResponseType.CANCEL)
        return False
    timer = GLib.timeout_add_seconds(10, deadline)
    window.review_button.clicked()
    pump_until(lambda: not window.busy and ('No write' in window.message.get_text() or
                                           'readback matched' in window.message.get_text()))
    GLib.source_remove(timer)
    result = window.message.get_text()
    assert ('Refused' in result) if refused else ('readback matched' in result if answer == 'yes' else 'No write' in result), result
    window.refresh_button.clicked()
    window.destroy()
    results.append(dict(answer=answer, keyboard=keyboard, refused=refused, result=result))


journey('no', refused=True); assert target.read_bytes() == old
journey('no', keyboard=True); assert target.read_bytes() == old
journey('escape', keyboard=True); assert target.read_bytes() == old
journey('close'); assert target.read_bytes() == old
journey('no'); assert target.read_bytes() == old
journey('yes', keyboard=True); assert target.read_bytes() == data+old[len(data):]
journey('no'); assert target.read_bytes() == data+old[len(data):]  # relaunch does not write
journey('yes'); assert target.read_bytes() == data+old[len(data):]
report = dict(results=results, source_sha256=cfg['sha256'], target_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              runtime={n:hashlib.sha256((a.runtime/n).read_bytes()).hexdigest() for n in ('sv08_sd_reimage.py','sv08_sd_reimage_ui.py')},
              memory=Path('/proc/meminfo').read_text(), fixture_only=True)
(a.work/'run.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(dict(cases=len(results), fixture_only=True, status='passed')))
