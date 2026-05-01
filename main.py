#!/usr/bin/env python3
import argparse
import json
import sys
import os

from panels import get_panel
from notify import send_qywx


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if not os.path.exists(config_path):
        print("配置文件不存在，请根据 config-template.json 创建 config.json")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run():
    parser = argparse.ArgumentParser(description="机场签到工具")
    parser.add_argument("--name", help="只执行指定名称的机场（支持逗号分隔多个）")
    args = parser.parse_args()

    cfg = load_config()
    accounts = cfg.get("accounts", [])
    notify_cfg = cfg.get("notify", {})

    if not accounts:
        print("没有配置任何账户")
        return

    if args.name:
        names = [n.strip() for n in args.name.split(",")]
        accounts = [a for a in accounts if a.get("name") in names]
        if not accounts:
            print(f"未找到匹配的机场: {names}")
            return

    qywx_key = notify_cfg.get("qywx_key") if notify_cfg.get("enabled") else None

    for account in accounts:
        name = account.get("name", "未命名")
        print(f"正在请求: {name} ...")
        try:
            panel_cls = get_panel(account.get("panel", "v2board"))
            panel = panel_cls(account)
            result = panel.run()
        except Exception as e:
            result = f"【{name}】\n  执行异常: {e}"
        print(result)
        print()

        if qywx_key:
            send_qywx(qywx_key, result)


if __name__ == "__main__":
    run()
