'use strict';
// Always use the ordinary authenticated bridge, even during administrator access.
window.sv08View = async (area, method = 'status', fields = {}) => {
    if (!window.cockpit || !window.sv08Session || !await sv08Session.ready || !sv08Session.available)
        throw new Error('Log in through Cockpit to view configuration.');
    const raw = await cockpit.spawn(['/usr/bin/sudo', '-n', '/usr/bin/python3', '-I', '/usr/lib/sv08/sv08_view.py'],
        {err: 'message'}).input(JSON.stringify({area, method, ...fields}));
    const reply = JSON.parse(raw);
    if (!reply.ok) throw new Error(reply.error || 'Configuration view unavailable. Refresh to retry.');
    return reply.result;
};
