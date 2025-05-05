import jwt
import secrets
import os
import redis
import pickle
from typing import Optional, Dict
from rejs import config
import datetime

class RedisPool:
    '''Class for managing a pool of Redis connections.'''
    pool = []
    next = 0

    @staticmethod
    def create_connection():
        '''Create a new Redis connection.'''
        return redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)

    @staticmethod
    def get_connection() -> redis.Redis:
        if not len(RedisPool.pool):
            for _ in range(10):
                RedisPool.pool.append(RedisPool.create_connection())
        conn = RedisPool.pool[RedisPool.next % len(RedisPool.pool)]
        if not conn.ping():
            conn = RedisPool.pool.append(RedisPool.create_connection())
            RedisPool.pool[RedisPool.next] = conn
            RedisPool.next = (RedisPool.next + 1) % 10
        return conn

class Session:
    def __init__(self, jwt_string: Optional[str]=None):
        self.jwt = jwt_string
        if not self.is_valid():
            self.system_data = {}

    def _set_redis_system_data(self, system_data: Dict[str, str], exp: int=config.JWT_EXPIRATION):
        redis = RedisPool().get_connection()
        if self.user_id:
            # Serialize the system data
            serialized_data = pickle.dumps(system_data)
            redis.set(f"session:{self.session_id}:{self.user_id}", serialized_data, ex=exp)
            self.system_data = system_data
        else:
            raise ValueError("User ID is not set")

    def _get_redis_system_data(self):
        redis = RedisPool().get_connection()
        if self.user_id:
            # Deserialize the system data
            serialized_data = redis.get(f"session:{self.session_id}:{self.user_id}")
            if serialized_data:
                return pickle.loads(serialized_data)
        else:
            raise ValueError("User ID is not set")
        return None

    def is_valid(self):
        if not self.jwt:
            return False
        try:
            payload = jwt.decode(self.jwt, config.JWT_SECRET, algorithms=['HS256'])
            self.user_id = payload['user_id']
            self.session_id = payload['session_id']
            self.data = payload['data']
            self.system_data = self._get_redis_system_data()
            if not self.system_data:
                return False
            return True
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False

    def create(self, user_id: str, data: Dict[str,str], system_data: Dict[str,str], exp: int=config.JWT_EXPIRATION):
        self.user_id = user_id
        self.data = data
        self.session_id = secrets.token_urlsafe(16)

        current_utc = datetime.datetime.now(datetime.timezone.utc)
        future_utc = current_utc + datetime.timedelta(seconds=exp)
        self.expires_at = future_utc
        self.jwt = jwt.encode({
            'exp': self.expires_at,
            'iss': config.JWT_ISSUER,
            'user_id': user_id,
            'session_id': self.session_id,
            'data': data
        }, os.getenv("JWT_SECRET", "secret"), algorithm='HS256')
        self._set_redis_system_data(system_data, exp)
        return True

    def update(self, system_data: Dict[str, str]):
        # Calculate the expiration time, based on the self.expires_at
        # The idea is to not extend the expiration time. So, we want
        # to keep the expiration time the same as the current one.
        # The final result is the expiration time in seconds (int)
        exp = int((self.expires_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
        self._set_redis_system_data(system_data, exp)

    def get_jwt_string(self):
        return self.jwt

    def __str__(self) -> str:
        return str(self.jwt)
