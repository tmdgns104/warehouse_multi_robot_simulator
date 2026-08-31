"""Read-only display projections for the V5.6 warehouse scenario."""
from dataclasses import dataclass
from .task_manager import LoadState, RobotWorkState
from .warehouse import WarehouseRequestType

@dataclass(frozen=True)
class WarehouseRobotView:
    robot_id:str; operational_state:str; mission:str|None=None; phase:str="AVAILABLE"; item_id:str|None=None
    sku:str|None=None; lot_id:str|None=None; source:str|None=None; destination:str|None=None
    order_id:str|None=None; request_id:str|None=None; task_id:str|None=None; has_cargo:bool=False
    route_node_ids:tuple[str,...]=(); source_node_id:str|None=None; destination_node_id:str|None=None

@dataclass(frozen=True)
class WarehouseBoxView:
    item_id:str; label:str; sku:str; lot_id:str; location:str

def warehouse_robot_view(engine,robot_id):
    tid=engine.robot_tasks[robot_id]; operational=engine.activity_states[robot_id].value
    if not tid:return WarehouseRobotView(robot_id,operational,phase="AVAILABLE")
    task=engine.factory.task_manager.tasks[tid]; req=engine.requests.get(task.transport_request_id)
    if not req:return WarehouseRobotView(robot_id,operational,task_id=tid)
    item=engine.items[req.item_id]; load=engine.factory.task_manager.loads[task.load_id]
    cargo=load.state==LoadState.ON_ROBOT and load.carried_by_robot_id==robot_id
    work=engine.work_states[robot_id]
    if work==RobotWorkState.PICKING: phase="PICKING ITEM"
    elif work==RobotWorkState.DROPPING: phase="DROPPING ITEM"
    elif operational=="TRAFFIC_WAIT": phase="TRAFFIC WAIT"
    elif operational=="RESOURCE_WAIT": phase="RESOURCE WAIT"
    elif operational=="HOLDING": phase="HOLD"
    elif cargo: phase="CARRYING"
    else: phase="TO PICKUP"
    entity=next(e for e in engine.entities if e.id==robot_id)
    source=(engine.receiving.get(req.source) or engine.storage.get(req.source))
    destination=engine.storage.get(req.destination) or engine.staging.get(req.destination)
    return WarehouseRobotView(robot_id,operational,"PUTAWAY" if req.request_type==WarehouseRequestType.PUTAWAY else "PICKING",phase,
        item.id,item.sku,item.lot_id,req.source,req.destination,req.outbound_order_id or req.inbound_order_id,
        req.id,task.id,cargo,tuple(entity.route[entity.route_index:]),
        engine.stations[source.station_id].service_node_id,engine.stations[destination.station_id].service_node_id)

def warehouse_robot_views(engine): return tuple(warehouse_robot_view(engine,e.id) for e in engine.entities)

def warehouse_box_views(engine):
    result=[]
    for location in (*engine.receiving.values(),*engine.storage.values(),*engine.staging.values()):
        for iid in location.contents:
            item=engine.items[iid]; result.append(WarehouseBoxView(iid,f"{item.sku[-1]}{iid[-2:]}",item.sku,item.lot_id,location.id))
    return tuple(result)


WAREHOUSE_LOCATION_ANCHORS={
    "RECV_A":(275,245),"RECV_B":(275,485),
    "RACK-A01":(425,245),"RACK-A02":(555,245),"RACK-A03":(685,245),
    "RACK-B01":(425,485),"RACK-B02":(555,485),"RACK-B03":(685,485),
    "OUT_STAGE_A":(835,245),"OUT_STAGE_B":(835,485),
}
