"""cut.cli — cut-cli 命令行入口。

agent 通过 shell 调用本模块完成所有剪辑操作。
设计原则：
- 每个命令都支持 --json 输出（适合 agent 解析）
- --backend jianying|capcut|premiere
- --dry-run 仅打印将要做的操作，不实际执行
- 出错返回非零退出码，stderr 输出错误信息

用法：
    python -m cut.cli detect
    python -m cut.cli get-state --backend jianying --project my_vlog
    python -m cut.cli import --backend jianying --project my_vlog --type video --path /path/to.mp4
    python -m cut.cli split --backend jianying --project my_vlog --track 0 --at 00:00:05.000
    python -m cut.cli add-text --backend jianying --project my_vlog --content "Hello" --start 0 --duration 3000000
    python -m cut.cli export --backend jianying --project my_vlog --output out.mp4 --method ffmpeg
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, List

from . import platform as P
from . import context


def _print_json(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _parse_time(s):
    """时间参数支持：纯数字（微秒）、HH:MM:SS.mmm、整数+s/ms 后缀。"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    s = str(s).strip()
    if s.endswith("s") and not s.endswith("ms"):
        return int(float(s[:-1]) * 1_000_000)
    if s.endswith("ms"):
        return int(float(s[:-2]) * 1000)
    if s.endswith("us"):
        return int(s[:-2])
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 3:
            h, m, sec = parts
            return int(float(h) * 3_600_000_000 + float(m) * 60_000_000 + float(sec) * 1_000_000)
        elif len(parts) == 2:
            m, sec = parts
            return int(float(m) * 60_000_000 + float(sec) * 1_000_000)
    return int(float(s))


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------

def cmd_detect(args):
    info = P.detect()
    if args.json:
        _print_json(info.to_dict())
    else:
        print(f"OS:         {info.os} {info.os_version}")
        print(f"Python:     {info.python_version}")
        print(f"剪映:        {'✓' if info.jianying.installed else '✗'} v{info.jianying.version or '?'}")
        if info.jianying.drafts_dir:
            print(f"  drafts:   {info.jianying.drafts_dir}")
        print(f"CapCut:     {'✓' if info.capcut.installed else '✗'} v{info.capcut.version or '?'}")
        print(f"Premiere:   {'✓' if info.premiere.installed else '✗'} v{info.premiere.version or '?'}"
              + (" (running)" if info.premiere.running else ""))


def cmd_list_drafts(args):
    drafts = P.list_drafts(app=args.app)
    if args.json:
        _print_json(drafts)
    else:
        for d in drafts:
            print(f"{d['name']:30s}  {d.get('duration_hms', '?')}  v{d.get('version', '?')}")


def cmd_get_state(args):
    state = context.get_project_state(
        backend=args.backend,
        project_name=args.project,
        project_dir=args.dir,
    )
    _print_json(state)


def cmd_list_materials(args):
    ms = context.list_materials(
        backend=args.backend,
        project_name=args.project,
        project_dir=args.dir,
        mtype=args.type,
    )
    _print_json(ms)


def cmd_get_timeline(args):
    tl = context.get_timeline(
        backend=args.backend,
        project_name=args.project,
        project_dir=args.dir,
    )
    _print_json(tl)


def cmd_import(args):
    if args.backend in ("jianying", "capcut"):
        from .jianying.draft import Draft
        from .jianying import materials as M
        draft = Draft.open(project_name=args.project, project_dir=args.dir, app=args.backend)
        if args.type == "video":
            mid = M.import_video(draft, args.path, alias=args.alias)
        elif args.type == "audio":
            mid = M.import_audio(draft, args.path, alias=args.alias)
        elif args.type == "image":
            mid = M.import_image(draft, args.path, alias=args.alias, duration_us=_parse_time(args.duration) or 5_000_000)
        else:
            print(f"未知 type: {args.type}", file=sys.stderr)
            sys.exit(1)
        if not args.dry_run:
            draft.save()
        _print_json({"success": True, "material_id": mid, "saved": not args.dry_run})
    elif args.backend == "premiere":
        from .premiere import materials as M
        result = M.import_file(args.path, alias=args.alias, bin_name=args.bin)
        _print_json(result)
    else:
        print(f"未知 backend: {args.backend}", file=sys.stderr)
        sys.exit(1)


