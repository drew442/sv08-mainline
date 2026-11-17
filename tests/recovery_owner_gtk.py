#!/usr/bin/env python3
"""Actual local GTK owner entry/cancel/reset/error at 800x480; disposable media."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from sv08_recovery_ui import RecoveryWindow, OwnerPasswordDialog, Gtk, GLib, Gdk
from sv08_recovery import RecoveryController
from sv08_recovery_restore_media import RestoreAdapter
from sv08_restore import Restore
from sv08_state import Store
from sv08_owner import Owner
from test_data_budget import fixture_budget
from contextlib import contextmanager


def wait(condition):
    deadline=time.monotonic()+8
    while not condition():
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        if time.monotonic()>deadline: raise AssertionError('GTK owner callback timeout')
        time.sleep(.01)


def capture(widget,name):
    for _ in range(25):
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        time.sleep(.01)
    image=Gdk.pixbuf_get_from_window(widget.get_window(),0,0,widget.get_allocated_width(),widget.get_allocated_height())
    assert image; image.savev(str(evidence/name),'png',[],[])


class Guard:
    fingerprint='fixture media'
    def recheck(self): pass


@contextmanager
def admission(target):
    assert target=='disk'
    yield Guard()


evidence=Path(os.environ['SV08_UI_EVIDENCE']);evidence.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=evidence) as temporary:
    parent=Path(temporary);root=parent/'sv08';Store(root,budget=fixture_budget(parent)).initialize();(root/'system').chmod(0o700)
    targets={'disk':dict(mount=str(parent),root=str(parent/'restored'),fresh_root=str(parent/'fresh'),label='Fixture data storage')}
    adapter=RestoreAdapter(Restore({},targets,admission,reserve_bytes=0));adapter.owner.root_uid=os.getuid()
    controller=RecoveryController(Store(root),adapter);window=RecoveryWindow(controller);window.show_all()
    wait(lambda:not window.busy);capture(window,'owner-entry.png')
    password='touch Password 12!'
    outcome=[]; errors=[]
    def drive_inner(mode):
        for dialog in Gtk.Window.list_toplevels():
            if isinstance(dialog,OwnerPasswordDialog):
                assert dialog.get_allocated_width()<=800 and dialog.get_allocated_height()<=480, (dialog.get_allocated_width(),dialog.get_allocated_height())
                assert all(not entry.get_visibility() for entry in dialog.entries)
                assert not dialog.review_button.get_sensitive()
                # Type through actual touch keyboard controls, including case,
                # space, symbols, backspace and switching the selected entry.
                dialog.key(None,'t');dialog.key(None,'Backspace')
                for field in dialog.entries:
                    dialog.active_entry=field
                    for char in password: dialog.key(None,'Space' if char==' ' else char)
                assert dialog.review_button.get_sensitive()
                dialog.entries[1].set_text('mismatch value');assert not dialog.review_button.get_sensitive()
                capture(dialog,'owner-mismatch.png')
                dialog.entries[1].set_text(password);dialog.entries[0].grab_focus()
                dialog.key(None,'Next field');assert dialog.active_entry is dialog.entries[1]
                assert dialog.review_button.get_sensitive(), 'Review local sensitivity false after focus change'
                assert dialog.review_button.is_sensitive(), 'Review ancestor sensitivity false after focus change'
                capture(dialog,'owner-keyboard.png')
                if mode=='entry-cancel': dialog.response(Gtk.ResponseType.CANCEL);outcome.append(mode);return False
                dialog.review_button.clicked();return True
            if isinstance(dialog,Gtk.MessageDialog):
                text=dialog.get_property('secondary-text');assert password not in text;assert 'password_hash' not in text
                assert 'Fixture data storage' in text and 'Current state' in text
                capture(dialog,'owner-review.png')
                dialog.response(Gtk.ResponseType.CANCEL if mode=='review-cancel' else Gtk.ResponseType.OK)
                outcome.append(mode);return False
            if isinstance(dialog,Gtk.Dialog):
                dialog.response(Gtk.ResponseType.OK);return True
        return True
    def drive(mode):
        try: return drive_inner(mode)
        except BaseException as error:
            errors.append(str(error))
            for dialog in Gtk.Window.list_toplevels():
                if isinstance(dialog,Gtk.Dialog): dialog.response(Gtk.ResponseType.CANCEL)
            return False
    for mode in ('entry-cancel','review-cancel','apply'):
        GLib.timeout_add(50,drive,mode);window.buttons[11][0].clicked()
        wait(lambda:bool(errors) or (mode in outcome and not window.busy))
        assert not errors, errors
        if mode!='apply':
            assert not (root/'system/owner.json').exists();assert window.owner_secret is None
            window.refresh();wait(lambda:not window.busy)
    assert Owner(root,os.getuid()).status()['enrolled']
    assert 'next normal boot' in window.message.get_text();capture(window,'owner-complete.png')
    # Initial setup on enrolled state is refused without changing its record.
    before=(root/'system/owner.json').read_bytes();window.refresh();wait(lambda:not window.busy)
    GLib.timeout_add(50,drive,'error');window.buttons[11][0].clicked()
    wait(lambda:not window.busy and 'already has an owner' in window.message.get_text())
    assert (root/'system/owner.json').read_bytes()==before and window.owner_secret is None
    capture(window,'owner-refused.png');window.destroy()
print(json.dumps(dict(owner_gtk=True,viewport=[800,480],masked=True,touch_entry=True,cancel_preserves=True,review_redacted=True,enroll=True,error_preserves=True)))
