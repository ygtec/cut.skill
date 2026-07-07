# Qwen Code 入口

Qwen Code（阿里通义）通过 `~/.qwen/skills.json` 加载 skill。

## 配置

### 方式 1：Skill

```json
{
  "skills": [
    {
      "name": "cut",
      "path": "/path/to/cut",
      "description": "视频剪辑操控（剪映 + Premiere）",
      "triggers": [
        "剪映", "CapCut", "JianYing", "Premiere", "Pr",
        "视频剪辑", "时间轴", "轨道", "片段",
        "字幕", "转场", "特效", "调色", "混音",
        "渲染导出", "vlog", "教学视频"
      ],
      "entry": "SKILL.md"
    }
  ]
}
```

### 方式 2：MCP Server

```json
{
  "mcp_servers": {
    "cut": {
      "command": "python",
      "args": ["-m", "cut.mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/cut/skill/scripts"
      }
    }
  }
}
```

## 使用

Qwen Code 会根据 triggers 自动触发。对话中：

```
> 检测一下我电脑上有什么视频剪辑软件
> 帮我在剪映里给视频加字幕
> 让 Premiere 把这几个素材按顺序排到时间轴上
```

## 调用方式

### CLI（推荐）

```bash
python -m cut.cli detect
python -m cut.cli get-state --backend jianying --project my_vlog
python -m cut.cli add-text --backend jianying --project my_vlog --content "你好" --start 0 --duration 3000000
```

### Python

```python
from cut.jianying.draft import Draft
from cut.jianying import text as TX

draft = Draft.open(project_name="my_vlog")
TX.add_subtitle(draft, "你好世界", start_us=0, duration_us=3_000_000)
draft.save()
```

## 关键规则

1. **修改前先 get_state**
2. **复杂操作用 --dry-run**
3. **告诉用户重启剪映**：draft 修改后需重新打开项目
4. **时间格式**：支持 `1500000` / `1.5s` / `1500ms` / `00:00:01.500`

## 完整文档

- 主文档：`SKILL.md`
- 剪映 draft schema：`references/jianying-draft-schema.md`
- 剪映操作详解：`references/jianying-operations.md`
- Premiere 操作详解：`references/premiere-operations.md`
- 上下文感知：`references/context-awareness.md`
- 跨平台：`references/cross-platform.md`
- 示例：`examples/*.py`
