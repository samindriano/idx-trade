# V4 CA Residual Document Semantics V1 — Preregistration

Status: `FROZEN_BEFORE_LOCAL_RUN`

## Scientific parent

- parent branch/result: `data/idx-v4-ca-voluntary-conversion-forensic-replay-v1@c2246e5e82dc642950017e38e57cd97700e15199`
- accepted forensic finding: 34 strict security-to-IDR Voluntary Conversion rows are genuinely non-blocking; 29 Voluntary Conversion rows remain schedule-required because source-native ratio text is empty/unresolved.
- residual support artifact: 61 schedule-required events.

This lane does not reinterpret the preceding results. It reuses only already acquired official KSEI Stage-2 bytes and immutable KSEI history/calendar artifacts.

## Question

Can the residual 61-event CA continuity blocker be narrowed further using exact semantics from the already downloaded official KSEI schedule documents, without provider calls, date guessing, price inference, or target/model access?

## Frozen evidence paths

### A. Voluntary Conversion cash-document path

A residual `Voluntary Conversion` may become `NON_BLOCKING` only when all are true:

1. the official KSEI document bytes were already acquired in Stage 2 and their SHA matches the immutable request record;
2. the document proves one of the frozen cash-transaction classes:
   - Voluntary Tender Offer;
   - Mandatory Tender Offer;
   - Share Buyback / cash repurchase;
   - dissenting-shareholder cash repurchase;
3. the event ticker is exactly evidenced in the document/index identity;
4. at least one immutable source-native event date exactly matches an explicitly labelled payment/settlement/cash-purchase date in the document;
5. there is no contradictory linked document semantics for the same event.

Ticker+subject alone is insufficient. Record Date alone is insufficient. A tender/buyback document is event-identity evidence only; it never supplies a mechanical transition date.

### B. Mechanical transition path

A residual mechanical event may receive `EXACT_TRANSITION` only when all are true:

1. official KSEI Stage-2 raw bytes and SHA are verified;
2. ticker and event family are compatible;
3. at least one immutable source-native event date exactly matches the document Record/Distribution identity fields;
4. the document explicitly identifies either:
   - regular-market Ex Date; or
   - first regular-market trading date on the new basis;
5. the extracted transition is an official exchange session;
6. all exact linked documents agree on one transition date/semantic.

Record/Distribution Date is never a transition fallback. A next-session inference is not added here. Price jumps, adjusted-price factors, and generic action dates remain prohibited.

## Raw corpus reuse

The lane must reuse exactly:

`D:\Documents\Project\idx-v4-ca-schedule-evidence-20260818-v3`

No redownload or source substitution is permitted. `request_records.jsonl` is the byte/path authority for successful Stage-2 document captures. Every admitted document must rehash to its recorded SHA.

## Execution sequence

1. validate focused tests + `py_compile` + `git diff --check`;
2. run one offline residual-document semantic audit;
3. if and only if the audit manifest is complete and internally verified, run one offline continuity replay using the resulting exact event evidence;
4. STOP regardless of pass/fail.

No code/config change is allowed between Step 2 and Step 3 after document results are exposed.

## Frozen continuity gate

Unchanged V4 gate:

- same frozen 610-ticker / 600-date decision universe;
- H5, H10 and consensus each require every date to reach `>= 90%` admitted continuity;
- no refill, target-contract change, adjusted-price rescue, universe shrink, or threshold change.

## Protected boundary

This lane must not materialize or inspect R5/R10, target ranks, model fits, predictions, IC, Top30/spread metrics, bootstrap results, protected outcomes, or fresh-forward outcomes.
