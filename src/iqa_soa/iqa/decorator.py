"""Non-invasive interception facade around the Service Gateway."""

from __future__ import annotations

from collections.abc import Callable

from iqa_soa.iqa.gateway import ServiceGateway
from iqa_soa.types import Action, GatewayOutcome, RuntimeContext


class ServiceDecorator:
    """Expose a tool-like executor while routing every action through IQA-SOA."""

    def __init__(self, gateway: ServiceGateway) -> None:
        self.gateway = gateway

    def execute(self, action: Action, context: RuntimeContext) -> GatewayOutcome:
        return self.gateway.execute(action, context)

    def __call__(self, action: Action, context: RuntimeContext) -> GatewayOutcome:
        return self.execute(action, context)

    def wrap(
        self, proposer: Callable[..., Action]
    ) -> Callable[..., GatewayOutcome]:
        """Wrap an arbitrary action-producing callable without changing its code.

        The returned function requires ``context=RuntimeContext`` and forwards all
        other arguments to the original action producer.
        """

        def governed(*args: object, context: RuntimeContext, **kwargs: object) -> GatewayOutcome:
            action = proposer(*args, **kwargs)
            if not isinstance(action, Action):
                raise TypeError("decorated callable must return Action")
            return self.execute(action, context)

        return governed


__all__ = ["ServiceDecorator"]
