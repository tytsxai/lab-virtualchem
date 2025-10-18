.PHONY: help install dev-install test lint format type-check clean run build

help:  ## 显示帮助信息
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## 安装项目依赖
	pip install -e .

dev-install:  ## 安装开发依赖
	pip install -e ".[dev]"

test:  ## 运行测试
	pytest --cov=src --cov-report=html --cov-report=term-missing -v

test-fast:  ## 快速运行测试（不生成覆盖率）
	pytest -v

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
