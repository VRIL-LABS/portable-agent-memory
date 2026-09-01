# Contributing to Portable Agent Memory

Thanks for helping improve `portable-agent-memory`. This project is intentionally small, local-first, and markdown-centric: the repository's source of truth stays in `memories/`, while the hidden `.memsys-db` file is a regenerable index and search layer.

GitHub surfaces contribution guidance automatically when a repository includes a root-level or `.github/` `CONTRIBUTING.md`, and the canonical reference for repository contributor expectations is the official GitHub documentation:

- https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors
- https://docs.github.com/en/contributing

## Before you contribute

Please read the project docs first:

- `README.md` for the high-level architecture and usage
- `AGENTS.md` for repo-specific development guidance
- `skills/memory-system/SKILL.md` for the skill's behavior and constraints

This repository values a single-file, offline-first design. Changes should keep the project portable, dependency-light, and easy to reason about.

## Ways to contribute

We welcome:

- bug reports with clear reproduction steps
- documentation improvements
- feature proposals that fit the project-local, markdown-first model
- fixes or tests for the memory tooling under `skills/memory-system/references/memory_tool/`

We are less likely to accept changes that:

- introduce a global daemon or extra service dependency
- replace the markdown source-of-truth model with a cloud-backed or remote store
- add new secret-handling risks or bypass the repository's fail-closed protections
- broaden scope beyond the issue being fixed

## Development setup

### Requirements

- Git
- Python 3.9 or newer
- a checkout of this repository

### Local workflow

1. Fork or clone the repository.
2. Create a focused topic branch.
3. Make the smallest change that addresses the problem.
4. Validate the relevant behavior before opening a pull request.

### Validation

For this project, the primary validation is the embedded self-test for the memory tool:

```bash
skills/memory-system/scripts/memory selftest
```

You can also run the underlying Python self-test directly:

```bash
python3 skills/memory-system/references/memory_tool/selftest.py
```

If you change documentation or behavior that affects the stored memory contract, update the relevant docs and ensure the self-test still passes.

## Project-specific expectations

Please keep these principles in mind when contributing:

- Markdown under `memories/` stays the source of truth.
- `.memsys-db` is a regenerable index and search layer, not the canonical record.
- Prefer stdlib-only or repo-local solutions over new dependencies.
- Do not add server daemons, admin UIs, or cloud storage dependencies.
- Never commit secrets or secret-like content.
- Keep paths, queries, and database access safe and minimal.

When you edit the skill logic, follow the existing conventions in the memory tool package and keep changes consistent with the repository's architecture.

## Opening issues and pull requests

### Issues

When filing a bug report or feature request, include:

- clear summary of the problem
- reproduction steps or commands
- expected behavior
- actual behavior
- relevant logs or output
- whether the issue affects docs, behavior, or the memory tool itself

### Pull requests

Please keep pull requests focused and easy to review. A good PR should include:

- a concise description of the change
- the reasoning behind it
- any validation commands you ran
- notes on edge cases or compatibility concerns

If you are unsure whether a change fits the project, open an issue first and discuss it before writing a large patch.

## Code of conduct and community expectations

Contributions should be respectful, constructive, and consistent with GitHub's community standards. Treat other contributors and users with the same care you would want for your own work.

## Questions

If you are unsure about the right change, the best first step is to open an issue or ask in the repository discussion before introducing a broad refactor.
