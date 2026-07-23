#!/usr/bin/env python3
"""
推理服务演示 — 启动 FastAPI 推理网关 + 示例请求

用法:
    python scripts/run_inference.py                    # 启动 HTTP 服务
    python scripts/run_inference.py --demo              # 运行演示（发送示例请求）
    python scripts/run_inference.py --demo --n 10      # 发送10个示例请求

需要先运行 train_model.py 生成模型文件。
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def run_demo(n_requests: int = 5):
    """发送示例请求"""
    import httpx

    # 等待服务启动
    print("等待服务就绪...")
    async with httpx.AsyncClient() as client:
        for _ in range(10):
            try:
                resp = await client.get(
                    "http://localhost:8000/api/v1/health", timeout=1.0
                )
                if resp.status_code == 200:
                    print(f"服务就绪: {resp.json()}")
                    break
            except Exception:
                await asyncio.sleep(0.5)

        print(f"\n发送 {n_requests} 个审批请求...\n")

        for i in range(n_requests):
            user_id = f"user_{i:06d}"
            payload = {
                "user_id": user_id,
                "product_type": "cash_loan",
                "apply_amount": 10000,
                "device_id": f"device_{i % 100:04d}",
            }

            t0 = time.perf_counter()
            resp = await client.post(
                "http://localhost:8000/api/v1/credit/apply",
                json=payload,
                timeout=5.0,
            )
            latency = (time.perf_counter() - t0) * 1000

            result = resp.json()
            print(
                f"[{i+1:3d}] {user_id:12s} | "
                f"决策: {result['decision']:14s} | "
                f"评分: {result['score']:6.0f} | "
                f"额度: {result['credit_limit']:8.0f} | "
                f"耗时: {latency:6.1f}ms | "
                f"原因: {result['reason_codes']}"
            )


def main():
    parser = argparse.ArgumentParser(description='信贷风控推理服务')
    parser.add_argument('--demo', action='store_true',
                        help='运行演示请求')
    parser.add_argument('--n', type=int, default=5,
                        help='演示请求数量')
    parser.add_argument('--port', type=int, default=8000,
                        help='服务端口')
    args = parser.parse_args()

    if args.demo:
        asyncio.run(run_demo(args.n))
    else:
        import uvicorn
        from src.services.api_gateway import create_app

        app = create_app()
        print(f"\n启动推理服务: http://localhost:{args.port}")
        print(f"API 文档: http://localhost:{args.port}/docs")
        print(f"健康检查: http://localhost:{args.port}/api/v1/health\n")

        uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == '__main__':
    main()
