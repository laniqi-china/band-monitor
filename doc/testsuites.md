# 网络监控系统 - 完整测试套件

## 一、测试目录结构

```
tests/
├── __init__.py
├── conftest.py                    # pytest配置和fixture
├── unit/                          # 单元测试
│   ├── __init__.py
│   ├── test_config_manager.py
│   ├── test_file_scanner.py
│   ├── test_log_parser.py
│   ├── test_report_generator.py
│   ├── test_email_sender.py
│   ├── test_archive_manager.py
│   ├── test_parallel_processor.py
│   └── utils/                     # 工具类单元测试
│       ├── test_validators.py
│       ├── test_date_utils.py
│       └── test_logger.py
├── integration/                   # 集成测试
│   ├── __init__.py
│   ├── test_end_to_end.py
│   ├── test_cli.py
│   └── test_pipeline.py
├── functional/                    # 功能测试
│   ├── __init__.py
│   ├── test_report_generation.py
│   └── test_email_delivery.py
├── performance/                   # 性能测试
│   ├── __init__.py
│   ├── test_scalability.py
│   └── test_memory_usage.py
├── fixtures/                      # 测试数据
│   ├── sample_logs/
│   │   ├── bandwhich_20250101_1200.log
│   │   └── bandwhich_20250101_1201.log
│   ├── test_config.yaml
│   └── test_emails/
│       └── test_template.html
└── test_reports/                  # 测试报告输出
    ├── html/
    └── xml/
```

## 二、测试配置文件

### `tests/conftest.py`

```python
import pytest
import tempfile
import shutil
import sys
import os
from pathlib import Path
from typing import Dict, Any, Generator
import yaml
import json
from datetime import datetime, timedelta
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_manager import ConfigManager
from src.utils.logger import setup_logging

@pytest.fixture(scope="session")
def project_root_path():
    """返回项目根目录路径"""
    return project_root

@pytest.fixture(scope="function")
def temp_dir():
    """创建临时目录"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    # 清理临时目录
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)

@pytest.fixture(scope="function")
def sample_config() -> Dict[str, Any]:
    """返回测试配置"""
    return {
        'version': '1.0',
        'paths': {
            'log_dir': './test_logs',
            'report_dir': './test_reports',
            'archive_dir': './test_archive',
            'temp_dir': './test_temp'
        },
        'email': {
            'smtp_server': 'smtp.test.com',
            'smtp_port': 587,
            'use_ssl': False,
            'use_tls': True,
            'username': 'test@test.com',
            'password': 'test_password',
            'from_addr': 'test@test.com',
            'to_addrs': ['recipient@test.com'],
            'cc_addrs': [],
            'subject_prefix': 'TEST - 网络流量监控报告'
        },
        'processing': {
            'max_workers': 2,
            'batch_size': 100,
            'chunk_size': 1024,
            'keep_temp_files': False
        },
        'reports': {
            'format': 'json',
            'include_csv': True,
            'compress_reports': False,
            'generate_summary': True,
            'include_charts': False
        },
        'archive': {
            'enabled': True,
            'compress_format': 'zip',
            'keep_original': False,
            'retention_days': 7,
            'clean_old_archives': True
        },
        'logging': {
            'level': 'DEBUG',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file_size': '1MB',
            'backup_count': 2,
            'enable_console': False
        }
    }

@pytest.fixture(scope="function")
def config_manager(temp_dir, sample_config):
    """创建配置管理器实例"""
    # 创建配置文件
    config_file = temp_dir / 'test_config.yaml'
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(sample_config, f)

    # 更新路径到临时目录
    sample_config['paths']['log_dir'] = str(temp_dir / 'test_logs')
    sample_config['paths']['report_dir'] = str(temp_dir / 'test_reports')
    sample_config['paths']['archive_dir'] = str(temp_dir / 'test_archive')
    sample_config['paths']['temp_dir'] = str(temp_dir / 'test_temp')

    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(sample_config, f)

    return ConfigManager(str(config_file))

@pytest.fixture(scope="function")
def sample_log_data():
    """返回示例日志数据"""
    return """Refreshing:
process: <12345> "firefox" up/down Bps: 150/120 connections: 2
connection: <12345> <enp3s0>:54321 => 192.168.1.100:443 (tcp) up/down Bps: 100/80 process: "firefox"
connection: <12345> <enp3s0>:54322 => 8.8.8.8:53 (udp) up/down Bps: 50/40 process: "firefox"
remote_address: <12345> 192.168.1.100 up/down Bps: 100/80 connections: 1
remote_address: <12345> 8.8.8.8 up/down Bps: 50/40 connections: 1

Refreshing:
process: <12346> "chrome" up/down Bps: 200/180 connections: 1
connection: <12346> <enp3s0>:54323 => 10.0.0.1:80 (tcp) up/down Bps: 200/180 process: "chrome"
remote_address: <12346> 10.0.0.1 up/down Bps: 200/180 connections: 1
"""

@pytest.fixture(scope="function")
def sample_traffic_records():
    """返回示例流量记录"""
    from datetime import datetime
    from src.log_parser import TrafficRecord

    return [
        TrafficRecord(
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            pid=12345,
            process_name='firefox',
            local_interface='enp3s0',
            local_port=54321,
            remote_address='192.168.1.100',
            remote_port=443,
            protocol='tcp',
            upload_bps=100,
            download_bps=80,
            source_file='bandwhich_20240101_1000.log'
        ),
        TrafficRecord(
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            pid=12345,
            process_name='firefox',
            local_interface='enp3s0',
            local_port=54322,
            remote_address='8.8.8.8',
            remote_port=53,
            protocol='udp',
            upload_bps=50,
            download_bps=40,
            source_file='bandwhich_20240101_1000.log'
        ),
        TrafficRecord(
            timestamp=datetime(2024, 1, 1, 10, 0, 1),
            pid=12346,
            process_name='chrome',
            local_interface='enp3s0',
            local_port=54323,
            remote_address='10.0.0.1',
            remote_port=80,
            protocol='tcp',
            upload_bps=200,
            download_bps=180,
            source_file='bandwhich_20240101_1000.log'
        )
    ]

@pytest.fixture(scope="function")
def mock_smtp_server():
    """模拟SMTP服务器"""
    import smtplib
    from unittest.mock import Mock, patch

    mock_server = Mock(spec=smtplib.SMTP)
    mock_server.send_message = Mock()
    mock_server.quit = Mock()

    with patch('smtplib.SMTP') as mock_smtp:
        mock_smtp.return_value = mock_server
        yield mock_server

@pytest.fixture(scope="session")
def test_logger():
    """测试日志记录器"""
    logger = logging.getLogger('test')
    logger.setLevel(logging.DEBUG)

    # 添加控制台处理器
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

@pytest.fixture(scope="function")
def create_sample_log_file(temp_dir):
    """创建示例日志文件的fixture"""
    def _create_file(filename: str, content: str = None) -> Path:
        log_dir = temp_dir / 'test_logs'
        log_dir.mkdir(parents=True, exist_ok=True)

        file_path = log_dir / filename

        if content is None:
            content = """Refreshing:
process: <12345> "firefox" up/down Bps: 150/120 connections: 2
connection: <12345> <enp3s0>:54321 => 192.168.1.100:443 (tcp) up/down Bps: 100/80 process: "firefox"
connection: <12345> <enp3s0>:54322 => 8.8.8.8:53 (udp) up/down Bps: 50/40 process: "firefox"
remote_address: <12345> 192.168.1.100 up/down Bps: 100/80 connections: 1
remote_address: <12345> 8.8.8.8 up/down Bps: 50/40 connections: 1
"""

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_path

    return _create_file

@pytest.fixture(scope="function")
def date_range():
    """返回测试日期范围"""
    from datetime import date
    return date(2024, 1, 1), date(2024, 1, 5)

class MockResponse:
    """模拟HTTP响应"""

    def __init__(self, status_code=200, content=None, json_data=None):
        self.status_code = status_code
        self.content = content or b''
        self._json_data = json_data or {}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")

@pytest.fixture(scope="module")
def vcr_config():
    """配置vcrpy用于HTTP请求录制/重放"""
    return {
        'filter_headers': [('authorization', 'DUMMY')],
        'record_mode': 'once',
        'match_on': ['method', 'scheme', 'host', 'port', 'path', 'query']
    }
```

## 三、单元测试

### `tests/unit/test_config_manager.py`

```python
import pytest
import yaml
from pathlib import Path
import tempfile
import shutil

from src.config_manager import ConfigManager, PathConfig, EmailConfig


class TestPathConfig:
    """测试路径配置类"""

    def test_from_dict(self):
        """测试从字典创建PathConfig"""
        data = {
            'log_dir': './logs',
            'report_dir': './reports',
            'archive_dir': './archive',
            'temp_dir': './temp'
        }

        config = PathConfig.from_dict(data)

        assert config.log_dir == Path('./logs')
        assert config.report_dir == Path('./reports')
        assert config.archive_dir == Path('./archive')
        assert config.temp_dir == Path('./temp')

    def test_path_resolution(self, temp_dir):
        """测试路径解析"""
        data = {
            'log_dir': str(temp_dir / 'logs'),
            'report_dir': str(temp_dir / 'reports'),
            'archive_dir': str(temp_dir / 'archive'),
            'temp_dir': str(temp_dir / 'temp')
        }

        config = PathConfig.from_dict(data)

        assert config.log_dir.exists() is False
        assert str(config.log_dir).endswith('logs')


class TestEmailConfig:
    """测试邮件配置类"""

    def test_from_dict(self):
        """测试从字典创建EmailConfig"""
        data = {
            'smtp_server': 'smtp.test.com',
            'smtp_port': 587,
            'use_ssl': False,
            'use_tls': True,
            'username': 'user@test.com',
            'password': 'password123',
            'from_addr': 'sender@test.com',
            'to_addrs': ['recipient1@test.com', 'recipient2@test.com'],
            'cc_addrs': ['cc@test.com'],
            'subject_prefix': '测试'
        }

        config = EmailConfig.from_dict(data)

        assert config.smtp_server == 'smtp.test.com'
        assert config.smtp_port == 587
        assert config.use_ssl is False
        assert config.use_tls is True
        assert config.username == 'user@test.com'
        assert config.password == 'password123'
        assert config.from_addr == 'sender@test.com'
        assert len(config.to_addrs) == 2
        assert len(config.cc_addrs) == 1
        assert config.subject_prefix == '测试'

    def test_default_values(self):
        """测试默认值"""
        data = {
            'smtp_server': 'smtp.test.com',
            'smtp_port': 465,
            'username': 'user@test.com',
            'password': 'password123',
            'from_addr': 'sender@test.com',
            'to_addrs': ['recipient@test.com']
        }

        config = EmailConfig.from_dict(data)

        assert config.use_ssl is False  # 默认值
        assert config.use_tls is True   # 默认值
        assert config.cc_addrs == []    # 默认值
        assert config.subject_prefix == '网络流量监控报告'  # 默认值


class TestConfigManager:
    """测试配置管理器"""

    def test_load_config(self, temp_dir, sample_config):
        """测试加载配置"""
        config_file = temp_dir / 'config.yaml'

        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(sample_config, f)

        manager = ConfigManager(str(config_file))

        # 验证配置已加载
        assert manager.config == sample_config

    def test_missing_config_file(self, temp_dir):
        """测试缺失配置文件"""
        config_file = temp_dir / 'missing.yaml'

        with pytest.raises(FileNotFoundError):
            ConfigManager(str(config_file))

    def test_get_path_config(self, config_manager):
        """测试获取路径配置"""
        paths = config_manager.get_path_config()

        assert isinstance(paths, PathConfig)
        assert 'test_logs' in str(paths.log_dir)
        assert 'test_reports' in str(paths.report_dir)

    def test_get_email_config(self, config_manager):
        """测试获取邮件配置"""
        email_config = config_manager.get_email_config()

        assert isinstance(email_config, EmailConfig)
        assert email_config.smtp_server == 'smtp.test.com'
        assert email_config.smtp_port == 587

    def test_update_config(self, config_manager):
        """测试更新配置"""
        # 更新处理配置中的最大工作线程数
        config_manager.update_config('processing', 'max_workers', 8)

        # 验证更新
        processing_config = config_manager.get_processing_config()
        assert processing_config['max_workers'] == 8

        # 验证配置已保存
        with open(config_manager.config_file, 'r', encoding='utf-8') as f:
            saved_config = yaml.safe_load(f)

        assert saved_config['processing']['max_workers'] == 8

    def test_to_json(self, config_manager):
        """测试转换为JSON"""
        json_str = config_manager.to_json()

        # 验证JSON格式
        import json
        parsed = json.loads(json_str)

        assert 'version' in parsed
        assert 'paths' in parsed
        assert 'email' in parsed

    def test_directory_creation(self, config_manager):
        """测试目录自动创建"""
        paths = config_manager.get_path_config()

        # 所有目录都应已创建
        assert paths.log_dir.exists()
        assert paths.report_dir.exists()
        assert paths.archive_dir.exists()
        assert paths.temp_dir.exists()

    def test_invalid_config_format(self, temp_dir):
        """测试无效配置格式"""
        config_file = temp_dir / 'invalid.yaml'

        # 写入无效的YAML
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write('invalid: yaml: : :')

        # 应该能够创建实例，但在使用时会出错
        manager = ConfigManager(str(config_file))

        # 尝试访问配置应该引发异常
        with pytest.raises(Exception):
            _ = manager.get_path_config()
```

### `tests/unit/test_file_scanner.py`

```python
import pytest
from datetime import datetime, date
from pathlib import Path
import tempfile

from src.file_scanner import FileScanner, LogFileInfo


class TestLogFileInfo:
    """测试日志文件信息类"""

    def test_initialization(self, temp_dir):
        """测试初始化"""
        file_path = temp_dir / 'test.log'
        file_path.touch()

        file_info = LogFileInfo(
            path=file_path,
            date=date(2024, 1, 1),
            base_time=datetime(2024, 1, 1, 12, 0, 0),
            size=1024,
            md5='test_md5',
            modified_time=datetime.now()
        )

        assert file_info.path == file_path
        assert file_info.date == date(2024, 1, 1)
        assert file_info.size == 1024
        assert file_info.md5 == 'test_md5'

    def test_str_representation(self, temp_dir):
        """测试字符串表示"""
        file_path = temp_dir / 'test.log'
        file_path.touch()

        file_info = LogFileInfo(
            path=file_path,
            date=date(2024, 1, 1),
            base_time=datetime(2024, 1, 1, 12, 0, 0),
            size=2048,
            md5='test',
            modified_time=datetime.now()
        )

        assert 'test.log' in str(file_info)
        assert '2.0KB' in str(file_info)


class TestFileScanner:
    """测试文件扫描器"""

    def test_scan_empty_directory(self, temp_dir):
        """测试扫描空目录"""
        scanner = FileScanner(temp_dir)
        result = scanner.scan_files()

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_scan_valid_files(self, temp_dir):
        """测试扫描有效文件"""
        # 创建测试日志文件
        log_dir = temp_dir / 'logs'
        log_dir.mkdir()

        # 创建不同日期的文件
        files = [
            'bandwhich_20240101_1200.log',
            'bandwhich_20240101_1300.log',
            'bandwhich_20240102_1200.log',
            'bandwhich_20240102_1300.log'
        ]

        for filename in files:
            file_path = log_dir / filename
            file_path.touch()

        scanner = FileScanner(log_dir)
        result = scanner.scan_files()

        # 验证结果
        assert len(result) == 2  # 两个日期
        assert date(2024, 1, 1) in result
        assert date(2024, 1, 2) in result

        # 每个日期应该有两个文件
        assert len(result[date(2024, 1, 1)]) == 2
        assert len(result[date(2024, 1, 2)]) == 2

    def test_scan_invalid_filenames(self, temp_dir):
        """测试扫描无效文件名"""
        log_dir = temp_dir / 'logs'
        log_dir.mkdir()

        # 创建无效文件名的文件
        invalid_files = [
            'invalid.log',
            'bandwhich_20241301_1200.log',  # 无效月份
            'bandwhich_20240101_2500.log',  # 无效时间
            'bandwhich.log'
        ]

        for filename in invalid_files:
            file_path = log_dir / filename
            file_path.touch()

        scanner = FileScanner(log_dir)
        result = scanner.scan_files()

        # 应该没有有效文件
        assert len(result) == 0

    def test_analyze_file(self, temp_dir):
        """测试分析单个文件"""
        log_dir = temp_dir / 'logs'
        log_dir.mkdir()

        # 创建有效文件
        file_path = log_dir / 'bandwhich_20240101_1200.log'
        file_path.touch()

        # 写入一些内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('test content')

        scanner = FileScanner(log_dir)
        file_info = scanner._analyze_file(file_path)

        # 验证分析结果
        assert file_info is not None
        assert file_info.path == file_path
        assert file_info.date == date(2024, 1, 1)
        assert file_info.base_time == datetime(2024, 1, 1, 12, 0)
        assert file_info.size > 0
        assert len(file_info.md5) == 32  # MD5哈希长度

    def test_analyze_invalid_file(self, temp_dir):
        """测试分析无效文件"""
        log_dir = temp_dir / 'logs'
        log_dir.mkdir()

        # 创建无效文件名的文件
        file_path = log_dir / 'invalid_filename.log'
        file_path.touch()

        scanner = FileScanner(log_dir)
        file_info = scanner._analyze_file(file_path)

        # 应该返回None
        assert file_info is None

    def test_calculate_md5(self, temp_dir):
        """测试计算MD5"""
        file_path = temp_dir / 'test.txt'

        # 写入固定内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('Hello, World!')

        scanner = FileScanner(temp_dir)
        md5_hash = scanner._calculate_md5(file_path)

        # 验证MD5哈希
        assert len(md5_hash) == 32
        assert md5_hash == '65a8e27d8879283831b664bd8b7f0ad4'  # "Hello, World!"的MD5

    def test_check_report_exists(self, temp_dir):
        """测试检查报告是否存在"""
        report_dir = temp_dir / 'reports'
        report_dir.mkdir()

        scanner = FileScanner(temp_dir)

        # 报告不存在的情况
        test_date = date(2024, 1, 1)
        exists = scanner.check_report_exists(test_date, report_dir)
        assert exists is False

        # 创建报告文件
        report_file = report_dir / 'report_20240101.json'
        report_file.touch()

        # 报告应该存在
        exists = scanner.check_report_exists(test_date, report_dir)
        assert exists is True

        # 测试其他模式
        report_file2 = report_dir / 'summary_20240101.json'
        report_file2.touch()

        exists = scanner.check_report_exists(test_date, report_dir)
        assert exists is True

    def test_scan_with_subdirectories(self, temp_dir):
        """测试扫描包含子目录的情况"""
        log_dir = temp_dir / 'logs'
        log_dir.mkdir()

        # 在子目录中创建文件（应该被忽略）
        subdir = log_dir / 'subdir'
        subdir.mkdir()
        subfile = subdir / 'bandwhich_20240101_1200.log'
        subfile.touch()

        # 在主目录中创建文件
        mainfile = log_dir / 'bandwhich_20240102_1200.log'
        mainfile.touch()

        scanner = FileScanner(log_dir)
        result = scanner.scan_files()

        # 应该只找到主目录中的文件
        assert len(result) == 1
        assert date(2024, 1, 2) in result

    def test_file_sorting(self, temp_dir):
        """测试文件排序"""
        log_dir = temp_dir / 'logs'
        log_dir.mkdir()

        # 创建不同时间的文件
        files = [
            'bandwhich_20240101_1400.log',
            'bandwhich_20240101_1200.log',
            'bandwhich_20240101_1300.log'
        ]

        for filename in files:
            file_path = log_dir / filename
            file_path.touch()

        scanner = FileScanner(log_dir)
        result = scanner.scan_files()

        # 获取第一天的文件
        day_files = result.get(date(2024, 1, 1), [])

        # 验证文件按时间排序
        times = [file.base_time for file in day_files]
        assert times == sorted(times)
```

