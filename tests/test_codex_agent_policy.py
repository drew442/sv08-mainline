"""Offline configuration invariants, not a Codex runtime or safety certification."""
from pathlib import Path
import re
import tomllib
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".codex" / "agents"
SOL = "gpt-6.1-sol"
LUNA = "gpt-6-luna"
# Explicit expectations make routing changes reviewable; this is not a launcher.
ROUTES = {
    "feature_approver": (SOL, "medium", "read-only"),
    "feature_suggester": (LUNA, "medium", "read-only"),
    "feature_verifier": (SOL, "medium", "read-only"),
    "high_consequence_reviewer": (SOL, "medium", "read-only"),
    "high_consequence_reviewer_high": (SOL, "high", "read-only"),
    "project_implementer": (SOL, "medium", "workspace-write"),
    "project_integration": (SOL, "medium", "workspace-write"),
    "project_narrow_implementer": (LUNA, "medium", "workspace-write"),
    "project_researcher": (LUNA, "medium", "read-only"),
    "project_routine_implementer": (SOL, "low", "workspace-write"),
    "project_test_runner": (LUNA, "medium", "workspace-write"),
}


def load_profiles():
    """Read repository profiles without executing their instructions or commands."""
    return [(path, tomllib.loads(path.read_text(encoding="utf-8")))
            for path in sorted(AGENTS.glob("*.toml"))]


class CodexAgentPolicyTests(unittest.TestCase):
    def test_profiles_have_explicit_reviewed_settings(self):
        profiles = load_profiles()
        names = [data["name"] for _, data in profiles]
        self.assertEqual(len(names), len(set(names)), "duplicate role names")
        self.assertEqual(set(names), set(ROUTES))
        for path, data in profiles:
            with self.subTest(path=path.name):
                self.assertEqual(set(data), {
                    "name", "description", "model", "model_reasoning_effort",
                    "sandbox_mode", "developer_instructions",
                })
                self.assertEqual(path.stem.replace("-", "_"), data["name"])
                self.assertEqual(
                    (data["model"], data["model_reasoning_effort"],
                     data["sandbox_mode"]), ROUTES[data["name"]])
                self.assertTrue(data["description"].strip())
                self.assertIn("AGENTS.md", data["developer_instructions"])
                self.assertIn(".codex/agent-guide.md", data["developer_instructions"])

    def test_coordinator_defaults_and_concurrency_are_unchanged(self):
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text())
        self.assertEqual(config, {"agents": {"max_concurrent_threads_per_session": 2}})

    def test_high_review_keeps_the_same_review_contract(self):
        profiles = {data["name"]: data for _, data in load_profiles()}
        normal = profiles["high_consequence_reviewer"]
        high = profiles["high_consequence_reviewer_high"]
        # Prevent a copied high-effort profile silently losing safety instructions.
        self.assertEqual(normal["developer_instructions"], high["developer_instructions"])
        self.assertEqual(normal["model"], high["model"])
        self.assertEqual(normal["sandbox_mode"], high["sandbox_mode"])
        self.assertEqual(normal["model_reasoning_effort"], "medium")
        self.assertEqual(high["model_reasoning_effort"], "high")

    def test_guide_table_matches_actual_profiles(self):
        text = (ROOT / ".codex/agent-guide.md").read_text()
        rows = re.findall(
            r"^\| `([a-z_]+)` \| (GPT-[^|]+?) / (low|medium|high) \|",
            text, re.MULTILINE)
        self.assertEqual(len(rows), len(ROUTES))
        documented = {name: (model.lower().replace(" ", "-"), effort)
                      for name, model, effort in rows}
        self.assertEqual(documented, {name: values[:2] for name, values in ROUTES.items()})

    def test_root_and_readme_reference_real_high_profile(self):
        for relative in ("AGENTS.md", ".codex/README.md"):
            with self.subTest(path=relative):
                text = (ROOT / relative).read_text()
                self.assertIn("high-consequence-reviewer-high.toml", text)
                self.assertIn("GPT-6.1 Sol", text)
        self.assertTrue((AGENTS / "high-consequence-reviewer-high.toml").is_file())

    def test_low_effort_pilot_excludes_high_consequence_work(self):
        text = tomllib.loads((AGENTS / "project-routine-implementer.toml").read_text())[
            "developer_instructions"]
        for boundary in ("opt-in pilot", "Exclude boot/recovery policy",
                         "storage writers", "data migration", "credentials",
                         "heater/motion safety", "release decisions",
                         "before editing", "one bounded correction",
                         "separate verifier"):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, text)

    def test_test_runner_only_produces_prescribed_evidence(self):
        text = tomllib.loads((AGENTS / "project-test-runner.toml").read_text())[
            "developer_instructions"]
        for boundary in ("exact reviewed commands", "deterministic script directly",
                         "physical block devices", "hardware passthrough",
                         "Do not change production code", "timeout is not permission",
                         "do not repair", "Never invent token"):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, text)

    def test_new_rollout_and_template_local_links_resolve(self):
        for relative in ("docs/development/codex-model-routing.md",
                         ".codex/templates/agent-task-observation.md"):
            source = ROOT / relative
            text = source.read_text(encoding="utf-8")
            for link in re.findall(r"\]\(([^)]+)\)", text):
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = (source.parent / unquote(parsed.path)).resolve()
                with self.subTest(source=relative, link=link):
                    self.assertTrue(target.is_relative_to(ROOT))
                    self.assertTrue(target.exists(), f"missing link target: {link}")


if __name__ == "__main__":
    unittest.main()
