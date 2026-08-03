# CI/CD and Engineering Standards

## Required checks

- formatting
- linting
- type checking
- unit tests
- integration tests
- schema validation
- dependency licence scan
- vulnerability scan
- secret scan
- generated-code drift check
- desktop build smoke test
- migration test

## Branch policy

- protected main branch
- feature branches
- reviewed pull requests
- conventional or documented commit format
- release tags
- generated changelog

## Dependency policy

- pin lockfiles
- prefer maintained dependencies
- document critical dependencies
- use automated update proposals, not blind updates
- require review for runtime dependencies with privileged access

## Code rules

- no provider logic in UI components
- no direct database access from UI
- no untyped event payloads
- no secrets in environment dumps
- no silent catch blocks
- no completion status before validation
- add tests for every fixed regression
