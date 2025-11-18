import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import __version__ as APP_VERSION

try:
    from fastapi import FastAPI
    from fastapi.openapi.utils import get_openapi

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None  # type: ignore
    get_openapi = None  # type: ignore

"""API文档生成器"""

logger = logging.getLogger(__name__)


@dataclass
class APIEndpoint:
    """API端点信息"""

    path: str
    method: str
    summary: str
    description: str = ""
    parameters: list[dict[str, Any]] = field(default_factory=list)
    request_body: dict[str, Any] | None = None
    responses: dict[str, dict[str, Any]] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class APISchema:
    """API模式信息"""

    name: str
    type: str
    description: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)
    example: Any = None


class APIDocumentationGenerator:
    """API文档生成器"""

    def __init__(self, title: str = "VirtualChemLab API", version: str = APP_VERSION):
        """初始化API文档生成器

        Args:
            title: API标题
            version: API版本
        """
        self.title = title
        self.version = version
        self.endpoints: list[APIEndpoint] = []
        self.schemas: dict[str, APISchema] = {}
        self.base_url = "http://localhost:8000"

        logger.info(f"API文档生成器已初始化: {title} v{version}")

    def add_endpoint(self, endpoint: APIEndpoint) -> None:
        """添加API端点

        Args:
            endpoint: API端点信息
        """
        self.endpoints.append(endpoint)
        logger.debug(f"添加API端点: {endpoint.method} {endpoint.path}")

    def add_schema(self, name: str, schema: APISchema) -> None:
        """添加API模式

        Args:
            name: 模式名称
            schema: API模式信息
        """
        self.schemas[name] = schema
        logger.debug(f"添加API模式: {name}")

    def generate_openapi_spec(self) -> dict[str, Any]:
        """生成OpenAPI规范

        Returns:
            OpenAPI规范字典
        """
        openapi_spec: dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "VirtualChemLab 虚拟化学实验室API文档",
                "contact": {"name": "VirtualChemLab Team", "email": "support@virtualchemlab.com"},
                "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
            },
            "servers": [{"url": self.base_url, "description": "开发服务器"}],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}},
            },
            "security": [{"BearerAuth": []}],
            "tags": [
                {"name": "experiments", "description": "实验管理"},
                {"name": "templates", "description": "实验模板"},
                {"name": "users", "description": "用户管理"},
                {"name": "records", "description": "实验记录"},
                {"name": "system", "description": "系统管理"},
            ],
        }

        # 添加端点
        for endpoint in self.endpoints:
            if endpoint.path not in openapi_spec["paths"]:
                openapi_spec["paths"][endpoint.path] = {}

            openapi_spec["paths"][endpoint.path][endpoint.method.lower()] = {
                "summary": endpoint.summary,
                "description": endpoint.description,
                "tags": endpoint.tags,
                "deprecated": endpoint.deprecated,
                "parameters": endpoint.parameters,
                "responses": endpoint.responses,
            }

            if endpoint.request_body:
                openapi_spec["paths"][endpoint.path][endpoint.method.lower()]["requestBody"] = endpoint.request_body

        # 添加模式
        for name, schema in self.schemas.items():
            openapi_spec["components"]["schemas"][name] = {
                "type": schema.type,
                "description": schema.description,
                "properties": schema.properties,
                "required": schema.required,
                "example": schema.example,
            }

        return openapi_spec

    def generate_markdown_docs(self) -> str:
        """生成Markdown文档

        Returns:
            Markdown文档字符串
        """
        md_content = f"""# {self.title} v{self.version}

## 概述

VirtualChemLab 虚拟化学实验室API提供了完整的实验管理、用户管理、数据记录等功能。

## 基础信息

- **基础URL**: {self.base_url}
- **API版本**: {self.version}
- **认证方式**: Bearer Token (JWT)

## 认证

所有API请求都需要在请求头中包含有效的JWT令牌：

```
Authorization: Bearer <your-jwt-token>
```

## 端点列表

"""

        # 按标签分组端点
        endpoints_by_tag: dict[str, list[APIEndpoint]] = {}
        for endpoint in self.endpoints:
            for tag in endpoint.tags:
                if tag not in endpoints_by_tag:
                    endpoints_by_tag[tag] = []
                endpoints_by_tag[tag].append(endpoint)

        # 生成端点文档
        for tag, endpoints in endpoints_by_tag.items():
            md_content += f"### {tag.title()}\n\n"

            for endpoint in endpoints:
                md_content += f"#### {endpoint.method.upper()} {endpoint.path}\n\n"
                md_content += f"**摘要**: {endpoint.summary}\n\n"

                if endpoint.description:
                    md_content += f"**描述**: {endpoint.description}\n\n"

                if endpoint.parameters:
                    md_content += "**参数**:\n\n"
                    md_content += "| 名称 | 类型 | 位置 | 必需 | 描述 |\n"
                    md_content += "|------|------|------|------|------|\n"

                    for param in endpoint.parameters:
                        name = param.get("name", "")
                        param_type = param.get("schema", {}).get("type", "string")
                        location = param.get("in", "query")
                        required = "是" if param.get("required", False) else "否"
                        description = param.get("description", "")

                        md_content += f"| {name} | {param_type} | {location} | {required} | {description} |\n"

                    md_content += "\n"

                if endpoint.request_body:
                    md_content += "**请求体**:\n\n"
                    md_content += "```json\n"
                    md_content += json.dumps(
                        endpoint.request_body.get("content", {}).get("application/json", {}).get("schema", {}), indent=2
                    )
                    md_content += "\n```\n\n"

                if endpoint.responses:
                    md_content += "**响应**:\n\n"
                    for status_code, response in endpoint.responses.items():
                        md_content += f"- **{status_code}**: {response.get('description', '')}\n"

                    md_content += "\n"

                md_content += "---\n\n"

        # 添加数据模式
        if self.schemas:
            md_content += "## 数据模式\n\n"

            for name, schema in self.schemas.items():
                md_content += f"### {name}\n\n"
                md_content += f"**类型**: {schema.type}\n\n"

                if schema.description:
                    md_content += f"**描述**: {schema.description}\n\n"

                if schema.properties:
                    md_content += "**属性**:\n\n"
                    md_content += "| 属性名 | 类型 | 必需 | 描述 |\n"
                    md_content += "|--------|------|------|------|\n"

                    for prop_name, prop_info in schema.properties.items():
                        prop_type = prop_info.get("type", "string")
                        required = "是" if prop_name in schema.required else "否"
                        description = prop_info.get("description", "")

                        md_content += f"| {prop_name} | {prop_type} | {required} | {description} |\n"

                    md_content += "\n"

                if schema.example:
                    md_content += "**示例**:\n\n"
                    md_content += "```json\n"
                    md_content += json.dumps(schema.example, indent=2)
                    md_content += "\n```\n\n"

                md_content += "---\n\n"

        # 添加错误代码
        md_content += """## 错误代码

| 代码 | 描述 |
|------|------|
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

## 示例

### 创建实验

```bash
curl -X POST "http://localhost:8000/api/experiments" \\
  -H "Authorization: Bearer <your-token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "pH滴定实验",
    "description": "测试pH值",
    "level": "basic"
  }'
```

### 获取实验列表

```bash
curl -X GET "http://localhost:8000/api/experiments" \\
  -H "Authorization: Bearer <your-token>"
```

## 更新日志

### v2.0.0 (2024-01-01)
- 初始版本发布
- 支持实验管理
- 支持用户管理
- 支持数据记录

"""

        return md_content

    def save_openapi_spec(self, file_path: str) -> None:
        """保存OpenAPI规范到文件

        Args:
            file_path: 文件路径
        """
        spec = self.generate_openapi_spec()

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)

        logger.info(f"OpenAPI规范已保存到: {file_path}")

    def save_markdown_docs(self, file_path: str) -> None:
        """保存Markdown文档到文件

        Args:
            file_path: 文件路径
        """
        docs = self.generate_markdown_docs()

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(docs)

        logger.info(f"Markdown文档已保存到: {file_path}")

    def generate_html_docs(self) -> str:
        """生成HTML文档

        Returns:
            HTML文档字符串
        """
        # 简单的HTML模板
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} v{version}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        h3 {{
            color: #666;
            margin-top: 25px;
        }}
        code {{
            background-color: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border-left: 4px solid #007bff;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .endpoint {{
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
        }}
        .method {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-weight: bold;
            color: white;
            margin-right: 10px;
        }}
        .get {{ background-color: #28a745; }}
        .post {{ background-color: #007bff; }}
        .put {{ background-color: #ffc107; color: #000; }}
        .delete {{ background-color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        {content}
    </div>
</body>
</html>
"""

        # 生成内容
        content = f"""
        <h1>{self.title} v{self.version}</h1>

        <h2>概述</h2>
        <p>VirtualChemLab 虚拟化学实验室API提供了完整的实验管理、用户管理、数据记录等功能。</p>

        <h2>基础信息</h2>
        <ul>
            <li><strong>基础URL</strong>: {self.base_url}</li>
            <li><strong>API版本</strong>: {self.version}</li>
            <li><strong>认证方式</strong>: Bearer Token (JWT)</li>
        </ul>

        <h2>端点列表</h2>
        """

        # 按标签分组端点
        endpoints_by_tag: dict[str, list[APIEndpoint]] = {}
        for endpoint in self.endpoints:
            for tag in endpoint.tags:
                if tag not in endpoints_by_tag:
                    endpoints_by_tag[tag] = []
                endpoints_by_tag[tag].append(endpoint)

        # 生成端点HTML
        for tag, endpoints in endpoints_by_tag.items():
            content += f"<h3>{tag.title()}</h3>"

            for endpoint in endpoints:
                method_class = endpoint.method.lower()
                content += f"""
                <div class="endpoint">
                    <h4>
                        <span class="method {method_class}">{endpoint.method.upper()}</span>
                        {endpoint.path}
                    </h4>
                    <p><strong>摘要</strong>: {endpoint.summary}</p>
                    {f"<p><strong>描述</strong>: {endpoint.description}</p>" if endpoint.description else ""}
                </div>
                """

        return html_template.format(title=self.title, version=self.version, content=content)

    def save_html_docs(self, file_path: str) -> None:
        """保存HTML文档到文件

        Args:
            file_path: 文件路径
        """
        html = self.generate_html_docs()

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"HTML文档已保存到: {file_path}")


class APIDocBuilder:
    """API文档构建器"""

    def __init__(self) -> None:
        """初始化API文档构建器"""
        self.generator = APIDocumentationGenerator()

        # 注册默认端点
        self._register_default_endpoints()

        # 注册默认模式
        self._register_default_schemas()

        logger.info("API文档构建器已初始化")

    def _register_default_endpoints(self) -> None:
        """注册默认端点"""
        # 实验管理端点
        self.generator.add_endpoint(
            APIEndpoint(
                path="/api/experiments",
                method="GET",
                summary="获取实验列表",
                description="获取所有实验的列表，支持分页和过滤",
                parameters=[
                    {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}, "description": "页码"},
                    {
                        "name": "size",
                        "in": "query",
                        "schema": {"type": "integer", "default": 10},
                        "description": "每页大小",
                    },
                    {"name": "level", "in": "query", "schema": {"type": "string"}, "description": "难度等级过滤"},
                ],
                responses={
                    "200": {
                        "description": "成功获取实验列表",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/ExperimentListResponse"}}
                        },
                    }
                },
                tags=["experiments"],
            )
        )

        self.generator.add_endpoint(
            APIEndpoint(
                path="/api/experiments",
                method="POST",
                summary="创建新实验",
                description="创建一个新的实验",
                request_body={
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/CreateExperimentRequest"}}
                    }
                },
                responses={
                    "201": {
                        "description": "实验创建成功",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/ExperimentResponse"}}
                        },
                    },
                    "400": {"description": "请求参数错误"},
                    "401": {"description": "未授权"},
                },
                tags=["experiments"],
            )
        )

        self.generator.add_endpoint(
            APIEndpoint(
                path="/api/experiments/{experiment_id}",
                method="GET",
                summary="获取实验详情",
                description="根据ID获取实验的详细信息",
                parameters=[
                    {
                        "name": "experiment_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "实验ID",
                    }
                ],
                responses={
                    "200": {
                        "description": "成功获取实验详情",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/ExperimentResponse"}}
                        },
                    },
                    "404": {"description": "实验未找到"},
                },
                tags=["experiments"],
            )
        )

        # 用户管理端点
        self.generator.add_endpoint(
            APIEndpoint(
                path="/api/users",
                method="GET",
                summary="获取用户列表",
                description="获取所有用户的列表",
                responses={
                    "200": {
                        "description": "成功获取用户列表",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UserListResponse"}}},
                    }
                },
                tags=["users"],
            )
        )

        # 系统管理端点
        self.generator.add_endpoint(
            APIEndpoint(
                path="/api/health",
                method="GET",
                summary="健康检查",
                description="检查系统健康状态",
                responses={
                    "200": {
                        "description": "系统健康",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/HealthResponse"}}},
                    }
                },
                tags=["system"],
            )
        )

    def _register_default_schemas(self) -> None:
        """注册默认模式"""
        # 实验相关模式
        self.generator.add_schema(
            "Experiment",
            APISchema(
                name="Experiment",
                type="object",
                description="实验信息",
                properties={
                    "id": {"type": "string", "description": "实验ID"},
                    "name": {"type": "string", "description": "实验名称"},
                    "description": {"type": "string", "description": "实验描述"},
                    "level": {"type": "string", "description": "难度等级"},
                    "status": {"type": "string", "description": "实验状态"},
                    "created_at": {"type": "string", "format": "date-time", "description": "创建时间"},
                    "updated_at": {"type": "string", "format": "date-time", "description": "更新时间"},
                },
                required=["id", "name", "level"],
                example={
                    "id": "exp_001",
                    "name": "pH滴定实验",
                    "description": "测试pH值",
                    "level": "basic",
                    "status": "active",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
            ),
        )

        self.generator.add_schema(
            "CreateExperimentRequest",
            APISchema(
                name="CreateExperimentRequest",
                type="object",
                description="创建实验请求",
                properties={
                    "name": {"type": "string", "description": "实验名称"},
                    "description": {"type": "string", "description": "实验描述"},
                    "level": {"type": "string", "description": "难度等级"},
                    "template_id": {"type": "string", "description": "模板ID"},
                },
                required=["name", "level"],
                example={
                    "name": "pH滴定实验",
                    "description": "测试pH值",
                    "level": "basic",
                    "template_id": "template_001",
                },
            ),
        )

        self.generator.add_schema(
            "ExperimentResponse",
            APISchema(
                name="ExperimentResponse",
                type="object",
                description="实验响应",
                properties={
                    "success": {"type": "boolean", "description": "是否成功"},
                    "data": {"$ref": "#/components/schemas/Experiment"},
                    "message": {"type": "string", "description": "响应消息"},
                },
                example={
                    "success": True,
                    "data": {
                        "id": "exp_001",
                        "name": "pH滴定实验",
                        "description": "测试pH值",
                        "level": "basic",
                        "status": "active",
                    },
                    "message": "操作成功",
                },
            ),
        )

        # 用户相关模式
        self.generator.add_schema(
            "User",
            APISchema(
                name="User",
                type="object",
                description="用户信息",
                properties={
                    "id": {"type": "string", "description": "用户ID"},
                    "username": {"type": "string", "description": "用户名"},
                    "email": {"type": "string", "format": "email", "description": "邮箱"},
                    "role": {"type": "string", "description": "用户角色"},
                    "created_at": {"type": "string", "format": "date-time", "description": "创建时间"},
                },
                required=["id", "username", "email"],
                example={
                    "id": "user_001",
                    "username": "testuser",
                    "email": "test@example.com",
                    "role": "student",
                    "created_at": "2024-01-01T00:00:00Z",
                },
            ),
        )

        # 系统相关模式
        self.generator.add_schema(
            "HealthResponse",
            APISchema(
                name="HealthResponse",
                type="object",
                description="健康检查响应",
                properties={
                    "status": {"type": "string", "description": "系统状态"},
                    "timestamp": {"type": "string", "format": "date-time", "description": "检查时间"},
                    "version": {"type": "string", "description": "系统版本"},
                    "services": {"type": "object", "description": "服务状态"},
                },
                example={
                    "status": "healthy",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "version": "2.0.0",
                    "services": {"database": "healthy", "cache": "healthy", "queue": "healthy"},
                },
            ),
        )

    def build_docs(self, output_dir: str = "docs") -> None:
        """构建文档

        Args:
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # 生成OpenAPI规范
        self.generator.save_openapi_spec(str(output_path / "openapi.json"))

        # 生成Markdown文档
        self.generator.save_markdown_docs(str(output_path / "api.md"))

        # 生成HTML文档
        self.generator.save_html_docs(str(output_path / "api.html"))

        logger.info(f"API文档已生成到: {output_dir}")


# 全局API文档构建器
api_doc_builder = APIDocBuilder()
