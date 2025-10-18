#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSON到SQLite数据迁移工具
将现有的JSON文件数据迁移到SQLite数据库
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.database_manager import DatabaseManager
from src.models.user_record import UserRecord, ExperimentScore, StepRecord, Mistake

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class DataMigration:
    """数据迁移器"""
    
    def __init__(self, source_dir: str = 'data', db_path: str = 'data/virtualchemlab.db'):
        """初始化迁移器
        
        Args:
            source_dir: JSON数据源目录
            db_path: 目标数据库路径
        """
        self.source_dir = Path(source_dir)
        self.db = DatabaseManager(db_path)
        
        # 统计信息
        self.stats = {
            'users_created': 0,
            'experiments_migrated': 0,
            'templates_migrated': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def migrate_all(self) -> Dict[str, Any]:
        """迁移所有数据
        
        Returns:
            迁移统计信息
        """
        logger.info("=" * 70)
        logger.info("开始数据迁移：JSON -> SQLite")
        logger.info("=" * 70)
        
        # 1. 迁移用户数据
        logger.info("\n[1/3] 迁移用户数据...")
        self._migrate_users()
        
        # 2. 迁移实验记录
        logger.info("\n[2/3] 迁移实验记录...")
        self._migrate_experiment_records()
        
        # 3. 迁移模板
        logger.info("\n[3/3] 迁移模板...")
        self._migrate_templates()
        
        # 输出统计
        logger.info("\n" + "=" * 70)
        logger.info("迁移完成！")
        logger.info("=" * 70)
        logger.info(f"\n统计信息:")
        logger.info(f"  用户: {self.stats['users_created']}")
        logger.info(f"  实验记录: {self.stats['experiments_migrated']}")
        logger.info(f"  模板: {self.stats['templates_migrated']}")
        logger.info(f"  错误: {self.stats['errors']}")
        logger.info(f"  跳过: {self.stats['skipped']}")
        
        return self.stats
    
    def _migrate_users(self):
        """迁移用户数据"""
        users_dir = self.source_dir / 'users'
        
        if not users_dir.exists():
            logger.warning(f"用户目录不存在: {users_dir}")
            return
        
        # 从records目录获取用户列表
        records_dir = self.source_dir / 'records'
        if records_dir.exists():
            for user_dir in records_dir.iterdir():
                if user_dir.is_dir():
                    user_id = user_dir.name
                    try:
                        # 检查用户是否已存在
                        existing_user = self.db.get_user(user_id)
                        if existing_user:
                            logger.debug(f"  用户已存在，跳过: {user_id}")
                            self.stats['skipped'] += 1
                            continue
                        
                        # 创建用户
                        self.db.create_user(
                            user_id=user_id,
                            username=user_id,  # 默认使用user_id作为用户名
                            email=f"{user_id}@virtualchemlab.local"
                        )
                        self.stats['users_created'] += 1
                        logger.info(f"  创建用户: {user_id}")
                    
                    except Exception as e:
                        logger.error(f"  创建用户失败 {user_id}: {e}")
                        self.stats['errors'] += 1
    
    def _migrate_experiment_records(self):
        """迁移实验记录"""
        records_dir = self.source_dir / 'records'
        
        if not records_dir.exists():
            logger.warning(f"记录目录不存在: {records_dir}")
            return
        
        total_files = 0
        migrated = 0
        
        # 遍历所有用户目录
        for user_dir in records_dir.iterdir():
            if not user_dir.is_dir():
                continue
            
            user_id = user_dir.name
            logger.info(f"\n  处理用户: {user_id}")
            
            # 查找所有JSON文件
            json_files = list(user_dir.glob('*.json'))
            
            for json_file in json_files:
                # 跳过索引文件
                if json_file.name == 'index.json':
                    continue
                
                total_files += 1
                
                try:
                    # 读取JSON数据
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 转换为UserRecord对象
                    record = self._convert_to_user_record(data)
                    
                    # 保存到数据库
                    self.db.save_experiment_record(record)
                    migrated += 1
                    
                    if migrated % 100 == 0:
                        logger.info(f"    已迁移: {migrated} 条记录")
                
                except Exception as e:
                    logger.error(f"    迁移失败 {json_file.name}: {e}")
                    self.stats['errors'] += 1
        
        self.stats['experiments_migrated'] = migrated
        logger.info(f"\n  共处理 {total_files} 个文件，成功迁移 {migrated} 条记录")
    
    def _convert_to_user_record(self, data: Dict[str, Any]) -> UserRecord:
        """将JSON数据转换为UserRecord对象"""
        # 处理score字段
        score_data = data.get('score', {})
        score = ExperimentScore(
            total=score_data.get('total', 0),
            scientific=score_data.get('scientific', 0),
            procedural=score_data.get('procedural', 0),
            safety=score_data.get('safety', 0),
            details=score_data.get('details', {})
        )
        
        # 处理step_records
        step_records = []
        for step_data in data.get('step_records', []):
            mistakes = [
                Mistake(**m) if isinstance(m, dict) else m
                for m in step_data.get('mistakes', [])
            ]
            step = StepRecord(
                step_id=step_data.get('step_id', ''),
                started_at=self._parse_datetime(step_data.get('started_at')),
                completed_at=self._parse_datetime(step_data.get('completed_at')),
                passed=step_data.get('passed', False),
                user_input=step_data.get('user_input', {}),
                mistakes=mistakes,
                attempts=step_data.get('attempts', 1)
            )
            step_records.append(step)
        
        # 处理mistakes_summary
        mistakes_summary = []
        for m_data in data.get('mistakes_summary', []):
            mistake = Mistake(
                step_id=m_data.get('step_id', ''),
                timestamp=self._parse_datetime(m_data.get('timestamp')),
                error_type=m_data.get('error_type', ''),
                description=m_data.get('description', ''),
                hint=m_data.get('hint', ''),
                severity=m_data.get('severity', 'warning')
            )
            mistakes_summary.append(mistake)
        
        # 创建UserRecord
        record = UserRecord(
            record_id=data.get('record_id', ''),
            user_id=data.get('user_id', ''),
            experiment_id=data.get('experiment_id', ''),
            experiment_title=data.get('experiment_title', ''),
            started_at=self._parse_datetime(data.get('started_at')),
            completed_at=self._parse_datetime(data.get('completed_at')),
            status=data.get('status', 'in_progress'),
            current_step_index=data.get('current_step_index', 0),
            step_records=step_records,
            score=score,
            context=data.get('context', {}),
            curve_data=data.get('curve_data', {}),
            mistakes_summary=mistakes_summary,
            version=data.get('version', '1.0.0')
        )
        
        return record
    
    def _parse_datetime(self, dt_str: Any) -> datetime:
        """解析日期时间字符串"""
        if dt_str is None:
            return None
        if isinstance(dt_str, datetime):
            return dt_str
        if isinstance(dt_str, str):
            try:
                return datetime.fromisoformat(dt_str)
            except:
                return datetime.now()
        return datetime.now()
    
    def _migrate_templates(self):
        """迁移模板"""
        templates_dir = self.source_dir / 'templates'
        
        if not templates_dir.exists():
            logger.warning(f"模板目录不存在: {templates_dir}")
            return
        
        # 查找所有YAML模板文件
        yaml_files = list(templates_dir.glob('*.yaml'))
        
        for yaml_file in yaml_files:
            # 跳过disabled文件
            if yaml_file.suffix == '.disabled':
                continue
            
            try:
                # 读取模板内容
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 保存到数据库
                template_id = yaml_file.stem
                self.db.save_template(
                    template_id=template_id,
                    name=template_id.replace('_', ' ').title(),
                    category='general',
                    content=content
                )
                self.stats['templates_migrated'] += 1
                logger.info(f"  迁移模板: {template_id}")
            
            except Exception as e:
                logger.error(f"  迁移模板失败 {yaml_file.name}: {e}")
                self.stats['errors'] += 1
    
    def verify_migration(self) -> bool:
        """验证迁移结果
        
        Returns:
            是否验证通过
        """
        logger.info("\n" + "=" * 70)
        logger.info("验证迁移结果...")
        logger.info("=" * 70)
        
        # 获取数据库统计
        exp_stats = self.db.get_experiment_statistics()
        
        logger.info(f"\n数据库统计:")
        logger.info(f"  实验记录总数: {exp_stats['total_records']}")
        logger.info(f"  完成的记录: {exp_stats['completed_records']}")
        logger.info(f"  完成率: {exp_stats['completion_rate']:.1f}%")
        logger.info(f"  平均分数: {exp_stats['average_score']:.2f}")
        
        # 验证数据完整性
        is_valid = True
        
        if self.stats['experiments_migrated'] != exp_stats['total_records']:
            logger.error(f"记录数量不匹配！迁移: {self.stats['experiments_migrated']}, 数据库: {exp_stats['total_records']}")
            is_valid = False
        
        if self.stats['errors'] > 0:
            logger.warning(f"迁移过程中发生 {self.stats['errors']} 个错误")
        
        if is_valid:
            logger.info("\n[OK] 数据完整性验证通过")
        else:
            logger.error("\n[FAIL] 数据完整性验证失败")
        
        return is_valid
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='迁移JSON数据到SQLite')
    parser.add_argument('--source', default='data', help='源数据目录')
    parser.add_argument('--db', default='data/virtualchemlab.db', help='目标数据库路径')
    parser.add_argument('--verify', action='store_true', help='验证迁移结果')
    
    args = parser.parse_args()
    
    try:
        # 创建迁移器
        migrator = DataMigration(source_dir=args.source, db_path=args.db)
        
        # 执行迁移
        stats = migrator.migrate_all()
        
        # 验证结果
        if args.verify:
            migrator.verify_migration()
        
        # 关闭连接
        migrator.close()
        
        logger.info("\n迁移工具已完成！")
        return 0
    
    except Exception as e:
        logger.error(f"\n[ERROR] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

