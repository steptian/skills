"""
feature_cli 子命令实现模块
"""

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from .core import (
    C, HARNESS_DIR, MEMORY_DIR, CONFIG,
    safe_load, locked_update, format_log_entry, log_display,
)
from .anti_patterns import record_anti_pattern


def cmd_status(_args):
    data = safe_load()
    from .core import _recompute_stats
    data = _recompute_stats(data)
    stats = data['statistics']
    project = data.get('project', {})

    if project.get('name'):
        print(f"  项目: {project['name']}")
    if project.get('description'):
        print(f"  描述: {project['description']}")
    print()
    print(f"  总计 {stats['total']} | "
          f"完成 {stats['completed']} | "
          f"进行中 {stats['in_progress']} | "
          f"待开发 {stats['pending']}"
          + (f" | 阻塞 {stats['blocked']}" if stats.get('blocked') else ""))

    sessions = data.get('sessions', [])
    if sessions:
        latest = sessions[-1]
        print(f"\n  最近会话: [{latest.get('id')}] "
              f"{latest.get('feature_id', '?')} - {latest.get('status', '?')}")
        for log_entry in (latest.get('logs') or [])[-3:]:
            print(f"     · {log_display(log_entry)}")


def cmd_list(args):
    data = safe_load()
    features = data.get('features', [])
    if args.status:
        features = [f for f in features if f.get('status') == args.status]
    if not features:
        print("  没有匹配的功能")
        return

    pi = {"urgent": "🔴⭐", "high": "🔴", "medium": "🟡", "low": "🟢"}
    si = {"completed": "✅", "in_progress": "🔄", "pending": "⏳", "blocked": "⛔"}
    for f in features:
        print(f"  {si.get(f.get('status',''),'❓')} "
              f"{pi.get(f.get('priority',''),'⚪')} "
              f"[{f['id']}] {f.get('description','')}")


def cmd_next(_args):
    """输出下一个应开发的功能"""
    data = safe_load()
    features = data.get('features', [])

    in_progress = [f for f in features if f.get('status') == 'in_progress']
    if in_progress:
        f = in_progress[0]
        print(f"[{f['id']}] {f.get('description', '')}")
        return

    completed_ids = {f['id'] for f in features if f.get('status') == 'completed'}
    pri = {'urgent': -1, 'high': 0, 'medium': 1, 'low': 2}
    available = [
        f for f in features
        if f.get('status') == 'pending'
        and all(d in completed_ids for d in f.get('dependencies', []))
    ]
    if not available:
        pending = [f for f in features if f.get('status') == 'pending']
        if pending:
            print(f"有 {len(pending)} 个 pending 功能但依赖未满足", file=sys.stderr)
        return

    available.sort(key=lambda f: pri.get(f.get('priority', 'medium'), 1))
    f = available[0]
    print(f"[{f['id']}] {f.get('description', '')}")


def cmd_context(_args):
    """输出下一个功能的上下文信息"""
    data = safe_load()
    features = data.get('features', [])
    sessions = data.get('sessions', [])

    in_progress = [f for f in features if f.get('status') == 'in_progress']
    if in_progress:
        target = in_progress[0]
    else:
        completed_ids = {f['id'] for f in features if f.get('status') == 'completed'}
        pri = {'urgent': -1, 'high': 0, 'medium': 1, 'low': 2}
        available = [
            f for f in features
            if f.get('status') == 'pending'
            and all(d in completed_ids for d in f.get('dependencies', []))
        ]
        if not available:
            return
        available.sort(key=lambda f: pri.get(f.get('priority', 'medium'), 1))
        target = available[0]

    fid = target['id']
    print(f"FEATURE_ID={fid}")
    print(f"DESCRIPTION={target.get('description', '')}")
    print(f"CATEGORY={target.get('category', 'feature')}")
    print(f"PRIORITY={target.get('priority', 'medium')}")
    print(f"STATUS={target.get('status', 'pending')}")

    steps = target.get('steps', [])
    if steps:
        print("STEPS:")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step}")

    criteria = target.get('acceptance_criteria', [])
    if criteria:
        print("ACCEPTANCE_CRITERIA:")
        for c in criteria:
            print(f"  - {c}")

    interrupt_reason = target.get('interrupt_reason')
    if interrupt_reason:
        print(f"INTERRUPT_REASON={interrupt_reason}")

    interrupt_count = target.get('interrupt_count', 0)
    if interrupt_count:
        print(f"INTERRUPT_COUNT={interrupt_count}")

    last_interrupted = target.get('last_interrupted_at')
    if last_interrupted:
        print(f"LAST_INTERRUPTED_AT={last_interrupted}")

    feature_sessions = [s for s in sessions if s.get('feature_id') == fid]
    if feature_sessions:
        latest = feature_sessions[-1]
        print(f"LAST_SESSION={latest.get('id', '?')}")
        print(f"LAST_SESSION_STATUS={latest.get('status', '?')}")
        if latest.get('started_at'):
            print(f"LAST_SESSION_STARTED={latest['started_at']}")
        logs = latest.get('logs', [])
        if logs:
            print("RECENT_LOGS:")
            for log in logs[-5:]:
                print(f"  - {log}")

    total_sessions_for_feature = len(feature_sessions)
    if total_sessions_for_feature > 1:
        print(f"TOTAL_ATTEMPTS={total_sessions_for_feature}")


