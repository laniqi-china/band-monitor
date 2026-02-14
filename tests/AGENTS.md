# NETWORK MONITOR: tests/ - Agent Guide

**Generated:** 2026-02-14T16:57:00Z

## OVERVIEW
Comprehensive pytest suite with 4 test categories, custom fixtures, and parallel execution support.

## STRUCTURE
```
tests/
├── pytest.ini              # Pytest config (non-standard: should be root)
├── conftest.py            # Shared fixtures
├── unit/                  # 10 test files + utils/
├── integration/           # 1 test file
├── functional/            # 1 test file
├── performance/           # 1 test file
├── fixtures/              # Empty (unused)
└── test_reports/          # Empty (output dir)
```

## TEST MARKERS

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | 单元测试 - Component testing |
| `@pytest.mark.integration` | 集成测试 - End-to-end |
| `@pytest.mark.functional` | 功能测试 - Feature validation |
| `@pytest.mark.performance` | 性能测试 - Scalability |
| `@pytest.mark.slow` | 慢速测试 |
| `@pytest.mark.network` | 需要网络 |
| `@pytest.mark.email` | 邮件相关 |

## KEY FIXTURES

- `temp_dir` - Function-scoped temp directory
- `sample_config` - ConfigManager instance
- `sample_log_data` - Parsed bandwhich log records
- `mock_smtp_server` - SMTP fixture for email tests
- `create_sample_log_file` - Factory for test log files

## RUNNING TESTS

```bash
python run_tests.py unit              # Unit tests
python run_tests.py integration       # Integration tests
python run_tests.py functional        # Functional tests
python run_tests.py performance       # Performance tests
python run_tests.py all --coverage    # With coverage
python run_tests.py all --parallel    # Parallel execution
python run_tests.py all --html        # HTML report
```

## CONVENTIONS

- Chinese docstrings throughout ("测试...", "验证...")
- Quantitative performance assertions (e.g., `records_per_second > 100`)
- VCR.py for HTTP request recording
- pytest-xdist for parallel execution
- pytest-html for HTML reports

## NOTES

- run_tests.py is custom wrapper (not direct pytest)
- fixtures/ and test_reports/ are empty directories
- Tests use mock_smtp_server to avoid real email
