from dataclasses import dataclass
from .factory import FactoryConfig
from .reference_factory_scenario import create_reference_factory_scenario
from .warehouse import WarehouseEngine

@dataclass(frozen=True)
class ReferenceWarehouseScenario:
    layout: object; graph: object; engine: WarehouseEngine

def create_reference_warehouse_scenario(entity_count=16,*,seed=1234):
    base=create_reference_factory_scenario(entity_count,seed=seed,config=FactoryConfig(queue_target=0,max_active_tasks=entity_count,engagement_warmup=10,balance_workload=False,park_when_empty=False))
    return ReferenceWarehouseScenario(base.layout,base.graph,WarehouseEngine(base.engine))
