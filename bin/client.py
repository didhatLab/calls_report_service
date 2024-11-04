import asyncio
import random

from faststream import FastStream
from faststream.rabbit import RabbitBroker

from src.config import RabbitmqSetting
from src.consumer import request_queue, service_exchange, response_queue
from src.dto import CallsStatRequest


async def main():
    config = RabbitmqSetting()
    broker = RabbitBroker(config.connection_url)
    await broker.connect()
    app = FastStream(broker)

    task_storage = {}
    publisher_task = asyncio.create_task(task_publisher(broker, task_storage))

    @broker.subscriber(response_queue, service_exchange)
    async def consume_responses(response: dict):
        print(
            f"get response from service for correlation id: {response["correlation_id"]}, total execution: {response["total_duration"]}"
        )
        if response["correlation_id"] in task_storage:
            del task_storage[response["correlation_id"]]

    try:
        await app.run()
    except KeyboardInterrupt:
        publisher_task.cancel()


async def task_publisher(broker: RabbitBroker, task_storage: dict):
    phone_numbers = [i for i in range(0, 200)]

    while True:
        tasks_for_generating = 1
        reqs = []
        for i in range(tasks_for_generating):
            req = CallsStatRequest(
                correlation_id=random.randint(1, 1000000000),
                phones=random.choices(phone_numbers, k=10),
            )
            reqs.append(req)
            task_storage[req.correlation_id] = req

        publish_tasks = [
            broker.publish(
                req, exchange=service_exchange, routing_key=request_queue.routing_key
            )
            for req in reqs
        ]
        await asyncio.gather(*publish_tasks)

        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
