# Core baseline and recovery boundary

- Repository: https://github.com/moruku36/agent-sleep-lab
- Baseline commit: 9853c4e993fefadab003c52b5a30729c6ddfa683
- Observed as main on: 2026-11-17 JST
- [Browse the exact baseline](https://github.com/moruku36/agent-sleep-lab/tree/9853c4e993fefadab003c52b5a30729c6ddfa683)
- This is a code baseline, not a backup or attestation of any user's runtime database.

Core development may continue after this revision. Keep experiment code in its
own directory and commits. Pin the supported core revision in the experiment's
future dependency/manifest files; deliberately review updates rather than
implicitly using whatever main points at.

Operational rollback: stop the experiment and use the core retrieval path.
Code rollback: revert experiment commits, preserving later unrelated core commits.
Historical inspection: check out this SHA in a separate worktree.
Never force-reset shared main or restore an old SQLite copy over current work.
No database migration is required by this design. A later independently approved
core schema migration has its own compatibility and recovery rules.
