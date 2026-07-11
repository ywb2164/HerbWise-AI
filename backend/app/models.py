"""Central SQLAlchemy model registry.

Import this module before reading ``Base.metadata`` so every mapped table is
registered on the single project-wide Base from ``app.core.database``.
"""

from app.modules.profiles import models as profile_models  # noqa: F401
from app.modules.resources import models as resource_models  # noqa: F401
from app.modules.tasks import models as task_models  # noqa: F401
from app.modules.traces import models as trace_models  # noqa: F401
