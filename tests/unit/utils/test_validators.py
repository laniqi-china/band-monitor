# tests/unit/utils/test_validators.py
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
    validate_config_file,
)


class TestValidator:
    """测试验证器基类"""

    def test_validate_email(self):
        """测试验证邮箱地址"""
        # 有效邮箱
        assert Validator.validate_email("test@example.com") is True
        assert Validator.validate_email("user.name@domain.co.uk") is True
        assert Validator.validate_email("user+tag@example.com") is True

        # 无效邮箱
        assert Validator.validate_email("invalid") is False
        assert Validator.validate_email("@example.com") is False
        assert Validator.validate_email("test@") is False
        assert Validator.validate_email("test@.com") is False
        assert Validator.validate_email("") is False

    def test_validate_ip(self):
        """测试验证IP地址"""
        # 有效IP
        assert Validator.validate_ip("192.168.1.1") is True
        assert Validator.validate_ip("8.8.8.8") is True
        assert Validator.validate_ip("255.255.255.255") is True
        assert Validator.validate_ip("0.0.0.0") is True
        assert Validator.validate_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334") is True

        # 无效IP
        assert Validator.validate_ip("256.256.256.256") is False
        assert Validator.validate_ip("192.168.1") is False
        assert Validator.validate_ip("example.com") is False
        assert Validator.validate_ip("") is False

    def test_validate_domain(self):
        """测试验证域名"""
        # 有效域名
        assert Validator.validate_domain("example.com") is True
        assert Validator.validate_domain("sub.domain.co.uk") is True
        assert Validator.validate_domain("a-b.com") is True

        # 无效域名
        assert Validator.validate_domain("") is False
        assert Validator.validate_domain(".com") is False
        assert Validator.validate_domain("example.") is False
        assert Validator.validate_domain("-example.com") is False
        assert Validator.validate_domain("example-.com") is False
        assert Validator.validate_domain("192.168.1.1") is False

    def test_validate_port(self):
        """测试验证端口号"""
        # 有效端口
        assert Validator.validate_port(80) is True
        assert Validator.validate_port(443) is True
        assert Validator.validate_port(1) is True
        assert Validator.validate_port(65535) is True
        assert Validator.validate_port("8080") is True

        # 无效端口
        assert Validator.validate_port(0) is False
        assert Validator.validate_port(65536) is False
        assert Validator.validate_port(-1) is False
        assert Validator.validate_port("invalid") is False
        assert Validator.validate_port("") is False

    def test_validate_file_exists(self, temp_dir):
        """测试验证文件是否存在"""
        # 创建测试文件
        existing_file = temp_dir / "test.txt"
        existing_file.touch()

        # 有效文件
        assert Validator.validate_file_exists(existing_file) is True
        assert Validator.validate_file_exists(str(existing_file)) is True

        # 不存在的文件
        missing_file = temp_dir / "missing.txt"
        assert Validator.validate_file_exists(missing_file) is False

        # 检查可读性
        existing_file.write_text("test content")
        assert (
            Validator.validate_file_exists(existing_file, check_readable=True) is True
        )

    def test_validate_directory_exists(self, temp_dir):
        """测试验证目录是否存在"""
        # 创建测试目录
        existing_dir = temp_dir / "test_dir"
        existing_dir.mkdir()

        # 有效目录
        assert Validator.validate_directory_exists(existing_dir) is True
        assert Validator.validate_directory_exists(str(existing_dir)) is True

        # 不存在的目录
        missing_dir = temp_dir / "missing_dir"
        assert Validator.validate_directory_exists(missing_dir) is False

        # 检查可写性
        assert (
            Validator.validate_directory_exists(existing_dir, check_writable=True)
            is True
        )

        # 文件不是目录
        test_file = temp_dir / "test.txt"
        test_file.touch()
        assert Validator.validate_directory_exists(test_file) is False

    def test_validate_json(self):
        """测试验证JSON字符串"""
        # 有效JSON
        assert Validator.validate_json('{"key": "value"}') is True
        assert Validator.validate_json("[1, 2, 3]") is True
        assert Validator.validate_json("null") is True

        # 无效JSON
        assert Validator.validate_json("{key: value}") is False
        assert Validator.validate_json("") is False
        assert Validator.validate_json("invalid") is False

    def test_validate_yaml(self):
        """测试验证YAML字符串"""
        # 有效YAML
        assert Validator.validate_yaml("key: value") is True
        assert Validator.validate_yaml("- item1\n- item2") is True
        assert Validator.validate_yaml("") is True  # 空YAML有效

        # 无效YAML
        assert Validator.validate_yaml("key: : :") is False
        assert Validator.validate_yaml("\tinvalid") is False

    def test_validate_date_format(self):
        """测试验证日期格式"""
        # 有效日期
        assert Validator.validate_date_format("20240101", "%Y%m%d") is True
        assert Validator.validate_date_format("2024-01-01", "%Y-%m-%d") is True
        assert Validator.validate_date_format("01/01/2024", "%d/%m/%Y") is True

        # 无效日期
        assert Validator.validate_date_format("20241301", "%Y%m%d") is False  # 无效月份
        assert Validator.validate_date_format("20240132", "%Y%m%d") is False  # 无效日期
        assert Validator.validate_date_format("invalid", "%Y%m%d") is False

    def test_validate_time_format(self):
        """测试验证时间格式"""
        # 有效时间
        assert Validator.validate_time_format("1200", "%H%M") is True
        assert Validator.validate_time_format("23:59", "%H:%M") is True

        # 无效时间
        assert Validator.validate_time_format("2500", "%H%M") is False  # 无效小时
        assert Validator.validate_time_format("1260", "%H%M") is False  # 无效分钟
        assert Validator.validate_time_format("invalid", "%H%M") is False


