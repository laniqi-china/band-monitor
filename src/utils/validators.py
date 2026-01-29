import re
import ipaddress
import socket
import os
from pathlib import Path
from typing import Union, Optional, List, Dict, Any
from urllib.parse import urlparse
import json
import yaml

class ValidationError(Exception):
    """验证错误"""
    pass

class Validator:
    """验证器基类"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱地址"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_ip(ip: str) -> bool:
        """验证IP地址"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_domain(domain: str) -> bool:
        """验证域名"""
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        return bool(re.match(pattern, domain))
    
    @staticmethod
    def validate_port(port: Union[int, str]) -> bool:
        """验证端口号"""
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_file_exists(file_path: Union[str, Path], check_readable: bool = True) -> bool:
        """验证文件是否存在（并可读）"""
        path = Path(file_path)
        exists = path.exists() and path.is_file()
        if exists and check_readable:
            return os.access(path, os.R_OK)
        return exists
    
    @staticmethod
    def validate_directory_exists(dir_path: Union[str, Path], check_writable: bool = False) -> bool:
        """验证目录是否存在（并可写）"""
        path = Path(dir_path)
        exists = path.exists() and path.is_dir()
        if exists and check_writable:
            return os.access(path, os.W_OK)
        return exists
    
    @staticmethod
    def validate_json(content: str) -> bool:
        """验证JSON字符串"""
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False
    
    @staticmethod
    def validate_yaml(content: str) -> bool:
        """验证YAML字符串"""
        try:
            yaml.safe_load(content)
            return True
        except yaml.YAMLError:
            return False
    
    @staticmethod
    def validate_date_format(date_str: str, format: str = '%Y%m%d') -> bool:
        """验证日期格式"""
        from datetime import datetime
        try:
            datetime.strptime(date_str, format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_time_format(time_str: str, format: str = '%H%M') -> bool:
        """验证时间格式"""
        from datetime import datetime
        try:
            datetime.strptime(time_str, format)
            return True
        except ValueError:
            return False

class ConfigValidator(Validator):
    """配置文件验证器"""
    
    @classmethod
    def validate_email_config(cls, config: Dict[str, Any]) -> List[str]:
        """验证邮件配置"""
        errors = []
        
        required_fields = ['smtp_server', 'smtp_port', 'username', 'from_addr', 'to_addrs']
        for field in required_fields:
            if field not in config:
                errors.append(f"邮件配置缺少必填字段: {field}")
        
        # 验证SMTP服务器
        if 'smtp_server' in config:
            server = config['smtp_server']
            if not cls.validate_domain(server.split(':')[0]):
                errors.append(f"SMTP服务器格式无效: {server}")
        
        # 验证端口
        if 'smtp_port' in config:
            if not cls.validate_port(config['smtp_port']):
                errors.append(f"SMTP端口无效: {config['smtp_port']}")
        
        # 验证邮箱地址
        email_fields = ['username', 'from_addr']
        for field in email_fields:
            if field in config and not cls.validate_email(config[field]):
                errors.append(f"邮箱地址格式无效: {field}={config[field]}")
        
        # 验证收件人列表
        if 'to_addrs' in config:
            if not isinstance(config['to_addrs'], list):
                errors.append("收件人列表必须是数组")
            else:
                for email in config['to_addrs']:
                    if not cls.validate_email(email):
                        errors.append(f"收件人邮箱格式无效: {email}")
        
        return errors
    
    @classmethod
    def validate_path_config(cls, config: Dict[str, Any]) -> List[str]:
        """验证路径配置"""
        errors = []
        
        required_paths = ['log_dir', 'report_dir', 'archive_dir']
        for path_key in required_paths:
            if path_key not in config:
                errors.append(f"路径配置缺少: {path_key}")
            else:
                path = Path(config[path_key])
                if not cls.validate_directory_exists(path, check_writable=True):
                    errors.append(f"路径不可写或不存在: {path_key}={path}")
        
        return errors

class TrafficValidator(Validator):
    """流量数据验证器"""
    
    @staticmethod
    def validate_traffic_record(record: Dict[str, Any]) -> List[str]:
        """验证流量记录"""
        errors = []
        
        required_fields = ['timestamp', 'pid', 'process_name', 'remote_address', 
                          'upload_bps', 'download_bps']
        
        for field in required_fields:
            if field not in record:
                errors.append(f"记录缺少必填字段: {field}")
        
        # 验证PID
        if 'pid' in record:
            try:
                pid = int(record['pid'])
                if pid <= 0:
                    errors.append(f"进程ID无效: {pid}")
            except (ValueError, TypeError):
                errors.append(f"进程ID格式错误: {record['pid']}")
        
        # 验证流量值
        for field in ['upload_bps', 'download_bps']:
            if field in record:
                try:
                    value = int(record[field])
                    if value < 0:
                        errors.append(f"{field}不能为负数: {value}")
                    if value > 10 * 1024 * 1024 * 1024:  # 10GB/s
                        errors.append(f"{field}值异常大: {value}")
                except (ValueError, TypeError):
                    errors.append(f"{field}格式错误: {record[field]}")
        
        # 验证远程地址
        if 'remote_address' in record:
            addr = record['remote_address']
            if not (cls.validate_ip(addr) or cls.validate_domain(addr)):
                errors.append(f"远程地址格式无效: {addr}")
        
        # 验证端口
        if 'remote_port' in record:
            if not cls.validate_port(record['remote_port']):
                errors.append(f"远程端口无效: {record['remote_port']}")
        
        if 'local_port' in record:
            if not cls.validate_port(record['local_port']):
                errors.append(f"本地端口无效: {record['local_port']}")
        
        return errors
    
    @staticmethod
    def validate_bandwhich_log_line(line: str) -> bool:
        """验证bandwhich日志行格式"""
        patterns = [
            r'^Refreshing:$',
            r'^<NO TRAFFIC>$',
            r'^process: <\d+> "[^"]+" up/down Bps: \d+/\d+ connections: \d+$',
            r'^connection: <\d+> <[^>]+>:\d+ => [^:]+:\d+ \(\w+\) up/down Bps: \d+/\d+ process: "[^"]+"$',
            r'^remote_address: <\d+> [^ ]+ up/down Bps: \d+/\d+ connections: \d+$'
        ]
        
        for pattern in patterns:
            if re.match(pattern, line.strip()):
                return True
        return False

def validate_config_file(config_path: Union[str, Path]) -> Dict[str, Any]:
    """验证配置文件"""
    config_path = Path(config_path)
    
    if not Validator.validate_file_exists(config_path):
        raise ValidationError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if not Validator.validate_yaml(content):
        raise ValidationError(f"配置文件YAML格式错误: {config_path}")
    
    config = yaml.safe_load(content)
    
    # 验证各配置节
    all_errors = []
    
    if 'email' in config:
        errors = ConfigValidator.validate_email_config(config['email'])
        all_errors.extend([f"email.{e}" for e in errors])
    
    if 'paths' in config:
        errors = ConfigValidator.validate_path_config(config['paths'])
        all_errors.extend([f"paths.{e}" for e in errors])
    
    if all_errors:
        raise ValidationError(f"配置验证失败:\n" + "\n".join(all_errors))
    
    return config

# 使用示例
if __name__ == '__main__':
    # 测试验证器
    print("邮箱验证:", Validator.validate_email("test@example.com"))
    print("IP验证:", Validator.validate_ip("192.168.1.1"))
    print("端口验证:", Validator.validate_port(8080))
    
    # 测试流量记录验证
    record = {
        'timestamp': '2023-01-01T00:00:00',
        'pid': 1234,
        'process_name': 'test',
        'remote_address': '8.8.8.8',
        'upload_bps': 1000,
        'download_bps': 2000
    }
    errors = TrafficValidator.validate_traffic_record(record)
    print("流量记录验证:", errors if errors else "通过")
