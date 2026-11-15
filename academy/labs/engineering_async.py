"""固定工人数的离线协程实验；sleep 代表等待，不代表真实网络或 GPU 性能。"""

import asyncio
import json


async def run_jobs(count=6, workers=2, delay=0.01, fail_at=None, stats=None):
    if not 0 <= count <= 100 or not 1 <= workers <= 8 or not 0 <= delay <= 1:
        raise ValueError("count=0..100, workers=1..8, delay=0..1 required")
    stats = stats if stats is not None else {}
    stats.update(active=0, peak=0, workers_stopped=0)
    queue = asyncio.Queue()
    for number in range(count):
        queue.put_nowait(number)
    results = [None] * count

    async def worker():
        try:
            while True:
                try:
                    number = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                stats["active"] += 1
                stats["peak"] = max(stats["peak"], stats["active"])
                try:
                    await asyncio.sleep(delay)
                    if number == fail_at:
                        raise ValueError("planned teaching failure")
                    results[number] = {"id": number, "status": "completed", "value": number * 2}
                except ValueError as error:
                    results[number] = {"id": number, "status": "failed", "error": str(error)}
                finally:
                    stats["active"] -= 1
                    queue.task_done()
        finally:
            stats["workers_stopped"] += 1

    tasks = [asyncio.create_task(worker()) for _ in range(workers)]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    return {"results": results, "stats": dict(stats), "scope": "simulated_io_no_network"}


async def demo():
    normal = await run_jobs(fail_at=2)
    stats = {}
    task = asyncio.create_task(run_jobs(delay=1, stats=stats))
    # 等待工人真正进入可取消的等待点。
    while stats.get("active", 0) == 0:
        await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        cancelled = True
    return {"bounded_run": normal, "cancelled": cancelled, "after_cancel": stats}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(demo()), ensure_ascii=False, indent=2))
