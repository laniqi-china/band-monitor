# NETWORK MONITOR - Agent Guide

**Generated:** 2026-02-14T16:57:00Z
**Commit:** 54681de
**Branch:** main

## OVERVIEW
Python network traffic monitoring system. Parses `bandwhich` logs, generates JSON/CSV/Parquet reports, sends email notifications, archives logs.

## STRUCTURE
```
./
├── src/               # Source code (main.py entry)
├── tests/            # Test suite (unit/integration/functional/performance)
├── config/           # settings.yaml, email_templates/
├── doc/              # Documentation
├── logs/             # Runtime logs (should be in .gitignore)
├── Makefile          # Build commands
├── run_tests.py      # Custom test runner
└── requirements*.txt
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Entry point | `src/main.py` | NetworkMonitor class, CLI via argparse |
| Config | `config/settings.yaml` | YAML-based config |
| Reports | `src/report_generator.py` | JSON/CSV/Parquet output |
| Email | `src/email_sender.py` | SMTP notifications |
| Parsing | `src/log_parser.py` | bandwhich log format |
| Tests | `tests/` | pytest with custom markers |

## CONVENTIONS

**Python:**
- requirements.txt (NOT Poetry/pyproject.toml)
- Makefile for all commands
- Custom test runner: `python run_tests.py`
- No setup.py/pyproject.toml (not installable as package)

**Testing:**
- pytest with custom markers: unit, integration, functional, performance
- pytest.ini in tests/ (non-standard: should be root)
- fixtures in tests/conftest.py
- run_tests.py supports --coverage, --parallel, --html

**Code Quality:**
- flake8, black, isort, mypy
- bandit for security
- Chinese comments throughout (README, tests, docstrings)

## ANTI-PATTERNS (THIS PROJECT)

1. **Hardcoded password** in config/settings.yaml - use env vars
2. **Missing pyproject.toml** - cannot `pip install -e .`
3. **src/main.py path hacking** - adds src/ to sys.path manually
4. **pytest.ini in tests/** - standard location is root
5. **Empty fixtures/ directories** - tests/fixtures/ and test_reports/ unused

## COMMANDS

```bash
make test          # Run all tests
make test-unit     # Unit tests only
make lint          # flake8, black, isort, mypy
make format        # black + isort
make security      # bandit scan
make ci            # lint + test + coverage + security
```

## NOTES

- TODO: Analysis mode (trend, anomaly, patterns) not implemented
- No GitHub Actions CI
- Uses .venv for virtual environment
- Project root has 4 test artifact dirs (test_archive, test_logs, test_reports, test_temp)
