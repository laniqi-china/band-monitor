import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator
import logging
from dataclasses import dataclass, asdict
import ijson

logger = logging.getLogger(__name__)

@dataclass
class ProcessRecord:
    """进程记录"""
    pid: int
    name: str
    upload_bps: int
    download_bps: int
    connections: int

@dataclass
class ConnectionRecord:
    """连接记录"""
    pid: int
    local_interface: str
    local_port: int
    remote_address: str
    remote_port: int
    protocol: str
    upload_bps: int
    download_bps: int
    process_name: str

@dataclass
class TrafficRecord:
    """流量记录（最终输出）"""
    timestamp: datetime
    pid: int
    process_name: str
    local_interface: str
    local_port: int
    remote_address: str
    remote_port: int
    protocol: str
    upload_bps: int
    download_bps: int
    source_file: str

class LogParser:
    """日志解析器"""
    
    # 正则表达式模式
    PROCESS_PATTERN = r'process:\s*<(\d+)>\s*"([^"]+)"\s*up/down Bps:\s*(\d+)/(\d+)\s*connections:\s*(\d+)'
    CONNECTION_PATTERN = r'connection:\s*<(\d+)>\s*<([^>]+)>:(\d+)\s*=>\s*([^:]+):(\d+)\s*\((\w+)\)\s*up/down Bps:\s*(\d+)/(\d+)\s*process:\s*"([^"]+)"'
    
    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size
    
    def parse_file(self, file_info: 'LogFileInfo') -> List[TrafficRecord]:
        """解析日志文件"""
        logger.info(f"开始解析文件: {file_info.path.name}")
        
        records = []
        refresh_count = 0
        
        with open(file_info.path, 'r', encoding='utf-8') as f:
            for block_idx, block in enumerate(self._read_refresh_blocks(f)):
                if not block.strip() or '<NO TRAFFIC>' in block:
                    continue
                
                # 计算时间戳
                timestamp = file_info.base_time + timedelta(seconds=block_idx)
                
                # 解析块
                block_records = self._parse_refresh_block(block, timestamp, file_info.path.name)
                records.extend(block_records)
                refresh_count += 1
        
        logger.info(f"文件解析完成: {file_info.path.name}, 刷新次数: {refresh_count}, 记录数: {len(records)}")
        return records
    
    def _read_refresh_blocks(self, file_obj) -> Generator[str, None, None]:
        """流式读取刷新块"""
        buffer = ""
        for line in file_obj:
            if line.startswith('Refreshing:'):
                if buffer:
                    yield buffer
                    buffer = ""
            else:
                buffer += line
        if buffer:
            yield buffer
    
    def _parse_refresh_block(self, block: str, timestamp: datetime, source_file: str) -> List[TrafficRecord]:
        """解析刷新块"""
        lines = block.strip().split('\n')
        
        # 收集进程和连接信息
        process_map = {}
        connections = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 解析进程行
            if line.startswith('process:'):
                process = self._parse_process_line(line)
                if process:
                    process_map[process.pid] = process
            
            # 解析连接行
            elif line.startswith('connection:'):
                connection = self._parse_connection_line(line)
                if connection:
                    connections.append(connection)
        
        # 生成流量记录
        records = []
        for conn in connections:
            pid = conn.pid
            process_name = process_map.get(pid, ProcessRecord(pid, conn.process_name, 0, 0, 0)).name
            
            record = TrafficRecord(
                timestamp=timestamp,
                pid=pid,
                process_name=process_name,
                local_interface=conn.local_interface,
                local_port=conn.local_port,
                remote_address=conn.remote_address,
                remote_port=conn.remote_port,
                protocol=conn.protocol,
                upload_bps=conn.upload_bps,
                download_bps=conn.download_bps,
                source_file=source_file
            )
            records.append(record)
        
        return records
    
    def _parse_process_line(self, line: str) -> Optional[ProcessRecord]:
        """解析进程行"""
        match = re.match(self.PROCESS_PATTERN, line)
        if match:
            return ProcessRecord(
                pid=int(match.group(1)),
                name=match.group(2),
                upload_bps=int(match.group(3)),
                download_bps=int(match.group(4)),
                connections=int(match.group(5))
            )
        return None
    
    def _parse_connection_line(self, line: str) -> Optional[ConnectionRecord]:
        """解析连接行"""
        match = re.match(self.CONNECTION_PATTERN, line)
        if match:
            return ConnectionRecord(
                pid=int(match.group(1)),
                local_interface=match.group(2),
                local_port=int(match.group(3)),
                remote_address=match.group(4),
                remote_port=int(match.group(5)),
                protocol=match.group(6),
                upload_bps=int(match.group(7)),
                download_bps=int(match.group(8)),
                process_name=match.group(9)
            )
        return None
    
    def records_to_json(self, records: List[TrafficRecord]) -> str:
        """将记录转换为JSON格式"""
        records_dict = [asdict(record) for record in records]
        
        # 处理datetime对象
        for record in records_dict:
            record['timestamp'] = record['timestamp'].isoformat()
        
        return json.dumps(records_dict, indent=2, ensure_ascii=False)
    
    def save_to_json_file(self, records: List[TrafficRecord], output_path: Path) -> None:
        """保存记录到JSON文件"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 流式写入JSON文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('[\n')
            
            for i, record in enumerate(records):
                record_dict = asdict(record)
                record_dict['timestamp'] = record_dict['timestamp'].isoformat()
                
                json_line = json.dumps(record_dict, ensure_ascii=False)
                if i < len(records) - 1:
                    f.write(f'  {json_line},\n')
                else:
                    f.write(f'  {json_line}\n')
            
            f.write(']\n')
        
        logger.info(f"记录已保存到: {output_path}")