def cmd_add_segment(args):
    """把素材加到时间轴（剪映专用，Premiere 用 import --add-to-timeline）。"""
    if args.backend not in ("jianying", "capcut"):
        print("add-segment 仅支持剪映后端", file=sys.stderr)
        sys.exit(1)
    from .jianying.draft import Draft
    from .jianying import materials as M
    draft = Draft.open(project_name=args.project, project_dir=args.dir, app=args.backend)
    start = _parse_time(args.start) or 0
    dur = _parse_time(args.duration) if args.duration else None
    if args.track_type == "video":
        sid = M.add_video_segment(draft, args.material_id, track_id=args.track,
                                   start_us=start, source_in_us=_parse_time(args.source_in) or 0,
                                   duration_us=dur)
    else:
        sid = M.add_audio_segment(draft, args.material_id, track_id=args.track,
                                   start_us=start, source_in_us=_parse_time(args.source_in) or 0,
                                   duration_us=dur, volume=args.volume)
    if not args.dry_run:
        draft.save()
    _print_json({"success": True, "segment_id": sid, "saved": not args.dry_run})


def cmd_split(args):
    if args.backend in ("jianying", "capcut"):
        from .jianying.draft import Draft
        from .jianying import segments as S
        draft = Draft.open(project_name=args.project, project_dir=args.dir, app=args.backend)
        track = draft.all_tracks()[args.track]
        at = _parse_time(args.at)
        # 找到跨过 at 的 segment
        results = []
        for seg in track.segments:
            if seg.start_us < at < seg.end_us:
                left, right = S.split_segment(draft, seg, at)
                results.append({"left": left, "right": right})
        if not args.dry_run:
            draft.save()
        _print_json({"success": True, "splits": results, "saved": not args.dry_run})
    elif args.backend == "premiere":
        from .premiere import timeline as T
        if args.clip is None:
            print("Premiere 后端必须提供 --clip 参数", file=sys.stderr)
            sys.exit(1)
        result = T.split_clip(args.track, "video" if args.track_type == "video" else "audio",
                              args.clip, _parse_time(args.at))
        _print_json(result)


def cmd_trim(args):
    if args.backend in ("jianying", "capcut"):
        from .jianying.draft import Draft
        from .jianying import segments as S
        draft = Draft.open(project_name=args.project, project_dir=args.dir, app=args.backend)
        track = draft.all_tracks()[args.track]
        if args.clip >= len(track.segments):
            print(f"clip index {args.clip} 越界", file=sys.stderr)
            sys.exit(1)
        seg = track.segments[args.clip]
        new_start = _parse_time(args.new_start) if args.new_start else None
        new_end = _parse_time(args.new_end) if args.new_end else None
        S.trim_segment(draft, seg, new_start_us=new_start, new_end_us=new_end)
        if not args.dry_run:
            draft.save()
        _print_json({"success": True, "saved": not args.dry_run})
    elif args.backend == "premiere":
        from .premiere import timeline as T
        result = T.trim_clip(args.track, "video" if args.track_type == "video" else "audio",
                             args.clip,
                             _parse_time(args.new_start) if args.new_start else None,
                             _parse_time(args.new_end) if args.new_end else None)
        _print_json(result)


def cmd_add_text(args):
    if args.backend in ("jianying", "capcut"):
        from .jianying.draft import Draft
        from .jianying import text as TX
        draft = Draft.open(project_name=args.project, project_dir=args.dir, app=args.backend)
        start = _parse_time(args.start)
        dur = _parse_time(args.duration) if args.duration else 3_000_000
        sid = TX.add_text(draft, args.content, start, dur,
                          preset=args.preset, style_overrides=json.loads(args.style) if args.style else None)
        if not args.dry_run:
            draft.save()
        _print_json({"success": True, "segment_id": sid, "saved": not args.dry_run})
    elif args.backend == "premiere":
        from .premiere import text as TX
        start = _parse_time(args.start)
        dur = _parse_time(args.duration) if args.duration else 3_000_000
        result = TX.add_text(args.content, start, dur)
        _print_json(result)


