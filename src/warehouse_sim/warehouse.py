"""Deterministic inbound, inventory, picking, and shipping lifecycle."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .factory import FactoryEngine
from .task_manager import LoadState, MaterialLoad, MaterialTask, TaskState


class InventoryState(str, Enum):
    EXPECTED="EXPECTED"; WAITING_PUTAWAY="WAITING_PUTAWAY"; IN_TRANSIT="IN_TRANSIT"
    STORED="STORED"; RESERVED_FOR_PICK="RESERVED_FOR_PICK"; OUTBOUND_STAGING="OUTBOUND_STAGING"; SHIPPED="SHIPPED"


class WarehouseRequestType(str, Enum):
    PUTAWAY="PUTAWAY"; PICKING="PICKING"


class WarehouseRequestState(str, Enum):
    OPEN="OPEN"; ASSIGNED="ASSIGNED"; IN_PROGRESS="IN_PROGRESS"; COMPLETED="COMPLETED"


class InboundState(str, Enum):
    PLANNED="PLANNED"; WAITING_DOCK="WAITING_DOCK"; PUTAWAY_IN_PROGRESS="PUTAWAY_IN_PROGRESS"; COMPLETED="COMPLETED"


class OutboundState(str, Enum):
    OPEN="OPEN"; WAITING_INVENTORY="WAITING_INVENTORY"; PICKING="PICKING"; READY_TO_SHIP="READY_TO_SHIP"; SHIPPED="SHIPPED"


@dataclass
class InventoryItem:
    id: str; sku: str; lot_id: str; inbound_order_id: str; arrival_time: float
    state: InventoryState = InventoryState.EXPECTED
    current_location: str | None = None
    outbound_order_id: str | None = None
    active_request_id: str | None = None
    stored_time: float | None = None


@dataclass
class InventoryLocation:
    id: str; station_id: str; capacity: int; compatible_skus: tuple[str, ...] = ()
    contents: list[str] = field(default_factory=list)
    reservations: set[str] = field(default_factory=set)
    @property
    def occupied(self): return len(self.contents)
    @property
    def free(self): return self.capacity - self.occupied - len(self.reservations)
    def add(self, item_id):
        if item_id in self.contents or self.occupied >= self.capacity: raise ValueError("location capacity or duplicate")
        self.contents.append(item_id)
    def remove(self, item_id):
        if item_id not in self.contents: raise ValueError("item absent from location")
        self.contents.remove(item_id)
    def reserve(self, request_id):
        if self.free <= 0: return False
        self.reservations.add(request_id); return True
    def receive(self, request_id, item_id):
        if request_id not in self.reservations: raise ValueError("capacity not reserved")
        self.reservations.remove(request_id); self.add(item_id)


@dataclass
class InboundOrder:
    id: str; supplier: str; arrival_time: float; item_ids: tuple[str, ...]
    state: InboundState = InboundState.PLANNED
    received_time: float | None = None; completed_time: float | None = None


@dataclass
class OutboundOrder:
    id: str; customer: str; lines: dict[str, int]; created_time: float; due_time: float
    state: OutboundState = OutboundState.OPEN; allocated_items: list[str] = field(default_factory=list)
    ready_time: float | None = None; shipped_time: float | None = None


@dataclass
class WarehouseRequest:
    id: str; request_type: WarehouseRequestType; item_id: str; source: str; destination: str
    created_time: float; inbound_order_id: str | None = None; outbound_order_id: str | None = None
    state: WarehouseRequestState = WarehouseRequestState.OPEN; task_id: str | None = None
    assigned_time: float | None = None; completed_time: float | None = None


@dataclass(frozen=True)
class WarehouseEvent:
    time: float; event: str; item_id: str | None = None; robot_id: str | None = None
    request_id: str | None = None; order_id: str | None = None; location: str | None = None


@dataclass(frozen=True)
class WarehouseMetrics:
    inbound_items_arrived: int; putaway_completed: int; average_putaway_time: float
    inventory_total: int; inventory_capacity: int; inventory_occupancy_ratio: float
    outbound_orders_created: int; outbound_orders_shipped: int; outbound_items_shipped: int
    average_order_cycle_time: float; average_pick_time: float; backordered_items: int
    receiving_wait_count: int; outbound_staging_count: int; inventory_integrity_errors: int


class WarehouseEngine:
    """Creates business requests; FactoryEngine remains the Robot execution boundary."""
    def __init__(self, factory: FactoryEngine):
        self.factory=factory; self.elapsed_time=0.0; self.running=True; self.integrity_errors=0
        self.request_seq=self.task_seq=0; self.events=[]; self.requests={}; self.items={}
        self.receiving={"RECV_A":InventoryLocation("RECV_A","IN_A",8), "RECV_B":InventoryLocation("RECV_B","IN_B",8)}
        specs=(("RACK-A01","PROC_A",4,("SKU-A",)),("RACK-A02","QC_A",4,("SKU-A","SKU-C")),
               ("RACK-A03","PROC_A",4,("SKU-A","SKU-C")),("RACK-B01","PROC_B",4,("SKU-B",)),
               ("RACK-B02","BUFFER_B",4,("SKU-B","SKU-C")),("RACK-B03","PROC_B",4,("SKU-B","SKU-C")))
        self.storage={i:InventoryLocation(i,s,c,k) for i,s,c,k in specs}
        self.staging={"OUT_STAGE_A":InventoryLocation("OUT_STAGE_A","OUT_A",8),"OUT_STAGE_B":InventoryLocation("OUT_STAGE_B","OUT_B",8)}
        self.inbound_orders={}; self.outbound_orders={}; self._build_schedule()

    def __getattr__(self,name): return getattr(self.factory,name)
    @property
    def factory_metrics(self): return self.factory.factory_metrics

    def _event(self,event,item=None,robot=None,request=None,order=None,location=None):
        self.events.append(WarehouseEvent(self.elapsed_time,event,item,robot,request,order,location))

    def _build_schedule(self):
        batches=(("IB-001",0,"RECV_A",("SKU-A",)*4),("IB-002",30,"RECV_B",("SKU-B",)*4),("IB-003",60,"RECV_A",("SKU-C",)*4),
                 ("IB-004",120,"RECV_A",("SKU-A",)*3),("IB-005",180,"RECV_B",("SKU-B","SKU-C","SKU-C")))
        n=0
        for oid,at,dock,skus in batches:
            ids=[]
            for sku in skus:
                n+=1; iid=f"ITEM-{n:03d}"; ids.append(iid)
                self.items[iid]=InventoryItem(iid,sku,f"LOT-{sku[-1]}-{n:03d}",oid,at,current_location=dock)
            order=InboundOrder(oid,f"SUPPLIER-{oid[-1]}",at,tuple(ids)); order.dock=dock
            self.inbound_orders[oid]=order
        for oid,at,lines in (("SO-001",90,{"SKU-A":2}),("SO-002",150,{"SKU-B":2,"SKU-C":1}),("SO-003",210,{"SKU-A":2,"SKU-C":1})):
            self.outbound_orders[oid]=OutboundOrder(oid,f"CUSTOMER-{oid[-1]}",lines,at,at+100)

    def _choose_storage(self,sku):
        candidates=[loc for loc in self.storage.values() if sku in loc.compatible_skus and loc.free>0]
        return min(candidates,key=lambda loc:(not any(self.items[i].sku==sku for i in loc.contents),loc.id)) if candidates else None

    def _create_request(self,item,kind,source,dest,*,inbound=None,outbound=None):
        self.request_seq+=1; rid=f"WR-{self.request_seq:04d}"
        destination=(self.storage.get(dest) or self.staging.get(dest))
        if not destination.reserve(rid): self.request_seq-=1; return None
        request=WarehouseRequest(rid,kind,item.id,source,dest,self.elapsed_time,inbound,outbound)
        self.task_seq+=1; tid=f"JOB-W{self.task_seq:04d}"; request.task_id=tid; self.requests[rid]=request
        source_station=(self.receiving.get(source) or self.storage.get(source)).station_id
        dest_station=destination.station_id
        task=MaterialTask(tid,source_station,dest_station,f"LOAD-{rid}",2 if kind==WarehouseRequestType.PICKING else 1,
                          created_time=self.elapsed_time,transport_request_id=rid)
        self.factory.task_manager.create_task(task,MaterialLoad(task.load_id,LoadState.AT_SOURCE,source_station,None,tid))
        item.active_request_id=rid
        self._event("REQUESTED",item.id,request=rid,order=outbound or inbound,location=f"{source}>{dest}")
        return request

    def _arrive(self):
        for order in self.inbound_orders.values():
            if order.state!=InboundState.PLANNED or order.arrival_time>self.elapsed_time: continue
            dock=self.receiving[order.dock]
            if dock.free < len(order.item_ids): order.state=InboundState.WAITING_DOCK; continue
            order.state=InboundState.PUTAWAY_IN_PROGRESS; order.received_time=self.elapsed_time
            for iid in order.item_ids:
                item=self.items[iid]; item.state=InventoryState.WAITING_PUTAWAY; dock.add(iid)
                self._event("ARRIVED",iid,order=order.id,location=dock.id)
        for order in self.inbound_orders.values():
            if order.state==InboundState.WAITING_DOCK: order.state=InboundState.PLANNED

    def _putaway(self):
        for item in self.items.values():
            if item.state!=InventoryState.WAITING_PUTAWAY or item.active_request_id: continue
            location=self._choose_storage(item.sku)
            if location: self._create_request(item,WarehouseRequestType.PUTAWAY,item.current_location,location.id,inbound=item.inbound_order_id)

    def _allocate(self):
        for order in self.outbound_orders.values():
            if order.created_time>self.elapsed_time or order.state in {OutboundState.PICKING,OutboundState.READY_TO_SHIP,OutboundState.SHIPPED}: continue
            selected=[]
            for sku,qty in order.lines.items():
                available=sorted((i for i in self.items.values() if i.sku==sku and i.state==InventoryState.STORED and not i.outbound_order_id),key=lambda i:(i.stored_time,i.id))
                if len(available)<qty: selected=[]; break
                selected.extend(available[:qty])
            if not selected: order.state=OutboundState.WAITING_INVENTORY; continue
            order.state=OutboundState.PICKING
            stage="OUT_STAGE_A" if order.id in {"SO-001","SO-003"} else "OUT_STAGE_B"
            for item in selected:
                item.outbound_order_id=order.id; item.state=InventoryState.RESERVED_FOR_PICK; order.allocated_items.append(item.id)
                self._event("ALLOCATED",item.id,order=order.id,location=item.current_location)
                self._create_request(item,WarehouseRequestType.PICKING,item.current_location,stage,outbound=order.id)

    def _sync(self):
        for req in self.requests.values():
            task=self.factory.task_manager.tasks[req.task_id]; item=self.items[req.item_id]
            if task.assigned_time is not None and req.state==WarehouseRequestState.OPEN:
                req.state=WarehouseRequestState.ASSIGNED; req.assigned_time=task.assigned_time
            if task.pickup_time is not None and req.state in {WarehouseRequestState.OPEN,WarehouseRequestState.ASSIGNED}:
                req.state=WarehouseRequestState.IN_PROGRESS
                source=self.receiving.get(req.source) or self.storage.get(req.source); source.remove(item.id)
                item.current_location=None; item.state=InventoryState.IN_TRANSIT
                self._event("PICKED_UP",item.id,task.assigned_robot_id,req.id,req.outbound_order_id or req.inbound_order_id,req.source)
            if task.state==TaskState.COMPLETED and req.state!=WarehouseRequestState.COMPLETED:
                req.state=WarehouseRequestState.COMPLETED; req.completed_time=task.completed_time; item.active_request_id=None
                dest=self.storage.get(req.destination) or self.staging.get(req.destination); dest.receive(req.id,item.id); item.current_location=req.destination
                if req.request_type==WarehouseRequestType.PUTAWAY:
                    item.state=InventoryState.STORED; item.stored_time=self.elapsed_time
                    inbound=self.inbound_orders[item.inbound_order_id]
                    if all(self.items[i].state in {InventoryState.STORED,InventoryState.RESERVED_FOR_PICK,InventoryState.IN_TRANSIT,InventoryState.OUTBOUND_STAGING,InventoryState.SHIPPED} for i in inbound.item_ids):
                        inbound.state=InboundState.COMPLETED; inbound.completed_time=self.elapsed_time
                else: item.state=InventoryState.OUTBOUND_STAGING
                self._event("DROPPED",item.id,task.assigned_robot_id,req.id,req.outbound_order_id or req.inbound_order_id,req.destination)

    def _ship(self):
        for order in self.outbound_orders.values():
            if order.state==OutboundState.PICKING and order.allocated_items and all(self.items[i].state==InventoryState.OUTBOUND_STAGING for i in order.allocated_items):
                order.state=OutboundState.READY_TO_SHIP; order.ready_time=self.elapsed_time; self._event("READY",order=order.id)
            if order.state==OutboundState.READY_TO_SHIP and self.elapsed_time-order.ready_time>=5:
                for iid in order.allocated_items:
                    item=self.items[iid]; self.staging[item.current_location].remove(iid); item.current_location=None; item.state=InventoryState.SHIPPED
                    self._event("SHIPPED",iid,order=order.id)
                order.state=OutboundState.SHIPPED; order.shipped_time=self.elapsed_time

    def update(self,dt):
        if not self.running or dt==0:return
        self.elapsed_time=self.factory.elapsed_time
        self._arrive(); self._putaway(); self._allocate(); self.factory.update(dt); self.elapsed_time=self.factory.elapsed_time
        self._sync(); self._ship(); self.validate_inventory_integrity()

    def pause(self): self.running=False; self.factory.pause()
    def start(self): self.running=True; self.factory.start()
    def reset(self): self.factory.reset(); self.__init__(self.factory)
    def validate_safety(self): self.factory.validate_safety(); self.validate_inventory_integrity()
    def validate_inventory_integrity(self):
        found={}
        for loc in (*self.receiving.values(),*self.storage.values(),*self.staging.values()):
            if loc.occupied>loc.capacity: raise AssertionError("warehouse location overflow")
            for iid in loc.contents:
                if iid in found: raise AssertionError("duplicate item location")
                found[iid]=loc.id
        for item in self.items.values():
            if item.state in {InventoryState.STORED,InventoryState.WAITING_PUTAWAY,InventoryState.OUTBOUND_STAGING} and found.get(item.id)!=item.current_location: raise AssertionError("item location mismatch")
            if item.state in {InventoryState.IN_TRANSIT,InventoryState.SHIPPED} and item.id in found: raise AssertionError("transit/shipped item in location")

    @property
    def warehouse_metrics(self):
        arrived=[i for i in self.items.values() if i.state!=InventoryState.EXPECTED]
        put=[r for r in self.requests.values() if r.request_type==WarehouseRequestType.PUTAWAY and r.state==WarehouseRequestState.COMPLETED]
        picks=[r for r in self.requests.values() if r.request_type==WarehouseRequestType.PICKING and r.state==WarehouseRequestState.COMPLETED]
        stored=sum(i.state in {InventoryState.STORED,InventoryState.RESERVED_FOR_PICK} for i in self.items.values())
        shipped=sum(i.state==InventoryState.SHIPPED for i in self.items.values()); cap=sum(l.capacity for l in self.storage.values())
        shipped_orders=[o for o in self.outbound_orders.values() if o.state==OutboundState.SHIPPED]
        return WarehouseMetrics(len(arrived),len(put),sum(r.completed_time-r.created_time for r in put)/len(put) if put else 0,
            stored,cap,stored/cap,len([o for o in self.outbound_orders.values() if o.created_time<=self.elapsed_time]),len(shipped_orders),shipped,
            sum(o.shipped_time-o.created_time for o in shipped_orders)/len(shipped_orders) if shipped_orders else 0,
            sum(r.completed_time-r.created_time for r in picks)/len(picks) if picks else 0,
            sum(sum(o.lines.values()) for o in self.outbound_orders.values() if o.state==OutboundState.WAITING_INVENTORY),
            sum(i.state==InventoryState.WAITING_PUTAWAY for i in self.items.values()),sum(i.state==InventoryState.OUTBOUND_STAGING for i in self.items.values()),self.integrity_errors)

    def item_trace(self,item_id): return tuple(e for e in self.events if e.item_id==item_id or e.order_id==self.items[item_id].outbound_order_id)
