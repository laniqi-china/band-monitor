# tests/performance/test_scalability.py
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
        log_file = temp_dir / "large.log"

        with open(log_file, "w", encoding="utf-8") as f:
            # 写入1000个刷新块
            for block_idx in range(1000):
                f.write("Refreshing:\n")

                # 每个块有10个连接
                for conn_idx in range(10):
                    pid = 10000 + (block_idx * 10 + conn_idx) % 100
                    process_name = f"process_{(block_idx + conn_idx) % 5}"
                    remote_ip = f"192.168.{(block_idx // 256) % 256}.{conn_idx + 1}"

                    f.write(
                        f'process: <{pid}> "{process_name}" up/down Bps: 100/50 connections: 1\n'
                    )
                    f.write(
                        f'connection: <{pid}> <eth0>:{50000 + conn_idx} => {remote_ip}:443 (tcp) up/down Bps: 100/50 process: "{process_name}"\n'
                    )
                    f.write(
                        f"remote_address: <{pid}> {remote_ip} up/down Bps: 100/50 connections: 1\n"
                    )

                f.write("\n")

        yield {
            "temp_dir": temp_dir,
            "log_file": log_file,
            "expected_records": 1000 * 10,  # 1000块 * 10连接/块
        }

        # 清理
        import shutil

        shutil.rmtree(temp_dir)

    def test_parser_performance(self, create_large_dataset):
        """测试解析器性能"""
        log_file = create_large_dataset["log_file"]
        expected_records = create_large_dataset["expected_records"]

        parser = LogParser()

        # 测量解析时间
        start_time = time.time()

        from src.file_scanner import LogFileInfo

        file_info = LogFileInfo(
            path=log_file,
            date=date.today(),
            base_time=datetime.now(),
            size=log_file.stat().st_size,
            md5="test",
            modified_time=datetime.now(),
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
        assert (
            records_per_second > 100
        ), f"解析速度太慢: {records_per_second:.2f} 记录/秒"

    def test_parser_memory_usage(self, create_large_dataset):
        """测试解析器内存使用"""
        log_file = create_large_dataset["log_file"]

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
            md5="test",
            modified_time=datetime.now(),
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
        assert (
            memory_increase / len(records) < 10
        ), f"每记录内存使用过高: {memory_increase / len(records) * 1024:.2f} KB"

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
                "time": elapsed_time,
                "items_per_second": items_per_second,
                "speedup": results[1]["time"] / elapsed_time if workers > 1 else 1.0,
            }

            print(f"\n工作线程数: {workers}")
            print(f"总时间: {elapsed_time:.2f} 秒")
            print(f"处理速度: {items_per_second:.2f} 项/秒")
            print(f"加速比: {results[workers]['speedup']:.2f}x")

        # 验证并行加速（允许一些开销）
        assert (
            results[4]["speedup"] > 2.0
        ), f"4线程加速不足: {results[4]['speedup']:.2f}x"

    def test_report_generation_performance(self, create_large_dataset):
        """测试报告生成性能"""
        temp_dir = create_large_dataset["temp_dir"]

        # 创建报告生成器
        report_dir = temp_dir / "reports"
        generator = ReportGenerator(report_dir)

        # 创建大量记录
        records = []
        for i in range(10000):
            records.append(
                type(
                    "Record",
                    (),
                    {
                        "timestamp": datetime.now() + timedelta(seconds=i),
                        "pid": 10000 + i % 100,
                        "process_name": f"process_{i % 10}",
                        "local_interface": "eth0",
                        "local_port": 50000 + i % 1000,
                        "remote_address": f"192.168.{i // 256 % 256}.{i % 256 + 1}",
                        "remote_port": 443 if i % 2 == 0 else 80,
                        "protocol": "tcp",
                        "upload_bps": 100 + i % 900,
                        "download_bps": 50 + i % 450,
                        "source_file": f"test_{i // 1000}.log",
                    },
                )
            )

        # 测量报告生成时间
        start_time = time.time()

        report_date = date.today()
        report_files = generator.generate_daily_report(
            report_date, records, include_csv=True, compress=False
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
        assert (
            records_per_second > 100
        ), f"报告生成速度太慢: {records_per_second:.2f} 记录/秒"

    def test_concurrent_file_processing(self, create_large_dataset):
        """测试并发文件处理"""
        temp_dir = create_large_dataset["temp_dir"]

        # 创建多个日志文件
        file_count = 10
        files = []

        for i in range(file_count):
            file_path = temp_dir / f"log_{i}.log"

            with open(file_path, "w", encoding="utf-8") as f:
                # 每个文件100个刷新块，每个块5个连接
                for block_idx in range(100):
                    f.write("Refreshing:\n")

                    for conn_idx in range(5):
                        pid = 10000 + i * 100 + conn_idx
                        process_name = f"process_{i % 5}"

                        f.write(
                            f'process: <{pid}> "{process_name}" up/down Bps: 100/50 connections: 1\n'
                        )
                        f.write(
                            f'connection: <{pid}> <eth0>:{50000 + conn_idx} => 192.168.{i}.{conn_idx + 1}:443 (tcp) up/down Bps: 100/50 process: "{process_name}"\n'
                        )

                    f.write("\n")

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
                md5="test",
                modified_time=datetime.now(),
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
        assert (
            files_per_second > 0.5
        ), f"文件处理速度太慢: {files_per_second:.2f} 文件/秒"
