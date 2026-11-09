"""Agent Sleep Lab Gate 1: read-only offline contract validation.

Scope: JSON Schema validation of the published v0.1 event/memory contracts and the
``sleep-promotion/1`` request contract, plus a small set of input-local checks.
The CLI remains read-only. Library modules additionally provide synthetic-only
evidence, receipt/policy, candidate and v3 adoption helpers; see gate reports for
limits. No runtime authentication, real adapters, model calls or network access.
"""

__version__ = "0.1.0.dev0"
