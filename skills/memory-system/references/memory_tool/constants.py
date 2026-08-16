"""Hardcoded values. Never override, recalculate, or reformat."""
SCHEMA = "memory-system/v1.1"
SKILL_NAME = "memory-system"
STORE_DIRNAME = "memories"
MARKER_NAME = ".memory-root"
DB_NAME = ".memsys-db"
SCOPES = ("user", "team")
DEFAULT_SCOPE = "user"
INDEX_NAME = "MEMORY.md"
INDEX_MAX_LINES = 200
SKILLS_DIRNAME = "skills"
SKILL_FILENAME = "SKILL.md"
SLUG_MAX = 64
PROJECT_MARKERS = (
    ".git",
    "go.mod",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "Makefile",
    "composer.json",
    "Gemfile",
    "mix.exs",
    "deno.json",
)
SECRET_RULES = (
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("github_pat", r"ghp_[A-Za-z0-9]{36}"),
    ("github_fine_grained_pat", r"github_pat_[A-Za-z0-9_]{20,}"),
    ("openai_ish_key", r"sk-(?:proj-)?[A-Za-z0-9]{20,}"),
    ("anthropic_key", r"sk-ant-[A-Za-z0-9_-]{20,}"),
    ("slack_token", r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    ("private_key", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ("jwt", r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("credential_assignment", r"(?i)(?:api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
)
CLASS_SKILL_HINTS = (
    "workflow", "checklist", "integration", "playbook", "runbook",
    "multi-step", "procedure", "how to", "guide",
)
CLASS_INDEX_HINTS = (
    "prefer", "preference", "always", "never use", "tabs", "spaces",
    "default to",
)
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_SECRET = 3
EXIT_NOT_FOUND = 4
EXIT_AMBIGUOUS = 5
