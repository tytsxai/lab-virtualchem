# Event Catalog（事件目录）

本文件提供“事件名称 → 用途 → Payload 概览”的目录式索引，便于快速定位。

> 当前仓库的协议主文档为：`docs/API_EVENT_PROTOCOL.md`。若目录与主文档描述不一致，请以主文档为准，并欢迎提交修正。

## 事件命名约定

- 推荐格式：`domain.action`（例如 `experiment.started`）
- 事件应具备清晰的触发时机与幂等语义（如果需要重放/重试）

## 目录（占位）

目前事件目录仍在逐步补齐中。请先参考：

- `docs/API_EVENT_PROTOCOL.md` 的“事件驱动协议”章节
- `src/core/event_bus.py` / `src/core/event_system.py` 中的实现与事件常量（若存在）

