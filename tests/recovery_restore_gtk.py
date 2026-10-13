#!/usr/bin/env python3
"""Actual GTK chooser/review/cancel/apply/failure with a disposable controller.

Run under installed Xvfb with /usr/bin/python3 and SV08_UI_EVIDENCE pointing to
private scratch. Screenshots show the real widgets and actual result messages.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from sv08_recovery_ui import RecoveryWindow, Gtk, GLib, Gdk
from sv08_recovery import RecoveryController
from sv08_recovery_restore_media import RestoreAdapter
from sv08_restore import Restore
from sv08_export import Export
from sv08_state import Store


def wait(condition):
    deadline=time.monotonic()+10
    while not condition():
        while Gtk.events_pending():Gtk.main_iteration_do(False)
        if time.monotonic()>deadline:raise AssertionError('GTK restore timeout')
        time.sleep(.01)


def capture(widget, filename):
    deadline=time.monotonic()+.08
    while time.monotonic()<deadline:
        while Gtk.events_pending():Gtk.main_iteration_do(False)
        time.sleep(.005)
    image=Gdk.pixbuf_get_from_window(widget.get_window(),0,0,widget.get_allocated_width(),widget.get_allocated_height())
    assert image
    image.savev(str(evidence/filename),'png',[],[])


class Guard:
    fingerprint='explicit-offline-fixture'
    def recheck(self):pass


@contextmanager
def admission(target):yield Guard()


evidence=Path(os.environ['SV08_UI_EVIDENCE']);evidence.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=evidence) as directory:
    root=Path(directory);source=root/'source';source.mkdir(mode=0o700);usb=root/'usb';usb.mkdir(mode=0o700)
    target=root/'target';target.mkdir(mode=0o700)
    (source/'sv08').mkdir(mode=0o700);(source/'sv08/state.json').write_bytes(b'broken fixture registry')
    (source/'printer.cfg').write_bytes(b'offline fixture configuration')
    exporter=Export(source,{'usb':dict(path=usb,label='Fixture USB')},admission,reserve_bytes=0)
    saved=exporter.execute(exporter.prepare('usb'));archive=usb/saved['filename']
    restorer=Restore({'backup':dict(path=archive,label='Saved user data · fixture USB')},
        {'target':dict(root=target/'data',fresh_root=target/'sv08',label='Prepared data storage · offline fixture')},admission,reserve_bytes=0)
    window=RecoveryWindow(RecoveryController(Store(source/'sv08'),RestoreAdapter(restorer)));window.show_all()
    wait(lambda:not window.busy);assert window.buttons[6][0].get_sensitive();capture(window,'restore-status.png')
    # Choose real configured IDs, then cancel the real review without writes.
    review_seen=[]
    def cancel_review():
        for dialog in Gtk.Window.list_toplevels():
            if not isinstance(dialog,Gtk.Dialog):continue
            if isinstance(dialog,Gtk.MessageDialog):
                text=dialog.get_property('secondary-text');assert str(target/'data') in text
                assert 'No boot selection' in text;assert 'private configuration' in text
                capture(dialog,'restore-review.png');review_seen.append(True)
                dialog.response(Gtk.ResponseType.CANCEL);return False
            assert dialog.get_title()=='Choose recovery items'
            capture(dialog,'restore-chooser.png');dialog.response(Gtk.ResponseType.OK)
        return True
    GLib.timeout_add(30,cancel_review);window.buttons[6][0].grab_focus();window.buttons[6][0].activate()
    wait(lambda:bool(review_seen) and not window.busy)
    assert not (target/'data').exists();assert not list(target.glob('.sv08-restore-*'))
    # Actual apply publishes the complete tree and leaves explicit feedback.
    def apply_dialogs():
        for dialog in Gtk.Window.list_toplevels():
            if isinstance(dialog,Gtk.Dialog):dialog.response(Gtk.ResponseType.OK)
        return not (target/'data').exists()
    GLib.timeout_add(30,apply_dialogs);window.buttons[6][0].clicked()
    wait(lambda:(target/'data').exists() and not window.busy)
    assert (target/'data/printer.cfg').read_bytes()==b'offline fixture configuration'
    assert (target/'data/sv08/state.json').read_bytes()==b'broken fixture registry'
    assert 'without repair' in window.message.get_text();assert 'No automatic' in window.message.get_text()
    capture(window,'restore-complete.png')
    # Refresh and retry honestly refuse the existing destination.
    window.buttons[5][0].clicked();wait(lambda:not window.busy)
    def choose_existing():
        for dialog in Gtk.Window.list_toplevels():
            if isinstance(dialog,Gtk.Dialog):dialog.response(Gtk.ResponseType.OK);return False
        return True
    GLib.timeout_add(30,choose_existing);window.buttons[6][0].clicked()
    wait(lambda:not window.busy and 'already exists' in window.message.get_text());capture(window,'restore-refused.png')
    assert (target/'data/printer.cfg').read_bytes()==b'offline fixture configuration'
    # Fresh action is separate and creates immutable defaults only on apply.
    window.buttons[5][0].clicked();wait(lambda:not window.busy)
    def fresh_dialogs():
        for dialog in Gtk.Window.list_toplevels():
            if isinstance(dialog,Gtk.Dialog):
                if isinstance(dialog,Gtk.MessageDialog):
                    assert 'fresh immutable state' in dialog.get_property('secondary-text')
                    capture(dialog,'fresh-review.png')
                dialog.response(Gtk.ResponseType.OK)
        return not (target/'sv08').exists()
    assert not (target/'sv08').exists()
    GLib.timeout_add(30,fresh_dialogs);window.buttons[7][0].clicked()
    wait(lambda:(target/'sv08').exists() and not window.busy)
    assert Store(target/'sv08').load()['requested_mode']=='immutable';capture(window,'fresh-complete.png')
    window.hide()
print('GTK chooser/review/cancel/full restore/refusal/fresh apply PASS; disposable files only')
