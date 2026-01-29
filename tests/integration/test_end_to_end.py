# tests/integration/test_end_to_end.py
import json
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest
from src.main import NetworkMonitor


class TestEndToEnd:
    """端到端测试"""

    @pytest.fixture
    def setup_test_environment(self):
        """设置测试环境"""
        # 创建临时目录
        temp_dir = Path(tempfile.mkdtemp())

        # 创建目录结构
        log_dir = temp_dir / "logs"
        report_dir = temp_dir / "reports"
        archive_dir = temp_dir / "archive"

        log_dir.mkdir()
        report_dir.mkdir()
        archive_dir.mkdir()

        # 创建配置文件
        config = {
            "version": "1.0",
            "paths": {
                "log_dir": str(log_dir),
                "report_dir": str(report_dir),
                "archive_dir": str(archive_dir),
                "temp_dir": str(temp_dir / "temp"),
            },
            "email": {
                "smtp_server": "smtp.test.com",
                "smtp_port": 587,
                "use_ssl": False,
                "use_tls": True,
                "username": "test@test.com",
                "password": "test_password",
                "from_addr": "test@test.com",
                "to_addrs": ["recipient@test.com"],
                "cc_addrs": [],
                "subject_prefix": "TEST - 网络流量监控报告",
            },
            "processing": {
                "max_workers": 2,
                "batch_size": 100,
                "chunk_size": 1024,
                "keep_temp_files": False,
            },
            "reports": {
                "format": "json",
                "include_csv": True,
                "compress_reports": False,
                "generate_summary": True,
                "include_charts": False,
            },
            "archive": {
                "enabled": True,
                "compress_format": "zip",
                "keep_original": False,
                "retention_days": 7,
                "clean_old_archives": True,
            },
            "logging": {
                "level": "WARNING",  # 降低日志级别以减少输出
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file_size": "1MB",
                "backup_count": 2,
                "enable_console": False,
            },
        }

        config_file = temp_dir / "config.yaml"
        import yaml

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        yield {
            "temp_dir": temp_dir,
            "log_dir": log_dir,
            "report_dir": report_dir,
            "archive_dir": archive_dir,
            "config_file": config_file,
        }

        # 清理临时目录
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def create_sample_log_files(self, setup_test_environment):
        """创建示例日志文件"""
        log_dir = setup_test_environment["log_dir"]

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

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            files.append(file_path)

        return files

    def test_end_to_end_processing(
        self, setup_test_environment, create_sample_log_files
    ):
        """测试端到端处理流程"""
        config_file = setup_test_environment["config_file"]

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 生成报告
        monitor.generate_report()

        report_dir = setup_test_environment["report_dir"]

        # 验证报告文件
        report_files = list(report_dir.glob("*20240101*"))
        assert len(report_files) >= 3  # 至少JSON、CSV、汇总报告

        # 验证详细报告
        json_report = report_dir / "report_20240101.json"
        assert json_report.exists()

        # 验证报告内容
        with open(json_report, "r", encoding="utf-8") as f:
            report_data = json.load(f)

        assert isinstance(report_data, list)
        assert len(report_data) == 4  # 2个文件 * 2个连接

        # 验证汇总报告
        summary_report = report_dir / "summary_20240101.json"
        assert summary_report.exists()

        with open(summary_report, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

        assert "overview" in summary_data
        assert summary_data["overview"]["total_records"] == 4

        # 验证存档
        archive_dir = setup_test_environment["archive_dir"]
        archive_files = list(archive_dir.glob("*20240101*"))
        assert len(archive_files) >= 1  # 至少一个存档文件

        # 验证原始日志文件已删除（keep_original=False）
        for log_file in create_sample_log_files:
            assert not log_file.exists()

    def test_end_to_end_with_existing_report(
        self, setup_test_environment, create_sample_log_files
    ):
        """测试已存在报告时的端到端处理"""
        config_file = setup_test_environment["config_file"]
        report_dir = setup_test_environment["report_dir"]

        # 先创建一个报告文件
        existing_report = report_dir / "report_20240101.json"
        existing_report.parent.mkdir(parents=True, exist_ok=True)

        with open(existing_report, "w", encoding="utf-8") as f:
            json.dump([{"test": "existing"}], f)

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 生成报告
        monitor.generate_report()

        # 验证报告文件数量
        report_files = list(report_dir.glob("*20240101*"))

        # 应该只有我们创建的那个文件（跳过处理）
        # 注意：实际可能会有其他文件（如日志文件），但详细报告应该只有一个
        json_reports = [
            f
            for f in report_files
            if f.name.startswith("report_") and f.suffix == ".json"
        ]
        assert len(json_reports) == 1

        # 验证报告内容没有被覆盖
        with open(existing_report, "r", encoding="utf-8") as f:
            report_data = json.load(f)

        assert report_data == [{"test": "existing"}]

    def test_end_to_end_multiple_days(self, setup_test_environment):
        """测试多天端到端处理"""
        log_dir = setup_test_environment["log_dir"]
        config_file = setup_test_environment["config_file"]

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

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 生成报告
        monitor.generate_report()

        report_dir = setup_test_environment["report_dir"]

        # 验证两天的报告
        for day in range(1, 3):
            date_str = f"202401{day:02d}"
            json_report = report_dir / f"report_{date_str}.json"

            assert json_report.exists()

            with open(json_report, "r", encoding="utf-8") as f:
                report_data = json.load(f)

            assert len(report_data) == 1  # 每条记录

    def test_end_to_end_with_no_traffic(self, setup_test_environment):
        """测试无流量日志的端到端处理"""
        log_dir = setup_test_environment["log_dir"]
        config_file = setup_test_environment["config_file"]

        # 创建只包含NO TRAFFIC的日志文件
        test_date = date(2024, 1, 1)
        filename = f'bandwhich_{test_date.strftime("%Y%m%d")}_1200.log'
        file_path = log_dir / filename

        content = """Refreshing:
<NO TRAFFIC>

Refreshing:
<NO TRAFFIC>
"""

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 生成报告
        monitor.generate_report()

        report_dir = setup_test_environment["report_dir"]

        # 应该没有报告文件（无有效记录）
        report_files = list(report_dir.glob("*20240101*"))
        assert len(report_files) == 0

    def test_end_to_end_with_invalid_logs(self, setup_test_environment):
        """测试包含无效日志的端到端处理"""
        log_dir = setup_test_environment["log_dir"]
        config_file = setup_test_environment["config_file"]

        # 创建混合文件：一个有效，一个无效
        test_date = date(2024, 1, 1)

        # 有效文件
        valid_file = log_dir / f'bandwhich_{test_date.strftime("%Y%m%d")}_1200.log'
        valid_content = """Refreshing:
process: <12345> "test" up/down Bps: 100/80 connections: 1
connection: <12345> <eth0>:54321 => 192.168.1.1:443 (tcp) up/down Bps: 100/80 process: "test"
"""

        with open(valid_file, "w", encoding="utf-8") as f:
            f.write(valid_content)

        # 无效文件（错误文件名格式）
        invalid_file = log_dir / "invalid.log"
        invalid_content = """无效内容"""

        with open(invalid_file, "w", encoding="utf-8") as f:
            f.write(invalid_content)

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 生成报告（应该不抛出异常）
        monitor.generate_report()

        report_dir = setup_test_environment["report_dir"]

        # 应该只有有效文件的报告
        report_files = list(report_dir.glob("*20240101*"))
        assert len(report_files) >= 1

    def test_end_to_end_date_filter(self, setup_test_environment):
        """测试日期过滤的端到端处理"""
        log_dir = setup_test_environment["log_dir"]
        config_file = setup_test_environment["config_file"]

        # 创建两天的日志文件
        for day in range(1, 4):  # 1-3号
            test_date = date(2024, 1, day)
            filename = f'bandwhich_{test_date.strftime("%Y%m%d")}_1200.log'
            file_path = log_dir / filename

            content = f"""Refreshing:
process: <12345> "test" up/down Bps: 100/80 connections: 1
connection: <12345> <eth0>:54321 => 192.168.1.{day}:443 (tcp) up/down Bps: 100/80 process: "test"
"""

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        # 创建监控实例
        monitor = NetworkMonitor(str(config_file))

        # 只处理1号和3号
        monitor.generate_report(date_filter="2024010[13]")

        report_dir = setup_test_environment["report_dir"]

        # 验证只有1号和3号的报告
        for day in [1, 2, 3]:
            date_str = f"202401{day:02d}"
            json_report = report_dir / f"report_{date_str}.json"

            if day in [1, 3]:
                assert json_report.exists()
            else:
                assert not json_report.exists()
