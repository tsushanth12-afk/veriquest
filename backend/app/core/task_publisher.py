"""API-owned publisher; no worker imports, database access or Docker dependency.

Only failure BEFORE send_task is definitely unpublished. Once send starts, an
exception (including connection cleanup) cannot prove whether Redis received it.
No automatic retry: the DB/broker boundary is deliberately not called atomic.
"""
from uuid import UUID, uuid4

from celery import Celery
from starlette.concurrency import run_in_threadpool

from .config import Settings
from .task_contract import EXECUTE_TASK, VALIDATE_TASK, TASK_QUEUE


class PublicationError(Exception):
    def __init__(self, *, uncertain: bool, task_id: str):
        self.uncertain, self.task_id = uncertain, task_id
        super().__init__("Task publication outcome unknown" if uncertain else "Task not published")


def _publish(task: str, arguments: list[str], settings: Settings) -> str:
    task_id = str(uuid4())
    sending = False
    app = None
    try:
        sizes = {EXECUTE_TASK: 1, VALIDATE_TASK: 2}
        if task not in sizes or len(arguments) != sizes[task]:
            raise ValueError("Invalid task contract")
        arguments = [str(UUID(value)) for value in arguments]
        app = Celery("veriquest-api-publisher", broker=settings.redis_url)
        timeout = settings.task_publish_timeout_seconds
        app.conf.update(
            task_serializer="json", accept_content=["json"],
            task_publish_retry=False, broker_connection_retry=False,
            broker_connection_retry_on_startup=False, broker_connection_max_retries=0,
            broker_connection_timeout=timeout,
            broker_transport_options={"socket_connect_timeout": timeout,
                                      "socket_timeout": timeout,
                                      "retry_on_timeout": False},
        )
        with app.connection_for_write() as connection:
            connection.ensure_connection(max_retries=0, timeout=timeout)
            sending = True
            app.send_task(task, args=arguments, task_id=task_id, queue=TASK_QUEUE,
                          serializer="json", retry=False, ignore_result=True,
                          connection=connection)
        return task_id
    except Exception:
        # Never disclose transport exceptions/credentials or retry ambiguous sends.
        raise PublicationError(uncertain=sending, task_id=task_id) from None
    finally:
        if app is not None:
            # The connection context above owns transport cleanup. Closing the
            # app's local pool must not erase the classified publication outcome.
            try:
                app.close()
            except Exception:
                pass


async def publish_task(task: str, arguments: list[str], settings: Settings) -> str:
    # No wait_for around this thread: cancellation would not stop a live send and
    # could falsely finalize a submission. Transport operations have finite waits.
    return await run_in_threadpool(_publish, task, arguments, settings)
