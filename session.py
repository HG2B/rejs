import jwt
import secrets
import os
import redis
import pickle
from typing import Optional

class Session:
    user_id = None
    session_id = None
    data = None
    jwt = None
    system_data = None

    def __init__(self, jwt: Optional[str]=None):
        self.jwt = jwt

    def _set_redis_system_data(self, system_data:str=""):
        if self.user_id:
            # Serialize the system data
            serialized_data = pickle.dumps(system_data)
            redis.set(f"session:{self.session_id}:{self.user_id}", serialized_data)

    def _get_redis_system_data(self):
        if self.user_id:
            # Deserialize the system data
            serialized_data = redis.get(f"session:{self.session_id}:{self.user_id}")
            if serialized_data:
                return pickle.loads(serialized_data)
        return None

    def is_valid(self):
        if not self.jwt:
            return False
        try:
            payload = jwt.decode(self.jwt, os.getenv("JWT_SECRET", "secret"), algorithms=['HS256'])
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

    def create(self, user_id: int, data: dict, system_data: dict):
        self.user_id = user_id
        self.data = data
        self.session_id = secrets.token_urlsafe(16)
        self.jwt = jwt.encode({
            'user_id': user_id,
            'session_id': self.session_id,
            'data': data
        }, os.getenv("JWT_SECRET", "secret"), algorithm='HS256')
        self._set_redis_system_data(system_data)
        return True

    def get_jwt_string():
        return self.jwt
