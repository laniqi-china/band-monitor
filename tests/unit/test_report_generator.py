# tests/unit/test_report_generator.py
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
        output_dir = temp_dir / "reports"
        return ReportGenerator(output_dir)

    @pytest.fixture
    def sample_dataframe(self, sample_traffic_records):
        """创建示例DataFrame"""
        from dataclasses import asdict

        records_dict = [asdict(r) for r in sample_traffic_records]
        return pd.DataFrame(records_dict)

    def test_initialization(self, temp_dir):
        """测试初始化"""
        output_dir = temp_dir / "reports"
        generator = ReportGenerator(output_dir)

        assert generator.output_dir == output_dir
        assert output_dir.exists()  # 目录应该已创建

    def test_generate_daily_report_empty(self, report_generator):
        """测试生成空报告"""
        date_key = date(2024, 1, 1)
        empty_records = []

        result = report_generator.generate_daily_report(
            date_key, empty_records, include_csv=True, compress=False
        )

        # 应该返回空字典
        assert result == {}

    def test_generate_daily_report_with_data(
        self, report_generator, sample_traffic_records
    ):
        """测试生成有数据的报告"""
        date_key = date(2024, 1, 1)

        result = report_generator.generate_daily_report(
            date_key, sample_traffic_records, include_csv=True, compress=False
        )

        # 应该生成多个文件
        assert len(result) >= 3  # JSON, CSV, 汇总报告

        # 验证文件存在
        json_file = report_generator.output_dir / "report_20240101.json"
        csv_file = report_generator.output_dir / "report_20240101.csv"
        summary_file = report_generator.output_dir / "summary_20240101.json"

        assert json_file.exists()
        assert csv_file.exists()
        assert summary_file.exists()

        # 验证JSON文件内容
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        assert isinstance(json_data, list)
        assert len(json_data) == 3

        # 验证CSV文件内容
        df = pd.read_csv(csv_file)
        assert len(df) == 3
        assert "process_name" in df.columns
        assert "upload_bps" in df.columns

        # 验证汇总报告
        with open(summary_file, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

        assert "overview" in summary_data
        assert "process_summary" in summary_data
        assert "remote_summary" in summary_data

    def test_generate_daily_report_without_csv(
        self, report_generator, sample_traffic_records
    ):
        """测试不生成CSV的报告"""
        date_key = date(2024, 1, 1)

        result = report_generator.generate_daily_report(
            date_key, sample_traffic_records, include_csv=False, compress=False
        )

        # 应该不包含CSV文件
        csv_file = report_generator.output_dir / "report_20240101.csv"
        assert not csv_file.exists()

        # 应该包含JSON文件
        json_file = report_generator.output_dir / "report_20240101.json"
        assert json_file.exists()

    def test_save_detailed_report(self, report_generator, sample_dataframe):
        """测试保存详细报告"""
        date_str = "20240101"

        result = report_generator._save_detailed_report(date_str, sample_dataframe)

        # 应该返回多个文件路径
        assert "json" in result
        assert "csv" in result

        # 验证文件已创建
        json_file = result["json"]
        csv_file = result["csv"]

        assert json_file.exists()
        assert csv_file.exists()

        # 验证JSON文件内容
        with open(json_file, "r", encoding="utf-8") as f:
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
            "process_name",
            "upload_sum",
            "upload_mean",
            "upload_max",
            "upload_std",
            "download_sum",
            "download_mean",
            "download_max",
            "download_std",
            "unique_pids",
            "unique_remotes",
            "upload_pct",
            "download_pct",
        ]

        for col in expected_columns:
            assert col in summary.columns

        # 验证firefox的统计
        firefox_row = summary[summary["process_name"] == "firefox"].iloc[0]
        assert firefox_row["upload_sum"] == 150  # 100 + 50
        assert firefox_row["download_sum"] == 120  # 80 + 40
        assert firefox_row["unique_pids"] == 1

    def test_calculate_remote_summary(self, report_generator, sample_dataframe):
        """测试计算远程地址汇总"""
        summary = report_generator._calculate_remote_summary(sample_dataframe)

        assert isinstance(summary, pd.DataFrame)

        # 应该有3个远程地址
        assert len(summary) == 3

        # 验证列
        expected_columns = [
            "remote_address",
            "upload_sum",
            "upload_mean",
            "upload_max",
            "download_sum",
            "download_mean",
            "download_max",
            "unique_processes",
            "common_protocol",
            "is_ip",
        ]

        for col in expected_columns:
            assert col in summary.columns

        # 验证IP地址检测
        ip_rows = summary[summary["is_ip"] == True]
        assert len(ip_rows) == 3  # 所有地址都是IP

    def test_calculate_time_summary(self, report_generator, sample_dataframe):
        """测试计算时间汇总"""
        # 添加小时列
        sample_dataframe["hour"] = pd.to_datetime(sample_dataframe["timestamp"]).dt.hour

        summary = report_generator._calculate_time_summary(sample_dataframe)

        # 应该是字典
        assert isinstance(summary, dict)

        # 应该包含每小时汇总
        assert "hourly" in summary

        hourly = summary["hourly"]
        assert "upload_bps" in hourly
        assert "download_bps" in hourly
        assert "process_name" in hourly

    def test_get_top_items(self, report_generator, sample_dataframe):
        """测试获取排名前N的项目"""
        # 按进程名称获取上传流量前2
        top_items = report_generator._get_top_items(
            sample_dataframe, "process_name", "upload_bps", 2
        )

        assert isinstance(top_items, list)
        assert len(top_items) == 2

        # 验证排序
        assert top_items[0]["item"] == "chrome"  # 200 > 150
        assert top_items[1]["item"] == "firefox"

        # 使用自定义函数
        def total_traffic(group):
            return group["upload_bps"].sum() + group["download_bps"].sum()

        top_custom = report_generator._get_top_items(
            sample_dataframe, "process_name", total_traffic, 2
        )

        assert len(top_custom) == 2

    def test_is_ip_address(self, report_generator):
        """测试IP地址检测"""
        # 有效IP地址
        assert report_generator._is_ip_address("192.168.1.1") is True
        assert report_generator._is_ip_address("8.8.8.8") is True
        assert report_generator._is_ip_address("255.255.255.255") is True

        # 无效IP地址
        assert report_generator._is_ip_address("example.com") is False
        assert report_generator._is_ip_address("192.168.1.256") is False  # 超出范围
        assert report_generator._is_ip_address("192.168.1") is False  # 不完整
        assert report_generator._is_ip_address("") is False

    def test_generate_statistics_report(self, report_generator, sample_dataframe):
        """测试生成统计报告"""
        date_str = "20240101"

        result = report_generator._generate_statistics_report(
            date_str, sample_dataframe
        )

        # 应该包含统计报告文件路径
        assert "stats_json" in result

        stats_file = result["stats_json"]
        assert stats_file.exists()

        # 验证统计报告内容
        with open(stats_file, "r", encoding="utf-8") as f:
            stats_data = json.load(f)

        assert "date" in stats_data
        assert stats_data["date"] == date_str

        assert "traffic_statistics" in stats_data
        assert "connection_statistics" in stats_data
        assert "process_statistics" in stats_data

        # 验证流量统计
        traffic_stats = stats_data["traffic_statistics"]
        assert "upload" in traffic_stats
        assert "download" in traffic_stats

        # 验证上传流量总和
        assert traffic_stats["upload"]["total_bytes"] == 350  # 100+50+200

    def test_compress_reports(self, report_generator, sample_dataframe, temp_dir):
        """测试压缩报告"""
        date_str = "20240101"

        # 先创建一些报告文件
        files = []
        for i in range(3):
            file_path = report_generator.output_dir / f"test_{i}.txt"
            file_path.write_text(f"Test content {i}")
            files.append(file_path)

        # 压缩文件
        zip_file = report_generator._compress_reports(date_str, files)

        # 验证压缩文件已创建
        assert zip_file.exists()
        assert zip_file.suffix == ".zip"

        # 验证压缩文件大小
        assert zip_file.stat().st_size > 0

    def test_generate_summary_report(self, report_generator, sample_dataframe):
        """测试生成汇总报告"""
        date_str = "20240101"

        result = report_generator._generate_summary_report(date_str, sample_dataframe)

        # 应该包含多个文件
        assert "summary_json" in result
        assert "summary_csv" in result

        # 验证JSON汇总报告
        json_file = result["summary_json"]
        with open(json_file, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

        assert "overview" in summary_data
        assert "process_summary" in summary_data
        assert "remote_summary" in summary_data
        assert "time_summary" in summary_data
        assert "top_items" in summary_data

        # 验证概览数据
        overview = summary_data["overview"]
        assert overview["total_records"] == 3
        assert overview["unique_processes"] == 2
        assert overview["unique_remote_addresses"] == 3

        # 验证CSV汇总报告
        csv_file = result["summary_csv"]
        assert csv_file.exists()

        # 读取CSV并验证内容
        with open(csv_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 应该包含多个部分
        content = "".join(lines)
        assert "=== 概览 ===" in content
        assert "=== 进程汇总 ===" in content
        assert "=== 远程地址汇总 ===" in content
