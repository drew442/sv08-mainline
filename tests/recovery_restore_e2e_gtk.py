#!/usr/bin/env python3
"""Rendered native activation review, cancellation, stale error and rollback."""
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
from sv08_state import Store
from test_recovery_activation import BOOT, admission, state_fixture


def wait(condition):
    deadline=time.monotonic()+10
    while not condition():
        while Gtk.events_pending():Gtk.main_iteration_do(False)
        if time.monotonic()>deadline:raise AssertionError('GTK activation timeout')
        time.sleep(.01)


evidence=Path(os.environ['SV08_UI_EVIDENCE']);evidence.mkdir(mode=0o700,parents=True,exist_ok=True)
def capture(widget,name):
    for _ in range(10):
        while Gtk.events_pending():Gtk.main_iteration_do(False)
        time.sleep(.01)
    image=Gdk.pixbuf_get_from_window(widget.get_window(),0,0,widget.get_allocated_width(),widget.get_allocated_height())
    assert image;image.savev(str(evidence/name),'png',[],[])


with tempfile.TemporaryDirectory(dir=evidence) as directory:
    root=Path(directory);state_fixture(root/'sv08','previous')
    (root/'restored').mkdir(mode=0o700);state_fixture(root/'restored/sv08','restored','b'*32)
    targets=dict(target=dict(label='Prepared disposable storage',mount=str(root),root=str(root/'restored'),fresh_root=str(root/'fresh')))
    adapter=RestoreAdapter(Restore({},targets,admission,reserve_bytes=0),BOOT)
    controller=RecoveryController(Store(root/'sv08'),adapter)
    window=RecoveryWindow(controller);window.show_all();wait(lambda:not window.busy)
    assert window.buttons[8][0].get_sensitive();capture(window,'activation-status.png')
    def journey(action,response,filename,mutate=None):
        seen=[]
        def dialogs():
            for dialog in Gtk.Window.list_toplevels():
                if not isinstance(dialog,Gtk.Dialog):continue
                if isinstance(dialog,Gtk.MessageDialog):
                    text=dialog.get_property('secondary-text')
                    assert 'next normal boot' in text;assert 'rollback' in text or 'previous configuration' in text
                    capture(dialog,filename);seen.append(True)
                    if mutate:mutate()
                    dialog.response(response);return False
                dialog.response(Gtk.ResponseType.OK)
            return True
        GLib.timeout_add(30,dialogs)
        button=next(button for button,key in window.buttons if key==action)
        button.grab_focus();button.activate();wait(lambda:bool(seen) and not window.busy)
    journey('recovery.activate',Gtk.ResponseType.CANCEL,'activation-review.png')
    assert not (root/'.sv08-activation.json').exists()
    assert (root/'sv08/system/machine-id').read_text()=='a'*32+'\n'
    journey('recovery.activate',Gtk.ResponseType.OK,'activation-apply-review.png')
    assert 'State activated' in window.message.get_text();assert (root/'sv08/system/machine-id').read_text()=='b'*32+'\n'
    capture(window,'activation-complete.png')
    window.refresh();wait(lambda:not window.busy)
    journey('recovery.rollback',Gtk.ResponseType.CANCEL,'rollback-review.png')
    assert (root/'sv08/system/machine-id').read_text()=='b'*32+'\n'
    journey('recovery.rollback',Gtk.ResponseType.OK,'rollback-apply-review.png')
    assert 'Previous state restored' in window.message.get_text();assert (root/'sv08/system/machine-id').read_text()=='a'*32+'\n'
    window.refresh();wait(lambda:not window.busy)
    store=Store(root/'restored/sv08');cfg=store.generation_path(store.load()['slots']['A'])/'config/printer.cfg'
    journey('recovery.activate',Gtk.ResponseType.OK,'activation-stale-review.png',lambda:cfg.write_text('changed after review'))
    assert 'review' in window.message.get_text().lower() or 'changed' in window.message.get_text().lower()
    assert (root/'sv08/system/machine-id').read_text()=='a'*32+'\n';capture(window,'activation-stale-error.png')
    window.hide()
print('GTK activation/rollback review, keyboard activation, cancel, actual apply and stale refusal PASS')
