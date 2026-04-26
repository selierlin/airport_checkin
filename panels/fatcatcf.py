import re
import json
import requests
from datetime import datetime
from .base import BasePanel


class Fatcatcf(BasePanel):
    """肥猫云 (fatcatcf) 面板实现 — 自定义 SSR 面板，Cookie 认证"""

    def __init__(self, account: dict):
        super().__init__(account)
        self.session = requests.Session()
        if self._proxies():
            self.session.proxies.update(self._proxies())
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.base_url + "/",
        })

    def login(self) -> bool:
        if not self.email or not self.password:
            print(f"[{self.name}] 没有配置邮箱密码")
            return False

        try:
            resp = self.session.get(
                f"{self.base_url}/api/?action=login",
                params={"email": self.email, "password": self.password},
                timeout=15,
            )
            data = resp.json()
            if data.get("data"):
                return True
            print(f"[{self.name}] 登录失败: {data.get('message', '未知错误')}")
            return False
        except Exception as e:
            print(f"[{self.name}] 登录异常: {e}")
            return False

    def checkin(self) -> str:
        try:
            resp = self.session.get(
                f"{self.base_url}/skyapi",
                params={"action": "checkin"},
                timeout=15,
            )
            # 签到失败返回纯文本 "error"
            if resp.text.strip() == "error":
                return ""
            data = resp.json()
            if data.get("data"):
                flow = data.get("data", "")
                top = data.get("top", "")
                parts = []
                if top:
                    parts.append(f"排名#{top}")
                if flow:
                    parts.append(f"获得{flow}")
                return "，".join(parts) if parts else "签到成功"
            return data.get("message", "")
        except Exception:
            return ""

    def get_user_info(self) -> dict:
        result = {}
        try:
            resp = self.session.get(f"{self.base_url}/dashboard", timeout=15)
            html = resp.text
            self._parse_subinfo(result, html)
            self._parse_userinfo(result, html)
        except Exception as e:
            print(f"[{self.name}] 获取用户信息失败: {e}")

        self._fill_invite_info(result)
        return result

    def _parse_subinfo(self, result: dict, html: str):
        """从 dashboard HTML 中的 subinfo JS 变量提取流量和套餐数据"""
        m = re.search(r'var subinfo = ({.*?});', html)
        if not m:
            return
        try:
            sub = json.loads(m.group(1)).get("data", {})
        except (json.JSONDecodeError, AttributeError):
            return

        # 流量
        u = sub.get("u", 0)
        d = sub.get("d", 0)
        transfer_enable = sub.get("transfer_enable", 0)
        used = u + d
        if transfer_enable > 0:
            from utils import format_bytes
            pct = used / transfer_enable * 100
            result["已用流量"] = "{:.1f}% ({} / {})".format(pct, format_bytes(used), format_bytes(transfer_enable))
        else:
            result["已用流量"] = "无限制"

        # 套餐名
        plan = sub.get("plan")
        if plan and plan.get("name"):
            result["套餐"] = plan["name"]

        # 到期时间
        expired_at = sub.get("expired_at")
        if expired_at and expired_at > 0:
            result["到期时间"] = datetime.fromtimestamp(expired_at).strftime("%Y-%m-%d")
        else:
            result["到期时间"] = "无限期"

    def _parse_userinfo(self, result: dict, html: str):
        """从 dashboard HTML 中的 userinfo JS 变量提取余额数据"""
        m = re.search(r'var userinfo = ({.*?});', html)
        if not m:
            return
        try:
            user = json.loads(m.group(1)).get("data", {})
        except (json.JSONDecodeError, AttributeError):
            return

        # 余额（单位：分）
        result["余额"] = "¥{:.2f}".format(user.get("balance", 0) / 100)

        # 佣金余额（单位：分）
        result["佣金余额"] = "¥{:.2f}".format(user.get("commission_balance", 0) / 100)

    def _fill_invite_info(self, result: dict):
        """从 /inv 页面提取邀请和佣金数据"""
        try:
            resp = self.session.get(f"{self.base_url}/inv", timeout=15)
            html = resp.text
            # 去掉 script/style 标签后提取纯文本
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text)

            # 注册人数: "注册人数 261 成功邀请人数"
            m = re.search(r'注册人数\s+(\d+)', text)
            if m:
                result["已注册人数"] = m.group(1)

            # 总返利: "总返利 ¥458.96"
            m = re.search(r'总返利\s*¥([\d.]+)', text)
            if m:
                result["总返利"] = "¥{}".format(m.group(1))

            # 分红比例: "分红比例 10%"
            m = re.search(r'分红比例\s*(\d+)%', text)
            if m:
                result["分红比例"] = "{}%".format(m.group(1))
        except Exception:
            pass
