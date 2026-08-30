from warehouse_sim.facility_layout import EntityShape, NetworkSegment
from warehouse_sim.reference_scenario import create_reference_layout
from warehouse_sim.render_plan import Primitive, build_render_plan


def test_reference_layout_matches_video_structure():
    layout = create_reference_layout()
    assert (layout.design_width, layout.design_height) == (1280, 720)
    assert layout.aspect_ratio == 16 / 9
    assert len(layout.machines) == 18
    assert len([station for station in layout.stations if station.id.startswith("top_")]) == 8
    assert len(layout.network) >= 40
    assert {entity.shape for entity in layout.entities} == {
        EntityShape.RECTANGLE,
        EntityShape.CIRCLE,
        EntityShape.DIAMOND,
    }


def test_layout_ids_are_unique_and_data_is_valid():
    layout = create_reference_layout()
    layout.validate()
    collections = (layout.zones, layout.machines, layout.stations, layout.network, layout.entities)
    identifiers = [item.id for collection in collections for item in collection]
    assert len(identifiers) == len(set(identifiers))


def test_network_rejects_diagonal_segments():
    try:
        NetworkSegment("diagonal", (0, 0), (1, 1))
    except ValueError as error:
        assert "orthogonal" in str(error)
    else:
        raise AssertionError("diagonal network segment should fail")


def test_render_plan_is_backend_neutral_and_layered():
    layout = create_reference_layout()
    plan = build_render_plan(layout)
    assert plan[0].primitive == Primitive.RECT
    assert any(command.primitive == Primitive.LINE for command in plan)
    assert any(command.primitive == Primitive.CIRCLE for command in plan)
    assert any(command.primitive == Primitive.DIAMOND for command in plan)
    assert len(plan) > len(layout.network) + len(layout.entities)
