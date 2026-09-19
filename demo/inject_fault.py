#!/usr/bin/env python3
"""
故障注入演示脚本
用于路演时一键制造故障，展示根因定位能力
"""
import time
import subprocess
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def inject_cpu_stress(seconds: int = 30):
    """注入 CPU 负载故障"""
    logger.info(f"🔥 注入 CPU 负载故障，持续 {seconds} 秒...")
    try:
        subprocess.Popen(["stress-ng", "--cpu", "4", "--timeout", str(seconds)])
        logger.info("✅ CPU 负载已注入，请观察 Prometheus 指标变化")
    except FileNotFoundError:
        logger.warning("⚠️  stress-ng 未安装，使用 Python 方式模拟...")
        end = time.time() + seconds
        while time.time() < end:
            _ = sum(i * i for i in range(100000))


def inject_memory_leak(mb: int = 500, seconds: int = 30):
    """注入内存泄漏故障"""
    logger.info(f"🔥 注入内存泄漏故障: 占用 {mb}MB，持续 {seconds} 秒...")
    blob = " " * (mb * 1024 * 1024)
    time.sleep(seconds)
    del blob
    logger.info("✅ 内存已释放")


def inject_disk_io(seconds: int = 30):
    """注入磁盘 IO 故障"""
    logger.info(f"🔥 注入磁盘 IO 故障，持续 {seconds} 秒...")
    try:
        subprocess.Popen(
            ["dd", "if=/dev/zero", "of=/tmp/test_io.tmp", "bs=1M", "count=1000"]
        )
        time.sleep(seconds)
        subprocess.run(["rm", "-f", "/tmp/test_io.tmp"])
        logger.info("✅ 磁盘 IO 测试完成")
    except Exception as e:
        logger.error(f"❌ 磁盘 IO 注入失败: {e}")


def inject_container_crash(container_name: str):
    """注入容器崩溃故障"""
    logger.info(f"🔥 停止容器 {container_name} ...")
    try:
        subprocess.run(["docker", "stop", container_name], check=True)
        logger.info(f"✅ 容器 {container_name} 已停止，观察告警和根因定位")
    except Exception as e:
        logger.error(f"❌ 容器停止失败: {e}")


def inject_gpu_busy(seconds: int = 30):
    """注入 GPU 高负载故障（需要 PyTorch）"""
    logger.info(f"🔥 注入 GPU 高负载故障，持续 {seconds} 秒...")
    try:
        import torch
        if not torch.cuda.is_available():
            logger.warning("⚠️  未检测到 GPU，跳过")
            return
        logger.info(f"   可用 GPU 数量: {torch.cuda.device_count()}")
        end = time.time() + seconds
        while time.time() < end:
            # 持续做矩阵乘法占用 GPU
            a = torch.randn(2048, 2048, device="cuda")
            b = torch.randn(2048, 2048, device="cuda")
            _ = torch.mm(a, b)
        logger.info("✅ GPU 负载测试完成")
    except ImportError:
        logger.warning("⚠️  PyTorch 未安装，无法注入 GPU 故障")


FAULT_MAP = {
    "cpu": inject_cpu_stress,
    "memory": inject_memory_leak,
    "disk": inject_disk_io,
    "gpu": inject_gpu_busy,
}


def main():
    parser = argparse.ArgumentParser(description="ZSvirt Observer 故障注入演示")
    parser.add_argument(
        "fault",
        choices=list(FAULT_MAP.keys()) + ["all"],
        help="故障类型: cpu, memory, disk, gpu, all",
    )
    parser.add_argument("--duration", type=int, default=30, help="持续时间（秒）")
    args = parser.parse_args()

    print("=" * 50)
    print("  ZSVirt Observer - 故障注入演示")
    print("=" * 50)
    print()

    if args.fault == "all":
        for name, func in FAULT_MAP.items():
            logger.info(f"\n--- 注入 {name} 故障 ---")
            if name == "memory":
                func(500, args.duration)
            else:
                func(args.duration)
            time.sleep(5)
    else:
        func = FAULT_MAP[args.fault]
        if args.fault == "memory":
            func(500, args.duration)
        else:
            func(args.duration)

    print()
    print("=" * 50)
    print("  故障注入完成，请观察 Grafana 和根因报告")
    print("=" * 50)


if __name__ == "__main__":
    main()
