# Gate 1 acceptance — 2026-11-10 JST

Status: **local acceptance passed** on macOS arm64 / CPython 3.13.18. GitHub publication and Linux CI status are separate observations; consult the feature branch and actual workflow runs.

## Delivered

Claude Code (`claude-sonnet-5-5`) authored the strict JSON parser, offline validator, read-only CLI, three packaged schemas and unittest suites. Review added a declared/pinned direct `referencing` dependency, reusable acceptance entry files, bilingual usage/status documentation, development dependency records and a Linux CI workflow. This development model use is not a sleep-harness provider integration.

The requested official [OpenAI Python SDK](https://github.com/openai/openai-python) 3.48.0 is installed and imports successfully as a **development dependency only**. No API client, credentials, or paid provider call was used to validate it.

## Executed acceptance

- `tests/run_tests.py`: **87 tests passed**. Covers strict parser errors, date-time checking, versions/extra fields, local consistency, bounded diagnostics, external schema rejection, read-only input behavior, CLI results, dependency pins, exact packaged-schema byte equality and all synthetic examples.
- `uv build --wheel --out-dir dist`: built `agent_sleep_lab-0.1.0.dev0-py3-none-any.whl` with all three schemas.
- Installed that wheel in a separate environment without the OpenAI SDK or an editable checkout.
- Invoked `tools/check_installed.py` from outside the checkout: imported the installed package, loaded packaged schemas, validated events (4 records), memory (1), and promotion (1), and checked invalid-content exit 1 / missing-input exit 2. All passed.
- `tools/check_environment.py`: Python 3.13.18; openai 3.48.0; jsonschema 4.23.0; referencing 0.37.0; rfc3339-validator 0.1.4.

## Environment and reproducibility

Used the native uv 0.13.7 macOS arm64 archive from the official Astral release, with downloaded SHA-256 matching release metadata: `81b811b57e4624df7ed3aac148e0359100d9962f3d9dce00aec533dc2e086731`.

Managed Python 3.13.18 and project environments are separate from system Python. No shell profile, system Python, or execution-approval setting was changed. The previous interpreter-module environment-creation command remained denied; a standard native package-manager operation was separately reviewed and allowed. This is not a remaining environment blocker.

`.python-version` selects the development interpreter. `requirements.txt` pins direct runtime dependencies; `requirements-dev.txt` adds the SDK; `requirements-dev.lock` records the resolved development tree with distribution hashes on the acceptance platform. Cross-platform lock acceptance is not claimed. Binary environments, caches and wheel/build outputs are excluded from source control.

## Limits

This gate checks structure and input-local consistency, not evidence truth, reference existence/hashes, trusted verifier identity, authorization/exclusions, transactional adoption, retrieval or model performance. SLP-01–12 runtime acceptance remains pending. Structurally valid synthetic requests are not adoptable memories. No scheduling, active-memory mutation or real-agent connection was introduced.

The wheel build succeeds but setuptools warns that the existing TOML-table license declaration is deprecated; this is recorded rather than silently selecting a new license. Linux/Python 3.11 and 3.13 checks are defined in CI; their actual outcomes must be read from GitHub. Test-suite execution is not independent security certification or a performance experiment.

[Usage](../docs/gate-1.md) / [日本語](../docs/gate-1.ja.md).
