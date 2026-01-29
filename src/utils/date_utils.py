from datetime import datetime, date, timedelta
from typing import Union, Optional, List, Tuple, Dict, Any
import time
import re
from dateutil.relativedelta import relativedelta
import pytz
from zoneinfo import ZoneInfo

class DateUtils:
    """日期时间工具类"""
    
    # 常见日期格式
    DATE_FORMATS = [
        '%Y-%m-%d', '%Y%m%d', '%d/%m/%Y', '%m/%d/%Y',
        '%Y-%m-%d %H:%M:%S', '%Y%m%d %H%M%S', '%Y%m%d_%H%M%S',
        '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ'
    ]
    
    @staticmethod
    def parse_date(date_str: str, formats: List[str] = None) -> Optional[date]:
        """解析日期字符串"""
        if formats is None:
            formats = DateUtils.DATE_FORMATS
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.date()
            except ValueError:
                continue
        
        # 尝试从bandwhich文件名提取
        match = re.search(r'bandwhich_(\d{8})_\d{4}\.log', date_str)
        if match:
            try:
                return datetime.strptime(match.group(1), '%Y%m%d').date()
            except ValueError:
                pass
        
        return None
    
    @staticmethod
    def parse_datetime(datetime_str: str, formats: List[str] = None) -> Optional[datetime]:
        """解析日期时间字符串"""
        if formats is None:
            formats = DateUtils.DATE_FORMATS
        
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        
        # 尝试ISO格式
        try:
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        return None
    
    @staticmethod
    def get_date_range(start_date: Union[str, date, datetime], 
                      end_date: Union[str, date, datetime] = None,
                      step_days: int = 1) -> List[date]:
        """获取日期范围"""
        start = DateUtils.ensure_date(start_date)
        
        if end_date is None:
            end = date.today()
        else:
            end = DateUtils.ensure_date(end_date)
        
        if start > end:
            start, end = end, start
        
        date_list = []
        current = start
        while current <= end:
            date_list.append(current)
            current += timedelta(days=step_days)
        
        return date_list
    
    @staticmethod
    def ensure_date(date_obj: Union[str, date, datetime]) -> date:
        """确保返回date对象"""
        if isinstance(date_obj, str):
            parsed = DateUtils.parse_date(date_obj)
            if parsed is None:
                raise ValueError(f"无法解析日期字符串: {date_obj}")
            return parsed
        elif isinstance(date_obj, datetime):
            return date_obj.date()
        elif isinstance(date_obj, date):
            return date_obj
        else:
            raise TypeError(f"不支持的日期类型: {type(date_obj)}")
    
    @staticmethod
    def ensure_datetime(datetime_obj: Union[str, date, datetime], 
                       timezone: str = None) -> datetime:
        """确保返回datetime对象"""
        if isinstance(datetime_obj, str):
            parsed = DateUtils.parse_datetime(datetime_obj)
            if parsed is None:
                # 尝试作为纯日期处理
                date_part = DateUtils.ensure_date(datetime_obj)
                parsed = datetime.combine(date_part, datetime.min.time())
            return parsed
        elif isinstance(datetime_obj, date):
            return datetime.combine(datetime_obj, datetime.min.time())
        elif isinstance(datetime_obj, datetime):
            return datetime_obj
        else:
            raise TypeError(f"不支持的日期时间类型: {type(datetime_obj)}")
    
    @staticmethod
    def format_date(date_obj: Union[date, datetime], 
                   format_str: str = '%Y-%m-%d') -> str:
        """格式化日期"""
        if isinstance(date_obj, datetime):
            return date_obj.strftime(format_str)
        elif isinstance(date_obj, date):
            return date_obj.strftime(format_str)
        else:
            raise TypeError(f"不支持的日期类型: {type(date_obj)}")
    
    @staticmethod
    def get_week_range(target_date: Union[str, date, datetime] = None) -> Tuple[date, date]:
        """获取周范围（周一到周日）"""
        if target_date is None:
            target_date = date.today()
        else:
            target_date = DateUtils.ensure_date(target_date)
        
        # 获取周一（0=Monday, 6=Sunday）
        weekday = target_date.weekday()
        start = target_date - timedelta(days=weekday)
        end = start + timedelta(days=6)
        
        return start, end
    
    @staticmethod
    def get_month_range(target_date: Union[str, date, datetime] = None) -> Tuple[date, date]:
        """获取月范围"""
        if target_date is None:
            target_date = date.today()
        else:
            target_date = DateUtils.ensure_date(target_date)
        
        start = date(target_date.year, target_date.month, 1)
        
        if target_date.month == 12:
            end = date(target_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)
        
        return start, end
    
    @staticmethod
    def get_quarter_range(target_date: Union[str, date, datetime] = None) -> Tuple[date, date]:
        """获取季度范围"""
        if target_date is None:
            target_date = date.today()
        else:
            target_date = DateUtils.ensure_date(target_date)
        
        quarter = (target_date.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        
        start = date(target_date.year, start_month, 1)
        
        if end_month == 12:
            end = date(target_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(target_date.year, end_month + 1, 1) - timedelta(days=1)
        
        return start, end
    
    @staticmethod
    def is_workday(target_date: Union[str, date, datetime], 
                  holidays: List[date] = None) -> bool:
        """判断是否为工作日"""
        target_date = DateUtils.ensure_date(target_date)
        
        # 周末判断
        if target_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            return False
        
        # 节假日判断
        if holidays and target_date in holidays:
            return False
        
        return True
    
    @staticmethod
    def calculate_time_difference(start: Union[str, datetime], 
                                end: Union[str, datetime],
                                unit: str = 'seconds') -> float:
        """计算时间差"""
        start_dt = DateUtils.ensure_datetime(start)
        end_dt = DateUtils.ensure_datetime(end)
        
        diff_seconds = (end_dt - start_dt).total_seconds()
        
        unit_map = {
            'seconds': 1,
            'minutes': 60,
            'hours': 3600,
            'days': 86400,
            'weeks': 604800
        }
        
        if unit not in unit_map:
            raise ValueError(f"不支持的时间单位: {unit}")
        
        return diff_seconds / unit_map[unit]
    
    @staticmethod
    def round_to_nearest(dt: datetime, 
                        minutes: int = 15,
                        rounding: str = 'nearest') -> datetime:
        """将时间舍入到最接近的时间间隔"""
        if minutes <= 0:
            return dt
        
        total_minutes = dt.hour * 60 + dt.minute
        remainder = total_minutes % minutes
        
        if rounding == 'nearest':
            if remainder >= minutes / 2:
                total_minutes = total_minutes - remainder + minutes
            else:
                total_minutes = total_minutes - remainder
        elif rounding == 'floor':
            total_minutes = total_minutes - remainder
        elif rounding == 'ceil':
            if remainder > 0:
                total_minutes = total_minutes - remainder + minutes
        else:
            raise ValueError(f"不支持的舍入方式: {rounding}")
        
        hour = total_minutes // 60
        minute = total_minutes % 60
        
        return dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    @staticmethod
    def convert_timezone(dt: datetime, 
                        from_tz: str = 'UTC',
                        to_tz: str = 'Asia/Shanghai') -> datetime:
        """转换时区"""
        try:
            from_zone = ZoneInfo(from_tz) if from_tz else ZoneInfo('UTC')
            to_zone = ZoneInfo(to_tz)
        except Exception:
            # 回退到pytz
            from_zone = pytz.timezone(from_tz) if from_tz else pytz.UTC
            to_zone = pytz.timezone(to_tz)
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=from_zone)
        
        return dt.astimezone(to_zone)

class DateRange:
    """日期范围类"""
    
    def __init__(self, start: date, end: date):
        self.start = start
        self.end = end
    
    def __contains__(self, date_obj: date) -> bool:
        return self.start <= date_obj <= self.end
    
    def __iter__(self):
        current = self.start
        while current <= self.end:
            yield current
            current += timedelta(days=1)
    
    def __len__(self) -> int:
        return (self.end - self.start).days + 1
    
    def __str__(self) -> str:
        return f"{self.start} 到 {self.end} ({len(self)}天)"
    
    def split_by_week(self) -> List['DateRange']:
        """按周拆分"""
        ranges = []
        current = self.start
        
        while current <= self.end:
            week_start = current
            week_end = min(week_start + timedelta(days=6), self.end)
            ranges.append(DateRange(week_start, week_end))
            current = week_end + timedelta(days=1)
        
        return ranges
    
    def split_by_month(self) -> List['DateRange']:
        """按月拆分"""
        ranges = []
        current = self.start
        
        while current <= self.end:
            month_start = date(current.year, current.month, 1)
            if month_start < self.start:
                month_start = self.start
            
            if current.month == 12:
                month_end = date(current.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(current.year, current.month + 1, 1) - timedelta(days=1)
            
            month_end = min(month_end, self.end)
            ranges.append(DateRange(month_start, month_end))
            
            current = month_end + timedelta(days=1)
        
        return ranges

# 使用示例
if __name__ == '__main__':
    # 测试日期工具
    print("今日:", DateUtils.format_date(date.today()))
    print("解析日期:", DateUtils.parse_date("20231219"))
    
    # 测试日期范围
    dr = DateRange(date(2023, 1, 1), date(2023, 1, 10))
    print("日期范围:", dr)
    print("天数:", len(dr))
    print("包含2023-01-05:", date(2023, 1, 5) in dr)
    
    # 测试时区转换
    dt = datetime.now()
    print("当前时间:", dt)
    print("转换到上海:", DateUtils.convert_timezone(dt, to_tz='Asia/Shanghai'))
