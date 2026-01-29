# tests/unit/test_file_scanner.py
import pytest
from datetime import datetime, date
from pathlib import Path
import tempfile

from src.file_scanner import FileScanner, LogFileInfo


class TestLogFileInfo:
    """测试日志文件信息类"""

    def test_initialization(self, temp_dir):
        """测试初始化"""
        file_path = temp_dir / "test.log"
        file_path.touch()

        file_info = LogFileInfo(
            path=file_path,
            date=date(2024, 1, 1),
            base_time=datetime(2024, 1, 1, 12, 0, 0),
            size=1024,
            md5="test_md5",
            modified_time=datetime.now(),
        )

        assert file_info.path == file_path
        assert file_info.date == date(2024, 1, 1)
        assert file_info.size == 1024
        assert file_info.md5 == "test_md5"

    def test_str_representation(self, temp_dir):
        """测试字符串表示"""
        file_path = temp_dir / "test.log"
        file_path.touch()

        file_info = LogFileInfo(
            path=file_path,
            date=date(2024, 1, 1),
            base_time=datetime(2024, 1, 1, 12, 0, 0),
            size=2048,
            md5="test",
            modified_time=datetime.now(),
        )

        assert "test.log" in str(file_info)
        assert "2.0KB" in str(file_info)


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
        log_dir = temp_dir / "logs"
        log_dir.mkdir()

        # 创建不同日期的文件
        files = [
            "bandwhich_20240101_1200.log",
            "bandwhich_20240101_1300.log",
            "bandwhich_20240102_1200.log",
            "bandwhich_20240102_1300.log",
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
        log_dir = temp_dir / "logs"
        log_dir.mkdir()

        # 创建无效文件名的文件
        invalid_files = [
            "invalid.log",
            "bandwhich_20241301_1200.log",  # 无效月份
            "bandwhich_20240101_2500.log",  # 无效时间
            "bandwhich.log",
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
        log_dir = temp_dir / "logs"
        log_dir.mkdir()

        # 创建有效文件
        file_path = log_dir / "bandwhich_20240101_1200.log"
        file_path.touch()

        # 写入一些内容
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("test content")

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
        log_dir = temp_dir / "logs"
        log_dir.mkdir()

        # 创建无效文件名的文件
        file_path = log_dir / "invalid_filename.log"
        file_path.touch()

        scanner = FileScanner(log_dir)
        file_info = scanner._analyze_file(file_path)

        # 应该返回None
        assert file_info is None

    def test_calculate_md5(self, temp_dir):
        """测试计算MD5"""
        file_path = temp_dir / "test.txt"

        # 写入固定内容
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("Hello, World!")

        scanner = FileScanner(temp_dir)
        md5_hash = scanner._calculate_md5(file_path)

        # 验证MD5哈希
        assert len(md5_hash) == 32
        assert md5_hash == "65a8e27d8879283831b664bd8b7f0ad4"  # "Hello, World!"的MD5

    def test_check_report_exists(self, temp_dir):
        """测试检查报告是否存在"""
        report_dir = temp_dir / "reports"
        report_dir.mkdir()

        scanner = FileScanner(temp_dir)

        # 报告不存在的情况
        test_date = date(2024, 1, 1)
        exists = scanner.check_report_exists(test_date, report_dir)
        assert exists is False

        # 创建报告文件
        report_file = report_dir / "report_20240101.json"
        report_file.touch()

        # 报告应该存在
        exists = scanner.check_report_exists(test_date, report_dir)
        assert exists is True

        # 测试其他模式
        report_file2 = report_dir / "summary_20240101.json"
        report_file2.touch()

        exists = scanner.check_report_exists(test_date, report_dir)
        assert exists is True

    def test_scan_with_subdirectories(self, temp_dir):
        """测试扫描包含子目录的情况"""
        log_dir = temp_dir / "logs"
        log_dir.mkdir()

        # 在子目录中创建文件（应该被忽略）
        subdir = log_dir / "subdir"
        subdir.mkdir()
        subfile = subdir / "bandwhich_20240101_1200.log"
        subfile.touch()

        # 在主目录中创建文件
        mainfile = log_dir / "bandwhich_20240102_1200.log"
        mainfile.touch()

        scanner = FileScanner(log_dir)
        result = scanner.scan_files()

        # 应该只找到主目录中的文件
        assert len(result) == 1
        assert date(2024, 1, 2) in result

    def test_file_sorting(self, temp_dir):
        """测试文件排序"""
        log_dir = temp_dir / "logs"
        log_dir.mkdir()

        # 创建不同时间的文件
        files = [
            "bandwhich_20240101_1400.log",
            "bandwhich_20240101_1200.log",
            "bandwhich_20240101_1300.log",
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