def cmd_pending_count(_args):
    data = safe_load()
    count = sum(1 for f in data['features']
                if f.get('status') in ('pending', 'in_progress'))
    print(count)


def cmd_begin(args):
    def updater(data):
        fid = args.feature_id
        found = False
        for f in data['features']:
            if f['id'] == fid:
                if f['status'] == 'completed':
                    print(f"{C.Y}警告: {fid} 已完成，跳过{C.N}", file=sys.stderr)
                    return data
                f['status'] = 'in_progress'
                found = True
                break
        if not found:
            print(f"{C.R}错误: 找不到功能 {fid}{C.N}", file=sys.stderr)
            return data

        sessions = data.setdefault('sessions', [])

        max_running = CONFIG.get('max_running_sessions', 1)
        running = [s for s in sessions if s.get('status') == 'running']
        if len(running) >= max_running:
            if not getattr(args, 'force', False):
                running_ids = ", ".join(s.get('feature_id', '?') for s in running)
                print(
                    f"{C.Y}警告: 已有 {len(running)} 个运行中的会话 ({running_ids})，"
                    f"上限 {max_running}{C.N}",
                    file=sys.stderr,
                )
                print(f"自动关闭最早的 running 会话...", file=sys.stderr)
                for stale in running[:len(running) - max_running + 1]:
                    stale['status'] = 'interrupted'
                    stale['ended_at'] = datetime.now().isoformat()
                    stale['logs'].append(format_log_entry("被新会话抢占，自动中断", "auto_preempt"))

        sid = f"SESSION-{len(sessions) + 1:02d}"
        sessions.append({
            'id': sid,
            'feature_id': fid,
            'started_at': datetime.now().isoformat(),
            'ended_at': None,
            'status': 'running',
            'logs': [],
        })
        print(sid)
        return data
    locked_update(updater)


def cmd_complete(args):
    def updater(data):
        fid = args.feature_id
        found = False
        for f in data['features']:
            if f['id'] == fid:
                f['status'] = 'completed'
                f['passes'] = True
                f['completed_at'] = datetime.now().isoformat()
                found = True
                break
        if not found:
            print(f"{C.R}错误: 找不到功能 {fid}{C.N}", file=sys.stderr)
            return data

        for s in reversed(data.get('sessions', [])):
            if s.get('feature_id') == fid and s.get('status') == 'running':
                s['status'] = 'completed'
                s['ended_at'] = datetime.now().isoformat()
                if args.message:
                    s['logs'].append(format_log_entry(args.message, "complete"))
                break
        print(f"{C.G}✓ 功能 {fid} 已完成{C.N}")
        return data
    locked_update(updater)


