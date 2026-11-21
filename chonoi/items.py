"""Cá thể nguyên liệu có độ tươi (Ticket-03, Contract v1.2). Xem docs/adr/0001-kho-ca-the.md.

Bên trong mô phỏng, một cá thể là dict {"id", "kind", "units"} với `units` = độ tươi × 240 (số nguyên) để so ngưỡng
30 và hao 0.5/s (gather) / 0.25/s (quán) chính xác: 2 và 1 đơn vị mỗi tick. Ra ngoài (JSONL, file kho) dùng
`public()` -> {"id", "kind", "fresh"}.
"""

import math

from .errors import BadInput
from .ids import sort_by_id

UNITS = 240  # đơn vị mỗi điểm tươi
TICK_HZ = 60


def units_per_tick(per_s: float) -> int:
    """Đổi mức hao (điểm/giây) sang đơn vị/tick; số liệu contract phải ra số nguyên."""
    u = per_s * UNITS / TICK_HZ
    if abs(u - round(u)) > 1e-9:
        raise BadInput(f"freshness: hao {per_s}/s không quy ra số nguyên đơn vị/tick")
    return int(round(u))


def threshold_units(fr: dict) -> int:
    return int(round(fr["spoiled_below"] * UNITS))


def new_item(item_id: str, kind: str, fresh: float) -> dict:
    return {"id": item_id, "kind": kind, "units": int(round(fresh * UNITS))}


def fresh_of(item) -> float:
    return item["units"] / UNITS


def public(item) -> dict:
    return {"id": item["id"], "kind": item["kind"], "fresh": item["units"] / UNITS}


def public_list(items, by_id=True) -> list:
    return [public(it) for it in (sort_by_id(items) if by_id else items)]


def spoiled(item, fr: dict) -> bool:
    return item["units"] < threshold_units(fr)


def decay(items, per_tick: int, fr: dict, location: str, events: list):
    """Trừ `per_tick` đơn vị (kẹp 0); phát `spoiled` theo id khi đi từ >= ngưỡng xuống < ngưỡng.
    Trả danh sách id vừa ươn (để quán xử lý giữ chỗ)."""
    th = threshold_units(fr)
    just = []
    for it in sort_by_id(items):
        before = it["units"]
        it["units"] = max(0, before - per_tick)
        if before >= th > it["units"]:
            just.append(it["id"])
            events.append(("spoiled", {"item_id": it["id"], "kind": it["kind"], "location": location}))
    return just


def parse_items(arr, kinds, where: str) -> list:
    """Kiểm và đổi mảng cá thể {id, kind, fresh} -> cá thể nội bộ. Sai -> BadInput (mã 2)."""
    if not isinstance(arr, list):
        raise BadInput(f"{where} phải là mảng cá thể {{id, kind, fresh}} (Contract v1.2)")
    seen, out = set(), []
    for i, it in enumerate(arr):
        if not isinstance(it, dict) or set(it) != {"id", "kind", "fresh"}:
            raise BadInput(f"{where}[{i}] phải có đúng các khóa id, kind, fresh")
        iid, kind, fresh = it["id"], it["kind"], it["fresh"]
        if not isinstance(iid, str) or not iid:
            raise BadInput(f"{where}[{i}].id phải là chuỗi khác rỗng")
        if iid in seen:
            raise BadInput(f"{where}: id trùng {iid}")
        seen.add(iid)
        if kind not in kinds:
            raise BadInput(f"{where}[{i}]: nguyên liệu lạ {kind!r}")
        if isinstance(fresh, bool) or not isinstance(fresh, (int, float)) or not math.isfinite(fresh) or not 0 <= fresh <= 100:
            raise BadInput(f"{where}[{i}].fresh phải là số hữu hạn trong [0, 100]")
        out.append(new_item(iid, kind, fresh))
    return out
