# ConsentRouter

An amendment should not inherit a fixed quorum when its effects are not fixed.

ConsentRouter stores a charter beside two to seven wallet-bound stewards. Each steward declares a protected scope. When a member proposes new charter text, GenLayer validators compare the full amendment with every scope and route consent to the exact members whose duties, permissions, protections, risks, or public claims would materially change.

The result is not a score. It is an enforceable consent manifest. Each required index carries an exact quote from the proposal and an exact quote from that member's frozen scope. The amendment cannot become the active charter until every routed wallet approves it. One routed member may reject it. Anyone may activate it after the approvals are complete.

## The manifest

1. `create_charter` freezes the initial text, member wallets, roles, and protected scopes.
2. `propose_change` binds an amendment to the current charter version and digest.
3. `route_consent` accepts a cited candidate route, then asks validators to reject it unless the affected-member set is exact and complete.
4. `approve` records consent only from a routed wallet. `reject` is terminal.
5. `activate` is permissionless once all required approvals exist.
6. A competing activation invalidates the old baseline. `mark_stale` closes the outdated proposal.
7. The proposer may withdraw a proposal before it becomes terminal.

## What consensus decides

Validators decide one bounded question: does the submitted route include every materially affected frozen member scope and no unaffected scope? They audit the complete candidate route instead of asking one model to invent the list. The stored result contains no unchecked narrative or score. Deterministic code validates exact member indexes, quote presence, one binding per member, lifecycle, wallet identity, baseline freshness, and unanimous approval within the routed subset.

This is different from a normal multisig, where the signer set is configured before the content is known. It also differs from semantic change classification: the validator result directly determines which wallets acquire veto power for this amendment.

## Failure behavior

- Empty routes, unknown members, duplicate bindings, invented quotes, and malformed JSON fail closed.
- A validator can reject a structurally valid route that omits an affected member.
- Unrouted wallets cannot approve or reject.
- Approvals cannot be replayed.
- Rejection, withdrawal, activation, and staleness are terminal.
- A proposal cannot activate against a newer charter version.
- No funds are held, so an ignored proposal leaves the active charter unchanged.

## Verify locally

```bash
python -m pip install -r requirements.txt
python -m pytest tests -q
genvm-lint lint contracts/consent_router.py --json
npm ci
```

For Studio Next deployment, load `GENLAYER_PRIVATE_KEY` and run `npm run deploy`. Set `CONTRACT_ADDRESS`, then run `npm run verify`. The live smoke lifecycle additionally requires `GENLAYER_SECONDARY_PRIVATE_KEY` and runs `npm run smoke`.

Deployment address, source digest, and finalized transaction evidence are recorded in `deployment.json` after the network lifecycle succeeds.

## Live Studio Next deployment

- Contract: [`0x03e4...842c`](https://explorer-studio-dev.genlayer.com/address/0x03e4b775b01B4a26CB038210F0DF46D7dD72842c)
- Deployment: [`0xab16...f558`](https://explorer-studio-dev.genlayer.com/tx/0xab16a90f466dda07ae8b946acc781c0f7b4300432ee05e757545d0370552f558)
- Validator-audited route: [`0x1702...7f58`](https://explorer-studio-dev.genlayer.com/tx/0x1702af9058f0d1a7368ab59e3ba230cc94dd0d1f0a7013bcd4cc968bcd8c7f58)
- Final activation: [`0x3fc1...dd18`](https://explorer-studio-dev.genlayer.com/tx/0x3fc1f48a45bbb1dae149ee3e41fe25b7d11b05a2b1ef5d960d4618718adadd18)
- Source SHA-256: `971b9e621d080631d403d498a574c0ba9a3f63b1b5c5a7d7aa8c3257f86eec97`

The recorded evidence run finalized every transaction with `MAJORITY_AGREE`, stored both required approvals, activated the change, and advanced the charter from version 1 to version 2. `npm run verify` confirmed an exact deployed-source match.

## Originality record

The mechanism-level comparison with earlier work is in [`docs/mechanism-comparison.md`](docs/mechanism-comparison.md). ConsentRouter is a standalone Intelligent Contract repository and intentionally contains no frontend.
