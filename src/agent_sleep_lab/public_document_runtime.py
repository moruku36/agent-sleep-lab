"""One-document public-data lifecycle v1, separate from all synthetic stores.

Trusted host code configures control, deterministic review and consumer boundaries
separately from proposals. These local capabilities are NOT authentication or a
sandbox against code with filesystem/Python access. No fetching or model client.
Every content API resolves the persisted current control under a SQLite lock.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from threading import Lock

from .provenance import canonical_json, sha256_hex
from .public_source_intake import (
    PublicDocumentApproval, _identifier, _stamp, recheck_public_document,
)
from .strictjson import loads_strict_bytes
from .public_document_sleep import (
    SleepLimits, PublicDocumentSleepError, build_light_request, build_deep_request,
    parse_deep_result,
)

VERSION = "agent-sleep-public-document/1"
EXCERPT_PROTOCOL = "exact-source-quotation/1"
EVALUATION_PROTOCOL = "excerpt-snapshot-mechanical/1"
EMPTY_HEAD = sha256_hex(canonical_json([]))
MAX_CONTENT_BYTES = 512 * 1024


class PublicDocumentError(ValueError):
    """Fail-closed lifecycle or binding violation; contains no source text."""


@dataclass(frozen=True)
class Authority:
    identity: str
    version: str

    def __post_init__(self):
        _identifier(self.identity)
        _identifier(self.version)


@dataclass(frozen=True)
class Consumer:
    identity: str
    version: str
    runtime_permission: str
    max_input_bytes: int
    max_output_bytes: int

    def __post_init__(self):
        for item in (self.identity, self.version, self.runtime_permission):
            _identifier(item)
        for value in (self.max_input_bytes, self.max_output_bytes):
            _bound(value)


def _bound(value):
    if type(value) is not int or not 1 <= value <= MAX_CONTENT_BYTES:
        raise PublicDocumentError("explicit positive byte bound required")
    return value


def _hash(value):
    if (type(value) is not str or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)):
        raise PublicDocumentError("SHA-256 required")
    return value


def _json(data):
    return loads_strict_bytes(bytes(data))


def _fingerprint(value):
    return sha256_hex(canonical_json(value))


def _execution_identity(request):
    # The dedicated store and current generation bind the control domain; complete
    # attributed reference bytes bind the source. Snapshot lineage/request IDs are
    # exact provenance, not fresh authorization for the same effective execution.
    return _fingerprint({key: request[key] for key in (
        "schema_version", "generation", "target_task", "scope",
        "task_input_sha256", "reference_sha256", "consumer",
    )})


def _now(clock):
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PublicDocumentError("trusted clock must return timezone-aware time")
    return value


class _Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class PublicDocumentStore:
    """Private dedicated SQLite bundle. Open never initializes an absent store.

    Source/evidence, proposals, memory/snapshots, request and result bytes all live
    in the managed content table. No external artifact/export is implicitly owned.
    The host must retain its own control/review capability, never pass it to an
    untrusted provider, and protect the database from unauthorized local writers.
    """

    @classmethod
    def create(cls, path, *, control, verifier, evaluator, semantic_reviewer,
               consumer, clock=lambda: datetime.now(timezone.utc)):
        for role in (control, verifier, evaluator, semantic_reviewer):
            if type(role) is not Authority:
                raise PublicDocumentError("separate authority configuration required")
        if len({r.identity for r in (control, verifier, evaluator, semantic_reviewer)}) != 4:
            raise PublicDocumentError("independent role identities required")
        if type(consumer) is not Consumer:
            raise PublicDocumentError("explicit consumer configuration required")
        if consumer.identity in {r.identity for r in (control, verifier, evaluator, semantic_reviewer)}:
            raise PublicDocumentError("consumer cannot be an authority")
        path = Path(path)
        # Exclusive creation: do not initialize or overwrite another bundle.
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb"):
            pass
        db = sqlite3.connect(path)
        try:
            db.executescript("""
                PRAGMA journal_mode=DELETE;
                PRAGMA secure_delete=ON;
                CREATE TABLE config (body BLOB NOT NULL);
                CREATE TABLE control (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    generation INTEGER NOT NULL, revision INTEGER NOT NULL,
                    state TEXT NOT NULL, body BLOB,
                    artifact_hash TEXT, source_hash TEXT, origin_task TEXT,
                    admitted_generation INTEGER, head TEXT NOT NULL);
                CREATE TABLE content (
                    key TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    digest TEXT NOT NULL, body BLOB NOT NULL);
                CREATE TABLE reviews (
                    digest TEXT PRIMARY KEY, kind TEXT NOT NULL, body BLOB NOT NULL);
                CREATE TABLE operations (
                    op_hash TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                    receipt BLOB NOT NULL);
                CREATE TABLE dispatches (
                    request_hash TEXT PRIMARY KEY, binding_hash TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    observation BLOB NOT NULL, result_key TEXT);
                CREATE TABLE semantic_reviews (
                    request_hash TEXT PRIMARY KEY, body BLOB NOT NULL);
                INSERT INTO control VALUES (1,0,0,'empty',NULL,NULL,NULL,NULL,NULL,'');
            """)
            config = {"schema_version": VERSION, "control": asdict(control),
                      "verifier": asdict(verifier), "evaluator": asdict(evaluator),
                      "semantic_reviewer": asdict(semantic_reviewer),
                      "consumer": asdict(consumer)}
            db.execute("INSERT INTO config VALUES (?)", (canonical_json(config),))
            db.execute("UPDATE control SET head=?", (EMPTY_HEAD,))
            db.commit()
        finally:
            db.close()
        return cls(path, clock=clock)

    def __init__(self, path, *, clock=lambda: datetime.now(timezone.utc)):
        self.path = Path(path).resolve()
        self.clock = clock
        with self._connect() as db:
            config = _json(db.execute("SELECT body FROM config").fetchone()[0])
            if config.get("schema_version") != VERSION:
                raise PublicDocumentError("unsupported public document store")

    def _connect(self):
        # Existing-file mode; no migration and no synthetic database fallback.
        try:
            db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=10,
                                 factory=_Connection)
        except sqlite3.Error:
            raise PublicDocumentError("existing public document database required") from None
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA secure_delete=ON")
        if db.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
            db.close()
            raise PublicDocumentError("dedicated DELETE-journal store required")
        return db

    def _role(self, role, identity):
        with self._connect() as db:
            config = _json(db.execute("SELECT body FROM config").fetchone()[0])
            if type(identity) is not Authority or asdict(identity) != config[role]:
                raise PublicDocumentError("configured independent authority required")

    def control(self, identity):
        self._role("control", identity)
        return PublicDocumentControl(self, identity)

    def verifier(self, identity):
        self._role("verifier", identity)
        return ExcerptVerifier(self, identity)

    def evaluator(self, identity):
        self._role("evaluator", identity)
        return MechanicalEvaluator(self, identity)

    def semantic_reviewer(self, identity):
        self._role("semantic_reviewer", identity)
        return SemanticReviewer(self, identity)

    @staticmethod
    def _put(db, key, kind, data):
        if type(data) is not bytes or len(data) > MAX_CONTENT_BYTES:
            raise PublicDocumentError("bounded canonical bytes required")
        digest = sha256_hex(data)
        existing = db.execute("SELECT * FROM content WHERE key=?", (key,)).fetchone()
        if existing:
            if existing["kind"] != kind or existing["digest"] != digest or existing["body"] != data:
                raise PublicDocumentError("immutable content conflict")
        else:
            db.execute("INSERT INTO content VALUES (?,?,?,?)", (key, kind, digest, data))
        return digest

    @staticmethod
    def _get(db, key, kind):
        row = db.execute("SELECT * FROM content WHERE key=? AND kind=?", (key, kind)).fetchone()
        if row is None or sha256_hex(row["body"]) != row["digest"]:
            raise PublicDocumentError("missing or corrupt managed content")
        return bytes(row["body"])

    def _guard(self, db, *, admitted=True):
        c = db.execute("SELECT * FROM control").fetchone()
        now = _now(self.clock)
        if c["state"] != "approved" or c["body"] is None:
            raise PublicDocumentError("current control excludes access")
        approval = PublicDocumentApproval(**_json(c["body"]))
        if not _stamp(approval.approved_at) <= now < _stamp(approval.expires_at):
            raise PublicDocumentError("current control expired or not yet valid")
        if admitted or c["admitted_generation"] is not None:
            if c["admitted_generation"] != c["generation"]:
                raise PublicDocumentError("admitted current-control generation changed")
            artifact = self._get(db, "source", "source_evidence")
            if sha256_hex(artifact) != c["artifact_hash"]:
                raise PublicDocumentError("exact admitted artifact changed")
            recheck_public_document(artifact, approval=approval, now=now)
            # Inventory integrity is checked before *every* managed data access.
            for row in db.execute("SELECT digest,body FROM content"):
                if sha256_hex(row["body"]) != row["digest"]:
                    raise PublicDocumentError("managed derivative integrity failure")
        return c

    @contextmanager
    def _live(self, *, admitted=True):
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            try:
                c = self._guard(db, admitted=admitted)
            except (ValueError, KeyError, TypeError):
                # Commit exclusion before any physical cleanup, even if it fails.
                db.execute("""UPDATE control SET generation=generation+1,state='purge_pending'
                              WHERE state='approved'""")
                db.commit()
                db.close()
                db = None
                self.purge()
                raise PublicDocumentError("document excluded; cleanup required or completed") from None
            yield db, c
            db.commit()
        except BaseException:
            if db is not None:
                db.rollback()
            raise
        finally:
            if db is not None:
                db.close()

    def sweep(self):
        """Explicit expiry/integrity sweep; never installs a timer."""
        try:
            with self._live(admitted=False):
                pass
        except PublicDocumentError:
            pass
        return self.audit()

    def audit(self):
        """Content-free suppression/operation summary, including after deletion."""
        with self._connect() as db:
            c = db.execute("SELECT * FROM control").fetchone()
            return {"schema_version": VERSION, "generation": c["generation"],
                    "state": c["state"], "artifact_sha256": c["artifact_hash"],
                    "source_sha256": c["source_hash"],
                    "managed_records": db.execute("SELECT count(*) FROM content").fetchone()[0],
                    "operation_count": db.execute("SELECT count(*) FROM operations").fetchone()[0]}

    def inventory(self):
        """No text; still requires current eligibility."""
        with self._live() as (db, _):
            return [dict(row) for row in db.execute(
                "SELECT kind,digest,length(body) AS bytes FROM content ORDER BY key")]

    def purge(self):
        """Crash-resumable deletion of this bundle's managed content only.

        First durably purge_pending, then secure_delete + VACUUM, finally deleted.
        Interruption/failure is never reported as physical deletion. Not forensic
        erasure of SSD snapshots/backups or of caller/remote exports.
        """
        db = self._connect()
        try:
            c = db.execute("SELECT state FROM control").fetchone()
            if c["state"] not in ("purge_pending", "deleted"):
                raise PublicDocumentError("explicit exclusion required before purge")
            if c["state"] == "deleted":
                return
            db.execute("BEGIN IMMEDIATE")
            for table in ("content", "reviews", "dispatches", "semantic_reviews"):
                db.execute("DELETE FROM " + table)
            db.execute("""UPDATE control SET body=NULL,origin_task=NULL,
                          admitted_generation=NULL,head=?""", (EMPTY_HEAD,))
            db.commit()
            self._compact(db)
            db.execute("UPDATE control SET state='deleted' WHERE state='purge_pending'")
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _compact(db):
        db.execute("VACUUM")

    def admit(self, artifact):
        with self._live(admitted=False) as (db, c):
            if type(artifact) is not bytes or sha256_hex(artifact) != c["artifact_hash"]:
                raise PublicDocumentError("artifact not bound by current control")
            approval = PublicDocumentApproval(**_json(c["body"]))
            recheck_public_document(artifact, approval=approval, now=_now(self.clock))
            self._put(db, "source", "source_evidence", artifact)
            db.execute("UPDATE control SET admitted_generation=generation")
            return {"artifact_sha256": c["artifact_hash"], "generation": c["generation"]}

    @contextmanager
    def _sleep_live(self):
        try:
            with self._live() as live:
                yield live
        except PublicDocumentSleepError:
            raise PublicDocumentError("invalid offline sleep protocol or bounds") from None

    def _sleep_current(self, db, c, sleep_id):
        """Reconstruct the saved request from CURRENT admitted body/control/head."""
        data = self._get(db, "sleep:" + sleep_id + ":light_request", "sleep_light_request")
        saved = _json(data)
        approval = _json(c["body"])
        artifact = _json(self._get(db, "source", "source_evidence"))
        expected = build_light_request(
            sleep_id=sleep_id, artifact_sha256=c["artifact_hash"],
            source_sha256=c["source_hash"], generation=c["generation"],
            scope={k: approval[k] for k in ("project", "task_family")},
            expected_parent=c["head"], origin_task=c["origin_task"],
            source_text=artifact["source"]["text"], limits=SleepLimits(**saved["limits"]))
        if data != expected:
            raise PublicDocumentError("sleep source, scope, generation or parent no longer current")
        return data

    def prepare_sleep(self, *, sleep_id, scope, expected_generation, expected_parent, limits):
        """Save/return canonical Light bytes, WITHOUT dispatch or authority issuance.

        No provider callback, live option or synthetic coordinator is involved.
        Exact current-bound replay returns the same bytes; a changed binding fails.
        """
        _identifier(sleep_id)
        with self._sleep_live() as (db, c):
            approval = _json(c["body"])
            if (type(expected_generation) is not int or expected_generation != c["generation"]
                    or expected_parent != c["head"] or type(scope) is not dict
                    or scope != {k: approval[k] for k in ("project", "task_family")}):
                raise PublicDocumentError("sleep current-control, scope or parent conflict")
            artifact = _json(self._get(db, "source", "source_evidence"))
            data = build_light_request(
                sleep_id=sleep_id, artifact_sha256=c["artifact_hash"],
                source_sha256=c["source_hash"], generation=c["generation"], scope=scope,
                expected_parent=expected_parent, origin_task=c["origin_task"],
                source_text=artifact["source"]["text"], limits=limits)
            self._put(db, "sleep:" + sleep_id + ":light_request", "sleep_light_request", data)
            return data

    def submit_light_result(self, *, sleep_id, expected_request_sha256, result_bytes):
        """Save a strict offline reply; return selected-only Deep bytes or None.

        Empty selection is terminal no-change, not permission to introduce evidence.
        Saved replies are not authenticated model responses or execution receipts.
        """
        _identifier(sleep_id)
        _hash(expected_request_sha256)
        with self._sleep_live() as (db, c):
            request = self._sleep_current(db, c, sleep_id)
            if sha256_hex(request) != expected_request_sha256:
                raise PublicDocumentError("light request hash conflict")
            deep = build_deep_request(request, result_bytes)  # validates WHOLE reply
            prefix = "sleep:" + sleep_id
            self._put(db, prefix + ":light_reply", "sleep_light_reply", result_bytes)
            if deep is None:
                self._put(db, prefix + ":result", "sleep_result", canonical_json({
                    "state": "no_change", "proposal_ids": [],
                    "light_request_sha256": sha256_hex(request),
                    "light_reply_sha256": sha256_hex(result_bytes)}))
            else:
                self._put(db, prefix + ":deep_request", "sleep_deep_request", deep)
            return deep

    def submit_deep_result(self, *, sleep_id, expected_request_sha256, result_bytes):
        """Atomically save ALL valid excerpts as UNVERIFIED proposals, or none.

        No reviews/receipts, snapshots, memory, head or operation are written.
        Exact byte replay is idempotent only while source/control/parent stay current.
        """
        _identifier(sleep_id)
        _hash(expected_request_sha256)
        with self._sleep_live() as (db, c):
            light = self._sleep_current(db, c, sleep_id)
            prefix = "sleep:" + sleep_id
            light_reply = self._get(db, prefix + ":light_reply", "sleep_light_reply")
            request = build_deep_request(light, light_reply)
            if request is None:
                raise PublicDocumentError("empty Light is terminal; Deep evidence forbidden")
            if (self._get(db, prefix + ":deep_request", "sleep_deep_request") != request
                    or sha256_hex(request) != expected_request_sha256):
                raise PublicDocumentError("deep request binding conflict")
            excerpts = parse_deep_result(request, result_bytes)  # before ANY writes
            self._put(db, prefix + ":deep_reply", "sleep_deep_reply", result_bytes)
            binding = _json(request)
            proposal_ids = []
            for index, excerpt in enumerate(excerpts):
                # Host-generated IDs cannot escape this run or choose another proposal.
                proposal_id = "sleep-" + _fingerprint(sleep_id) + "-" + str(index + 1)
                proposal = {
                    "schema_version": VERSION, "kind": "source_attributed_excerpt",
                    "proposal_id": proposal_id, "quotation": excerpt["quotation"],
                    "source_sha256": c["source_hash"], "artifact_sha256": c["artifact_hash"],
                    "generation": c["generation"], "untrusted": True, "authority": False,
                    "sleep_binding": {
                        "sleep_id": sleep_id, "deep_request_sha256": sha256_hex(request),
                        "source_selection_sha256": binding["source_selection_sha256"],
                        "unit_id": excerpt["unit_id"],
                        "source_unit_sha256": excerpt["source_unit_sha256"],
                    },
                }
                self._put(db, "proposal:" + proposal_id, "proposal", canonical_json(proposal))
                proposal_ids.append(proposal_id)
            result = {"state": "unverified_proposals" if proposal_ids else "no_change",
                      "proposal_ids": proposal_ids, "deep_request_sha256": sha256_hex(request),
                      "deep_reply_sha256": sha256_hex(result_bytes)}
            self._put(db, prefix + ":result", "sleep_result", canonical_json(result))
            return result

    def propose_excerpt(self, *, proposal_id, quotation):
        """Unverified immutable data; never executes source prose or issues receipts."""
        _identifier(proposal_id)
        if type(quotation) is not str or not quotation or len(quotation.encode("utf-8")) > 65536:
            raise PublicDocumentError("bounded nonempty quotation required")
        with self._live() as (db, c):
            proposal = {"schema_version": VERSION, "kind": "source_attributed_excerpt",
                        "proposal_id": proposal_id, "quotation": quotation,
                        "source_sha256": c["source_hash"], "artifact_sha256": c["artifact_hash"],
                        "generation": c["generation"], "untrusted": True,
                        "authority": False}
            digest = self._put(db, "proposal:" + proposal_id, "proposal", canonical_json(proposal))
            return digest

    def read_proposal(self, proposal_id):
        _identifier(proposal_id)
        with self._live() as (db, _):
            return _json(self._get(db, "proposal:" + proposal_id, "proposal"))

    def _candidate(self, db, c, proposal_id, parent):
        _hash(parent)
        proposal_bytes = self._get(db, "proposal:" + proposal_id, "proposal")
        proposal = _json(proposal_bytes)
        if proposal["generation"] != c["generation"]:
            raise PublicDocumentError("stale proposal generation")
        record = {"kind": "source_attributed_excerpt", "quotation": proposal["quotation"],
                  "source_uri": _json(c["body"])["source_uri"],
                  "source_sha256": c["source_hash"], "artifact_sha256": c["artifact_hash"],
                  "scope": {k: _json(c["body"])[k] for k in ("project", "task_family")},
                  "untrusted": True, "authority": False}
        members = [] if parent == EMPTY_HEAD else _json(self._get(db, "snapshot:" + parent, "snapshot"))["records"]
        if record not in members:
            members.append(record)
        snapshot = {"schema_version": VERSION, "parent": parent, "generation": c["generation"],
                    "proposal_sha256": sha256_hex(proposal_bytes), "records": members}
        data = canonical_json(snapshot)
        return proposal, snapshot, data

    def candidate_snapshot(self, *, proposal_id, expected_parent):
        """Read-only proposal view. No receipt creation or authority issuance."""
        with self._live() as (db, c):
            if expected_parent != c["head"]:
                raise PublicDocumentError("expected parent conflict")
            _, snapshot, _ = self._candidate(db, c, proposal_id, expected_parent)
            return snapshot

    def _review(self, db, digest, kind, c):
        row = db.execute("SELECT body FROM reviews WHERE digest=? AND kind=?", (digest, kind)).fetchone()
        if row is None or sha256_hex(row["body"]) != digest:
            raise PublicDocumentError("authoritative registered receipt required")
        receipt = _json(row["body"])
        config = _json(db.execute("SELECT body FROM config").fetchone()[0])
        role = "verifier" if kind == "quotation" else "evaluator"
        protocol = EXCERPT_PROTOCOL if kind == "quotation" else EVALUATION_PROTOCOL
        if (receipt["authority"] != config[role] or receipt["protocol"] != protocol
                or receipt["generation"] != c["generation"]
                or not _stamp(receipt["issued_at"]) <= _now(self.clock) < _stamp(receipt["expires_at"])
                or _stamp(receipt["expires_at"]) > _stamp(_json(c["body"])["expires_at"])):
            raise PublicDocumentError("receipt authority, protocol, time or generation mismatch")
        return receipt

    def read_review(self, digest, *, kind):
        if kind not in ("quotation", "mechanical"):
            raise PublicDocumentError("unknown review kind")
        with self._live() as (db, c):
            return self._review(db, _hash(digest), kind, c)

    def adopt(self, *, operation_id, proposal_id, expected_parent, expected_generation,
              verification_receipt, evaluation_receipt):
        _identifier(operation_id)
        _identifier(proposal_id)
        fingerprint = _fingerprint([proposal_id, expected_parent, expected_generation,
                                    verification_receipt, evaluation_receipt])
        op_hash = _fingerprint(operation_id)
        # Replay also sweeps CURRENT control, without resurrecting eligibility.
        self.sweep()
        # Exact historical replay is content-free; it never reactivates a head.
        with self._connect() as db:
            old = db.execute("SELECT * FROM operations WHERE op_hash=?", (op_hash,)).fetchone()
            if old:
                if old["fingerprint"] != fingerprint:
                    raise PublicDocumentError("operation identity conflict")
                receipt = _json(old["receipt"])
                receipt["historical_replay"] = True
                receipt["eligibility_not_asserted"] = True
                return receipt
        with self._live() as (db, c):
            # Recheck after acquiring writer lock for concurrent exact replay.
            old = db.execute("SELECT * FROM operations WHERE op_hash=?", (op_hash,)).fetchone()
            if old:
                if old["fingerprint"] != fingerprint:
                    raise PublicDocumentError("operation identity conflict")
                return dict(_json(old["receipt"]), historical_replay=True,
                            eligibility_not_asserted=True)
            if expected_parent != c["head"] or expected_generation != c["generation"]:
                raise PublicDocumentError("head or current-control CAS conflict")
            proposal, snapshot, data = self._candidate(db, c, proposal_id, expected_parent)
            digest = sha256_hex(data)
            verification = self._review(db, verification_receipt, "quotation", c)
            evaluation = self._review(db, evaluation_receipt, "mechanical", c)
            if (verification["proposal_sha256"] != snapshot["proposal_sha256"]
                    or evaluation["snapshot_sha256"] != digest
                    or evaluation["verification_receipt"] != verification_receipt):
                raise PublicDocumentError("receipt hash binding mismatch")
            self._put(db, "snapshot:" + digest, "snapshot", data)
            self._put(db, "memory:" + snapshot["proposal_sha256"], "memory",
                      canonical_json(next(r for r in snapshot["records"]
                                          if r["quotation"] == proposal["quotation"])))
            receipt = {"schema_version": VERSION, "operation_sha256": op_hash,
                       "fingerprint": fingerprint, "parent": expected_parent, "head": digest,
                       "generation": c["generation"], "verification": verification_receipt,
                       "evaluation": evaluation_receipt, "mechanical_only": True}
            db.execute("INSERT INTO operations VALUES (?,?,?)",
                       (op_hash, fingerprint, canonical_json(receipt)))
            db.execute("UPDATE control SET head=?", (digest,))
            return receipt

    def _retrieve(self, db, c, *, target_task, scope, max_bytes):
        _identifier(target_task)
        _bound(max_bytes)
        a = _json(c["body"])
        if (target_task == c["origin_task"] or type(scope) is not dict
                or scope != {k: a[k] for k in ("project", "task_family")}):
            raise PublicDocumentError("different target task and identical approved scope required")
        if c["head"] == EMPTY_HEAD:
            raise PublicDocumentError("adopted snapshot required")
        snapshot = _json(self._get(db, "snapshot:" + c["head"], "snapshot"))
        selected = []
        for record in snapshot["records"]:
            # Whole canonical records, including attribution, never partial text.
            if len(canonical_json(selected + [record])) <= max_bytes:
                selected.append(record)
        references = canonical_json(selected)
        if not selected:
            raise PublicDocumentError("no whole reference fits retrieval bound")
        return references

    def retrieve(self, *, target_task, scope, max_bytes):
        with self._live() as (db, c):
            return self._retrieve(db, c, target_task=target_task, scope=scope, max_bytes=max_bytes)

    def prepare_request(self, *, request_id, target_task, scope, task_input,
                        reference_max_bytes, consumer):
        _identifier(request_id)
        if type(consumer) is not Consumer or type(task_input) is not str:
            raise PublicDocumentError("explicit consumer and task text required")
        with self._live() as (db, c):
            config = _json(db.execute("SELECT body FROM config").fetchone()[0])
            if asdict(consumer) != config["consumer"]:
                raise PublicDocumentError("consumer permission/identity/version mismatch")
            references = self._retrieve(db, c, target_task=target_task, scope=scope,
                                        max_bytes=reference_max_bytes)
            body = {"schema_version": VERSION, "request_id": request_id,
                    "generation": c["generation"], "snapshot_sha256": c["head"],
                    "target_task": target_task, "scope": scope, "task_input": task_input,
                    "task_input_sha256": sha256_hex(task_input.encode("utf-8")),
                    "references": _json(references), "reference_sha256": sha256_hex(references),
                    "consumer": asdict(consumer), "references_are_untrusted_data": True}
            data = canonical_json(body)
            if len(data) > consumer.max_input_bytes:
                raise PublicDocumentError("whole request exceeds consumer byte bound")
            digest = self._put(db, "request:" + request_id, "request", data)
            return {"state": "prepared", "request_sha256": digest,
                    "generation": c["generation"], "snapshot_sha256": c["head"],
                    "input_bytes": len(data), "semantic_use": "not_reviewed"}

    def read_request(self, request_id):
        _identifier(request_id)
        with self._live() as (db, _):
            return self._get(db, "request:" + request_id, "request")

    def dispatch(self, *, request_id, consumer, invoke):
        """Explicit one-shot call. Durable unknown intent BEFORE consumer entry.

        invoke(exact_request_bytes, observe_input) must acknowledge the exact hash
        at its actual input boundary. Acknowledgment is a local boundary observation,
        NOT authentication, task success, citation verification or semantic use.
        Any exception/crash leaves outcome unknown; never retry after restart.
        """
        _identifier(request_id)
        with self._live() as (db, c):
            data = self._get(db, "request:" + request_id, "request")
            request = _json(data)
            config = _json(db.execute("SELECT body FROM config").fetchone()[0])
            if type(consumer) is not Consumer or asdict(consumer) != config["consumer"]:
                raise PublicDocumentError("configured runtime permission required")
            if (request["consumer"] != asdict(consumer) or request["generation"] != c["generation"]
                    or request["snapshot_sha256"] != c["head"]):
                raise PublicDocumentError("prepared bindings no longer current")
            digest = sha256_hex(data)
            observation = {"state": "dispatch_outcome_unknown", "request_sha256": digest,
                           "input_observed": False, "semantic_use": "not_reviewed"}
            # Keep the existing exact-provenance column/schema, but independently
            # compare effective identity under this same writer lock. Derive it from
            # persisted requests so pre-fix unknown intents remain no-retry too.
            binding_hash = _fingerprint({k: v for k, v in request.items() if k != "request_id"})
            identity = _execution_identity(request)
            for attempted in db.execute("""
                    SELECT d.request_hash,c.body FROM dispatches AS d
                    LEFT JOIN content AS c ON c.kind='request' AND c.digest=d.request_hash"""):
                if attempted["body"] is None:
                    raise PublicDocumentError("missing attempted request binding")
                if (attempted["request_hash"] == digest
                        or _execution_identity(_json(attempted["body"])) == identity):
                    raise PublicDocumentError("dispatch already attempted; no retry or refund")
            db.execute("INSERT INTO dispatches VALUES (?, ?, 'dispatch_outcome_unknown', ?, NULL)",
                       (digest, binding_hash, canonical_json(observation)))
        # New live check immediately before entering separately configured consumer.
        with self._live() as (db, c):
            if c["generation"] != request["generation"] or c["head"] != request["snapshot_sha256"]:
                raise PublicDocumentError("predispatch control changed")

        observer_lock = Lock()
        accepting_input = True

        def observe_input(observed_bytes):
            # Close and the entire observation transaction share one boundary.
            # An in-flight observer finishes before close; queued/late ones reject.
            with observer_lock:
                if not accepting_input:
                    raise PublicDocumentError("input observer is no longer active")
                if type(observed_bytes) is not bytes or observed_bytes != data:
                    raise PublicDocumentError("actual boundary input mismatch")
                with self._live() as (db, c):
                    if c["generation"] != request["generation"]:
                        raise PublicDocumentError("input observation after exclusion")
                    row = db.execute("""SELECT observation FROM dispatches
                                        WHERE request_hash=? AND status='dispatch_outcome_unknown'""",
                                     (digest,)).fetchone()
                    if row is None:
                        raise PublicDocumentError("input observation requires unknown dispatch")
                    current = _json(row["observation"])
                    current.update(input_observed=True, observed_input_sha256=digest)
                    updated = db.execute("""UPDATE dispatches SET observation=?
                                            WHERE request_hash=? AND status='dispatch_outcome_unknown'""",
                                         (canonical_json(current), digest))
                    if updated.rowcount != 1:
                        raise PublicDocumentError("input observation transition conflict")

        try:
            result = invoke(data, observe_input)  # unknown state survives BaseException
        finally:
            with observer_lock:
                accepting_input = False
        with self._live() as (db, c):
            if c["generation"] != request["generation"]:
                raise PublicDocumentError("postreturn control changed; result unusable")
            if type(result) is not bytes or len(result) > consumer.max_output_bytes:
                raise PublicDocumentError("returned output violates byte bound; outcome remains unknown")
            row = db.execute("""SELECT observation FROM dispatches
                                WHERE request_hash=? AND status='dispatch_outcome_unknown'""",
                             (digest,)).fetchone()
            if row is None:
                raise PublicDocumentError("return requires unknown dispatch")
            current = _json(row["observation"])
            if not current["input_observed"]:
                raise PublicDocumentError("no actual boundary input observation; outcome remains unknown")
            result_key = "result:" + digest
            result_hash = self._put(db, result_key, "result", result)
            current.update(state="returned", result_sha256=result_hash, output_bytes=len(result))
            updated = db.execute("""UPDATE dispatches SET status='returned',observation=?,result_key=?
                                    WHERE request_hash=? AND status='dispatch_outcome_unknown'""",
                                 (canonical_json(current), result_key, digest))
            if updated.rowcount != 1:
                raise PublicDocumentError("return transition conflict")
            return current

    def execution_receipt(self, request_id):
        with self._live() as (db, _):
            request = self._get(db, "request:" + _identifier(request_id), "request")
            digest = sha256_hex(request)
            row = db.execute("SELECT observation FROM dispatches WHERE request_hash=?", (digest,)).fetchone()
            if row is None:
                return {"state": "prepared", "request_sha256": digest, "semantic_use": "not_reviewed"}
            receipt = _json(row["observation"])
            review = db.execute("SELECT body FROM semantic_reviews WHERE request_hash=?", (digest,)).fetchone()
            if review:
                receipt["semantic_review"] = _json(review["body"])
            return receipt

    def read_result(self, request_id):
        with self._live() as (db, _):
            request = self._get(db, "request:" + _identifier(request_id), "request")
            row = db.execute("SELECT status,result_key FROM dispatches WHERE request_hash=?",
                             (sha256_hex(request),)).fetchone()
            if row is None or row["status"] != "returned":
                raise PublicDocumentError("no usable returned result")
            return self._get(db, row["result_key"], "result")


class PublicDocumentControl:
    """Trusted host capability; never created from source/provider content."""
    def __init__(self, store, authority):
        self.store, self.authority = store, authority

    def approve(self, *, approval, artifact_sha256, origin_task, expected_generation):
        self.store._role("control", self.authority)
        if type(approval) is not PublicDocumentApproval:
            raise PublicDocumentError("separate exact approval required")
        _hash(artifact_sha256)
        _identifier(origin_task)
        now = _now(self.store.clock)
        if not _stamp(approval.approved_at) <= now < _stamp(approval.expires_at):
            raise PublicDocumentError("approval not currently valid")
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            c = db.execute("SELECT * FROM control").fetchone()
            if (c["generation"] != expected_generation or approval.revision <= c["revision"]
                    or c["state"] not in ("empty", "approved")):
                raise PublicDocumentError("stale control or suppressed document")
            if c["body"] is not None:
                old = PublicDocumentApproval(**_json(c["body"]))
                if approval.ref != old.ref:
                    raise PublicDocumentError("cannot change control identity")
            # Revision changes after admission deliberately exclude old derivatives.
            db.execute("""UPDATE control SET generation=generation+1,revision=?,state='approved',
                          body=?,artifact_hash=?,source_hash=?,origin_task=?""",
                       (approval.revision, canonical_json(asdict(approval)), artifact_sha256,
                        approval.source_sha256, origin_task))
            return c["generation"] + 1

    def withdraw(self, *, expected_generation, purge=True):
        self.store._role("control", self.authority)
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            c = db.execute("SELECT * FROM control").fetchone()
            if c["generation"] != expected_generation or c["state"] != "approved":
                raise PublicDocumentError("stale withdrawal control")
            db.execute("UPDATE control SET generation=generation+1,state='purge_pending'")
        if purge:
            self.store.purge()
        return self.store.audit()


class ExcerptVerifier:
    """Deterministic exact quotation fidelity only, never fact truth or quality."""
    def __init__(self, store, authority):
        self.store, self.authority = store, authority

    def issue(self, *, proposal_id, expires_at):
        self.store._role("verifier", self.authority)
        with self.store._live() as (db, c):
            data = self.store._get(db, "proposal:" + _identifier(proposal_id), "proposal")
            proposal = _json(data)
            source = _json(self.store._get(db, "source", "source_evidence"))["source"]["text"]
            if proposal["quotation"] not in source or proposal["generation"] != c["generation"]:
                raise PublicDocumentError("quotation is not exact current source evidence")
            return _register(db, c, self.store, self.authority, "quotation", EXCERPT_PROTOCOL,
                             {"proposal_sha256": sha256_hex(data), "fidelity_only": True}, expires_at)


class MechanicalEvaluator:
    """Independent fixed snapshot protocol; does not claim task performance."""
    def __init__(self, store, authority):
        self.store, self.authority = store, authority

    def issue(self, *, proposal_id, expected_parent, verification_receipt, expires_at):
        self.store._role("evaluator", self.authority)
        with self.store._live() as (db, c):
            if c["head"] != expected_parent:
                raise PublicDocumentError("evaluation parent conflict")
            _, snapshot, data = self.store._candidate(db, c, proposal_id, expected_parent)
            receipt = self.store._review(db, verification_receipt, "quotation", c)
            if receipt["proposal_sha256"] != snapshot["proposal_sha256"]:
                raise PublicDocumentError("verification belongs to another proposal")
            return _register(db, c, self.store, self.authority, "mechanical", EVALUATION_PROTOCOL,
                             {"snapshot_sha256": sha256_hex(data),
                              "verification_receipt": verification_receipt,
                              "performance_evaluated": False}, expires_at)


def _register(db, c, store, authority, kind, protocol, binding, expires_at):
    now = _now(store.clock)
    if not now < _stamp(expires_at) <= _stamp(_json(c["body"])["expires_at"]):
        raise PublicDocumentError("receipt expiry outside current approval")
    receipt = dict(binding, schema_version=VERSION, authority=asdict(authority),
                   generation=c["generation"], protocol=protocol,
                   issued_at=now.isoformat(), expires_at=expires_at)
    data = canonical_json(receipt)
    digest = sha256_hex(data)
    db.execute("INSERT OR IGNORE INTO reviews VALUES (?,?,?)", (digest, kind, data))
    return digest


class SemanticReviewer:
    """Separate host review of exact request/result; no consumer self-promotion.

    This records a trusted reviewer's explicit judgment, not automated verification
    of human identity or scientific performance. No free-text review is retained.
    """
    def __init__(self, store, authority):
        self.store, self.authority = store, authority

    def record(self, *, request_id, expected_request_sha256, expected_result_sha256,
               semantic_use_confirmed):
        self.store._role("semantic_reviewer", self.authority)
        if type(semantic_use_confirmed) is not bool:
            raise PublicDocumentError("explicit independent semantic decision required")
        with self.store._live() as (db, c):
            data = self.store._get(db, "request:" + _identifier(request_id), "request")
            digest = sha256_hex(data)
            row = db.execute("SELECT * FROM dispatches WHERE request_hash=?", (digest,)).fetchone()
            if row is None or row["status"] != "returned":
                raise PublicDocumentError("separate review requires actual returned result")
            result = self.store._get(db, row["result_key"], "result")
            if digest != expected_request_sha256 or sha256_hex(result) != expected_result_sha256:
                raise PublicDocumentError("semantic review request/result hash mismatch")
            review = {"authority": asdict(self.authority), "generation": c["generation"],
                      "request_sha256": digest, "result_sha256": sha256_hex(result),
                      "semantic_use_confirmed": semantic_use_confirmed,
                      "independent_judgment_not_performance": True}
            db.execute("INSERT INTO semantic_reviews VALUES (?,?)", (digest, canonical_json(review)))
            return review