def cmd_add_transition(args):
    if args.backend in ("jianying", "capcut"):
        from .jianying.draft import Draft
        from .jianying import effects as E
        draft = Draft.open(project_name=args.project, project_dir=args.dir, app=args.backend)
        track = draft.all_tracks()[args.track]
        if args.clip + 1 >= len(track.segments):
            print(f"clip index {args.clip} 后没有更多片段", file=sys.stderr)
            sys.exit(1)
        tid = E.add_transition_simple(draft, track.id, args.clip, preset=args.preset,
                                       duration_us=_parse_time(args.duration) or 500_000)
        if not args.dry_run:
            draft.save()
        _print_json({"success": True, "transition_id": tid, "saved": not args.dry_run})
    elif args.backend == "premiere":
        from .premiere import effects as E
        result = E.add_transition(args.track, args.clip, args.preset,
                                  _parse_time(args.duration) or 500_000)
        _print_json(result)


def cmd_add_effect(args):
    if args.backend in ("jianying", "capcut"):
        from .jianying.draft import Draft
        from .jianying import effects as E
        draft = Draft.open(project_name=args.project, project_dir=args.dir, app=args.backend)
        track = draft.all_tracks()[args.track]
        seg = track.segments[args.clip]
        sid = E.add_video_effect(draft, seg.id, preset=args.preset, intensity=args.intensity)
        if not args.dry_run:
            draft.save()
        _print_json({"success": True, "effect_segment_id": sid, "saved": not args.dry_run})
    elif args.backend == "premiere":
        from .premiere import effects as E
        result = E.add_video_effect(args.track, args.clip, args.preset)
        _print_json(result)


def cmd_set_audio(args):
    if args.backend in ("jianying", "capcut"):
        from .jianying.draft import Draft
        from .jianying import audio as A
        draft = Draft.open(project_name=args.project, project_dir=args.dir, app=args.backend)
        track = draft.all_tracks()[args.track]
        seg = track.segments[args.clip]
        if args.action == "volume":
            A.set_volume(draft, seg.id, args.value)
        elif args.action == "fade_in":
            A.add_audio_fade_in(draft, seg.id, _parse_time(args.duration) or 500_000)
        elif args.action == "fade_out":
            A.add_audio_fade_out(draft, seg.id, _parse_time(args.duration) or 500_000)
        elif args.action == "effect":
            A.apply_audio_effect(draft, seg.id, preset=args.preset)
        else:
            print(f"未知 action: {args.action}", file=sys.stderr)
            sys.exit(1)
        if not args.dry_run:
            draft.save()
        _print_json({"success": True, "saved": not args.dry_run})
    elif args.backend == "premiere":
        from .premiere import audio as A
        if args.action == "volume":
            result = A.set_volume(args.track, args.clip, args.value)
        elif args.action == "fade_in":
            result = A.add_fade_in(args.track, args.clip, _parse_time(args.duration) or 500_000)
        elif args.action == "fade_out":
            result = A.add_fade_out(args.track, args.clip, _parse_time(args.duration) or 500_000)
        elif args.action == "effect":
            result = A.apply_audio_effect(args.track, args.clip, args.preset)
        else:
            print(f"未知 action: {args.action}", file=sys.stderr)
            sys.exit(1)
        _print_json(result)


