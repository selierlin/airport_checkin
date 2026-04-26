import re
import requests
from .base import BasePanel


class SSPanel(BasePanel):
    """SSPanel (Stisla) 面板实现 — Cookie 认证，HTML 页面解析"""

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
            # 先访问首页获取 PHPSESSID
            self.session.get(self.base_url + "/", timeout=15)

            # 登录（form-urlencoded，需要 X-Requested-With 头）
            resp = self.session.post(
                self.base_url + "/auth/login",
                data={"email": self.email, "passwd": self.password, "code": ""},
                headers={"X-Requested-With": "XMLHttpRequest"},
                timeout=15,
            )
            data = resp.json()
            if data.get("ret") == 1:
                return True
            else:
                print(f"[{self.name}] 登录失败: {data.get('msg', '未知错误')}")
                return False
        except Exception as e:
            print(f"[{self.name}] 登录异常: {e}")
            return False

    def checkin(self) -> str:
        try:
            resp = self.session.post(
                self.base_url + "/user/checkin",
                headers={"X-Requested-With": "XMLHttpRequest"},
                timeout=15,
            )
            data = resp.json()
            return data.get("msg", "")
        except Exception:
            return ""

    def get_user_info(self) -> dict:
        result = {}
        try:
            # 从 /user 页面 HTML 提取数据
            resp = self.session.get(self.base_url + "/user", timeout=15)
            html = resp.text
            self._parse_user_page(result, html)
        except Exception as e:
            print(f"[{self.name}] 获取用户信息失败: {e}")

        # 从 /user/invite 页面提取邀请数据
        try:
            resp = self.session.get(self.base_url + "/user/invite", timeout=15)
            self._parse_invite_page(result, resp.text)
        except Exception:
            pass

        return result

    def _parse_user_page(self, result: dict, html: str):
        """从 /user 页面 HTML 解析用户数据"""

        # 余额 — 搜索 "钱包余额" 后的 counter
        m = re.search(r'钱包余额.*?<span class="counter">([\d.]+)</span>', html, re.DOTALL)
        if m:
            result["余额"] = "¥{}".format(m.group(1))

        # 剩余流量
        m = re.search(r'剩余流量.*?<span class="counter">([\d.]+)</span>\s*(GB|TB|MB)', html, re.DOTALL)
        if m:
            result["剩余流量"] = "{} {}".format(m.group(1), m.group(2))

        # 会员时长 + 状态
        m = re.search(r'会员时长.*?<span class="counter">([\d.]+)</span>\s*天', html, re.DOTALL)
        if m:
            days = m.group(1)
            # 判断是否过期
            if "已过期" in html:
                result["会员状态"] = "已过期"
            else:
                result["会员时长"] = "{} 天".format(days)

        # 累计返利（在钱包余额卡片下方）
        m = re.search(r'累计获得返利金额:\s*¥([\d.]+)', html)
        if m:
            result["累计返利"] = "¥{}".format(m.group(1))

    def _parse_invite_page(self, result: dict, html: str):
        """从 /user/invite 页面 HTML 解析邀请数据"""

        # 返利额: "59.13 / 169.34 / 14131.12 元"
        m = re.search(r'<h3 class="mt-2">([\d.]+)\s*/\s*([\d.]+)\s*/\s*([\d.]+)\s*元</h3>', html)
        if m:
            result["本月返利"] = "¥{}".format(m.group(1))
            result["累计返利"] = "¥{}".format(m.group(3))

        # 注册用户: "2 / 33 / 1 / 25 位"
        m = re.search(r'<h3 class="mt-3">(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*位</h3>', html)
        if m:
            result["本月注册"] = "{} 人".format(m.group(2))

        # 返利比例: "30 %"
        m = re.search(r'<h3 class="mt-3">(\d+)\s*%</h3>', html)
        if m:
            result["返利比例"] = "{}%".format(m.group(1))
