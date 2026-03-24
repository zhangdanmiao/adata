# -*- coding: utf-8 -*-
"""
测试ETF行情接口的频率限制功能
"""
import time
from adata.fund.market.etf_market_ths import ETFMarketThs
from adata import reset_rate_limit

def test_etf_rate_limit():
    print("=== 测试ETF行情接口频率限制 ===")
    
    # 重置所有频率限制
    reset_rate_limit()
    
    etf_market = ETFMarketThs()
    fund_code = '512880'
    start_date = '2024-01-01'
    
    print(f"\n测试目标：调用 {fund_code} 的ETF行情接口")
    print(f"默认限制：每分钟最多30次请求")
    print("-" * 60)
    
    success_count = 0
    try:
        # 尝试调用35次，应该在第31次触发限流
        for i in range(35):
            print(f"\n第 {i+1} 次请求...")
            try:
                result = etf_market.get_market_etf_ths(
                    fund_code=fund_code, 
                    start_date=start_date
                )
                if isinstance(result, Exception):
                    print(f"  请求返回异常: {result}")
                else:
                    success_count += 1
                    print(f"  请求成功！获取到 {len(result)} 条数据")
            except Exception as e:
                print(f"  捕获到异常: {type(e).__name__}: {e}")
                print(f"\n{'='*60}")
                print(f"频率限制已触发！")
                print(f"成功请求次数: {success_count}")
                print(f"{'='*60}")
                break
                
            # 稍微间隔一下，避免请求过快同时也能测试频率限制
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n发生未预期的错误: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_etf_rate_limit()
