# tests/unit/test_log_parser.py
import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from src.log_parser import LogParser, ProcessRecord, ConnectionRecord, TrafficRecord


class TestProcessRecord:
    """测试进程记录类"""

    def test_initialization(self):
        """测试初始化"""
        record = ProcessRecord(
            pid=12345,
            name="test_process",
            upload_bps=100,
            download_bps=200,
            connections=3,
        )

        assert record.pid == 12345
        assert record.name == "test_process"
        assert record.upload_bps == 100
        assert record.download_bps == 200
        assert record.connections == 3


class TestConnectionRecord:
    """测试连接记录类"""

    def test_initialization(self):
        """测试初始化"""
        record = ConnectionRecord(
            pid=12345,
            local_interface="eth0",
            local_port=54321,
            remote_address="192.168.1.1",
            remote_port=80,
            protocol="tcp",
            upload_bps=50,
            download_bps=100,
            process_name="test_process",
        )

        assert record.pid == 12345
        assert record.local_interface == "eth0"
        assert record.local_port == 54321
        assert record.remote_address == "192.168.1.1"
        assert record.remote_port == 80
        assert record.protocol == "tcp"
        assert record.upload_bps == 50
        assert record.download_bps == 100
        assert record.process_name == "test_process"


class TestTrafficRecord:
    """测试流量记录类"""

    def test_initialization(self):
        """测试初始化"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        record = TrafficRecord(
            timestamp=timestamp,
            pid=12345,
            process_name="firefox",
            local_interface="eth0",
            local_port=54321,
            remote_address="8.8.8.8",
            remote_port=443,
            protocol="tcp",
            upload_bps=100,
            download_bps=200,
            source_file="test.log",
        )

        assert record.timestamp == timestamp
        assert record.pid == 12345
        assert record.process_name == "firefox"
        assert record.local_interface == "eth0"
        assert record.local_port == 54321
        assert record.remote_address == "8.8.8.8"
        assert record.remote_port == 443
        assert record.protocol == "tcp"
        assert record.upload_bps == 100
        assert record.download_bps == 200
        assert record.source_file == "test.log"


class TestLogParser:
    """测试日志解析器"""

    def test_parse_process_line_valid(self):
        """测试解析有效的进程行"""
        parser = LogParser()

        line = 'process: <12345> "firefox" up/down Bps: 100/200 connections: 3'
        result = parser._parse_process_line(line)

        assert result is not None
        assert result.pid == 12345
        assert result.name == "firefox"
        assert result.upload_bps == 100
        assert result.download_bps == 200
        assert result.connections == 3

    def test_parse_process_line_invalid(self):
        """测试解析无效的进程行"""
        parser = LogParser()

        # 无效格式
        line = "process: invalid format"
        result = parser._parse_process_line(line)

        assert result is None

        # 空行
        line = ""
        result = parser._parse_process_line(line)

        assert result is None

    def test_parse_connection_line_valid(self):
        """测试解析有效的连接行"""
        parser = LogParser()

        line = 'connection: <12345> <eth0>:54321 => 8.8.8.8:443 (tcp) up/down Bps: 100/200 process: "firefox"'
        result = parser._parse_connection_line(line)

        assert result is not None
        assert result.pid == 12345
        assert result.local_interface == "eth0"
        assert result.local_port == 54321
        assert result.remote_address == "8.8.8.8"
        assert result.remote_port == 443
        assert result.protocol == "tcp"
        assert result.upload_bps == 100
        assert result.download_bps == 200
        assert result.process_name == "firefox"

    def test_parse_connection_line_with_domain(self):
        """测试解析包含域名的连接行"""
        parser = LogParser()

        line = 'connection: <12345> <eth0>:54321 => google.com:443 (tcp) up/down Bps: 100/200 process: "firefox"'
        result = parser._parse_connection_line(line)

        assert result is not None
        assert result.remote_address == "google.com"
        assert result.remote_port == 443

    def test_parse_connection_line_invalid(self):
        """测试解析无效的连接行"""
        parser = LogParser()

        # 无效格式
        line = "connection: invalid format"
        result = parser._parse_connection_line(line)

        assert result is None

        # 缺少字段
        line = "connection: <12345> <eth0>:54321 => 8.8.8.8:443 (tcp)"
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
        records = parser._parse_refresh_block(block, timestamp, "test.log")

        # 应该解析出两条连接记录
        assert len(records) == 2

        # 验证第一条记录
        record1 = records[0]
        assert record1.timestamp == timestamp
        assert record1.pid == 12345
        assert record1.process_name == "firefox"
        assert record1.local_interface == "eth0"
        assert record1.local_port == 54321
        assert record1.remote_address == "192.168.1.1"
        assert record1.remote_port == 443
        assert record1.protocol == "tcp"
        assert record1.upload_bps == 100
        assert record1.download_bps == 80

        # 验证第二条记录
        record2 = records[1]
        assert record2.protocol == "udp"
        assert record2.remote_address == "8.8.8.8"
        assert record2.remote_port == 53

    def test_parse_refresh_block_no_traffic(self):
        """测试解析无流量块"""
        parser = LogParser()

        block = "<NO TRAFFIC>"

        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        records = parser._parse_refresh_block(block, timestamp, "test.log")

        # 应该返回空列表
        assert len(records) == 0

    def test_parse_refresh_block_unknown_process(self):
        """测试解析包含未知进程的块"""
        parser = LogParser()

        block = """
