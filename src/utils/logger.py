import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import colorlog
from datetime import datetime
import json

class JSONFormatter(logging.Formatter):
    """JSON格式的日志格式化器"""
    
    def format(self, record):
        log_obj = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # 添加异常信息
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, 'extra_fields'):
            log_obj.update(record.extra_fields)
        
        return json.dumps(log_obj, ensure_ascii=False)

class ColoredFormatter(colorlog.ColoredFormatter):
    """彩色日志格式化器"""
    
    def __init__(self):
        super().__init__(
            fmt='%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )

def setup_logging(config: dict = None):
    """设置日志配置"""
    if config is None:
        config = {}
    
    # 获取配置
    log_level = config.get('level', 'INFO')
    log_format = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = config.get('file', 'logs/network_monitor.log')
    max_file_size = config.get('file_size', '10MB')
    backup_count = config.get('backup_count', 5)
    enable_console = config.get('enable_console', True)
    enable_json = config.get('enable_json', False)
    
    # 创建日志目录
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 文件处理器
    if max_file_size.endswith('MB'):
        max_bytes = int(max_file_size[:-2]) * 1024 * 1024
    elif max_file_size.endswith('GB'):
        max_bytes = int(max_file_size[:-2]) * 1024 * 1024 * 1024
    else:
        max_bytes = 10 * 1024 * 1024  # 默认10MB
    
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    if enable_json:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(logging.Formatter(log_format))
    
    logger.addHandler(file_handler)
    
    # 控制台处理器
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter())
        logger.addHandler(console_handler)
    
    # 特定模块的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('smtplib').setLevel(logging.WARNING)
    
    return logger

def get_logger(name: str, level: str = None) -> logging.Logger:
    """获取指定名称的日志记录器"""
    logger = logging.getLogger(name)
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    return logger

class LoggerMixin:
    """日志混合类，方便在其他类中使用"""
    
    @property
    def logger(self):
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
    
    def log_with_context(self, level: str, message: str, **kwargs):
        """记录带上下文的日志"""
        extra = {'extra_fields': kwargs}
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message, extra=extra)

# 使用示例
if __name__ == '__main__':
    # 配置日志
    config = {
        'level': 'DEBUG',
        'file': 'logs/test.log',
        'enable_json': True,
        'enable_console': True
    }
    setup_logging(config)
    
    # 使用日志
    logger = get_logger('test_module')
    logger.info('测试信息')
    logger.error('测试错误', extra={'extra_fields': {'user': 'admin', 'action': 'login'}})
