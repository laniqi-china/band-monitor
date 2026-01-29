import re
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class LogFileInfo:
    """日志文件信息"""
    path: Path
    date: date
    base_time: datetime
    size: int
    md5: str
    modified_time: datetime
    
    def __str__(self) -> str:
        return f"{self.path.name} ({self.date}, {self.size/1024:.1f}KB)"

class FileScanner:
    """文件扫描器"""
    
    # 文件名模式: bandwhich_YYYYMMDD_HHMM.log
    FILENAME_PATTERN = r'bandwhich_(\d{8})_(\d{4})\.log'
    
    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.scan_cache = {}
    
    def scan_files(self) -> Dict[date, List[LogFileInfo]]:
        """扫描日志文件并按日期分组"""
        if not self.log_dir.exists():
            logger.warning(f"日志目录不存在: {self.log_dir}")
            return {}
        
        date_files = defaultdict(list)
        
        for file_path in self.log_dir.glob('bandwhich_*.log'):
            file_info = self._analyze_file(file_path)
            if file_info:
                date_files[file_info.date].append(file_info)
        
        # 按日期排序
        for date_key in date_files:
            date_files[date_key].sort(key=lambda x: x.base_time)
        
        logger.info(f"扫描完成: 找到 {len(date_files)} 天的日志")
        return dict(sorted(date_files.items()))
    
    def _analyze_file(self, file_path: Path) -> Optional[LogFileInfo]:
        """分析单个文件"""
        try:
            # 提取日期和时间
            match = re.match(self.FILENAME_PATTERN, file_path.name)
            if not match:
                logger.warning(f"文件名格式错误: {file_path.name}")
                return None
            
            date_str = match.group(1)
            time_str = match.group(2)
            
            # 解析日期和时间
            file_date = datetime.strptime(date_str, '%Y%m%d').date()
            base_time = datetime.strptime(
                f"{date_str} {time_str[:2]}:{time_str[2:]}", 
                '%Y%m%d %H:%M'
            )
            
            # 获取文件信息
            stat = file_path.stat()
            md5_hash = self._calculate_md5(file_path)
            
            return LogFileInfo(
                path=file_path,
                date=file_date,
                base_time=base_time,
                size=stat.st_size,
                md5=md5_hash,
                modified_time=datetime.fromtimestamp(stat.st_mtime)
            )
            
        except Exception as e:
            logger.error(f"分析文件失败 {file_path}: {e}")
            return None
    
    def _calculate_md5(self, file_path: Path) -> str:
        """计算文件MD5"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def check_report_exists(self, date: date, report_dir: Path) -> bool:
        """检查指定日期的报告是否已存在"""
        date_str = date.strftime('%Y%m%d')
        report_patterns = [
            f"report_{date_str}.json",
            f"report_{date_str}_*.json",
            f"summary_{date_str}.json",
        ]
        
        for pattern in report_patterns:
            if list(report_dir.glob(pattern)):
                return True
        return False