### `tests/unit/test_log_parser.py`

```python
import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from src.log_parser import (
    LogParser,
    ProcessRecord,
    ConnectionRecord,
    TrafficRecord
)


class TestProcessRecord:
    """测试进程记录类"""

    def test_initialization(self):
        """测试初始化"""
        record = ProcessRecord(
            pid=12345,
            name='test_process',
            upload_bps=100,
            download_bps=200,
            connections=3
        )

        assert record.pid == 12345
        assert record.name == 'test_process'
        assert record.upload_bps == 100
        assert record.download_bps == 200
        assert record.connections == 3


class TestConnectionRecord:
    """测试连接记录类"""

    def test_initialization(self):
        """测试初始化"""
        record = ConnectionRecord(
            pid=12345,
            local_interface='eth0',
            local_port=54321,
            remote_address='192.168.1.1',
            remote_port=80,
            protocol='tcp',
            upload_bps=50,
            download_bps=100,
            process_name='test_process'
        )

        assert record.pid == 12345
        assert record.local_interface == 'eth0'
        assert record.local_port == 54321
        assert record.remote_address == '192.168.1.1'
        assert record.remote_port == 80
        assert record.protocol == 'tcp'
        assert record.upload_bps == 50
        assert record.download_bps == 100
        assert record.process_name == 'test_process'


class TestTrafficRecord:
    """测试流量记录类"""

    def test_initialization(self):
        """测试初始化"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        record = TrafficRecord(
            timestamp=timestamp,
            pid=12345,
            process_name='firefox',
            local_interface='eth0',
            local_port=54321,
            remote_address='8.8.8.8',
            remote_port=443,
            protocol='tcp',
            upload_bps=100,
            download_bps=200,
            source_file='test.log'
        )

        assert record.timestamp == timestamp
        assert record.pid == 12345
        assert record.process_name == 'firefox'
        assert record.local_interface == 'eth0'
        assert record.local_port == 54321
        assert record.remote_address == '8.8.8.8'
        assert record.remote_port == 443
        assert record.protocol == 'tcp'
        assert record.upload_bps == 100
        assert record.download_bps == 200
        assert record.source_file == 'test.log'


class TestLogParser:
    """测试日志解析器"""

    def test_parse_process_line_valid(self):
        """测试解析有效的进程行"""
        parser = LogParser()

        line = 'process: <12345> "firefox" up/down Bps: 100/200 connections: 3'
        result = parser._parse_process_line(line)

        assert result is not None
        assert result.pid == 12345
        assert result.name == 'firefox'
        assert result.upload_bps == 100
        assert result.download_bps == 200
        assert result.connections == 3

    def test_parse_process_line_invalid(self):
        """测试解析无效的进程行"""
        parser = LogParser()

        # 无效格式
        line = 'process: invalid format'
        result = parser._parse_process_line(line)

        assert result is None

        # 空行
        line = ''
        result = parser._parse_process_line(line)

        assert result is None

    def test_parse_connection_line_valid(self):
        """测试解析有效的连接行"""
        parser = LogParser()

        line = 'connection: <12345> <eth0>:54321 => 8.8.8.8:443 (tcp) up/down Bps: 100/200 process: "firefox"'
        result = parser._parse_connection_line(line)

        assert result is not None
        assert result.pid == 12345
        assert result.local_interface == 'eth0'
        assert result.local_port == 54321
        assert result.remote_address == '8.8.8.8'
        assert result.remote_port == 443
        assert result.protocol == 'tcp'
        assert result.upload_bps == 100
        assert result.download_bps == 200
        assert result.process_name == 'firefox'

    def test_parse_connection_line_with_domain(self):
        """测试解析包含域名的连接行"""
        parser = LogParser()

        line = 'connection: <12345> <eth0>:54321 => google.com:443 (tcp) up/down Bps: 100/200 process: "firefox"'
        result = parser._parse_connection_line(line)

        assert result is not None
        assert result.remote_address == 'google.com'
        assert result.remote_port == 443

    def test_parse_connection_line_invalid(self):
        """测试解析无效的连接行"""
        parser = LogParser()

        # 无效格式
        line = 'connection: invalid format'
        result = parser._parse_connection_line(line)

        assert result is None

        # 缺少字段
        line = 'connection: <12345> <eth0>:54321 => 8.8.8.8:443 (tcp)'
        result = parser._parse_connection_line(line)

        assert result is None

    def test_parse_refresh_block(self):
        """测试解析刷新块"""
        parser = LogParser()

        block = """
process: <12345> "firefox" up/down Bps: 150/120 connections: 2
connection: <12345> <eth0>:54321 => 192.168.1.1:443 (tcp) up/down Bps: 100/80 process: "firefox"
connection: <12345> <eth0>:54322 => 8.8.8.8:53 (udp) up/down Bps: 50/40 process: "firefox"
"""

        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        records = parser._parse_refresh_block(block, timestamp, 'test.log')

        # 应该解析出两条连接记录
        assert len(records) == 2

        # 验证第一条记录
        record1 = records[0]
        assert record1.timestamp == timestamp
        assert record1.pid == 12345
        assert record1.process_name == 'firefox'
        assert record1.local_interface == 'eth0'
        assert record1.local_port == 54321
        assert record1.remote_address == '192.168.1.1'
        assert record1.remote_port == 443
        assert record1.protocol == 'tcp'
        assert record1.upload_bps == 100
        assert record1.download_bps == 80

        # 验证第二条记录
        record2 = records[1]
        assert record2.protocol == 'udp'
        assert record2.remote_address == '8.8.8.8'
        assert record2.remote_port == 53

    def test_parse_refresh_block_no_traffic(self):
        """测试解析无流量块"""
        parser = LogParser()

        block = '<NO TRAFFIC>'

        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        records = parser._parse_refresh_block(block, timestamp, 'test.log')

        # 应该返回空列表
        assert len(records) == 0

    def test_parse_refresh_block_unknown_process(self):
        """测试解析包含未知进程的块"""
        parser = LogParser()

        block = """
connection: <12345> <eth0>:54321 => 8.8.8.8:53 (udp) up/down Bps: 50/40 process: "<UNKNOWN>"
"""

        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        records = parser._parse_refresh_block(block, timestamp, 'test.log')

        # 应该解析出一条记录
        assert len(records) == 1

        # 进程名称应该是<UNKNOWN>
        assert records[0].process_name == '<UNKNOWN>'

    def test_parse_file(self, temp_dir, sample_log_data):
        """测试解析完整文件"""
        parser = LogParser()

        # 创建测试文件
        file_path = temp_dir / 'test.log'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sample_log_data)

        # 模拟LogFileInfo
        from src.file_scanner import LogFileInfo
        file_info = LogFileInfo(
            path=file_path,
            date=datetime(2024, 1, 1).date(),
            base_time=datetime(2024, 1, 1, 12, 0, 0),
            size=len(sample_log_data),
            md5='test',
            modified_time=datetime.now()
        )

        records = parser.parse_file(file_info)

        # 应该解析出3条记录
        assert len(records) == 3

        # 验证记录
        assert records[0].process_name == 'firefox'
        assert records[0].remote_address == '192.168.1.100'
        assert records[0].upload_bps == 100

        assert records[1].process_name == 'firefox'
        assert records[1].remote_address == '8.8.8.8'
        assert records[1].protocol == 'udp'

        assert records[2].process_name == 'chrome'
        assert records[2].remote_address == '10.0.0.1'

    def test_parse_file_empty(self, temp_dir):
        """测试解析空文件"""
        parser = LogParser()

        # 创建空文件
        file_path = temp_dir / 'empty.log'
        file_path.touch()

        from src.file_scanner import LogFileInfo
        file_info = LogFileInfo(
            path=file_path,
            date=datetime(2024, 1, 1).date(),
            base_time=datetime(2024, 1, 1, 12, 0, 0),
            size=0,
            md5='test',
            modified_time=datetime.now()
        )

        records = parser.parse_file(file_info)

        # 应该返回空列表
        assert len(records) == 0

    def test_parse_file_with_multiple_refreshes(self, temp_dir):
        """测试解析包含多个刷新块的文件"""
        parser = LogParser()

        content = """
Refreshing:
process: <12345> "firefox" up/down Bps: 100/80 connections: 1
connection: <12345> <eth0>:54321 => 8.8.8.8:443 (tcp) up/down Bps: 100/80 process: "firefox"
remote_address: <12345> 8.8.8.8 up/down Bps: 100/80 connections: 1

Refreshing:
process: <12346> "chrome" up/down Bps: 200/150 connections: 1
connection: <12346> <eth0>:54322 => 1.1.1.1:80 (tcp) up/down Bps: 200/150 process: "chrome"
remote_address: <12346> 1.1.1.1 up/down Bps: 200/150 connections: 1

Refreshing:
<NO TRAFFIC>
"""

        file_path = temp_dir / 'test.log'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        from src.file_scanner import LogFileInfo
        file_info = LogFileInfo(
            path=file_path,
            date=datetime(2024, 1, 1).date(),
            base_time=datetime(2024, 1, 1, 12, 0, 0),
            size=len(content),
            md5='test',
            modified_time=datetime.now()
        )

        records = parser.parse_file(file_info)

        # 应该解析出2条记录（跳过NO TRAFFIC）
        assert len(records) == 2

        # 时间戳应该递增
        assert records[0].timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert records[1].timestamp == datetime(2024, 1, 1, 12, 0, 1)

    def test_records_to_json(self, sample_traffic_records):
        """测试将记录转换为JSON"""
        parser = LogParser()

        json_str = parser.records_to_json(sample_traffic_records)

        # 验证JSON格式
        parsed = json.loads(json_str)

        assert isinstance(parsed, list)
        assert len(parsed) == 3

        # 验证第一条记录
        record1 = parsed[0]
        assert record1['pid'] == 12345
        assert record1['process_name'] == 'firefox'
        assert record1['upload_bps'] == 100
        assert 'timestamp' in record1  # 应该被转换为字符串

    def test_save_to_json_file(self, temp_dir, sample_traffic_records):
        """测试保存记录到JSON文件"""
        parser = LogParser()

        output_path = temp_dir / 'output.json'
        parser.save_to_json_file(sample_traffic_records, output_path)

        # 验证文件已创建
        assert output_path.exists()

        # 验证文件内容
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 应该是有效的JSON数组
        parsed = json.loads(content)
        assert isinstance(parsed, list)
        assert len(parsed) == 3

        # 验证记录顺序
        assert parsed[0]['pid'] == 12345
        assert parsed[1]['pid'] == 12345
        assert parsed[2]['pid'] == 12346

    def test_read_refresh_blocks(self, temp_dir):
        """测试流式读取刷新块"""
        parser = LogParser()

        content = """Before first refresh
Refreshing:
First block
Refreshing:
Second block
Refreshing:
Third block
After last refresh"""

        file_path = temp_dir / 'test.log'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        with open(file_path, 'r', encoding='utf-8') as f:
            blocks = list(parser._read_refresh_blocks(f))

        # 应该读取到3个块
        assert len(blocks) == 3

        # 验证块内容
        assert blocks[0].strip() == 'Before first refresh'
        assert blocks[1].strip() == 'First block'
        assert blocks[2].strip() == 'Second block\nThird block\nAfter last refresh'
```

### `tests/unit/test_report_generator.py`

```python
import pytest
import pandas as pd
import json
from datetime import date, datetime
from pathlib import Path
import tempfile
import csv

from src.report_generator import ReportGenerator
from src.log_parser import TrafficRecord


class TestReportGenerator:
    """测试报告生成器"""

    @pytest.fixture
    def report_generator(self, temp_dir):
        """创建报告生成器实例"""
        output_dir = temp_dir / 'reports'
        return ReportGenerator(output_dir)

    @pytest.fixture
    def sample_dataframe(self, sample_traffic_records):
        """创建示例DataFrame"""
        from dataclasses import asdict
        records_dict = [asdict(r) for r in sample_traffic_records]
        return pd.DataFrame(records_dict)

    def test_initialization(self, temp_dir):
        """测试初始化"""
        output_dir = temp_dir / 'reports'
        generator = ReportGenerator(output_dir)

        assert generator.output_dir == output_dir
        assert output_dir.exists()  # 目录应该已创建

    def test_generate_daily_report_empty(self, report_generator):
        """测试生成空报告"""
        date_key = date(2024, 1, 1)
        empty_records = []

        result = report_generator.generate_daily_report(
            date_key,
            empty_records,
            include_csv=True,
            compress=False
        )

        # 应该返回空字典
        assert result == {}

    def test_generate_daily_report_with_data(self, report_generator, sample_traffic_records):
        """测试生成有数据的报告"""
        date_key = date(2024, 1, 1)

        result = report_generator.generate_daily_report(
            date_key,
            sample_traffic_records,
            include_csv=True,
            compress=False
        )

        # 应该生成多个文件
        assert len(result) >= 3  # JSON, CSV, 汇总报告

        # 验证文件存在
        json_file = report_generator.output_dir / 'report_20240101.json'
        csv_file = report_generator.output_dir / 'report_20240101.csv'
        summary_file = report_generator.output_dir / 'summary_20240101.json'

        assert json_file.exists()
        assert csv_file.exists()
        assert summary_file.exists()

        # 验证JSON文件内容
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        assert isinstance(json_data, list)
        assert len(json_data) == 3

        # 验证CSV文件内容
        df = pd.read_csv(csv_file)
        assert len(df) == 3
        assert 'process_name' in df.columns
        assert 'upload_bps' in df.columns

        # 验证汇总报告
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)

        assert 'overview' in summary_data
        assert 'process_summary' in summary_data
        assert 'remote_summary' in summary_data

    def test_generate_daily_report_without_csv(self, report_generator, sample_traffic_records):
        """测试不生成CSV的报告"""
        date_key = date(2024, 1, 1)

        result = report_generator.generate_daily_report(
            date_key,
            sample_traffic_records,
            include_csv=False,
            compress=False
        )

        # 应该不包含CSV文件
        csv_file = report_generator.output_dir / 'report_20240101.csv'
        assert not csv_file.exists()

        # 应该包含JSON文件
        json_file = report_generator.output_dir / 'report_20240101.json'
        assert json_file.exists()

    def test_save_detailed_report(self, report_generator, sample_dataframe):
        """测试保存详细报告"""
        date_str = '20240101'

        result = report_generator._save_detailed_report(date_str, sample_dataframe)

        # 应该返回多个文件路径
        assert 'json' in result
        assert 'csv' in result

        # 验证文件已创建
        json_file = result['json']
        csv_file = result['csv']

        assert json_file.exists()
        assert csv_file.exists()

        # 验证JSON文件内容
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        assert len(json_data) == 3

        # 验证CSV文件内容
        df = pd.read_csv(csv_file)
        assert len(df) == 3

    def test_calculate_process_summary(self, report_generator, sample_dataframe):
        """测试计算进程汇总"""
        summary = report_generator._calculate_process_summary(sample_dataframe)

        # 应该是DataFrame
        assert isinstance(summary, pd.DataFrame)

        # 应该有2个进程
        assert len(summary) == 2

        # 验证列
        expected_columns = [
            'process_name', 'upload_sum', 'upload_mean', 'upload_max', 'upload_std',
            'download_sum', 'download_mean', 'download_max', 'download_std',
            'unique_pids', 'unique_remotes', 'upload_pct', 'download_pct'
        ]

        for col in expected_columns:
            assert col in summary.columns

        # 验证firefox的统计
        firefox_row = summary[summary['process_name'] == 'firefox'].iloc[0]
        assert firefox_row['upload_sum'] == 150  # 100 + 50
        assert firefox_row['download_sum'] == 120  # 80 + 40
        assert firefox_row['unique_pids'] == 1

    def test_calculate_remote_summary(self, report_generator, sample_dataframe):
        """测试计算远程地址汇总"""
        summary = report_generator._calculate_remote_summary(sample_dataframe)

        assert isinstance(summary, pd.DataFrame)

        # 应该有3个远程地址
        assert len(summary) == 3

        # 验证列
        expected_columns = [
            'remote_address', 'upload_sum', 'upload_mean', 'upload_max',
            'download_sum', 'download_mean', 'download_max',
            'unique_processes', 'common_protocol', 'is_ip'
        ]

        for col in expected_columns:
            assert col in summary.columns

        # 验证IP地址检测
        ip_rows = summary[summary['is_ip'] == True]
        assert len(ip_rows) == 3  # 所有地址都是IP

    def test_calculate_time_summary(self, report_generator, sample_dataframe):
        """测试计算时间汇总"""
        # 添加小时列
        sample_dataframe['hour'] = pd.to_datetime(sample_dataframe['timestamp']).dt.hour

        summary = report_generator._calculate_time_summary(sample_dataframe)

        # 应该是字典
        assert isinstance(summary, dict)

        # 应该包含每小时汇总
        assert 'hourly' in summary

        hourly = summary['hourly']
        assert 'upload_bps' in hourly
        assert 'download_bps' in hourly
        assert 'process_name' in hourly

    def test_get_top_items(self, report_generator, sample_dataframe):
        """测试获取排名前N的项目"""
        # 按进程名称获取上传流量前2
        top_items = report_generator._get_top_items(
            sample_dataframe,
            'process_name',
            'upload_bps',
            2
        )

        assert isinstance(top_items, list)
        assert len(top_items) == 2

        # 验证排序
        assert top_items[0]['item'] == 'chrome'  # 200 > 150
        assert top_items[1]['item'] == 'firefox'

        # 使用自定义函数
        def total_traffic(group):
            return group['upload_bps'].sum() + group['download_bps'].sum()

        top_custom = report_generator._get_top_items(
            sample_dataframe,
            'process_name',
            total_traffic,
            2
        )

        assert len(top_custom) == 2

    def test_is_ip_address(self, report_generator):
        """测试IP地址检测"""
        # 有效IP地址
        assert report_generator._is_ip_address('192.168.1.1') is True
        assert report_generator._is_ip_address('8.8.8.8') is True
        assert report_generator._is_ip_address('255.255.255.255') is True

        # 无效IP地址
        assert report_generator._is_ip_address('example.com') is False
        assert report_generator._is_ip_address('192.168.1.256') is False  # 超出范围
        assert report_generator._is_ip_address('192.168.1') is False  # 不完整
        assert report_generator._is_ip_address('') is False

    def test_generate_statistics_report(self, report_generator, sample_dataframe):
        """测试生成统计报告"""
        date_str = '20240101'

        result = report_generator._generate_statistics_report(date_str, sample_dataframe)

        # 应该包含统计报告文件路径
        assert 'stats_json' in result

        stats_file = result['stats_json']
        assert stats_file.exists()

        # 验证统计报告内容
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats_data = json.load(f)

        assert 'date' in stats_data
        assert stats_data['date'] == date_str

        assert 'traffic_statistics' in stats_data
        assert 'connection_statistics' in stats_data
        assert 'process_statistics' in stats_data

        # 验证流量统计
        traffic_stats = stats_data['traffic_statistics']
        assert 'upload' in traffic_stats
        assert 'download' in traffic_stats

        # 验证上传流量总和
        assert traffic_stats['upload']['total_bytes'] == 350  # 100+50+200

    def test_compress_reports(self, report_generator, sample_dataframe, temp_dir):
        """测试压缩报告"""
        date_str = '20240101'

        # 先创建一些报告文件
        files = []
        for i in range(3):
            file_path = report_generator.output_dir / f'test_{i}.txt'
            file_path.write_text(f'Test content {i}')
            files.append(file_path)

        # 压缩文件
        zip_file = report_generator._compress_reports(date_str, files)

        # 验证压缩文件已创建
        assert zip_file.exists()
        assert zip_file.suffix == '.zip'

        # 验证压缩文件大小
        assert zip_file.stat().st_size > 0

    def test_generate_summary_report(self, report_generator, sample_dataframe):
        """测试生成汇总报告"""
        date_str = '20240101'

        result = report_generator._generate_summary_report(date_str, sample_dataframe)

        # 应该包含多个文件
        assert 'summary_json' in result
        assert 'summary_csv' in result

        # 验证JSON汇总报告
        json_file = result['summary_json']
        with open(json_file, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)

        assert 'overview' in summary_data
        assert 'process_summary' in summary_data
        assert 'remote_summary' in summary_data
        assert 'time_summary' in summary_data
        assert 'top_items' in summary_data

        # 验证概览数据
        overview = summary_data['overview']
        assert overview['total_records'] == 3
        assert overview['unique_processes'] == 2
        assert overview['unique_remote_addresses'] == 3

        # 验证CSV汇总报告
        csv_file = result['summary_csv']
        assert csv_file.exists()

        # 读取CSV并验证内容
        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 应该包含多个部分
        content = ''.join(lines)
        assert '=== 概览 ===' in content
        assert '=== 进程汇总 ===' in content
        assert '=== 远程地址汇总 ===' in content
```

