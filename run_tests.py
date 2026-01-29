#!/usr/bin/env python3
"""
运行测试套件的主脚本
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type=None, coverage=False, parallel=False, html_report=False):
    """运行测试"""
    cmd = [sys.executable, "-m", "pytest"]

    # 添加测试类型筛选
    if test_type:
        if test_type == "unit":
            cmd.extend(["tests/unit", "-m", "unit"])
        elif test_type == "integration":
            cmd.extend(["tests/integration", "-m", "integration"])
        elif test_type == "functional":
            cmd.extend(["tests/functional", "-m", "functional"])
        elif test_type == "performance":
            cmd.extend(["tests/performance", "-m", "performance"])
        elif test_type == "all":
            cmd.append("tests")
        else:
            # 运行特定测试文件
            test_file = Path(f"tests/{test_type}")
            if test_file.exists():
                cmd.append(str(test_file))
            else:
                print(f"错误: 未找到测试文件 {test_file}")
                return False
    else:
        cmd.append("tests")

    # 添加覆盖率
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term", "--cov-report=html"])

    # 并行运行
    if parallel:
        cmd.extend(["-n", "auto"])

    # HTML报告
    if html_report:
        cmd.extend(["--html=test_reports/html/report.html", "--self-contained-html"])

    # 添加详细输出
    cmd.append("-v")

    print(f"运行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return False
    except Exception as e:
        print(f"运行测试时出错: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行网络监控系统测试套件")
    parser.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=["all", "unit", "integration", "functional", "performance"],
        help="测试类型 (默认: all)",
    )
    parser.add_argument(
        "--coverage", "-c", action="store_true", help="生成测试覆盖率报告"
    )
    parser.add_argument("--parallel", "-p", action="store_true", help="并行运行测试")
    parser.add_argument("--html", action="store_true", help="生成HTML测试报告")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有测试")
    parser.add_argument("--slow", action="store_true", help="包含慢速测试")

    args = parser.parse_args()

    # 创建测试报告目录
    report_dir = Path("test_reports")
    report_dir.mkdir(exist_ok=True)
    (report_dir / "html").mkdir(exist_ok=True)
    (report_dir / "xml").mkdir(exist_ok=True)

    if args.list:
        # 列出所有测试
        cmd = [sys.executable, "-m", "pytest", "--collect-only", "tests"]
        subprocess.run(cmd)
        return

    # 运行测试
    success = run_tests(
        test_type=args.type,
        coverage=args.coverage,
        parallel=args.parallel,
        html_report=args.html,
    )

    if success:
        print("\n✅ 所有测试通过!")
        sys.exit(0)
    else:
        print("\n❌ 测试失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()
