"""
主窗口游戏化功能扩展
将游戏化相关方法分离到单独文件，保持代码整洁
"""

from PySide6.QtWidgets import QMessageBox

from ..gamification.achievement_system import Achievement
from ..utils.logger import get_logger
from .gamification_dialogs import AchievementUnlockedDialog, LevelUpDialog

logger = get_logger(__name__)


class MainWindowGamificationMixin:
    """主窗口游戏化功能混合类"""

    def _update_gamification_panel(self):
        """更新游戏化面板显示"""
        try:
            if not self.gamification_panel:
                return

            # 获取用户进度
            progress = self.gamification_manager.get_user_progress(self.user_id)

            # 更新等级卡片
            user_data = self.gamification_manager.get_or_create_user_data(self.user_id)
            self.gamification_panel.update_level_card(user_data.level, progress["exp"], progress["next_level_exp"])

            # 更新任务列表
            self.gamification_panel.clear_quests()
            active_quests = [q for q in user_data.quests if q.status.value == "active" or q.status.value == "completed"]
            for user_quest in active_quests[:5]:  # 只显示前5个
                quest = self.gamification_manager.quest_manager.get_quest(user_quest.quest_id)
                if quest:
                    card = self.gamification_panel.add_quest_card(quest, user_quest)
                    card.claim_clicked.connect(self._on_claim_quest_reward)

            # 更新成就显示（显示最近解锁的）
            self.gamification_panel.clear_achievements()
            completed_achievements = [a for a in user_data.achievements if a.completed]
            recent_achievements = sorted(completed_achievements, key=lambda x: x.unlocked_at, reverse=True)[:6]

            for user_achievement in recent_achievements:
                achievement = self.gamification_manager.achievement_manager.get_achievement(
                    user_achievement.achievement_id
                )
                if achievement:
                    self.gamification_panel.add_achievement_card(achievement, unlocked=True)

        except Exception as e:
            logger.error(f"更新游戏化面板失败: {e}", exc_info=True)

    def _show_gamification_rewards(self, result: dict):
        """显示游戏化奖励（升级、成就等）

        Args:
            result: 完成实验后的游戏化结果
        """
        try:
            # 显示升级对话框
            if result.get("level_up", False):
                level_info = result.get("level_info", {})
                old_level = level_info.get("old_level", 1)
                new_level = level_info.get("new_level", 1)
                new_title = level_info.get("new_title", "")

                dialog = LevelUpDialog(old_level, new_level, new_title, self)
                dialog.exec()

            # 显示新成就对话框
            new_achievements: list[Achievement] = result.get("new_achievements", [])
            if new_achievements:
                dialog = AchievementUnlockedDialog(new_achievements, self)
                dialog.exec()

            # 显示完成任务提示
            completed_quests = result.get("completed_quests", [])
            if completed_quests:
                quest_names = [q.name for q in completed_quests]
                QMessageBox.information(
                    self,
                    "任务完成",
                    "恭喜完成任务：\n" + "\n".join(f"✓ {name}" for name in quest_names),
                )

        except Exception as e:
            logger.error(f"显示游戏化奖励失败: {e}", exc_info=True)

    def _on_claim_quest_reward(self, quest_id: str):
        """领取任务奖励"""
        try:
            result = self.gamification_manager.claim_quest_reward(self.user_id, quest_id)

            if result["success"]:
                exp_gained = result["exp_gained"]
                QMessageBox.information(self, "奖励领取", f"成功领取任务奖励！\n获得 {exp_gained} 经验值")

                # 刷新面板
                self._update_gamification_panel()
            else:
                QMessageBox.warning(self, "领取失败", "无法领取该任务奖励，请稍后再试。")

        except Exception as e:
            logger.error(f"领取任务奖励失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"领取奖励时发生错误: {e}")

    def _on_view_all_achievements(self):
        """查看所有成就"""
        try:
            from PySide6.QtWidgets import QDialog, QGridLayout, QLabel, QVBoxLayout

            dialog = QDialog(self)
            dialog.setWindowTitle("全部成就")
            dialog.resize(800, 600)

            layout = QVBoxLayout(dialog)

            # 标题
            title = QLabel("🏆 成就墙")
            title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
            layout.addWidget(title)

            # 获取用户数据
            user_data = self.gamification_manager.get_or_create_user_data(self.user_id)
            unlocked_ids = {a.achievement_id for a in user_data.achievements if a.completed}

            # 成就网格
            from PySide6.QtWidgets import QScrollArea, QWidget

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)

            content = QWidget()
            grid = QGridLayout(content)

            all_achievements = self.gamification_manager.achievement_manager.get_all_achievements(include_hidden=False)

            for i, achievement in enumerate(all_achievements):
                from .gamification_widgets import AchievementCard

                card = AchievementCard(achievement, achievement.id in unlocked_ids)
                row = i // 4
                col = i % 4
                grid.addWidget(card, row, col)

            scroll.setWidget(content)
            layout.addWidget(scroll)

            dialog.exec()

        except Exception as e:
            logger.error(f"查看成就失败: {e}", exc_info=True)
