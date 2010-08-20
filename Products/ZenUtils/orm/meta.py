from sqlalchemy import MetaData
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

__all__ = ['Session', 'metadata', 'Base']

engine = None
Session = scoped_session(sessionmaker())
metadata = MetaData()
Base = declarative_base(metadata=metadata)
