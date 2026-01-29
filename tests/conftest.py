# tests/conftest.py
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