### `tests/unit/test_email_sender.py`

```python
import pytest
import smtplib
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from src.email_sender import EmailSender
from src.config_manager import EmailConfig


class TestEmailSender:
    """测试邮件发送器"""

    @pytest.fixture
    def email_config(self):
        """创建邮件配置"""
        return EmailConfig(
            smtp_server='smtp.test.com',
            smtp_port=587,
            use_ssl=False,
            use_tls=True,
            username='test@test.com',
            password='test_password',
            from_addr='sender@test.com',
            to_addrs=['recipient1@test.com', 'recipient2@test.com'],
            cc_addrs=['cc@test.com'],
            subject_prefix='测试'
        )

    @pytest.fixture
    def email_sender(self, email_config):
        """创建邮件发送器实例"""
        return EmailSender(email_config)

    @pytest.fixture
    def sample_attachments(self, temp_dir):
        """创建示例附件"""
        attachments = []

        for i in range(2):
            file_path = temp_dir / f'test_{i}.txt'
            file_path.write_text(f'Test content {i}')
            attachments.append(file_path)

        return attachments

    def test_initialization(self, email_config):
        """测试初始化"""
        sender = EmailSender(email_config)

        assert sender.config == email_config
        assert sender.logger is not None

    def test_create_message_basic(self, email_sender):
        """测试创建基本邮件"""
        subject = '测试主题'
        body = '测试正文'
        content_type = 'plain'

        msg = email_sender._create_message(subject, body, content_type)

        # 验证邮件头
        assert msg['From'] == 'sender@test.com'
        assert msg['To'] == 'recipient1@test.com, recipient2@test.com'
        assert msg['Cc'] == 'cc@test.com'
        assert msg['Subject'] == '测试 - 测试主题'

        # 验证正文
        assert msg.get_content_type() == 'text/plain'
        assert msg.get_payload() == '测试正文'

    def test_create_message_html(self, email_sender):
        """测试创建HTML邮件"""
        subject = 'HTML测试'
        body = '<h1>HTML正文</h1>'
        content_type = 'html'

        msg = email_sender._create_message(subject, body, content_type)

        assert msg.get_content_type() == 'text/html'
        assert '<h1>HTML正文</h1>' in msg.get_payload()

    def test_create_message_with_attachments(self, email_sender, sample_attachments):
        """测试创建带附件的邮件"""
        subject = '带附件测试'
        body = '测试正文'

        msg = email_sender._create_message(
            subject,
            body,
            'plain',
            attachments=sample_attachments
        )

        # 应该是multipart消息
        assert msg.is_multipart()

        # 计算部分数量（1个正文 + N个附件）
        parts = list(msg.walk())
        assert len(parts) == 3  # multipart容器 + 正文 + 2个附件

        # 验证附件
        attachment_filenames = []
        for part in parts:
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    attachment_filenames.append(filename)

        assert len(attachment_filenames) == 2
        assert 'test_0.txt' in attachment_filenames
        assert 'test_1.txt' in attachment_filenames

    def test_add_attachments(self, email_sender, sample_attachments):
        """测试添加附件"""
        # 创建基本消息
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart()
        msg.attach(MIMEText('测试正文', 'plain'))

        # 添加附件
        email_sender._add_attachments(msg, sample_attachments)

        # 计算附件数量
        attachment_count = 0
        for part in msg.walk():
            if part.get_content_disposition() == 'attachment':
                attachment_count += 1

        assert attachment_count == 2

    def test_send_email_success(self, email_sender, mock_smtp_server):
        """测试成功发送邮件"""
        subject = '测试邮件'
        body = '测试正文'

        # 模拟成功发送
        success = email_sender.send_email(subject, body, 'plain')

        # 验证发送成功
        assert success is True

        # 验证SMTP调用
        mock_smtp_server.assert_called_once()

        # 验证服务器连接
        mock_smtp_server.return_value.starttls.assert_called_once()
        mock_smtp_server.return_value.login.assert_called_once_with(
            'test@test.com', 'test_password'
        )
        mock_smtp_server.return_value.send_message.assert_called_once()
        mock_smtp_server.return_value.quit.assert_called_once()

    def test_send_email_with_ssl(self, email_config):
        """测试使用SSL发送邮件"""
        email_config.use_ssl = True
        email_config.use_tls = False

        sender = EmailSender(email_config)

        with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
            mock_server = Mock()
            mock_smtp_ssl.return_value = mock_server

            success = sender.send_email('测试', '正文')

            # 应该使用SMTP_SSL
            mock_smtp_ssl.assert_called_once_with('smtp.test.com', 587)

            # 不应该调用starttls
            mock_server.starttls.assert_not_called()

    def test_send_email_without_tls(self, email_config):
        """测试不使用TLS发送邮件"""
        email_config.use_tls = False

        sender = EmailSender(email_config)

        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server

            success = sender.send_email('测试', '正文')

            # 不应该调用starttls
            mock_server.starttls.assert_not_called()

    def test_send_email_failure(self, email_sender):
        """测试发送邮件失败"""
        subject = '测试邮件'
        body = '测试正文'

        # 模拟SMTP异常
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception('SMTP连接失败')

            success = email_sender.send_email(subject, body, 'plain')

            # 应该返回False
            assert success is False

    def test_send_email_auth_failure(self, email_sender):
        """测试认证失败"""
        subject = '测试邮件'
        body = '测试正文'

        # 模拟认证异常
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server
            mock_server.login.side_effect = Exception('认证失败')

            success = email_sender.send_email(subject, body, 'plain')

            assert success is False
            mock_server.quit.assert_called_once()  # 应该仍然尝试退出

    def test_send_daily_report(self, email_sender, sample_traffic_records, sample_attachments, mock_smtp_server):
        """测试发送每日报告"""
        from datetime import date

        report_date = date(2024, 1, 1)

        success = email_sender.send_daily_report(
            report_date,
            sample_traffic_records,
            attachments=sample_attachments
        )

        # 应该成功发送
        assert success is True

        # 验证邮件发送
        mock_smtp_server.return_value.send_message.assert_called_once()

        # 获取发送的消息
        call_args = mock_smtp_server.return_value.send_message.call_args
        sent_msg = call_args[0][0]  # 第一个位置参数

        # 验证邮件主题
        assert '2024-01-01' in sent_msg['Subject']
        assert '网络流量监控报告' in sent_msg['Subject']

        # 验证收件人
        assert 'recipient1@test.com' in sent_msg['To']
        assert 'recipient2@test.com' in sent_msg['To']

        # 验证抄送
        assert 'cc@test.com' in sent_msg['Cc']

    def test_generate_report_html(self, email_sender, sample_traffic_records):
        """测试生成报告HTML"""
        from datetime import date

        report_date = date(2024, 1, 1)

        html_content = email_sender._generate_report_html(report_date, sample_traffic_records)

        # 应该包含基本元素
        assert '<html' in html_content
        assert '<body' in html_content
        assert '2024-01-01' in html_content

        # 应该包含进程信息
        assert 'firefox' in html_content.lower()
        assert 'chrome' in html_content.lower()

        # 应该包含流量信息
        assert 'mb' in html_content.lower()
        assert '流量' in html_content

        # 应该包含表格
        assert '<table' in html_content
        assert '<tr>' in html_content
        assert '<td>' in html_content

    def test_calculate_report_stats(self, email_sender, sample_traffic_records):
        """测试计算报告统计"""
        stats = email_sender._calculate_report_stats(sample_traffic_records)

        # 验证统计字典结构
        assert isinstance(stats, dict)

        # 验证关键统计
        assert 'total_records' in stats
        assert stats['total_records'] == 3

        assert 'total_upload_mb' in stats
        assert 'total_download_mb' in stats
        assert 'unique_processes' in stats
        assert 'unique_remotes' in stats

        # 验证流量转换（字节到MB）
        total_upload_bytes = 100 + 50 + 200  # 350
        expected_upload_mb = total_upload_bytes / (1024 * 1024)
        assert abs(stats['total_upload_mb'] - expected_upload_mb) < 0.001

    def test_get_top_processes(self, email_sender, sample_traffic_records):
        """测试获取顶级进程"""
        top_processes = email_sender._get_top_processes(sample_traffic_records, top_n=2)

        # 应该返回2个进程
        assert len(top_processes) == 2

        # 应该按总流量排序
        assert top_processes[0]['process_name'] == 'chrome'  # 总流量380
        assert top_processes[1]['process_name'] == 'firefox'  # 总流量270

        # 验证进程统计
        for process in top_processes:
            assert 'process_name' in process
            assert 'upload_mb' in process
            assert 'download_mb' in process
            assert 'total_mb' in process
            assert 'connections' in process

    def test_get_top_remotes(self, email_sender, sample_traffic_records):
        """测试获取顶级远程地址"""
        top_remotes = email_sender._get_top_remotes(sample_traffic_records, top_n=2)

        # 应该返回2个远程地址
        assert len(top_remotes) <= 2

        # 验证远程地址统计
        for remote in top_remotes:
            assert 'remote_address' in remote
            assert 'upload_mb' in remote
            assert 'download_mb' in remote
            assert 'access_count' in remote
            assert 'common_protocol' in remote
```

### `tests/unit/test_archive_manager.py`

