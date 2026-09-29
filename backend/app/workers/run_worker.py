"""Worker entrypoint that pays the expensive imports once, before forking.

RQ runs each job in a forked child, and a fork inherits whatever the parent has
already imported. The provider is built lazily inside the job (so that the API
process never imports an SDK it does not use), which meant every child imported
the Google SDK from scratch.

Measured on the project machine: importing google.genai takes ~44s, while
building the client afterwards is free. A document only spends ~17s actually
talking to the model, so that import was the single largest cost of processing
a document -- larger than every model call combined.

Warming it here moves it out of the per-job path: the parent imports it once at
startup and every job after that inherits it.
"""

import logging

from redis import Redis
from rq import Queue, Worker

from app.core.config import settings
from app.services.ai import get_ai_provider
from app.workers.queue import JOB_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

QUEUE_NAME = "studymate"


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    try:
        get_ai_provider()
        logger.info("AI provider warmed; jobs will not pay the SDK import")
    except Exception as exc:  # noqa: BLE001
        # Not fatal: without this the first job in each fork simply pays the
        # import cost, exactly as it did before. Refusing to start would take
        # the whole queue down over a cost optimisation.
        logger.warning("Could not warm the AI provider (%s); continuing", exc)

    connection = Redis.from_url(settings.redis_url)
    queue = Queue(QUEUE_NAME, connection=connection, default_timeout=JOB_TIMEOUT_SECONDS)
    Worker([queue], connection=connection).work()


if __name__ == "__main__":
    main()
