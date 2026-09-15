# ADR 0001: A local transactional kernel before a distributed platform

Status: accepted for the foundation; revisit on measured need.

## Decision

Use a small Python package, file-backed SQLite, integer units, and semantic deterministic randomness. Keep identity, gateway, economic policy, and UI outside the reference kernel. The first application should remain a modular service.

## Rationale

The initial uncertainty is about accounting semantics, economic validity, and reproducible behavior, not high-throughput distributed deployment. Independent connections and explicit transactions permit focused contention/recovery tests with few moving parts.

## Consequences

The reference implementation does not claim distributed availability, hostile-process containment, hierarchical budget enforcement, a general ledger, or a working HTTP integration. Those claims require separate implementation and evidence. SQLite writer serialization is an accepted initial constraint. Moving to another database requires re-running the same state and contention tests rather than relying on interface similarity.
