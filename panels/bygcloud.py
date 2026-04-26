import re
import requests
from .base import BasePanel


class Bygcloud(BasePanel):
    """白月光 (bygcloud.com) 面板实现 — htmx SSR，Cookie 认证"""

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
            "Origin": self.base_url,
        })

    def login(self) -> bool:
        if not self.email or not self.password:
            print(f"[{self.name}] 没有配置邮箱密码")
            return False

        try:
            # 先访问首页获取 session cookie
            self.session.get(self.base_url + "/", timeout=15)

            # 登录 (form-urlencoded，成功返回 302 重定向到 /)
            resp = self.session.post(
                self.base_url + "/login",
                data={"email": self.email, "password": self.password},
                allow_redirects=False,
                timeout=15,
            )
            if resp.status_code in (302, 303) and "/login" not in resp.headers.get("Location", ""):
                return True
            print(f"[{self.name}] 登录失败")
            return False
        except Exception as e:
            print(f"[{self.name}] 登录异常: {e}")
            return False

    def checkin(self) -> str:
        # 该面板没有签到功能
        return ""

    def get_user_info(self) -> dict:
        result = {}
        try:
            # 从仪表盘 HTML 提取用户数据
            resp = self.session.get(self.base_url + "/", timeout=15)
            self._parse_dashboard(result, resp.text)
        except Exception as e:
            print(f"[{self.name}] 获取用户信息失败: {e}")

        # 从邀请页面提取邀请和佣金数据
        self._fill_invite_info(result)

        # 从 /api/sub/info 获取流量数据
        self._fill_traffic_info(result)

        return result

    def _parse_dashboard(self, result: dict, html: str):
        """从仪表盘 HTML 中解析嵌入的 JSON 用户数据"""
        # 余额（单位：分）
        m = re.search(r'"balance"\s*:\s*(\d+)', html)
        if m:
            result["余额"] = "¥{:.2f}".format(int(m.group(1)) / 100)

        # 到期时间
        m = re.search(r'"expired_at"\s*:\s*(\d+)', html)
        if m:
            expired_at = int(m.group(1))
            if expired_at > 0:
                from datetime import datetime
                result["到期时间"] = datetime.fromtimestamp(expired_at).strftime("%Y-%m-%d")
            else:
                result["到期时间"] = "无限期"

    def _fill_invite_info(self, result: dict):
        """从邀请页面 HTML 提取邀请和佣金数据"""
        try:
            resp = self.session.get(self.base_url + "/invite", timeout=15)
            html = resp.text

            # 邀请人数: <div ...>48</div><div ...>邀请人数</div>
            m = re.search(r'>(\d+)</div>\s*<div[^>]*>邀请人数</div>', html)
            if m:
                result["已注册人数"] = m.group(1)

            # 累计佣金: <div ...>¥759.66</div><div ...>累计佣金</div>
            m = re.search(r'>¥([\d.]+)</div>\s*<div[^>]*>累计佣金</div>', html)
            if m:
                result["累计佣金"] = "¥{}".format(m.group(1))

            # 可提现佣金: <div ...>¥119.66</div><div ...>可提现佣金</div>
            m = re.search(r'>¥([\d.]+)</div>\s*<div[^>]*>可提现佣金</div>', html)
            if m:
                result["可提现佣金"] = "¥{}".format(m.group(1))

            # 佣金比例: 佣金比例 <span ...>20%</span>
            m = re.search(r'佣金比例\s*<span[^>]*>(\d+)%</span>', html)
            if m:
                result["佣金比例"] = "{}%".format(m.group(1))
        except Exception:
            pass

    def _fill_traffic_info(self, result: dict):
        """从 /api/sub/info 获取流量数据"""
        try:
            resp = self.session.get(self.base_url + "/api/sub/info", timeout=15)
            data = resp.json().get("data", {})
            u = data.get("u", 0)
            d = data.get("d", 0)
            transfer_enable = data.get("transfer_enable", 0)
            used = u + d

            if transfer_enable > 0:
                from utils import format_bytes
                pct = used / transfer_enable * 100
                result["已用流量"] = "{:.1f}% ({} / {})".format(pct, format_bytes(used), format_bytes(transfer_enable))
            else:
                result["已用流量"] = "无限制"
        except Exception:
            pass
