import asyncio
from contextlib import asynccontextmanager

from faststream import FastStream
from faststream.rabbit import RabbitBroker
from fast_depends import dependency_provider

from src.consumer import handler, service_exchange, response_queue
from src.config import AppSettings
from src.providers import get_app_config, get_mongo_db, get_mongo_client
from src.mongo import get_mongodb, create_mongo_client


def create_broker(config: AppSettings):
    broker = RabbitBroker(config.rabbitmq.connection_url)
    broker.include_router(handler)

    return broker


def create_app():
    config = AppSettings()

    broker = create_broker(config)

    mongo_client = create_mongo_client(config.mongo)
    mongo_db = get_mongodb(mongo_client, config.mongo)

    dependency_provider.override(get_app_config, lambda: config)
    dependency_provider.override(get_mongo_client, lambda: mongo_client)
    dependency_provider.override(get_mongo_db, lambda: mongo_db)

    @asynccontextmanager
    async def lifespan():
        yield
        mongo_client.close()

    app = FastStream(broker, lifespan=lifespan)

    @app.after_startup
    async def declare_response_queue():
        exh = await broker.declare_exchange(service_exchange)
        resp_queue = await broker.declare_queue(response_queue)
        await resp_queue.bind(exh, response_queue.routing_key)

    return app


application = create_app()

if __name__ == "__main__":
    asyncio.run(application.run())
