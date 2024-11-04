import asyncio
import time

import ijson

from src.mongo import get_mongodb, create_mongo_client
from src.config import AppSettings


async def main():
    start = time.time()

    config = AppSettings()
    mongo = create_mongo_client(config.mongo)
    db = get_mongodb(mongo, config.mongo)

    calls_collection = db.get_collection(config.mongo.calls_collection)

    with open("data.json", mode="rb") as f:
        calls = ijson.items(f, "item")
        call_batch = []
        for call in calls:
            duration = (call["end_date"] - call["start_date"]) / 1000
            call["duration"] = duration
            call["price"] = duration * 10
            call_batch.append(call)
            if len(call_batch) == 30000:
                await calls_collection.insert_many(call_batch)
                call_batch.clear()

        if call_batch:
            await calls_collection.insert_many(call_batch)

    await calls_collection.create_index("phone")

    print(f"Migration time: {time.time() - start} seconds")


if __name__ == "__main__":
    asyncio.run(main())
