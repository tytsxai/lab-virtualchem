"""VirtualChemLab API客户端

用于连接和调用VirtualChemLab API
"""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class VirtualChemLabClient:
    """VirtualChemLab API客户端"""

    def __init__(self, base_url: str = "http://localhost:8080"):
        """初始化客户端

        Args:
            base_url: API服务器基础URL
        """
        self.base_url = base_url.rstrip("/")
        self.session_id: str | None = None

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """发送HTTP请求

        Args:
            method: HTTP方法
            endpoint: API端点
            data: 请求数据
            params: URL参数

        Returns:
            响应数据

        Raises:
            requests.HTTPError: HTTP错误
        """
        url = f"{self.base_url}{endpoint}"

        response = requests.request(
            method=method,
            url=url,
            json=data,
            params=params,
            headers={"Content-Type": "application/json"},
            timeout=30,  # 30秒超时
        )

        response.raise_for_status()
        return response.json()

    # ============ 健康检查 ============

    def health_check(self) -> dict[str, Any]:
        """健康检查

        Returns:
            服务器状态信息
        """
        return self._request("GET", "/api/health")

    # ============ 实验管理 ============

    def list_experiments(self) -> list[dict[str, Any]]:
        """列出所有实验

        Returns:
            实验列表
        """
        response = self._request("GET", "/api/experiments")
        return response["experiments"]

    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        """获取实验详情

        Args:
            experiment_id: 实验ID

        Returns:
            实验详情
        """
        response = self._request("GET", f"/api/experiments/{experiment_id}")
        return response["experiment"]

    def start_experiment(
        self, experiment_id: str, user_id: str = "anonymous"
    ) -> dict[str, Any]:
        """开始实验

        Args:
            experiment_id: 实验ID
            user_id: 用户ID

        Returns:
            会话信息
        """
        response = self._request(
            "POST",
            "/api/experiments/start",
            {"experiment_id": experiment_id, "user_id": user_id},
        )

        self.session_id = response["session_id"]
        return response

    def submit_step(self, data: dict[str, Any]) -> dict[str, Any]:
        """提交步骤

        Args:
            data: 步骤数据

        Returns:
            提交结果

        Raises:
            ValueError: 没有活动会话
        """
        if not self.session_id:
            raise ValueError("No active session. Call start_experiment first.")

        return self._request(
            "POST",
            "/api/experiments/submit",
            {"session_id": self.session_id, "data": data},
        )

    def finish_experiment(self) -> dict[str, Any]:
        """完成实验

        Returns:
            实验结果

        Raises:
            ValueError: 没有活动会话
        """
        if not self.session_id:
            raise ValueError("No active session. Call start_experiment first.")

        response = self._request(
            "POST", "/api/experiments/finish", {"session_id": self.session_id}
        )

        self.session_id = None
        return response

    # ============ 记录管理 ============

    def list_records(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """列出实验记录

        Args:
            user_id: 用户ID(可选)

        Returns:
            记录列表
        """
        params = {"user_id": user_id} if user_id else None
        response = self._request("GET", "/api/records", params=params)
        return response["records"]

    def get_record(self, record_id: str) -> dict[str, Any]:
        """获取记录详情

        Args:
            record_id: 记录ID

        Returns:
            记录详情
        """
        response = self._request("GET", f"/api/records/{record_id}")
        return response["record"]

    # ============ 报告生成 ============

    def generate_report(
        self, record_id: str, format_type: str = "html"
    ) -> dict[str, Any]:
        """生成报告

        Args:
            record_id: 记录ID
            format_type: 报告格式(html/pdf)

        Returns:
            报告信息
        """
        return self._request(
            "POST",
            "/api/reports/generate",
            {"record_id": record_id, "format": format_type},
        )

    # ============ 便捷方法 ============

    def run_experiment(
        self,
        experiment_id: str,
        steps_data: list[dict[str, Any]],
        user_id: str = "anonymous",
    ) -> dict[str, Any]:
        """运行完整实验

        Args:
            experiment_id: 实验ID
            steps_data: 步骤数据列表
            user_id: 用户ID

        Returns:
            实验结果
        """
        # 开始实验
        start_result = self.start_experiment(experiment_id, user_id)
        logger.info(f"✅ 开始实验: {start_result['experiment_id']}")

        # 提交所有步骤
        for i, data in enumerate(steps_data, 1):
            result = self.submit_step(data)
            logger.info(
                f"📝 步骤 {i}: {'通过' if result['passed'] else '失败'} - {result['message']}"
            )

            if not result["has_next_step"]:
                break

        # 完成实验
        final_result = self.finish_experiment()
        logger.info(f"🎉 实验完成! 得分: {final_result['final_score']}")

        return final_result


# ============ 示例使用 ============


def example_usage():
    """示例使用"""

    # 创建客户端
    client = VirtualChemLabClient("http://localhost:8080")

    # 健康检查
    health = client.health_check()
    logger.info(f"服务器状态: {health['status']}")

    # 列出实验
    experiments = client.list_experiments()
    logger.info(f"\n可用实验 ({len(experiments)}个):")
    for exp in experiments:
        logger.info(f"  - {exp['id']}: {exp['title']}")

    # 运行实验
    if experiments:
        exp_id = experiments[0]["id"]

        # 准备步骤数据(示例)
        steps_data = [
            {"confirmed": True},  # 步骤1: 确认
            {"value": "25.0"},  # 步骤2: 输入
            {"selected": "option1"},  # 步骤3: 选择
        ]

        # 运行实验
        result = client.run_experiment(exp_id, steps_data, user_id="test_user")

        # 生成报告
        report = client.generate_report(result["record_id"])
        logger.info(f"\n📄 报告已生成: {report['url']}")


if __name__ == "__main__":
    example_usage()
