# Mechanism comparison

ConsentRouter was checked against the user's recent GenLayer contracts before implementation.

| Contract | Decision unit | State transition | Authorization model | Why ConsentRouter differs |
| --- | --- | --- | --- | --- |
| DeltaCouncil | classify a whole revision | proposal to approved revision | fixed council approval | ConsentRouter derives the exact affected subset from per-member protected scopes, then requires only that routed subset. |
| IntentLock | compare a new action with prior actions | request to lease or duplicate block | workspace owner and agents | ConsentRouter does not deduplicate or lease actions. It creates a consent obligation graph for a charter amendment. |
| Mandate Firewall | compare an agent action with one delegation | request to allow, review, or deny | principal and agent | ConsentRouter evaluates impact across multiple independent scopes and gates activation on their individual wallet approvals. |
| PatchProof | assess implementation against criteria | revision to ready or needs work | case owner | ConsentRouter changes the authoritative charter only after dynamic consent routing and approvals. |

The mechanism signature is: frozen member scopes, validator-derived affected-member indexes, exact proposal and scope bindings, wallet-isolated consent, permissionless activation, and stale-baseline protection.
