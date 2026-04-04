#!/usr/bin/env python3
"""
云效流水线 API 调用工具

使用方式:
    python3 pipeline_api.py list                    # 获取流水线列表
    python3 pipeline_api.py list --json             # JSON 格式输出
    python3 pipeline_api.py run <pipelineId>        # 运行流水线
    python3 pipeline_api.py status <pipelineId>     # 查看状态
"""

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

# 固定配置
ORGANIZATION_ID = "6475aec3c3226d3f2e4e0f30"
DEFAULT_DOMAIN = "openapi-rdc.aliyuncs.com"

# 全局参数
JSON_OUTPUT = False
NON_INTERACTIVE = False


def is_interactive() -> bool:
    """检查是否在交互式终端"""
    return sys.stdin.isatty() and not NON_INTERACTIVE


def load_config() -> Dict[str, str]:
    """加载配置文件"""
    # 读取 Token 配置
    token_file = Path.home() / ".yunxiaorc"
    if not token_file.exists():
        print("❌ 未找到配置文件 ~/.yunxiaorc")
        print("请创建配置文件并添加以下内容:")
        print(json.dumps({"token": "pt-xxxxxxxx", "domain": DEFAULT_DOMAIN}, indent=2))
        sys.exit(1)

    try:
        with open(token_file) as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print("❌ ~/.yunxiaorc 格式错误，请检查 JSON 格式")
        sys.exit(1)

    if "token" not in config:
        print("❌ ~/.yunxiaorc 中缺少 token 字段")
        sys.exit(1)

    return {
        "token": config["token"],
        "domain": config.get("domain", DEFAULT_DOMAIN)
    }


def load_pipeline_config() -> Optional[Dict[str, Any]]:
    """加载项目流水线配置"""
    config_file = Path.cwd() / ".pipeline.json"
    if config_file.exists():
        with open(config_file) as f:
            return json.load(f)
    return None


def api_request(config: Dict[str, str], method: str, path: str, data: Optional[Dict] = None) -> Any:
    """发送 API 请求"""
    url = f"https://{config['domain']}/oapi/v1/flow/organizations/{ORGANIZATION_ID}{path}"

    headers = {
        "Content-Type": "application/json",
        "x-yunxiao-token": config["token"]
    }

    req_data = None
    if data:
        req_data = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            if body:
                return json.loads(body)
            return {"status": response.status}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"❌ API 请求失败: {e.code}")
        print(f"错误信息: {error_body}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"❌ 网络错误: {e.reason}")
        sys.exit(1)


def cmd_list(config: Dict[str, str]) -> List[Dict[str, Any]]:
    """获取流水线列表"""
    result = api_request(config, "GET", "/pipelines?perPage=30")

    # JSON 输出模式
    if JSON_OUTPUT:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    print("\n📋 可用流水线列表:\n")
    print(f"{'ID':<12} {'名称':<30} {'创建时间':<20}")
    print("-" * 65)

    for p in result:
        create_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(p.get("createTime", 0) / 1000))
        pipeline_id = p.get("pipelineId", "-")
        pipeline_name = p.get("pipelineName", "-")
        print(f"{pipeline_id:<12} {pipeline_name:<30} {create_time:<20}")

    print()

    # 交互式保存配置（仅在交互模式下）
    if is_interactive():
        pipeline_config = load_pipeline_config()
        if not pipeline_config:
            print("💡 当前项目未配置流水线，是否选择要关联的流水线？")
            try:
                choice = input("输入流水线 ID（多个用逗号分隔，回车跳过）: ").strip()
                if choice:
                    selected_ids = [x.strip() for x in choice.split(",")]
                    selected_pipelines = [p for p in result if str(p.get("pipelineId", "")) in selected_ids]

                    if selected_pipelines:
                        config_data = {
                            "organizationId": ORGANIZATION_ID,
                            "pipelines": [
                                {
                                    "pipelineId": str(p.get("pipelineId", "")),
                                    "pipelineName": p.get("pipelineName", "")
                                }
                                for p in selected_pipelines
                            ]
                        }

                        with open(".pipeline.json", "w") as f:
                            json.dump(config_data, f, indent=2, ensure_ascii=False)

                        print(f"\n✅ 已保存 {len(selected_pipelines)} 个流水线配置到 .pipeline.json")
            except EOFError:
                pass  # 非交互模式，跳过

    return result


