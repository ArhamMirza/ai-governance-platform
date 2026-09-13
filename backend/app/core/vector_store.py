"""Loading sqlite-vec, and coping when it cannot be loaded.

The vector index lives in the same SQLite file as everything else, which is
what keeps document search from needing a second service to deploy. The
price is that it arrives as a loadable extension, and some Python builds
ship with extension loading compiled out.

So this module never assumes. It reports whether vectors are available, and
retrieval falls back to keyword search alone when they are not -- degraded,
still useful, and honest about which mode it is in, rather than a stack
trace on a machine that was fine yesterday.
"""

import sqlite3
import struct
from functools import lru_cache

from sqlalchemy import Engine, event

# BAAI/bge-small-en-v1.5, the model app.core.embeddings loads.
EMBEDDING_DIMENSIONS = 384


def serialize(vector: list[float]) -> bytes:
    """The packed float32 form sqlite-vec stores and matches on."""
    return struct.pack(f"{len(vector)}f", *vector)


def _load_into(connection: sqlite3.Connection) -> bool:
    try:
        import sqlite_vec
    except ImportError:
        return False
    try:
        connection.enable_load_extension(True)
    except AttributeError:
        # Python built without extension support.
        return False
    try:
        sqlite_vec.load(connection)
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        try:
            connection.enable_load_extension(False)
        except AttributeError:
            pass


@lru_cache(maxsize=1)
def vectors_available() -> bool:
    """Whether this machine can do vector search at all.

    Answered once, on a throwaway connection, so the check never depends on
    the state of a connection someone else is using.
    """
    probe = sqlite3.connect(":memory:")
    try:
        if not _load_into(probe):
            return False
        probe.execute("SELECT vec_version()")
        return True
    except sqlite3.Error:
        return False
    finally:
        probe.close()


def register(engine: Engine) -> None:
    """Load the extension into every connection this engine opens.

    An extension is per-connection, and the pool hands out several, so this
    has to happen on connect rather than once at startup.
    """
    if not engine.url.get_backend_name().startswith("sqlite"):
        return

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection, _record) -> None:  # noqa: ANN001
        _load_into(dbapi_connection)