```python
import pytest
import zipfile
import tarfile
import json
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, timedelta

from src.archive_manager import ArchiveManager, ArchiveInfo


class TestArchiveInfo:
    """测试存档信息类"""

    def test_initialization(self, temp_dir):
        """测试初始化"""
        archive_path = temp_dir / 'test.zip'

        info = ArchiveInfo(
            path=archive_path,
            format='zip',
            size=1024,
            created=datetime.now(),
            contents=['file1.txt', 'file2.txt'],
            metadata={'files_count': 2, 'compression_ratio': 50.5}
        )

        assert info.path == archive_path
        assert info.format == 'zip'
        assert info.size == 1024
        assert len(info.contents) == 2
        assert info.metadata['files_count'] == 2
        assert info.metadata['compression_ratio'] == 50.5


class TestArchiveManager:
    """测试存档管理器"""

    @pytest.fixture
    def archive_manager(self, temp_dir):
        """创建存档管理器实例"""
        archive_dir = temp_dir / 'archive'
        return ArchiveManager(archive_dir, keep_original=False)

    @pytest.fixture
    def sample_files(self, temp_dir):
        """创建示例文件"""
        files = []
        test_dir = temp_dir / 'test_files'
        test_dir.mkdir()

        for i in range(3):
            file_path = test_dir / f'test_{i}.txt'
            file_path.write_text(f'测试内容 {i}' * 100)  # 创建足够大的文件
            files.append(file_path)

        return files

    def test_initialization(self, temp_dir):
        """测试初始化"""
        archive_dir = temp_dir / 'archive'
        manager = ArchiveManager(archive_dir, keep_original=True)

        assert manager.archive_dir == archive_dir
        assert manager.keep_original is True
        assert archive_dir.exists()  # 目录应该已创建

    def test_archive_logs_zip(self, archive_manager, sample_files):
        """测试ZIP格式存档日志"""
        from datetime import date

        archive_date = date(2024, 1, 1)
        archive_path = archive_manager.archive_logs(archive_date, sample_files, format='zip')

        # 验证存档已创建
        assert archive_path is not None
        assert archive_path.exists()
        assert archive_path.suffix == '.zip'

        # 验证存档大小
        assert archive_path.stat().st_size > 0

        # 验证元数据文件
        metadata_file = archive_manager.archive_dir / 'metadata_20240101.json'
        assert metadata_file.exists()

        # 验证元数据内容
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        assert metadata['archive_format'] == 'zip'
        assert metadata['original_files'] is not None
        assert len(metadata['original_files']) == 3

        # 验证原始文件已被删除
        for file_path in sample_files:
            assert not file_path.exists()  # keep_original=False

    def test_archive_logs_tar_gz(self, archive_manager, sample_files):
        """测试tar.gz格式存档日志"""
        from datetime import date

        archive_date = date(2024, 1, 1)
        archive_path = archive_manager.archive_logs(archive_date, sample_files, format='tar.gz')

        # 验证存档已创建
        assert archive_path is not None
        assert archive_path.exists()
        assert archive_path.suffix == '.gz'

        # 验证存档可以打开
        with tarfile.open(archive_path, 'r:gz') as tar:
            members = tar.getmembers()
            assert len(members) == 3

    def test_archive_logs_keep_original(self, temp_dir, sample_files):
        """测试保留原始文件的存档"""
        from datetime import date

        manager = ArchiveManager(temp_dir / 'archive', keep_original=True)
        archive_date = date(2024, 1, 1)

        archive_path = manager.archive_logs(archive_date, sample_files, format='zip')

        # 验证存档已创建
        assert archive_path.exists()

        # 验证原始文件仍然存在
        for file_path in sample_files:
            assert file_path.exists()

    def test_archive_logs_empty(self, archive_manager):
        """测试空文件列表存档"""
        from datetime import date

        archive_date = date(2024, 1, 1)
        archive_path = archive_manager.archive_logs(archive_date, [], format='zip')

        # 应该返回None
        assert archive_path is None

    def test_archive_logs_invalid_format(self, archive_manager, sample_files):
        """测试无效格式存档"""
        from datetime import date

        archive_date = date(2024, 1, 1)

        with pytest.raises(ValueError):
            archive_manager.archive_logs(archive_date, sample_files, format='invalid')

    def test_create_zip_archive(self, archive_manager, sample_files, temp_dir):
        """测试创建ZIP存档"""
        archive_path = temp_dir / 'test.zip'

        archive_manager._create_zip_archive(archive_path, sample_files)

        # 验证ZIP文件
        assert archive_path.exists()

        # 验证ZIP内容
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            # 应该包含所有文件
            assert len(zipf.namelist()) == 3

            # 验证文件名
            for file_path in sample_files:
                assert file_path.name in zipf.namelist()

            # 验证文件内容
            for file_path in sample_files:
                with zipf.open(file_path.name) as zipped_file:
                    content = zipped_file.read().decode('utf-8')
                    assert f'测试内容 {file_path.stem[-1]}' in content

    def test_create_tar_gz_archive(self, archive_manager, sample_files, temp_dir):
        """测试创建tar.gz存档"""
        archive_path = temp_dir / 'test.tar.gz'

        archive_manager._create_tar_gz_archive(archive_path, sample_files)

        # 验证tar.gz文件
        assert archive_path.exists()

        # 验证tar.gz内容
        with tarfile.open(archive_path, 'r:gz') as tar:
            # 应该包含所有文件
            members = tar.getmembers()
            assert len(members) == 3

            # 验证文件名
            member_names = [member.name for member in members]
            for file_path in sample_files:
                assert file_path.name in member_names

    def test_create_archive_metadata(self, archive_manager, sample_files, temp_dir):
        """测试创建存档元数据"""
        archive_path = temp_dir / 'test.zip'
        archive_path.touch()  # 创建空文件

        metadata = archive_manager._create_archive_metadata(archive_path, sample_files)

        # 验证元数据结构
        assert 'archive_path' in metadata
        assert 'archive_size' in metadata
        assert 'archive_format' in metadata
        assert 'creation_time' in metadata
        assert 'original_files' in metadata
        assert 'total_original_size' in metadata
        assert 'compression_ratio' in metadata

        # 验证原始文件信息
        assert len(metadata['original_files']) == 3

        for file_info in metadata['original_files']:
            assert 'path' in file_info
            assert 'name' in file_info
            assert 'size' in file_info
            assert 'exists' in file_info

        # 验证总大小计算
        total_size = sum(file_path.stat().st_size for file_path in sample_files)
        assert metadata['total_original_size'] == total_size

        # 验证压缩比计算（空存档）
        assert metadata['compression_ratio'] == 100.0  # 0字节存档

    def test_calculate_compression_ratio(self, archive_manager, temp_dir):
        """测试计算压缩比"""
        # 创建原始文件
        original_file = temp_dir / 'original.txt'
        original_content = '测试内容' * 1000
        original_file.write_text(original_content)
        original_size = original_file.stat().st_size

        # 创建存档文件（模拟压缩）
        archive_file = temp_dir / 'archive.zip'
        archive_content = '压缩内容'  # 比原始文件小
        archive_file.write_text(archive_content)
        archive_size = archive_file.stat().st_size

        ratio = archive_manager._calculate_compression_ratio(
            archive_file, [original_file]
        )

        # 验证压缩比计算
        expected_ratio = (1 - archive_size / original_size) * 100
        assert abs(ratio - expected_ratio) < 0.01

    def test_calculate_compression_ratio_zero_original(self, archive_manager, temp_dir):
        """测试原始大小为0的压缩比计算"""
        # 创建空原始文件
        empty_file = temp_dir / 'empty.txt'
        empty_file.touch()

        # 创建存档文件
        archive_file = temp_dir / 'archive.zip'
        archive_file.write_text('内容')

        ratio = archive_manager._calculate_compression_ratio(
            archive_file, [empty_file]
        )

        # 应该返回0
        assert ratio == 0.0

    def test_cleanup_original_files(self, archive_manager, sample_files):
        """测试清理原始文件"""
        # 确保文件存在
        for file_path in sample_files:
            assert file_path.exists()

        # 清理文件
        archive_manager._cleanup_original_files(sample_files)

        # 验证文件已被删除
        for file_path in sample_files:
            assert not file_path.exists()

    def test_cleanup_original_files_missing(self, archive_manager, temp_dir):
        """测试清理不存在的原始文件"""
        missing_file = temp_dir / 'missing.txt'

        # 应该不抛出异常
        archive_manager._cleanup_original_files([missing_file])

    def test_cleanup_old_archives(self, archive_manager):
        """测试清理旧存档"""
        from datetime import datetime, timedelta

        archive_dir = archive_manager.archive_dir

        # 创建不同时间的存档文件
        old_time = datetime.now() - timedelta(days=35)  # 35天前
        recent_time = datetime.now() - timedelta(days=5)  # 5天前

        # 旧存档
        old_archive = archive_dir / 'old_archive.zip'
        old_archive.touch()
        os.utime(old_archive, (old_time.timestamp(), old_time.timestamp()))

        # 新存档
        new_archive = archive_dir / 'new_archive.zip'
        new_archive.touch()
        os.utime(new_archive, (recent_time.timestamp(), recent_time.timestamp()))

        # 清理旧存档（保留30天）
        deleted = archive_manager.cleanup_old_archives(retention_days=30)

        # 验证清理结果
        assert len(deleted) == 1
        assert deleted[0] == old_archive

        # 验证文件状态
        assert not old_archive.exists()
        assert new_archive.exists()

    def test_extract_archive_zip(self, archive_manager, temp_dir, sample_files):
        """测试解压ZIP存档"""
        # 先创建ZIP存档
        archive_path = temp_dir / 'test.zip'
        with zipfile.ZipFile(archive_path, 'w') as zipf:
            for file_path in sample_files:
                zipf.write(file_path, file_path.name)

        # 解压存档
        extracted_files = archive_manager.extract_archive(
            archive_path,
            temp_dir / 'extracted'
        )

        # 验证解压结果
        assert len(extracted_files) == 3

        # 验证提取的文件
        for extracted_file in extracted_files:
            assert extracted_file.exists()
            assert extracted_file.stat().st_size > 0

    def test_extract_archive_tar_gz(self, archive_manager, temp_dir, sample_files):
        """测试解压tar.gz存档"""
        # 先创建tar.gz存档
        archive_path = temp_dir / 'test.tar.gz'
        with tarfile.open(archive_path, 'w:gz') as tar:
            for file_path in sample_files:
                tar.add(file_path, arcname=file_path.name)

        # 解压存档
        extracted_files = archive_manager.extract_archive(
            archive_path,
            temp_dir / 'extracted'
        )

        # 验证解压结果
        assert len(extracted_files) == 3

    def test_extract_archive_invalid(self, archive_manager, temp_dir):
        """测试解压无效存档"""
        # 创建无效存档文件
        invalid_archive = temp_dir / 'invalid.txt'
        invalid_archive.write_text('不是存档文件')

        extracted_files = archive_manager.extract_archive(invalid_archive)

        # 应该返回空列表
        assert extracted_files == []

    def test_list_archives(self, archive_manager):
        """测试列出存档"""
        archive_dir = archive_manager.archive_dir

        # 创建不同类型的存档
        archives = [
            archive_dir / 'test1.zip',
            archive_dir / 'test2.tar.gz',
            archive_dir / 'test3.tgz',
            archive_dir / 'test4.txt'  # 不是存档文件
        ]

        for archive_path in archives:
            archive_path.touch()

        # 列出存档
        archive_list = archive_manager.list_archives()

        # 应该只返回3个存档文件（排除.txt）
        assert len(archive_list) == 3

        # 验证存档信息
        for archive_info in archive_list:
            assert isinstance(archive_info, ArchiveInfo)
            assert archive_info.path.exists()
            assert archive_info.format in ['zip', 'tar.gz']
            assert archive_info.size == 0  # 空文件

    def test_get_archive_info_zip(self, archive_manager, temp_dir, sample_files):
        """测试获取ZIP存档信息"""
        # 创建ZIP存档
        archive_path = temp_dir / 'test.zip'
        with zipfile.ZipFile(archive_path, 'w') as zipf:
            for file_path in sample_files:
                zipf.write(file_path, file_path.name)

        info = archive_manager._get_archive_info(archive_path)

        # 验证存档信息
        assert info.path == archive_path
        assert info.format == 'zip'
        assert info.size == archive_path.stat().st_size
        assert len(info.contents) == 3
        assert info.metadata['files_count'] == 3

    def test_get_archive_info_tar_gz(self, archive_manager, temp_dir, sample_files):
        """测试获取tar.gz存档信息"""
        # 创建tar.gz存档
        archive_path = temp_dir / 'test.tar.gz'
        with tarfile.open(archive_path, 'w:gz') as tar:
            for file_path in sample_files:
                tar.add(file_path, arcname=file_path.name)

        info = archive_manager._get_archive_info(archive_path)

        # 验证存档信息
        assert info.path == archive_path
        assert info.format == 'tar.gz'
        assert info.size == archive_path.stat().st_size
        assert len(info.contents) == 3
```

### `tests/unit/test_parallel_processor.py`

```python
import pytest
import time
from unittest.mock import Mock, patch
from datetime import date
from concurrent.futures import Future

from src.parallel_processor import ParallelProcessor, ProcessingPipeline


class TestParallelProcessor:
    """测试并行处理器"""

    @pytest.fixture
    def parallel_processor(self):
        """创建并行处理器实例"""
        return ParallelProcessor(max_workers=2)

    @pytest.fixture
    def sample_date_files(self):
        """创建示例日期文件字典"""
        from src.file_scanner import LogFileInfo
        from pathlib import Path
        from datetime import datetime

        date_files = {}

        # 创建两个日期的数据
        for day in range(1, 3):
            date_key = date(2024, 1, day)
            files = []

            for hour in range(2):  # 每个日期两个文件
                file_path = Path(f'test_{date_key}_{hour}.log')
                file_info = LogFileInfo(
                    path=file_path,
                    date=date_key,
                    base_time=datetime(2024, 1, day, 10 + hour, 0, 0),
                    size=1024,
                    md5='test',
                    modified_time=datetime.now()
                )
                files.append(file_info)

            date_files[date_key] = files

        return date_files

    def test_initialization(self):
        """测试初始化"""
        processor = ParallelProcessor(max_workers=4)

        assert processor.max_workers == 4
        assert processor._results == {}
        assert processor._errors == {}

    def test_process_daily_logs_success(self, parallel_processor, sample_date_files):
        """测试成功处理每日日志"""
        # 模拟处理函数
        def mock_process_func(date_key, files):
            return {
                'date': date_key,
                'files_count': len(files),
                'processed': True
            }

        # 处理日志
        results = parallel_processor.process_daily_logs(
            sample_date_files,
            mock_process_func
        )

        # 验证结果
        assert len(results) == 2  # 两个日期

        for date_key, result in results.items():
            assert result['date'] == date_key
            assert result['files_count'] == 2
            assert result['processed'] is True

        # 验证内部状态
        assert len(parallel_processor.get_results()) == 2
        assert len(parallel_processor.get_errors()) == 0

    def test_process_daily_logs_with_errors(self, parallel_processor, sample_date_files):
        """测试处理每日日志时出现错误"""
        # 模拟处理函数，第二个日期抛出异常
        def mock_process_func(date_key, files):
            if date_key == date(2024, 1, 2):
                raise Exception('处理失败')

            return {
                'date': date_key,
                'files_count': len(files),
                'processed': True
            }

        # 处理日志
        results = parallel_processor.process_daily_logs(
            sample_date_files,
            mock_process_func
        )

        # 验证结果
        assert len(results) == 1  # 只有一个成功
        assert date(2024, 1, 1) in results

        # 验证错误
        errors = parallel_processor.get_errors()
        assert len(errors) == 1
        assert date(2024, 1, 2) in errors
        assert '处理失败' in errors[date(2024, 1, 2)]

    def test_process_in_batches(self, parallel_processor):
        """测试批量处理"""
        items = list(range(10))

        def process_item(item):
            return item * 2

        results = parallel_processor.process_in_batches(
            items, process_item, batch_size=3
        )

        # 验证结果
        assert len(results) == 10

        for i, result in enumerate(results):
            assert result == i * 2

    def test_process_in_batches_with_errors(self, parallel_processor):
        """测试批量处理时出现错误"""
        items = list(range(5))

        def process_item(item):
            if item == 2:
                raise Exception('处理失败')
            return item * 2

        results = parallel_processor.process_in_batches(
            items, process_item, batch_size=2
        )

        # 验证结果
        assert len(results) == 5

        # 正常项
        assert results[0] == 0
        assert results[1] == 2
        assert results[3] == 6
        assert results[4] == 8

        # 错误项应该为None
        assert results[2] is None

    def test_process_single_date(self, parallel_processor):
        """测试处理单个日期"""
        from datetime import date
        from src.file_scanner import LogFileInfo
        from pathlib import Path

        # 创建模拟文件
        date_key = date(2024, 1, 1)
        files = [
            Mock(spec=LogFileInfo, path=Path('test1.log')),
            Mock(spec=LogFileInfo, path=Path('test2.log'))
        ]

        def mock_process_func(date_key, files):
            return f'处理了{len(files)}个文件'

        result = parallel_processor._process_single_date(
            date_key, files, mock_process_func
        )

        assert result == '处理了2个文件'

    def test_process_single_date_exception(self, parallel_processor):
        """测试处理单个日期时抛出异常"""
        from datetime import date

        date_key = date(2024, 1, 1)
        files = []

        def mock_process_func(date_key, files):
            raise Exception('测试异常')

        with pytest.raises(Exception, match='测试异常'):
            parallel_processor._process_single_date(
                date_key, files, mock_process_func
            )

    def test_process_batch(self, parallel_processor):
        """测试处理批次"""
        batch = [1, 2, 3, 4, 5]

        def process_item(item):
            return item * item

        results = parallel_processor._process_batch(batch, process_item)

        # 验证结果
        assert len(results) == 5
        assert results == [1, 4, 9, 16, 25]

    def test_get_results_and_errors(self, parallel_processor):
        """测试获取结果和错误"""
        # 设置一些结果和错误
        parallel_processor._results = {
            date(2024, 1, 1): '结果1',
            date(2024, 1, 2): '结果2'
        }

        parallel_processor._errors = {
            date(2024, 1, 3): '错误1'
        }

        # 验证获取结果
        results = parallel_processor.get_results()
        assert len(results) == 2
        assert results[date(2024, 1, 1)] == '结果1'

        # 验证获取错误
        errors = parallel_processor.get_errors()
        assert len(errors) == 1
        assert errors[date(2024, 1, 3)] == '错误1'


class TestProcessingPipeline:
    """测试处理管道"""

    @pytest.fixture
    def processing_pipeline(self):
        """创建处理管道实例"""
        return ProcessingPipeline()

    def test_initialization(self):
        """测试初始化"""
        pipeline = ProcessingPipeline()

        assert pipeline.stages == []
        assert pipeline.context == {}

    def test_add_stage(self):
        """测试添加阶段"""
        pipeline = ProcessingPipeline()

        def stage1(context):
            return '结果1'

        def stage2(context):
            return '结果2'

        pipeline.add_stage('stage1', stage1)
        pipeline.add_stage('stage2', stage2, depends_on=['stage1'])

        # 验证阶段
        assert len(pipeline.stages) == 2

        stage1_info = pipeline.stages[0]
        assert stage1_info['name'] == 'stage1'
        assert stage1_info['func'] == stage1
        assert stage1_info['depends_on'] == []

        stage2_info = pipeline.stages[1]
        assert stage2_info['name'] == 'stage2'
        assert stage2_info['depends_on'] == ['stage1']

    def test_run_linear_pipeline(self):
        """测试运行线性管道"""
        pipeline = ProcessingPipeline()

        results = []

        def stage1(context):
            results.append('stage1')
            return '结果1'

        def stage2(context):
            results.append('stage2')
            return '结果2'

        def stage3(context):
            results.append('stage3')
            return '结果3'

        pipeline.add_stage('stage1', stage1)
        pipeline.add_stage('stage2', stage2)
        pipeline.add_stage('stage3', stage3)

        context = pipeline.run()

        # 验证执行顺序
        assert results == ['stage1', 'stage2', 'stage3']

        # 验证上下文
        assert context['stage1'] == '结果1'
        assert context['stage2'] == '结果2'
        assert context['stage3'] == '结果3'

    def test_run_dependent_pipeline(self):
        """测试运行依赖管道"""
        pipeline = ProcessingPipeline()

        execution_order = []

        def stage_a(context):
            execution_order.append('A')
            return 'A'

        def stage_b(context):
            execution_order.append('B')
            return 'B'

        def stage_c(context):
            execution_order.append('C')
            # 可以访问之前的阶段结果
            return context['stage_a'] + context['stage_b'] + 'C'

        # 添加有依赖关系的阶段
        pipeline.add_stage('stage_a', stage_a)
        pipeline.add_stage('stage_b', stage_b)
        pipeline.add_stage('stage_c', stage_c, depends_on=['stage_a', 'stage_b'])

        context = pipeline.run()

        # 验证C在A和B之后执行
        assert 'C' in execution_order
        c_index = execution_order.index('C')
        assert 'A' in execution_order[:c_index]
        assert 'B' in execution_order[:c_index]

        # 验证C的结果使用了A和B的结果
        assert context['stage_c'] == 'ABC'

    def test_run_with_initial_context(self):
        """测试运行带有初始上下文的管道"""
        pipeline = ProcessingPipeline()

        def stage1(context):
            return context['input'] * 2

        def stage2(context):
            return context['stage1'] + 1

        pipeline.add_stage('stage1', stage1)
        pipeline.add_stage('stage2', stage2, depends_on=['stage1'])

        initial_context = {'input': 5}
        context = pipeline.run(initial_context)

        # 验证结果
        assert context['input'] == 5  # 原始输入
        assert context['stage1'] == 10  # 5 * 2
        assert context['stage2'] == 11  # 10 + 1

    def test_run_with_exception(self):
        """测试运行管道时出现异常"""
        pipeline = ProcessingPipeline()

        def stage1(context):
            return '正常'

        def stage2(context):
            raise Exception('阶段2失败')

        def stage3(context):
            return '不应该执行'

        pipeline.add_stage('stage1', stage1)
        pipeline.add_stage('stage2', stage2)
        pipeline.add_stage('stage3', stage3)

        # 应该抛出异常
        with pytest.raises(Exception, match='阶段2失败'):
            pipeline.run()

        # 验证stage3没有执行
        assert 'stage3' not in pipeline.context

    def test_run_with_circular_dependency(self):
        """测试运行带有循环依赖的管道"""
        pipeline = ProcessingPipeline()

        def stage1(context):
            return '结果1'

        def stage2(context):
            return '结果2'

        # 创建循环依赖
        pipeline.add_stage('stage1', stage1, depends_on=['stage2'])
        pipeline.add_stage('stage2', stage2, depends_on=['stage1'])

        # 应该无法运行（无限循环）
        with pytest.raises(Exception):
            pipeline.run()

    def test_chaining(self):
        """测试方法链"""
        pipeline = ProcessingPipeline()

        result = (pipeline
                 .add_stage('stage1', lambda ctx: 1)
                 .add_stage('stage2', lambda ctx: 2)
                 .add_stage('stage3', lambda ctx: 3)
                 .run())

        # 验证链式调用和结果
        assert result['stage1'] == 1
        assert result['stage2'] == 2
        assert result['stage3'] == 3

    def test_complex_pipeline(self):
        """测试复杂管道"""
        pipeline = ProcessingPipeline()

        # 定义阶段
        def load_data(context):
            return [1, 2, 3, 4, 5]

        def filter_even(context):
            data = context['load_data']
            return [x for x in data if x % 2 == 0]

        def filter_odd(context):
            data = context['load_data']
            return [x for x in data if x % 2 == 1]

        def sum_even(context):
            even = context['filter_even']
            return sum(even)

        def sum_odd(context):
            odd = context['filter_odd']
            return sum(odd)

        def total_sum(context):
            return context['sum_even'] + context['sum_odd']

        # 添加阶段
        pipeline.add_stage('load_data', load_data)
        pipeline.add_stage('filter_even', filter_even, depends_on=['load_data'])
        pipeline.add_stage('filter_odd', filter_odd, depends_on=['load_data'])
        pipeline.add_stage('sum_even', sum_even, depends_on=['filter_even'])
        pipeline.add_stage('sum_odd', sum_odd, depends_on=['filter_odd'])
        pipeline.add_stage('total_sum', total_sum, depends_on=['sum_even', 'sum_odd'])

        # 运行管道
        context = pipeline.run()

        # 验证结果
        assert context['load_data'] == [1, 2, 3, 4, 5]
        assert context['filter_even'] == [2, 4]
        assert context['filter_odd'] == [1, 3, 5]
        assert context['sum_even'] == 6
        assert context['sum_odd'] == 9
        assert context['total_sum'] == 15
```

