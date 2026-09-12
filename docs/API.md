# API documentation

The authoritative interface is [`API_CONTRACT.md`](API_CONTRACT.md). It defines the
frozen JSON shapes, enumerations, null semantics, error codes, investigation timeline,
simulator endpoints, and evaluation response.

The contract is ahead of the current endpoint implementation. When routes are added under
`services/api/`, verify them against that document rather than inventing a parallel shape.
The frontend must render uncomputed `null` values as an explicit “not evaluated” state,
never as zero.

