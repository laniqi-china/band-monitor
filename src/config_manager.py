import os
import yaml
import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class PathConfig:
    """路径配置"""
    log_dir: Path
    report_dir: Path
    archive_dir: Path
    temp_dir: Path
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'PathConfig':
        return cls(
            log_dir=Path(data['log_dir']),
            report_dir=Path(data['report_dir']),
            archive_dir=Path(data['archive_dir']),
            temp_dir=Path(data['temp_dir'])
        )

@dataclass
class EmailConfig:
    """邮件配置"""
    smtp_server: str
    smtp_port: int
    use_ssl: bool
    use_tls: bool
    username: str
    password: str
    from_addr: str
    to_addrs: List[str]
    cc_addrs: List[str]
    subject_prefix: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailConfig':
        return cls(
            smtp_server=data['smtp_server'],
            smtp_port=data['smtp_port'],
            use_ssl=data.get('use_ssl', False),
            use_tls=data.get('use_tls', True),
            username=data['username'],
            password=os.environ.get('EMAIL_PASSWORD', data.get('password', '')),
            from_addr=data['from_addr'],
            to_addrs=data['to_addrs'],
            cc_addrs=data.get('cc_addrs', []),
            subject_prefix=data.get('subject_prefix', '网络流量监控报告')
        )

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config/settings.yaml"):
        self.config_file = Path(config_file)
        self.config = {}
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 确保路径存在
        self._ensure_directories()
        logger.info(f"配置加载成功: {self.config_file}")
    
    def _ensure_directories(self) -> None:
        """确保所有目录都存在"""
        paths = self.get_path_config()
        for path in [paths.log_dir, paths.report_dir, 
                    paths.archive_dir, paths.temp_dir]:
            path.mkdir(parents=True, exist_ok=True)
    
    def get_path_config(self) -> PathConfig:
        """获取路径配置"""
        return PathConfig.from_dict(self.config['paths'])
    
    def get_email_config(self) -> EmailConfig:
        """获取邮件配置"""
        return EmailConfig.from_dict(self.config['email'])
    
    def get_processing_config(self) -> Dict[str, Any]:
        """获取处理配置"""
        return self.config.get('processing', {})
    
    def get_report_config(self) -> Dict[str, Any]:
        """获取报告配置"""
        return self.config.get('reports', {})
    
    def get_archive_config(self) -> Dict[str, Any]:
        """获取存档配置"""
        return self.config.get('archive', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.config.get('logging', {})
    
    def update_config(self, section: str, key: str, value: Any) -> None:
        """更新配置"""
        if section in self.config:
            if key in self.config[section]:
                self.config[section][key] = value
                self.save_config()
                logger.info(f"配置已更新: {section}.{key} = {value}")
    
    def save_config(self) -> None:
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
    
    def to_json(self) -> str:
        """将配置转换为JSON格式"""
        return json.dumps(self.config, indent=2, ensure_ascii=False)
