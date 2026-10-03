#!/usr/bin/env python3
"""SD-only native attended screen; GTK controls, no automatic write or restart.

Present the modal explicitly for the recovery X server without a window manager.
GTK's internal focus alone does not establish X keyboard focus. Keep No as the
fallback default while focused buttons accept Enter through native GTK traversal.
"""
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from sv08_sd_reimage import installed_session, EFFECT


class ReimageWindow(Gtk.Window):
    def __init__(self, factory=installed_session):
        super().__init__(title='SV08 · Attended SD reimage')
        self.factory, self.session, self.busy, self.answered = factory, None, False, False
        self.set_default_size(960, 600)
        self.connect('delete-event', self.closing)
        self.connect('destroy', lambda *_: Gtk.main_quit() if Gtk.main_level() else None)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin=20)
        scroll = Gtk.ScrolledWindow(); scroll.add(box); self.add(scroll)
        self.message = Gtk.Label(label=EFFECT+'\nSD remains the manual recovery route.\n'
                                 'Use Tab / Shift+Tab and Enter, or touch/click. Escape cancels.',
                                 wrap=True, xalign=0)
        box.pack_start(self.message, True, True, 0)
        self.review_button = Gtk.Button.new_with_mnemonic('_Review image and target')
        self.review_button.connect('clicked', lambda *_: self.prepare())
        box.pack_start(self.review_button, False, False, 0)
        self.refresh_button = Gtk.Button.new_with_mnemonic('_Refresh')
        self.refresh_button.connect('clicked', lambda *_: self.refresh())
        box.pack_start(self.refresh_button, False, False, 0)
        for button in (self.review_button, self.refresh_button):
            button.set_size_request(-1, 56)

    def closing(self, *_):
        if self.busy: return True
        if self.session: self.session.close()
        return False

    def work(self, operation, complete):
        if self.busy: return
        self.busy = True
        self.review_button.set_sensitive(False); self.refresh_button.set_sensitive(False)
        def run():
            try: result, error = operation(), None
            except Exception as exc: result, error = None, str(exc)
            GLib.idle_add(done, result, error)
        def done(result, error):
            self.busy = False
            self.refresh_button.set_sensitive(True)
            self.review_button.set_sensitive(not self.answered)
            complete(result, error)
            return False
        threading.Thread(target=run, daemon=True).start()

    def refresh(self):
        if self.busy: return
        if self.session: self.session.close(); self.session = None
        self.message.set_text(EFFECT+'\nRefresh performs no write. '+
                              ('Relaunch to review again.' if self.answered else 'Choose Review when ready.'))

    def prepare(self):
        if self.answered: return
        self.message.set_text('Checking configured image and intended target…')
        self.work(self.factory, self.review)

    def review(self, session, error):
        if error:
            self.message.set_text('Refused: '+error+'\nNo write.'); return
        self.session = session
        dialog = Gtk.MessageDialog(transient_for=self, modal=True,
                                   message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.NONE, text='Replace the complete image range?')
        dialog.format_secondary_text(session.review())
        dialog.add_button('_No', Gtk.ResponseType.NO)
        dialog.add_button('_Yes, replace image', Gtk.ResponseType.YES)
        dialog.set_default_response(Gtk.ResponseType.NO)
        no = dialog.get_widget_for_response(Gtk.ResponseType.NO)
        yes = dialog.get_widget_for_response(Gtk.ResponseType.YES)
        selection = Gtk.Label(label='Tab / Shift+Tab selects; Enter activates; Escape cancels.', wrap=True)
        dialog.get_content_area().pack_end(selection, False, False, 8)
        # Always show focus, even when the theme suppresses keyboard focus rings.
        style = Gtk.CssProvider()
        style.load_from_data(b'button:focus { outline: 4px solid #204a87; outline-offset: -5px; }')
        def show_selection(*_):
            selected = next((button.get_label().replace('_', '') for button in (no, yes)
                             if button.has_focus()), None)
            selection.set_text(('Keyboard selection: '+selected+'. Enter activates. ' if selected else
                                'No keyboard selection. ')+
                               'Tab / Shift+Tab selects; Escape cancels. No is the default.')
        for button in (no, yes):
            button.get_style_context().add_provider(style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            button.connect('notify::has-focus', show_selection)
        self.dialog = dialog
        dialog.show_all()
        dialog.present()  # Request native input focus; no WM is present in recovery.
        no.grab_focus()
        show_selection()
        response = dialog.run(); dialog.destroy(); self.dialog = None
        self.answered = True
        self.review_button.set_sensitive(False)
        self.message.set_text('Writing and verifying; keep power on.' if response == Gtk.ResponseType.YES else 'No write.')
        self.work(lambda: session.apply(response == Gtk.ResponseType.YES), self.result)

    def result(self, result, error):
        self.session = None
        self.message.set_text(error or result)


def main():
    window = ReimageWindow()
    window.set_decorated(False)
    window.show_all()
    window.present()
    Gtk.main()


if __name__ == '__main__': main()
