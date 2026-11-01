"""Focused tests for the one-time SEC-001 operation; no network or real tokens."""
import contextlib
import copy
import importlib.util
from pathlib import Path
import sys
import types
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/revoke_exposed_pilot_code.py"
spec = importlib.util.spec_from_file_location("revocation", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Registry:
    MIN_ACCESS_CODE_CHARS = 12
    registry_file = SCRIPT

    def __init__(self):
        self.records = {
            "customer": {"name": "NTDCO", "access_code_hash": "compromised-hash", "token_hash": "safe-hash", "actors": {}, "customer_data": "preserved"},
            "other": {"name": "Other", "access_code_hash": "other-hash"},
        }
        self.writes = 0

    _locked = contextlib.nullcontext

    def _load(self):
        return copy.deepcopy(self.records)

    def _save(self, records):
        self.records = copy.deepcopy(records)
        self.writes += 1


class RevocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = types.ModuleType("infrastructure")
        registry = types.ModuleType("infrastructure.operator_registry")
        registry.OperatorRegistry = Registry
        cls.original = {key: sys.modules.get(key) for key in (package.__name__, registry.__name__)}
        sys.modules[package.__name__] = package
        sys.modules[registry.__name__] = registry
        namespace = {}
        exec(module.REMOTE, namespace)
        cls.remediate = staticmethod(namespace["remediate"])

    @classmethod
    def tearDownClass(cls):
        for key, value in cls.original.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value

    def test_inspection_never_writes(self):
        registry = Registry()
        result = self.remediate(registry, "compromised-hash", 6, False)
        self.assertTrue(result["historical_code_registered"])
        self.assertEqual(registry.writes, 0)

    def test_revocation_only_clears_matching_code_and_is_idempotent(self):
        registry = Registry()
        before = copy.deepcopy(registry.records)
        result = self.remediate(registry, "compromised-hash", 6, True)
        before["customer"]["access_code_hash"] = None
        self.assertEqual(registry.records, before)
        self.assertTrue(result["revoked"])
        self.assertFalse(self.remediate(registry, "compromised-hash", 6, True)["revoked"])
        self.assertEqual(registry.writes, 1)

    def test_rotated_code_is_preserved(self):
        registry = Registry()
        registry.records["customer"]["access_code_hash"] = "new-hash"
        self.assertFalse(self.remediate(registry, "compromised-hash", 6, True)["revoked"])
        self.assertEqual(registry.writes, 0)

    def test_shared_credential_fails_before_any_write(self):
        registry = Registry()
        registry.records["other"]["access_code_hash"] = "compromised-hash"
        with self.assertRaises(RuntimeError):
            self.remediate(registry, "compromised-hash", 6, True)
        self.assertEqual(registry.writes, 0)

    def test_old_runtime_fails_closed(self):
        registry = Registry()
        registry.MIN_ACCESS_CODE_CHARS = 6
        with self.assertRaises(RuntimeError):
            self.remediate(registry, "compromised-hash", 6, True)
        self.assertEqual(registry.writes, 0)

    def test_workspace_token_collision_fails_closed(self):
        registry = Registry()
        registry.records["customer"]["token_hash"] = "compromised-hash"
        with self.assertRaises(RuntimeError):
            self.remediate(registry, "compromised-hash", 6, True)
        self.assertEqual(registry.writes, 0)


if __name__ == "__main__":
    unittest.main()
