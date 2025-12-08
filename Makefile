.PHONY: help install dev-install test lint format type-check clean run build sync-version bump-version

help:  ## 显示帮助信息
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## 安装项目依赖
	pip install -r requirements.lock
	pip install --no-deps -e .

dev-install:  ## 安装开发依赖
	pip install -r requirements.lock
	pip install --no-deps -e .

test:  ## 运行测试（包含覆盖率门禁）
	pytest

test-fast:  ## 快速运行测试（跳过覆盖率）
	pytest --no-cov -v

lint:  ## 运行代码检查
	ruff check src tests

lint-fix:  ## 自动修复代码问题
	ruff check --fix src tests

format:  ## 格式化代码
	ruff format src tests

type-check:  ## 运行类型检查
	mypy src

clean:  ## 清理临时文件
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:  ## 运行应用程序
	python main.py

build:  ## 构建可执行文件
	pyinstaller --name VirtualChemLab --windowed --onefile main.py

all-checks: lint type-check test  ## 运行所有检查

ci: all-checks  ## CI流程
	@echo "✅ 所有检查通过！"

sync-version:  ## 将 src/__init__.py 中的版本同步到配置/构建文件
	python3 tools/bump_version.py

bump-version:  ## 设置新的 VERSION=MAJOR.MINOR.PATCH 并同步
	@if [ -z "$(VERSION)" ]; then echo "请提供 VERSION=MAJOR.MINOR.PATCH"; exit 1; fi
	python3 tools/bump_version.py --set $(VERSION)