### `tests/unit/utils/test_validators.py`

```python
import pytest
import tempfile
import json
import yaml
from pathlib import Path

from src.utils.validators import (
    Validator,
    ConfigValidator,
    TrafficValidator,
    ValidationError,
    validate_config_file
)


class TestValidator:
    """测试验证器基类"""

    def test_validate_email(self):
        """测试验证邮箱地址"""
        # 有效邮箱
        assert Validator.validate_email('test@example.com') is True
        assert Validator.validate_email('user.name@domain.co.uk') is True
        assert Validator.validate_email('user+tag@example.com') is True

        # 无效邮箱
        assert Validator.validate_email('invalid') is False
        assert Validator.validate_email('@example.com') is False
        assert Validator.validate_email('test@') is False
        assert Validator.validate_email('test@.com') is False
        assert Validator.validate_email('') is False

    def test_validate_ip(self):
        """测试验证IP地址"""
        # 有效IP
        assert Validator.validate_ip('192.168.1.1') is True
        assert Validator.validate_ip('8.8.8.8') is True
        assert Validator.validate_ip('255.255.255.255') is True
        assert Validator.validate_ip('0.0.0.0') is True
        assert Validator.validate_ip('2001:0db8:85a3:0000:0000:8a2e:0370:7334') is True

        # 无效IP
        assert Validator.validate_ip('256.256.256.256') is False
        assert Validator.validate_ip('192.168.1') is False
        assert Validator.validate_ip('example.com') is False
        assert Validator.validate_ip('') is False

    def test_validate_domain(self):
        """测试验证域名"""
        # 有效域名
        assert Validator.validate_domain('example.com') is True
        assert Validator.validate_domain('sub.domain.co.uk') is True
        assert Validator.validate_domain('a-b.com') is True

        # 无效域名
        assert Validator.validate_domain('') is False
        assert Validator.validate_domain('.com') is False
        assert Validator.validate_domain('example.') is False
        assert Validator.validate_domain('-example.com') is False
        assert Validator.validate_domain('example-.com') is False
        assert Validator.validate_domain('192.168.1.1') is False

    def test_validate_port(self):
        """测试验证端口号"""
        # 有效端口
        assert Validator.validate_port(80) is True
        assert Validator.validate_port(443) is True
        assert Validator.validate_port(1) is True
        assert Validator.validate_port(65535) is True
        assert Validator.validate_port('8080') is True

        # 无效端口
        assert Validator.validate_port(0) is False
        assert Validator.validate_port(65536) is False
        assert Validator.validate_port(-1) is False
        assert Validator.validate_port('invalid') is False
        assert Validator.validate_port('') is False

    def test_validate_file_exists(self, temp_dir):
        """测试验证文件是否存在"""
        # 创建测试文件
        existing_file = temp_dir / 'test.txt'
        existing_file.touch()

        # 有效文件
        assert Validator.validate_file_exists(existing_file) is True
        assert Validator.validate_file_exists(str(existing_file)) is True

        # 不存在的文件
        missing_file = temp_dir / 'missing.txt'
        assert Validator.validate_file_exists(missing_file) is False

        # 检查可读性
        existing_file.write_text('test content')
        assert Validator.validate_file_exists(existing_file, check_readable=True) is True

    def test_validate_directory_exists(self, temp_dir):
        """测试验证目录是否存在"""
        # 创建测试目录
        existing_dir = temp_dir / 'test_dir'
        existing_dir.mkdir()

        # 有效目录
        assert Validator.validate_directory_exists(existing_dir) is True
        assert Validator.validate_directory_exists(str(existing_dir)) is True

        # 不存在的目录
        missing_dir = temp_dir / 'missing_dir'
        assert Validator.validate_directory_exists(missing_dir) is False

        # 检查可写性
        assert Validator.validate_directory_exists(existing_dir, check_writable=True) is True

        # 文件不是目录
        test_file = temp_dir / 'test.txt'
        test_file.touch()
        assert Validator.validate_directory_exists(test_file) is False

    def test_validate_json(self):
        """测试验证JSON字符串"""
        # 有效JSON
        assert Validator.validate_json('{"key": "value"}') is True
        assert Validator.validate_json('[1, 2, 3]') is True
        assert Validator.validate_json('null') is True

        # 无效JSON
        assert Validator.validate_json('{key: value}') is False
        assert Validator.validate_json('') is False
        assert Validator.validate_json('invalid') is False

    def test_validate_yaml(self):
        """测试验证YAML字符串"""
        # 有效YAML
        assert Validator.validate_yaml('key: value') is True
        assert Validator.validate_yaml('- item1\n- item2') is True
        assert Validator.validate_yaml('') is True  # 空YAML有效

        # 无效YAML
        assert Validator.validate_yaml('key: : :') is False
        assert Validator.validate_yaml('\tinvalid') is False

    def test_validate_date_format(self):
        """测试验证日期格式"""
        # 有效日期
        assert Validator.validate_date_format('20240101', '%Y%m%d') is True
        assert Validator.validate_date_format('2024-01-01', '%Y-%m-%d') is True
        assert Validator.validate_date_format('01/01/2024', '%d/%m/%Y') is True

        # 无效日期
        assert Validator.validate_date_format('20241301', '%Y%m%d') is False  # 无效月份
        assert Validator.validate_date_format('20240132', '%Y%m%d') is False  # 无效日期
        assert Validator.validate_date_format('invalid', '%Y%m%d') is False

    def test_validate_time_format(self):
        """测试验证时间格式"""
        # 有效时间
        assert Validator.validate_time_format('1200', '%H%M') is True
        assert Validator.validate_time_format('23:59', '%H:%M') is True

        # 无效时间
        assert Validator.validate_time_format('2500', '%H%M') is False  # 无效小时
        assert Validator.validate_time_format('1260', '%H%M') is False  # 无效分钟
        assert Validator.validate_time_format('invalid', '%H%M') is False


class TestConfigValidator:
    """测试配置文件验证器"""

    def test_validate_email_config_valid(self):
        """测试验证有效的邮件配置"""
        config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'user@example.com',
            'password': 'password',
            'from_addr': 'sender@example.com',
            'to_addrs': ['recipient@example.com']
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该没有错误
        assert errors == []

    def test_validate_email_config_missing_fields(self):
        """测试验证缺少字段的邮件配置"""
        config = {
            'smtp_server': 'smtp.example.com',
            # 缺少其他必填字段
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该有多个错误
        assert len(errors) > 0
        assert any('缺少必填字段' in error for error in errors)

    def test_validate_email_config_invalid_server(self):
        """测试验证无效的SMTP服务器"""
        config = {
            'smtp_server': 'invalid:server',
            'smtp_port': 587,
            'username': 'user@example.com',
            'password': 'password',
            'from_addr': 'sender@example.com',
            'to_addrs': ['recipient@example.com']
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该有服务器格式错误
        assert any('SMTP服务器格式无效' in error for error in errors)

    def test_validate_email_config_invalid_port(self):
        """测试验证无效的端口"""
        config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 70000,  # 无效端口
            'username': 'user@example.com',
            'password': 'password',
            'from_addr': 'sender@example.com',
            'to_addrs': ['recipient@example.com']
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该有端口错误
        assert any('SMTP端口无效' in error for error in errors)

    def test_validate_email_config_invalid_emails(self):
        """测试验证无效的邮箱地址"""
        config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'invalid-email',
            'password': 'password',
            'from_addr': 'invalid-email',
            'to_addrs': ['recipient@example.com', 'invalid']
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该有多个邮箱格式错误
        assert len(errors) >= 2
        assert any('邮箱地址格式无效' in error for error in errors)

    def test_validate_email_config_invalid_to_addrs_type(self):
        """测试验证无效的收件人列表类型"""
        config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'user@example.com',
            'password': 'password',
            'from_addr': 'sender@example.com',
            'to_addrs': 'not-a-list'  # 不是列表
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该有类型错误
        assert any('必须是数组' in error for error in errors)

    def test_validate_path_config_valid(self, temp_dir):
        """测试验证有效的路径配置"""
        config = {
            'log_dir': str(temp_dir / 'logs'),
            'report_dir': str(temp_dir / 'reports'),
            'archive_dir': str(temp_dir / 'archive')
        }

        errors = ConfigValidator.validate_path_config(config)

        # 应该没有错误
        assert errors == []

    def test_validate_path_config_missing_fields(self):
        """测试验证缺少字段的路径配置"""
        config = {
            'log_dir': './logs',
            # 缺少其他必填字段
        }

        errors = ConfigValidator.validate_path_config(config)

        # 应该有多个错误
        assert len(errors) > 0
        assert any('路径配置缺少' in error for error in errors)

    def test_validate_path_config_invalid_path(self, temp_dir):
        """测试验证无效的路径"""
        # 创建只读目录
        read_only_dir = temp_dir / 'readonly'
        read_only_dir.mkdir()
        read_only_dir.chmod(0o444)  # 只读

        config = {
            'log_dir': str(read_only_dir),
            'report_dir': str(temp_dir / 'reports'),
            'archive_dir': str(temp_dir / 'archive')
        }

        errors = ConfigValidator.validate_path_config(config)

        # 应该有路径不可写错误
        assert any('路径不可写' in error for error in errors)

        # 恢复权限
        read_only_dir.chmod(0o755)


class TestTrafficValidator:
    """测试流量数据验证器"""

    def test_validate_traffic_record_valid(self):
        """测试验证有效的流量记录"""
        record = {
            'timestamp': '2024-01-01T12:00:00',
            'pid': 12345,
            'process_name': 'firefox',
            'remote_address': '8.8.8.8',
            'upload_bps': 100,
            'download_bps': 200
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该没有错误
        assert errors == []

    def test_validate_traffic_record_missing_fields(self):
        """测试验证缺少字段的流量记录"""
        record = {
            'pid': 12345,
            # 缺少其他必填字段
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有多个错误
        assert len(errors) > 0
        assert any('缺少必填字段' in error for error in errors)

    def test_validate_traffic_record_invalid_pid(self):
        """测试验证无效的PID"""
        record = {
            'timestamp': '2024-01-01T12:00:00',
            'pid': -1,  # 无效PID
            'process_name': 'firefox',
            'remote_address': '8.8.8.8',
            'upload_bps': 100,
            'download_bps': 200
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有PID错误
        assert any('进程ID无效' in error for error in errors)

    def test_validate_traffic_record_invalid_traffic_values(self):
        """测试验证无效的流量值"""
        record = {
            'timestamp': '2024-01-01T12:00:00',
            'pid': 12345,
            'process_name': 'firefox',
            'remote_address': '8.8.8.8',
            'upload_bps': -100,  # 负数
            'download_bps': 'invalid'  # 非数字
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有两个错误
        assert len(errors) >= 2
        assert any('不能为负数' in error for error in errors)
        assert any('格式错误' in error for error in errors)

    def test_validate_traffic_record_huge_traffic_value(self):
        """测试验证过大的流量值"""
        record = {
            'timestamp': '2024-01-01T12:00:00',
            'pid': 12345,
            'process_name': 'firefox',
            'remote_address': '8.8.8.8',
            'upload_bps': 20 * 1024 * 1024 * 1024,  # 20GB/s，异常大
            'download_bps': 200
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有流量过大错误
        assert any('值异常大' in error for error in errors)

    def test_validate_traffic_record_invalid_remote_address(self):
        """测试验证无效的远程地址"""
        record = {
            'timestamp': '2024-01-01T12:00:00',
            'pid': 12345,
            'process_name': 'firefox',
            'remote_address': 'invalid-address',
            'upload_bps': 100,
            'download_bps': 200
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有地址错误
        assert any('远程地址格式无效' in error for error in errors)

    def test_validate_traffic_record_domain_address(self):
        """测试验证域名地址"""
        record = {
            'timestamp': '2024-01-01T12:00:00',
            'pid': 12345,
            'process_name': 'firefox',
            'remote_address': 'example.com',  # 域名
            'upload_bps': 100,
            'download_bps': 200
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该没有错误（域名是有效的）
        assert errors == []

    def test_validate_traffic_record_invalid_ports(self):
        """测试验证无效的端口"""
        record = {
            'timestamp': '2024-01-01T12:00:00',
            'pid': 12345,
            'process_name': 'firefox',
            'remote_address': '8.8.8.8',
            'remote_port': 70000,  # 无效端口
            'local_port': 0,  # 无效端口
            'upload_bps': 100,
            'download_bps': 200
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有两个端口错误
        port_errors = [e for e in errors if '端口无效' in e]
        assert len(port_errors) >= 2

    def test_validate_bandwhich_log_line(self):
        """测试验证bandwhich日志行"""
        # 有效行
        valid_lines = [
            'Refreshing:',
            '<NO TRAFFIC>',
            'process: <12345> "firefox" up/down Bps: 100/200 connections: 3',
            'connection: <12345> <eth0>:54321 => 8.8.8.8:443 (tcp) up/down Bps: 100/200 process: "firefox"',
            'remote_address: <12345> 8.8.8.8 up/down Bps: 100/200 connections: 1'
        ]

        for line in valid_lines:
            assert TrafficValidator.validate_bandwhich_log_line(line) is True

        # 无效行
        invalid_lines = [
            '',
            'invalid line',
            'process: invalid',
            'connection: invalid'
        ]

        for line in invalid_lines:
            assert TrafficValidator.validate_bandwhich_log_line(line) is False


class TestValidateConfigFile:
    """测试验证配置文件"""

    def test_validate_config_file_valid(self, temp_dir, sample_config):
        """测试验证有效的配置文件"""
        config_file = temp_dir / 'config.yaml'

        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(sample_config, f)

        # 应该成功加载
        config = validate_config_file(config_file)

        assert config == sample_config

    def test_validate_config_file_missing(self, temp_dir):
        """测试验证不存在的配置文件"""
        config_file = temp_dir / 'missing.yaml'

        with pytest.raises(ValidationError, match='配置文件不存在'):
            validate_config_file(config_file)

    def test_validate_config_file_invalid_yaml(self, temp_dir):
        """测试验证无效的YAML配置文件"""
        config_file = temp_dir / 'invalid.yaml'

        with open(config_file, 'w', encoding='utf-8') as f:
            f.write('invalid: yaml: : :')

        with pytest.raises(ValidationError, match='YAML格式错误'):
            validate_config_file(config_file)

    def test_validate_config_file_invalid_email_config(self, temp_dir):
        """测试验证邮件配置无效的配置文件"""
        config = {
            'paths': {
                'log_dir': './logs',
                'report_dir': './reports',
                'archive_dir': './archive',
                'temp_dir': './temp'
            },
            'email': {
                'smtp_server': 'invalid:server',
                'smtp_port': 70000,
                'username': 'invalid-email',
                'password': 'password',
                'from_addr': 'invalid-email',
                'to_addrs': ['invalid']
            }
        }

        config_file = temp_dir / 'config.yaml'

        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        with pytest.raises(ValidationError, match='配置验证失败'):
            validate_config_file(config_file)
```

### `tests/unit/utils/test_date_utils.py`

