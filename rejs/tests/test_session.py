import sys
import time
import pickle

# Add the sys.path.append
from quopri import decode


print(sys.path)

user_id = "123456"

from session import Session, RedisPool

# Let's create a simple test
def test_session_creation():
    session = Session()
    assert session is not None

# Let's create a session with a system_data
def test_session_creation_with_system_data():
    data = {'key': 'value'}
    session = Session()
    system_data = { "system": "data"}
    session.create(user_id=user_id, data=data, system_data=system_data)

    assert session.session_id is not None
    assert session.user_id == user_id
    assert session.system_data == system_data
    assert session.data == data

def test_session_recovery():
    session1 = Session()
    data = {'key': 'value'}
    system_data = { "system": "data"}
    session1.create(user_id=user_id, data=data, system_data=system_data)

    session2 = Session(session1.get_jwt_string())

    assert session1.data == session2.data
    assert session1.user_id == session2.user_id
    assert session1.system_data == session2.system_data
    assert session1.session_id == session2.session_id

    # Get redis connection to check if the key is expired
    redis = RedisPool.get_connection()
    data = pickle.loads(redis.get(f"session:{session1.session_id}:{session1.user_id}"))

    assert data == system_data


def test_session_recovery_expired_token():
    session1 = Session()
    data = {'key': 'value'}
    system_data = { "system": "data"}
    session1.create(user_id=user_id, data=data, system_data=system_data, exp=1)

    # Sleep 2 seconds
    time.sleep(2)
    session2 = Session(session1.get_jwt_string())

    assert not hasattr(session2, 'data')
    assert session2.system_data == {}
    assert not hasattr(session2, 'user_id')
    assert not hasattr(session2, 'session_id')

    # Get redis connection to check if the key is expired
    redis = RedisPool.get_connection()
    data = redis.get(f"session:{session1.session_id}:{session1.user_id}")

    assert data is None

def test_session_recovery_token_with_update():
    session1 = Session()
    data = {'key': 'value'}
    system_data = { "system": "data"}
    session1.create(user_id=user_id, data=data, system_data=system_data, exp=12)

    # Sleep 2 seconds
    time.sleep(5)
    new_system_data = { "system": "new data"}
    session1.update(system_data=new_system_data)
    time.sleep(5)

    session2 = Session(session1.get_jwt_string())

    assert session1.data == session2.data
    assert session1.user_id == session2.user_id
    assert session1.system_data == new_system_data
    assert session1.session_id == session2.session_id

    # Get redis connection to check if the key is expired
    redis = RedisPool.get_connection()
    data = pickle.loads(redis.get(f"session:{session1.session_id}:{session1.user_id}"))

    assert data == new_system_data



def test_session_recovery_expired_token_with_update():
    session1 = Session()
    data = {'key': 'value'}
    system_data = { "system": "data"}
    session1.create(user_id=user_id, data=data, system_data=system_data, exp=10)

    # Sleep 2 seconds
    time.sleep(5)
    new_system_data = { "system": "new data"}
    session1.update(system_data=new_system_data)
    time.sleep(5)

    session2 = Session(session1.get_jwt_string())

    assert not hasattr(session2, 'data')
    assert session2.system_data == {}
    assert not hasattr(session2, 'user_id')
    assert not hasattr(session2, 'session_id')

    # Get redis connection to check if the key is expired
    redis = RedisPool.get_connection()
    data = redis.get(f"session:{session1.session_id}:{session1.user_id}")

    assert data is None
