# NETWORK MONITOR: src/ - Agent Guide

**Generated:** 2026-02-14T16:57:00Z

## OVERVIEW
Main source directory with network monitoring logic, report generation, email sending, and utilities.

## STRUCTURE
```
src/
├── main.py                 # Entry point: NetworkMonitor class + CLI
├── config_manager.py       # YAML config loading
├── file_scanner.py         # Log directory scanning
├── log_parser.py           # bandwhich log parsing
├── report_generator.py     # JSON/CSV/Parquet output
├── email_sender.py         # SMTP notifications
├── archive_manager.py     # ZIP/tar.gz compression
├── parallel_processor.py  # Concurrent file processing
├── __init__.py
└── utils/
    ├── date_utils.py       # Date parsing/range
    ├── logger.py           # Logging setup
    └── validators.py       # Config validation
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| CLI entry | `main.py` | argparse with report/analysis commands |
| Core logic | `log_parser.py` | bandwhich format parsing |
| Reports | `report_generator.py` | pandas-based output |
| Email | `email_sender.py` | SMTP with TLS |

## CONVENTIONS

- **No pyproject.toml** - cannot `pip install -e .`
- **Path hacking** - main.py adds src/ to sys.path manually
- Chinese docstrings

## ANTI-PATTERNS

- Hardcoded SMTP password in config/settings.yaml
- TODO: Analysis mode unimplemented (main.py:230)

## NOTES

- Entry: `python src/main.py report --config config/settings.yaml`
- Analysis mode is experimental placeholder
