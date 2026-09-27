import json, sys

CONTRACT = "contracts/consent_router.py"


def address(value):
    return "0x" + bytes(value).hex()


def members(alice, bob):
    return json.dumps([
        {"address": address(alice), "role": "Release steward", "protected_scope": "Release finality, deployment status, and public completion claims."},
        {"address": address(bob), "role": "Evidence steward", "protected_scope": "Source attribution, exact evidence quotes, and validator audit integrity."},
    ])


BASELINE = "A release is complete only after finalization. Public evidence findings preserve exact source quotes and validator-audited attribution."
PROPOSAL = "A release may be shown as complete when accepted. Public evidence findings may summarize source quotes without preserving exact text."


def route_both():
    return json.dumps({"required_indexes": [0, 1], "bindings": [
        {"member_index": 0, "proposal_quote": "shown as complete when accepted", "scope_quote": "Release finality, deployment status, and public completion claims"},
        {"member_index": 1, "proposal_quote": "summarize source quotes without preserving exact text", "scope_quote": "Source attribution, exact evidence quotes, and validator audit integrity"},
    ]})


def enable_consensus(contract, monkeypatch, validator=None):
    module = sys.modules[contract.__class__.__module__]
    monkeypatch.setattr(module.gl.eq_principle, "prompt_non_comparative", validator or (lambda fn, **_kwargs: fn()))


def setup(contract, vm, alice, bob, charter_id="release-charter"):
    vm.sender = alice
    contract.create_charter(charter_id, "Release truth charter", BASELINE, members(alice, bob))
    contract.propose_change(charter_id, charter_id + "-change", "Relax release and evidence rules", PROPOSAL)
    return charter_id + "-change"


def test_00_contract_loads(direct_vm, direct_deploy):
    assert direct_deploy(CONTRACT) is not None


def test_member_identity_and_duplicate_charters_are_guarded(direct_vm, direct_deploy, direct_alice, direct_bob):
    c = direct_deploy(CONTRACT); direct_vm.sender = direct_alice
    duplicate = json.loads(members(direct_alice, direct_bob)); duplicate[1]["address"] = duplicate[0]["address"]
    with direct_vm.expect_revert("unique"): c.create_charter("bad-charter", "Bad charter", BASELINE, json.dumps(duplicate))
    not_member = json.loads(members(direct_alice, direct_bob)); not_member[0]["address"] = "0x" + "33" * 20
    with direct_vm.expect_revert("creator must be a listed member"): c.create_charter("orphan-charter", "Orphan charter", BASELINE, json.dumps(not_member))
    c.create_charter("safe-charter", "Safe charter", BASELINE, members(direct_alice, direct_bob))
    with direct_vm.expect_revert("already exists"): c.create_charter("safe-charter", "Safe charter", BASELINE, members(direct_alice, direct_bob))


