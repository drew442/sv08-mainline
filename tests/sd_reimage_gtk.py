#!/usr/bin/env python3
"""Native GTK fixture driver, also runnable against installed ARM64 runtime.

Run under Xvfb locally; in the installed VM use the service X display. Only an
explicit regular-file fixture is admitted. No window manager is required. Native
Return opens Review; Tab/Shift+Tab navigate from No to Yes without grab_focus.
Pointer activation also exercises the dialog; target bytes, not screenshots,
determine the result. Focus/key delivery may settle asynchronously; wait for actual
native focus within the journey deadline, and retain samples on failure.
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


# XTest sends real keys through X input focus, rather than GTK widget activation.
x = ctypes.CDLL(ctypes.util.find_library('X11'))
xt = ctypes.CDLL(ctypes.util.find_library('Xtst'))
x.XOpenDisplay.restype = ctypes.c_void_p
x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
x.XGetInputFocus.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int)]
x.XFlush.argtypes = [ctypes.c_void_p]
x.XCloseDisplay.argtypes = [ctypes.c_void_p]
xt.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
xt.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
xt.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
display = x.XOpenDisplay(None)
if not display: raise AssertionError('No X display')


def key(symbol, shift=False):
    code = x.XKeysymToKeycode(display, symbol)
    modifier = x.XKeysymToKeycode(display, Gdk.KEY_Shift_L)
    if shift: xt.XTestFakeKeyEvent(display, modifier, 1, 0)
    xt.XTestFakeKeyEvent(display, code, 1, 0)
    xt.XTestFakeKeyEvent(display, code, 0, 0)
    if shift: xt.XTestFakeKeyEvent(display, modifier, 0, 0)
    x.XFlush(display)


def journey(answer, keyboard=False, refused=False):
    def factory():
        return Session(dict(cfg, sha256='0'*64) if refused else cfg, FileFixtureAdmission())
    window = ReimageWindow(factory)
    window.set_title('SV08 · Explicit disposable file fixture')
    window.set_decorated(False)
    window.show_all(); window.present()
    failures, focus = [], []
    step = 0
    started = time.monotonic()
    def respond():
        nonlocal step
        if not getattr(window, 'dialog', None): return True
        dialog = window.dialog
        try:
            if keyboard:
                no = dialog.get_widget_for_response(Gtk.ResponseType.NO)
                yes = dialog.get_widget_for_response(Gtk.ResponseType.YES)
                expected = yes if answer != 'absent' and step in (1, 3) else no
                native, revert = ctypes.c_ulong(), ctypes.c_int()
                x.XGetInputFocus(display, ctypes.byref(native), ctypes.byref(revert))
                surface = dialog.get_window()
                focus.append(dict(step=step, elapsed=round(time.monotonic()-started, 3),
                                  x_input_focus=native.value,
                                  dialog_xid=surface.get_xid() if hasattr(surface, 'get_xid') else None,
                                  mapped=dialog.get_mapped(),
                                  choice='Yes' if dialog.get_focus() == yes else
                                  'No' if dialog.get_focus() == no else 'other',
                                  toplevel=dialog.has_toplevel_focus(), actual=expected.has_focus()))
                assert dialog.get_default_widget() == no, 'No must remain the default'
                # present() and XTest are asynchronous. Do not send the next key
                # until native focus and GTK's chosen widget agree. Never focus
                # a choice here; missing focus/navigation still fails the deadline.
                if not (dialog.has_toplevel_focus() and dialog.get_focus() == expected and expected.has_focus()):
                    return True
                assert dialog.get_focus() == expected and expected.has_focus(), focus
                assert dialog.get_property('secondary-text') == window.session.review()
                labels = [child.get_text() for child in dialog.get_content_area().get_children()
                          if isinstance(child, Gtk.Label)]
                choice = expected.get_label().replace('_', '')
                assert any(text.startswith('Keyboard selection: '+choice+'.') for text in labels), labels
                if answer == 'absent':
                    assert target.read_bytes() == old, 'No answer must leave target unchanged'
                    step += 1
                    if step < 3: return True
                    dialog.response(Gtk.ResponseType.CANCEL)
                    return False
                if answer in ('yes', 'escape-yes') and step < 3:
                    # Forward, backward, forward: test both native traversal directions.
                    key(Gdk.KEY_Tab, shift=step == 1)
                    step += 1
                    return True
                key(Gdk.KEY_Escape if answer.startswith('escape') else Gdk.KEY_Return)
            elif answer == 'close': dialog.response(Gtk.ResponseType.DELETE_EVENT)
            else:
                widget = dialog.get_widget_for_response(Gtk.ResponseType.YES if answer == 'yes' else Gtk.ResponseType.NO)
                coords = widget.translate_coordinates(dialog, widget.get_allocated_width()//2, widget.get_allocated_height()//2)
                origin = dialog.get_window().get_origin()
                xt.XTestFakeMotionEvent(display, -1, origin[-2]+coords[0], origin[-1]+coords[1], 0)
                xt.XTestFakeButtonEvent(display, 1, 1, 0); xt.XTestFakeButtonEvent(display, 1, 0, 0)
                x.XFlush(display)
        except Exception as exc:
            failures.append(str(exc))
            dialog.response(Gtk.ResponseType.CANCEL)
        return False
    if not refused: GLib.timeout_add(100, respond)
    expired = False
    def deadline():
        nonlocal expired
        expired = True
        if getattr(window, 'dialog', None): window.dialog.response(Gtk.ResponseType.CANCEL)
        return False
    timer = GLib.timeout_add_seconds(10, deadline)
    try:
        if keyboard:
            pump_until(lambda: window.review_button.has_focus())
            key(Gdk.KEY_Return)
        else: window.review_button.clicked()
        pump_until(lambda: not window.busy and ('No write' in window.message.get_text() or
                                               'readback matched' in window.message.get_text()))
    except AssertionError as exc:
        failures.append(str(exc))
    if not expired: GLib.source_remove(timer)
    if failures or expired:
        (a.work/'journey-failure.json').write_text(json.dumps(dict(
            answer=answer, keyboard=keyboard, failures=failures, expired=expired,
            focus=focus, gtk_version=[Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()],
            runtime={n:hashlib.sha256((a.runtime/n).read_bytes()).hexdigest()
                     for n in ('sv08_sd_reimage.py', 'sv08_sd_reimage_ui.py')},
            target_unchanged=target.read_bytes() == old), indent=2)+'\n')
    assert not failures, failures
    assert not expired, ('GTK response deadline exceeded; cancellation is not a passing answer; '
                         'see journey-failure.json for native focus samples')
    result = window.message.get_text()
    assert ('Refused' in result) if refused else ('readback matched' in result if answer == 'yes' else 'No write' in result), result
    window.refresh_button.clicked()
    window.destroy()
    results.append(dict(answer=answer, keyboard=keyboard, refused=refused, result=result, focus=focus))


journey('no', refused=True); assert target.read_bytes() == old
journey('no', keyboard=True); assert target.read_bytes() == old
journey('escape', keyboard=True); assert target.read_bytes() == old
journey('escape-yes', keyboard=True); assert target.read_bytes() == old
journey('absent', keyboard=True); assert target.read_bytes() == old
journey('close'); assert target.read_bytes() == old
journey('no'); assert target.read_bytes() == old
journey('yes', keyboard=True); assert target.read_bytes() == data+old[len(data):]
journey('no'); assert target.read_bytes() == data+old[len(data):]  # relaunch does not write
target.write_bytes(old)  # Make the pointer Yes case prove a fresh byte replacement.
journey('yes'); assert target.read_bytes() == data+old[len(data):]
x.XCloseDisplay(display)
report = dict(results=results, source_sha256=cfg['sha256'], target_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              runtime={n:hashlib.sha256((a.runtime/n).read_bytes()).hexdigest() for n in ('sv08_sd_reimage.py','sv08_sd_reimage_ui.py')},
              memory=Path('/proc/meminfo').read_text(), fixture_only=True)
(a.work/'run.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(dict(cases=len(results), fixture_only=True, status='passed')))
