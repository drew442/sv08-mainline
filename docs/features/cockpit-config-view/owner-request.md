# Owner request — 2026-10-11

“i currently cant see configuration without first enabling administrator access. i'd like to be able to see all configuration without enabling admin access.”

Normal authenticated Cockpit users can view hardware/current/previous configuration, definitions/sources/connections and host/network/software/access/identity configuration without elevation. Mutations and private credential/identity operations still require explicit administrator access. Protect stored state and private secrets. Deploy the implemented change to the currently installed UI under the preceding deployment authorization.
