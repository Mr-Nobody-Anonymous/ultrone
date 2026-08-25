# Copyright (c) Ultrone Contributors. All rights reserved.
"""Authentication boundary tests (Sprint C).

Proves: authorization consumes an authenticated Principal (never a
caller-supplied string/role), unknown credentials fail closed, audit
records carry the authenticated identity, providers are replaceable
without touching the workflow, and forged client-supplied identity cannot
elevate privileges.
"""

import pytest
from fastapi.testclient import TestClient

from core.contracts import DecisionTrace
from ultrone_hitl.audit_store import InMemoryAuditStore
from ultrone_hitl.authentication import (
    AuthenticationError,
    Authenticator,
    DevelopmentAuthenticator,
    Principal,
    UnauthenticatedError,
)
from ultrone_hitl.decision_workflow import (
    Authorizer,
    DecisionWorkflow,
    Role,
    UnauthorizedActionError,
)


def _workflow():
    store = InMemoryAuditStore()
    wf = DecisionWorkflow(store=store)
    return wf, store


def _trace(decision_id="DEC-AUTH-1"):
    return DecisionTrace(decision_id=decision_id, episode_id="EP-1", tick=1)


class TestPrincipal:
    def test_principal_is_immutable(self):
        p = Principal(subject="bob", role=Role.OPERATOR)
        with pytest.raises(Exception):      # frozen dataclass
            p.role = Role.ADMIN

    def test_audit_projection_shape(self):
        p = Principal(subject="alice", role=Role.SUPERVISOR, display_name="A")
        assert p.to_dict() == {
            "subject": "alice", "role": "supervisor", "display_name": "A",
        }


class TestFailClosed:
    def test_unknown_credential_fails_closed(self):
        auth = DevelopmentAuthenticator(Authorizer())
        with pytest.raises(UnauthenticatedError):
            auth.authenticate("mallory")

    def test_unauthenticated_is_also_legacy_unauthorized(self):
        """Back-compat: existing 403-style expectations keep holding."""
        with pytest.raises(UnauthorizedActionError):
            raise UnauthenticatedError("mallory")

    def test_workflow_refuses_unknown_actor_before_anything_else(self):
        wf, store = _workflow()
        with pytest.raises(AuthenticationError):
            wf.approve("DEC-x", "ghost")
        assert store.replay() == []         # no audit write for ghosts


class TestAuditRecordsAuthenticatedIdentity:
    def test_submit_records_subject_and_role(self):
        wf, store = _workflow()
        wf.submit(_trace(), actor="bob")
        ev = store.replay()[0]
        assert ev["payload"]["principal"]["subject"] == "bob"
        assert ev["payload"]["principal"]["role"] == "operator"

    def test_execute_records_executor_identity(self):
        wf, store = _workflow()
        wf.submit(_trace(), actor="bob")
        wf.approve("DEC-AUTH-1", actor="bob")
        wf.execute("DEC-AUTH-1", actor="alice")
        exec_ev = next(e for e in store.replay() if e["type"] == "execute")
        assert exec_ev["payload"]["principal"]["subject"] == "alice"
        assert exec_ev["payload"]["principal"]["role"] == "supervisor"


class TestRolePreservation:
    def test_operator_cannot_override(self):
        wf, _ = _workflow()
        wf.submit(_trace(), actor="bob")
        with pytest.raises(UnauthorizedActionError):
            wf.override("DEC-AUTH-1", "bob", target={"action": "move"})

    def test_operator_can_approve_and_execute(self):
        wf, _ = _workflow()
        wf.submit(_trace(), actor="bob")
        wf.approve("DEC-AUTH-1", actor="bob")           # operator+
        wf.execute("DEC-AUTH-1", actor="bob")           # operator+
        assert wf.get("DEC-AUTH-1").state.value == "EXECUTED"

    def test_supervisor_override_still_supervisor_only(self):
        wf, _ = _workflow()
        wf.submit(_trace(), actor="bob")
        with pytest.raises(UnauthorizedActionError):
            wf.override("DEC-AUTH-1", "bob", target={"action": "move"})
        parent, child = wf.override(
            "DEC-AUTH-1", "alice", target={"action": "move"},
        )
        assert parent.state.value == "OVERRIDDEN"


