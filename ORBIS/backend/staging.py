#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""待审数据暂存区（staging）。

独立于现有自动抓取/发布流程：抓取结果先落到暂存区，经管理员人工检查后
再「发布」覆盖正式数据文件。后续接入其他爬虫/接口时，只需把数据写进
暂存批次即可，审核与发布逻辑无需改动。

目录结构：
  data/staging/index.json          批次索引（按创建时间倒序）
  data/staging/<batch>/meta.json   批次元信息（来源、时间、状态、备注）
  data/staging/<batch>/<file>      待审数据文件（wb.json / fx.json / 任意扩展）
"""
import json
import os
import re
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
ROOT = os.path.dirname(HERE)
STAGE = os.path.join(DATA, "staging")
INDEX = os.path.join(STAGE, "index.json")
# 可发布到项目的数据文件白名单：暂存文件名 -> 正式文件绝对路径
PUBLISH_TARGETS = {
    "wb.json": os.path.join(DATA, "wb.json"),
    "fx.json": os.path.join(DATA, "fx.json"),
}


def _now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def _ensure():
    os.makedirs(STAGE, exist_ok=True)


def _read_index():
    _ensure()
    try:
        with open(INDEX, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _write_index(rows):
    _ensure()
    tmp = INDEX + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    os.replace(tmp, INDEX)


def _batch_dir(bid):
    # 防目录穿越：批次 id 只能是字母数字与下划线/短横线
    if not re.match(r"^[A-Za-z0-9_-]+$", bid or ""):
        return None
    return os.path.join(STAGE, bid)


def create(source="manual", note="", files=None):
    """新建待审批次。files: {文件名: 可JSON序列化对象} 或 {文件名: 磁盘路径}。

    返回 (ok, batch_info 或 error)。
    """
    _ensure()
    bid = "b" + datetime.now().strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]
    bdir = os.path.join(STAGE, bid)
    os.makedirs(bdir, exist_ok=False)
    saved = []
    try:
        for name, payload in (files or {}).items():
            if not re.match(r"^[\w.\-]+$", name):
                raise ValueError("非法文件名: %s" % name)
            dest = os.path.join(bdir, name)
            if isinstance(payload, str) and os.path.isfile(payload):
                shutil.copyfile(payload, dest)
            else:
                with open(dest, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
            saved.append(name)
        meta = {
            "id": bid, "source": source, "status": "pending",
            "created": _now(), "note": note, "files": saved,
        }
        with open(os.path.join(bdir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        rows = _read_index()
        rows.insert(0, {"id": bid, "source": source, "status": "pending",
                        "created": meta["created"], "note": note, "files": saved})
        _write_index(rows)
        return True, meta
    except Exception as e:  # noqa: BLE001
        shutil.rmtree(bdir, ignore_errors=True)
        return False, "创建暂存批次失败: %s" % e


def list_batches():
    rows = _read_index()
    out = []
    for r in rows:
        bdir = _batch_dir(r["id"])
        if not bdir or not os.path.isdir(bdir):
            continue
        item = dict(r)
        item["size"] = sum(
            os.path.getsize(os.path.join(bdir, f))
            for f in os.listdir(bdir) if os.path.isfile(os.path.join(bdir, f))
        )
        out.append(item)
    return out


def get_batch(bid):
    bdir = _batch_dir(bid)
    if not bdir or not os.path.isdir(bdir):
        return None
    try:
        with open(os.path.join(bdir, "meta.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    files = {}
    for name in meta.get("files", []):
        path = os.path.join(bdir, name)
        if not os.path.isfile(path):
            continue
        info = {"size": os.path.getsize(path), "name": name,
                "publishable": name in PUBLISH_TARGETS}
        # 对 JSON 文件做摘要，便于人工检查（不返回全量数据）
        if name.endswith(".json"):
            try:
                with open(path, encoding="utf-8") as f:
                    doc = json.load(f)
                info["summary"] = _summarize(name, doc)
            except (OSError, json.JSONDecodeError):
                info["summary"] = None
        files[name] = info
    meta["files_detail"] = files
    return meta


def _summarize(name, doc):
    """给不同数据文件生成人工检查用的摘要（后续接新数据源可在此扩展）。"""
    if not isinstance(doc, dict):
        return {"type": type(doc).__name__}
    if name == "wb.json":
        years = doc.get("years") or []
        return {
            "fetched_at": doc.get("fetched_at"),
            "source_updated": doc.get("source_updated"),
            "years": [years[0], years[-1]] if years else [],
            "countries": len(doc.get("countries") or {}),
            "events": len(doc.get("events") or []),
            "indicators": len(doc.get("indicators") or {}),
        }
    if name == "fx.json":
        return {
            "date": doc.get("date"), "updated": doc.get("updated"),
            "base": doc.get("base"), "source": doc.get("source"),
            "currencies": len(doc.get("currencies") or {}),
        }
    return {"keys": list(doc.keys())[:20]}


def preview(bid, name, limit=5):
    """返回某个待审 JSON 文件的内容预览（列表/字典截取前若干项），供人工检查。"""
    bdir = _batch_dir(bid)
    if not bdir or not re.match(r"^[\w.\-]+$", name or ""):
        return None
    path = os.path.join(bdir, name)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    limit = max(1, min(20, int(limit or 5)))
    out = {}
    for k, v in doc.items():
        if isinstance(v, list):
            out[k] = {"type": "list", "total": len(v), "sample": v[:limit]}
        elif isinstance(v, dict):
            keys = list(v.keys())[:limit]
            out[k] = {"type": "dict", "total": len(v),
                      "sample": {x: v[x] for x in keys}}
        else:
            out[k] = v
    return out


def compare(bid, name):
    """对比待审 JSON 与当前正式 JSON 的差异（摘要级），返回差异说明。"""
    bdir = _batch_dir(bid)
    if not bdir or name not in PUBLISH_TARGETS:
        return None
    new_path = os.path.join(bdir, name)
    old_path = PUBLISH_TARGETS[name]
    try:
        with open(new_path, encoding="utf-8") as f:
            new = json.load(f)
        with open(old_path, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    diffs = []
    for key in sorted(set(list(new.keys()) + list(old.keys()))):
        nv, ov = new.get(key), old.get(key)
        if isinstance(nv, dict) and isinstance(ov, dict):
            nk, ok = set(nv.keys()), set(ov.keys())
            added, removed = nk - ok, ok - nk
            if added:
                diffs.append({"field": key, "change": "新增 %d 项" % len(added),
                              "sample": sorted(added)[:8]})
            if removed:
                diffs.append({"field": key, "change": "减少 %d 项" % len(removed),
                              "sample": sorted(removed)[:8]})
            if not added and not removed:
                diffs.append({"field": key, "change": "条目数相同 (%d)" % len(nk)})
        elif nv != ov:
            diffs.append({"field": key, "change": "已更新",
                          "old": _short(ov), "new": _short(nv)})
        else:
            diffs.append({"field": key, "change": "无变化"})
    return {"file": name, "diffs": diffs}


def _short(v):
    s = str(v)
    return s[:160] + ("…" if len(s) > 160 else "")


def publish(bid, names=None, backup=True):
    """发布批次到正式数据文件。names 指定要发布的文件，默认全部可发布文件。

    发布前对旧文件做备份（data/backups/<bid>/），失败可回滚。
    """
    bdir = _batch_dir(bid)
    if not bdir or not os.path.isdir(bdir):
        return False, "批次不存在"
    try:
        with open(os.path.join(bdir, "meta.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False, "批次元信息损坏"
    if meta.get("status") == "published":
        return False, "该批次已发布过"
    names = [n for n in (names or meta.get("files") or []) if n in PUBLISH_TARGETS]
    if not names:
        return False, "批次内没有可发布的数据文件"
    done, backups = [], {}
    try:
        for name in names:
            src = os.path.join(bdir, name)
            if not os.path.isfile(src):
                raise FileNotFoundError(name)
            dst = PUBLISH_TARGETS[name]
            if backup and os.path.exists(dst):
                bdir_bak = os.path.join(DATA, "backups", bid)
                os.makedirs(bdir_bak, exist_ok=True)
                backups[name] = os.path.join(bdir_bak, name)
                shutil.copyfile(dst, backups[name])
            tmp = dst + ".tmp"
            shutil.copyfile(src, tmp)
            os.replace(tmp, dst)
            done.append(name)
    except Exception as e:  # noqa: BLE001
        # 回滚已发布的文件
        for name in done:
            dst = PUBLISH_TARGETS[name]
            bak = backups.get(name)
            if bak and os.path.exists(bak):
                shutil.copyfile(bak, dst)
        return False, "发布失败已回滚: %s" % e
    meta["status"] = "published"
    meta["published"] = _now()
    meta["published_files"] = done
    with open(os.path.join(bdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    rows = _read_index()
    for r in rows:
        if r["id"] == bid:
            r["status"] = "published"
            r["published"] = meta["published"]
    _write_index(rows)
    return True, {"published": done, "backup": bool(backups)}


def reject(bid):
    """驳回并删除批次（保留最近 backup 以便追溯）。"""
    bdir = _batch_dir(bid)
    if not bdir or not os.path.isdir(bdir):
        return False, "批次不存在"
    try:
        with open(os.path.join(bdir, "meta.json"), encoding="utf-8") as f:
            meta = json.load(f)
        meta["status"] = "rejected"
        meta["rejected"] = _now()
        # 保留元信息到审计目录，删除数据文件
        audit = os.path.join(STAGE, "_audit")
        os.makedirs(audit, exist_ok=True)
        with open(os.path.join(audit, bid + ".json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        pass
    shutil.rmtree(bdir, ignore_errors=True)
    rows = [r for r in _read_index() if r["id"] != bid]
    _write_index(rows)
    return True, {"rejected": bid}
