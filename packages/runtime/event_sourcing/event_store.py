import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .events import EventType, ImmutableEvent


try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class IntegrityViolationError(Exception):
    """Raised when tamper detection or chain broken in event log."""
    pass


@dataclass(frozen=True)
class SignedCheckpoint:
    """Cryptographically signed audit checkpoint over cumulative event chain.

    Supports both:
    1. Asymmetric Ed25519 signatures (Writer has private key, Auditor has public key).
    2. Symmetric HMAC-SHA256 signatures.
    """
    checkpoint_id: str
    trace_id: str
    event_count: int
    cumulative_chain_hash: str
    timestamp: float
    signer_id: str
    signature: str
    signature_scheme: str = "ed25519"  # "ed25519" or "hmac-sha256"
    key_id: Optional[str] = None
    public_key_hex: Optional[str] = None

    def canonical_bytes(self) -> bytes:
        msg = f"{self.checkpoint_id}:{self.trace_id}:{self.event_count}:{self.cumulative_chain_hash}:{self.timestamp}:{self.signer_id}:{self.key_id or ''}"
        return msg.encode("utf-8")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "trace_id": self.trace_id,
            "event_count": self.event_count,
            "cumulative_chain_hash": self.cumulative_chain_hash,
            "timestamp": self.timestamp,
            "signer_id": self.signer_id,
            "signature": self.signature,
            "signature_scheme": self.signature_scheme,
            "key_id": self.key_id,
            "public_key_hex": self.public_key_hex,
        }