def cmd_run(config: Dict[str, str], pipeline_ids: List[str]) -> None:
    """运行流水线"""
    for pipeline_id in pipeline_ids:
        print(f"\n🚀 正在触发流水线 {pipeline_id}...")

        # 运行流水线不需要额外参数时，body 为空
        result = api_request(config, "POST", f"/pipelines/{pipeline_id}/runs", data={})

        run_id = result if isinstance(result, int) else result.get("runId", "unknown")

        print(f"✅ 流水线 {pipeline_id} 触发成功")
        print(f"   运行 ID: {run_id}")
        print(f"   查看详情: https://flow.aliyun.com/pipelines/{pipeline_id}/builds/{run_id}")


def cmd_status(config: Dict[str, str], pipeline_id: str) -> None:
    """查看流水线状态"""
    result = api_request(config, "GET", f"/pipelines/{pipeline_id}/runs?perPage=5")

    print(f"\n📊 流水线 {pipeline_id} 最近运行记录:\n")
    print(f"{'运行ID':<10} {'状态':<15} {'触发时间':<20}")
    print("-" * 50)

    runs = result if isinstance(result, list) else []
    for run in runs[:5]:
        trigger_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(run.get("createTime", 0) / 1000))
        status = run.get("status", "unknown")
        run_id = run.get("runId", "-")
        print(f"{run_id:<10} {status:<15} {trigger_time:<20}")


def cmd_latest(config: Dict[str, str], pipeline_id: str) -> Dict[str, Any]:
    """获取最近一次流水线运行状态"""
    result = api_request(config, "GET", f"/pipelines/{pipeline_id}/runs/latestPipelineRun")

    if JSON_OUTPUT:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    status = result.get("status", "unknown")
    pipeline_run_id = result.get("pipelineRunId", "-")
    trigger_mode = result.get("triggerMode", 0)
    create_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(result.get("createTime", 0) / 1000))

    # 触发模式映射
    trigger_modes = {1: "人工触发", 2: "定时触发", 3: "代码提交触发", 5: "流水线触发", 6: "WEBHOOK 触发"}
    trigger_str = trigger_modes.get(trigger_mode, f"未知({trigger_mode})")

    # 状态颜色映射
    status_icons = {
        "SUCCESS": "✅",
        "FAIL": "❌",
        "RUNNING": "🔄",
        "WAITING": "⏳",
        "CANCELED": "⚪"
    }
    icon = status_icons.get(status, "❓")

    print(f"\n{icon} 流水线 {pipeline_id} 最新运行状态:\n")
    print(f"  运行 ID: {pipeline_run_id}")
    print(f"  状态: {status}")
    print(f"  触发方式: {trigger_str}")
    print(f"  触发时间: {create_time}")

    # 显示阶段信息
    stages = result.get("stages", [])
    if stages:
        print(f"\n  📋 阶段详情:")
        for stage in stages:
            stage_name = stage.get("name", "-")
            stage_status = stage.get("status", "unknown")
            stage_icon = status_icons.get(stage_status, "❓")
            print(f"     {stage_icon} {stage_name}: {stage_status}")

    print(f"\n  🔗 查看详情: https://flow.aliyun.com/pipelines/{pipeline_id}/builds/{pipeline_run_id}\n")

    return result


