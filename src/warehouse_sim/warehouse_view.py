"""Read-only display projections for the V5.6 warehouse scenario."""
from dataclasses import dataclass
from .task_manager import LoadState
from .warehouse import WarehouseRequestType

@dataclass(frozen=True)
class WarehouseRobotView:
    robot_id:str; operational_state:str; mission:str|None=None; item_id:str|None=None
    sku:str|None=None; lot_id:str|None=None; source:str|None=None; destination:str|None=None
    order_id:str|None=None; request_id:str|None=None; task_id:str|None=None; has_cargo:bool=False

@dataclass(frozen=True)
class WarehouseBoxView:
    item_id:str; label:str; sku:str; lot_id:str; location:str

def warehouse_robot_view(engine,robot_id):
    tid=engine.robot_tasks[robot_id]; operational=engine.activity_states[robot_id].value
    if not tid:return WarehouseRobotView(robot_id,operational)
    task=engine.factory.task_manager.tasks[tid]; req=engine.requests.get(task.transport_request_id)
    if not req:return WarehouseRobotView(robot_id,operational,task_id=tid)
    item=engine.items[req.item_id]; load=engine.factory.task_manager.loads[task.load_id]
    return WarehouseRobotView(robot_id,operational,"PUT" if req.request_type==WarehouseRequestType.PUTAWAY else "PICK",
        item.id,item.sku,item.lot_id,req.source,req.destination,req.outbound_order_id or req.inbound_order_id,
        req.id,task.id,load.state==LoadState.ON_ROBOT and load.carried_by_robot_id==robot_id)

def warehouse_robot_views(engine): return tuple(warehouse_robot_view(engine,e.id) for e in engine.entities)

def warehouse_box_views(engine):
    result=[]
    for location in (*engine.receiving.values(),*engine.storage.values(),*engine.staging.values()):
        for iid in location.contents:
            item=engine.items[iid]; result.append(WarehouseBoxView(iid,f"{item.sku[-1]}{iid[-2:]}",item.sku,item.lot_id,location.id))
    return tuple(result)
