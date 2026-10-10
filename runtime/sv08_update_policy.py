#!/usr/bin/env python3
"""Named image admission checks; physical and data invariants are unconditional.

Release ordering uses authenticated positive integers only. Display identifiers
and feed sequence numbers never imply release order. Provenance exceptions are
one manual request, never a persistent automatic policy.
"""
DEFAULTS = dict(check_compatibility=True, check_customization=True,
                check_version=True, allow_downgrade=False,
                allow_untrusted_provenance=False)


def effective(options=None, *, automatic=False):
    if type(automatic) is not bool:
        raise ValueError('Automatic operation must be a boolean')
    if options is None: options = {}
    if not isinstance(options, dict) or set(options) - set(DEFAULTS):
        raise ValueError('Unknown update policy option')
    if any(type(value) is not bool for value in options.values()):
        raise ValueError('Update policy options must be booleans')
    result = dict(DEFAULTS, **options)
    if automatic and result['allow_untrusted_provenance']:
        raise ValueError('Automatic updates require trusted provenance')
    return result


def release_revision(value):
    if type(value) is not int or value <= 0:
        raise ValueError('Release revision must be a positive integer')
    return value


def admit(proof, state, boot, options=None, *, automatic=False):
    policy = effective(options, automatic=automatic)
    if proof.get('update_policy') is not None and proof['update_policy'] != policy:
        raise ValueError('Authenticated proof differs from the reviewed update policy')
    if automatic and proof.get('signer_trusted') is not True:
        raise ValueError('Automatic updates require trusted bundle provenance')
    if type(proof.get('signer_trusted')) is not bool:
        raise ValueError('Missing authenticated signer provenance proof')
    if proof.get('signer_trusted') is False and not policy['allow_untrusted_provenance']:
        raise ValueError('Manual provenance exception was not reviewed')
    if policy['check_version']:
        current = state['slots'][boot['slot']].get('release_revision')
        candidate = proof.get('release_revision')
        if current is None or candidate is None:
            raise ValueError('Release ordering is unknown; signed release revisions are required')
        release_revision(current); release_revision(candidate)
        if candidate == current:
            raise ValueError('Release revision is already installed')
        if candidate < current and not policy['allow_downgrade']:
            raise ValueError('Release downgrade is disabled')
    return policy


def check_source(state, boot, policy=None):
    policy = effective(policy)
    record = state['slots'].get(boot['slot'])
    if not record or record['release'] != boot['release']:
        raise ValueError('Running release differs from state registry')
    if boot['mode'] != 'immutable' or state['requested_mode'] != 'immutable':
        raise ValueError('Writable system requires immutable mode before image replacement')
    if policy['check_customization'] and any(r['customized'] for r in state['slots'].values()):
        raise ValueError('Customized slots require reconciliation before image replacement')
    return policy


def policy_revision(policy):
    import hashlib, json
    return hashlib.sha256(json.dumps(effective(policy), sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()
