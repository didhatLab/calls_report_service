import asyncio
import random
import json
from collections import defaultdict

from faststream import FastStream
from faststream.rabbit import RabbitBroker
from aio_pika.message import Message

from src.config import RabbitmqSetting
from src.consumer import request_queue, service_exchange, response_queue
from src.dto import CallsStatRequest

TEST_NUMBERS_PER_TASK_COUNT = 10


async def main():
    config = RabbitmqSetting()
    broker = RabbitBroker(config.connection_url)
    await broker.connect()
    # app = FastStream(broker)

    queue = await broker.declare_queue(response_queue)
    task_storage = {}
    stats = defaultdict(list)

    paralel_tasks = 1

    async def consume_responses(msg: Message) -> None:
        response = json.loads(msg.body)
        correlation_id = response["correlation_id"]
        duration = response["total_duration"]
        if correlation_id in task_storage:
            del task_storage[correlation_id]
            stats[paralel_tasks].append(duration)

    consume_tasks = asyncio.create_task(queue.consume(consume_responses))

    while paralel_tasks <= 15:
        gen = 0
        while gen != TEST_NUMBERS_PER_TASK_COUNT:
            tasks = await publish_tasks(broker, paralel_tasks)
            for t in tasks:
                task_storage[t.correlation_id] = t
            print(f"bench, parallel tasks: {paralel_tasks}, generation: {gen}")
            while len(task_storage) != 0:
                await asyncio.sleep(1)
            gen += 1

        paralel_tasks += 1

    average_duration_per_parallel_tasks = {}

    for paralel, durations in stats.items():
        average_duration_per_parallel_tasks[paralel] = sum(durations) / len(durations)

    print(average_duration_per_parallel_tasks)

    consume_tasks.cancel()
    await broker.close()


async def publish_tasks(broker: RabbitBroker, tasks_number: int):
    phone_numbers = [i for i in range(0, 200)]

    tasks_for_generating = tasks_number
    reqs = []
    for i in range(tasks_for_generating):
        req = CallsStatRequest(
            correlation_id=random.randint(1, 1000000000),
            phones=random.choices(phone_numbers, k=10),
        )
        reqs.append(req)

    publish_tasks = [
        broker.publish(
            req, exchange=service_exchange, routing_key=request_queue.routing_key
        )
        for req in reqs
    ]
    await asyncio.gather(*publish_tasks)

    return reqs


if __name__ == "__main__":
    asyncio.run(main())
