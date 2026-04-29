"""pytest 配置：确保速率限制测试最后运行"""



def pytest_collection_modifyitems(items):
    """将 test_ratelimit.py 的测试移到末尾"""
    ratelimit = []
    others = []
    for item in items:
        if "test_ratelimit" in item.nodeid:
            ratelimit.append(item)
        else:
            others.append(item)
    items[:] = others + ratelimit
