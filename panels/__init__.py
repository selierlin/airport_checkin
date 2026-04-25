from .v2board import V2Board

PANEL_MAP = {
    "v2board": V2Board,
}


def get_panel(panel_type: str):
    cls = PANEL_MAP.get(panel_type)
    if not cls:
        raise ValueError(f"不支持的面板类型: {panel_type}，当前支持: {list(PANEL_MAP.keys())}")
    return cls
