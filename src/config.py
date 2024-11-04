from pydantic_settings import BaseSettings, SettingsConfigDict


class MongoSetting(BaseSettings):
    host: str = "localhost"
    port: int = 27018
    username: str = "root"
    password: str = "example"
    database: str = "calls"
    max_pool_size: int = 100

    calls_collection: str = "calls"

    model_config = SettingsConfigDict(env_prefix="mongo_")


class RabbitmqSetting(BaseSettings):
    host: str = "localhost"
    port: int = 5672
    username: str = "user"
    password: str = "123"

    request_queue_name: str = "calls_stats_request"
    response_queue_name: str = "calls_stats_response"
    service_exchange_name: str = "calls_stat_service"

    model_config = SettingsConfigDict(env_prefix="rabbitmq_")

    @property
    def connection_url(self):
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/"


class AppSettings(BaseSettings):
    mongo: MongoSetting = MongoSetting()
    rabbitmq: RabbitmqSetting = RabbitmqSetting()

    service_name: str = "report_service"


setting = AppSettings()
