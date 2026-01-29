import concurrent.futures
from datetime import date
from pathlib import Path
from typing import Dict, List, Any, Callable, Tuple
import logging
import threading
from queue import Queue
import time

logger = logging.getLogger(__name__)

class ParallelProcessor:
    """并行处理器"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = None
        self._lock = threading.Lock()
        self._results = {}
        self._errors = {}
    
    def process_daily_logs(self, date_files: Dict[date, List['LogFileInfo']], 
                          process_func: Callable) -> Dict[date, Any]:
        """并行处理多天的日志"""
        logger.info(f"开始并行处理，工作线程数: {self.max_workers}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交任务
            future_to_date = {
                executor.submit(self._process_single_date, date_key, files, process_func): date_key
                for date_key, files in date_files.items()
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_date):
                date_key = future_to_date[future]
                try:
                    result = future.result()
                    with self._lock:
                        self._results[date_key] = result
                    logger.info(f"日期 {date_key} 处理完成")
                except Exception as e:
                    with self._lock:
                        self._errors[date_key] = str(e)
                    logger.error(f"日期 {date_key} 处理失败: {e}")
        
        logger.info(f"并行处理完成: 成功 {len(self._results)}, 失败 {len(self._errors)}")
        return self._results
    
    def _process_single_date(self, date_key: date, files: List['LogFileInfo'], 
                           process_func: Callable) -> Any:
        """处理单日日志"""
        try:
            return process_func(date_key, files)
        except Exception as e:
            logger.error(f"处理日期 {date_key} 时出错: {e}")
            raise
    
    def get_results(self) -> Dict[date, Any]:
        """获取处理结果"""
        return self._results
    
    def get_errors(self) -> Dict[date, str]:
        """获取错误信息"""
        return self._errors
    
    def process_in_batches(self, items: List[Any], process_func: Callable, 
                          batch_size: int = 100) -> List[Any]:
        """批量处理项目"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            batch_results = self._process_batch(batch, process_func)
            results.extend(batch_results)
            
            logger.info(f"批次处理进度: {min(i+batch_size, len(items))}/{len(items)}")
        
        return results
    
    def _process_batch(self, batch: List[Any], process_func: Callable) -> List[Any]:
        """处理单个批次"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(process_func, item) for item in batch]
            
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"批次处理失败: {e}")
                    results.append(None)
            
            return results

class ProcessingPipeline:
    """处理管道"""
    
    def __init__(self):
        self.stages = []
        self.context = {}
    
    def add_stage(self, name: str, func: Callable, 
                  depends_on: List[str] = None) -> 'ProcessingPipeline':
        """添加处理阶段"""
        self.stages.append({
            'name': name,
            'func': func,
            'depends_on': depends_on or []
        })
        return self
    
    def run(self, initial_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行处理管道"""
        if initial_context:
            self.context.update(initial_context)
        
        executed = set()
        
        while len(executed) < len(self.stages):
            for stage in self.stages:
                if stage['name'] in executed:
                    continue
                
                # 检查依赖
                deps_met = all(dep in executed for dep in stage['depends_on'])
                if deps_met or not stage['depends_on']:
                    logger.info(f"执行阶段: {stage['name']}")
                    
                    try:
                        result = stage['func'](self.context)
                        self.context[stage['name']] = result
                        executed.add(stage['name'])
                        
                        logger.info(f"阶段完成: {stage['name']}")
                    except Exception as e:
                        logger.error(f"阶段失败 {stage['name']}: {e}")
                        raise
        
        return self.context
