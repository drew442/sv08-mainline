#!/usr/bin/env python3
"""Run with /usr/bin/python3 under Xvfb; callbacks are explicit offline doubles."""
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_recovery_ui import RecoveryWindow, Gtk, GLib
from sv08_admin import Controller
from sv08_state import Store


def wait(condition):
    deadline = time.monotonic()+5
    while not condition():
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        if time.monotonic()>deadline: raise AssertionError('GTK callback did not finish')
        time.sleep(.01)


class Adapter:
    def __init__(self): self.calls=[]
    def capability(self, action, _): return (action=='recovery.boot', 'Offline callback fixture')
    def catalog(self): return []
    def images(self): return []
    def destinations(self): return []
    def hostname(self): return 'fixture'
    def apply(self, plan):
        self.calls.append(plan['arguments']['slot'])
        return {'message':'Offline callback completed; no bootloader exists in this test.'}


with tempfile.TemporaryDirectory() as directory:
    store=Store(Path(directory)/'state', reserve_bytes=0);store.initialize()
    boot=store.prepare_boot('A','fixture-1');adapter=Adapter()
    window=RecoveryWindow(Controller(store,boot,'recovery',adapter));window.show_all()
    wait(lambda:not window.busy)
    assert window.buttons[0][0].get_sensitive()
    window.present()
    window.get_window().focus(0)
    wait(lambda:window.has_toplevel_focus())
    window.buttons[0][0].grab_focus()
    assert window.get_focus() is window.buttons[0][0]
    while Gtk.events_pending(): Gtk.main_iteration_do(False)
    window.get_focus().get_parent().child_focus(Gtk.DirectionType.TAB_FORWARD)
    assert window.get_focus() is window.buttons[1][0]
    # Native review defaults to cancellation. Exercise both dialog outcomes.
    def respond(response):
        for dialog in Gtk.Window.list_toplevels():
            if isinstance(dialog,Gtk.MessageDialog):
                dialog.response(response);return False
        return True
    GLib.timeout_add(20,respond,Gtk.ResponseType.CANCEL)
    window.buttons[0][0].clicked()
    wait(lambda:not window.busy and window.status is not None)
    # Drain the follow-up asynchronous refresh after cancelling.
    wait(lambda:window.buttons[0][0].get_sensitive())
    assert adapter.calls==[]
    GLib.timeout_add(20,respond,Gtk.ResponseType.OK)
    window.buttons[1][0].clicked()
    wait(lambda:adapter.calls==['B'] and not window.busy)
    assert 'Offline callback completed' in window.message.get_text()
    # Corrupt state stays corrupt and displays a diagnostic rather than resetting.
    (store.root/'state.json').write_text('damaged')
    window.refresh();wait(lambda:not window.busy)
    assert 'Cannot read system state' in window.message.get_text()
    assert (store.root/'state.json').read_text()=='damaged'
    assert all(not button.get_sensitive() for button,action in window.buttons if action)
    window.hide()
print('GTK focus, cancel, confirm, and damaged-state tests PASS (offline callbacks only)')
