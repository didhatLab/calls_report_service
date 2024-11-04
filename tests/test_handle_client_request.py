import pytest
import pytest_asyncio
from fast_depends import dependency_provider

from src.config import AppSettings
from src.providers import get_app_config
from src.consumer import handle_client_ring_request
from src.mongo import create_mongo_client, get_mongodb
from src.dto import CallsStatRequest, CallsStatsResponse, ResponseStatus


@pytest.fixture(scope="session")
def motor_mongo_client(config):
    return create_mongo_client(config.mongo)


@pytest.fixture(scope="session")
def motor_mongodb(motor_mongo_client, config):
    return get_mongodb(motor_mongo_client, config.mongo)


@pytest_asyncio.fixture(loop_scope="function", autouse=True)
async def clear_mongodb(motor_mongo_client, config):
    yield
    test_db = motor_mongo_client.get_database(config.mongo.database)
    collections = await test_db.list_collection_names()

    for coll in collections:
        if not coll.startswith("system."):
            await test_db.drop_collection(coll)


@pytest.fixture(scope="session")
def config():
    config = AppSettings()
    dependency_provider.override(get_app_config, lambda: config)
    return config


async def test_handle_client_request(motor_mongodb, config):
    calls_collection = motor_mongodb.get_collection(config.mongo.calls_collection)

    start_ns = 1684957028364

    await calls_collection.insert_many(
        [
            {"phone": 1, "start_date": start_ns, "end_date": start_ns + 4000},
            {"phone": 1, "start_date": start_ns, "end_date": start_ns + 8000},
            {"phone": 1, "start_date": start_ns, "end_date": start_ns + 40000},
            {"phone": 1, "start_date": start_ns, "end_date": start_ns + 12000},
        ]
    )

    req = CallsStatRequest(correlation_id=1, phones=[1])

    response: CallsStatsResponse = await handle_client_ring_request(
        req, motor_mongodb, config
    )

    assert response.correlation_id == req.correlation_id
    assert response.to == "client"
    assert response.from_ == config.service_name
    assert response.status == ResponseStatus.complete
    assert response.total_duration is not None
    assert len(response.data) == 1
    phone_stat = response.data[0]

    assert phone_stat.phone == 1
    assert phone_stat.min_price_att == 40
    assert phone_stat.max_price_att == 400
    assert phone_stat.cnt_all_attempts == 4
    assert phone_stat.cnt_att_dur.sec_10 == 2
    assert phone_stat.cnt_att_dur.sec_10_30 == 1
    assert phone_stat.cnt_att_dur.sec_30 == 1
    assert phone_stat.sum_price_att_over_15 == 400
    assert phone_stat.avg_dur_att == 16
