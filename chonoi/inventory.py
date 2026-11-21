"""File kho v1.2 (Ticket-03): {"items": [{"id", "kind", "fresh"}, ...]} — kho CÁ THỂ có độ tươi.

Đọc: chỉ nhận schema cá thể; kho đếm v1.1 ({"items": {kind: n}}), sai schema, kind lạ, id trùng, fresh ngoài
[0, 100] -> BadInput (mã 2). Trả cá thể nội bộ {id, kind, units} (xem chonoi/items.py).
Ghi: sắp theo id, fresh đủ chính xác để đọc lại đúng đơn vị (không làm tròn 3 chữ số), qua file tạm cùng
thư mục rồi thay thế nguyên tử, byte-ổn-định.
"""

import json
import os
import tempfile

from .errors import BadInput
from .items import parse_items, public_list

# v1.1 (Ticket-02) thêm ca_keo, keo_neo. Tên KINDS_P1 giữ lại để không phải sửa nơi gọi.
KINDS_P1 = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung", "ca_keo", "keo_neo")


def read_inventory(path: str, kinds=KINDS_P1) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    if isinstance(data["items"], dict):
        raise BadInput("file kho đếm theo loại (v1.1) không còn hợp lệ ở Contract v1.2: cần mảng cá thể")
    return parse_items(data["items"], kinds, "items")


def write_inventory(path: str, items: list):
    """`items`: cá thể nội bộ {id, kind, units}."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": public_list(items)}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
