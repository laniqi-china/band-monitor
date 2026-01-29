import zipfile
import tarfile
import gzip
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import shutil
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class ArchiveInfo:
    """存档信息"""
    path: Path
    format: str
    size: int
    created: datetime
    contents: List[str]
    metadata: Dict[str, Any]

class ArchiveManager:
    """存档管理器"""
    
    def __init__(self, archive_dir: Path, keep_original: bool = False):
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.keep_original = keep_original
        
    def archive_logs(self, date_key: date, log_files: List[Path], 
                     format: str = 'zip') -> Optional[Path]:
        """存档日志文件"""
        if not log_files:
            logger.warning(f"没有日志文件需要存档: {date_key}")
            return None
        
        date_str = date_key.strftime('%Y%m%d')
        archive_path = self.archive_dir / f"logs_{date_str}.{format}"
        
        try:
            # 创建存档
            if format == 'zip':
                self._create_zip_archive(archive_path, log_files)
            elif format == 'tar.gz':
                self._create_tar_gz_archive(archive_path, log_files)
            else:
                raise ValueError(f"不支持的存档格式: {format}")
            
            # 生成元数据
            metadata = self._create_archive_metadata(archive_path, log_files)
            
            # 保存元数据
            metadata_file = self.archive_dir / f"metadata_{date_str}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # 处理原始文件
            if not self.keep_original:
                self._cleanup_original_files(log_files)
            
            logger.info(f"日志存档完成: {archive_path} ({archive_path.stat().st_size/1024:.1f}KB)")
            return archive_path
            
        except Exception as e:
            logger.error(f"存档失败: {e}")
            return None
    
    def _create_zip_archive(self, archive_path: Path, files: List[Path]) -> None:
        """创建ZIP存档"""
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                if file_path.exists():
                    # 使用相对路径存储
                    arcname = file_path.name
                    zipf.write(file_path, arcname)
    
    def _create_tar_gz_archive(self, archive_path: Path, files: List[Path]) -> None:
        """创建tar.gz存档"""
        with tarfile.open(archive_path, 'w:gz') as tar:
            for file_path in files:
                if file_path.exists():
                    tar.add(file_path, arcname=file_path.name)
    
    def _create_archive_metadata(self, archive_path: Path, 
                               original_files: List[Path]) -> Dict[str, Any]:
        """创建存档元数据"""
        metadata = {
            'archive_path': str(archive_path),
            'archive_size': archive_path.stat().st_size,
            'archive_format': archive_path.suffix.lstrip('.'),
            'creation_time': datetime.now().isoformat(),
            'original_files': [
                {
                    'path': str(file_path),
                    'name': file_path.name,
                    'size': file_path.stat().st_size if file_path.exists() else 0,
                    'exists': file_path.exists()
                }
                for file_path in original_files
            ],
            'total_original_size': sum(
                file_path.stat().st_size 
                for file_path in original_files 
                if file_path.exists()
            ),
            'compression_ratio': self._calculate_compression_ratio(archive_path, original_files)
        }
        
        return metadata
    
    def _calculate_compression_ratio(self, archive_path: Path, 
                                   original_files: List[Path]) -> float:
        """计算压缩比"""
        original_size = sum(
            file_path.stat().st_size 
            for file_path in original_files 
            if file_path.exists()
        )
        
        if original_size == 0:
            return 0.0
        
        archive_size = archive_path.stat().st_size
        return (1 - archive_size / original_size) * 100
    
    def _cleanup_original_files(self, files: List[Path]) -> None:
        """清理原始文件"""
        for file_path in files:
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.debug(f"已删除原始文件: {file_path}")
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path}: {e}")
    
    def cleanup_old_archives(self, retention_days: int = 30) -> List[Path]:
        """清理旧存档"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_files = []
        
        for archive_file in self.archive_dir.glob('*.*'):
            # 跳过当天和最近的文件
            try:
                file_time = datetime.fromtimestamp(archive_file.stat().st_mtime)
                if file_time < cutoff_date:
                    archive_file.unlink()
                    deleted_files.append(archive_file)
                    logger.info(f"已清理旧存档: {archive_file.name}")
            except Exception as e:
                logger.error(f"清理存档失败 {archive_file}: {e}")
        
        return deleted_files
    
    def extract_archive(self, archive_path: Path, 
                       target_dir: Optional[Path] = None) -> List[Path]:
        """解压存档"""
        if not target_dir:
            target_dir = self.archive_dir / 'extracted'
        
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        extracted_files = []
        
        try:
            if archive_path.suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    zipf.extractall(target_dir)
                    extracted_files = [target_dir / name for name in zipf.namelist()]
                    
            elif archive_path.suffix in ['.tar.gz', '.tgz']:
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.extractall(target_dir)
                    extracted_files = [target_dir / member.name for member in tar.getmembers()]
            
            logger.info(f"存档解压完成: {len(extracted_files)} 个文件")
            return extracted_files
            
        except Exception as e:
            logger.error(f"解压存档失败: {e}")
            return []
    
    def list_archives(self) -> List[ArchiveInfo]:
        """列出所有存档"""
        archives = []
        
        for archive_file in self.archive_dir.glob('*.*'):
            if archive_file.suffix in ['.zip', '.tar.gz', '.tgz']:
                try:
                    archive_info = self._get_archive_info(archive_file)
                    archives.append(archive_info)
                except Exception as e:
                    logger.error(f"获取存档信息失败 {archive_file}: {e}")
        
        return sorted(archives, key=lambda x: x.created, reverse=True)
    
    def _get_archive_info(self, archive_path: Path) -> ArchiveInfo:
        """获取存档信息"""
        format_map = {
            '.zip': 'zip',
            '.tar.gz': 'tar.gz',
            '.tgz': 'tar.gz'
        }
        
        format_type = format_map.get(archive_path.suffix, 'unknown')
        stat = archive_path.stat()
        
        # 获取存档内容
        contents = []
        try:
            if format_type == 'zip':
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    contents = zipf.namelist()
            elif format_type == 'tar.gz':
                with tarfile.open(archive_path, 'r:gz') as tar:
                    contents = [member.name for member in tar.getmembers()]
        except:
            contents = []
        
        return ArchiveInfo(
            path=archive_path,
            format=format_type,
            size=stat.st_size,
            created=datetime.fromtimestamp(stat.st_mtime),
            contents=contents,
            metadata={'files_count': len(contents)}
        )
