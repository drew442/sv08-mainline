import json
from pathlib import Path
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from integrate_host_os import validate


class IntegrationManifestTests(unittest.TestCase):
    def test_requires_distinct_real_uuid_paths_and_non_deployable_status(self):
        manifest = dict(release='fixture-1', state_schema=1, deployable=False,
                        devices={name: '/dev/disk/by-partuuid/'+str(uuid.uuid4()) for name in
                                 ('boot-a', 'root-a', 'boot-b', 'root-b', 'data', 'recovery')})
        validate(manifest)
        for field, value in [('deployable', True), ('state_schema', 2)]:
            changed = dict(manifest, **{field: value})
            with self.assertRaises(ValueError):
                validate(changed)
        changed = json.loads(json.dumps(manifest))
        changed['devices']['data'] = changed['devices']['root-a']
        with self.assertRaises(ValueError):
            validate(changed)
        changed['devices']['data'] = '/dev/disk/by-partuuid/'+'-'*36
        with self.assertRaises(ValueError):
            validate(changed)