def cmd_fail(args):
    def updater(data):
        fid = args.feature_id
        is_blocked = getattr(args, 'blocked', False)
        found = False
        for f in data['features']:
            if f['id'] == fid:
                old_status = f.get('status', 'pending')
                if old_status == 'completed':
                    f['last_completed_at'] = f.get('completed_at')
                    f['completed_at'] = None

                f['status'] = 'blocked' if is_blocked else 'in_progress'
                f['passes'] = False
                if args.message:
                    f['interrupt_reason'] = args.message

                f['interrupt_count'] = f.get('interrupt_count', 0) + 1
                f['last_interrupted_at'] = datetime.now().isoformat()

                found = True
                break
        if not found:
            print(f"{C.R}错误: 找不到功能 {fid}{C.N}", file=sys.stderr)
            return data

        for s in reversed(data.get('sessions', [])):
            if s.get('feature_id') == fid and s.get('status') == 'running':
                s['status'] = 'interrupted'
                s['ended_at'] = datetime.now().isoformat()
                log_type = "blocked" if is_blocked else "interrupt"
                if args.message:
                    s['logs'].append(format_log_entry(args.message, log_type))
                break

        # 获取实际的 interrupt_count 用于显示
        actual_count = 0
        for f in data['features']:
            if f['id'] == fid:
                actual_count = f.get('interrupt_count', 0)
                break

        if is_blocked:
            print(f"{C.R}⛔ 功能 {fid} 已阻塞: {args.message or '未说明'}{C.N}")
        else:
            print(f"{C.Y}⚠ 功能 {fid} 已中断（第{actual_count}次），下次会话将继续{C.N}")

        record_anti_pattern(fid, args.message or "", is_blocked)
        return data
    locked_update(updater)


def cmd_log(args):
    log_type = getattr(args, 'type', None) or "progress"

    def updater(data):
        for s in reversed(data.get('sessions', [])):
            if s.get('status') == 'running':
                s['logs'].append(format_log_entry(args.message, log_type))
                print(f"已记录到 {s['id']}")
                return data
        print(f"{C.Y}警告: 没有运行中的会话，日志未记录{C.N}", file=sys.stderr)
        return data
    locked_update(updater)


def cmd_recover(_args):
    from .core import BACKUP_DIR, FEATURES_FILE
    if not BACKUP_DIR.exists():
        print(f"{C.R}没有可用的备份{C.N}")
        return
    backups = sorted(BACKUP_DIR.glob('features_*.json'))
    if not backups:
        print(f"{C.R}没有可用的备份{C.N}")
        return

    for candidate in reversed(backups):
        try:
            with open(candidate, 'r', encoding='utf-8') as f:
                json.load(f)
            shutil.copy2(candidate, FEATURES_FILE)
            print(f"{C.G}✓ 已从 {candidate.name} 恢复{C.N}")
            return
        except json.JSONDecodeError:
            continue
    print(f"{C.R}所有备份均已损坏{C.N}")


def cmd_stale(args):
    """检测并处理僵尸会话"""
    from .core import BACKUP_DIR, _recompute_stats
    stale_hours = args.hours if hasattr(args, 'hours') and args.hours else CONFIG.get('stale_hours', 24)

    def updater(data):
        now = datetime.now()
        features = data.get('features', [])
        sessions = data.get('sessions', [])
        stale_features = []

        for f in features:
            if f.get('status') != 'in_progress':
                continue

            feature_sessions = [s for s in sessions if s.get('feature_id') == f['id']]
            if not feature_sessions:
                stale_features.append((f, "无会话记录"))
                continue

            latest_session = feature_sessions[-1]
            session_time = latest_session.get('started_at') or latest_session.get('ended_at')

            if session_time:
                try:
                    last_update = datetime.fromisoformat(session_time)
                    hours_elapsed = (now - last_update).total_seconds() / 3600
                    if hours_elapsed > stale_hours:
                        stale_features.append((f, f"已过 {hours_elapsed:.1f} 小时"))
                except (ValueError, TypeError):
                    stale_features.append((f, "时间格式错误"))

        if not stale_features:
            print(f"{C.G}✓ 没有检测到僵尸会话（超时阈值: {stale_hours}h）{C.N}")
            return data

        print(f"{C.Y}检测到 {len(stale_features)} 个僵尸会话:{C.N}")
        for f, reason in stale_features:
            print(f"  [{f['id']}] {f.get('description', '')} - {reason}")

        if hasattr(args, 'fix') and args.fix:
            print(f"\n{C.B}正在修复...{C.N}")
            for f, _ in stale_features:
                f['interrupt_reason'] = f"自动检测: 会话超时（>{stale_hours}h）"
                for s in reversed(sessions):
                    if s.get('feature_id') == f['id'] and s.get('status') == 'running':
                        s['status'] = 'interrupted'
                        s['ended_at'] = now.isoformat()
                        s['logs'].append(format_log_entry("会话超时，标记为中断", "auto_stale"))
                        break
            print(f"{C.G}✓ 已修复 {len(stale_features)} 个僵尸会话{C.N}")

        return data

    locked_update(updater)


