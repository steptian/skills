#!/usr/bin/env python3
"""
功能清单管理工具 - 单一数据源的安全读写层

所有对 features.json 的修改都必须通过此工具，保证：
  1. 原子写入（写临时文件再 rename，不会出现半写状态）
  2. 文件锁（防止多进程同时写入）
  3. 自动备份（每次写入前保留快照，可随时恢复）
  4. 统计自动重算（写入时自动更新 statistics）

用法:
  feature_cli.py status                        显示功能统计概览
  feature_cli.py list [--status pending]       列出功能
  feature_cli.py next                          获取下一个待开发功能
  feature_cli.py pending-count                 获取未完成数量
  feature_cli.py begin <feature_id>            开始开发（创建会话）
  feature_cli.py complete <feature_id> [-m ""] 标记功能完成
  feature_cli.py fail <feature_id> [-m ""]     标记中断/失败
  feature_cli.py log <message>                 添加当前会话日志
  feature_cli.py recover                       从最近备份恢复
  feature_cli.py --version                     查看版本
"""

import argparse
import sys

# 将 lib 目录加入搜索路径
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from lib.core import VERSION
from lib import (
    cmd_status, cmd_list, cmd_next, cmd_context, cmd_pending_count,
    cmd_begin, cmd_complete, cmd_fail, cmd_log, cmd_recover, cmd_stale,
    cmd_deps, cmd_unblock, cmd_config, cmd_report, cmd_add, cmd_remember,
    cmd_memory, cmd_doctor,
)


def main():
    parser = argparse.ArgumentParser(
        description='功能清单管理工具（安全读写层）',
    )
    parser.add_argument('--version', '-v', action='version', version=f'harness {VERSION}')

    sub = parser.add_subparsers(dest='command')

    sub.add_parser('status', help='显示统计概览')

    p = sub.add_parser('list', help='列出功能')
    p.add_argument('--status', '-s',
                   choices=['pending', 'in_progress', 'completed', 'blocked'])

    sub.add_parser('next', help='获取下一个待开发功能')
    sub.add_parser('context', help='输出下一个功能的上下文信息')
    sub.add_parser('pending-count', help='获取未完成数量')

    p = sub.add_parser('begin', help='开始开发功能（创建会话）')
    p.add_argument('feature_id')

    p = sub.add_parser('complete', help='标记功能完成')
    p.add_argument('feature_id')
    p.add_argument('-m', '--message', help='完成说明')

    p = sub.add_parser('fail', help='标记中断/失败')
    p.add_argument('feature_id')
    p.add_argument('-m', '--message', help='原因说明')
    p.add_argument('--blocked', action='store_true', help='标记为外部阻塞（而非可继续）')

    p = sub.add_parser('log', help='添加会话日志')
    p.add_argument('message')
    p.add_argument('--type', '-t', choices=['progress', 'error', 'decision', 'test'],
                   default='progress', help='日志类型')

    sub.add_parser('recover', help='从最近的有效备份恢复')

    p = sub.add_parser('stale', help='检测僵尸会话（长时间未更新的功能）')
    p.add_argument('--hours', type=int, default=24, help='超时阈值（小时）')
    p.add_argument('--fix', action='store_true', help='自动修复僵尸会话')

    sub.add_parser('deps', help='显示功能依赖树')
    sub.add_parser('unblock', help='显示可以开始开发的功能（依赖已满足）')
    sub.add_parser('config', help='显示当前配置')

    p = sub.add_parser('report', help='生成进度汇总报告')
    p.add_argument('--export', '-e', help='导出报告到 JSON 文件')

    p = sub.add_parser('add', help='添加迭代需求到功能清单')
    p.add_argument('doc_path', help='需求文档路径')
    p.add_argument('--type', '-t', choices=['bugfix', 'feature', 'enhancement'],
                   default='feature', help='需求类型')
    p.add_argument('--force', '-f', action='store_true', help='强制添加（跳过去重检查）')

    p = sub.add_parser('remember', help='记录设计决策')
    p.add_argument('topic', help='决策主题')
    p.add_argument('reason', help='决策原因')

    p = sub.add_parser('memory', help='记忆系统管理')
    memory_sub = p.add_subparsers(dest='memory_cmd')
    memory_sub.add_parser('status', help='显示记忆系统状态')
    p_show = memory_sub.add_parser('show', help='显示指定类型的记忆')
    p_show.add_argument('mem_type', choices=['project', 'decisions', 'structure', 'interfaces'])
    p_add = memory_sub.add_parser('add', help='添加记忆条目')
    p_add.add_argument('mem_type', choices=['project', 'decisions', 'structure', 'interfaces'])
    p_add.add_argument('content', help='记忆内容')
    p_search = memory_sub.add_parser('search', help='搜索记忆内容')
    p_search.add_argument('query', help='搜索关键词')
    memory_sub.add_parser('export', help='导出记忆为可注入格式')

    sub.add_parser('doctor', help='项目健康检查')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        'status': cmd_status, 'list': cmd_list, 'next': cmd_next,
        'context': cmd_context, 'pending-count': cmd_pending_count,
        'begin': cmd_begin, 'complete': cmd_complete, 'fail': cmd_fail,
        'log': cmd_log, 'recover': cmd_recover, 'stale': cmd_stale,
        'deps': cmd_deps, 'unblock': cmd_unblock, 'config': cmd_config,
        'report': cmd_report, 'add': cmd_add, 'remember': cmd_remember,
        'memory': cmd_memory, 'doctor': cmd_doctor,
    }
    dispatch[args.command](args)


if __name__ == '__main__':
    main()
