"""CSV 导入共享函数 validate_csv_upload 单元测试"""

import asyncio

import pytest

from app.services.csv_import import validate_csv_upload


class _FakeUpload:
    """模拟 FastAPI UploadFile"""

    def __init__(self, filename: str | None, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


def _run(coro):
    return asyncio.run(coro)


# ─── 正常路径 ────────────────────────────────────────────────


def test_valid_csv_returns_reader():
    """合法 CSV 返回 DictReader"""
    csv_bytes = "名称,价格\n测试商品,100\n".encode()
    f = _FakeUpload("data.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["名称"] == "测试商品"
    assert rows[0]["价格"] == "100"


def test_valid_csv_with_bom():
    """UTF-8 BOM 文件能正确解析"""
    csv_bytes = b"\xef\xbb\xbf" + "名称,价格\n测试,200\n".encode()
    f = _FakeUpload("data.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    rows = list(reader)
    assert rows[0]["名称"] == "测试"


def test_chinese_headers():
    """中文表头能正确解析"""
    csv_bytes = "商品名称,销售价,成本价\n测试,100,60\n".encode()
    f = _FakeUpload("products.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    assert "商品名称" in reader.fieldnames


# ─── 文件名校验 ──────────────────────────────────────────────


def test_no_filename_rejected():
    """无文件名被拒绝"""
    f = _FakeUpload(None, b"a,b\n1,2\n")
    with pytest.raises(Exception) as exc_info:
        _run(validate_csv_upload(f))
    assert exc_info.value.status_code == 400
    assert "CSV" in exc_info.value.detail["message"]


def test_non_csv_extension_rejected():
    """非 .csv 扩展名被拒绝"""
    f = _FakeUpload("data.xlsx", b"a,b\n1,2\n")
    with pytest.raises(Exception) as exc_info:
        _run(validate_csv_upload(f))
    assert exc_info.value.status_code == 400


# ─── 编码校验 ────────────────────────────────────────────────


def test_non_utf8_rejected():
    """非 UTF-8 编码被拒绝"""
    csv_bytes = "名称,价格\n测试,100\n".encode("gbk")
    f = _FakeUpload("data.csv", csv_bytes)
    with pytest.raises(Exception) as exc_info:
        _run(validate_csv_upload(f))
    assert exc_info.value.status_code == 400
    assert "UTF-8" in exc_info.value.detail["message"]


# ─── 文件大小校验 ────────────────────────────────────────────


def test_oversized_file_rejected():
    """超过大小限制被拒绝"""
    from unittest.mock import patch

    large = b"x" * 100
    f = _FakeUpload("data.csv", large)
    with patch("app.services.csv_import.settings.MAX_CSV_IMPORT_SIZE_MB", 0):
        with pytest.raises(Exception) as exc_info:
            _run(validate_csv_upload(f))
        assert exc_info.value.status_code == 400
        assert "MB" in exc_info.value.detail["message"]


# ─── 空文件/空表头 ──────────────────────────────────────────


def test_empty_file_rejected():
    """空文件被拒绝"""
    f = _FakeUpload("empty.csv", b"")
    with pytest.raises(Exception) as exc_info:
        _run(validate_csv_upload(f))
    assert exc_info.value.status_code == 400


def test_only_headers_no_data_ok():
    """只有表头无数据行可以返回 reader"""
    csv_bytes = "名称,价格\n".encode()
    f = _FakeUpload("headers.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    assert reader.fieldnames == ["名称", "价格"]
    assert list(reader) == []


# ─── 边界条件 ──────────────────────────────────────────────


def test_mixed_line_endings():
    """混合 \\r\\n 和 \\n 行尾均能解析"""
    csv_bytes = "名称,价格\r\n测试1,100\n测试2,200\r\n".encode()
    f = _FakeUpload("mixed.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["名称"] == "测试1"
    assert rows[1]["价格"] == "200"


def test_quoted_field_with_comma():
    """CSV 引号内含逗号能正确解析"""
    csv_bytes = '名称,备注\n"含,逗号",正常备注\n'.encode()
    f = _FakeUpload("quoted.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["名称"] == "含,逗号"


def test_quoted_field_with_newline():
    """CSV 引号内含换行能正确解析"""
    csv_bytes = '名称,备注\n"含\n换行",正常备注\n'.encode()
    f = _FakeUpload("quoted_nl.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    rows = list(reader)
    assert len(rows) == 1
    assert "换行" in rows[0]["名称"]


def test_duplicate_column_names():
    """重复列名时后者覆盖前者（Python csv.DictReader 行为）"""
    csv_bytes = "名称,名称\n值1,值2\n".encode()
    f = _FakeUpload("dup_col.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    rows = list(reader)
    assert len(rows) == 1
    # DictReader 对重复列名只保留最后一个值
    assert rows[0]["名称"] == "值2"


def test_header_with_extra_whitespace():
    """表头列名含前后空格能正确匹配"""
    csv_bytes = " 名称 , 价格 \n测试,100\n".encode()
    f = _FakeUpload("ws_header.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    rows = list(reader)
    assert len(rows) == 1
    # csv.DictReader 保留表头中的空格，fieldnames 含空格
    assert " 名称 " in reader.fieldnames


def test_single_column_csv():
    """单列 CSV 能正确解析"""
    csv_bytes = "名称\n单列测试\n".encode()
    f = _FakeUpload("single.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["名称"] == "单列测试"


def test_unicode_emoji_in_csv():
    """Unicode emoji 内容能正确解析"""
    csv_bytes = "名称,备注\n🎉庆典商品,备注🚀\n".encode()
    f = _FakeUpload("emoji.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    rows = list(reader)
    assert "🎉" in rows[0]["名称"]
    assert "🚀" in rows[0]["备注"]


def test_very_long_row():
    """超长行（5000+ 字符）能正确解析"""
    long_val = "A" * 5000
    csv_bytes = f"名称,备注\n{long_val},短备注\n".encode()
    f = _FakeUpload("long.csv", csv_bytes)
    reader = _run(validate_csv_upload(f))
    rows = list(reader)
    assert len(rows[0]["名称"]) == 5000
