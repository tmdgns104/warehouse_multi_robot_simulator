# UI and Visual Contract

## General

- Design coordinate space is 1280×720; right operations panel starts near x=990.
- Bright facility background, thin driving rails, small Robot geometry.
- Drivable rail comes from SafeLaneGraph; visual-only structures use a distinct style.
- Text accompanies mission colors; do not encode meaning with color alone.
- Normal mode explains business flow; debug may add nodes, reservations, buffers and traces.

## Warehouse V5.6.1

Window title: `Warehouse Multi-Robot Inventory Digital Twin - V5.6.1`.

Three read-only overlay zones: Receiving left, Storage/Rack center, Outbound/Shipping right. Every
`InventoryLocation` has one card showing exact ID and `occupied/capacity`. Every visible box comes
from `warehouse_box_views()` and uses `<SKU suffix><last two item digits>` (A02/B05/C11). Display
anchors in `WAREHOUSE_LOCATION_ANCHORS` are visual only and never service nodes/obstacles.

Robot row priority: `robot_id`, Work (`PUTAWAY`/`PICKING`/`AVAILABLE`), human Phase, Item suffix,
source→destination. Raw MOVING/SERVICE must not lead warehouse rows. Cargo is shown only when the
matching MaterialLoad is ON_ROBOT and owned by that Robot.

Clicking a Robot selects it. Detail must show Robot, Work, Phase, Item, SKU, Lot, From, To, Order and
Cargo. Highlight `entity.route[entity.route_index:]`; never compute a display-only route.

Shipping removal is not animation: SHIPPED Item leaves staging contents, therefore no BoxView exists.

## Production V5.5

Window title: `Warehouse Multi-Robot Factory - V5.5`. Show WorkOrders, production/starvation/blocking,
mission active/done counts and all 16 Robots. Badges: SUPPLY, WIP, QC, OUT plus operational activity.
Selected detail shows Mission/State/Lifecycle/Cargo/WO/Lot/Request/Task/endpoints/priority/reason.

## Controls

Space pause/start; R reset; N nodes; P routes; T reservations; I entity IDs; D debug; Q/Escape quit;
left click selects production/warehouse Robot.

## Rendering invariant

Pillow evidence and pygame consume the same actual domain/view state. Rendering cannot call update,
allocate, dispatch, random selection or mutate route/index/location/contents.
