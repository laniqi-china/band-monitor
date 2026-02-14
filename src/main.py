#!/usr/bin/env python3
"""
网络流量监控系统 - 主程序入口
"""

import sys
import argparse
from pathlib import Path
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import re

# 添加src目录到Python路径
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

from src.config_manager import ConfigManager
from src.file_scanner import FileScanner, LogFileInfo
from src.log_parser import LogParser, TrafficRecord
from src.report_generator import ReportGenerator
from src.email_sender import EmailSender
from src.archive_manager import ArchiveManager
from src.parallel_processor import ParallelProcessor, ProcessingPipeline
from src.utils.logger import setup_logging

class NetworkMonitor:
    """网络监控主程序"""
    
    def __init__(self, config_file: str = "config/settings.yaml"):
        # 加载配置
        self.config = ConfigManager(config_file)
        
        # 设置日志
        logging_config = self.config.get_logging_config()
        setup_logging(logging_config)
        
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        paths = self.config.get_path_config()
        
        self.file_scanner = FileScanner(paths.log_dir)
        self.log_parser = LogParser()
        self.report_generator = ReportGenerator(paths.report_dir)
        self.archive_manager = ArchiveManager(
            paths.archive_dir,
            keep_original=self.config.get_archive_config().get('keep_original', False)
        )
        
        # 邮件发送器
        email_config = self.config.get_email_config()
        self.email_sender = EmailSender(email_config)
        
        # 并行处理器
        processing_config = self.config.get_processing_config()
        self.parallel_processor = ParallelProcessor(
            max_workers=processing_config.get('max_workers', 4)
        )
    
    def generate_report(self, date_filter: str = None) -> None:
        """生成报告（主功能）"""
        self.logger.info("开始生成报告...")
        
        # 扫描日志文件
        date_files = self.file_scanner.scan_files()
        
        if not date_files:
            self.logger.info("未找到日志文件")
            return
        
        # 过滤日期
        if date_filter:
            date_files = self._filter_dates(date_files, date_filter)
        
        # 过滤已处理的日期
        paths = self.config.get_path_config()
        date_files = {
            date_key: files
            for date_key, files in date_files.items()
            if not self.file_scanner.check_report_exists(date_key, paths.report_dir)
        }
        
        if not date_files:
            self.logger.info("所有日志都已处理过")
            return
        
        self.logger.info(f"需要处理 {len(date_files)} 天的日志")
        
        # 并行处理
        results = self.parallel_processor.process_daily_logs(
            date_files, 
            self._process_single_day
        )
        
        # 处理结果
        successful_dates = []
        failed_dates = []
        
        for date_key, result in results.items():
            if result.get('success'):
                successful_dates.append(date_key)
                self.logger.info(f"日期 {date_key} 处理成功")
            else:
                failed_dates.append(date_key)
                self.logger.error(f"日期 {date_key} 处理失败: {result.get('error')}")
        
        # 总结报告
        self._generate_summary_report(successful_dates, failed_dates)
        
        # 清理旧存档
        archive_config = self.config.get_archive_config()
        if archive_config.get('clean_old_archives', False):
            retention_days = archive_config.get('retention_days', 30)
            deleted = self.archive_manager.cleanup_old_archives(retention_days)
            self.logger.info(f"清理了 {len(deleted)} 个旧存档")
        
        self.logger.info("报告生成完成")
    
    def _process_single_day(self, date_key, files: List[LogFileInfo]) -> Dict[str, Any]:
        """处理单日日志"""
        result = {'date': date_key, 'success': False}
        
        try:
            # 解析所有文件
            all_records = []
            for file_info in files:
                records = self.log_parser.parse_file(file_info)
                all_records.extend(records)
            
            if not all_records:
                result['error'] = "无有效记录"
                return result
            
            # 生成报告
            report_config = self.config.get_report_config()
            report_files = self.report_generator.generate_daily_report(
                date_key, 
                all_records,
                include_csv=report_config.get('include_csv', True),
                compress=report_config.get('compress_reports', False)
            )
            
            # 发送邮件
            paths = self.config.get_path_config()
            email_sent = self.email_sender.send_daily_report(
                date_key, 
                all_records,
                attachments=list(report_files.values())
            )
            
            # 存档日志文件
            archive_config = self.config.get_archive_config()
            if archive_config.get('enabled', True):
                log_files = [file_info.path for file_info in files]
                archive_format = archive_config.get('compress_format', 'zip')
                archive_path = self.archive_manager.archive_logs(
                    date_key, log_files, format=archive_format
                )
                result['archive_path'] = str(archive_path) if archive_path else None
            
            result.update({
                'success': True,
                'records_count': len(all_records),
                'report_files': [str(p) for p in report_files.values()],
                'email_sent': email_sent,
                'files_processed': len(files)
            })
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"处理日期 {date_key} 失败: {e}")
        
        return result
    
    def _filter_dates(self, date_files: Dict, date_filter: str) -> Dict:
        """过滤日期"""
        filtered = {}
        
        for date_key, files in date_files.items():
            date_str = date_key.strftime('%Y%m%d')
            
            # 支持多种过滤方式
            if date_filter == 'today':
                if date_key == datetime.now().date():
                    filtered[date_key] = files
            elif date_filter == 'yesterday':
                yesterday = datetime.now().date() - timedelta(days=1)
                if date_key == yesterday:
                    filtered[date_key] = files
            elif date_filter == 'week':
                week_ago = datetime.now().date() - timedelta(days=7)
                if date_key >= week_ago:
                    filtered[date_key] = files
            elif date_filter == 'month':
                month_ago = datetime.now().date() - timedelta(days=30)
                if date_key >= month_ago:
                    filtered[date_key] = files
            elif re.search(date_filter, date_str):
                # 正则匹配
                filtered[date_key] = files
        
        return filtered
    
    def _generate_summary_report(self, successful_dates: List, failed_dates: List) -> None:
        """生成汇总报告"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'successful_dates': [d.strftime('%Y-%m-%d') for d in successful_dates],
            'failed_dates': [d.strftime('%Y-%m-%d') for d in failed_dates],
            'total_processed': len(successful_dates) + len(failed_dates),
            'success_rate': len(successful_dates) / (len(successful_dates) + len(failed_dates)) * 100 
            if (len(successful_dates) + len(failed_dates)) > 0 else 0
        }
        
        # 保存汇总报告
        paths = self.config.get_path_config()
        summary_file = paths.report_dir / f"processing_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        import json
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"处理汇总报告已保存: {summary_file}")
    
    def analysis_mode(self, analysis_type: str, date_range: str = None) -> None:
        """分析模式（未来扩展）"""
        self.logger.info(f"进入分析模式: {analysis_type}")
        
        # TODO: 实现分析功能
        # 1. 趋势分析
        # 2. 异常检测
        # 3. 模式识别
        # 4. 预测模型
        
        if analysis_type == 'trend':
            self._analyze_trends(date_range)
        elif analysis_type == 'anomaly':
            self._detect_anomalies(date_range)
        elif analysis_type == 'patterns':
            self._identify_patterns(date_range)
        else:
            self.logger.error(f"不支持的分析类型: {analysis_type}")
    
    def _analyze_trends(self, date_range: str) -> None:
        """分析趋势"""
        self.logger.info("趋势分析功能开发中...")
    
    def _detect_anomalies(self, date_range: str) -> None:
        """检测异常"""
        self.logger.info("异常检测功能开发中...")
    
    def _identify_patterns(self, date_range: str) -> None:
        """识别模式"""
        self.logger.info("模式识别功能开发中...")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='网络流量监控系统')
    parser.add_argument('mode', choices=['report', 'analysis'], 
                       help='运行模式: report(生成报告), analysis(分析报告)')
    parser.add_argument('--config', '-c', default='config/settings.yaml',
                       help='配置文件路径')
    parser.add_argument('--date', '-d', help='指定日期或日期范围')
    parser.add_argument('--type', '-t', help='分析类型 (trend/anomaly/patterns)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出模式')
    
    args = parser.parse_args()
    
    try:
        # 创建监控实例
        monitor = NetworkMonitor(args.config)
        
        if args.mode == 'report':
            monitor.generate_report(args.date)
        elif args.mode == 'analysis':
            if not args.type:
                parser.error("分析模式需要指定 --type 参数")
            monitor.analysis_mode(args.type, args.date)
    
    except Exception as e:
        logging.error(f"程序执行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