def cmd_interactive_run(config: Dict[str, str]) -> None:
    """交互式选择并运行流水线"""
    pipeline_config = load_pipeline_config()

    if pipeline_config and "pipelines" in pipeline_config:
        pipelines = pipeline_config["pipelines"]
        print("\n📦 已配置的流水线:\n")
        for i, p in enumerate(pipelines, 1):
            name = p.get("pipelineName", "-")
            pid = p.get("pipelineId", "-")
            print(f"  {i}. {name} (ID: {pid})")
        print()

        choice = input("选择要运行的流水线（输入序号或ID，多个用逗号分隔）: ").strip()

        if not choice:
            print("已取消")
            return

        # 解析选择
        selected_ids: List[str] = []
        for item in choice.split(","):
            item = item.strip()
            if item.isdigit():
                idx = int(item) - 1
                if 0 <= idx < len(pipelines):
                    pid = pipelines[idx].get("pipelineId", "")
                    if pid:
                        selected_ids.append(pid)
                else:
                    selected_ids.append(item)
            else:
                selected_ids.append(item)

        if selected_ids:
            cmd_run(config, selected_ids)
    else:
        # 没有配置，先获取列表
        print("当前项目未配置流水线，正在获取可用流水线...")
        cmd_list(config)


def cmd_save(config: Dict[str, str], pipeline_ids: List[str]) -> None:
    """保存流水线到配置文件"""
    # 获取所有流水线
    result = api_request(config, "GET", "/pipelines?perPage=30")

    selected_pipelines = [p for p in result if str(p.get("pipelineId", "")) in pipeline_ids]

    if not selected_pipelines:
        print(f"❌ 未找到匹配的流水线: {pipeline_ids}")
        sys.exit(1)

    # 读取现有配置
    existing_config = load_pipeline_config() or {"organizationId": ORGANIZATION_ID, "pipelines": []}
    existing_ids = {p.get("pipelineId") for p in existing_config.get("pipelines", [])}

    # 添加新流水线（去重）
    for p in selected_pipelines:
        pid = str(p.get("pipelineId", ""))
        if pid not in existing_ids:
            existing_config["pipelines"].append({
                "pipelineId": pid,
                "pipelineName": p.get("pipelineName", "")
            })

    with open(".pipeline.json", "w") as f:
        json.dump(existing_config, f, indent=2, ensure_ascii=False)

    print(f"✅ 已保存 {len(selected_pipelines)} 个流水线配置到 .pipeline.json")


def main() -> None:
    global JSON_OUTPUT, NON_INTERACTIVE

    # 解析参数
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    JSON_OUTPUT = "--json" in flags
    NON_INTERACTIVE = "--non-interactive" in flags or not sys.stdin.isatty()

    if not args:
        print(__doc__)
        print("\n示例:")
        print("  python3 pipeline_api.py list")
        print("  python3 pipeline_api.py list --json")
        print("  python3 pipeline_api.py run 123")
        print("  python3 pipeline_api.py status 123")
        print("\n选项:")
        print("  --json            JSON 格式输出")
        print("  --non-interactive 非交互模式")
        sys.exit(1)

    config = load_config()
    command = args[0]

    if command == "list":
        cmd_list(config)
    elif command == "run":
        if len(args) < 2:
            # 没有指定流水线，进入交互模式
            if is_interactive():
                cmd_interactive_run(config)
            else:
                print("❌ 非交互模式下需要指定流水线 ID")
                sys.exit(1)
        else:
            cmd_run(config, args[1:])
    elif command == "status":
        if len(args) < 2:
            print("❌ 请指定流水线 ID")
            sys.exit(1)
        cmd_status(config, args[1])
    elif command == "latest":
        # 获取最近一次运行状态
        if len(args) < 2:
            print("❌ 请指定流水线 ID")
            sys.exit(1)
        cmd_latest(config, args[1])
    elif command == "save":
        # 保存指定流水线到配置
        if len(args) < 2:
            print("❌ 请指定流水线 ID")
            sys.exit(1)
        cmd_save(config, args[1:])
    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
