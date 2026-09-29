from redis import Redis
from rq import Queue

from app.core.config import settings

# RQ's default is 180s, which a real document can exceed: a lecture PDF costs
# several sequential model calls, and on free-tier capacity each one can take
# ten seconds or more before a model answers. Jobs were being killed mid-run and
# reported to the student as a failure when nothing was actually wrong.
JOB_TIMEOUT_SECONDS = 900

redis_conn = Redis.from_url(settings.redis_url)
queue = Queue("studymate", connection=redis_conn, default_timeout=JOB_TIMEOUT_SECONDS)