def test_complete_dynamic_consent_route_and_permissionless_activation(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    c = direct_deploy(CONTRACT); enable_consensus(c, monkeypatch); change_id = setup(c, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm("CONSENTROUTER_PRODUCER", json.dumps(route_both())); routed = c.route_consent(change_id); direct_vm.clear_mocks()
    assert routed["required_indexes"] == [0, 1] and len(routed["bindings"]) == 2
    direct_vm.sender = direct_alice; assert c.approve(change_id)["remaining"] == 1
    with direct_vm.expect_revert("Missing required approvals"): c.activate(change_id)
    direct_vm.sender = direct_bob; assert c.approve(change_id)["remaining"] == 0
    direct_vm.sender = direct_alice; activated = c.activate(change_id)
    assert activated["status"] == "ACTIVE" and activated["charter_version"] == 2
    assert c.get_charter("release-charter")["baseline"] == PROPOSAL


def test_only_semantically_routed_members_can_consent_or_reject(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    c = direct_deploy(CONTRACT); enable_consensus(c, monkeypatch); change_id = setup(c, direct_vm, direct_alice, direct_bob)
    one = json.dumps({"required_indexes": [1], "bindings": [{"member_index": 1, "proposal_quote": "summarize source quotes without preserving exact text", "scope_quote": "Source attribution, exact evidence quotes, and validator audit integrity"}]})
    direct_vm.mock_llm("CONSENTROUTER_PRODUCER", json.dumps(one)); c.route_consent(change_id); direct_vm.clear_mocks()
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("consent is not required"): c.approve(change_id)
    direct_vm.sender = direct_bob; result = c.reject(change_id, "Exact evidence quotes remain mandatory.")
    assert result["status"] == "REJECTED"
    with direct_vm.expect_revert("not awaiting consent"): c.approve(change_id)


def test_forged_routes_and_quotes_fail_closed(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    c = direct_deploy(CONTRACT); enable_consensus(c, monkeypatch)
    bad_routes = [
        ({"required_indexes": [], "bindings": []}, "At least one member"),
        ({"required_indexes": [9], "bindings": []}, "out of range"),
        ({"required_indexes": [0, 0], "bindings": [{"member_index": 0, "proposal_quote": "shown as complete when accepted", "scope_quote": "Release finality, deployment status, and public completion claims"}, {"member_index": 0, "proposal_quote": "shown as complete when accepted", "scope_quote": "Release finality, deployment status, and public completion claims"}]}, "Every required member"),
        ({"required_indexes": [0], "bindings": [{"member_index": 0, "proposal_quote": "invented proposal quote", "scope_quote": "Release finality, deployment status, and public completion claims"}]}, "Proposal quote"),
        ({"required_indexes": [0], "bindings": [{"member_index": 0, "proposal_quote": "shown as complete when accepted", "scope_quote": "invented member scope"}]}, "Scope quote"),
    ]
    for number, (payload, message) in enumerate(bad_routes):
        change_id = setup(c, direct_vm, direct_alice, direct_bob, "guard-" + str(number))
        direct_vm.mock_llm("CONSENTROUTER_PRODUCER", json.dumps(json.dumps(payload)))
        with direct_vm.expect_revert(message): c.route_consent(change_id)
        direct_vm.clear_mocks(); assert c.get_change(change_id)["status"] == "PROPOSED"


def test_validator_rejects_semantic_omission_even_when_shape_is_valid(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    c = direct_deploy(CONTRACT)
    def independent_validator(fn, **_kwargs):
        candidate = json.loads(fn())
        if candidate["required_indexes"] != [0, 1]:
            raise sys.modules[c.__class__.__module__].gl.vm.UserError("[LLM_ERROR] Validator rejected omitted affected member")
        return json.dumps(candidate)
    enable_consensus(c, monkeypatch, independent_validator); change_id = setup(c, direct_vm, direct_alice, direct_bob)
    omitted = json.dumps({"required_indexes": [0], "bindings": [{"member_index": 0, "proposal_quote": "shown as complete when accepted", "scope_quote": "Release finality, deployment status, and public completion claims"}]})
    direct_vm.mock_llm("CONSENTROUTER_PRODUCER", json.dumps(omitted))
    with direct_vm.expect_revert("Validator rejected omitted affected member"): c.route_consent(change_id)
    direct_vm.clear_mocks(); assert c.get_change(change_id)["status"] == "PROPOSED"


def test_concurrent_change_becomes_stale_after_other_activation(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    c = direct_deploy(CONTRACT); enable_consensus(c, monkeypatch); direct_vm.sender = direct_alice
    c.create_charter("parallel-charter", "Parallel charter", BASELINE, members(direct_alice, direct_bob))
    c.propose_change("parallel-charter", "change-one", "First change", PROPOSAL)
    c.propose_change("parallel-charter", "change-two", "Second change", PROPOSAL + " Additional release note.")
    for change_id in ("change-one", "change-two"):
        direct_vm.mock_llm("CONSENTROUTER_PRODUCER", json.dumps(route_both())); c.route_consent(change_id); direct_vm.clear_mocks()
    c.approve("change-one"); direct_vm.sender = direct_bob; c.approve("change-one"); c.activate("change-one")
    stale = c.mark_stale("change-two"); assert stale["status"] == "STALE"
    with direct_vm.expect_revert("not awaiting activation"): c.activate("change-two")


def test_withdrawal_and_replay_are_terminal(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    c = direct_deploy(CONTRACT); enable_consensus(c, monkeypatch); change_id = setup(c, direct_vm, direct_alice, direct_bob)
    assert c.withdraw_change(change_id)["status"] == "WITHDRAWN"
    with direct_vm.expect_revert("cannot be withdrawn"): c.withdraw_change(change_id)
    with direct_vm.expect_revert("only be routed once"): c.route_consent(change_id)
