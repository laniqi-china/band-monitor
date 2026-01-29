# Network Traffic Monitor

A comprehensive network traffic monitoring and reporting system that parses `bandwhich` log files, generates detailed traffic reports, and delivers them via email.

## Features

- **Log Scanning**: Automatically scans log directories and organizes files by date
- **Log Parsing**: Parses `bandwhich` log files containing network traffic data
- **Multi-Format Reports**: Generates reports in JSON, CSV, and Parquet formats
- **Email Notifications**: Sends daily traffic reports with configurable email templates
- **Log Archiving**: Compresses and archives processed log files (ZIP, tar.gz)
- **Parallel Processing**: Efficiently processes multiple log files concurrently
- **Extensible Analysis**: Support for trend analysis, anomaly detection, and pattern recognition (in development)

## Project Structure

```
network-monitor/
├── config/
│   └── settings.yaml          # Main configuration file
├── doc/
│   └── testsuites.md          # Test documentation
├── src/
│   ├── main.py                # Application entry point
│   ├── config_manager.py      # Configuration management
│   ├── file_scanner.py        # Log file scanner
│   ├── log_parser.py          # Bandwhich log parser
│   ├── report_generator.py    # Report generator (JSON/CSV/Parquet)
│   ├── email_sender.py        # Email notification handler
│   ├── archive_manager.py     # Log archiving handler
│   ├── parallel_processor.py  # Parallel processing engine
│   └── utils/                 # Utility modules
├── tests/                     # Comprehensive test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   ├── functional/            # Functional tests
│   └── performance/           # Performance tests
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── Makefile                   # Build and test commands
└── run_tests.py              # Test runner

```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd network-monitor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install development dependencies (optional, for testing):
```bash
pip install -r requirements-dev.txt
```

4. Configure the system:
```bash
cp config/settings.yaml config/settings.yaml.local
# Edit settings.yaml.local with your configuration
```

## Configuration

Edit `config/settings.yaml` to configure the system:

```yaml
paths:
  log_dir: "~/audit/bandwhich/log"      # Directory containing bandwhich logs
  report_dir: "~/audit/bandwhich/reports"  # Output directory for reports
  archive_dir: "~/audit/bandwhich/archive"  # Directory for archived logs

email:
  smtp_server: "smtp.example.com"
  smtp_port: 587
  use_tls: true
  username: "your_email@example.com"
  password: "your_password"  # Consider using environment variables
  to_addrs:
    - "recipient@example.com"

processing:
  max_workers: 4  # Number of parallel workers

reports:
  format: "json"
  include_csv: true
  compress_reports: true

archive:
  enabled: true
  compress_format: "zip"
  retention_days: 30
```

## Usage

### Generate Reports

Process all pending log files and generate reports:

```bash
python src/main.py report --config config/settings.yaml
```

### Generate Reports for Specific Date

Process logs for a specific date:

```bash
# Process today's logs
python src/main.py report --date today

# Process yesterday's logs
python src/main.py report --date yesterday

# Process logs for last week
python src/main.py report --date week

# Process logs for specific date (YYYYMMDD)
python src/main.py report --date 20250101
```

### Analysis Mode (Experimental)

Perform traffic analysis:

```bash
# Trend analysis
python src/main.py analysis --type trend --date week

# Anomaly detection
python src/main.py analysis --type anomaly --date month

# Pattern recognition
python src/main.py analysis --type patterns --date week
```

## Testing

The project includes a comprehensive test suite covering unit, integration, functional, and performance tests.

### Run All Tests

```bash
make test
# or
python run_tests.py all
```

### Run Specific Test Categories

```bash
# Unit tests
make test-unit

# Integration tests
make test-integration

# Functional tests
make test-functional

# Performance tests
make test-performance
```

### Test with Coverage

```bash
make coverage
```

### Parallel Test Execution

```bash
make test-parallel
```

### HTML Test Reports

```bash
make test-html
```

## Development

### Code Quality

Run code quality checks:

```bash
make lint
```

### Code Formatting

Format code using Black and isort:

```bash
make format
```

### Security Scan

Run security checks:

```bash
make security
```

### Dependency Check

Check for dependency issues:

```bash
make deps
```

### Full CI Pipeline

Run the complete CI pipeline:

```bash
make ci
```

## Report Formats

### JSON Format

```json
{
  "timestamp": "2025-01-01T12:00:00",
  "total_upload_bps": 1024000,
  "total_download_bps": 5120000,
  "top_processes": [
    {
      "pid": 1234,
      "name": "chrome",
      "upload_bps": 512000,
      "download_bps": 2560000
    }
  ],
  "connections": [...]
}
```

### CSV Format

Process name, PID, Upload (bps), Download (bps), Local Port, Remote Address, Protocol
chrome,1234,512000,2560000,54321,192.168.1.100:443,tcp

### Parquet Format

Optimized columnar format for large datasets and analytics.

## Email Notifications

The system sends daily traffic reports via email with:

- Traffic summary statistics
- Top processes by bandwidth usage
- Connection details
- Attachments for reports (JSON, CSV, Parquet)

Email templates can be customized in `config/email_templates/`.

## Archiving

Processed log files are automatically archived:

- Configurable compression format (ZIP, tar.gz)
- Optional deletion of original logs
- Automatic cleanup of old archives based on retention period
- Configurable retention days

## Troubleshooting

### Common Issues

1. **No log files found**
   - Verify `log_dir` path in configuration
   - Check file permissions

2. **Email sending fails**
   - Verify SMTP settings and credentials
   - Check firewall/network connectivity

3. **Parsing errors**
   - Ensure log files are in correct `bandwhich` format
   - Check for corrupted log files

### Debug Mode

Enable verbose logging:

```bash
python src/main.py report --config config/settings.yaml --verbose
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Write tests for new features
2. Ensure all tests pass (`make test`)
3. Run code quality checks (`make lint`)
4. Follow the existing code style

## License

[Add your license information here]

## Author

[Add author information]

## Acknowledgments

- [bandwhich](https://github.com/imsnif/bandwhich) - Network bandwidth monitoring tool
- All contributors and users