```python
import pytest
from datetime import datetime, date, timedelta

from src.utils.date_utils import DateUtils, DateRange


class TestDateUtils:
    """测试日期时间工具类"""

    def test_parse_date_valid(self):
        """测试解析有效的日期字符串"""
        # 各种格式
        test_cases = [
            ('2024-01-01', date(2024, 1, 1)),
            ('20240101', date(2024, 1, 1)),
            ('01/01/2024', date(2024, 1, 1)),
            ('2024-01-01 12:00:00', date(2024, 1, 1)),
            ('2024-01-01T12:00:00', date(2024, 1, 1))
        ]

        for date_str, expected in test_cases:
            result = DateUtils.parse_date(date_str)
            assert result == expected

    def test_parse_date_from_bandwhich_filename(self):
        """测试从bandwhich文件名解析日期"""
        filename = 'bandwhich_20240101_1200.log'
        result = DateUtils.parse_date(filename)

        assert result == date(2024, 1, 1)

    def test_parse_date_invalid(self):
        """测试解析无效的日期字符串"""
        invalid_cases = [
            '',
            'invalid',
            '2024-13-01',  # 无效月份
            '2024-01-32',  # 无效日期
            '20240101_invalid'
        ]

        for date_str in invalid_cases:
            result = DateUtils.parse_date(date_str)
            assert result is None

    def test_parse_datetime_valid(self):
        """测试解析有效的日期时间字符串"""
        test_cases = [
            ('2024-01-01 12:00:00', datetime(2024, 1, 1, 12, 0, 0)),
            ('20240101 120000', datetime(2024, 1, 1, 12, 0, 0)),
            ('2024-01-01T12:00:00', datetime(2024, 1, 1, 12, 0, 0)),
            ('2024-01-01T12:00:00Z', datetime(2024, 1, 1, 12, 0, 0)),
            ('2024-01-01T12:00:00.123456Z', datetime(2024, 1, 1, 12, 0, 0, 123456))
        ]

        for datetime_str, expected in test_cases:
            result = DateUtils.parse_datetime(datetime_str)
            assert result == expected

    def test_parse_datetime_iso_format(self):
        """测试解析ISO格式"""
        # ISO格式应该能正确解析
        iso_str = '2024-01-01T12:30:45.123456+08:00'
        result = DateUtils.parse_datetime(iso_str)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 45

    def test_parse_datetime_invalid(self):
        """测试解析无效的日期时间字符串"""
        invalid_cases = [
            '',
            'invalid',
            '2024-13-01 12:00:00',
            '2024-01-01 25:00:00'
        ]

        for datetime_str in invalid_cases:
            result = DateUtils.parse_datetime(datetime_str)
            assert result is None

    def test_get_date_range(self):
        """测试获取日期范围"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)

        # 默认步长
        date_range = DateUtils.get_date_range(start, end)

        assert len(date_range) == 5
        assert date_range[0] == start
        assert date_range[-1] == end

        # 指定步长
        date_range_step2 = DateUtils.get_date_range(start, end, step_days=2)

        assert len(date_range_step2) == 3
        assert date_range_step2 == [date(2024, 1, 1), date(2024, 1, 3), date(2024, 1, 5)]

        # 只指定开始日期
        today_range = DateUtils.get_date_range(start)
        assert len(today_range) >= 1
        assert today_range[0] == start

    def test_get_date_range_string_input(self):
        """测试字符串输入获取日期范围"""
        start = '2024-01-01'
        end = '2024-01-03'

        date_range = DateUtils.get_date_range(start, end)

        assert len(date_range) == 3
        assert date_range[0] == date(2024, 1, 1)
        assert date_range[1] == date(2024, 1, 2)
        assert date_range[2] == date(2024, 1, 3)

    def test_get_date_range_reversed(self):
        """测试开始日期晚于结束日期的日期范围"""
        start = date(2024, 1, 5)
        end = date(2024, 1, 1)

        date_range = DateUtils.get_date_range(start, end)

        # 应该自动交换开始和结束
        assert date_range[0] == date(2024, 1, 1)
        assert date_range[-1] == date(2024, 1, 5)

    def test_ensure_date(self):
        """测试确保返回date对象"""
        # date对象
        d = date(2024, 1, 1)
        assert DateUtils.ensure_date(d) == d

        # datetime对象
        dt = datetime(2024, 1, 1, 12, 0, 0)
        assert DateUtils.ensure_date(dt) == date(2024, 1, 1)

        # 字符串
        assert DateUtils.ensure_date('2024-01-01') == date(2024, 1, 1)

        # 无效类型
        with pytest.raises(TypeError):
            DateUtils.ensure_date(123)

    def test_ensure_datetime(self):
        """测试确保返回datetime对象"""
        # datetime对象
        dt = datetime(2024, 1, 1, 12, 0, 0)
        assert DateUtils.ensure_datetime(dt) == dt

        # date对象
        d = date(2024, 1, 1)
        result = DateUtils.ensure_datetime(d)
        assert result.date() == d
        assert result.time() == datetime.min.time()  # 00:00:00

        # 字符串
        assert DateUtils.ensure_datetime('2024-01-01 12:00:00') == datetime(2024, 1, 1, 12, 0, 0)

        # 纯日期字符串
        result = DateUtils.ensure_datetime('2024-01-01')
        assert result.date() == date(2024, 1, 1)
        assert result.time() == datetime.min.time()

    def test_format_date(self):
        """测试格式化日期"""
        d = date(2024, 1, 1)
        dt = datetime(2024, 1, 1, 12, 30, 45)

        # 默认格式
        assert DateUtils.format_date(d) == '2024-01-01'
        assert DateUtils.format_date(dt) == '2024-01-01'

        # 自定义格式
        assert DateUtils.format_date(d, '%Y/%m/%d') == '2024/01/01'
        assert DateUtils.format_date(dt, '%Y-%m-%d %H:%M:%S') == '2024-01-01 12:30:45'

    def test_get_week_range(self):
        """测试获取周范围"""
        # 2024-01-01 是周一
        test_date = date(2024, 1, 1)
        start, end = DateUtils.get_week_range(test_date)

        assert start == date(2024, 1, 1)  # 周一
        assert end == date(2024, 1, 7)    # 周日

        # 2024-01-15 是周一
        test_date2 = date(2024, 1, 15)
        start2, end2 = DateUtils.get_week_range(test_date2)

        assert start2 == date(2024, 1, 15)
        assert end2 == date(2024, 1, 21)

        # 使用默认值（今天）
        today = date.today()
        start_today, end_today = DateUtils.get_week_range()

        # 应该是本周的周一到周日
        assert start_today.weekday() == 0  # 周一
        assert end_today.weekday() == 6    # 周日
        assert start_today <= today <= end_today

    def test_get_month_range(self):
        """测试获取月范围"""
        test_date = date(2024, 1, 15)
        start, end = DateUtils.get_month_range(test_date)

        assert start == date(2024, 1, 1)
        assert end == date(2024, 1, 31)

        # 二月（闰年）
        test_date2 = date(2024, 2, 15)
        start2, end2 = DateUtils.get_month_range(test_date2)

        assert start2 == date(2024, 2, 1)
        assert end2 == date(2024, 2, 29)

        # 十二月
        test_date3 = date(2024, 12, 15)
        start3, end3 = DateUtils.get_month_range(test_date3)

        assert start3 == date(2024, 12, 1)
        assert end3 == date(2024, 12, 31)

    def test_get_quarter_range(self):
        """测试获取季度范围"""
        # 第一季度
        q1_date = date(2024, 2, 15)
        q1_start, q1_end = DateUtils.get_quarter_range(q1_date)

        assert q1_start == date(2024, 1, 1)
        assert q1_end == date(2024, 3, 31)

        # 第二季度
        q2_date = date(2024, 5, 15)
        q2_start, q2_end = DateUtils.get_quarter_range(q2_date)

        assert q2_start == date(2024, 4, 1)
        assert q2_end == date(2024, 6, 30)

        # 第四季度
        q4_date = date(2024, 11, 15)
        q4_start, q4_end = DateUtils.get_quarter_range(q4_date)

        assert q4_start == date(2024, 10, 1)
        assert q4_end == date(2024, 12, 31)

    def test_is_workday(self):
        """测试判断工作日"""
        # 周一
        monday = date(2024, 1, 1)  # 2024-01-01是周一
        assert DateUtils.is_workday(monday) is True

        # 周六
        saturday = date(2024, 1, 6)  # 2024-01-06是周六
        assert DateUtils.is_workday(saturday) is False

        # 周日
        sunday = date(2024, 1, 7)  # 2024-01-07是周日
        assert DateUtils.is_workday(sunday) is False

        # 带节假日
        holidays = [date(2024, 1, 1)]  # 元旦
        assert DateUtils.is_workday(monday, holidays) is False

    def test_calculate_time_difference(self):
        """测试计算时间差"""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 13, 30, 0)  # 1.5小时后

        # 秒
        seconds = DateUtils.calculate_time_difference(start, end, 'seconds')
        assert seconds == 90 * 60  # 90分钟 * 60秒

        # 分钟
        minutes = DateUtils.calculate_time_difference(start, end, 'minutes')
        assert minutes == 90

        # 小时
        hours = DateUtils.calculate_time_difference(start, end, 'hours')
        assert hours == 1.5

        # 天
        start2 = datetime(2024, 1, 1, 12, 0, 0)
        end2 = datetime(2024, 1, 3, 12, 0, 0)  # 2天后
        days = DateUtils.calculate_time_difference(start2, end2, 'days')
        assert days == 2.0

        # 字符串输入
        seconds_str = DateUtils.calculate_time_difference(
            '2024-01-01 12:00:00',
            '2024-01-01 13:30:00',
            'seconds'
        )
        assert seconds_str == 90 * 60

    def test_calculate_time_difference_invalid_unit(self):
        """测试计算时间差使用无效单位"""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 13, 0, 0)

        with pytest.raises(ValueError, match='不支持的时间单位'):
            DateUtils.calculate_time_difference(start, end, 'invalid')

    def test_round_to_nearest(self):
        """测试将时间舍入到最接近的时间间隔"""
        dt = datetime(2024, 1, 1, 12, 7, 30)

        # 最接近的15分钟
        rounded = DateUtils.round_to_nearest(dt, minutes=15, rounding='nearest')
        assert rounded == datetime(2024, 1, 1, 12, 0, 0)

        dt2 = datetime(2024, 1, 1, 12, 8, 30)
        rounded2 = DateUtils.round_to_nearest(dt2, minutes=15, rounding='nearest')
        assert rounded2 == datetime(2024, 1, 1, 12, 15, 0)

        # 向下舍入
        floor = DateUtils.round_to_nearest(dt, minutes=15, rounding='floor')
        assert floor == datetime(2024, 1, 1, 12, 0, 0)

        # 向上舍入
        ceil = DateUtils.round_to_nearest(dt, minutes=15, rounding='ceil')
        assert ceil == datetime(2024, 1, 1, 12, 15, 0)

    def test_round_to_nearest_edge_cases(self):
        """测试舍入的边缘情况"""
        # 正好在边界上
        dt = datetime(2024, 1, 1, 12, 0, 0)
        rounded = DateUtils.round_to_nearest(dt, minutes=15, rounding='nearest')
        assert rounded == dt

        # 负分钟数
        dt2 = datetime(2024, 1, 1, 12, 0, 0)
        rounded2 = DateUtils.round_to_nearest(dt2, minutes=0, rounding='nearest')
        assert rounded2 == dt2  # 应该返回原时间

    def test_convert_timezone(self):
        """测试转换时区"""
        # 北京时间中午12点
        dt = datetime(2024, 1, 1, 12, 0, 0)

        # 转换为UTC
        utc_time = DateUtils.convert_timezone(dt, 'Asia/Shanghai', 'UTC')

        # 北京时间比UTC早8小时
        assert utc_time.hour == 4  # 12 - 8 = 4

        # 从UTC转换回来
        shanghai_time = DateUtils.convert_timezone(utc_time, 'UTC', 'Asia/Shanghai')
        assert shanghai_time.hour == 12

        # 无时区信息，默认UTC
        dt_no_tz = datetime(2024, 1, 1, 12, 0, 0)
        converted = DateUtils.convert_timezone(dt_no_tz, to_tz='Asia/Shanghai')
        assert converted.tzinfo is not None


class TestDateRange:
    """测试日期范围类"""

    def test_initialization(self):
        """测试初始化"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)

        dr = DateRange(start, end)

        assert dr.start == start
        assert dr.end == end

    def test_contains(self):
        """测试包含关系"""
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 5))

        # 范围内的日期
        assert date(2024, 1, 1) in dr
        assert date(2024, 1, 3) in dr
        assert date(2024, 1, 5) in dr

        # 范围外的日期
        assert date(2023, 12, 31) not in dr
        assert date(2024, 1, 6) not in dr

    def test_iteration(self):
        """测试迭代"""
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 3))

        dates = list(dr)

        assert len(dates) == 3
        assert dates[0] == date(2024, 1, 1)
        assert dates[1] == date(2024, 1, 2)
        assert dates[2] == date(2024, 1, 3)

    def test_length(self):
        """测试长度计算"""
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 5))

        assert len(dr) == 5  # 包含首尾

        # 单日范围
        dr_single = DateRange(date(2024, 1, 1), date(2024, 1, 1))
        assert len(dr_single) == 1

    def test_str_representation(self):
        """测试字符串表示"""
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 5))

        s = str(dr)

        assert '2024-01-01' in s
        assert '2024-01-05' in s
        assert '5天' in s

    def test_split_by_week(self):
        """测试按周拆分"""
        # 跨两周的范围
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 14))

        weeks = dr.split_by_week()

        # 应该拆分为两周
        assert len(weeks) == 2

        # 第一周
        assert weeks[0].start == date(2024, 1, 1)
        assert weeks[0].end == date(2024, 1, 7)

        # 第二周
        assert weeks[1].start == date(2024, 1, 8)
        assert weeks[1].end == date(2024, 1, 14)

    def test_split_by_week_partial(self):
        """测试按周拆分部分周"""
        # 从周中开始
        dr = DateRange(date(2024, 1, 3), date(2024, 1, 10))

        weeks = dr.split_by_week()

        # 第一周（部分周）
        assert weeks[0].start == date(2024, 1, 3)
        assert weeks[0].end == date(2024, 1, 7)

        # 第二周（部分周）
        assert weeks[1].start == date(2024, 1, 8)
        assert weeks[1].end == date(2024, 1, 10)

    def test_split_by_month(self):
        """测试按月拆分"""
        # 跨两个月的范围
        dr = DateRange(date(2024, 1, 15), date(2024, 2, 15))

        months = dr.split_by_month()

        # 应该拆分为两个月
        assert len(months) == 2

        # 一月
        assert months[0].start == date(2024, 1, 15)
        assert months[0].end == date(2024, 1, 31)

        # 二月
        assert months[1].start == date(2024, 2, 1)
        assert months[1].end == date(2024, 2, 15)

    def test_split_by_month_multiple(self):
        """测试跨越多个月份的拆分"""
        dr = DateRange(date(2024, 1, 10), date(2024, 3, 20))

        months = dr.split_by_month()

        # 应该拆分为三个月
        assert len(months) == 3

        assert months[0].start == date(2024, 1, 10)
        assert months[0].end == date(2024, 1, 31)

        assert months[1].start == date(2024, 2, 1)
        assert months[1].end == date(2024, 2, 29)  # 2024是闰年

        assert months[2].start == date(2024, 3, 1)
        assert months[2].end == date(2024, 3, 20)
```

### `tests/unit/utils/test_logger.py`

```python
import pytest
import logging
import json
import tempfile
from pathlib import Path

from src.utils.logger import (
    setup_logging,
    get_logger,
    LoggerMixin,
    JSONFormatter,
    ColoredFormatter
)


class TestJSONFormatter:
    """测试JSON格式化器"""

    @pytest.fixture
    def json_formatter(self):
        """创建JSON格式化器实例"""
        return JSONFormatter()

    def test_format_basic(self, json_formatter):
        """测试基本格式化"""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='测试消息',
            args=(),
            exc_info=None
        )

        formatted = json_formatter.format(record)

        # 应该是有效的JSON
        parsed = json.loads(formatted)

        # 验证基本字段
        assert parsed['level'] == 'INFO'
        assert parsed['logger'] == 'test'
        assert parsed['message'] == '测试消息'
        assert parsed['module'] == 'test'
        assert 'timestamp' in parsed

    def test_format_with_exception(self, json_formatter):
        """测试带异常的格式化"""
        try:
            raise ValueError('测试异常')
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name='test',
            level=logging.ERROR,
            pathname='test.py',
            lineno=10,
            msg='发生异常',
            args=(),
            exc_info=exc_info
        )

        formatted = json_formatter.format(record)
        parsed = json.loads(formatted)

        # 应该包含异常信息
        assert 'exception' in parsed
        assert 'ValueError' in parsed['exception']
        assert '测试异常' in parsed['exception']

    def test_format_with_extra_fields(self, json_formatter):
        """测试带额外字段的格式化"""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='测试消息',
            args=(),
            exc_info=None
        )

        # 添加额外字段
        record.extra_fields = {
            'user': 'testuser',
            'action': 'login',
            'duration_ms': 123.45
        }

        formatted = json_formatter.format(record)
        parsed = json.loads(formatted)

        # 验证额外字段
        assert parsed['user'] == 'testuser'
        assert parsed['action'] == 'login'
        assert parsed['duration_ms'] == 123.45


class TestColoredFormatter:
    """测试彩色格式化器"""

    @pytest.fixture
    def colored_formatter(self):
        """创建彩色格式化器实例"""
        return ColoredFormatter()

    def test_format_basic(self, colored_formatter):
        """测试基本格式化"""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='测试消息',
            args=(),
            exc_info=None
        )

        formatted = colored_formatter.format(record)

        # 应该包含基本元素
        assert 'test' in formatted
        assert 'INFO' in formatted
        assert '测试消息' in formatted

        # 应该包含颜色代码（ANSI转义序列）
        assert '\x1b[' in formatted  # ANSI转义序列

    def test_different_levels(self, colored_formatter):
        """测试不同级别的颜色"""
        levels = [
            (logging.DEBUG, 'cyan'),
            (logging.INFO, 'green'),
            (logging.WARNING, 'yellow'),
            (logging.ERROR, 'red'),
            (logging.CRITICAL, 'red,bg_white')
        ]

        for level, _ in levels:
            record = logging.LogRecord(
                name='test',
                level=level,
                pathname='test.py',
                lineno=10,
                msg=f'级别 {level}',
                args=(),
                exc_info=None
            )

            formatted = colored_formatter.format(record)
            assert '\x1b[' in formatted  # 所有级别都应该有颜色


class TestLoggerFunctions:
    """测试日志函数"""

    def test_setup_logging_default(self, temp_dir):
        """测试默认日志设置"""
        log_file = temp_dir / 'test.log'

        config = {
            'file': str(log_file),
            'enable_console': False
        }

        setup_logging(config)

        # 获取根日志记录器
        root_logger = logging.getLogger()

        # 应该配置了文件处理器
        file_handlers = [h for h in root_logger.handlers
                        if isinstance(h, logging.FileHandler)]

        assert len(file_handlers) > 0

        # 记录测试消息
        test_logger = logging.getLogger('test_module')
        test_logger.info('测试消息')

        # 验证消息已写入文件
        assert log_file.exists()
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()

        assert '测试消息' in content

    def test_setup_logging_json_format(self, temp_dir):
        """测试JSON格式日志设置"""
        log_file = temp_dir / 'test.json.log'

        config = {
            'file': str(log_file),
            'enable_json': True,
            'enable_console': False
        }

        setup_logging(config)

        # 记录测试消息
        test_logger = logging.getLogger('test_json')
        test_logger.info('JSON测试消息')

        # 验证消息是JSON格式
        assert log_file.exists()
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 应该有一行JSON
        assert len(lines) > 0

        # 验证是有效的JSON
        parsed = json.loads(lines[0].strip())
        assert parsed['message'] == 'JSON测试消息'
        assert parsed['level'] == 'INFO'

    def test_setup_logging_console_only(self):
        """测试仅控制台日志设置"""
        config = {
            'enable_console': True
        }

        setup_logging(config)

        # 获取根日志记录器
        root_logger = logging.getLogger()

        # 应该只有控制台处理器
        console_handlers = [h for h in root_logger.handlers
                           if isinstance(h, logging.StreamHandler)]

        assert len(console_handlers) > 0

    def test_get_logger(self):
        """测试获取日志记录器"""
        logger = get_logger('test_module')

        assert isinstance(logger, logging.Logger)
        assert logger.name == 'test_module'

        # 指定级别
        debug_logger = get_logger('debug_module', 'DEBUG')
        assert debug_logger.level == logging.DEBUG

        # 默认级别
        info_logger = get_logger('info_module')
        assert info_logger.level == logging.NOTSET  # 继承根日志记录器级别

    def test_setup_logging_with_file_rotation(self, temp_dir):
        """测试带文件轮转的日志设置"""
        log_file = temp_dir / 'rotating.log'

        config = {
            'file': str(log_file),
            'file_size': '1KB',  # 1KB后轮转
            'backup_count': 2,
            'enable_console': False
        }

        setup_logging(config)

        # 获取根日志记录器
        root_logger = logging.getLogger()

        # 查找轮转文件处理器
        from logging.handlers import RotatingFileHandler
        rotating_handlers = [h for h in root_logger.handlers
                           if isinstance(h, RotatingFileHandler)]

        assert len(rotating_handlers) > 0

        # 验证轮转配置
        handler = rotating_handlers[0]
        assert handler.maxBytes == 1024  # 1KB
        assert handler.backupCount == 2


class TestLoggerMixin:
    """测试日志混合类"""

    class TestClass(LoggerMixin):
        """测试类"""

        def do_something(self):
            """测试方法"""
            self.logger.info('正在执行操作')
            return '完成'

    def test_logger_property(self):
        """测试logger属性"""
        test_instance = self.TestClass()

        # logger属性应该存在
        assert hasattr(test_instance, 'logger')
        assert isinstance(test_instance.logger, logging.Logger)

        # 应该是相同的实例
        logger1 = test_instance.logger
        logger2 = test_instance.logger
        assert logger1 is logger2

    def test_log_with_context(self, temp_dir):
        """测试带上下文的日志"""
        log_file = temp_dir / 'context.log'

        config = {
            'file': str(log_file),
            'enable_json': True,
            'enable_console': False
        }

        setup_logging(config)

        test_instance = self.TestClass()

        # 记录带上下文的日志
        test_instance.log_with_context(
            'info',
            '用户操作',
            user='testuser',
            action='login',
            success=True
        )

        # 验证日志内容
        assert log_file.exists()
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 应该有一行JSON日志
        assert len(lines) > 0

        parsed = json.loads(lines[0].strip())
        assert parsed['message'] == '用户操作'
        assert parsed['user'] == 'testuser'
        assert parsed['action'] == 'login'
        assert parsed['success'] is True

    def test_log_with_context_invalid_level(self, temp_dir):
        """测试无效级别的带上下文日志"""
        config = {
            'enable_console': False
        }

        setup_logging(config)

        test_instance = self.TestClass()

        # 使用无效的级别，应该回退到info
        test_instance.log_with_context(
            'invalid_level',
            '测试消息',
            test='data'
        )

        # 应该不抛出异常

    def test_inheritance(self):
        """测试继承"""
        class ChildClass(self.TestClass):
            """子类"""

            def do_child_thing(self):
                self.logger.info('子类操作')

        child_instance = ChildClass()

        # 应该可以访问logger
        assert hasattr(child_instance, 'logger')

        # logger名称应该是子类名
        assert child_instance.logger.name == 'TestChildClass'

    def test_multiple_instances(self):
        """测试多个实例"""
        instance1 = self.TestClass()
        instance2 = self.TestClass()

        # 每个实例应该有独立的logger
        assert instance1.logger is not instance2.logger

        # 但是相同类的不同实例应该有相同名称的logger
        assert instance1.logger.name == instance2.logger.name

    def test_method_usage(self):
        """测试方法使用"""
        test_instance = self.TestClass()

        result = test_instance.do_something()

        assert result == '完成'
        # 注意：这里我们无法验证日志是否被记录，
        # 因为测试环境可能没有配置日志处理器
```