class TestConfigValidator:
    """测试配置文件验证器"""

    def test_validate_email_config_valid(self):
        """测试验证有效的邮件配置"""
        config = {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "username": "user@example.com",
            "password": "password",
            "from_addr": "sender@example.com",
            "to_addrs": ["recipient@example.com"],
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该没有错误
        assert errors == []

    def test_validate_email_config_missing_fields(self):
        """测试验证缺少字段的邮件配置"""
        config = {
            "smtp_server": "smtp.example.com",
            # 缺少其他必填字段
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该有多个错误
        assert len(errors) > 0
        assert any("缺少必填字段" in error for error in errors)

    def test_validate_email_config_invalid_server(self):
        """测试验证无效的SMTP服务器"""
        config = {
            "smtp_server": "invalid:server",
            "smtp_port": 587,
            "username": "user@example.com",
            "password": "password",
            "from_addr": "sender@example.com",
            "to_addrs": ["recipient@example.com"],
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该有服务器格式错误
        assert any("SMTP服务器格式无效" in error for error in errors)

    def test_validate_email_config_invalid_port(self):
        """测试验证无效的端口"""
        config = {
            "smtp_server": "smtp.example.com",
            "smtp_port": 70000,  # 无效端口
            "username": "user@example.com",
            "password": "password",
            "from_addr": "sender@example.com",
            "to_addrs": ["recipient@example.com"],
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该有端口错误
        assert any("SMTP端口无效" in error for error in errors)

    def test_validate_email_config_invalid_emails(self):
        """测试验证无效的邮箱地址"""
        config = {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "username": "invalid-email",
            "password": "password",
            "from_addr": "invalid-email",
            "to_addrs": ["recipient@example.com", "invalid"],
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该有多个邮箱格式错误
        assert len(errors) >= 2
        assert any("邮箱地址格式无效" in error for error in errors)

    def test_validate_email_config_invalid_to_addrs_type(self):
        """测试验证无效的收件人列表类型"""
        config = {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "username": "user@example.com",
            "password": "password",
            "from_addr": "sender@example.com",
            "to_addrs": "not-a-list",  # 不是列表
        }

        errors = ConfigValidator.validate_email_config(config)

        # 应该有类型错误
        assert any("必须是数组" in error for error in errors)

    def test_validate_path_config_valid(self, temp_dir):
        """测试验证有效的路径配置"""
        config = {
            "log_dir": str(temp_dir / "logs"),
            "report_dir": str(temp_dir / "reports"),
            "archive_dir": str(temp_dir / "archive"),
        }

        errors = ConfigValidator.validate_path_config(config)

        # 应该没有错误
        assert errors == []

    def test_validate_path_config_missing_fields(self):
        """测试验证缺少字段的路径配置"""
        config = {
            "log_dir": "./logs",
            # 缺少其他必填字段
        }

        errors = ConfigValidator.validate_path_config(config)

        # 应该有多个错误
        assert len(errors) > 0
        assert any("路径配置缺少" in error for error in errors)

    def test_validate_path_config_invalid_path(self, temp_dir):
        """测试验证无效的路径"""
        # 创建只读目录
        read_only_dir = temp_dir / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o444)  # 只读

        config = {
            "log_dir": str(read_only_dir),
            "report_dir": str(temp_dir / "reports"),
            "archive_dir": str(temp_dir / "archive"),
        }

        errors = ConfigValidator.validate_path_config(config)

        # 应该有路径不可写错误
        assert any("路径不可写" in error for error in errors)

        # 恢复权限
        read_only_dir.chmod(0o755)


class TestTrafficValidator:
    """测试流量数据验证器"""

    def test_validate_traffic_record_valid(self):
        """测试验证有效的流量记录"""
        record = {
            "timestamp": "2024-01-01T12:00:00",
            "pid": 12345,
            "process_name": "firefox",
            "remote_address": "8.8.8.8",
            "upload_bps": 100,
            "download_bps": 200,
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该没有错误
        assert errors == []

    def test_validate_traffic_record_missing_fields(self):
        """测试验证缺少字段的流量记录"""
        record = {
            "pid": 12345,
            # 缺少其他必填字段
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有多个错误
        assert len(errors) > 0
        assert any("缺少必填字段" in error for error in errors)

    def test_validate_traffic_record_invalid_pid(self):
        """测试验证无效的PID"""
        record = {
            "timestamp": "2024-01-01T12:00:00",
            "pid": -1,  # 无效PID
            "process_name": "firefox",
            "remote_address": "8.8.8.8",
            "upload_bps": 100,
            "download_bps": 200,
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有PID错误
        assert any("进程ID无效" in error for error in errors)

    def test_validate_traffic_record_invalid_traffic_values(self):
        """测试验证无效的流量值"""
        record = {
            "timestamp": "2024-01-01T12:00:00",
            "pid": 12345,
            "process_name": "firefox",
            "remote_address": "8.8.8.8",
            "upload_bps": -100,  # 负数
            "download_bps": "invalid",  # 非数字
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有两个错误
        assert len(errors) >= 2
        assert any("不能为负数" in error for error in errors)
        assert any("格式错误" in error for error in errors)

    def test_validate_traffic_record_huge_traffic_value(self):
        """测试验证过大的流量值"""
        record = {
            "timestamp": "2024-01-01T12:00:00",
            "pid": 12345,
            "process_name": "firefox",
            "remote_address": "8.8.8.8",
            "upload_bps": 20 * 1024 * 1024 * 1024,  # 20GB/s，异常大
            "download_bps": 200,
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有流量过大错误
        assert any("值异常大" in error for error in errors)

    def test_validate_traffic_record_invalid_remote_address(self):
        """测试验证无效的远程地址"""
        record = {
            "timestamp": "2024-01-01T12:00:00",
            "pid": 12345,
            "process_name": "firefox",
            "remote_address": "invalid-address",
            "upload_bps": 100,
            "download_bps": 200,
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有地址错误
        assert any("远程地址格式无效" in error for error in errors)

    def test_validate_traffic_record_domain_address(self):
        """测试验证域名地址"""
        record = {
            "timestamp": "2024-01-01T12:00:00",
            "pid": 12345,
            "process_name": "firefox",
            "remote_address": "example.com",  # 域名
            "upload_bps": 100,
            "download_bps": 200,
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该没有错误（域名是有效的）
        assert errors == []

    def test_validate_traffic_record_invalid_ports(self):
        """测试验证无效的端口"""
        record = {
            "timestamp": "2024-01-01T12:00:00",
            "pid": 12345,
            "process_name": "firefox",
            "remote_address": "8.8.8.8",
            "remote_port": 70000,  # 无效端口
            "local_port": 0,  # 无效端口
            "upload_bps": 100,
            "download_bps": 200,
        }

        errors = TrafficValidator.validate_traffic_record(record)

        # 应该有两个端口错误
        port_errors = [e for e in errors if "端口无效" in e]
        assert len(port_errors) >= 2

    def test_validate_bandwhich_log_line(self):
        """测试验证bandwhich日志行"""
        # 有效行
        valid_lines = [
            "Refreshing:",
            "<NO TRAFFIC>",
            'process: <12345> "firefox" up/down Bps: 100/200 connections: 3',
            'connection: <12345> <eth0>:54321 => 8.8.8.8:443 (tcp) up/down Bps: 100/200 process: "firefox"',
            "remote_address: <12345> 8.8.8.8 up/down Bps: 100/200 connections: 1",
        ]

        for line in valid_lines:
            assert TrafficValidator.validate_bandwhich_log_line(line) is True

        # 无效行
        invalid_lines = ["", "invalid line", "process: invalid", "connection: invalid"]

        for line in invalid_lines:
            assert TrafficValidator.validate_bandwhich_log_line(line) is False


class TestValidateConfigFile:
    """测试验证配置文件"""

    def test_validate_config_file_valid(self, temp_dir, sample_config):
        """测试验证有效的配置文件"""
        config_file = temp_dir / "config.yaml"

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_config, f)

        # 应该成功加载
        config = validate_config_file(config_file)

        assert config == sample_config

    def test_validate_config_file_missing(self, temp_dir):
        """测试验证不存在的配置文件"""
        config_file = temp_dir / "missing.yaml"

        with pytest.raises(ValidationError, match="配置文件不存在"):
            validate_config_file(config_file)

    def test_validate_config_file_invalid_yaml(self, temp_dir):
        """测试验证无效的YAML配置文件"""
        config_file = temp_dir / "invalid.yaml"

        with open(config_file, "w", encoding="utf-8") as f:
            f.write("invalid: yaml: : :")

        with pytest.raises(ValidationError, match="YAML格式错误"):
            validate_config_file(config_file)

    def test_validate_config_file_invalid_email_config(self, temp_dir):
        """测试验证邮件配置无效的配置文件"""
        config = {
            "paths": {
                "log_dir": "./logs",
                "report_dir": "./reports",
                "archive_dir": "./archive",
                "temp_dir": "./temp",
            },
            "email": {
                "smtp_server": "invalid:server",
                "smtp_port": 70000,
                "username": "invalid-email",
                "password": "password",
                "from_addr": "invalid-email",
                "to_addrs": ["invalid"],
            },
        }

        config_file = temp_dir / "config.yaml"

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        with pytest.raises(ValidationError, match="配置验证失败"):
            validate_config_file(config_file)
