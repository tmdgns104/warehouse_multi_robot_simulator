"""Reference-derived layout with a synthetic deterministic manufacturing scenario."""
from __future__ import annotations

from dataclasses import dataclass

from .factory import FactoryConfig
from .production import ProductionEngine
from .reference_factory_scenario import create_reference_factory_scenario


@dataclass(frozen=True)
class ReferenceProductionScenario:
    layout: object
    graph: object
    engine: ProductionEngine


def create_reference_production_scenario(
    entity_count: int = 16, *, seed: int = 1234, target_per_product: int = 10,
) -> ReferenceProductionScenario:
    base = create_reference_factory_scenario(
        entity_count, seed=seed,
        config=FactoryConfig(queue_target=0, max_active_tasks=entity_count,
                             engagement_warmup=10.0, balance_workload=False,
                             park_when_empty=False),
    )
    engine = ProductionEngine(base.engine, target_per_product=target_per_product)
    return ReferenceProductionScenario(base.layout, base.graph, engine)
