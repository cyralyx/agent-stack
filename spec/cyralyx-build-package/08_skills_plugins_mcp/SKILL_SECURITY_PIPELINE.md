# Skill Security Pipeline

Every external skill must pass:

1. licence check
2. source reputation check
3. commit history review
4. dependency review
5. secret scan
6. static analysis
7. suspicious command detection
8. network domain inspection
9. permission minimisation
10. sandbox execution
11. tests
12. reviewer approval
13. user confirmation for medium/high risk

Flag:

- obfuscated code
- download-and-execute
- cookie access
- credential access
- destructive filesystem operations
- persistence
- privilege escalation
- unknown binaries
- mining
- undisclosed telemetry
