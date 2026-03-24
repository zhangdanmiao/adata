# -*- coding: utf-8 -*-
"""
@desc: 频率限制功能测试
@author: 1nchaos
@time: 2026/3/24
"""

import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 直接导入模块，避免触发整个包的导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'adata', 'common', 'utils'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'adata', 'common', 'exception'))

# 手动导入需要的模块
from rate_limiter import RateLimiter, RateLimitConfig, RateLimitExceeded


class MockResponse:
    """模拟requests.Response对象"""
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self._text = text
        self.headers = {}
    
    def json(self):
        return self._json
    
    def text(self):
        return self._text
    
    def __bool__(self):
        return self.status_code == 200


class RateLimitResponse:
    """
    频率限制响应对象
    当请求频率超过限制时返回此对象，模拟requests.Response接口
    """
    
    def __init__(self, domain: str, max_requests: int, window: int, retry_after: int):
        self.status_code = 429  # HTTP 429 Too Many Requests
        self.domain = domain
        self.max_requests = max_requests
        self.window = window
        self.retry_after = retry_after
        self.headers = {'Retry-After': str(retry_after)}
        self._json_data = {
            'status_code': 429,
            'error': 'RATE_LIMIT_EXCEEDED',
            'message': f'请求频率超过限制: 域名 "{domain}" 在 {window} 秒内最多允许 {max_requests} 次请求，请 {retry_after} 秒后重试',
            'domain': domain,
            'retry_after': retry_after
        }
    
    def json(self):
        """返回JSON格式的错误信息"""
        return self._json_data
    
    def text(self):
        """返回文本格式的错误信息"""
        return self._json_data['message']
    
    def __bool__(self):
        """频率限制响应始终为False，表示请求未成功"""
        return False


def test_basic_rate_limit():
    """测试基本限流功能"""
    print("=" * 60)
    print("测试1: 基本限流功能")
    print("=" * 60)
    
    limiter = RateLimiter()
    url = "https://api.example.com/data"
    
    # 设置每秒最多2次请求
    config = RateLimitConfig(enabled=True, max_requests=2, window=1)
    
    # 前2次应该成功
    result1 = limiter.allow_request(url, config)
    print(f"第1次请求: 允许={result1[0]}, 域名={result1[1]}")
    
    result2 = limiter.allow_request(url, config)
    print(f"第2次请求: 允许={result2[0]}, 域名={result2[1]}")
    
    # 第3次应该被限制
    result3 = limiter.allow_request(url, config)
    print(f"第3次请求: 允许={result3[0]}, 域名={result3[1]}, 重试时间={result3[3]}秒")
    
    assert result1[0] == True, "第1次请求应该被允许"
    assert result2[0] == True, "第2次请求应该被允许"
    assert result3[0] == False, "第3次请求应该被限制"
    
    print("✓ 基本限流功能测试通过\n")


def test_domain_isolation():
    """测试域名隔离"""
    print("=" * 60)
    print("测试2: 域名隔离")
    print("=" * 60)
    
    limiter = RateLimiter()
    config = RateLimitConfig(enabled=True, max_requests=2, window=60)
    
    url1 = "https://api1.example.com/data"
    url2 = "https://api2.example.com/data"
    
    # 对api1请求2次
    r1 = limiter.allow_request(url1, config)
    r2 = limiter.allow_request(url1, config)
    print(f"api1 - 第1次: 允许={r1[0]}")
    print(f"api1 - 第2次: 允许={r2[0]}")
    
    # api1应该被限制
    r3 = limiter.allow_request(url1, config)
    print(f"api1 - 第3次: 允许={r3[0]}")
    
    # api2应该仍然可以请求
    r4 = limiter.allow_request(url2, config)
    print(f"api2 - 第1次: 允许={r4[0]}")
    
    assert r3[0] == False, "api1 第3次应该被限制"
    assert r4[0] == True, "api2 第1次应该被允许"
    
    print("✓ 域名隔离测试通过\n")


def test_sliding_window():
    """测试滑动窗口"""
    print("=" * 60)
    print("测试3: 滑动窗口")
    print("=" * 60)
    
    limiter = RateLimiter()
    config = RateLimitConfig(enabled=True, max_requests=2, window=2)  # 2秒窗口
    
    url = "https://api.example.com/data"
    
    # 请求2次
    limiter.allow_request(url, config)
    limiter.allow_request(url, config)
    print("已请求2次")
    
    # 第3次应该被限制
    result = limiter.allow_request(url, config)
    print(f"第3次请求: 允许={result[0]}")
    assert result[0] == False, "应该被限制"
    
    # 等待窗口过期
    print("等待2.5秒...")
    time.sleep(2.5)
    
    # 现在应该可以请求了
    result = limiter.allow_request(url, config)
    print(f"窗口过期后请求: 允许={result[0]}")
    assert result[0] == True, "窗口过期后应该允许"
    
    print("✓ 滑动窗口测试通过\n")


