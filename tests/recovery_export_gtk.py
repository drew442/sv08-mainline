#!/usr/bin/env python3
"""Native UI -> actual local archive; disposable files and admission only."""
from contextlib import contextmanager
from pathlib import Path
import sys
import tarfile
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from sv08_recovery_ui import RecoveryWindow, Gtk, GLib
from sv08_recovery import RecoveryController
from sv08_export import Export, ExportAdapter
from sv08_state import Store


def wait(condition):
    deadline=time.monotonic()+10
    while not condition():
        while Gtk.events_pending():Gtk.main_iteration_do(False)
        if time.monotonic()>deadline:raise AssertionError('GTK export timeout')
        time.sleep(.01)


with tempfile.TemporaryDirectory() as directory:
    root=Path(directory);source=root/'source';source.mkdir();destination=root/'usb';destination.mkdir()
    (source/'state.json').write_text('damaged')
    (source/'printer.cfg').write_text('preserved private configuration')
    @contextmanager
    def admission(target):
        assert target=='test-usb'
        yield  # Explicit local fixture; no physical mount identity is claimed.
    exporter=Export(source,{'test-usb':{'path':destination,'label':'Disposable test USB'}},admission,reserve_bytes=0)
    window=RecoveryWindow(RecoveryController(Store(source),ExportAdapter(exporter)));window.show_all()
    wait(lambda:not window.busy)
    assert window.buttons[3][0].get_sensitive()
    def accept():
        for dialog in Gtk.Window.list_toplevels():
            if isinstance(dialog,Gtk.Dialog):
                if isinstance(dialog,Gtk.MessageDialog):
                    assert 'private configuration' in dialog.get_property('secondary-text')
                dialog.response(Gtk.ResponseType.OK)
        return not bool(list(destination.glob('*.tar')))
    GLib.timeout_add(20,accept)
    window.buttons[3][0].clicked()
    wait(lambda:bool(list(destination.glob('*.tar'))) and not window.busy)
    assert 'readback verified' in window.message.get_text()
    archive=next(destination.glob('*.tar'))
    with tarfile.open(archive) as stream:
        assert stream.extractfile('data/printer.cfg').read()==b'preserved private configuration'
    assert (source/'state.json').read_text()=='damaged'
    window.hide()
print('GTK selection/review -> actual export/readback PASS; no printer or USB hardware')