def cmd_deps(_args):
    """显示功能依赖树"""
    data = safe_load()
    features = data.get('features', [])
    feature_map = {f['id']: f for f in features}

    def print_tree(fid, indent=0, visited=None):
        if visited is None:
            visited = set()
        if fid in visited:
            print("  " * indent + f"↻ {fid} (循环依赖!)")
            return
        visited.add(fid)

        f = feature_map.get(fid)
        if not f:
            return

        si = {"completed": "✅", "in_progress": "🔄", "pending": "⏳", "blocked": "⛔"}
        status_icon = si.get(f.get('status', ''), '❓')

        deps = f.get('dependencies', [])
        if indent == 0:
            print(f"{status_icon} [{fid}] {f.get('description', '')}")
        else:
            print("  " * indent + f"└─ {status_icon} [{fid}] {f.get('description', '')}")

        for dep_id in deps:
            print_tree(dep_id, indent + 1, visited.copy())

    all_deps = set()
    for f in features:
        all_deps.update(f.get('dependencies', []))

    roots = [f for f in features if f['id'] not in all_deps]
    if not roots:
        roots = features

    print(f"{C.B}功能依赖树:{C.N}")
    for f in roots:
        print_tree(f['id'])
        print()


def cmd_unblock(_args):
    """显示可以开始开发的功能"""
    data = safe_load()
    features = data.get('features', [])

    completed_ids = {f['id'] for f in features if f.get('status') == 'completed'}
    in_progress_ids = {f['id'] for f in features if f.get('status') == 'in_progress'}

    pri = {'urgent': -1, 'high': 0, 'medium': 1, 'low': 2}
    pi = {"urgent": "🔴⭐", "high": "🔴", "medium": "🟡", "low": "🟢"}

    unblocked = []
    blocked = []

    for f in features:
        if f.get('status') not in ('pending', 'blocked'):
            continue

        deps = f.get('dependencies', [])
        missing_deps = [d for d in deps if d not in completed_ids]

        if missing_deps:
            blocked.append((f, missing_deps))
        else:
            unblocked.append(f)

    unblocked.sort(key=lambda f: pri.get(f.get('priority', 'medium'), 1))

    if unblocked:
        print(f"{C.G}已解锁（可开始开发）:{C.N}")
        for f in unblocked:
            print(f"  {pi.get(f.get('priority', ''), '⚪')} "
                  f"[{f['id']}] {f.get('description', '')}")
    else:
        print(f"{C.Y}没有已解锁的功能{C.N}")

    print()

    if blocked:
        print(f"{C.R}被阻塞（等待依赖）:{C.N}")
        for f, missing in blocked:
            missing_str = ", ".join(missing)
            print(f"  [{f['id']}] {f.get('description', '')} "
                  f"{C.R}(等待: {missing_str}){C.N}")

    print()
    print(f"已完成: {len(completed_ids)} | 进行中: {len(in_progress_ids)} | "
          f"已解锁: {len(unblocked)} | 被阻塞: {len(blocked)}")


def cmd_config(_args):
    """显示当前配置"""
    from .core import DEFAULT_CONFIG, CONFIG_FILE
    print(f"{C.B}当前配置:{C.N}")
    print(f"  配置文件: {CONFIG_FILE}")
    print()
    for key, value in CONFIG.items():
        default_val = DEFAULT_CONFIG.get(key)
        marker = "" if value == default_val else f" {C.Y}(默认: {default_val}){C.N}"
        print(f"  {key}: {value}{marker}")

    if not CONFIG_FILE.exists():
        print()
        print(f"{C.Y}提示: 配置文件不存在，使用默认值{C.N}")
        print(f"  创建 {CONFIG_FILE} 来自定义配置")


