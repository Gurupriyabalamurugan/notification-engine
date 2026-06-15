from collections.abc import AsyncGenerator

import pytest

pytestmark = pytest.mark.usefixtures("migrated_db", "clean_tables")
