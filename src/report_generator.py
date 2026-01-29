import json
import pandas as pd
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
import csv
import numpy as np
from dataclasses import asdict
from collections import defaultdict

logger = logging.getLogger(__name__)

class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_daily_report(self, date_key: date, 
                            records: List[Any],
                            include_csv: bool = True,
                            compress: bool = False) -> Dict[str, Path]:
        """生成每日报告"""
        date_str = date_key.strftime('%Y%m%d')
        
        if not records:
            logger.warning(f"日期 {date_str} 无记录")
            return {}
        
        # 转换为DataFrame以便分析
        df = pd.DataFrame([asdict(r) for r in records])
        
        # 保存详细报告（JSON格式）
        report_files = self._save_detailed_report(date_str, df)
        
        # 生成汇总报告
        summary_files = self._generate_summary_report(date_str, df)
        
        # 生成统计报告
        stats_files = self._generate_statistics_report(date_str, df)
        
        # 合并所有文件
        all_files = {**report_files, **summary_files, **stats_files}
        
        # 如果需要压缩
        if compress:
            compressed_file = self._compress_reports(date_str, all_files.values())
            all_files['compressed'] = compressed_file
        
        logger.info(f"日期 {date_str} 报告生成完成")
        return all_files
    
    def _save_detailed_report(self, date_str: str, df: pd.DataFrame) -> Dict[str, Path]:
        """保存详细报告"""
        report_files = {}
        
        # JSON格式（主格式）
        json_file = self.output_dir / f"report_{date_str}.json"
        df.to_json(json_file, orient='records', indent=2, date_format='iso')
        report_files['json'] = json_file
        
        # CSV格式（可选）
        csv_file = self.output_dir / f"report_{date_str}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        report_files['csv'] = csv_file
        
        # Parquet格式（可选，更高效）
        try:
            parquet_file = self.output_dir / f"report_{date_str}.parquet"
            df.to_parquet(parquet_file, index=False)
            report_files['parquet'] = parquet_file
        except Exception as e:
            logger.warning(f"无法保存Parquet格式: {e}")
        
        return report_files
    
    def _generate_summary_report(self, date_str: str, df: pd.DataFrame) -> Dict[str, Path]:
        """生成汇总报告"""
        summary_files = {}
        
        # 1. 进程汇总
        process_summary = self._calculate_process_summary(df)
        
        # 2. 远程地址汇总
        remote_summary = self._calculate_remote_summary(df)
        
        # 3. 时间窗口汇总
        time_summary = self._calculate_time_summary(df)
        
        # 保存汇总报告
        summary_file = self.output_dir / f"summary_{date_str}.json"
        
        summary_data = {
            'date': date_str,
            'overview': {
                'total_records': len(df),
                'unique_processes': df['process_name'].nunique(),
                'unique_remote_addresses': df['remote_address'].nunique(),
                'total_upload_mb': df['upload_bps'].sum() / (1024 * 1024),
                'total_download_mb': df['download_bps'].sum() / (1024 * 1024),
                'time_span': {
                    'start': df['timestamp'].min(),
                    'end': df['timestamp'].max(),
                    'duration_hours': (
                        df['timestamp'].max() - df['timestamp'].min()
                    ).total_seconds() / 3600
                }
            },
            'process_summary': process_summary.to_dict(orient='records'),
            'remote_summary': remote_summary.to_dict(orient='records'),
            'time_summary': time_summary.to_dict(),
            'top_items': {
                'top_processes_by_upload': self._get_top_items(df, 'process_name', 'upload_bps', 10),
                'top_processes_by_download': self._get_top_items(df, 'process_name', 'download_bps', 10),
                'top_remotes_by_traffic': self._get_top_items(df, 'remote_address', 
                                                              lambda x: x['upload_bps'] + x['download_bps'], 10),
                'most_active_ports': self._get_top_items(df, 'local_port', 'count', 10)
            }
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False, default=str)
        
        summary_files['summary_json'] = summary_file
        
        # 保存CSV格式汇总
        csv_file = self.output_dir / f"summary_{date_str}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入概览
            writer.writerow(['=== 概览 ==='])
            for key, value in summary_data['overview'].items():
                writer.writerow([key, value])
            
            writer.writerow([])
            writer.writerow(['=== 进程汇总 ==='])
            process_summary.to_csv(f, index=False)
            
            writer.writerow([])
            writer.writerow(['=== 远程地址汇总 ==='])
            remote_summary.to_csv(f, index=False)
        
        summary_files['summary_csv'] = csv_file
        
        return summary_files
    
    def _calculate_process_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算进程汇总"""
        if df.empty:
            return pd.DataFrame()
        
        summary = df.groupby('process_name').agg({
            'upload_bps': ['sum', 'mean', 'max', 'std'],
            'download_bps': ['sum', 'mean', 'max', 'std'],
            'pid': 'nunique',
            'remote_address': 'nunique'
        }).round(2)
        
        # 重命名列
        summary.columns = [
            'upload_sum', 'upload_mean', 'upload_max', 'upload_std',
            'download_sum', 'download_mean', 'download_max', 'download_std',
            'unique_pids', 'unique_remotes'
        ]
        
        # 计算总流量和占比
        total_upload = summary['upload_sum'].sum()
        total_download = summary['download_sum'].sum()
        
        summary['upload_pct'] = (summary['upload_sum'] / total_upload * 100).round(2)
        summary['download_pct'] = (summary['download_sum'] / total_download * 100).round(2)
        
        return summary.reset_index()
    
    def _calculate_remote_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算远程地址汇总"""
        if df.empty:
            return pd.DataFrame()
        
        summary = df.groupby('remote_address').agg({
            'upload_bps': ['sum', 'mean', 'max'],
            'download_bps': ['sum', 'mean', 'max'],
            'process_name': 'nunique',
            'protocol': lambda x: x.mode()[0] if not x.empty else ''
        }).round(2)
        
        summary.columns = [
            'upload_sum', 'upload_mean', 'upload_max',
            'download_sum', 'download_mean', 'download_max',
            'unique_processes', 'common_protocol'
        ]
        
        # 添加域名解析（如果有）
        summary['is_ip'] = summary.index.map(lambda x: self._is_ip_address(x))
        
        return summary.reset_index()
    
    def _calculate_time_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算时间窗口汇总"""
        if df.empty:
            return {}
        
        # 按小时汇总
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        hourly_summary = df.groupby('hour').agg({
            'upload_bps': 'sum',
            'download_bps': 'sum',
            'process_name': 'nunique'
        }).round(2).to_dict()
        
        return {'hourly': hourly_summary}
    
    def _get_top_items(self, df: pd.DataFrame, group_by: str, 
                      metric: Any, top_n: int) -> List[Dict[str, Any]]:
        """获取排名前N的项目"""
        if df.empty:
            return []
        
        if callable(metric):
            # 使用自定义函数
            grouped = df.groupby(group_by).apply(metric)
        else:
            # 使用列名
            if metric == 'count':
                grouped = df.groupby(group_by).size()
            else:
                grouped = df.groupby(group_by)[metric].sum()
        
        top_items = grouped.nlargest(top_n)
        
        return [
            {'item': idx, 'value': float(val)}
            for idx, val in top_items.items()
        ]
    
    def _is_ip_address(self, address: str) -> bool:
        """检查是否为IP地址"""
        import re
        ip_pattern = r'^\d{1,3}(\.\d{1,3}){3}$'
        return bool(re.match(ip_pattern, address))
    
    def _generate_statistics_report(self, date_str: str, df: pd.DataFrame) -> Dict[str, Path]:
        """生成统计报告"""
        if df.empty:
            return {}
        
        # 计算各种统计指标
        stats = {
            'date': date_str,
            'traffic_statistics': {
                'upload': {
                    'total_bytes': int(df['upload_bps'].sum()),
                    'average_bps': float(df['upload_bps'].mean()),
                    'max_bps': int(df['upload_bps'].max()),
                    'percentiles': {
                        'p50': float(df['upload_bps'].quantile(0.5)),
                        'p90': float(df['upload_bps'].quantile(0.9)),
                        'p95': float(df['upload_bps'].quantile(0.95)),
                        'p99': float(df['upload_bps'].quantile(0.99))
                    }
                },
                'download': {
                    'total_bytes': int(df['download_bps'].sum()),
                    'average_bps': float(df['download_bps'].mean()),
                    'max_bps': int(df['download_bps'].max()),
                    'percentiles': {
                        'p50': float(df['download_bps'].quantile(0.5)),
                        'p90': float(df['download_bps'].quantile(0.9)),
                        'p95': float(df['download_bps'].quantile(0.95)),
                        'p99': float(df['download_bps'].quantile(0.99))
                    }
                }
            },
            'connection_statistics': {
                'total_connections': len(df),
                'unique_ports': df['local_port'].nunique(),
                'ports_distribution': df['local_port'].value_counts().head(20).to_dict(),
                'protocol_distribution': df['protocol'].value_counts().to_dict()
            },
            'process_statistics': {
                'total_processes': df['process_name'].nunique(),
                'process_distribution': df['process_name'].value_counts().head(20).to_dict(),
                'process_with_most_connections': df.groupby('process_name').size().idxmax(),
                'process_with_most_traffic': df.groupby('process_name')['upload_bps'].sum().idxmax()
            }
        }
        
        # 保存统计报告
        stats_file = self.output_dir / f"stats_{date_str}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False, default=str)
        
        return {'stats_json': stats_file}
    
    def _compress_reports(self, date_str: str, files: List[Path]) -> Path:
        """压缩报告文件"""
        import zipfile
        
        zip_file = self.output_dir / f"reports_{date_str}.zip"
        
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                if file_path.exists():
                    zipf.write(file_path, file_path.name)
        
        return zip_file