def cmd_report(args):
    """生成进度汇总报告"""
    from .core import _recompute_stats
    data = safe_load()
    project = data.get('project', {})
    features = data.get('features', [])
    sessions = data.get('sessions', [])

    print(f"{C.CYAN}{'='*50}{C.N}")
    print(f"{C.CYAN}  项目进度报告{C.N}")
    print(f"{C.CYAN}{'='*50}{C.N}")
    print()

    if project.get('name'):
        print(f"{C.B}项目: {C.N}{project['name']}")
    if project.get('description'):
        print(f"{C.B}描述: {C.N}{project['description']}")
    if project.get('created_at'):
        print(f"{C.B}创建: {C.N}{project['created_at']}")
    print()

    stats = _recompute_stats(data)['statistics']

    print(f"{C.B}功能统计:{C.N}")
    print(f"  总计: {stats['total']}")
    print(f"  {C.G}完成: {stats['completed']}{C.N}")
    print(f"  {C.Y}进行中: {stats['in_progress']}{C.N}")
    print(f"  待开发: {stats['pending']}")
    if stats['blocked'] > 0:
        print(f"  {C.R}阻塞: {stats['blocked']}{C.N}")

    if stats['total'] > 0:
        progress = stats['completed'] / stats['total']
        bar_len = 30
        filled = int(bar_len * progress)
        bar = '█' * filled + '░' * (bar_len - filled)
        print(f"\n  [{C.G}{bar}{C.N}] {progress*100:.1f}%")

    print()

    if sessions:
        print(f"{C.B}会话统计:{C.N}")
        print(f"  总会话数: {len(sessions)}")

        completed_sessions = sum(1 for s in sessions if s.get('status') == 'completed')
        interrupted_sessions = sum(1 for s in sessions if s.get('status') == 'interrupted')
        running_sessions = sum(1 for s in sessions if s.get('status') == 'running')

        print(f"  {C.G}完成: {completed_sessions}{C.N} | "
              f"{C.Y}中断: {interrupted_sessions}{C.N} | "
              f"运行中: {running_sessions}")

        durations = []
        for s in sessions:
            if s.get('started_at') and s.get('ended_at'):
                try:
                    start = datetime.fromisoformat(s['started_at'])
                    end = datetime.fromisoformat(s['ended_at'])
                    durations.append((end - start).total_seconds() / 60)
                except (ValueError, TypeError):
                    pass

        if durations:
            avg_duration = sum(durations) / len(durations)
            total_duration = sum(durations)
            print(f"  平均会话时长: {avg_duration:.1f} 分钟")
            print(f"  总开发时长: {total_duration:.1f} 分钟 ({total_duration/60:.1f} 小时)")

        print()

    if sessions:
        print(f"{C.B}最近会话:{C.N}")
        for s in sessions[-5:]:
            status_icon = {'completed': '✅', 'interrupted': '⚠️', 'running': '🔄'}.get(s.get('status'), '❓')
            feature_id = s.get('feature_id', '?')
            started = s.get('started_at', '')[:10] if s.get('started_at') else '?'
            print(f"  {status_icon} [{feature_id}] {started} ({s.get('id', '?')})")
        print()

    # v2 关键指标
    print(f"{C.B}v2 关键指标:{C.N}")

    total_interrupts = sum(f.get('interrupt_count', 0) for f in features)
    features_with_interrupts = sum(1 for f in features if f.get('interrupt_count', 0) > 0)
    print(f"  总中断次数: {total_interrupts} (涉及 {features_with_interrupts} 个功能)")

    feature_attempts = {}
    for s in sessions:
        fid = s.get('feature_id')
        if fid:
            feature_attempts.setdefault(fid, []).append(s)

    multi_attempt = {fid: ss for fid, ss in feature_attempts.items() if len(ss) > 1}
    if multi_attempt:
        print(f"  多次尝试的功能: {len(multi_attempt)}")
        for fid, ss in sorted(multi_attempt.items(), key=lambda x: -len(x[1]))[:5]:
            print(f"    [{fid}] {len(ss)} 次会话")

    sessions_with_logs = sum(1 for s in sessions if s.get('logs'))
    print(f"  有效会话率: {sessions_with_logs}/{len(sessions)} "
          f"({sessions_with_logs / max(len(sessions), 1) * 100:.0f}%)")

    success_rate = stats['completed'] / max(stats['total'], 1) * 100
    print(f"  任务完成率: {success_rate:.1f}%")
    print()

    if hasattr(args, 'export') and args.export:
        export_file = args.export
        export_data = {
            'project': project,
            'statistics': stats,
            'sessions': sessions,
            'features': features,
            'generated_at': datetime.now().isoformat(),
        }
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        print(f"{C.G}✓ 报告已导出到: {export_file}{C.N}")


