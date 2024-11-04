import asyncio
import datetime
from typing import Optional
from timeit import default_timer as timer

from faststream import Depends
from faststream.rabbit import (
    RabbitExchange,
    RabbitQueue,
    RabbitRouter,
)
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from src.config import setting, AppSettings
from src.dto import (
    PhoneStats,
    DurationStat,
    CallsStatRequest,
    CallsStatsResponse,
    ResponseStatus,
)
from src.providers import get_mongo_db, get_app_config

handler = RabbitRouter()

service_exchange = RabbitExchange(
    name=setting.rabbitmq.service_exchange_name, durable=True
)
request_queue = RabbitQueue(
    name=setting.rabbitmq.request_queue_name, durable=True, routing_key="client_request"
)
response_queue = RabbitQueue(
    name=setting.rabbitmq.response_queue_name,
    durable=True,
    routing_key="service_response",
)


@handler.publisher(queue=response_queue, exchange=service_exchange)
@handler.subscriber(queue=request_queue, exchange=service_exchange, retry=3)
async def handle_client_ring_request(
    request: CallsStatRequest,
    mongodb: AsyncIOMotorDatabase = Depends(get_mongo_db),
    config: AppSettings = Depends(get_app_config),
):
    task_received_time = datetime.datetime.now(datetime.timezone.utc)
    start_report_time = timer()

    calls_collection = mongodb.get_collection(config.mongo.calls_collection)
    reports = await _calc_stats_for_numbers(calls_collection, request.phones)

    response = CallsStatsResponse(
        correlation_id=request.correlation_id,
        status=ResponseStatus.complete,
        task_received=task_received_time,
        from_=config.service_name,
        to="client",
        data=reports,
        total_duration=timer() - start_report_time,
    )
    return response


async def _calc_stats_for_numbers(
    calls_collection: AsyncIOMotorCollection, phone_numbers: list[int]
) -> list[PhoneStats]:
    report_tasks = [
        _calc_stats_number(calls_collection, phone) for phone in phone_numbers
    ]
    phone_stats = await asyncio.gather(*report_tasks)

    return [stat for stat in phone_stats if stat is not None]


async def _calc_stats_number(
    collection: AsyncIOMotorCollection, number: int
) -> Optional[PhoneStats]:
    pipeline = [
        {"$match": {"phone": {"$eq": number}}},
        {
            "$addFields": {
                "duration": {
                    "$divide": [{"$subtract": ["$end_date", "$start_date"]}, 1000]
                },
                "price": {
                    "$divide": [{"$subtract": ["$end_date", "$start_date"]}, 100]
                },
            }
        },
        {
            "$group": {
                "_id": "$phone",
                "cnt_all_attempts": {"$sum": 1},
                "cnt_10_sec": {"$sum": {"$cond": [{"$lt": ["$duration", 10]}, 1, 0]}},
                "cnt_10_30_sec": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$gte": ["$duration", 10]},
                                    {"$lt": ["$duration", 30]},
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "cnt_30_sec": {"$sum": {"$cond": [{"$gte": ["$duration", 30]}, 1, 0]}},
                "min_price_att": {"$min": "$price"},
                "max_price_att": {"$max": "$price"},
                "avg_dur_att": {"$avg": "$duration"},
                "sum_price_att_over_15": {
                    "$sum": {
                        "$cond": [
                            {"$gt": ["$duration", 15]},
                            "$price",
                            0,
                        ]
                    }
                },
            }
        },
        {
            "$project": {
                "cnt_all_attempts": 1,
                "cnt_10_sec": 1,
                "cnt_10_30_sec": 1,
                "cnt_30_sec": 1,
                "min_price_att": 1,
                "max_price_att": 1,
                "avg_dur_att": 1,
                "sum_price_att_over_15": 1,
            }
        },
    ]

    cursor = collection.aggregate(pipeline)
    try:
        result = await cursor.next()
    except StopAsyncIteration:
        return None

    return PhoneStats(
        phone=result["_id"],
        cnt_all_attempts=result["cnt_all_attempts"],
        cnt_att_dur=DurationStat(
            sec_10=result["cnt_10_sec"],
            sec_10_30=result["cnt_10_30_sec"],
            sec_30=result["cnt_30_sec"],
        ),
        min_price_att=result["min_price_att"],
        max_price_att=result["max_price_att"],
        avg_dur_att=result["avg_dur_att"],
        sum_price_att_over_15=result["sum_price_att_over_15"],
    )
