#!/usr/bin/env python3
"""Touch/keyboard/mouse recovery frontend; no shell or device writes in widgets.

GTK's native controls provide focus, activation, and accessible labels. Actions
use the same review/apply contract as host administration. See ADR 0010.
"""
import argparse
import json
from pathlib import Path
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from sv08_recovery import RecoveryController, installed_controller
from sv08_state import Store


class RecoveryWindow(Gtk.Window):
    def __init__(self, controller):
        super().__init__(title='SV08 Recovery')
        self.controller, self.busy, self.status = controller, False, None
        self.set_default_size(800, 480)
        self.connect('destroy', Gtk.main_quit)
        self.connect('delete-event', lambda *_: True)
        style = Gtk.CssProvider()
        style.load_from_data(b'window {background: #f4f6f3; color: #21332e;} button {min-height: 48px; padding: 8px 16px; font-size: 17px;} button:focus {outline: 3px solid #ca6b21;} label {font-size: 17px;} .title {font-size: 28px; font-weight: bold;}')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        scroll = Gtk.ScrolledWindow(); self.add(scroll)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=20); scroll.add(box)
        title = Gtk.Label(label='SV08 · Recovery', xalign=0); title.get_style_context().add_class('title'); box.pack_start(title, False, False, 0)
        self.message = Gtk.Label(label='Reading recovery status…', xalign=0, wrap=True)
        self.message.set_selectable(True); box.pack_start(self.message, False, False, 0)
        self.buttons = []
        grid = Gtk.Grid(column_spacing=12, row_spacing=12, column_homogeneous=True)
        box.pack_start(grid, False, False, 0)
        items = [('Boot system _A', 'recovery.boot', {'slot': 'A'}),
                 ('Boot system _B', 'recovery.boot', {'slot': 'B'}),
                 ('_Restore an OS image', 'recovery.restore', None),
                 ('_Save user data', 'recovery.export', None),
                 ('_Check storage', 'recovery.check', {}),
                 ('_Refresh', None, {})]
        for index, (label, action, arguments) in enumerate(items):
            button = Gtk.Button.new_with_mnemonic(label)
            button.connect('clicked', self.clicked, action, arguments)
            grid.attach(button, index % 2, index // 2, 1, 1)
            self.buttons.append((button, action))
        self.reason = Gtk.Label(xalign=0, wrap=True); box.pack_start(self.reason, False, False, 0)
        help_text = Gtk.Label(label='Touch a button, or use Tab / Shift+Tab and Enter.\nEscape cancels a review. A mouse works too.\nOS recovery preserves user data; export readable files before restoring.', xalign=0, wrap=True)
        box.pack_start(help_text, False, False, 0)
        self.refresh()

    def work(self, operation, complete):
        if self.busy: return
        self.busy = True
        for button, _ in self.buttons: button.set_sensitive(False)
        def run():
            try: result, error = operation(), None
            except Exception as exc: result, error = None, str(exc)
            GLib.idle_add(done, result, error)
        def done(result, error):
            self.busy = False
            complete(result, error)
            return False
        threading.Thread(target=run, daemon=True).start()

    def refresh(self):
        def received(status, error):
            self.status = status
            if error:
                self.message.set_text('Cannot read system state: '+error)
                self.reason.set_text('No storage has been changed. Keep the factory eMMC or use the USB-reader recovery procedure. Storage inspection remains available only with a verified recovery backend.')
                for button, action in self.buttons: button.set_sensitive(action is None)
                return
            self.message.set_text(status.get('diagnostic', 'Choose how to recover. Configuration and user files are preserved.'))
            reasons = set()
            for button, action in self.buttons:
                cap = status['capabilities'].get(action, {'available': True, 'reason': ''})
                button.set_sensitive(cap['available'])
                button.set_tooltip_text(cap['reason'] or None)
                if cap['reason']: reasons.add(cap['reason'])
            self.reason.set_text('\n'.join(sorted(reasons)))
        self.work(self.controller.status, received)

    def clicked(self, button, action, arguments):
        if action is None: self.refresh(); return
        if arguments is None:
            field, choices = ('image', self.status['images']) if action == 'recovery.restore' else ('destination', self.status['destinations'])
            dialog = Gtk.Dialog(title='Choose '+field, transient_for=self, modal=True)
            dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
            choose = dialog.add_button('Review', Gtk.ResponseType.OK)
            combo = Gtk.ComboBoxText()
            for item in choices: combo.append(item['id'], item['label'])
            combo.set_active(0); choose.set_sensitive(bool(choices))
            dialog.get_content_area().add(combo); dialog.show_all()
            response = dialog.run(); selected = combo.get_active_id(); dialog.destroy()
            if response != Gtk.ResponseType.OK: return
            arguments = {field: selected}
        self.work(lambda: self.controller.plan(action, arguments), self.review)

    def review(self, plan, error):
        if error:
            self.message.set_text(error)
            for button, action in self.buttons: button.set_sensitive(action is None)
            return
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.NONE, text=plan['title'])
        details = '\n'.join(f'{key}: {value}' for key, value in plan['arguments'].items())
        dialog.format_secondary_text(plan['effect']+'\n\n'+details+'\n\nConfiguration and user files are preserved.')
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dialog.add_button('Apply change', Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        response = dialog.run(); dialog.destroy()
        if response != Gtk.ResponseType.OK: self.refresh(); return
        def applied(result, error):
            self.message.set_text(error or result.get('message', 'Completed. Refresh to inspect the system.'))
            # Explicit refresh keeps the result visible and prevents double apply.
            for button, action in self.buttons: button.set_sensitive(action is None)
        self.work(lambda: self.controller.apply(plan), applied)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, help='Explicit disposable offline state under build/')
    parser.add_argument('--screenshot', type=Path, help='Fixture-only screenshot for virtual-display tests')
    args = parser.parse_args()
    if args.fixture:
        root = args.fixture.resolve()
        repository = Path(__file__).resolve().parents[1]
        if not root.is_relative_to(repository / 'build') or not (root / 'ui-fixture.json').is_file():
            parser.error('Use a marked disposable build fixture')
        boot = json.loads((root / 'ui-fixture.json').read_text())
        controller = RecoveryController(Store(root / 'state'))
    else:
        if args.screenshot: parser.error('Screenshots require an offline fixture')
        # Missing/damaged registry is displayed without initializing or repairing it.
        controller = installed_controller()
    window = RecoveryWindow(controller)
    if args.fixture:
        window.set_title('SV08 Recovery · Offline test fixture')
    else:
        window.set_decorated(False)
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        if monitor:
            area = monitor.get_geometry()
            window.move(area.x, area.y)
            window.set_default_size(area.width, area.height)
    window.show_all()
    if args.screenshot:
        def capture():
            if window.busy: return True
            image = Gdk.pixbuf_get_from_window(window.get_window(), 0, 0, window.get_allocated_width(), window.get_allocated_height())
            image.savev(str(args.screenshot), 'png', [], [])
            Gtk.main_quit(); return False
        GLib.timeout_add(500, capture)
    Gtk.main()


if __name__ == '__main__': main()