def test_disabled_rate_limit():
    """测试禁用限流"""
    print("=" * 60)
    print("测试4: 禁用限流")
    print("=" * 60)
    
    limiter = RateLimiter()
    config = RateLimitConfig(enabled=False, max_requests=1, window=60)
    
    url = "https://api.example.com/data"
    
    # 即使配置为每秒1次，但禁用了，应该都可以请求
    for i in range(5):
        result = limiter.allow_request(url, config)
        print(f"第{i+1}次请求: 允许={result[0]}")
        assert result[0] == True, f"第{i+1}次请求应该被允许"
    
    print("✓ 禁用限流测试通过\n")


def test_rate_limit_response():
    """测试 RateLimitResponse 对象"""
    print("=" * 60)
    print("测试5: RateLimitResponse 对象")
    print("=" * 60)
    
    response = RateLimitResponse(
        domain="api.example.com",
        max_requests=30,
        window=60,
        retry_after=15
    )
    
    print(f"状态码: {response.status_code}")
    print(f"域名: {response.domain}")
    print(f"重试时间: {response.retry_after}")
    print(f"JSON数据: {response.json()}")
    print(f"布尔值: {bool(response)}")
    
    assert response.status_code == 429
    assert response.domain == "api.example.com"
    assert response.retry_after == 15
    assert bool(response) == False  # 频率限制响应应该为False
    
    print("✓ RateLimitResponse 测试通过\n")


def test_domain_config():
    """测试域名特定配置"""
    print("=" * 60)
    print("测试6: 域名特定配置")
    print("=" * 60)
    
    limiter = RateLimiter()
    
    # 设置默认配置：每分钟30次
    limiter.set_default_config({'enabled': True, 'max_requests': 30, 'window': 60})
    
    # 为特定域名设置不同配置：每分钟5次
    limiter.set_domain_config('api.example.com', {'enabled': True, 'max_requests': 5, 'window': 60})
    
    url1 = "https://api.example.com/data"
    url2 = "https://other.example.com/data"
    
    # api.example.com 应该只能请求5次
    count1 = 0
    for i in range(10):
        result = limiter.allow_request(url1)
        if result[0]:
            count1 += 1
        else:
            print(f"api.example.com 在第{i+1}次被限制")
            break
    
    # other.example.com 应该可以请求更多次（使用默认配置30次）
    count2 = 0
    for i in range(10):
        result = limiter.allow_request(url2)
        if result[0]:
            count2 += 1
        else:
            print(f"other.example.com 在第{i+1}次被限制")
            break
    
    print(f"api.example.com 成功请求: {count1}次 (预期: 5次)")
    print(f"other.example.com 成功请求: {count2}次 (预期: 10次，因为默认是30次)")
    
    assert count1 == 5, f"api.example.com 应该只能请求5次，实际{count1}次"
    assert count2 == 10, f"other.example.com 应该能请求10次，实际{count2}次"
    
    print("✓ 域名特定配置测试通过\n")


def test_status_and_reset():
    """测试状态查询和重置功能"""
    print("=" * 60)
    print("测试7: 状态查询和重置")
    print("=" * 60)
    
    limiter = RateLimiter()
    
    # 为域名设置特定配置
    limiter.set_domain_config('api.example.com', {'enabled': True, 'max_requests': 10, 'window': 60})
    
    url = "https://api.example.com/data"
    
    # 请求3次
    for _ in range(3):
        limiter.allow_request(url)
    
    # 查询状态
    status = limiter.get_domain_status("api.example.com")
    print(f"域名状态: {status}")
    
    assert status['current_requests'] == 3
    assert status['max_requests'] == 10
    assert status['remaining'] == 7
    
    # 重置
    limiter.reset("api.example.com")
    
    # 再次查询
    status = limiter.get_domain_status("api.example.com")
    print(f"重置后状态: {status}")
    
    assert status['current_requests'] == 0
    assert status['remaining'] == 10
    
    print("✓ 状态查询和重置测试通过\n")


def test_exception():
    """测试异常抛出"""
    print("=" * 60)
    print("测试8: 异常抛出")
    print("=" * 60)
    
    limiter = RateLimiter()
    config = RateLimitConfig(enabled=True, max_requests=1, window=60)
    
    url = "https://api.example.com/data"
    
    # 第一次请求成功
    limiter.allow_request(url, config)
    
    # 第二次应该抛出异常
    try:
        limiter.check_rate_limit(url, config)
        assert False, "应该抛出 RateLimitExceeded 异常"
    except RateLimitExceeded as e:
        print(f"捕获到异常: {e}")
        print(f"状态码: {e.status_code}")
        print(f"域名: {e.domain}")
        print(f"重试时间: {e.retry_after}秒")
        assert e.status_code == 429
        assert e.domain == "api.example.com"
    
    print("✓ 异常抛出测试通过\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始频率限制功能测试")
    print("=" * 60 + "\n")
    
    try:
        test_basic_rate_limit()
        test_domain_isolation()
        test_sliding_window()
        test_disabled_rate_limit()
        test_rate_limit_response()
        test_domain_config()
        test_status_and_reset()
        test_exception()
        
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
