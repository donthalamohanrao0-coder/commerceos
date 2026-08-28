"""Single import point that pulls every ORM model into ``Base.metadata``.

Cross-domain foreign keys (e.g. ``carts.agent_session_id`` -> ``agent_sessions.id``)
are declared as string targets, so SQLAlchemy can only resolve them once *every*
model module has been imported into the shared registry. Importing this module
guarantees that. It is imported for its side effects only.

Keep this list in sync with ``db/migrations/env.py``.
"""

from app.agent_commerce import models as agent_commerce_models  # noqa: F401
from app.agents import models as agent_models  # noqa: F401
from app.approvals import models as approval_models  # noqa: F401
from app.audit import models as audit_models  # noqa: F401
from app.core import idempotency_models  # noqa: F401
from app.domains.campaigns import models as campaigns_models  # noqa: F401
from app.domains.cart import models as cart_models  # noqa: F401
from app.domains.catalog import models as catalog_models  # noqa: F401
from app.domains.customers import models as customers_models  # noqa: F401
from app.domains.merchants import models as merchants_models  # noqa: F401
from app.domains.orders import models as orders_models  # noqa: F401
from app.domains.payments import models as payments_models  # noqa: F401
from app.knowledge import models as knowledge_models  # noqa: F401
from app.policies import models as policy_models  # noqa: F401
from app.webhooks import models as webhook_models  # noqa: F401
