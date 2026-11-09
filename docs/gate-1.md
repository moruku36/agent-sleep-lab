# Gate 1: offline contract validation

[日本語](gate-1.ja.md) | [Home](../README.md)

Status: locally accepted on macOS arm64 / CPython 3.13.18. See the [acceptance report](../reports/gate-1-progress.md) for executed checks and limits. GitHub publication and CI state must be verified separately.

## Boundary

This slice is a read-only validator for event JSONL, memory JSON objects/arrays, and single promotion-request JSON objects. It uses packaged copies of the repository's Draft-07 and 2020-12 schemas and refuses external schema resolution. The schema dialect URI is an identifier, not an instruction to download anything.

Validation does not authenticate a verifier, inspect opaque evidence/receipt references, check current authorization or exclusions, or adopt memory. The synthetic promotion example is structurally valid but unusable for adoption. No durable writer, capture/retrieval adapter, sleep provider, schedule, or performance experiment is implemented by this gate. SLP-01–12 runtime acceptance remains pending.

## Development installation and usage

Requires Python 3.11+; the development interpreter is pinned to 3.13.18. Use [official uv](https://docs.astral.sh/uv/getting-started/installation/) (verified locally with 0.13.7) without replacing the system Python:

```sh
uv python install 3.13.18 --no-bin
uv venv --python 3.13.18 .venv
uv pip install --python .venv/bin/python --require-hashes -r requirements-dev.lock
uv pip install --python .venv/bin/python --no-deps -e .
.venv/bin/python tools/check_environment.py
.venv/bin/python tests/run_tests.py
.venv/bin/python tools/check_docs.py
.venv/bin/agent-sleep-lab schemas
.venv/bin/agent-sleep-lab validate events examples/events.synthetic.jsonl
.venv/bin/agent-sleep-lab validate memory examples/memory.candidates.synthetic.json --format json
.venv/bin/agent-sleep-lab validate promotion examples/promotion-request.synthetic.json
```

`requirements.txt` pins direct runtime dependencies, not their full dependency tree. `requirements-dev.txt` adds the requested [official OpenAI Python SDK](https://github.com/openai/openai-python), version 3.48.0, as a development dependency only. `requirements-dev.lock` captures the resolved development tree and distribution hashes on macOS arm64/Python 3.13; it is not a claim of acceptance on every platform. No API calls or credentials are needed for the checks above. The CLI's runtime dependencies do not include OpenAI, and the read-only gate does not call a provider.

Exit codes: `0` valid, including warnings; `1` invalid content; `2` usage, unreadable input, or schema-loading failure. Diagnostics are text by default; `--format json` selects JSON validation results. `--max-diagnostics` limits displayed diagnostics (default 50; range 1–1000). Read errors are printed to stderr even in JSON mode.

## Implemented checks

- Strict UTF-8/JSON: reject BOMs, duplicate keys, lone surrogates, NaN/Infinity and float overflow, malformed syntax, and excessive nesting. Large integers are bounded by the supported interpreter's default digit limit.
- Contract version, required fields, extra fields, types, and RFC3339 date-time formats. No UTC normalization is performed.
- Input-local consistency: identical event/memory ID repeats warn; conflicting repeats error. Reject self-correction, self-supersession, unconfirmed verified memories, and verified hypotheses. These checks are not provenance enforcement or authenticated verification.
- Read regular files only, with bounded reads: 8 MiB/file, 1 MiB/event line, 10,000 records, 64 container levels, and 10 displayed schema errors per record plus a summary diagnostic.
- Event JSONL uses physical newline-separated records; blank lines are errors. An empty file or memory array produces a warning, not adoption or a successful sleep run.

## Wheel acceptance

```sh
uv build --wheel --out-dir dist
uv venv --python 3.13.18 .venv-wheel
uv pip install --python .venv-wheel/bin/python dist/agent_sleep_lab-0.1.0.dev0-py3-none-any.whl
```

Then invoke `.venv-wheel/bin/python tools/check_installed.py /absolute/checkout/path` using absolute paths and a working directory outside the checkout. This was executed successfully locally: all three synthetic examples, packaged schema loading, invalid-content exit 1, and missing-file exit 2. The helper checks that the imported module is not the source tree.

A CI workflow defines these contract and wheel checks for Python 3.11 and 3.13 on Linux; consult its actual GitHub run before claiming those environments passed. No performance result or memory adoption follows from these checks.