def cmd_add(args):
    """添加迭代需求到功能清单"""
    doc_path = Path(args.doc_path)
    if not doc_path.exists():
        print(f"{C.R}错误: 文件不存在: {doc_path}{C.N}", file=sys.stderr)
        return

    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.strip().split('\n')
    title = ""
    description_lines = []
    in_frontmatter = False

    for line in lines:
        if line.strip() == '---':
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if line.startswith('# ') and not title:
            title = line[2:].strip()
        else:
            description_lines.append(line)

    if not title:
        title = doc_path.stem

    description = '\n'.join(description_lines).strip() or title

    req_type = getattr(args, 'type', None) or 'feature'
    priority_map = {'bugfix': 'high', 'feature': 'medium', 'enhancement': 'low'}
    priority = priority_map.get(req_type, 'medium')

    def updater(data):
        features = data.setdefault('features', [])
        existing_ids = [f['id'] for f in features]
        max_num = 0
        for fid in existing_ids:
            if fid.startswith('F') and fid[1:].isdigit():
                max_num = max(max_num, int(fid[1:]))
        new_id = f"F{max_num + 1:03d}"

        if not getattr(args, 'force', False):
            for f in features:
                if title.lower() in f.get('description', '').lower():
                    print(f"{C.Y}警告: 可能存在相似功能 [{f['id']}] {f.get('description')}{C.N}")
                    print(f"使用 --force 强制添加")
                    return data

        new_feature = {
            'id': new_id,
            'priority': priority,
            'status': 'pending',
            'description': title,
            'steps': [],
            'acceptance_criteria': [],
            'dependencies': [],
            'source': str(doc_path),
            'type': req_type,
            'created_at': datetime.now().isoformat(),
        }

        features.append(new_feature)
        print(f"{C.G}✓ 已添加 [{new_id}] {title}{C.N}")
        return data

    locked_update(updater)


