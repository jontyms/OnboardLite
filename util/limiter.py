import time
from functools import wraps

import redis
from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, redis_host: str, redis_port: int, db: int):
        self.redis_pool = redis.ConnectionPool(
            host=redis_host, port=redis_port, db=db, decode_responses=True
        )

    def get_redis(self):
        return redis.Redis(connection_pool=self.redis_pool)

    def is_rate_limited(self, key: str, max_requests: int, window: int) -> bool:
        current = int(time.time())
        window_start = current - window
        redis_conn = self.get_redis()
        with redis_conn.pipeline() as pipe:
            try:
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zcard(key)
                pipe.zadd(key, {current: current})
                pipe.expire(key, window)
                results = pipe.execute()
            except redis.RedisError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Redis error: {str(e)}",
                ) from e
        return results[1] > max_requests

    def rate_limit(self, max_requests: int, window: int, request_path: str):
        def decorator(func):
            @wraps(func)
            async def wrapper(request: Request, payload, *args, **kwargs):
                payload = args[0]
                user_id = payload.get("id")
                if user_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User ID not found in payload",
                    )
                key = f"rate_limit:{user_id}:{request_path}"
                if self.is_rate_limited(key, max_requests, window):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests",
                    )
                return await func(request=request, payload=payload, **kwargs)

            return wrapper

        return decorator
