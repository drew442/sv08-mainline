import atexit
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_data_budget import Budget, BATCH_BYTES, METADATA_BYTES, rounded


_private_fixture = None


def fixture_root():
    """Optional assigned root, otherwise one private, automatically cleaned root.

    TMPDIR may select a suitably resourced safe parent. Product path and space
    validation still applies; this helper does not relax either check.
    """
    override = os.environ.get('SV08_TEST_ROOT')
    if override:
        return Path(override)
    global _private_fixture
    if _private_fixture is None:
        parent = Path(os.environ.get('TMPDIR', str(Path.home())))
        _private_fixture = tempfile.TemporaryDirectory(prefix='.sv08-tests-', dir=parent)
        atexit.register(_private_fixture.cleanup)
    return Path(_private_fixture.name)


def fixture_budget(root=None):
    """Deterministic component budget; real shared-root tests use Budget(root).

    Zero configured floors are deliberate for small component fixtures, while H
    and inode headroom remain enforced. This is not production admission proof.
    """
    root = Path(root) if root is not None else fixture_root()
    if os.environ.get('SV08_TEST_PRODUCTION_RESERVE') == '1': return Budget(root)
    return Budget(root, state_reserve=0, copy_limit=0, staging_reserve=0)


class DataBudgetTests(unittest.TestCase):
    def test_exact_byte_inode_edges_and_configured_floor(self):
        budget = Budget(Path(fixture_root()), state_reserve=100, copy_limit=200, staging_reserve=400)
        block = 4096; delta = 1
        h = 2*rounded(BATCH_BYTES, block)+rounded(METADATA_BYTES, block)
        need = 400+4096+h
        fs = SimpleNamespace(f_frsize=block, f_bsize=block, f_bavail=(need+block-1)//block, f_favail=65)
        budget.check(delta, 1, fs=fs)
        fs.f_bavail -= 1
        with self.assertRaises(ValueError): budget.check(delta, 1, fs=fs)
        fs.f_bavail += 1; fs.f_favail -= 1
        with self.assertRaises(ValueError): budget.check(delta, 1, fs=fs)
        fs.f_favail = 65; fs.f_bavail = 2
        budget.check(delta, 1, fs=fs, result=True)
        with self.assertRaises(ValueError): budget.check(delta, 1, fs=fs)

    def test_real_process_leaf_exclusion_and_persistent_inode(self):
        root = Path(fixture_root())
        budget = fixture_budget()
        with budget.locked():
            inode = (root / 'allocation.lock').stat().st_ino
            child = multiprocessing.Process(target=_busy, args=(str(root),))
            child.start(); child.join(5)
            self.assertEqual(child.exitcode, 0)
        with budget.locked(): self.assertEqual((root / 'allocation.lock').stat().st_ino, inode)


def _busy(root):
    try:
        with Budget(root).locked(): raise AssertionError('Contender acquired held allocation')
    except ValueError as error:
        if 'busy' not in str(error): raise
