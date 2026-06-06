# Workflow: Review a Change

Use this to review a diff/PR (or self-review your own change) before merge.

## Roles & skills

- Role: [`../roles/code-reviewer.md`](../roles/code-reviewer.md).
- Primary skill: [`../skills/code-review.md`](../skills/code-review.md).
- If architecture is affected: [`../skills/architecture-review.md`](../skills/architecture-review.md).

## Steps

1. **Understand intent.** Read the task/PR description and the task file it
   claims to implement. Out-of-scope churn is a finding.
2. **Read context.** `AGENTS.md` §3, `docs/ARCHITECTURE.md`, the relevant layer
   docs, and any ADR the change touches.
3. **Apply the code-review skill process** in order: architecture & boundaries →
   lifecycle/state → public interface → errors → security → testability/tests →
   simplicity → backward compatibility.
4. **Escalate architecture concerns** to `architecture-review` when the change
   crosses layers or alters a contract; require an ADR where needed.
5. **Write the structured report** (below).

## Output (required structure)

1. Summary
2. Blocking issues
3. Non-blocking issues
4. Architecture concerns
5. Security concerns
6. Testing gaps
7. Suggested improvements
8. Final recommendation (Approve / Approve with changes / Request changes)

## Done when

- Every section of the report is filled, and the recommendation is explicit.
- Any contract change is backed by an ADR (or flagged as blocking).
