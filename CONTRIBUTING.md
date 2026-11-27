# Contributing

Thanks for contributing to OMR Checker.

## Before starting
- Read the [product requirements](docs/product/PRD.md) and relevant architecture docs.
- Search existing issues and pull requests first.
- For substantial work, open an issue describing the problem and proposed approach.

## Engineering principles
- Keep recognition, scoring, and UI concerns separate.
- Prefer small, typed, testable functions.
- Preserve source scans and version derived processing.
- Never hide uncertain recognition behind a guessed answer.
- Do not commit credentials, production data, or real student scans.
- Update docs when changing API, template, data, or processing contracts.

## Pull requests

Include the problem, proposed change, scope, tests run, UI screenshots where relevant, and impact on template compatibility, result reproducibility, and retention.

## Commit style

Use clear imperative messages, e.g.:
- `docs: clarify template version lifecycle`
- `feat(omr): add bubble fill measurement`
- `fix(api): enforce organization scope on batch reads`
- `test(omr): add shadowed phone captures`

## Testing

Run relevant package tests and formatters before review. Add regression tests for recognition bugs. Follow the [Code of Conduct](CODE_OF_CONDUCT.md).
