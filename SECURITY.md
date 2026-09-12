# Security policy

## Scope

RAI is an offline-first engineering prototype. It processes telemetry and produces
maintenance recommendations; it must not issue physical control commands.

## Reporting

Do not publish credentials, private telemetry, model weights, or sensitive plant
information in an issue. Report security concerns privately to the project owner through
the repository’s configured GitHub security contact.

## Development safeguards

- Keep `.env`, credentials, tokens, and generated private data out of Git.
- Treat all telemetry as sensitive by default.
- Keep the agent input limited to structured evidence packets.
- Keep ticket creation confirm-required and all plant actions outside the agent.
- Do not treat synthetic knowledge documents as OEM procedures.

