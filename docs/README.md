# Documentation index

This directory is the source of truth for product and engineering decisions.

## Product
- [Product requirements](product/PRD.md)

## Architecture
- [System overview](architecture/overview.md)
- [Recognition pipeline](architecture/omr-pipeline.md)
- [End-to-end data flow](architecture/data-flow.md)
- [ADR 0001: Modular monolith](architecture/adr/0001-modular-monolith.md)
- [ADR 0002: Normalized template coordinates](architecture/adr/0002-normalized-template-coordinates.md)

## Engineering contracts
- [API conventions](api/openapi-notes.md)
- [Database model](data/database-schema.md)
- [Template format](omr/template-format.md)
- [Recognition and confidence](omr/recognition-and-confidence.md)
- [Phone and scanner capture](scanning/mobile-scanning.md)
- [Security and privacy](security/privacy.md)
- [Testing strategy](testing/strategy.md)
- [Deployment and operations](operations/deployment.md)
- [Implementation roadmap](roadmap/implementation-plan.md)

Update the relevant document whenever an implementation changes an API, template, data lifecycle, recognition assumption, or operational requirement. Material architecture changes should be recorded as a new numbered ADR.
