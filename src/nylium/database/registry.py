"""The single SQLAlchemy registry shared by mapped Row classes."""
from sqlalchemy.orm import registry

reg = registry()
