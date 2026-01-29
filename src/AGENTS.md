# NETWORK MONITOR: src/ - Agent Guide

**Generated:** 2026-01-12T12:01:00Z

## OVERVIEW
Separate Python service for network monitoring. Uses requirements.txt (not Poetry) with Makefile-based commands.

## STRUCTURE
```
src/
└── main.py    # Network monitoring entry point
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Monitoring logic | main.py | Network analysis, data collection |
| Email alerts | src/email_sender.py | Alert notifications |

## CONVENTIONS

**Python:**
- requirements.txt for dependencies (not Poetry)
- Makefile for build/test commands
- Custom test runner: run_tests.py

**Linting:**
- flake8, black-check, isort-check, mypy
- bandit for security scanning

## COMMANDS

```bash
cd network-monitor
make install   # Install dependencies
make test      # Run all tests
make ci        # Full lint + test + security
```

## NOTES

- Has separate dependency management from main backend
- Custom test runner with categories: unit, integration, functional, performance
- TODO: Network monitor analysis functionality not implemented
