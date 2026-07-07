"""cut.jianying — 剪映 draft 文件操控子包。

通过直接解析/编辑 draft_content.json 实现离线操控，
不需要剪映运行，修改后用户重开项目即可看到效果。

核心模块：
- draft: Draft 类，文件读写与三层结构解析
- materials: 素材导入
- segments: 片段裁切
- text: 字幕与文本
- effects: 转场与特效
- audio: 音频混音
- export: 导出（UI 自动化 / ffmpeg）
- state: 反向读取时间轴状态
"""
from .draft import Draft, Segment, Track, Material, TimeRange, DraftError, UnsupportedSchemaError
from . import materials, segments, text, effects, audio, export, state

__all__ = [
    "Draft", "Segment", "Track", "Material", "TimeRange",
    "DraftError", "UnsupportedSchemaError",
    "materials", "segments", "text", "effects", "audio", "export", "state",
]
