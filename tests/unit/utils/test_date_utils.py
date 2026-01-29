# tests/unit/utils/test_date_utils.py
import pytest
from datetime import datetime, date, timedelta
from src.utils.date_utils import DateUtils, DateRange


class TestDateUtils:
    """测试日期时间工具类"""

    def test_parse_date_valid(self):
        """测试解析有效的日期字符串"""
        # 各种格式
        test_cases = [
            ("2024-01-01", date(2024, 1, 1)),
            ("20240101", date(2024, 1, 1)),
            ("01/01/2024", date(2024, 1, 1)),
            ("2024-01-01 12:00:00", date(2024, 1, 1)),
            ("2024-01-01T12:00:00", date(2024, 1, 1)),
        ]

        for date_str, expected in test_cases:
            result = DateUtils.parse_date(date_str)
            assert result == expected

    def test_parse_date_from_bandwhich_filename(self):
        """测试从bandwhich文件名解析日期"""
        filename = "bandwhich_20240101_1200.log"
        result = DateUtils.parse_date(filename)

        assert result == date(2024, 1, 1)

    def test_parse_date_invalid(self):
        """测试解析无效的日期字符串"""
        invalid_cases = [
            "",
            "invalid",
            "2024-13-01",  # 无效月份
            "2024-01-32",  # 无效日期
            "20240101_invalid",
        ]

        for date_str in invalid_cases:
            result = DateUtils.parse_date(date_str)
            assert result is None

    def test_parse_datetime_valid(self):
        """测试解析有效的日期时间字符串"""
        test_cases = [
            ("2024-01-01 12:00:00", datetime(2024, 1, 1, 12, 0, 0)),
            ("20240101 120000", datetime(2024, 1, 1, 12, 0, 0)),
            ("2024-01-01T12:00:00", datetime(2024, 1, 1, 12, 0, 0)),
            ("2024-01-01T12:00:00Z", datetime(2024, 1, 1, 12, 0, 0)),
            ("2024-01-01T12:00:00.123456Z", datetime(2024, 1, 1, 12, 0, 0, 123456)),
        ]

        for datetime_str, expected in test_cases:
            result = DateUtils.parse_datetime(datetime_str)
            assert result == expected

    def test_parse_datetime_iso_format(self):
        """测试解析ISO格式"""
        # ISO格式应该能正确解析
        iso_str = "2024-01-01T12:30:45.123456+08:00"
        result = DateUtils.parse_datetime(iso_str)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 45

    def test_parse_datetime_invalid(self):
        """测试解析无效的日期时间字符串"""
        invalid_cases = ["", "invalid", "2024-13-01 12:00:00", "2024-01-01 25:00:00"]

        for datetime_str in invalid_cases:
            result = DateUtils.parse_datetime(datetime_str)
            assert result is None

    def test_get_date_range(self):
        """测试获取日期范围"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)

        # 默认步长
        date_range = DateUtils.get_date_range(start, end)

        assert len(date_range) == 5
        assert date_range[0] == start
        assert date_range[-1] == end

        # 指定步长
        date_range_step2 = DateUtils.get_date_range(start, end, step_days=2)

        assert len(date_range_step2) == 3
        assert date_range_step2 == [
            date(2024, 1, 1),
            date(2024, 1, 3),
            date(2024, 1, 5),
        ]

        # 只指定开始日期
        today_range = DateUtils.get_date_range(start)
        assert len(today_range) >= 1
        assert today_range[0] == start

    def test_get_date_range_string_input(self):
        """测试字符串输入获取日期范围"""
        start = "2024-01-01"
        end = "2024-01-03"

        date_range = DateUtils.get_date_range(start, end)

        assert len(date_range) == 3
        assert date_range[0] == date(2024, 1, 1)
        assert date_range[1] == date(2024, 1, 2)
        assert date_range[2] == date(2024, 1, 3)

    def test_get_date_range_reversed(self):
        """测试开始日期晚于结束日期的日期范围"""
        start = date(2024, 1, 5)
        end = date(2024, 1, 1)

        date_range = DateUtils.get_date_range(start, end)

        # 应该自动交换开始和结束
        assert date_range[0] == date(2024, 1, 1)
        assert date_range[-1] == date(2024, 1, 5)

    def test_ensure_date(self):
        """测试确保返回date对象"""
        # date对象
        d = date(2024, 1, 1)
        assert DateUtils.ensure_date(d) == d

        # datetime对象
        dt = datetime(2024, 1, 1, 12, 0, 0)
        assert DateUtils.ensure_date(dt) == date(2024, 1, 1)

        # 字符串
        assert DateUtils.ensure_date("2024-01-01") == date(2024, 1, 1)

        # 无效类型
        with pytest.raises(TypeError):
            DateUtils.ensure_date(123)

    def test_ensure_datetime(self):
        """测试确保返回datetime对象"""
        # datetime对象
        dt = datetime(2024, 1, 1, 12, 0, 0)
        assert DateUtils.ensure_datetime(dt) == dt

        # date对象
        d = date(2024, 1, 1)
        result = DateUtils.ensure_datetime(d)
        assert result.date() == d
        assert result.time() == datetime.min.time()  # 00:00:00

        # 字符串
        assert DateUtils.ensure_datetime("2024-01-01 12:00:00") == datetime(
            2024, 1, 1, 12, 0, 0
        )

        # 纯日期字符串
        result = DateUtils.ensure_datetime("2024-01-01")
        assert result.date() == date(2024, 1, 1)
        assert result.time() == datetime.min.time()

    def test_format_date(self):
        """测试格式化日期"""
        d = date(2024, 1, 1)
        dt = datetime(2024, 1, 1, 12, 30, 45)

        # 默认格式
        assert DateUtils.format_date(d) == "2024-01-01"
        assert DateUtils.format_date(dt) == "2024-01-01"

        # 自定义格式
        assert DateUtils.format_date(d, "%Y/%m/%d") == "2024/01/01"
        assert DateUtils.format_date(dt, "%Y-%m-%d %H:%M:%S") == "2024-01-01 12:30:45"

    def test_get_week_range(self):
        """测试获取周范围"""
        # 2024-01-01 是周一
        test_date = date(2024, 1, 1)
        start, end = DateUtils.get_week_range(test_date)

        assert start == date(2024, 1, 1)  # 周一
        assert end == date(2024, 1, 7)  # 周日

        # 2024-01-15 是周一
        test_date2 = date(2024, 1, 15)
        start2, end2 = DateUtils.get_week_range(test_date2)

        assert start2 == date(2024, 1, 15)
        assert end2 == date(2024, 1, 21)

        # 使用默认值（今天）
        today = date.today()
        start_today, end_today = DateUtils.get_week_range()

        # 应该是本周的周一到周日
        assert start_today.weekday() == 0  # 周一
        assert end_today.weekday() == 6  # 周日
        assert start_today <= today <= end_today

    def test_get_month_range(self):
        """测试获取月范围"""
        test_date = date(2024, 1, 15)
        start, end = DateUtils.get_month_range(test_date)

        assert start == date(2024, 1, 1)
        assert end == date(2024, 1, 31)

        # 二月（闰年）
        test_date2 = date(2024, 2, 15)
        start2, end2 = DateUtils.get_month_range(test_date2)

        assert start2 == date(2024, 2, 1)
        assert end2 == date(2024, 2, 29)

        # 十二月
        test_date3 = date(2024, 12, 15)
        start3, end3 = DateUtils.get_month_range(test_date3)

        assert start3 == date(2024, 12, 1)
        assert end3 == date(2024, 12, 31)

    def test_get_quarter_range(self):
        """测试获取季度范围"""
        # 第一季度
        q1_date = date(2024, 2, 15)
        q1_start, q1_end = DateUtils.get_quarter_range(q1_date)

        assert q1_start == date(2024, 1, 1)
        assert q1_end == date(2024, 3, 31)

        # 第二季度
        q2_date = date(2024, 5, 15)
        q2_start, q2_end = DateUtils.get_quarter_range(q2_date)

        assert q2_start == date(2024, 4, 1)
        assert q2_end == date(2024, 6, 30)

        # 第四季度
        q4_date = date(2024, 11, 15)
        q4_start, q4_end = DateUtils.get_quarter_range(q4_date)

        assert q4_start == date(2024, 10, 1)
        assert q4_end == date(2024, 12, 31)

    def test_is_workday(self):
        """测试判断工作日"""
        # 周一
        monday = date(2024, 1, 1)  # 2024-01-01是周一
        assert DateUtils.is_workday(monday) is True

        # 周六
        saturday = date(2024, 1, 6)  # 2024-01-06是周六
        assert DateUtils.is_workday(saturday) is False

        # 周日
        sunday = date(2024, 1, 7)  # 2024-01-07是周日
        assert DateUtils.is_workday(sunday) is False

        # 带节假日
        holidays = [date(2024, 1, 1)]  # 元旦
        assert DateUtils.is_workday(monday, holidays) is False

    def test_calculate_time_difference(self):
        """测试计算时间差"""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 13, 30, 0)  # 1.5小时后

        # 秒
        seconds = DateUtils.calculate_time_difference(start, end, "seconds")
        assert seconds == 90 * 60  # 90分钟 * 60秒

        # 分钟
        minutes = DateUtils.calculate_time_difference(start, end, "minutes")
        assert minutes == 90

        # 小时
        hours = DateUtils.calculate_time_difference(start, end, "hours")
        assert hours == 1.5

        # 天
        start2 = datetime(2024, 1, 1, 12, 0, 0)
        end2 = datetime(2024, 1, 3, 12, 0, 0)  # 2天后
        days = DateUtils.calculate_time_difference(start2, end2, "days")
        assert days == 2.0

        # 字符串输入
        seconds_str = DateUtils.calculate_time_difference(
            "2024-01-01 12:00:00", "2024-01-01 13:30:00", "seconds"
        )
        assert seconds_str == 90 * 60

    def test_calculate_time_difference_invalid_unit(self):
        """测试计算时间差使用无效单位"""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 13, 0, 0)

        with pytest.raises(ValueError, match="不支持的时间单位"):
            DateUtils.calculate_time_difference(start, end, "invalid")

    def test_round_to_nearest(self):
        """测试将时间舍入到最接近的时间间隔"""
        dt = datetime(2024, 1, 1, 12, 7, 30)

        # 最接近的15分钟
        rounded = DateUtils.round_to_nearest(dt, minutes=15, rounding="nearest")
        assert rounded == datetime(2024, 1, 1, 12, 0, 0)

        dt2 = datetime(2024, 1, 1, 12, 8, 30)
        rounded2 = DateUtils.round_to_nearest(dt2, minutes=15, rounding="nearest")
        assert rounded2 == datetime(2024, 1, 1, 12, 15, 0)

        # 向下舍入
        floor = DateUtils.round_to_nearest(dt, minutes=15, rounding="floor")
        assert floor == datetime(2024, 1, 1, 12, 0, 0)

        # 向上舍入
        ceil = DateUtils.round_to_nearest(dt, minutes=15, rounding="ceil")
        assert ceil == datetime(2024, 1, 1, 12, 15, 0)

    def test_round_to_nearest_edge_cases(self):
        """测试舍入的边缘情况"""
        # 正好在边界上
        dt = datetime(2024, 1, 1, 12, 0, 0)
        rounded = DateUtils.round_to_nearest(dt, minutes=15, rounding="nearest")
        assert rounded == dt

        # 负分钟数
        dt2 = datetime(2024, 1, 1, 12, 0, 0)
        rounded2 = DateUtils.round_to_nearest(dt2, minutes=0, rounding="nearest")
        assert rounded2 == dt2  # 应该返回原时间

    def test_convert_timezone(self):
        """测试转换时区"""
        # 北京时间中午12点
        dt = datetime(2024, 1, 1, 12, 0, 0)

        # 转换为UTC
        utc_time = DateUtils.convert_timezone(dt, "Asia/Shanghai", "UTC")

        # 北京时间比UTC早8小时
        assert utc_time.hour == 4  # 12 - 8 = 4

        # 从UTC转换回来
        shanghai_time = DateUtils.convert_timezone(utc_time, "UTC", "Asia/Shanghai")
        assert shanghai_time.hour == 12

        # 无时区信息，默认UTC
        dt_no_tz = datetime(2024, 1, 1, 12, 0, 0)
        converted = DateUtils.convert_timezone(dt_no_tz, to_tz="Asia/Shanghai")
        assert converted.tzinfo is not None


class TestDateRange:
    """测试日期范围类"""

    def test_initialization(self):
        """测试初始化"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)

        dr = DateRange(start, end)

        assert dr.start == start
        assert dr.end == end

    def test_contains(self):
        """测试包含关系"""
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 5))

        # 范围内的日期
        assert date(2024, 1, 1) in dr
        assert date(2024, 1, 3) in dr
        assert date(2024, 1, 5) in dr

        # 范围外的日期
        assert date(2023, 12, 31) not in dr
        assert date(2024, 1, 6) not in dr

    def test_iteration(self):
        """测试迭代"""
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 3))

        dates = list(dr)

        assert len(dates) == 3
        assert dates[0] == date(2024, 1, 1)
        assert dates[1] == date(2024, 1, 2)
        assert dates[2] == date(2024, 1, 3)

    def test_length(self):
        """测试长度计算"""
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 5))

        assert len(dr) == 5  # 包含首尾

        # 单日范围
        dr_single = DateRange(date(2024, 1, 1), date(2024, 1, 1))
        assert len(dr_single) == 1

    def test_str_representation(self):
        """测试字符串表示"""
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 5))

        s = str(dr)

        assert "2024-01-01" in s
        assert "2024-01-05" in s
        assert "5天" in s

    def test_split_by_week(self):
        """测试按周拆分"""
        # 跨两周的范围
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 14))

        weeks = dr.split_by_week()

        # 应该拆分为两周
        assert len(weeks) == 2

        # 第一周
        assert weeks[0].start == date(2024, 1, 1)
        assert weeks[0].end == date(2024, 1, 7)

        # 第二周
        assert weeks[1].start == date(2024, 1, 8)
        assert weeks[1].end == date(2024, 1, 14)

    def test_split_by_week_partial(self):
        """测试按周拆分部分周"""
        # 从周中开始
        dr = DateRange(date(2024, 1, 3), date(2024, 1, 10))

        weeks = dr.split_by_week()

        # 第一周（部分周）
        assert weeks[0].start == date(2024, 1, 3)
        assert weeks[0].end == date(2024, 1, 7)

        # 第二周（部分周）
        assert weeks[1].start == date(2024, 1, 8)
        assert weeks[1].end == date(2024, 1, 10)

    def test_split_by_month(self):
        """测试按月拆分"""
        # 跨两个月的范围
        dr = DateRange(date(2024, 1, 15), date(2024, 2, 15))

        months = dr.split_by_month()

        # 应该拆分为两个月
        assert len(months) == 2

        # 一月
        assert months[0].start == date(2024, 1, 15)
        assert months[0].end == date(2024, 1, 31)

        # 二月
        assert months[1].start == date(2024, 2, 1)
        assert months[1].end == date(2024, 2, 15)

    def test_split_by_month_multiple(self):
        """测试跨越多个月份的拆分"""
        dr = DateRange(date(2024, 1, 10), date(2024, 3, 20))

        months = dr.split_by_month()

        # 应该拆分为三个月
        assert len(months) == 3

        assert months[0].start == date(2024, 1, 10)
        assert months[0].end == date(2024, 1, 31)

        assert months[1].start == date(2024, 2, 1)
        assert months[1].end == date(2024, 2, 29)  # 2024是闰年

        assert months[2].start == date(2024, 3, 1)
        assert months[2].end == date(2024, 3, 20)
