import binascii
import datetime
import hashlib
import os

from vj4 import db
from vj4.util import argmethod

TYPE_REGISTRATION = 1
TYPE_SAVED_SESSION = 2
TYPE_UNSAVED_SESSION = 3
TYPE_ACTIVATION = 4


def _get_id(id_binary):
  return hashlib.sha256(id_binary).digest()


@argmethod.wrap
async def add(token_type: int, expire_seconds: int, **kwargs):
  """Add a token.

  Args:
    token_type: type of the token.
    expire_seconds: expire time, in seconds.
    **kwargs: extra data.

  Returns:
    Tuple of (token ID, token document).
  """
  id_binary = hashlib.sha256(os.urandom(32)).digest()
  now = datetime.datetime.utcnow()
  doc = {**kwargs,
         '_id': _get_id(id_binary),
         'token_type': token_type,
         'create_at': now,
         'update_at': now,
         'expire_at': now + datetime.timedelta(seconds=expire_seconds)}
  coll = db.Collection('token')
  await coll.insert(doc)
  return binascii.hexlify(id_binary).decode(), doc


@argmethod.wrap
async def get(token_id: str, token_type: int):
  """Get a token.

  Args:
    token_id: token ID.
    token_type: type of the token.

  Returns:
    The token document, or None.
  """
  id_binary = binascii.unhexlify(token_id)
  coll = db.Collection('token')
  doc = await coll.find_one({'_id': _get_id(id_binary), 'token_type': token_type})
  return doc


@argmethod.wrap
async def get_most_recent_session_by_uid(uid: int):
  """Get the most recent session by uid."""
  coll = db.Collection('token')
  doc = await coll.find_one({'uid': uid,
                             'token_type': {'$in': [TYPE_SAVED_SESSION, TYPE_UNSAVED_SESSION]}},
                            sort=[('update_at', -1)])
  return doc


@argmethod.wrap
async def get_session_list_by_uid(uid: int):
  """Get the session list by uid."""
  coll = db.Collection('token')
  return await coll.find({'uid': uid,
                          'token_type': {'$in': [TYPE_SAVED_SESSION, TYPE_UNSAVED_SESSION]}},
                         sort=[('create_at', 1)]).to_list(None)


@argmethod.wrap
async def update(token_id: str, token_type: int, expire_seconds: int, **kwargs):
  """Update a token.

  Args:
    token_id: token ID.
    token_type: type of the token.
    expire_seconds: expire time, in seconds.
    **kwargs: extra data.

  Returns:
    The token document, or None.
  """
  id_binary = binascii.unhexlify(token_id)
  coll = db.Collection('token')
  assert 'token_type' not in kwargs
  now = datetime.datetime.utcnow()
  doc = await coll.find_and_modify(
    query={'_id': _get_id(id_binary), 'token_type': token_type},
    update={'$set': {**kwargs,
                     'update_at': now,
                     'expire_at': now + datetime.timedelta(seconds=expire_seconds)}},
    new=True)
  return doc


@argmethod.wrap
async def delete(token_id: str, token_type: int):
  """Delete a token.

  Args:
    token_id: token ID.
    token_type: type of the token.

  Returns:
    True if deleted, or False.
  """
  return await delete_by_hashed_id(_get_id(binascii.unhexlify(token_id)), token_type)


@argmethod.wrap
async def delete_by_hashed_id(hashed_id: str, token_type: int):
  """Delete a token by the hashed ID."""
  coll = db.Collection('token')
  doc = await coll.remove({'_id': hashed_id, 'token_type': token_type})
  return bool(doc['n'])


@argmethod.wrap
async def delete_by_uid(uid: int):
  """Delete all tokens by uid."""
  coll = db.Collection('token')
  doc = await coll.remove({'uid': uid,
                           'token_type': {'$in': [TYPE_SAVED_SESSION, TYPE_UNSAVED_SESSION]}})
  return bool(doc['n'])


@argmethod.wrap
async def ensure_indexes():
  coll = db.Collection('token')
  await coll.ensure_index([('uid', 1), ('token_type', 1), ('update_at', -1)], sparse=True)
  await coll.ensure_index('expire_at', expireAfterSeconds=0)


if __name__ == '__main__':
  argmethod.invoke_by_args()