def cmd_export(args):
    if args.backend in ("jianying", "capcut"):
        from .jianying.draft import Draft
        from .jianying import export as E
        draft = Draft.open(project_name=args.project, project_dir=args.dir, app=args.backend)
        result = E.export(draft, args.output, method=args.method)
        _print_json(result)
    elif args.backend == "premiere":
        from .premiere import export as E
        result = E.export_to_file(args.output, preset=args.preset)
        _print_json(result)


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="cut-cli",
        description="统一视频剪辑操控 CLI（剪映 + Premiere）",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # detect
    sp = sub.add_parser("detect", help="检测本机环境与可用后端")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_detect)

    # list-drafts
    sp = sub.add_parser("list-drafts", help="列出剪映项目")
    sp.add_argument("--app", default="jianying", choices=["jianying", "capcut"])
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_list_drafts)

    # get-state
    sp = sub.add_parser("get-state", help="读取项目状态")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    sp.add_argument("--project", help="剪映项目名")
    sp.add_argument("--dir", help="剪映项目目录绝对路径")
    sp.set_defaults(func=cmd_get_state)

    # list-materials
    sp = sub.add_parser("list-materials", help="列出素材池")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    sp.add_argument("--project")
    sp.add_argument("--dir")
    sp.add_argument("--type", choices=["video", "audio", "image", "sticker", "text", "effect"])
    sp.set_defaults(func=cmd_list_materials)

    # get-timeline
    sp = sub.add_parser("get-timeline", help="读取时间轴")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    sp.add_argument("--project")
    sp.add_argument("--dir")
    sp.set_defaults(func=cmd_get_timeline)

    # import
    sp = sub.add_parser("import", help="导入素材")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    sp.add_argument("--project")
    sp.add_argument("--dir")
    sp.add_argument("--type", required=True, choices=["video", "audio", "image"])
    sp.add_argument("--path", required=True)
    sp.add_argument("--alias")
    sp.add_argument("--bin", help="Premiere 项目面板 bin 名")
    sp.add_argument("--duration", default="5000000", help="图片时长（仅剪映）")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_import)

    # add-segment
    sp = sub.add_parser("add-segment", help="把素材加到时间轴")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut"])
    sp.add_argument("--project")
    sp.add_argument("--dir")
    sp.add_argument("--material-id", required=True)
    sp.add_argument("--track-type", default="video", choices=["video", "audio"])
    sp.add_argument("--track", help="track ID（不指定则自动）")
    sp.add_argument("--start", default="0")
    sp.add_argument("--source-in", default="0")
    sp.add_argument("--duration")
    sp.add_argument("--volume", type=float, default=1.0)
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_add_segment)

    # split
    sp = sub.add_parser("split", help="切分片段")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    sp.add_argument("--project")
    sp.add_argument("--dir")
    sp.add_argument("--track-type", default="video", choices=["video", "audio"])
    sp.add_argument("--track", type=int, required=True, help="轨道索引（0 = 最上）")
    sp.add_argument("--clip", type=int, help="clip 索引（Premiere 必填）")
    sp.add_argument("--at", required=True, help="切点时间")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_split)

    # trim
    sp = sub.add_parser("trim", help="调整片段入点/出点")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    sp.add_argument("--project")
    sp.add_argument("--dir")
    sp.add_argument("--track-type", default="video", choices=["video", "audio"])
    sp.add_argument("--track", type=int, required=True)
    sp.add_argument("--clip", type=int, required=True)
    sp.add_argument("--new-start", help="新入点（时间轴坐标）")
    sp.add_argument("--new-end", help="新出点（时间轴坐标）")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_trim)

    # add-text
    sp = sub.add_parser("add-text", help="添加文字")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    sp.add_argument("--project")
    sp.add_argument("--dir")
    sp.add_argument("--content", required=True)
    sp.add_argument("--start", required=True)
    sp.add_argument("--duration", default="3000000")
    sp.add_argument("--preset", default="subtitle", choices=["subtitle", "title"])
    sp.add_argument("--style", help='JSON 字符串，如 \'{"text_color":"#FF0000"}\'')
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_add_text)

    # add-transition
    sp = sub.add_parser("add-transition", help="添加转场")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    sp.add_argument("--project")
    sp.add_argument("--dir")
    sp.add_argument("--track", type=int, required=True, help="轨道索引")
    sp.add_argument("--clip", type=int, required=True, help="在该 clip 与下个 clip 之间加")
    sp.add_argument("--preset", default="fade")
    sp.add_argument("--duration", default="500000")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_add_transition)

    # add-effect
    sp = sub.add_parser("add-effect", help="添加特效")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    sp.add_argument("--project")
    sp.add_argument("--dir")
    sp.add_argument("--track", type=int, required=True)
    sp.add_argument("--clip", type=int, required=True)
    sp.add_argument("--preset", default="vignette")
    sp.add_argument("--intensity", type=float, default=1.0)
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_add_effect)

    # set-audio
    sp = sub.add_parser("set-audio", help="音频操作")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    sp.add_argument("--project")
    sp.add_argument("--dir")
    sp.add_argument("--track", type=int, required=True)
    sp.add_argument("--clip", type=int, required=True)
    sp.add_argument("--action", required=True, choices=["volume", "fade_in", "fade_out", "effect"])
    sp.add_argument("--value", type=float, help="volume (0-1+)")
    sp.add_argument("--preset", help="effect preset name")
    sp.add_argument("--duration", default="500000")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_set_audio)

    # export
    sp = sub.add_parser("export", help="导出渲染")
    sp.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    sp.add_argument("--project")
    sp.add_argument("--dir")
    sp.add_argument("--output", required=True)
    sp.add_argument("--method", default="ffmpeg", choices=["ui", "ffmpeg"], help="剪映专用")
    sp.add_argument("--preset", default="h264_1080p", help="Premiere 预设")
    sp.set_defaults(func=cmd_export)

    return p


def main(argv: Optional[List[str]] = None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
