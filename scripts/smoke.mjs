import { createAccount, createClient, isSuccessful } from "genlayer-js";
import { studioDevnet } from "genlayer-js/chains";

const contract = process.env.CONTRACT_ADDRESS?.trim();
const primaryRaw = process.env.GENLAYER_PRIVATE_KEY?.trim();
const secondaryRaw = process.env.GENLAYER_SECONDARY_PRIVATE_KEY?.trim();
if (!contract || !primaryRaw || !secondaryRaw) throw new Error("CONTRACT_ADDRESS and both private keys are required");
const normalize = value => value.startsWith("0x") ? value : `0x${value}`;
const chain = { ...studioDevnet, id: 61997, name: "GenLayer Studio Next", rpcUrls: { default: { http: ["https://studio-next.genlayer.com/api"] } } };
const primary = createAccount(normalize(primaryRaw));
const secondary = createAccount(normalize(secondaryRaw));
const clients = [createClient({ chain, account: primary }), createClient({ chain, account: secondary })];
const id = `consent-demo-${Date.now().toString(36)}`;
const change = `${id}-change`;
const baseline = "A release is complete only after finalization. Public evidence findings preserve exact source quotes and validator-audited attribution.";
const proposal = "A release may be shown as complete when accepted. Public evidence findings may summarize source quotes without preserving exact text.";
const members = JSON.stringify([
  { address: primary.address, role: "Release steward", protected_scope: "Release finality, deployment status, and public completion claims." },
  { address: secondary.address, role: "Evidence steward", protected_scope: "Source attribution, exact evidence quotes, and validator audit integrity." },
]);

async function write(client, label, functionName, args, intelligent = false) {
  const fees = await client.estimateTransactionFees({ leaderTimeunitsAllocation: intelligent ? 500n : 180n, validatorTimeunitsAllocation: intelligent ? 650n : 360n });
  const hash = await client.writeContract({ address: contract, functionName, args, fees });
  console.log(`${label}_TX=${hash}`);
  const receipt = await client.waitForTransactionReceipt({ hash, waitUntil: "finalized", retries: 300, interval: 3000, fullTransaction: true });
  const status = String(receipt.statusName ?? receipt.status ?? "unknown");
  const execution = String(receipt.txExecutionResultName ?? receipt.txExecutionResult ?? "unknown");
  const consensus = String(receipt.resultName ?? receipt.result_name ?? "unknown");
  console.log(`${label}_STATUS=${status};EXECUTION_RESULT=${execution};CONSENSUS=${consensus}`);
  if (!isSuccessful(receipt) || status !== "FINALIZED" || execution !== "FINISHED_WITH_RETURN" || consensus === "MAJORITY_DISAGREE") throw new Error(`${label} failed`);
  return hash;
}

await write(clients[0], "CREATE", "create_charter", [id, "Release truth charter", baseline, members]);
await write(clients[0], "PROPOSE", "propose_change", [id, change, "Relax release and evidence rules", proposal]);
await write(clients[0], "ROUTE", "route_consent", [change], true);
const routed = await clients[0].readContract({ address: contract, functionName: "get_change", args: [change], jsonSafeReturn: true });
console.log(`ROUTED_STATE=${JSON.stringify(routed)}`);
if (routed.status !== "AWAITING_CONSENT" || routed.required_indexes.length !== 2) throw new Error("Live route did not bind both affected members");
await write(clients[0], "APPROVE_RELEASE", "approve", [change]);
await write(clients[1], "APPROVE_EVIDENCE", "approve", [change]);
await write(clients[0], "ACTIVATE", "activate", [change]);
const finalState = await clients[0].readContract({ address: contract, functionName: "get_change", args: [change], jsonSafeReturn: true });
const charter = await clients[0].readContract({ address: contract, functionName: "get_charter", args: [id], jsonSafeReturn: true });
console.log(`FINAL_CHANGE=${JSON.stringify(finalState)}\nFINAL_CHARTER=${JSON.stringify(charter)}`);
if (finalState.status !== "ACTIVE" || charter.version !== 2 || charter.baseline !== proposal) throw new Error("Live activation state is incorrect");
console.log(`DEMO_CHARTER=${id}`);
