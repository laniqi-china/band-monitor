# tests/functional/test_report_generation.py
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
        report_dir = temp_dir / "reports"
        generator = ReportGenerator(report_dir)

        # 创建测试记录
        records = [
            TrafficRecord(
                timestamp=datetime(2024, 1, 1, 10 + i, 0, 0),
                pid=10000 + i,
                process_name=f"process_{i % 3}",
                local_interface="eth0",
                local_port=50000 + i,
                remote_address=f"192.168.1.{i + 1}",
                remote_port=443 if i % 2 == 0 else 80,
                protocol="tcp",
                upload_bps=100 * (i + 1),
                download_bps=50 * (i + 1),
                source_file=f"test_{i}.log",
            )
            for i in range(10)  # 10条记录
        ]

        yield {
            "temp_dir": temp_dir,
            "generator": generator,
            "records": records,
            "report_date": date(2024, 1, 1),
        }

        # 清理
        shutil.rmtree(temp_dir)

    def test_large_dataset_processing(self, setup_test_data):
        """测试大数据集处理"""
        generator = setup_test_data["generator"]
        report_date = setup_test_data["report_date"]
        records = setup_test_data["records"]

        # 生成报告
        report_files = generator.generate_daily_report(
            report_date, records, include_csv=True, compress=False
        )

        # 验证所有报告文件
        assert len(report_files) >= 4  # JSON, CSV, 汇总, 统计

        # 验证JSON报告
        json_file = generator.output_dir / "report_20240101.json"
        assert json_file.exists()

        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        assert len(json_data) == 10

        # 验证CSV报告
        csv_file = generator.output_dir / "report_20240101.csv"
        assert csv_file.exists()

        df = pd.read_csv(csv_file)
        assert len(df) == 10
        assert df["upload_bps"].sum() == sum(r.upload_bps for r in records)

    def test_report_with_different_processes(self, setup_test_data):
        """测试不同进程的报告"""
        generator = setup_test_data["generator"]

        # 转换记录为DataFrame
        from dataclasses import asdict

        records_dict = [asdict(r) for r in setup_test_data["records"]]
        df = pd.DataFrame(records_dict)

        # 测试进程汇总
        process_summary = generator._calculate_process_summary(df)

        # 应该有3个不同的进程
        assert len(process_summary) == 3

        # 验证进程名称
        process_names = set(process_summary["process_name"])
        assert process_names == {"process_0", "process_1", "process_2"}

        # 验证总流量
        total_upload = process_summary["upload_sum"].sum()
        expected_upload = sum(r.upload_bps for r in setup_test_data["records"])
        assert total_upload == expected_upload

    def test_report_with_different_remotes(self, setup_test_data):
        """测试不同远程地址的报告"""
        generator = setup_test_data["generator"]

        from dataclasses import asdict

        records_dict = [asdict(r) for r in setup_test_data["records"]]
        df = pd.DataFrame(records_dict)

        # 测试远程地址汇总
        remote_summary = generator._calculate_remote_summary(df)

        # 应该有10个不同的远程地址
        assert len(remote_summary) == 10

        # 验证所有地址都是IP
        assert remote_summary["is_ip"].all()

    def test_time_distribution_analysis(self, setup_test_data):
        """测试时间分布分析"""
        generator = setup_test_data["generator"]

        from dataclasses import asdict

        records_dict = [asdict(r) for r in setup_test_data["records"]]
        df = pd.DataFrame(records_dict)

        # 添加小时列
        df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour

        # 测试时间汇总
        time_summary = generator._calculate_time_summary(df)

        assert "hourly" in time_summary

        hourly = time_summary["hourly"]
        assert "upload_bps" in hourly

        # 验证小时分布
        upload_by_hour = hourly["upload_bps"]

        # 应该有10-19小时的数据
        for hour in range(10, 20):
            if hour in upload_by_hour:
                assert upload_by_hour[hour] > 0

    def test_top_items_calculation(self, setup_test_data):
        """测试顶级项目计算"""
        generator = setup_test_data["generator"]

        from dataclasses import asdict

        records_dict = [asdict(r) for r in setup_test_data["records"]]
        df = pd.DataFrame(records_dict)

        # 测试按进程获取顶级项目
        top_processes = generator._get_top_items(df, "process_name", "upload_bps", 2)

        assert len(top_processes) == 2

        # 应该按上传流量排序
        values = [item["value"] for item in top_processes]
        assert values == sorted(values, reverse=True)

        # 测试按远程地址获取顶级项目
        top_remotes = generator._get_top_items(df, "remote_address", "download_bps", 3)

        assert len(top_remotes) == 3

        # 测试计数
        top_ports = generator._get_top_items(df, "local_port", "count", 5)

        assert len(top_ports) == 5
        # 每个端口应该只有1条记录
        for item in top_ports:
            assert item["value"] == 1.0

    def test_statistics_report_generation(self, setup_test_data):
        """测试统计报告生成"""
        generator = setup_test_data["generator"]

        from dataclasses import asdict

        records_dict = [asdict(r) for r in setup_test_data["records"]]
        df = pd.DataFrame(records_dict)

        date_str = "20240101"

        # 生成统计报告
        result = generator._generate_statistics_report(date_str, df)

        assert "stats_json" in result

        stats_file = result["stats_json"]
        assert stats_file.exists()

        # 验证统计报告内容
        with open(stats_file, "r", encoding="utf-8") as f:
            stats_data = json.load(f)

        # 验证基本结构
        assert "traffic_statistics" in stats_data
        assert "connection_statistics" in stats_data
        assert "process_statistics" in stats_data

        # 验证流量统计
        traffic_stats = stats_data["traffic_statistics"]

        # 验证上传统计
        upload_stats = traffic_stats["upload"]
        assert upload_stats["total_bytes"] == sum(
            r.upload_bps for r in setup_test_data["records"]
        )
        assert "average_bps" in upload_stats
        assert "max_bps" in upload_stats
        assert "percentiles" in upload_stats

        # 验证连接统计
        conn_stats = stats_data["connection_statistics"]
        assert conn_stats["total_connections"] == 10
        assert conn_stats["unique_ports"] == 10

        # 验证进程统计
        proc_stats = stats_data["process_statistics"]
        assert proc_stats["total_processes"] == 3

    def test_report_compression(self, setup_test_data):
        """测试报告压缩"""
        generator = setup_test_data["generator"]
        temp_dir = setup_test_data["temp_dir"]

        # 创建一些测试文件
        test_files = []
        for i in range(3):
            file_path = temp_dir / f"test_{i}.txt"
            file_path.write_text("测试内容 " * 100)  # 创建大文件
            test_files.append(file_path)

        date_str = "20240101"

        # 压缩文件
        zip_file = generator._compress_reports(date_str, test_files)

        assert zip_file.exists()
        assert zip_file.suffix == ".zip"

        # 验证压缩文件大小
        original_size = sum(f.stat().st_size for f in test_files)
        compressed_size = zip_file.stat().st_size

        # 压缩文件应该更小
        assert compressed_size < original_size

        # 验证压缩文件内容
        import zipfile

        with zipfile.ZipFile(zip_file, "r") as zipf:
            file_list = zipf.namelist()
            assert len(file_list) == 3
            assert all(f.name in file_list for f in test_files)