def cmd_remember(args):
    """记录设计决策到 memory/decisions.md"""
    MEMORY_DIR.mkdir(exist_ok=True)
    decisions_file = MEMORY_DIR / "decisions.md"

    topic = args.topic
    reason = args.reason

    if decisions_file.exists():
        with open(decisions_file, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = "# 设计决策记录\n\n记录项目中的关键设计决策及其原因。\n\n---\n\n"

    today = datetime.now().strftime('%Y-%m-%d')
    new_entry = f"""
## {today} {topic}

**决策**: {topic}

**原因**: {reason}


---

"""

    content += new_entry

    with open(decisions_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"{C.G}✓ 已记录设计决策: {topic}{C.N}")


def cmd_memory(args):
    """记忆系统管理"""
    from .anti_patterns import ANTI_PATTERNS_FILE
    MEMORY_DIR.mkdir(exist_ok=True)

    subcmd = args.memory_cmd

    if subcmd == 'status':
        print(f"{C.B}记忆系统状态:{C.N}")
        print(f"  目录: {MEMORY_DIR}")

        memory_files = {
            'project.json': '项目信息',
            'decisions.md': '设计决策',
            'structure.md': '代码结构',
            'interfaces.md': '接口文档',
        }

        for filename, desc in memory_files.items():
            filepath = MEMORY_DIR / filename
            if filepath.exists():
                size = filepath.stat().st_size
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                print(f"  {C.G}✓{C.N} {filename} ({desc}) - {size}B, {mtime}")
            else:
                print(f"  {C.Y}○{C.N} {filename} ({desc}) - 未创建")

        history_dir = MEMORY_DIR / "history"
        if history_dir.exists():
            history_count = len(list(history_dir.glob("*.md")))
            print(f"  {C.G}✓{C.N} history/ - {history_count} 条历史记录")
        else:
            print(f"  {C.Y}○{C.N} history/ - 未创建")

    elif subcmd == 'show':
        mem_type = args.mem_type
        file_map = {
            'project': 'project.json',
            'decisions': 'decisions.md',
            'structure': 'structure.md',
            'interfaces': 'interfaces.md',
        }

        if mem_type not in file_map:
            print(f"{C.R}错误: 未知的记忆类型 '{mem_type}'{C.N}", file=sys.stderr)
            print(f"可用类型: {', '.join(file_map.keys())}")
            return

        filepath = MEMORY_DIR / file_map[mem_type]
        if not filepath.exists():
            print(f"{C.Y}记忆文件不存在: {filepath}{C.N}")
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            print(f.read())

    elif subcmd == 'add':
        mem_type = args.mem_type
        content = args.content

        if mem_type == 'decisions':
            print(f"{C.Y}提示: 请使用 'remember' 命令添加设计决策{C.N}")
            return
        elif mem_type == 'project':
            project_file = MEMORY_DIR / "project.json"
            if project_file.exists():
                with open(project_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"name": "", "tech_stack": [], "architecture": {}, "key_directories": {}}

            if '=' in content:
                key, value = content.split('=', 1)
                data[key.strip()] = value.strip()

            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"{C.G}✓ 已更新 project.json{C.N}")
        else:
            file_map = {'structure': 'structure.md', 'interfaces': 'interfaces.md'}
            if mem_type in file_map:
                filepath = MEMORY_DIR / file_map[mem_type]
                with open(filepath, 'a', encoding='utf-8') as f:
                    f.write(f"\n{content}\n")
                print(f"{C.G}✓ 已添加到 {file_map[mem_type]}{C.N}")

    elif subcmd == 'search':
        query = args.query.lower()
        print(f"{C.B}搜索: {query}{C.N}\n")

        for filepath in MEMORY_DIR.glob("*"):
            if filepath.is_file() and filepath.suffix in ['.md', '.json']:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if query in content.lower():
                        print(f"{C.CYAN}{filepath.name}:{C.N}")
                        for i, line in enumerate(content.split('\n'), 1):
                            if query in line.lower():
                                print(f"  L{i}: {line[:100]}...")
                        print()

    elif subcmd == 'export':
        print(f"{C.B}项目记忆导出:{C.N}\n")

        project_file = MEMORY_DIR / "project.json"
        if project_file.exists():
            with open(project_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('name'):
                print(f"**项目**: {data['name']}")
            if data.get('tech_stack'):
                print(f"**技术栈**: {', '.join(data['tech_stack'])}")

        decisions_file = MEMORY_DIR / "decisions.md"
        if decisions_file.exists():
            with open(decisions_file, 'r', encoding='utf-8') as f:
                content = f.read()
            titles = re.findall(r'^## \d{4}-\d{2}-\d{2} (.+)$', content, re.MULTILINE)
            if titles:
                print(f"\n**关键决策**:")
                for title in titles[-5:]:
                    print(f"- {title}")

        if ANTI_PATTERNS_FILE.exists():
            try:
                with open(ANTI_PATTERNS_FILE, 'r', encoding='utf-8') as f:
                    ap_data = json.load(f)
                history = ap_data.get("history", [])
                if history:
                    from collections import Counter
                    cat_counts = Counter(e.get("category", "unknown") for e in history)
                    categories = ap_data.get("categories", {})

                    print(f"\n**已知失败模式** ({len(history)} 次记录):")
                    for cat_id, count in cat_counts.most_common(5):
                        cat_info = categories.get(cat_id, {})
                        label = cat_info.get("label", cat_id)
                        countermeasure = cat_info.get("countermeasure", "")
                        print(f"- {label} ({count}次)")
                        if countermeasure:
                            print(f"  对策: {countermeasure}")
            except (json.JSONDecodeError, IOError):
                pass


def cmd_doctor(_args):
    """项目健康检查"""
    from .core import FEATURES_FILE, BACKUP_DIR, _recompute_stats
    print(f"{C.CYAN}{'='*50}{C.N}")
    print(f"{C.CYAN}  Harness 项目健康检查{C.N}")
    print(f"{C.CYAN}{'='*50}{C.N}\n")

    issues = []

    print(f"{C.B}[1/5] 核心文件检查{C.N}")
    core_files = [
        ('features.json', '功能清单'),
        ('config.json', '配置文件'),
        ('feature_cli.py', 'CLI 工具'),
        ('dev.sh', '开发入口'),
    ]

    for filename, desc in core_files:
        filepath = HARNESS_DIR / filename
        if filepath.exists():
            print(f"  {C.G}✓{C.N} {filename} ({desc})")
        else:
            print(f"  {C.R}✗{C.N} {filename} ({desc}) - 缺失")
            issues.append(f"缺失 {filename}")

    print(f"\n{C.B}[2/5] 目录结构检查{C.N}")
    dirs = [
        ('.backups', '备份目录'),
        ('logs', '日志目录'),
        ('memory', '记忆系统'),
        ('prompts', 'Prompt 模板'),
    ]

    for dirname, desc in dirs:
        dirpath = HARNESS_DIR / dirname
        if dirpath.exists() and dirpath.is_dir():
            count = len(list(dirpath.iterdir()))
            print(f"  {C.G}✓{C.N} {dirname}/ ({desc}) - {count} 个文件")
        else:
            print(f"  {C.Y}○{C.N} {dirname}/ ({desc}) - 不存在")

    print(f"\n{C.B}[3/5] 功能状态检查{C.N}")
    if FEATURES_FILE.exists():
        data = safe_load()
        stats = _recompute_stats(data)['statistics']

        print(f"  总计: {stats['total']} | 完成: {stats['completed']} | "
              f"进行中: {stats['in_progress']} | 待开发: {stats['pending']}")

        in_progress_count = sum(1 for f in data.get('features', []) if f.get('status') == 'in_progress')
        if in_progress_count > 0:
            print(f"  {C.Y}⚠{C.N} 有 {in_progress_count} 个进行中的功能，检查是否需要清理")
            issues.append(f"{in_progress_count} 个进行中的功能")
    else:
        print(f"  {C.Y}○{C.N} 功能清单不存在")

    print(f"\n{C.B}[4/5] 备份检查{C.N}")
    if BACKUP_DIR.exists():
        backups = list(BACKUP_DIR.glob("features_*.json"))
        print(f"  备份数量: {len(backups)}")
        if backups:
            latest = sorted(backups)[-1]
            mtime = datetime.fromtimestamp(latest.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            print(f"  最新备份: {latest.name} ({mtime})")
    else:
        print(f"  {C.Y}○{C.N} 无备份目录")

    print(f"\n{C.B}[5/5] Git 状态检查{C.N}")
    git_dir = HARNESS_DIR.parent / '.git'
    if git_dir.exists():
        print(f"  {C.G}✓{C.N} Git 仓库已初始化")

        import subprocess
        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=HARNESS_DIR.parent,
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                uncommitted = len(result.stdout.strip().split('\n'))
                print(f"  {C.Y}⚠{C.N} 有 {uncommitted} 个未提交的变更")
                issues.append(f"{uncommitted} 个未提交的变更")
            else:
                print(f"  {C.G}✓{C.N} 工作区干净")
        except Exception:
            print(f"  {C.Y}?{C.N} 无法检查 Git 状态")
    else:
        print(f"  {C.Y}○{C.N} 未初始化 Git 仓库")

    print(f"\n{C.CYAN}{'='*50}{C.N}")
    if issues:
        print(f"{C.Y}发现 {len(issues)} 个问题:{C.N}")
        for issue in issues:
            print(f"  - {issue}")
        print(f"\n建议运行: python3 .harness/feature_cli.py stale --fix")
    else:
        print(f"{C.G}✓ 项目状态良好{C.N}")
