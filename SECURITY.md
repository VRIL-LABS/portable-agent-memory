# Security Policy

This project takes security seriously. We appreciate responsible disclosure and ask that security issues be reported privately and not as public issues or pull requests.

GitHub's official repository guidance for adding and using a security policy is here:

- https://docs.github.com/en/code-security/reporting-security-vulnerabilities/adding-a-security-policy-to-your-repository
- https://docs.github.com/en/code-security/reporting-security-vulnerabilities/privately-reporting-a-security-vulnerability

## Reporting a vulnerability

If you believe you have discovered a security issue in this repository, please do not open a public issue or discussion for it.

Instead, use the repository's GitHub private vulnerability reporting flow if it is enabled in the repository's Security tab. If private reporting is not enabled, follow the maintainer-provided security contact in the repository or another secure, non-public channel designated for this project.

Please include as much detail as possible, such as:

- a summary of the vulnerability and affected component
- steps to reproduce or a proof of concept
- the potential impact or risk
- any suggested remediation or mitigation

## Scope

This policy applies to vulnerabilities in the project code and repository assets, including:

- the memory-system tooling under `skills/memory-system/`
- the SQLite + FTS5 ledger behavior and any write/indexing paths
- secret handling, path validation, and storage logic
- documentation or examples that could create a security or operational risk

## Supported versions

This project is under active development. Please report issues against the latest branch or the most recently published revision in the repository.

## Disclosure expectations

Please do not disclose a vulnerability publicly until the maintainers have had a reasonable opportunity to investigate, remediate, and communicate a fix.

We will do our best to review reports promptly and coordinate a fix in a timely manner.
