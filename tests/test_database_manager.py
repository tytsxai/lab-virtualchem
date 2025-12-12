#!/usr/bin/env python
"""
数据库管理器测试
测试SQLAlchemy数据访问层的功能和性能
"""

import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.user_record import ExperimentScore, UserRecord
from src.storage.database_manager import DatabaseManager


def test_database_creation():
    """测试数据库创建"""
    print("\n=== 数据库创建测试 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test.db'
        db = DatabaseManager(str(db_path))

        try:
            assert db_path.exists()
            print(f"[OK] 数据库创建成功: {db_path}")
        finally:
            db.close()


def test_user_operations():
    """测试用户CRUD操作"""
    print("\n=== 用户操作测试 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test.db'
        db = DatabaseManager(str(db_path))

        try:
            # 创建用户
            user = db.create_user(
                user_id='test_user_001',
                username='测试用户',
                email='test@example.com',
                role='student',
                preferences={'theme': 'dark'}
            )
            assert user['user_id'] == 'test_user_001'
            print("[OK] 创建用户")

            # 获取用户
            loaded_user = db.get_user('test_user_001')
            assert loaded_user is not None
            assert loaded_user['username'] == '测试用户'
            print("[OK] 获取用户")

            # 更新用户
            success = db.update_user('test_user_001', username='修改后的用户名')
            assert success
            loaded_user = db.get_user('test_user_001')
            assert loaded_user['username'] == '修改后的用户名'
            print("[OK] 更新用户")

            # 列出用户
            users = db.list_users()
            assert len(users) >= 1
            print("[OK] 列出用户")

            # 删除用户
            success = db.delete_user('test_user_001')
            assert success
            loaded_user = db.get_user('test_user_001')
            assert loaded_user is None
            print("[OK] 删除用户")

        finally:
            db.close()


def test_experiment_record_operations():
    """测试实验记录操作"""
    print("\n=== 实验记录操作测试 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test.db'
        db = DatabaseManager(str(db_path))

        # 创建用户
        db.create_user('test_user', '测试用户', 'test@example.com')

        # 创建实验记录
        record = UserRecord(
            record_id='exp_001',
            user_id='test_user',
            experiment_id='titration_test',
            experiment_title='酸碱滴定测试',
            status='in_progress',
            started_at=datetime.now(),
            score=ExperimentScore(total=0, scientific=0, procedural=0, safety=0),
            step_records=[],
            context={},
            curve_data={},
            mistakes_summary=[]
        )

        try:
            db_record = db.save_experiment_record(record)
            assert db_record['record_id'] == 'exp_001'
            print("[OK] 保存实验记录")

            # 获取实验记录
            loaded_record = db.get_experiment_record('exp_001')
            assert loaded_record is not None
            assert loaded_record['experiment_id'] == 'titration_test'
            print("[OK] 获取实验记录")

            # 更新实验记录
            record.status = 'completed'
            record.score.total = 95
            db_record = db.save_experiment_record(record)
            loaded_record = db.get_experiment_record('exp_001')
            assert loaded_record['status'] == 'completed'
            assert loaded_record['score']['total'] == 95
            print("[OK] 更新实验记录")

            # 列出用户实验
            records = db.list_user_experiments('test_user')
            assert len(records) == 1
            print("[OK] 列出用户实验")

            # 删除实验记录
            success = db.delete_experiment_record('exp_001')
            assert success
            print("[OK] 删除实验记录")

        finally:
            db.close()


def test_template_operations():
    """测试模板操作"""
    print("\n=== 模板操作测试 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test.db'
        db = DatabaseManager(str(db_path))

        # 保存模板
        try:
            template = db.save_template(
                template_id='template_001',
                name='测试模板',
                category='titration',
                content='template content here',
                difficulty='easy',
                description='这是一个测试模板'
            )
            # template是Template对象，需要在session内访问
            print("[OK] 保存模板")

            # 获取模板
            loaded_template = db.get_template('template_001')
            assert loaded_template is not None
            assert loaded_template['name'] == '测试模板'
            print("[OK] 获取模板")

            # 列出模板
            templates = db.list_templates(category='titration')
            assert len(templates) == 1
            print("[OK] 列出模板")

        finally:
            db.close()


def test_config_operations():
    """测试配置操作"""
    print("\n=== 配置操作测试 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test.db'
        db = DatabaseManager(str(db_path))

        try:
            # 设置不同类型的配置
            db.set_config('string_key', 'string_value')
            db.set_config('int_key', 42)
            db.set_config('float_key', 3.14)
            db.set_config('bool_key', True)
            db.set_config('json_key', {'nested': 'value'})

            # 获取配置
            assert db.get_config('string_key') == 'string_value'
            assert db.get_config('int_key') == 42
            assert db.get_config('float_key') == 3.14
            assert db.get_config('bool_key') is True
            assert db.get_config('json_key') == {'nested': 'value'}

            print("[OK] 配置类型转换")

            # 默认值
            assert db.get_config('nonexistent', 'default') == 'default'
            print("[OK] 默认值")

        finally:
            db.close()


def test_statistics():
    """测试统计功能"""
    print("\n=== 统计功能测试 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test.db'
        db = DatabaseManager(str(db_path))

        try:
            # 创建测试数据
            db.create_user('user1', '用户1', 'user1@example.com')

            for i in range(5):
                record = UserRecord(
                    record_id=f'exp_{i}',
                    user_id='user1',
                    experiment_id=f'test_exp_{i}',
                    experiment_title=f'测试实验{i}',
                    status='completed',
                    started_at=datetime.now(),
                    completed_at=datetime.now(),
                    score=ExperimentScore(total=80 + i * 2, scientific=0, procedural=0, safety=0),
                    step_records=[],
                    context={},
                    curve_data={},
                    mistakes_summary=[]
                )
                db.save_experiment_record(record)

            # 用户统计
            user_stats = db.get_user_stats('user1')
            assert user_stats['total_experiments'] == 5
            assert user_stats['completed_experiments'] == 5
            assert user_stats['average_score'] > 0
            print(f"[OK] 用户统计: {user_stats}")

            # 实验统计
            exp_stats = db.get_experiment_statistics()
            assert exp_stats['total_records'] == 5
            assert exp_stats['completion_rate'] == 100
            print(f"[OK] 实验统计: {exp_stats}")

        finally:
            db.close()


def benchmark_performance():
    """性能基准测试"""
    print("\n=== 性能基准测试 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test.db'
        db = DatabaseManager(str(db_path))

        try:
            # 创建用户
            db.create_user('bench_user', '性能测试用户', 'bench@example.com')

            # 测试批量写入
            num_records = 1000
            records = []
            for i in range(num_records):
                record = UserRecord(
                    record_id=f'bench_exp_{i}',
                    user_id='bench_user',
                    experiment_id=f'test_{i}',
                    experiment_title=f'测试{i}',
                    status='completed',
                    started_at=datetime.now(),
                    completed_at=datetime.now(),
                    score=ExperimentScore(total=85, scientific=0, procedural=0, safety=0),
                    step_records=[],
                    context={'test': True},
                    curve_data={},
                    mistakes_summary=[]
                )
                records.append(record)

            print(f"准备写入 {num_records} 条记录...")
            start_time = time.time()
            count = db.bulk_save_experiments(records)
            write_time = time.time() - start_time

            print(f"  批量写入: {count}条记录, 耗时 {write_time:.3f}秒")
            print(f"  写入速度: {count/write_time:.0f} records/s")

            # 测试批量读取
            start_time = time.time()
            loaded_records = db.list_user_experiments('bench_user', limit=num_records)
            read_time = time.time() - start_time

            print(f"  批量读取: {len(loaded_records)}条记录, 耗时 {read_time:.3f}秒")
            print(f"  读取速度: {len(loaded_records)/read_time:.0f} records/s")

            # 测试单条查询
            num_queries = 100
            start_time = time.time()
            for i in range(num_queries):
                db.get_experiment_record(f'bench_exp_{i}')
            query_time = time.time() - start_time

            print(f"  单条查询: {num_queries}次, 耗时 {query_time:.3f}秒")
            print(f"  查询速度: {num_queries/query_time:.0f} queries/s")

            # 性能验证
            assert count/write_time > 100, f"写入性能不足: {count/write_time:.0f} records/s"
            assert len(loaded_records)/read_time > 1000, f"读取性能不足: {len(loaded_records)/read_time:.0f} records/s"

            print("\n[EXCELLENT] 数据库性能测试通过！")
            print("  预期性能提升: 相比JSON约10-50倍")

        finally:
            db.close()


def main():
    """运行所有测试"""
    print("=" * 70)
    print("数据库管理器测试")
    print("=" * 70)

    try:
        test_database_creation()
        test_user_operations()
        test_experiment_record_operations()
        test_template_operations()
        test_config_operations()
        test_statistics()

        print("\n" + "=" * 70)
        print("性能测试")
        print("=" * 70)
        benchmark_performance()

        print("\n" + "=" * 70)
        print("所有测试通过！")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] 测试错误: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
