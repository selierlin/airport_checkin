#!/usr/bin/env python3
"""浏览器认证助手 — 手动通过 Cloudflare 验证并登录，自动抓取认证信息保存到 config.json

用法:
  python get_auth.py <网站地址> [名称]

示例:
  python get_auth.py https://www.example.com 魔戒
  python get_auth.py https://www.mojie.cyou

流程:
  1. 打开浏览器，用户手动通过 Cloudflare 验证 + 登录
  2. 脚本自动检测登录成功（监控登录 API 响应）
  3. 登录后等待 5 秒捕获更多 API 响应
  4. 自动保存认证信息到 config.json
"""

import json
import sys
import os
import time
from playwright.sync_api import sync_playwright


def main():
    if len(sys.argv) < 2:
        print("用法: python get_auth.py <网站地址> [名称]")
        print("示例: python get_auth.py https://www.example.com 魔戒")
        sys.exit(1)

    url = sys.argv[1].rstrip("/")
    name = sys.argv[2] if len(sys.argv) > 2 else ""

    # 读取 config.json
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)

    # 抓取结果
    captured = {
        "auth_token": "",
        "cf_clearance": "",
        "api_prefix": "",
        "login_response": {},
        "api_responses": {},
    }
    login_detected = False
    login_time = 0
    start_time = time.time()

    def handle_response(response):
        """拦截响应，抓取认证信息"""
        nonlocal login_detected, login_time
        req_url = response.url
        try:
            ct = response.headers.get("content-type", "")
            if "json" not in ct and "text/plain" not in ct:
                return
            body = response.json()
        except Exception:
            return

        # 捕获登录响应
        if "passport/auth/login" in req_url or "auth/login" in req_url:
            captured["login_response"] = body
            # 提取 API prefix
            for login_path in ["/passport/auth/login", "/auth/login"]:
                if login_path in req_url:
                    prefix = req_url.split(login_path)[0]
                    prefix = prefix.replace(url, "")
                    if not prefix:
                        prefix = "/api/v1"
                    captured["api_prefix"] = prefix
                    break
            # 提取 auth_token
            data = body.get("data")
            if data:
                login_detected = True
                login_time = time.time()
                if isinstance(data, dict):
                    captured["auth_token"] = data.get("auth_data", "")
                else:
                    captured["auth_token"] = str(data)
            print(f"\n[捕获] 登录响应: {json.dumps(body, ensure_ascii=False)[:200]}")

        # 捕获其他 API 响应
        for endpoint in ["user/info", "user/getSubscribe", "user/checkin",
                         "user/plan/fetch", "user/order/fetch", "user/invite/fetch",
                         "user/server/fetch", "user/comm/config"]:
            if endpoint in req_url:
                captured["api_responses"][endpoint] = body
                status = body.get("status", "")
                print(f"[捕获] {endpoint}: status={status}")

    print(f"正在打开浏览器访问: {url}")
    print()
    print("请在浏览器中完成:")
    print("  1. 通过 Cloudflare 人机验证")
    print("  2. 输入账号密码并登录")
    print()
    print("登录成功后脚本会自动检测并保存认证信息...")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.on("response", handle_response)

        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # 轮询等待登录成功
        print("等待登录中...")
        while True:
            time.sleep(1)
            # 检查 cookies
            for c in context.cookies():
                if c["name"] == "cf_clearance" and not captured["cf_clearance"]:
                    captured["cf_clearance"] = c["value"]
                    print(f"[捕获] cf_clearance: {c['value'][:20]}...")

            if login_detected:
                # 登录成功后再等 5 秒，让页面加载更多 API
                print("\n检测到登录成功，等待页面加载完成...")
                time.sleep(5)

                # 再次检查 cookies
                for c in context.cookies():
                    if c["name"] == "cf_clearance":
                        captured["cf_clearance"] = c["value"]

                # 从 localStorage 提取 token（备用）
                try:
                    local_storage = page.evaluate("""() => {
                        const data = {};
                        for (let i = 0; i < localStorage.length; i++) {
                            const key = localStorage.key(i);
                            if (key.toLowerCase().includes('token') || key.toLowerCase().includes('auth')) {
                                data[key] = localStorage.getItem(key);
                            }
                        }
                        return data;
                    }""")
                    if local_storage:
                        print(f"[捕获] localStorage: {json.dumps(local_storage, ensure_ascii=False)[:200]}")
                        for key, value in local_storage.items():
                            if not captured["auth_token"] and value:
                                captured["auth_token"] = value
                except Exception:
                    pass

                break

            # 超时 3 分钟
            if time.time() - start_time > 180 and not login_detected:
                # 超时前也检查一下 cookies
                for c in context.cookies():
                    if c["name"] == "cf_clearance":
                        captured["cf_clearance"] = c["value"]
                if captured["cf_clearance"]:
                    print("\n超时，但已捕获 cf_clearance，继续保存...")
                break

        browser.close()

    # 输出结果
    print("\n" + "=" * 50)
    print("捕获结果:")
    print(f"  api_prefix: {captured['api_prefix']}")
    if captured["auth_token"]:
        print(f"  auth_token: {captured['auth_token'][:50]}...")
    else:
        print("  auth_token: (未捕获)")
    if captured["cf_clearance"]:
        print(f"  cf_clearance: {captured['cf_clearance'][:30]}...")
    else:
        print("  cf_clearance: (未捕获)")
    print(f"  捕获到 {len(captured['api_responses'])} 个 API 响应")
    for ep, body in captured["api_responses"].items():
        print(f"    - {ep}: {json.dumps(body, ensure_ascii=False)[:100]}")

    # 保存
    if not captured["auth_token"] and not captured["cf_clearance"]:
        print("\n未捕获到任何认证信息，跳过保存")
        return

    account = {
        "name": name or url.split("//")[1].split("/")[0].split(".")[0],
        "panel": "v2board",
        "base_url": url,
        "email": "",
        "password": "",
        "auth_token": captured["auth_token"],
        "proxy": "http://127.0.0.1:7890",
    }
    if captured["api_prefix"]:
        account["api_prefix"] = captured["api_prefix"]
    if captured["cf_clearance"]:
        account["cf_clearance"] = captured["cf_clearance"]

    if "accounts" not in config:
        config["accounts"] = []
    config["accounts"].append(account)

    with open(config_path, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"\n已保存到 {config_path}")


if __name__ == "__main__":
    main()