## 四、集成测试

### `tests/integration/test_end_to_end.py`

```python
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import date, datetime
import json

from src.main import NetworkMonitor


class TestEndToEnd:
    """端到端测试"""

    @pytest.fixture
    def setup_test_environment(self):
        """设置测试环境"""
        # 创建临时目录
        temp_dir = Path(tempfile.mkdtemp())

        # 创建目录结构
        log_dir = temp_dir / 'logs'
        report_dir = temp_dir / 'reports'
        archive_dir = temp_dir / 'archive'

        log_dir.mkdir()
        report_dir.mkdir()
        archive_dir.mkdir()

        # 创建配置文件
        config = {
            'version': '1.0',
            'paths': {
                'log_dir': str(log_dir),
                'report_dir': str(report_dir),
                'archive_dir': str(archive_dir),
                'temp_dir': str(temp_dir / 'temp')
            },
            'email': {
                'smtp_server': 'smtp.test.com',
                'smtp_port': 587,
                'use_ssl': False,
                'use_tls': True,
                'username': 'test@test.com',
                'password': 'test_password',
                'from_addr': 'test@test.com',
                'to_addrs': ['recipient@test.com'],
                'cc_addrs': [],
                'subject_prefix': 'TEST - 网络流量监控报告'
            },
            'processing': {
                'max_workers': 2,
                'batch_size': 100,
                'chunk_size': 1024,
                'keep_temp_files': False
            },
            'reports': {
                'format': 'json',
                'include_csv': True,
                'compress_reports': False,
                'generate_summary': True,
                'include_charts': False
            },
            'archive': {
                'enabled': True,
                'compress_format': 'zip',
                'keep_original': False,
                'retention_days': 7,
                'clean_old_archives': True
            },
            'logging': {
                'level': 'WARNING',  # 降低日志级别以减少输出
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file_size': '1MB',
                'backup_count': 2,
                'enable_console': False
            }
        }

        config_file = temp_dir / 'config.yaml'
        import yaml
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        yield {
            'temp_dir': temp_dir,
            'log_dir': log_dir,
            'report_dir': report_dir,
            'archive_dir': archive_dir,
            'config_file': config_file
        }

        # 清理临时目录
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def create_sample_log_files(self, setup_test_environment):
        """创建示例日志文件"""
        log_dir = setup_test_environment['log_dir']

        # 创建两个日期的日志文件
        test_date = date(2024, 1, 1)

        files = []
        for hour in range(2):  # 每个日期两个文件
            filename = f'bandwhich_{test_date.strftime("%Y%m%d")}_{1200 + hour:04d}.log'
            file_path = log_dir / filename

            content = f"""Refreshing:
process: <12345> "firefox" up/down Bps: 150/120 connections: 2
connection: <12345> <enp3s0>:54321 => 192.168.1.{hour + 1}:443 (tcp) up/down Bps: 100/80 process: "firefox"
connection: <12345> <enp3s0>:54322 => 8.8.8.8:53 (udp) up/down Bps: 50/40 process: "firefox"
remote_address: <12345> 192.168.1.{hour + 1} up/down Bps: 100/80 connections: 1
remote_address: <12345> 8.8.8.8 up/down Bps: 50/40 connections: 1
"""

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            files.append(file_path)

        return files

    def test_end_to_end_processing(self, setup_test_environment, create_sample_log_files):
        """测试端到端处理流程"""
        config_file = setup_test_environment['config_file']

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 生成报告
        monitor.generate_report()

        report_dir = setup_test_environment['report_dir']

        # 验证报告文件
        report_files = list(report_dir.glob('*20240101*'))
        assert len(report_files) >= 3  # 至少JSON、CSV、汇总报告

        # 验证详细报告
        json_report = report_dir / 'report_20240101.json'
        assert json_report.exists()

        # 验证报告内容
        with open(json_report, 'r', encoding='utf-8') as f:
            report_data = json.load(f)

        assert isinstance(report_data, list)
        assert len(report_data) == 4  # 2个文件 * 2个连接

        # 验证汇总报告
        summary_report = report_dir / 'summary_20240101.json'
        assert summary_report.exists()

        with open(summary_report, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)

        assert 'overview' in summary_data
        assert summary_data['overview']['total_records'] == 4

        # 验证存档
        archive_dir = setup_test_environment['archive_dir']
        archive_files = list(archive_dir.glob('*20240101*'))
        assert len(archive_files) >= 1  # 至少一个存档文件

        # 验证原始日志文件已删除（keep_original=False）
        for log_file in create_sample_log_files:
            assert not log_file.exists()

    def test_end_to_end_with_existing_report(self, setup_test_environment, create_sample_log_files):
        """测试已存在报告时的端到端处理"""
        config_file = setup_test_environment['config_file']
        report_dir = setup_test_environment['report_dir']

        # 先创建一个报告文件
        existing_report = report_dir / 'report_20240101.json'
        existing_report.parent.mkdir(parents=True, exist_ok=True)

        with open(existing_report, 'w', encoding='utf-8') as f:
            json.dump([{'test': 'existing'}], f)

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 生成报告
        monitor.generate_report()

        # 验证报告文件数量
        report_files = list(report_dir.glob('*20240101*'))

        # 应该只有我们创建的那个文件（跳过处理）
        # 注意：实际可能会有其他文件（如日志文件），但详细报告应该只有一个
        json_reports = [f for f in report_files if f.name.startswith('report_') and f.suffix == '.json']
        assert len(json_reports) == 1

        # 验证报告内容没有被覆盖
        with open(existing_report, 'r', encoding='utf-8') as f:
            report_data = json.load(f)

        assert report_data == [{'test': 'existing'}]

    def test_end_to_end_multiple_days(self, setup_test_environment):
        """测试多天端到端处理"""
        log_dir = setup_test_environment['log_dir']
        config_file = setup_test_environment['config_file']

        # 创建两天的日志文件
        for day in range(1, 3):
            test_date = date(2024, 1, day)
            filename = f'bandwhich_{test_date.strftime("%Y%m%d")}_1200.log'
            file_path = log_dir / filename

            content = f"""Refreshing:
process: <12345> "test" up/down Bps: 100/80 connections: 1
connection: <12345> <eth0>:54321 => 192.168.1.1:443 (tcp) up/down Bps: 100/80 process: "test"
remote_address: <12345> 192.168.1.1 up/down Bps: 100/80 connections: 1
"""

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 生成报告
        monitor.generate_report()

        report_dir = setup_test_environment['report_dir']

        # 验证两天的报告
        for day in range(1, 3):
            date_str = f'202401{day:02d}'
            json_report = report_dir / f'report_{date_str}.json'

            assert json_report.exists()

            with open(json_report, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            assert len(report_data) == 1  # 每条记录

    def test_end_to_end_with_no_traffic(self, setup_test_environment):
        """测试无流量日志的端到端处理"""
        log_dir = setup_test_environment['log_dir']
        config_file = setup_test_environment['config_file']

        # 创建只包含NO TRAFFIC的日志文件
        test_date = date(2024, 1, 1)
        filename = f'bandwhich_{test_date.strftime("%Y%m%d")}_1200.log'
        file_path = log_dir / filename

        content = """Refreshing:
<NO TRAFFIC>

Refreshing:
<NO TRAFFIC>
"""

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 生成报告
        monitor.generate_report()

        report_dir = setup_test_environment['report_dir']

        # 应该没有报告文件（无有效记录）
        report_files = list(report_dir.glob('*20240101*'))
        assert len(report_files) == 0

    def test_end_to_end_with_invalid_logs(self, setup_test_environment):
        """测试包含无效日志的端到端处理"""
        log_dir = setup_test_environment['log_dir']
        config_file = setup_test_environment['config_file']

        # 创建混合文件：一个有效，一个无效
        test_date = date(2024, 1, 1)

        # 有效文件
        valid_file = log_dir / f'bandwhich_{test_date.strftime("%Y%m%d")}_1200.log'
        valid_content = """Refreshing:
process: <12345> "test" up/down Bps: 100/80 connections: 1
connection: <12345> <eth0>:54321 => 192.168.1.1:443 (tcp) up/down Bps: 100/80 process: "test"
"""

        with open(valid_file, 'w', encoding='utf-8') as f:
            f.write(valid_content)

        # 无效文件（错误文件名格式）
        invalid_file = log_dir / 'invalid.log'
        invalid_content = """无效内容"""

        with open(invalid_file, 'w', encoding='utf-8') as f:
            f.write(invalid_content)

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 生成报告（应该不抛出异常）
        monitor.generate_report()

        report_dir = setup_test_environment['report_dir']

        # 应该只有有效文件的报告
        report_files = list(report_dir.glob('*20240101*'))
        assert len(report_files) >= 1

    def test_end_to_end_date_filter(self, setup_test_environment):
        """测试日期过滤的端到端处理"""
        log_dir = setup_test_environment['log_dir']
        config_file = setup_test_environment['config_file']

        # 创建两天的日志文件
        for day in range(1, 4):  # 1-3号
            test_date = date(2024, 1, day)
            filename = f'bandwhich_{test_date.strftime("%Y%m%d")}_1200.log'
            file_path = log_dir / filename

            content = f"""Refreshing:
process: <12345> "test" up/down Bps: 100/80 connections: 1
connection: <12345> <eth0>:54321 => 192.168.1.{day}:443 (tcp) up/down Bps: 100/80 process: "test"
"""

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 只处理1号和3号
        monitor.generate_report(date_filter='2024010[13]')

        report_dir = setup_test_environment['report_dir']

        # 验证只有1号和3号的报告
        for day in [1, 2, 3]:
            date_str = f'202401{day:02d}'
            json_report = report_dir / f'report_{date_str}.json'

            if day in [1, 3]:
                assert json_report.exists()
            else:
                assert not json_report.exists()
```

## 五、功能测试

### `tests/functional/test_report_generation.py`

```python
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import date, datetime
import pandas as pd
import json

from src.report_generator import ReportGenerator
from src.log_parser import TrafficRecord


class TestReportGeneration:
    """报告生成功能测试"""

    @pytest.fixture
    def setup_test_data(self):
        """设置测试数据"""
        temp_dir = Path(tempfile.mkdtemp())

        # 创建报告生成器
        report_dir = temp_dir / 'reports'
        generator = ReportGenerator(report_dir)

        # 创建测试记录
        records = [
            TrafficRecord(
                timestamp=datetime(2024, 1, 1, 10 + i, 0, 0),
                pid=10000 + i,
                process_name=f'process_{i % 3}',
                local_interface='eth0',
                local_port=50000 + i,
                remote_address=f'192.168.1.{i + 1}',
                remote_port=443 if i % 2 == 0 else 80,
                protocol='tcp',
                upload_bps=100 * (i + 1),
                download_bps=50 * (i + 1),
                source_file=f'test_{i}.log'
            )
            for i in range(10)  # 10条记录
        ]

        yield {
            'temp_dir': temp_dir,
            'generator': generator,
            'records': records,
            'report_date': date(2024, 1, 1)
        }

        # 清理
        shutil.rmtree(temp_dir)

    def test_large_dataset_processing(self, setup_test_data):
        """测试大数据集处理"""
        generator = setup_test_data['generator']
        report_date = setup_test_data['report_date']
        records = setup_test_data['records']

        # 生成报告
        report_files = generator.generate_daily_report(
            report_date,
            records,
            include_csv=True,
            compress=False
        )

        # 验证所有报告文件
        assert len(report_files) >= 4  # JSON, CSV, 汇总, 统计

        # 验证JSON报告
        json_file = generator.output_dir / 'report_20240101.json'
        assert json_file.exists()

        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        assert len(json_data) == 10

        # 验证CSV报告
        csv_file = generator.output_dir / 'report_20240101.csv'
        assert csv_file.exists()

        df = pd.read_csv(csv_file)
        assert len(df) == 10
        assert df['upload_bps'].sum() == sum(r.upload_bps for r in records)

    def test_report_with_different_processes(self, setup_test_data):
        """测试不同进程的报告"""
        generator = setup_test_data['generator']

        # 转换记录为DataFrame
        from dataclasses import asdict
        records_dict = [asdict(r) for r in setup_test_data['records']]
        df = pd.DataFrame(records_dict)

        # 测试进程汇总
        process_summary = generator._calculate_process_summary(df)

        # 应该有3个不同的进程
        assert len(process_summary) == 3

        # 验证进程名称
        process_names = set(process_summary['process_name'])
        assert process_names == {'process_0', 'process_1', 'process_2'}

        # 验证总流量
        total_upload = process_summary['upload_sum'].sum()
        expected_upload = sum(r.upload_bps for r in setup_test_data['records'])
        assert total_upload == expected_upload

    def test_report_with_different_remotes(self, setup_test_data):
        """测试不同远程地址的报告"""
        generator = setup_test_data['generator']

        from dataclasses import asdict
        records_dict = [asdict(r) for r in setup_test_data['records']]
        df = pd.DataFrame(records_dict)

        # 测试远程地址汇总
        remote_summary = generator._calculate_remote_summary(df)

        # 应该有10个不同的远程地址
        assert len(remote_summary) == 10

        # 验证所有地址都是IP
        assert remote_summary['is_ip'].all()

    def test_time_distribution_analysis(self, setup_test_data):
        """测试时间分布分析"""
        generator = setup_test_data['generator']

        from dataclasses import asdict
        records_dict = [asdict(r) for r in setup_test_data['records']]
        df = pd.DataFrame(records_dict)

        # 添加小时列
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour

        # 测试时间汇总
        time_summary = generator._calculate_time_summary(df)

        assert 'hourly' in time_summary

        hourly = time_summary['hourly']
        assert 'upload_bps' in hourly

        # 验证小时分布
        upload_by_hour = hourly['upload_bps']

        # 应该有10-19小时的数据
        for hour in range(10, 20):
            if hour in upload_by_hour:
                assert upload_by_hour[hour] > 0

    def test_top_items_calculation(self, setup_test_data):
        """测试顶级项目计算"""
        generator = setup_test_data['generator']

        from dataclasses import asdict
        records_dict = [asdict(r) for r in setup_test_data['records']]
        df = pd.DataFrame(records_dict)

        # 测试按进程获取顶级项目
        top_processes = generator._get_top_items(df, 'process_name', 'upload_bps', 2)

        assert len(top_processes) == 2

        # 应该按上传流量排序
        values = [item['value'] for item in top_processes]
        assert values == sorted(values, reverse=True)

        # 测试按远程地址获取顶级项目
        top_remotes = generator._get_top_items(df, 'remote_address', 'download_bps', 3)

        assert len(top_remotes) == 3

        # 测试计数
        top_ports = generator._get_top_items(df, 'local_port', 'count', 5)

        assert len(top_ports) == 5
        # 每个端口应该只有1条记录
        for item in top_ports:
            assert item['value'] == 1.0

    def test_statistics_report_generation(self, setup_test_data):
        """测试统计报告生成"""
        generator = setup_test_data['generator']

        from dataclasses import asdict
        records_dict = [asdict(r) for r in setup_test_data['records']]
        df = pd.DataFrame(records_dict)

        date_str = '20240101'

        # 生成统计报告
        result = generator._generate_statistics_report(date_str, df)

        assert 'stats_json' in result

        stats_file = result['stats_json']
        assert stats_file.exists()

        # 验证统计报告内容
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats_data = json.load(f)

        # 验证基本结构
        assert 'traffic_statistics' in stats_data
        assert 'connection_statistics' in stats_data
        assert 'process_statistics' in stats_data

        # 验证流量统计
        traffic_stats = stats_data['traffic_statistics']

        # 验证上传统计
        upload_stats = traffic_stats['upload']
        assert upload_stats['total_bytes'] == sum(r.upload_bps for r in setup_test_data['records'])
        assert 'average_bps' in upload_stats
        assert 'max_bps' in upload_stats
        assert 'percentiles' in upload_stats

        # 验证连接统计
        conn_stats = stats_data['connection_statistics']
        assert conn_stats['total_connections'] == 10
        assert conn_stats['unique_ports'] == 10

        # 验证进程统计
        proc_stats = stats_data['process_statistics']
        assert proc_stats['total_processes'] == 3

    def test_report_compression(self, setup_test_data):
        """测试报告压缩"""
        generator = setup_test_data['generator']
        temp_dir = setup_test_data['temp_dir']

        # 创建一些测试文件
        test_files = []
        for i in range(3):
            file_path = temp_dir / f'test_{i}.txt'
            file_path.write_text('测试内容 ' * 100)  # 创建大文件
            test_files.append(file_path)

        date_str = '20240101'

        # 压缩文件
        zip_file = generator._compress_reports(date_str, test_files)

        assert zip_file.exists()
        assert zip_file.suffix == '.zip'

        # 验证压缩文件大小
        original_size = sum(f.stat().st_size for f in test_files)
        compressed_size = zip_file.stat().st_size

        # 压缩文件应该更小
        assert compressed_size < original_size

        # 验证压缩文件内容
        import zipfile
        with zipfile.ZipFile(zip_file, 'r') as zipf:
            file_list = zipf.namelist()
            assert len(file_list) == 3
            assert all(f.name in file_list for f in test_files)
```

