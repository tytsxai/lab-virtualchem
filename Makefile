.PHONY: help install dev-install test test-fast lint lint-fix format type-check type-check-strict clean run build all-checks all-checks-strict ci sync-version bump-version
.PHONY: docs-check

PYTHON ?= $(shell \
	if [ -x .venv312/bin/python ]; then echo .venv312/bin/python; \
	elif [ -x .venv311/bin/python ]; then echo .venv311/bin/python; \
	elif [ -x .venv39/bin/python ]; then echo .venv39/bin/python; \
	elif [ -x .venv/bin/python ]; then echo .venv/bin/python; \
	elif command -v python3.12 >/dev/null 2>&1; then echo python3.12; \
	elif command -v python3.11 >/dev/null 2>&1; then echo python3.11; \
	elif command -v python3.10 >/dev/null 2>&1; then echo python3.10; \
	else echo python3; fi)

help:  ## 显示帮助信息
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## 安装项目依赖
	$(PYTHON) -m pip install --require-hashes -r requirements.lock
	$(PYTHON) -m pip install --no-deps -e .

dev-install:  ## 安装开发依赖
	$(PYTHON) -m pip install --require-hashes -r requirements.lock
	$(PYTHON) -m pip install --no-deps -e .

test:  ## 运行测试（包含覆盖率门禁）
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest --ignore=tests/ui

test-fast:  ## 快速运行测试（跳过覆盖率）
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest --no-cov -v --ignore=tests/ui

lint:  ## 运行代码检查
	$(PYTHON) -m ruff check src tests

lint-fix:  ## 自动修复代码问题
	$(PYTHON) -m ruff check --fix src tests

format:  ## 格式化代码
	$(PYTHON) -m ruff format src tests

type-check:  ## 运行类型检查
	$(PYTHON) -m mypy src --no-error-summary || (echo "⚠️ mypy 报告了类型问题（当前为非阻塞检查）" && exit 0)

type-check-strict:  ## 运行类型检查（严格门禁）
	$(PYTHON) -m mypy src

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
	$(PYTHON) main.py

build:  ## 构建可执行文件
	PYTHON_BIN=$(PYTHON) bash build.sh

all-checks: lint type-check test  ## 运行所有检查（mypy为非阻塞）

all-checks-strict: lint type-check-strict test  ## 运行所有检查（含严格类型门禁）

ci: all-checks  ## CI流程
	@echo "✅ 所有检查通过！"

sync-version:  ## 将 src/__init__.py 中的版本同步到配置/构建文件
	$(PYTHON) tools/bump_version.py

bump-version:  ## 设置新的 VERSION=MAJOR.MINOR.PATCH 并同步
	@if [ -z "$(VERSION)" ]; then echo "请提供 VERSION=MAJOR.MINOR.PATCH"; exit 1; fi
	$(PYTHON) tools/bump_version.py --set $(VERSION)

docs-check:  ## 检查入口文档的本地链接是否失效
	$(PYTHON) tools/check_docs_links.py
