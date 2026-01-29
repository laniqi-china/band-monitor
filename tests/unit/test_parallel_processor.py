# tests/unit/test_parallel_processor.py
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
                file_path = Path(f"test_{date_key}_{hour}.log")
                file_info = LogFileInfo(
                    path=file_path,
                    date=date_key,
                    base_time=datetime(2024, 1, day, 10 + hour, 0, 0),
                    size=1024,
                    md5="test",
                    modified_time=datetime.now(),
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
            return {"date": date_key, "files_count": len(files), "processed": True}

        # 处理日志
        results = parallel_processor.process_daily_logs(
            sample_date_files, mock_process_func
        )

        # 验证结果
        assert len(results) == 2  # 两个日期

        for date_key, result in results.items():
            assert result["date"] == date_key
            assert result["files_count"] == 2
            assert result["processed"] is True

        # 验证内部状态
        assert len(parallel_processor.get_results()) == 2
        assert len(parallel_processor.get_errors()) == 0

    def test_process_daily_logs_with_errors(
        self, parallel_processor, sample_date_files
    ):
        """测试处理每日日志时出现错误"""

        # 模拟处理函数，第二个日期抛出异常
        def mock_process_func(date_key, files):
            if date_key == date(2024, 1, 2):
                raise Exception("处理失败")

            return {"date": date_key, "files_count": len(files), "processed": True}

        # 处理日志
        results = parallel_processor.process_daily_logs(
            sample_date_files, mock_process_func
        )

        # 验证结果
        assert len(results) == 1  # 只有一个成功
        assert date(2024, 1, 1) in results

        # 验证错误
        errors = parallel_processor.get_errors()
        assert len(errors) == 1
        assert date(2024, 1, 2) in errors
        assert "处理失败" in errors[date(2024, 1, 2)]

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
                raise Exception("处理失败")
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
            Mock(spec=LogFileInfo, path=Path("test1.log")),
            Mock(spec=LogFileInfo, path=Path("test2.log")),
        ]

        def mock_process_func(date_key, files):
            return f"处理了{len(files)}个文件"

        result = parallel_processor._process_single_date(
            date_key, files, mock_process_func
        )

        assert result == "处理了2个文件"

    def test_process_single_date_exception(self, parallel_processor):
        """测试处理单个日期时抛出异常"""
        from datetime import date

        date_key = date(2024, 1, 1)
        files = []

        def mock_process_func(date_key, files):
            raise Exception("测试异常")

        with pytest.raises(Exception, match="测试异常"):
            parallel_processor._process_single_date(date_key, files, mock_process_func)

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
            date(2024, 1, 1): "结果1",
            date(2024, 1, 2): "结果2",
        }

        parallel_processor._errors = {date(2024, 1, 3): "错误1"}

        # 验证获取结果
        results = parallel_processor.get_results()
        assert len(results) == 2
        assert results[date(2024, 1, 1)] == "结果1"

        # 验证获取错误
        errors = parallel_processor.get_errors()
        assert len(errors) == 1
        assert errors[date(2024, 1, 3)] == "错误1"


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
            return "结果1"

        def stage2(context):
            return "结果2"

        pipeline.add_stage("stage1", stage1)
        pipeline.add_stage("stage2", stage2, depends_on=["stage1"])

        # 验证阶段
        assert len(pipeline.stages) == 2

        stage1_info = pipeline.stages[0]
        assert stage1_info["name"] == "stage1"
        assert stage1_info["func"] == stage1
        assert stage1_info["depends_on"] == []

        stage2_info = pipeline.stages[1]
        assert stage2_info["name"] == "stage2"
        assert stage2_info["depends_on"] == ["stage1"]

    def test_run_linear_pipeline(self):
        """测试运行线性管道"""
        pipeline = ProcessingPipeline()

        results = []

        def stage1(context):
            results.append("stage1")
            return "结果1"

        def stage2(context):
            results.append("stage2")
            return "结果2"

        def stage3(context):
            results.append("stage3")
            return "结果3"

        pipeline.add_stage("stage1", stage1)
        pipeline.add_stage("stage2", stage2)
        pipeline.add_stage("stage3", stage3)

        context = pipeline.run()

        # 验证执行顺序
        assert results == ["stage1", "stage2", "stage3"]

        # 验证上下文
        assert context["stage1"] == "结果1"
        assert context["stage2"] == "结果2"
        assert context["stage3"] == "结果3"

    def test_run_dependent_pipeline(self):
        """测试运行依赖管道"""
        pipeline = ProcessingPipeline()

        execution_order = []

        def stage_a(context):
            execution_order.append("A")
            return "A"

        def stage_b(context):
            execution_order.append("B")
            return "B"

        def stage_c(context):
            execution_order.append("C")
            # 可以访问之前的阶段结果
            return context["stage_a"] + context["stage_b"] + "C"

        # 添加有依赖关系的阶段
        pipeline.add_stage("stage_a", stage_a)
        pipeline.add_stage("stage_b", stage_b)
        pipeline.add_stage("stage_c", stage_c, depends_on=["stage_a", "stage_b"])

        context = pipeline.run()

        # 验证C在A和B之后执行
        assert "C" in execution_order
        c_index = execution_order.index("C")
        assert "A" in execution_order[:c_index]
        assert "B" in execution_order[:c_index]

        # 验证C的结果使用了A和B的结果
        assert context["stage_c"] == "ABC"

    def test_run_with_initial_context(self):
        """测试运行带有初始上下文的管道"""
        pipeline = ProcessingPipeline()

        def stage1(context):
            return context["input"] * 2

        def stage2(context):
            return context["stage1"] + 1

        pipeline.add_stage("stage1", stage1)
        pipeline.add_stage("stage2", stage2, depends_on=["stage1"])

        initial_context = {"input": 5}
        context = pipeline.run(initial_context)

        # 验证结果
        assert context["input"] == 5  # 原始输入
        assert context["stage1"] == 10  # 5 * 2
        assert context["stage2"] == 11  # 10 + 1

    def test_run_with_exception(self):
        """测试运行管道时出现异常"""
        pipeline = ProcessingPipeline()

        def stage1(context):
            return "正常"

        def stage2(context):
            raise Exception("阶段2失败")

        def stage3(context):
            return "不应该执行"

        pipeline.add_stage("stage1", stage1)
        pipeline.add_stage("stage2", stage2)
        pipeline.add_stage("stage3", stage3)

        # 应该抛出异常
        with pytest.raises(Exception, match="阶段2失败"):
            pipeline.run()

        # 验证stage3没有执行
        assert "stage3" not in pipeline.context

    def test_run_with_circular_dependency(self):
        """测试运行带有循环依赖的管道"""
        pipeline = ProcessingPipeline()

        def stage1(context):
            return "结果1"

        def stage2(context):
            return "结果2"

        # 创建循环依赖
        pipeline.add_stage("stage1", stage1, depends_on=["stage2"])
        pipeline.add_stage("stage2", stage2, depends_on=["stage1"])

        # 应该无法运行（无限循环）
        with pytest.raises(Exception):
            pipeline.run()

    def test_chaining(self):
        """测试方法链"""
        pipeline = ProcessingPipeline()

        result = (
            pipeline.add_stage("stage1", lambda ctx: 1)
            .add_stage("stage2", lambda ctx: 2)
            .add_stage("stage3", lambda ctx: 3)
            .run()
        )

        # 验证链式调用和结果
        assert result["stage1"] == 1
        assert result["stage2"] == 2
        assert result["stage3"] == 3

    def test_complex_pipeline(self):
        """测试复杂管道"""
        pipeline = ProcessingPipeline()

        # 定义阶段
        def load_data(context):
            return [1, 2, 3, 4, 5]

        def filter_even(context):
            data = context["load_data"]
            return [x for x in data if x % 2 == 0]

        def filter_odd(context):
            data = context["load_data"]
            return [x for x in data if x % 2 == 1]

        def sum_even(context):
            even = context["filter_even"]
            return sum(even)

        def sum_odd(context):
            odd = context["filter_odd"]
            return sum(odd)

        def total_sum(context):
            return context["sum_even"] + context["sum_odd"]

        # 添加阶段
        pipeline.add_stage("load_data", load_data)
        pipeline.add_stage("filter_even", filter_even, depends_on=["load_data"])
        pipeline.add_stage("filter_odd", filter_odd, depends_on=["load_data"])
        pipeline.add_stage("sum_even", sum_even, depends_on=["filter_even"])
        pipeline.add_stage("sum_odd", sum_odd, depends_on=["filter_odd"])
        pipeline.add_stage("total_sum", total_sum, depends_on=["sum_even", "sum_odd"])

        # 运行管道
        context = pipeline.run()

        # 验证结果
        assert context["load_data"] == [1, 2, 3, 4, 5]
        assert context["filter_even"] == [2, 4]
        assert context["filter_odd"] == [1, 3, 5]
        assert context["sum_even"] == 6
        assert context["sum_odd"] == 9
        assert context["total_sum"] == 15