## 六、性能测试

### `tests/performance/test_scalability.py`

```python
import pytest
import tempfile
import time
from pathlib import Path
from datetime import datetime, date, timedelta
import psutil
import os

from src.parallel_processor import ParallelProcessor
from src.log_parser import LogParser
from src.report_generator import ReportGenerator


class TestScalability:
    """可扩展性测试"""

    @pytest.fixture
    def create_large_dataset(self):
        """创建大型数据集"""
        temp_dir = Path(tempfile.mkdtemp())

        # 创建包含大量记录的日志文件
        log_file = temp_dir / 'large.log'

        with open(log_file, 'w', encoding='utf-8') as f:
            # 写入1000个刷新块
            for block_idx in range(1000):
                f.write('Refreshing:\n')

                # 每个块有10个连接
                for conn_idx in range(10):
                    pid = 10000 + (block_idx * 10 + conn_idx) % 100
                    process_name = f'process_{(block_idx + conn_idx) % 5}'
                    remote_ip = f'192.168.{(block_idx // 256) % 256}.{conn_idx + 1}'

                    f.write(f'process: <{pid}> "{process_name}" up/down Bps: 100/50 connections: 1\n')
                    f.write(f'connection: <{pid}> <eth0>:{50000 + conn_idx} => {remote_ip}:443 (tcp) up/down Bps: 100/50 process: "{process_name}"\n')
                    f.write(f'remote_address: <{pid}> {remote_ip} up/down Bps: 100/50 connections: 1\n')

                f.write('\n')

        yield {
            'temp_dir': temp_dir,
            'log_file': log_file,
            'expected_records': 1000 * 10  # 1000块 * 10连接/块
        }

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

    def test_parser_performance(self, create_large_dataset):
        """测试解析器性能"""
        log_file = create_large_dataset['log_file']
        expected_records = create_large_dataset['expected_records']

        parser = LogParser()

        # 测量解析时间
        start_time = time.time()

        from src.file_scanner import LogFileInfo
        file_info = LogFileInfo(
            path=log_file,
            date=date.today(),
            base_time=datetime.now(),
            size=log_file.stat().st_size,
            md5='test',
            modified_time=datetime.now()
        )

        records = parser.parse_file(file_info)

        end_time = time.time()
        elapsed_time = end_time - start_time

        # 验证解析结果
        assert len(records) == expected_records

        # 输出性能指标
        records_per_second = len(records) / elapsed_time
        print(f"\n解析性能: {records_per_second:.2f} 记录/秒")
        print(f"总记录数: {len(records)}")
        print(f"总时间: {elapsed_time:.2f} 秒")

        # 性能断言（可根据实际硬件调整）
        assert records_per_second > 100, f"解析速度太慢: {records_per_second:.2f} 记录/秒"

    def test_parser_memory_usage(self, create_large_dataset):
        """测试解析器内存使用"""
        log_file = create_large_dataset['log_file']

        parser = LogParser()

        # 获取初始内存使用
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 解析文件
        from src.file_scanner import LogFileInfo
        file_info = LogFileInfo(
            path=log_file,
            date=date.today(),
            base_time=datetime.now(),
            size=log_file.stat().st_size,
            md5='test',
            modified_time=datetime.now()
        )

        records = parser.parse_file(file_info)

        # 获取最终内存使用
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # 输出内存使用信息
        print(f"\n内存使用:")
        print(f"初始内存: {initial_memory:.2f} MB")
        print(f"最终内存: {final_memory:.2f} MB")
        print(f"内存增加: {memory_increase:.2f} MB")
        print(f"记录数: {len(records)}")
        print(f"每记录内存: {memory_increase / len(records) * 1024:.2f} KB")

        # 内存使用断言
        assert memory_increase / len(records) < 10, f"每记录内存使用过高: {memory_increase / len(records) * 1024:.2f} KB"

    def test_parallel_processing_scalability(self):
        """测试并行处理可扩展性"""
        # 创建测试数据
        items = list(range(1000))

        # 模拟处理函数
        def process_item(item):
            time.sleep(0.001)  # 模拟处理时间
            return item * 2

        # 测试不同工作线程数的性能
        results = {}

        for workers in [1, 2, 4, 8]:
            processor = ParallelProcessor(max_workers=workers)

            start_time = time.time()
            processed = processor.process_in_batches(
                items, process_item, batch_size=100
            )
            end_time = time.time()

            elapsed_time = end_time - start_time
            items_per_second = len(items) / elapsed_time

            results[workers] = {
                'time': elapsed_time,
                'items_per_second': items_per_second,
                'speedup': results[1]['time'] / elapsed_time if workers > 1 else 1.0
            }

            print(f"\n工作线程数: {workers}")
            print(f"总时间: {elapsed_time:.2f} 秒")
            print(f"处理速度: {items_per_second:.2f} 项/秒")
            print(f"加速比: {results[workers]['speedup']:.2f}x")

        # 验证并行加速（允许一些开销）
        assert results[4]['speedup'] > 2.0, f"4线程加速不足: {results[4]['speedup']:.2f}x"

    def test_report_generation_performance(self, create_large_dataset):
        """测试报告生成性能"""
        temp_dir = create_large_dataset['temp_dir']

        # 创建报告生成器
        report_dir = temp_dir / 'reports'
        generator = ReportGenerator(report_dir)

        # 创建大量记录
        records = []
        for i in range(10000):
            records.append(type('Record', (), {
                'timestamp': datetime.now() + timedelta(seconds=i),
                'pid': 10000 + i % 100,
                'process_name': f'process_{i % 10}',
                'local_interface': 'eth0',
                'local_port': 50000 + i % 1000,
                'remote_address': f'192.168.{i // 256 % 256}.{i % 256 + 1}',
                'remote_port': 443 if i % 2 == 0 else 80,
                'protocol': 'tcp',
                'upload_bps': 100 + i % 900,
                'download_bps': 50 + i % 450,
                'source_file': f'test_{i // 1000}.log'
            }))

        # 测量报告生成时间
        start_time = time.time()

        report_date = date.today()
        report_files = generator.generate_daily_report(
            report_date,
            records,
            include_csv=True,
            compress=False
        )

        end_time = time.time()
        elapsed_time = end_time - start_time

        # 输出性能指标
        records_per_second = len(records) / elapsed_time
        print(f"\n报告生成性能: {records_per_second:.2f} 记录/秒")
        print(f"总记录数: {len(records)}")
        print(f"总时间: {elapsed_time:.2f} 秒")

        # 验证报告文件
        assert len(report_files) >= 3

        # 性能断言
        assert records_per_second > 100, f"报告生成速度太慢: {records_per_second:.2f} 记录/秒"

    def test_concurrent_file_processing(self, create_large_dataset):
        """测试并发文件处理"""
        temp_dir = create_large_dataset['temp_dir']

        # 创建多个日志文件
        file_count = 10
        files = []

        for i in range(file_count):
            file_path = temp_dir / f'log_{i}.log'

            with open(file_path, 'w', encoding='utf-8') as f:
                # 每个文件100个刷新块，每个块5个连接
                for block_idx in range(100):
                    f.write('Refreshing:\n')

                    for conn_idx in range(5):
                        pid = 10000 + i * 100 + conn_idx
                        process_name = f'process_{i % 5}'

                        f.write(f'process: <{pid}> "{process_name}" up/down Bps: 100/50 connections: 1\n')
                        f.write(f'connection: <{pid}> <eth0>:{50000 + conn_idx} => 192.168.{i}.{conn_idx + 1}:443 (tcp) up/down Bps: 100/50 process: "{process_name}"\n')

                    f.write('\n')

            files.append(file_path)

        # 测试并行处理
        processor = ParallelProcessor(max_workers=4)

        def process_file(file_path):
            parser = LogParser()

            from src.file_scanner import LogFileInfo
            file_info = LogFileInfo(
                path=file_path,
                date=date.today(),
                base_time=datetime.now(),
                size=file_path.stat().st_size,
                md5='test',
                modified_time=datetime.now()
            )

            return parser.parse_file(file_info)

        # 测量并行处理时间
        start_time = time.time()
        results = processor.process_in_batches(files, process_file, batch_size=3)
        end_time = time.time()

        elapsed_time = end_time - start_time

        # 计算总记录数
        total_records = sum(len(r) for r in results if r is not None)

        # 输出性能指标
        files_per_second = len(files) / elapsed_time
        records_per_second = total_records / elapsed_time

        print(f"\n并发文件处理性能:")
        print(f"文件数: {len(files)}")
        print(f"总记录数: {total_records}")
        print(f"总时间: {elapsed_time:.2f} 秒")
        print(f"文件处理速度: {files_per_second:.2f} 文件/秒")
        print(f"记录处理速度: {records_per_second:.2f} 记录/秒")

        # 验证所有文件都成功处理
        assert len(results) == len(files)
        assert all(r is not None for r in results)

        # 性能断言
        assert files_per_second > 0.5, f"文件处理速度太慢: {files_per_second:.2f} 文件/秒"
```

## 七、测试配置和运行脚本

### `tests/__init__.py`

```python
"""
网络监控系统测试套件
"""

__version__ = '1.0.0'
```

### `pytest.ini`

```ini
[pytest]
# 测试配置
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    -p no:warnings

# 测试标记
markers =
    unit: 单元测试
    integration: 集成测试
    functional: 功能测试
    performance: 性能测试
    slow: 慢速测试（需要较长时间）
    network: 需要网络连接的测试
    email: 邮件相关测试

# 日志配置
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)s] %(name)s: %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# 测试覆盖率
minversion = 6.0
```

### `requirements-dev.txt`

```txt
# 测试依赖
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-xdist>=3.0.0
pytest-mock>=3.10.0
pytest-asyncio>=0.20.0
pytest-html>=3.2.0
pytest-rerunfailures>=11.0
pytest-timeout>=2.1.0

# 性能测试
psutil>=5.9.0
memory-profiler>=0.60.0

# 代码质量
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
isort>=5.12.0
pylint>=2.17.0
bandit>=1.7.0

# HTTP测试
pytest-httpx>=0.24.0
vcrpy>=4.3.0
requests-mock>=1.10.0

# 文档测试
sphinx>=6.0.0
sphinx-rtd-theme>=1.2.0

# 其他工具
coverage>=7.0.0
tox>=4.0.0
pre-commit>=3.0.0
```

### `run_tests.py`

```python
#!/usr/bin/env python3
"""
运行测试套件的主脚本
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_tests(test_type=None, coverage=False, parallel=False, html_report=False):
    """运行测试"""
    cmd = [sys.executable, '-m', 'pytest']

    # 添加测试类型筛选
    if test_type:
        if test_type == 'unit':
            cmd.extend(['tests/unit', '-m', 'unit'])
        elif test_type == 'integration':
            cmd.extend(['tests/integration', '-m', 'integration'])
        elif test_type == 'functional':
            cmd.extend(['tests/functional', '-m', 'functional'])
        elif test_type == 'performance':
            cmd.extend(['tests/performance', '-m', 'performance'])
        elif test_type == 'all':
            cmd.append('tests')
        else:
            # 运行特定测试文件
            test_file = Path(f'tests/{test_type}')
            if test_file.exists():
                cmd.append(str(test_file))
            else:
                print(f"错误: 未找到测试文件 {test_file}")
                return False
    else:
        cmd.append('tests')

    # 添加覆盖率
    if coverage:
        cmd.extend(['--cov=src', '--cov-report=term', '--cov-report=html'])

    # 并行运行
    if parallel:
        cmd.extend(['-n', 'auto'])

    # HTML报告
    if html_report:
        cmd.extend(['--html=test_reports/html/report.html', '--self-contained-html'])

    # 添加详细输出
    cmd.append('-v')

    print(f"运行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return False
    except Exception as e:
        print(f"运行测试时出错: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='运行网络监控系统测试套件')
    parser.add_argument('type', nargs='?', default='all',
                       choices=['all', 'unit', 'integration', 'functional', 'performance'],
                       help='测试类型 (默认: all)')
    parser.add_argument('--coverage', '-c', action='store_true',
                       help='生成测试覆盖率报告')
    parser.add_argument('--parallel', '-p', action='store_true',
                       help='并行运行测试')
    parser.add_argument('--html', action='store_true',
                       help='生成HTML测试报告')
    parser.add_argument('--list', '-l', action='store_true',
                       help='列出所有测试')
    parser.add_argument('--slow', action='store_true',
                       help='包含慢速测试')

    args = parser.parse_args()

    # 创建测试报告目录
    report_dir = Path('test_reports')
    report_dir.mkdir(exist_ok=True)
    (report_dir / 'html').mkdir(exist_ok=True)
    (report_dir / 'xml').mkdir(exist_ok=True)

    if args.list:
        # 列出所有测试
        cmd = [sys.executable, '-m', 'pytest', '--collect-only', 'tests']
        subprocess.run(cmd)
        return

    # 运行测试
    success = run_tests(
        test_type=args.type,
        coverage=args.coverage,
        parallel=args.parallel,
        html_report=args.html
    )

    if success:
        print("\n✅ 所有测试通过!")
        sys.exit(0)
    else:
        print("\n❌ 测试失败!")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### `Makefile`

```makefile
# 网络监控系统测试 Makefile

.PHONY: test test-unit test-integration test-functional test-performance coverage clean install

# 默认目标
all: test

# 安装开发依赖
install:
	pip install -r requirements-dev.txt

# 运行所有测试
test:
	python run_tests.py all

# 运行单元测试
test-unit:
	python run_tests.py unit

# 运行集成测试
test-integration:
	python run_tests.py integration

# 运行功能测试
test-functional:
	python run_tests.py functional

# 运行性能测试
test-performance:
	python run_tests.py performance

# 带覆盖率的测试
coverage:
	python run_tests.py all --coverage

# 并行运行测试
test-parallel:
	python run_tests.py all --parallel

# 生成HTML报告
test-html:
	python run_tests.py all --html

# 清理测试文件
clean:
	rm -rf test_reports/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# 代码质量检查
lint:
	flake8 src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/
	mypy src/

# 格式化代码
format:
	black src/ tests/
	isort src/ tests/

# 安全扫描
security:
	bandit -r src/

# 依赖检查
deps:
	pipdeptree --warn fail

# 运行完整CI流程
ci: lint test coverage security

# 帮助信息
help:
	@echo "可用命令:"
	@echo "  make install     安装开发依赖"
	@echo "  make test        运行所有测试"
	@echo "  make test-unit   运行单元测试"
	@echo "  make test-integration 运行集成测试"
	@echo "  make test-functional 运行功能测试"
	@echo "  make test-performance 运行性能测试"
	@echo "  make coverage    运行测试并生成覆盖率报告"
	@echo "  make test-parallel 并行运行测试"
	@echo "  make test-html   生成HTML测试报告"
	@echo "  make lint        代码质量检查"
	@echo "  make format      格式化代码"
	@echo "  make security    安全扫描"
	@echo "  make deps        依赖检查"
	@echo "  make ci          运行完整CI流程"
	@echo "  make clean       清理测试文件"
	@echo "  make help        显示此帮助信息"
```

## 八、使用说明

### 1. **安装测试依赖**

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 或者使用Makefile
make install
```

### 2. **运行测试**

```bash
# 运行所有测试
python run_tests.py all
# 或者
make test

# 运行特定类型的测试
python run_tests.py unit
python run_tests.py integration
python run_tests.py functional
python run_tests.py performance

# 带覆盖率的测试
python run_tests.py all --coverage
# 或者
make coverage

# 并行运行测试
python run_tests.py all --parallel

# 生成HTML报告
python run_tests.py all --html
```

### 3. **代码质量检查**

```bash
# 运行代码质量检查
make lint

# 格式化代码
make format

# 安全扫描
make security
```

### 4. **完整CI流程**

```bash
# 运行完整CI流程
make ci
```

### 5. **查看测试覆盖率**

```bash
# 生成覆盖率报告后，可以在浏览器中打开
open htmlcov/index.html
```

### 6. **测试标记**

测试用例可以使用pytest标记进行分类：

```python
@pytest.mark.unit
def test_unit_function():
    pass

@pytest.mark.integration
def test_integration():
    pass

@pytest.mark.performance
def test_performance():
    pass

@pytest.mark.slow
def test_slow_function():
    pass
```

运行特定标记的测试：

```bash
pytest -m unit
pytest -m "not slow"  # 排除慢速测试
```

## 九、测试套件特点

1. **全面覆盖**: 包含单元测试、集成测试、功能测试和性能测试
2. **模块化设计**: 每个模块都有独立的测试文件
3. **丰富的测试夹具**: 提供各种测试数据和环境配置
4. **性能监控**: 包含内存使用和性能基准测试
5. **代码覆盖率**: 支持生成详细的覆盖率报告
6. **并行测试**: 支持并行运行测试以加快执行速度
7. **多种报告格式**: 支持控制台、HTML、XML等多种报告格式
8. **易于扩展**: 添加新测试非常容易
9. **与CI/CD集成**: 支持持续集成流程

这个测试套件确保了网络监控系统的代码质量、功能正确性和性能表现。