connection: <12345> <eth0>:54321 => 8.8.8.8:53 (udp) up/down Bps: 50/40 process: "<UNKNOWN>"
"""

        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        records = parser._parse_refresh_block(block, timestamp, "test.log")

        # 应该解析出一条记录
        assert len(records) == 1

        # 进程名称应该是<UNKNOWN>
        assert records[0].process_name == "<UNKNOWN>"

    def test_parse_file(self, temp_dir, sample_log_data):
        """测试解析完整文件"""
        parser = LogParser()

        # 创建测试文件
        file_path = temp_dir / "test.log"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sample_log_data)

        # 模拟LogFileInfo
        from src.file_scanner import LogFileInfo

        file_info = LogFileInfo(
            path=file_path,
            date=datetime(2024, 1, 1).date(),
            base_time=datetime(2024, 1, 1, 12, 0, 0),
            size=len(sample_log_data),
            md5="test",
            modified_time=datetime.now(),
        )

        records = parser.parse_file(file_info)

        # 应该解析出3条记录
        assert len(records) == 3

        # 验证记录
        assert records[0].process_name == "firefox"
        assert records[0].remote_address == "192.168.1.100"
        assert records[0].upload_bps == 100

        assert records[1].process_name == "firefox"
        assert records[1].remote_address == "8.8.8.8"
        assert records[1].protocol == "udp"

        assert records[2].process_name == "chrome"
        assert records[2].remote_address == "10.0.0.1"

    def test_parse_file_empty(self, temp_dir):
        """测试解析空文件"""
        parser = LogParser()

        # 创建空文件
        file_path = temp_dir / "empty.log"
        file_path.touch()

        from src.file_scanner import LogFileInfo

        file_info = LogFileInfo(
            path=file_path,
            date=datetime(2024, 1, 1).date(),
            base_time=datetime(2024, 1, 1, 12, 0, 0),
            size=0,
            md5="test",
            modified_time=datetime.now(),
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

        file_path = temp_dir / "test.log"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        from src.file_scanner import LogFileInfo

        file_info = LogFileInfo(
            path=file_path,
            date=datetime(2024, 1, 1).date(),
            base_time=datetime(2024, 1, 1, 12, 0, 0),
            size=len(content),
            md5="test",
            modified_time=datetime.now(),
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
        assert record1["pid"] == 12345
        assert record1["process_name"] == "firefox"
        assert record1["upload_bps"] == 100
        assert "timestamp" in record1  # 应该被转换为字符串

    def test_save_to_json_file(self, temp_dir, sample_traffic_records):
        """测试保存记录到JSON文件"""
        parser = LogParser()

        output_path = temp_dir / "output.json"
        parser.save_to_json_file(sample_traffic_records, output_path)

        # 验证文件已创建
        assert output_path.exists()

        # 验证文件内容
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 应该是有效的JSON数组
        parsed = json.loads(content)
        assert isinstance(parsed, list)
        assert len(parsed) == 3

        # 验证记录顺序
        assert parsed[0]["pid"] == 12345
        assert parsed[1]["pid"] == 12345
        assert parsed[2]["pid"] == 12346

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

        file_path = temp_dir / "test.log"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        with open(file_path, "r", encoding="utf-8") as f:
            blocks = list(parser._read_refresh_blocks(f))

        # 应该读取到3个块
        assert len(blocks) == 3

        # 验证块内容
        assert blocks[0].strip() == "Before first refresh"
        assert blocks[1].strip() == "First block"
        assert blocks[2].strip() == "Second block\nThird block\nAfter last refresh"
