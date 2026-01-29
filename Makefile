# 网络监控系统测试 Makefile

.PHONY: test test-unit test-integration test-functional test-performance coverage clean install

# 默认目标
all: test

# 安装开发依赖
install:
	pip install -r requirements-dev.txt

# 运行所有测试
test:
	python run_tests.py all

# 运行单元测试
test-unit:
	python run_tests.py unit

# 运行集成测试
test-integration:
	python run_tests.py integration

# 运行功能测试
test-functional:
	python run_tests.py functional

# 运行性能测试
test-performance:
	python run_tests.py performance

# 带覆盖率的测试
coverage:
	python run_tests.py all --coverage

# 并行运行测试
test-parallel:
	python run_tests.py all --parallel

# 生成HTML报告
test-html:
	python run_tests.py all --html

# 清理测试文件
clean:
	rm -rf test_reports/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# 代码质量检查
lint:
	flake8 src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/
	mypy src/

# 格式化代码
format:
	black src/ tests/
	isort src/ tests/

# 安全扫描
security:
	bandit -r src/

# 依赖检查
deps:
	pipdeptree --warn fail

# 运行完整CI流程
ci: lint test coverage security

# 帮助信息
help:
	@echo "可用命令:"
	@echo "  make install     安装开发依赖"
	@echo "  make test        运行所有测试"
	@echo "  make test-unit   运行单元测试"
	@echo "  make test-integration 运行集成测试"
	@echo "  make test-functional 运行功能测试"
	@echo "  make test-performance 运行性能测试"
	@echo "  make coverage    运行测试并生成覆盖率报告"
	@echo "  make test-parallel 并行运行测试"
	@echo "  make test-html   生成HTML测试报告"
	@echo "  make lint        代码质量检查"
	@echo "  make format      格式化代码"
	@echo "  make security    安全扫描"
	@echo "  make deps        依赖检查"
	@echo "  make ci          运行完整CI流程"
	@echo "  make clean       清理测试文件"
	@echo "  make help        显示此帮助信息"
