"""Static safety contracts for the disposable SD/NFS composer."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'build_sd_network_image', REPO / 'scripts/build_sd_network_image.py')
sd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sd)


class SdNetworkImageTests(unittest.TestCase):
    def test_default_environment_only_loads_sd_and_verifies_script(self):
        env = sd.default_environment('a' * 64)
        self.assertIn('mmc dev 0', env)
        self.assertIn('fatload mmc 0:1', env)
        self.assertIn('hash -v sha256', env)
        self.assertIn('a' * 64, env)
        for forbidden in ('mmc 1', 'mmc1', 'saveenv', 'BOOT_ORDER', 'rauc'):
            self.assertNotIn(forbidden, env)

    def test_script_bounds_root_and_all_payloads(self):
        hashes = {'Image': 'a' * 64, 'initrd.img': 'b' * 64,
                  'sv08.dtb': 'c' * 64}
        script = sd.boot_script('10.0.2.2', '/srv/sv08-sd-nfs', hashes)
        self.assertIn('root=/dev/nfs ro ip=dhcp', script)
        self.assertIn('init=/sd-network-init', script)
        self.assertIn('panic=0', script)
        for value in hashes.values():
            self.assertIn(value, script)
        for forbidden in ('mmc 1', 'mmc1', 'saveenv', 'BOOT_ORDER', 'rauc'):
            self.assertNotIn(forbidden, script)

    def test_effective_config_rejects_emmc_environment(self):
        safe = '''CONFIG_ENV_IS_NOWHERE=y
# CONFIG_ENV_IS_IN_MMC is not set
# CONFIG_ENV_IS_IN_FAT is not set
# CONFIG_ENV_IS_IN_EXT4 is not set
# CONFIG_ENV_REDUNDANT is not set
# CONFIG_BOOTMETH_RAUC is not set
# CONFIG_BOOTSTD is not set
# CONFIG_CMD_SAVEENV is not set
CONFIG_CMD_HASH=y
CONFIG_MMC_SUNXI_SLOT_EXTRA=-1
CONFIG_DEFAULT_DEVICE_TREE="allwinner/sun50i-h616-sovol-sv08-sd-network"
CONFIG_ENV_DEFAULT_ENV_TEXT_FILE="sv08-sd-network.env"
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / '.config'
            path.write_text(safe)
            self.assertEqual(sd.inspect_config(path)['CONFIG_ENV_IS_NOWHERE'], 'y')
            path.write_text(safe.replace('# CONFIG_ENV_IS_IN_MMC is not set',
                                         'CONFIG_ENV_IS_IN_MMC=y'))
            with self.assertRaisesRegex(ValueError, 'Unsafe effective'):
                sd.inspect_config(path)


if __name__ == '__main__':
    unittest.main()
