#!/usr/bin/env python
"""
开源项目集成健康检查脚本
检查所有依赖、插件状态、潜在冲突并生成详细报告
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# 设置UTF-8编码输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.plugins import registry
from src.utils.dependency_checker import DependencyChecker


def main():
    """执行完整的集成健康检查"""
    print("="*80)
    print("VirtualChemLab 开源项目集成健康检查")
    print("="*80 + "\n")

    # 1. 检查依赖
    print("📦 步骤 1/3: 检查依赖库...")
    checker = DependencyChecker()
    dep_report = checker.check_all()
    checker.print_report(dep_report)

    # 2. 检查插件系统
    print("\n🔌 步骤 2/3: 检查插件系统...")
    registry.print_health_report()
    plugin_report = registry.get_health_report()

    # 3. 生成综合报告
    print("\n📊 步骤 3/3: 生成综合报告...")

    # 计算总体评分
    dep_score = dep_report['summary']['core_percentage']
    plugin_score = plugin_report['health_percentage']

    # 可选依赖和增强功能的加权
    optional_score = dep_report['summary'].get('optional_percentage', 0)

    # 总分计算: 核心40% + 插件30% + 可选30%
    total_score = (dep_score * 0.4 + plugin_score * 0.3 + optional_score * 0.3)

    # 评级
    if total_score >= 90:
        grade = "A (优秀)"
        emoji = "🟢"
    elif total_score >= 80:
        grade = "B (良好)"
        emoji = "🟡"
    elif total_score >= 70:
        grade = "C (合格)"
        emoji = "🟠"
    else:
        grade = "D (需改进)"
        emoji = "🔴"

    # 综合报告
    comprehensive_report = {
        'timestamp': datetime.now().isoformat(),
        'score': round(total_score, 2),
        'grade': grade,
        'python_version': dep_report['summary']['python_version'],
        'dependencies': {
            'core': {
                'installed': dep_report['summary']['core_installed'],
                'total': dep_report['summary']['core_total'],
                'percentage': round(dep_report['summary']['core_percentage'], 2)
            },
            'optional': {
                'installed': dep_report['summary'].get('optional_installed', 0),
                'total': dep_report['summary'].get('optional_total', 0),
                'percentage': round(dep_report['summary'].get('optional_percentage', 0), 2)
            }
        },
        'plugins': {
            'total': plugin_report['total_plugins'],
            'available': plugin_report['available'],
            'missing': plugin_report['missing'],
            'errors': plugin_report['errors'],
            'percentage': round(plugin_report['health_percentage'], 2)
        },
        'issues': {
            'missing_core_deps': dep_report['issues']['missing_core'],
            'version_conflicts': dep_report['issues']['version_conflicts'],
            'import_errors': dep_report['issues']['import_errors'],
            'plugin_conflicts': plugin_report['conflict_warnings'],
            'potential_conflicts': dep_report['issues']['potential_conflicts']
        },
        'recommendations': []
    }

    # 生成建议
    recommendations = []

    if dep_report['issues']['missing_core']:
        recommendations.append({
            'priority': 'HIGH',
            'category': '核心依赖',
            'action': '安装缺失的核心依赖',
            'command': 'pip install ' + ' '.join([d['name'] for d in dep_report['issues']['missing_core']])
        })

    if dep_report['issues']['version_conflicts']:
        recommendations.append({
            'priority': 'HIGH',
            'category': '版本冲突',
            'action': '升级或降级冲突的依赖',
            'details': dep_report['issues']['version_conflicts']
        })

    if plugin_report['missing'] > 0:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': '可选插件',
            'action': '安装可选插件以获得完整功能',
            'command': 'pip install -r requirements-optional.txt'
        })

    # 检查增强功能
    enhanced_missing = []
    for dep_name in ['langchain', 'sphinx', 'pubchempy', 'qtawesome', 'pint', 'tinydb']:
        if dep_name not in dep_report['all_dependencies'] or \
           dep_report['all_dependencies'][dep_name]['status'] != 'installed':
            enhanced_missing.append(dep_name)

    if enhanced_missing:
        recommendations.append({
            'priority': 'LOW',
            'category': '增强功能',
            'action': '安装增强功能库',
            'command': 'pip install -r requirements-enhanced.txt',
            'missing': enhanced_missing
        })

    comprehensive_report['recommendations'] = recommendations

    # 保存报告
    report_file = Path('开源集成健康检查报告.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(comprehensive_report, f, indent=2, ensure_ascii=False)

    # 打印总结
    print("\n" + "="*80)
    print("综合评估结果")
    print("="*80 + "\n")

    print(f"{emoji} 总体评分: {total_score:.1f}/100")
    print(f"   等级: {grade}\n")

    print(f"核心依赖: {comprehensive_report['dependencies']['core']['percentage']}% "
          f"({comprehensive_report['dependencies']['core']['installed']}/{comprehensive_report['dependencies']['core']['total']})")
    print(f"可选依赖: {comprehensive_report['dependencies']['optional']['percentage']}% "
          f"({comprehensive_report['dependencies']['optional']['installed']}/{comprehensive_report['dependencies']['optional']['total']})")
    print(f"插件系统: {comprehensive_report['plugins']['percentage']}% "
          f"({comprehensive_report['plugins']['available']}/{comprehensive_report['plugins']['total']})")

    # 打印建议
    if recommendations:
        print("\n📋 改进建议:\n")
        for i, rec in enumerate(recommendations, 1):
            priority_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(rec['priority'], '⚪')
            print(f"{i}. {priority_emoji} [{rec['category']}] {rec['action']}")
            if 'command' in rec:
                print(f"   命令: {rec['command']}")
            if 'missing' in rec:
                print(f"   缺失: {', '.join(rec['missing'])}")
            print()

    print(f"\n详细报告已保存至: {report_file.absolute()}")
    print("="*80 + "\n")

    # 返回状态码
    if total_score >= 80:
        return 0  # 成功
    elif total_score >= 70:
        return 1  # 警告
    else:
        return 2  # 错误


if __name__ == '__main__':
    sys.exit(main())
