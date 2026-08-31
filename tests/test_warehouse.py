from pathlib import Path
import pytest
from warehouse_sim.reference_warehouse_scenario import create_reference_warehouse_scenario
from warehouse_sim.reference_renderer import render_warehouse_with_pillow
from warehouse_sim.task_manager import LoadState
from warehouse_sim.warehouse import InventoryLocation,InventoryState,InboundState,OutboundState,WarehouseRequestState,WarehouseRequestType
from warehouse_sim.warehouse_view import warehouse_box_views,warehouse_robot_views

def advance(engine,seconds,step=1/30):
    for _ in range(round(seconds/step)):engine.update(step)

def test_location_capacity_reservation_and_overbooking():
    loc=InventoryLocation("R","S",1)
    assert loc.reserve("WR1") and not loc.reserve("WR2")
    loc.receive("WR1","I1")
    assert loc.occupied==1 and loc.free==0
    with pytest.raises(ValueError):loc.add("I2")

def test_scheduled_inbound_arrives_to_finite_receiving():
    e=create_reference_warehouse_scenario(4).engine
    e.update(1/30)
    assert e.inbound_orders["IB-001"].state==InboundState.PUTAWAY_IN_PROGRESS
    assert e.receiving["RECV_A"].occupied==4
    assert all(e.items[i].state==InventoryState.WAITING_PUTAWAY for i in e.inbound_orders["IB-001"].item_ids)
    assert all(l.occupied<=l.capacity for l in e.receiving.values())

def test_putaway_location_policy_is_sku_compatible_and_stable():
    e=create_reference_warehouse_scenario(4).engine
    assert e._choose_storage("SKU-A").id=="RACK-A01"
    assert e._choose_storage("SKU-B").id=="RACK-B01"
    assert len(e.storage)>=6

def test_putaway_request_reuses_material_task_and_load():
    e=create_reference_warehouse_scenario(4).engine;e.update(1/30)
    req=next(iter(e.requests.values()));task=e.factory.task_manager.tasks[req.task_id]
    assert req.request_type==WarehouseRequestType.PUTAWAY
    assert task.transport_request_id==req.id
    assert e.factory.task_manager.loads[task.load_id].state in {LoadState.AT_SOURCE,LoadState.RESERVED}

def test_pickup_removes_item_from_location_and_gives_exact_robot_custody():
    e=create_reference_warehouse_scenario(8).engine
    for _ in range(4000):
        e.update(1/30)
        views=[v for v in warehouse_robot_views(e) if v.has_cargo]
        if views:break
    assert views
    v=views[0];item=e.items[v.item_id]
    assert item.state==InventoryState.IN_TRANSIT and item.current_location is None
    task=e.factory.task_manager.tasks[v.task_id]
    assert e.factory.task_manager.loads[task.load_id].carried_by_robot_id==v.robot_id

def test_storage_drop_increases_real_inventory_and_trace():
    e=create_reference_warehouse_scenario(8).engine;advance(e,100)
    stored=[i for i in e.items.values() if i.state in {InventoryState.STORED,InventoryState.RESERVED_FOR_PICK}]
    assert stored and all(i.current_location in e.storage for i in stored)
    trace=e.item_trace(stored[0].id)
    assert {x.event for x in trace}>={"ARRIVED","REQUESTED","PICKED_UP","DROPPED"}

def test_outbound_allocation_is_fifo_and_never_exceeds_available_inventory():
    e=create_reference_warehouse_scenario(16).engine;advance(e,100)
    order=e.outbound_orders["SO-001"]
    assert order.state in {OutboundState.PICKING,OutboundState.READY_TO_SHIP,OutboundState.SHIPPED}
    allocated=[e.items[i] for i in order.allocated_items]
    assert len(allocated)==2 and all(i.sku=="SKU-A" and i.outbound_order_id==order.id for i in allocated)
    assert [i.stored_time for i in allocated]==sorted(i.stored_time for i in allocated)

def test_insufficient_inventory_waits_without_creating_fake_items():
    e=create_reference_warehouse_scenario(4).engine;advance(e,91)
    before=len(e.items)
    assert e.outbound_orders["SO-001"].state in {OutboundState.WAITING_INVENTORY,OutboundState.PICKING}
    assert len(e.items)==before==18

def test_outbound_staging_is_capacity_bounded_and_shipping_removes_items():
    e=create_reference_warehouse_scenario(16).engine;advance(e,300,1/60)
    assert any(o.state==OutboundState.SHIPPED for o in e.outbound_orders.values())
    shipped=[i for i in e.items.values() if i.state==InventoryState.SHIPPED]
    assert shipped and all(i.current_location is None for i in shipped)
    assert all(i.id not in l.contents for i in shipped for l in (*e.storage.values(),*e.staging.values()))
    assert all(l.occupied<=l.capacity for l in e.staging.values())

def test_box_and_robot_views_are_exact_domain_projections():
    e=create_reference_warehouse_scenario(8).engine;advance(e,80)
    boxes=warehouse_box_views(e)
    expected=sum(l.occupied for l in (*e.receiving.values(),*e.storage.values(),*e.staging.values()))
    assert len(boxes)==expected
    assert all(box.item_id in (e.receiving.get(box.location) or e.storage.get(box.location) or e.staging.get(box.location)).contents for box in boxes)
    assert all(v.mission in {None,"PUT","PICK"} for v in warehouse_robot_views(e))

def test_renderer_does_not_mutate_inventory_state(tmp_path:Path):
    s=create_reference_warehouse_scenario(8);advance(s.engine,80)
    before=(s.engine.elapsed_time,s.engine.warehouse_metrics,tuple((i.id,i.state,i.current_location) for i in s.engine.items.values()))
    render_warehouse_with_pillow(s.layout,s.engine,tmp_path/"w.png",debug=True)
    after=(s.engine.elapsed_time,s.engine.warehouse_metrics,tuple((i.id,i.state,i.current_location) for i in s.engine.items.values()))
    assert before==after and (tmp_path/"w.png").stat().st_size>0

def test_same_seed_warehouse_replay_is_deterministic():
    a=create_reference_warehouse_scenario(8,seed=9).engine;b=create_reference_warehouse_scenario(8,seed=9).engine
    advance(a,120);advance(b,120)
    assert a.warehouse_metrics==b.warehouse_metrics
    assert [(e.event,e.item_id,e.robot_id) for e in a.events]==[(e.event,e.item_id,e.robot_id) for e in b.events]

def test_300_second_acceptance_integrity_and_traffic_safety():
    e=create_reference_warehouse_scenario(16,seed=1234).engine;advance(e,300,1/60);e.validate_safety()
    m=e.warehouse_metrics;t=e.factory.traffic.metrics
    assert m.inbound_items_arrived==18 and m.putaway_completed>=15
    assert m.outbound_orders_shipped>=1 and m.outbound_items_shipped>=2 and m.inventory_integrity_errors==0
    assert (t.head_on_conflict_count,t.deadlock_count,t.obstacle_penetration_count)==(0,0,0)
