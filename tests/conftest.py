import pytest

from afi_agent.afizi_mock import AfiziMock
from afi_agent.config import load_settings
from afi_agent.store import InMemoryStore
from afi_agent.tools import ToolContext


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore.from_file(load_settings().seed_path)


@pytest.fixture
def ctx(store: InMemoryStore) -> ToolContext:
    return ToolContext(store=store, afizi=AfiziMock(store))
