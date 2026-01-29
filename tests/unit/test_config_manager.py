# tests/unit/test_config_manager.py
import pytest
import yaml
from pathlib import Path
import tempfile
import shutil

from src.config_manager import ConfigManager, PathConfig, EmailConfig


class TestPathConfig:
    """测试路径配置类"""

    def test_from_dict(self):
        """测试从字典创建PathConfig"""
        data = {
            "log_dir": "./logs",
            "report_dir": "./reports",
            "archive_dir": "./archive",
            "temp_dir": "./temp",
        }

        config = PathConfig.from_dict(data)

        assert config.log_dir == Path("./logs")
        assert config.report_dir == Path("./reports")
        assert config.archive_dir == Path("./archive")
        assert config.temp_dir == Path("./temp")

    def test_path_resolution(self, temp_dir):
        """测试路径解析"""
        data = {
            "log_dir": str(temp_dir / "logs"),
            "report_dir": str(temp_dir / "reports"),
            "archive_dir": str(temp_dir / "archive"),
            "temp_dir": str(temp_dir / "temp"),
        }

        config = PathConfig.from_dict(data)

        assert config.log_dir.exists() is False
        assert str(config.log_dir).endswith("logs")


class TestEmailConfig:
    """测试邮件配置类"""

    def test_from_dict(self):
        """测试从字典创建EmailConfig"""
        data = {
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "use_ssl": False,
            "use_tls": True,
            "username": "user@test.com",
            "password": "password123",
            "from_addr": "sender@test.com",
            "to_addrs": ["recipient1@test.com", "recipient2@test.com"],
            "cc_addrs": ["cc@test.com"],
            "subject_prefix": "测试",
        }

        config = EmailConfig.from_dict(data)

        assert config.smtp_server == "smtp.test.com"
        assert config.smtp_port == 587
        assert config.use_ssl is False
        assert config.use_tls is True
        assert config.username == "user@test.com"
        assert config.password == "password123"
        assert config.from_addr == "sender@test.com"
        assert len(config.to_addrs) == 2
        assert len(config.cc_addrs) == 1
        assert config.subject_prefix == "测试"

    def test_default_values(self):
        """测试默认值"""
        data = {
            "smtp_server": "smtp.test.com",
            "smtp_port": 465,
            "username": "user@test.com",
            "password": "password123",
            "from_addr": "sender@test.com",
            "to_addrs": ["recipient@test.com"],
        }

        config = EmailConfig.from_dict(data)

        assert config.use_ssl is False  # 默认值
        assert config.use_tls is True  # 默认值
        assert config.cc_addrs == []  # 默认值
        assert config.subject_prefix == "网络流量监控报告"  # 默认值


class TestConfigManager:
    """测试配置管理器"""

    def test_load_config(self, temp_dir, sample_config):
        """测试加载配置"""
        config_file = temp_dir / "config.yaml"

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_config, f)

        manager = ConfigManager(str(config_file))

        # 验证配置已加载
        assert manager.config == sample_config

    def test_missing_config_file(self, temp_dir):
        """测试缺失配置文件"""
        config_file = temp_dir / "missing.yaml"

        with pytest.raises(FileNotFoundError):
            ConfigManager(str(config_file))

    def test_get_path_config(self, config_manager):
        """测试获取路径配置"""
        paths = config_manager.get_path_config()

        assert isinstance(paths, PathConfig)
        assert "test_logs" in str(paths.log_dir)
        assert "test_reports" in str(paths.report_dir)

    def test_get_email_config(self, config_manager):
        """测试获取邮件配置"""
        email_config = config_manager.get_email_config()

        assert isinstance(email_config, EmailConfig)
        assert email_config.smtp_server == "smtp.test.com"
        assert email_config.smtp_port == 587

    def test_update_config(self, config_manager):
        """测试更新配置"""
        # 更新处理配置中的最大工作线程数
        config_manager.update_config("processing", "max_workers", 8)

        # 验证更新
        processing_config = config_manager.get_processing_config()
        assert processing_config["max_workers"] == 8

        # 验证配置已保存
        with open(config_manager.config_file, "r", encoding="utf-8") as f:
            saved_config = yaml.safe_load(f)

        assert saved_config["processing"]["max_workers"] == 8

    def test_to_json(self, config_manager):
        """测试转换为JSON"""
        json_str = config_manager.to_json()

        # 验证JSON格式
        import json

        parsed = json.loads(json_str)

        assert "version" in parsed
        assert "paths" in parsed
        assert "email" in parsed

    def test_directory_creation(self, config_manager):
        """测试目录自动创建"""
        paths = config_manager.get_path_config()

        # 所有目录都应已创建
        assert paths.log_dir.exists()
        assert paths.report_dir.exists()
        assert paths.archive_dir.exists()
        assert paths.temp_dir.exists()

    def test_invalid_config_format(self, temp_dir):
        """测试无效配置格式"""
        config_file = temp_dir / "invalid.yaml"

        # 写入无效的YAML
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("invalid: yaml: : :")

        # 应该能够创建实例，但在使用时会出错
        manager = ConfigManager(str(config_file))

        # 尝试访问配置应该引发异常
        with pytest.raises(Exception):
            _ = manager.get_path_config()
