"""安全加固：速率限制 _SlidingWindow 滑动窗口单元测试
覆盖窗口计数、过期清理、记录、边界条件"""

import time

from app.core.ratelimit import _SlidingWindow


class TestSlidingWindow:
    """_SlidingWindow 滑动窗口计数器纯单元测试"""

    def test_empty_window_count_is_zero(self):
        """新窗口计数为 0"""
        sw = _SlidingWindow()
        assert sw.count(60.0, time.monotonic()) == 0

    def test_record_increments_count(self):
        """record 增加计数"""
        sw = _SlidingWindow()
        now = time.monotonic()
        sw.record(now)
        assert sw.count(60.0, now) == 1

    def test_multiple_records(self):
        """多次 record 累加"""
        sw = _SlidingWindow()
        now = time.monotonic()
        for _ in range(5):
            sw.record(now)
        assert sw.count(60.0, now) == 5

    def test_expired_entries_not_counted(self):
        """过期条目不计入"""
        sw = _SlidingWindow()
        now = time.monotonic()
        sw.record(now - 120.0)  # 2 分钟前
        assert sw.count(60.0, now) == 0

    def test_partial_expiry(self):
        """部分条目过期后只计算未过期的"""
        sw = _SlidingWindow()
        now = time.monotonic()
        sw.record(now - 90.0)   # 过期
        sw.record(now - 30.0)   # 未过期
        sw.record(now)           # 未过期
        assert sw.count(60.0, now) == 2

    def test_exact_boundary_not_expired(self):
        """恰好等于窗口大小的条目仍过期（cutoff = now - window）"""
        sw = _SlidingWindow()
        now = time.monotonic()
        window = 60.0
        sw.record(now - window)  # now - 60 < now - 60 不成立，所以不过期
        # cutoff = now - 60.0, timestamp = now - 60.0
        # ts[0] < cutoff → (now-60) < (now-60) → False → 不过期
        assert sw.count(window, now) == 1

    def test_just_past_boundary_expired(self):
        """超过窗口边界 0.001 秒的条目过期"""
        sw = _SlidingWindow()
        now = time.monotonic()
        window = 60.0
        sw.record(now - window - 0.001)
        assert sw.count(window, now) == 0

    def test_zero_window_counts_all_as_current(self):
        """窗口为 0 时当前时刻的记录仍计入（timestamp < cutoff 不成立）"""
        sw = _SlidingWindow()
        now = time.monotonic()
        sw.record(now)
        sw.record(now)
        # cutoff = now - 0 = now, ts[0] = now, now < now → False → 不过期
        assert sw.count(0.0, now) == 2

    def test_large_window_keeps_all(self):
        """超大窗口保留所有记录"""
        sw = _SlidingWindow()
        now = time.monotonic()
        for i in range(100):
            sw.record(now - i)
        assert sw.count(10000.0, now) == 100

    def test_count_cleans_up_old_entries(self):
        """count 调用清理过期条目，后续 count 更快"""
        sw = _SlidingWindow()
        now = time.monotonic()
        # 记录：50 个在窗口内（now-50 到 now），150 个在窗口外（now-200 到 now-51）
        for i in range(200):
            sw.record(now - 200.0 + i)
        # 窗口 60s：now-200 到 now-61 过期（共 140 个），now-60 到 now 未过期（共 60 个）
        count1 = sw.count(60.0, now)
        assert count1 == 60
        # 过期条目已被 pop 掉
        count2 = sw.count(60.0, now)
        assert count1 == count2

    def test_record_at_different_timestamps(self):
        """不同时间戳的 record"""
        sw = _SlidingWindow()
        now = time.monotonic()
        sw.record(now - 59.0)
        sw.record(now - 30.0)
        sw.record(now - 1.0)
        sw.record(now)
        assert sw.count(60.0, now) == 4

    def test_window_slides_correctly(self):
        """窗口滑动后计数减少"""
        sw = _SlidingWindow()
        base = time.monotonic()
        # 在 t=0 时记录
        sw.record(base)
        assert sw.count(10.0, base) == 1
        # 在 t=5 时仍计入
        assert sw.count(10.0, base + 5.0) == 1
        # 在 t=10.001 时过期
        assert sw.count(10.0, base + 10.001) == 0

    def test_many_records_performance(self):
        """大量记录性能可接受（1000 条 < 1s）"""
        sw = _SlidingWindow()
        now = time.monotonic()
        start = time.monotonic()
        for i in range(1000):
            sw.record(now - 0.001 * i)
        sw.count(60.0, now)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0

    def test_timestamps_list_order(self):
        """timestamps 保持插入顺序（递增）"""
        sw = _SlidingWindow()
        base = time.monotonic()
        for i in range(10):
            sw.record(base + i * 0.1)
        ts = sw.timestamps
        for i in range(len(ts) - 1):
            assert ts[i] <= ts[i + 1]

    def test_slots_optimization(self):
        """__slots__ 限制实例属性"""
        sw = _SlidingWindow()
        assert hasattr(sw, '__slots__')
        assert 'timestamps' in _SlidingWindow.__slots__

    def test_single_record_exact_window_edge(self):
        """单条记录恰好在窗口边缘"""
        sw = _SlidingWindow()
        now = time.monotonic()
        sw.record(now - 59.999)
        assert sw.count(60.0, now) == 1

    def test_records_all_same_timestamp(self):
        """所有记录使用同一时间戳"""
        sw = _SlidingWindow()
        now = time.monotonic()
        for _ in range(50):
            sw.record(now)
        assert sw.count(60.0, now) == 50

    def test_count_does_not_modify_count(self):
        """连续调用 count 不改变结果"""
        sw = _SlidingWindow()
        now = time.monotonic()
        sw.record(now - 30.0)
        sw.record(now)
        c1 = sw.count(60.0, now)
        c2 = sw.count(60.0, now)
        assert c1 == c2 == 2