class TestOverrideAuditIdentity:
    def test_override_records_authenticated_supervisor_on_parent_and_child(self):
        wf, store = _workflow()
        wf.submit(_trace(), actor="bob")
        parent, child = wf.override(
            "DEC-AUTH-1", "carol", target={"action": "move"}, note="fix",
        )
        events = store.replay()
        override_ev = next(e for e in events if e["type"] == "override")
        child_ev = next(e for e in events
                        if e["decision_id"] == child.decision_id)
        # The authenticated admin principal -- not a request-supplied value.
        assert override_ev["payload"]["principal"]["subject"] == "carol"
        assert override_ev["payload"]["principal"]["role"] == "admin"
        assert child_ev["payload"]["principal"]["subject"] == "carol"
        assert child_ev["payload"]["principal"]["role"] == "admin"


class TestProviderReplacement:
    def test_custom_provider_without_touching_workflow(self):
        """A production-style provider drops in; workflow is unchanged."""

        class TokenAuthenticator(Authenticator):
            TOKENS = {
                "tok-op-1": ("user-77", Role.OPERATOR),
                "tok-sup-9": ("chief-3", Role.SUPERVISOR),
            }

            def authenticate(self, credential):
                info = self.TOKENS.get(credential)
                if info is None:
                    raise UnauthenticatedError(credential)
                subject, role = info
                return Principal(subject=subject, role=role)

        store = InMemoryAuditStore()
        wf = DecisionWorkflow(store=store, authenticator=TokenAuthenticator())

        wf.submit(_trace("DEC-TOK"), actor="tok-op-1")
        sub_ev = store.replay()[0]
        assert sub_ev["payload"]["principal"]["subject"] == "user-77"
        assert sub_ev["payload"]["principal"]["role"] == "operator"

        wf.override("DEC-TOK", "tok-sup-9", target={"action": "move"})
        events = store.replay()
        assert any(
            e["type"] == "override"
            and e["payload"]["principal"]["subject"] == "chief-3"
            for e in events
        )

        with pytest.raises(UnauthenticatedError):    # forged token
            wf.approve("DEC-nonexistent", "tok-forged")


class TestAPIForgery:
    """HTTP-level proof that body-supplied identity cannot elevate."""

    @staticmethod
    def _client():
        from ultrone_hitl.api import create_app

        app = create_app(store=InMemoryAuditStore())
        return TestClient(app), app

    def _submit_decision(self, client):
        resp = client.post("/api/human/decisions", json={
            "trace": _trace("DEC-FORGE").to_dict(),
            "actor": "bob",
        })
        assert resp.status_code == 200
        return "DEC-FORGE"

    def test_body_cannot_claim_admin_for_override(self):
        client, _ = self._client()
        did = self._submit_decision(client)

        # bob (operator) tries to override while CLAIMING to be carol
        # (admin) in the body. The credential comes from the header.
        resp = client.post(
            f"/api/human/decisions/{did}/override",
            json={"actor": "carol",
                  "target": {"action": "strike",
                             "asset_type": "missiles",
                             "target": [60, 60]}},
            headers={"X-ULTRONE-Subject": "bob"},
        )
        assert resp.status_code in (401, 403)
        state = client.get(f"/api/human/decisions/{did}").json()["decision"]
        assert state["state"] == "PENDING"          # nothing happened

    def test_identity_mismatch_rejected(self):
        client, _ = self._client()
        did = self._submit_decision(client)
        resp = client.post(
            f"/api/human/decisions/{did}/approve",
            json={"actor": "bob"},
            headers={"X-ULTRONE-Subject": "alice"},  # header/body disagree
        )
        assert resp.status_code == 403

    def test_matching_header_flow_works_and_audits_header_identity(self):
        client, app = self._client()
        did = self._submit_decision(client)
        resp = client.post(
            f"/api/human/decisions/{did}/approve",
            json={"actor": "alice"},
            headers={"X-ULTRONE-Subject": "alice"},
        )
        assert resp.status_code == 200
        events = app.state.store.replay()
        approve_ev = next(e for e in events if e["type"] == "approve")
        assert approve_ev["payload"]["principal"]["subject"] == "alice"