class EventStore:
    """In-memory and file-backed append-only event store with hash-chain integrity verification."""

    def __init__(self):
        self._traces: Dict[str, List[ImmutableEvent]] = {}
        self._last_event_hash: Dict[str, Optional[str]] = {}
        self._checkpoints: Dict[str, List[SignedCheckpoint]] = {}

    def append(
        self,
        trace_id: str,
        event_type: EventType,
        logical_tick: int,
        payload: Dict,
    ) -> ImmutableEvent:
        """Append an event to the trace, chaining hash to the previous event."""
        prev_hash = self._last_event_hash.get(trace_id)
        evt = ImmutableEvent.create(
            event_type=event_type,
            trace_id=trace_id,
            logical_tick=logical_tick,
            payload=payload,
            previous_event_hash=prev_hash,
        )
        if trace_id not in self._traces:
            self._traces[trace_id] = []
        self._traces[trace_id].append(evt)
        self._last_event_hash[trace_id] = evt.compute_event_hash()
        return evt

    def get_trace(self, trace_id: str) -> List[ImmutableEvent]:
        """Fetch chronological event list for trace."""
        return list(self._traces.get(trace_id, []))

    def verify_chain_integrity(self, trace_id: str) -> Tuple[bool, Optional[str]]:
        """Verify SHA256 cryptographic chain integrity across all events in a trace."""
        events = self._traces.get(trace_id, [])
        if not events:
            return True, None

        expected_prev_hash: Optional[str] = None
        for idx, evt in enumerate(events):
            # Verify payload hash matches actual payload
            actual_p_hash = hashlib.sha256(json.dumps(evt.payload, sort_keys=True).encode("utf-8")).hexdigest()
            if evt.payload_hash != actual_p_hash:
                return False, f"Payload hash mismatch at index {idx} (event {evt.event_id}): payload was modified"

            if evt.previous_event_hash != expected_prev_hash:
                return False, (
                    f"Integrity check failed at index {idx} (event {evt.event_id}): "
                    f"expected prev_hash {expected_prev_hash}, got {evt.previous_event_hash}"
                )
            expected_prev_hash = evt.compute_event_hash()

        return True, None

    def save_to_jsonl(self, trace_id: str, path: Path | str) -> int:
        """Persist trace to JSONL file."""
        events = self.get_trace(trace_id)
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt.to_dict()) + "\n")
        return len(events)

    def load_from_jsonl(self, path: Path | str) -> str:
        """Load trace from JSONL file and register in memory."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Trace file not found: {p}")

        loaded_trace_id: Optional[str] = None
        events: List[ImmutableEvent] = []

        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                evt = ImmutableEvent(
                    event_id=d["event_id"],
                    event_type=EventType(d["event_type"]),
                    trace_id=d["trace_id"],
                    logical_tick=d["logical_tick"],
                    timestamp=d["timestamp"],
                    payload=d["payload"],
                    payload_hash=d["payload_hash"],
                    previous_event_hash=d.get("previous_event_hash"),
                )
                if loaded_trace_id is None:
                    loaded_trace_id = evt.trace_id
                events.append(evt)

        if not loaded_trace_id:
            raise ValueError("No events found in file")

        self._traces[loaded_trace_id] = events
        self._last_event_hash[loaded_trace_id] = events[-1].compute_event_hash() if events else None

        ok, err = self.verify_chain_integrity(loaded_trace_id)
        if not ok:
            raise IntegrityViolationError(f"Loaded trace corrupted: {err}")

        return loaded_trace_id

    def create_signed_checkpoint(
        self,
        trace_id: str,
        signing_key: str,
        signer_id: str = "security-officer",
    ) -> SignedCheckpoint:
        """Issue an authentic HMAC-SHA256 signed audit checkpoint over cumulative chain."""
        events = self.get_trace(trace_id)
        if not events:
            raise ValueError(f"Trace '{trace_id}' has no events to checkpoint")

        ok, err = self.verify_chain_integrity(trace_id)
        if not ok:
            raise IntegrityViolationError(f"Cannot checkpoint corrupted trace: {err}")

        cum_hash = events[-1].compute_event_hash()
        now = time.time()
        chk_id = f"chk-{uuid.uuid4().hex[:12]}"
        msg = f"{chk_id}:{trace_id}:{len(events)}:{cum_hash}:{now}:{signer_id}"
        sig = hmac.new(signing_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()

        checkpoint = SignedCheckpoint(
            checkpoint_id=chk_id,
            trace_id=trace_id,
            event_count=len(events),
            cumulative_chain_hash=cum_hash,
            timestamp=now,
            signer_id=signer_id,
            signature=sig,
        )
        if trace_id not in self._checkpoints:
            self._checkpoints[trace_id] = []
        self._checkpoints[trace_id].append(checkpoint)
        return checkpoint

    def verify_checkpoint(
        self,
        checkpoint: SignedCheckpoint,
        signing_key: str,
    ) -> Tuple[bool, Optional[str]]:
        """Verify HMAC signature and assert that cumulative chain hash matches event history."""
        msg = f"{checkpoint.checkpoint_id}:{checkpoint.trace_id}:{checkpoint.event_count}:{checkpoint.cumulative_chain_hash}:{checkpoint.timestamp}:{checkpoint.signer_id}"
        expected_sig = hmac.new(signing_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, checkpoint.signature):
            return False, "Cryptographic signature mismatch: checkpoint signature invalid"

        # Verify underlying event integrity
        ok, err = self.verify_chain_integrity(checkpoint.trace_id)
        if not ok:
            return False, f"Event chain compromised: {err}"

        events = self.get_trace(checkpoint.trace_id)
        if len(events) < checkpoint.event_count:
            return False, f"Event count mismatch: expected at least {checkpoint.event_count}, got {len(events)}"

        target_event = events[checkpoint.event_count - 1]
        if target_event.compute_event_hash() != checkpoint.cumulative_chain_hash:
            return False, "Cumulative chain hash mismatch against actual event log"

        return True, None

    @staticmethod
    def generate_ed25519_keypair() -> Tuple[Any, Any]:
        """Generate an Ed25519 private/public keypair."""
        if not HAS_CRYPTOGRAPHY:
            raise RuntimeError("cryptography package required for Ed25519 keys")
        priv = ed25519.Ed25519PrivateKey.generate()
        return priv, priv.public_key()

    def create_asymmetric_checkpoint(
        self,
        trace_id: str,
        private_key: Any,
        signer_id: str = "security-officer",
        key_id: Optional[str] = None,
    ) -> SignedCheckpoint:
        """Issue an authentic Ed25519 asymmetric signed audit checkpoint over cumulative chain."""
        events = self.get_trace(trace_id)
        if not events:
            raise ValueError(f"Trace '{trace_id}' has no events to checkpoint")

        ok, err = self.verify_chain_integrity(trace_id)
        if not ok:
            raise IntegrityViolationError(f"Cannot checkpoint corrupted trace: {err}")

        cum_hash = events[-1].compute_event_hash()
        now = time.time()
        chk_id = f"chk-{uuid.uuid4().hex[:12]}"
        kid = key_id or f"key-{uuid.uuid4().hex[:8]}"

        pub_bytes = private_key.public_key().public_bytes_raw()
        pub_hex = pub_bytes.hex()

        temp_chk = SignedCheckpoint(
            checkpoint_id=chk_id,
            trace_id=trace_id,
            event_count=len(events),
            cumulative_chain_hash=cum_hash,
            timestamp=now,
            signer_id=signer_id,
            signature="",
            signature_scheme="ed25519",
            key_id=kid,
            public_key_hex=pub_hex,
        )

        sig_bytes = private_key.sign(temp_chk.canonical_bytes())
        sig_hex = sig_bytes.hex()

        checkpoint = SignedCheckpoint(
            checkpoint_id=chk_id,
            trace_id=trace_id,
            event_count=len(events),
            cumulative_chain_hash=cum_hash,
            timestamp=now,
            signer_id=signer_id,
            signature=sig_hex,
            signature_scheme="ed25519",
            key_id=kid,
            public_key_hex=pub_hex,
        )

        if trace_id not in self._checkpoints:
            self._checkpoints[trace_id] = []
        self._checkpoints[trace_id].append(checkpoint)
        return checkpoint

    def verify_asymmetric_checkpoint(
        self,
        checkpoint: SignedCheckpoint,
        public_key: Optional[Any] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Verify Ed25519 signature with public key (Auditor trust model)."""
        if checkpoint.signature_scheme != "ed25519":
            return False, f"Unsupported signature scheme for asymmetric verification: '{checkpoint.signature_scheme}'"

        if public_key is None:
            if not checkpoint.public_key_hex:
                return False, "No public key available to verify checkpoint"
            try:
                pub_bytes = bytes.fromhex(checkpoint.public_key_hex)
                pub = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            except Exception as e:
                return False, f"Failed to deserialize public key: {e}"
        else:
            pub = public_key

        sig_bytes = bytes.fromhex(checkpoint.signature)
        canonical = checkpoint.canonical_bytes()
        try:
            pub.verify(sig_bytes, canonical)
        except Exception:
            return False, "Ed25519 asymmetric signature verification failed: checkpoint tampered"

        # Verify underlying chain integrity
        ok, err = self.verify_chain_integrity(checkpoint.trace_id)
        if not ok:
            return False, f"Event chain compromised: {err}"

        events = self.get_trace(checkpoint.trace_id)
        if len(events) < checkpoint.event_count:
            return False, f"Event count mismatch: expected at least {checkpoint.event_count}, got {len(events)}"

        target_event = events[checkpoint.event_count - 1]
        if target_event.compute_event_hash() != checkpoint.cumulative_chain_hash:
            return False, "Cumulative chain hash mismatch against actual event log"

        return True, None
