# tests/unit/utils/test_logger.py
import json
import logging
import tempfile
from pathlib import Path

import pytest
from src.utils.logger import (
    ColoredFormatter,
    JSONFormatter,
    LoggerMixin,
    get_logger,
    setup_logging,
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
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="测试消息",
            args=(),
            exc_info=None,
        )

        formatted = json_formatter.format(record)

        # 应该是有效的JSON
        parsed = json.loads(formatted)

        # 验证基本字段
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert parsed["message"] == "测试消息"
        assert parsed["module"] == "test"
        assert "timestamp" in parsed

    def test_format_with_exception(self, json_formatter):
        """测试带异常的格式化"""
        try:
            raise ValueError("测试异常")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="发生异常",
            args=(),
            exc_info=exc_info,
        )

        formatted = json_formatter.format(record)
        parsed = json.loads(formatted)

        # 应该包含异常信息
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]
        assert "测试异常" in parsed["exception"]

    def test_format_with_extra_fields(self, json_formatter):
        """测试带额外字段的格式化"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="测试消息",
            args=(),
            exc_info=None,
        )

        # 添加额外字段
        record.extra_fields = {
            "user": "testuser",
            "action": "login",
            "duration_ms": 123.45,
        }

        formatted = json_formatter.format(record)
        parsed = json.loads(formatted)

        # 验证额外字段
        assert parsed["user"] == "testuser"
        assert parsed["action"] == "login"
        assert parsed["duration_ms"] == 123.45


class TestColoredFormatter:
    """测试彩色格式化器"""

    @pytest.fixture
    def colored_formatter(self):
        """创建彩色格式化器实例"""
        return ColoredFormatter()

    def test_format_basic(self, colored_formatter):
        """测试基本格式化"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="测试消息",
            args=(),
            exc_info=None,
        )

        formatted = colored_formatter.format(record)

        # 应该包含基本元素
        assert "test" in formatted
        assert "INFO" in formatted
        assert "测试消息" in formatted

        # 应该包含颜色代码（ANSI转义序列）
        assert "\x1b[" in formatted  # ANSI转义序列

    def test_different_levels(self, colored_formatter):
        """测试不同级别的颜色"""
        levels = [
            (logging.DEBUG, "cyan"),
            (logging.INFO, "green"),
            (logging.WARNING, "yellow"),
            (logging.ERROR, "red"),
            (logging.CRITICAL, "red,bg_white"),
        ]

        for level, _ in levels:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=10,
                msg=f"级别 {level}",
                args=(),
                exc_info=None,
            )

            formatted = colored_formatter.format(record)
            assert "\x1b[" in formatted  # 所有级别都应该有颜色


class TestLoggerFunctions:
    """测试日志函数"""

    def test_setup_logging_default(self, temp_dir):
        """测试默认日志设置"""
        log_file = temp_dir / "test.log"

        config = {"file": str(log_file), "enable_console": False}

        setup_logging(config)

        # 获取根日志记录器
        root_logger = logging.getLogger()

        # 应该配置了文件处理器
        file_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.FileHandler)
        ]

        assert len(file_handlers) > 0

        # 记录测试消息
        test_logger = logging.getLogger("test_module")
        test_logger.info("测试消息")

        # 验证消息已写入文件
        assert log_file.exists()
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "测试消息" in content

    def test_setup_logging_json_format(self, temp_dir):
        """测试JSON格式日志设置"""
        log_file = temp_dir / "test.json.log"

        config = {"file": str(log_file), "enable_json": True, "enable_console": False}

        setup_logging(config)

        # 记录测试消息
        test_logger = logging.getLogger("test_json")
        test_logger.info("JSON测试消息")

        # 验证消息是JSON格式
        assert log_file.exists()
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 应该有一行JSON
        assert len(lines) > 0

        # 验证是有效的JSON
        parsed = json.loads(lines[0].strip())
        assert parsed["message"] == "JSON测试消息"
        assert parsed["level"] == "INFO"

    def test_setup_logging_console_only(self):
        """测试仅控制台日志设置"""
        config = {"enable_console": True}

        setup_logging(config)

        # 获取根日志记录器
        root_logger = logging.getLogger()

        # 应该只有控制台处理器
        console_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)
        ]

        assert len(console_handlers) > 0

    def test_get_logger(self):
        """测试获取日志记录器"""
        logger = get_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

        # 指定级别
        debug_logger = get_logger("debug_module", "DEBUG")
        assert debug_logger.level == logging.DEBUG

        # 默认级别
        info_logger = get_logger("info_module")
        assert info_logger.level == logging.NOTSET  # 继承根日志记录器级别

    def test_setup_logging_with_file_rotation(self, temp_dir):
        """测试带文件轮转的日志设置"""
        log_file = temp_dir / "rotating.log"

        config = {
            "file": str(log_file),
            "file_size": "1KB",  # 1KB后轮转
            "backup_count": 2,
            "enable_console": False,
        }

        setup_logging(config)

        # 获取根日志记录器
        root_logger = logging.getLogger()

        # 查找轮转文件处理器
        from logging.handlers import RotatingFileHandler

        rotating_handlers = [
            h for h in root_logger.handlers if isinstance(h, RotatingFileHandler)
        ]

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
            self.logger.info("正在执行操作")
            return "完成"

    def test_logger_property(self):
        """测试logger属性"""
        test_instance = self.TestClass()

        # logger属性应该存在
        assert hasattr(test_instance, "logger")
        assert isinstance(test_instance.logger, logging.Logger)

        # 应该是相同的实例
        logger1 = test_instance.logger
        logger2 = test_instance.logger
        assert logger1 is logger2

    def test_log_with_context(self, temp_dir):
        """测试带上下文的日志"""
        log_file = temp_dir / "context.log"

        config = {"file": str(log_file), "enable_json": True, "enable_console": False}

        setup_logging(config)

        test_instance = self.TestClass()

        # 记录带上下文的日志
        test_instance.log_with_context(
            "info", "用户操作", user="testuser", action="login", success=True
        )

        # 验证日志内容
        assert log_file.exists()
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 应该有一行JSON日志
        assert len(lines) > 0

        parsed = json.loads(lines[0].strip())
        assert parsed["message"] == "用户操作"
        assert parsed["user"] == "testuser"
        assert parsed["action"] == "login"
        assert parsed["success"] is True

    def test_log_with_context_invalid_level(self, temp_dir):
        """测试无效级别的带上下文日志"""
        config = {"enable_console": False}

        setup_logging(config)

        test_instance = self.TestClass()

        # 使用无效的级别，应该回退到info
        test_instance.log_with_context("invalid_level", "测试消息", test="data")

        # 应该不抛出异常

    def test_inheritance(self):
        """测试继承"""

        class ChildClass(self.TestClass):
            """子类"""

            def do_child_thing(self):
                self.logger.info("子类操作")

        child_instance = ChildClass()

        # 应该可以访问logger
        assert hasattr(child_instance, "logger")

        # logger名称应该是子类名
        assert child_instance.logger.name == "TestChildClass"

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

        assert result == "完成"
        # 注意：这里我们无法验证日志是否被记录，
        # 因为测试环境可能没有配置日志处理器
