# Email Agent Supervisor

Building AI course project

## Summary

Email Agent Supervisor is a lightweight governance layer for automated email agents. It detects high-impact situations (M&A interest, legal/compliance requests, security/fraud signals) and decides whether to auto-reply, escalate to a human, or block the workflow.

## Background

Automated email agents can handle routine messages efficiently, but they often lack escalation logic for exceptional cases. This creates operational risk: high-impact emails can be answered automatically when they should be reviewed by humans.

Examples of emails that should not receive an automatic reply:
- acquisition / investment interest (M&A)
- legal notices, NDA, compliance topics
- security incidents or fraud-like requests (bank details changes, urgent wire transfers)

The core problem is not email categorization for inbox organization.  
It is autonomy regulation: deciding when automation must stop.

## Conceptual Architecture

Incoming Email  
→ Layer 1: Cheap Pattern Filter  
→ Layer 2: Semantic Intent + Entity Signals  
→ Layer 3: Escalation Policy Engine  
→ Decision: AUTO_REPLY or ESCALATE_HUMAN or BLOCK

## How is it used?

The supervisor runs inline with an email agent:

Email arrives → Supervisor decides action → workflow continues or escalates

The prototype extracts:
- intent signals (M&A, legal, security, sales, support)
- entities and cues (roles like CEO/board, urgency markers, links, phone numbers)
- sender-domain cues (free domain vs corporate)

And returns one action:
- AUTO_REPLY
- ESCALATE_HUMAN
- BLOCK

## Demo

Run:

```bash
python supervisor_demo.py
```

Example (M&A escalation):

Sender: investment@globalholdings.com  
Subject: Confidential acquisition proposal  
Body: We would like to discuss valuation, due diligence, and an NDA. Please connect us with your CEO.

Expected: ESCALATE_HUMAN

Example (fraud/security):

Sender: finance-update@gmail.com  
Subject: URGENT: Change bank details  
Body: Update bank details for wire transfer. Confidential. Call +34...

Expected: BLOCK

## Data sources and AI methods

This project uses:
- explainable rule-based scoring (intent weights)
- entity extraction with pattern matching
- a layered decision policy (auto-reply vs escalation vs block)
- human-in-the-loop escalation for high-impact cases

No model training is performed in this prototype; it is designed as a governance layer that could later incorporate a lightweight classifier or an LLM-based supervisor.

## Quick Evaluation (small-scale)

A small hand-labeled set of 20 synthetic emails was used to compare:
- a naive baseline
- the supervisor

Example run:
- Overall accuracy improved from 0.65 (baseline) to 0.95 (supervisor)
- ESCALATE_HUMAN recall improved from 0.44 to 1.0
- Critical false negatives reduced from 5 to 0

The system prioritizes minimizing critical false negatives (missing an escalation). This can increase false positives, which can be tuned with additional context rules (e.g., separating account-support password resets from security incidents).

## Challenges

- Heuristic intent scoring can produce false positives without careful tuning.
- Real deployment would need audit logging and privacy-safe handling.
- A production system should add:
  - a lightweight ML classifier for ambiguous cases
  - optional LLM supervisor for rare high-risk cases
  - reliability signals from infrastructure (latency/errors)

## What next?

Future work: add a human feedback loop (correct/incorrect escalation) to collect labels for periodic recalibration or training a lightweight classifier.

## Contact

If you are interested in developing this further, include your contact link here (LinkedIn or email).
