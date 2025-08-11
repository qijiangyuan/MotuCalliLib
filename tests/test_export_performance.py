#!/usr/bin/env python3
"""
导出图片性能测试脚本
"""

import requests
import time
import json

def test_export_performance(num_images=70):
    """测试导出图片的性能"""
    
    # 生成测试用的图片ID列表（模拟70张图片）
    # 这里使用一些已知存在的图片ID
    test_image_ids = []
    for i in range(1, num_images + 1):
        test_image_ids.append(str(i))
    
    # 测试数据
    test_data = {
        "image_ids": test_image_ids,
        "cols": 5,
        "direction": "horizontal"
    }
    
    print(f"开始测试导出 {num_images} 张图片的性能...")
    print(f"图片ID范围: 1-{num_images}")
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 发送请求
        response = requests.post(
            'http://localhost:5000/export_image_by_ids',
            json=test_data,
            timeout=60  # 60秒超时
        )
        
        # 记录结束时间
        end_time = time.time()
        total_time = end_time - start_time
        
        if response.status_code == 200:
            print(f"✅ 导出成功!")
            print(f"⏱️  总耗时: {total_time:.2f} 秒")
            print(f"📊 平均每张图片耗时: {total_time/num_images:.3f} 秒")
            print(f"📦 响应大小: {len(response.content)} 字节")
            
            # 保存测试结果图片
            with open(f'test_export_{num_images}images.png', 'wb') as f:
                f.write(response.content)
            print(f"💾 测试结果已保存为: test_export_{num_images}images.png")
            
        else:
            print(f"❌ 导出失败: HTTP {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时（60秒）")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    # 测试不同数量的图片
    test_cases = [10, 30, 50, 70]
    
    for num_images in test_cases:
        print("=" * 60)
        test_export_performance(num_images)
        print()
        time.sleep(2)  # 间隔2秒