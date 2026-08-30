"""Deterministic reconstruction of the provided reference video's layout."""

from __future__ import annotations

from .facility_layout import (
    EntityShape,
    FacilityLayout,
    MachineBlock,
    MobileEntity,
    NetworkSegment,
    Station,
    Zone,
)


VISUAL_ONLY_NETWORK_COLOR = (172, 187, 196)


def _segment(identifier, x1, y1, x2, y2, width=1.0, drivable=True, color=(218, 133, 145)):
    return NetworkSegment(
        identifier, (x1, y1), (x2, y2), color=color, width=width, drivable=drivable
    )


def create_reference_layout() -> FacilityLayout:
    """Build the V2 layout from measurements of several video frames.

    Industrial meaning is deliberately not encoded.  Names describe visual
    position or appearance only.
    """
    zones = (
        Zone("canvas", "outer surround", 0, 0, 1280, 720, (183, 183, 183)),
        Zone("facility", "facility board", 210, 50, 765, 615, (252, 252, 249)),
        Zone("top_margin", "upper equipment area", 286, 112, 615, 105, (255, 255, 252)),
        Zone("center", "repeating facility area", 285, 216, 615, 330, (255, 255, 252)),
        Zone("bottom", "lower network area", 228, 555, 735, 95, (252, 252, 249)),
    )

    machines = []
    machine_x = (334, 429, 524, 640, 735, 830)
    machine_y = (234, 356, 478)
    for row, y in enumerate(machine_y):
        for column, x in enumerate(machine_x):
            family = "cyan" if row == 0 and column in (2, 3) else "blue"
            machines.append(MachineBlock(f"machine_{row}_{column}", x, y, family=family))

    stations = []
    top_colors = ((61, 145, 236), (75, 186, 219)) + ((71, 220, 220),) * 4 + ((65, 165, 221), (51, 127, 231))
    for index, (x, color) in enumerate(zip((302, 397, 489, 551, 613, 675, 764, 854), top_colors)):
        stations.append(Station(f"top_station_{index}", x, 136, 30, 26, color))
    for side, x in (("left", 239), ("right", 939)):
        for group, base_y in enumerate((211, 367)):
            for index in range(3):
                stations.append(Station(f"{side}_marker_{group}_{index}", x, base_y + index * 27, 12, 15, (65, 125, 31), "vertical"))

    network = []
    # Main horizontal corridors, including the dense lower return network.
    for index, y in enumerate((190, 219, 311, 343, 433, 462, 555, 588, 618, 648)):
        x1, x2 = (228, 963) if y >= 555 else (226, 962)
        network.append(_segment(f"horizontal_{index}", x1, y, x2, y, 1.15 if y >= 555 else 0.9))
    # Repeating vertical paths through the central machine rows.
    for index, x in enumerate((259, 289, 320, 365, 405, 460, 494, 555, 594, 625, 685, 716, 778, 808, 870, 900, 932)):
        top = 113 if x in (289, 320, 365, 405, 460, 494, 555, 594, 625, 685, 716, 778, 808, 870, 900) else 190
        network.append(_segment(f"vertical_{index}", x, top, x, 633, 0.85))
    # Top cap and small black-marker enclosure.
    network.extend((
        # Video review shows no MobileEntity using this enclosure. Keep it as
        # visual facility detail, not as an artificial driving component.
        _segment("top_left", 286, 112, 561, 112, drivable=False, color=VISUAL_ONLY_NETWORK_COLOR),
        _segment("top_right", 684, 112, 869, 112, drivable=False, color=VISUAL_ONLY_NETWORK_COLOR),
        _segment("top_cap_a", 500, 66, 684, 66, drivable=False, color=VISUAL_ONLY_NETWORK_COLOR),
        _segment("top_cap_b", 500, 66, 500, 112, drivable=False, color=VISUAL_ONLY_NETWORK_COLOR),
        _segment("top_cap_c", 684, 66, 684, 112, drivable=False, color=VISUAL_ONLY_NETWORK_COLOR),
        _segment("left_loop_a", 226, 190, 226, 280),
        _segment("left_loop_b", 226, 280, 258, 280),
        _segment("left_loop_c", 226, 343, 226, 404),
        _segment("left_loop_d", 226, 404, 258, 404),
        _segment("right_loop_a", 962, 190, 962, 280),
        _segment("right_loop_b", 930, 280, 962, 280),
        _segment("right_loop_c", 962, 343, 962, 404),
        _segment("right_loop_d", 930, 404, 962, 404),
        _segment("bottom_left_drop", 228, 555, 228, 649),
        _segment("bottom_right_drop", 963, 555, 963, 649),
    ))

    entities = [
        # Four dark circular markers repeatedly visible in the top enclosure.
        MobileEntity(f"black_marker_{i}", x, 77, 10, 10, (40, 40, 43), EntityShape.CIRCLE)
        for i, x in enumerate((560, 577, 607, 623))
    ]
    entities.extend(
        MobileEntity(f"green_entity_{i}", x, y, 13, 13, (58, 150, 26))
        for i, (x, y) in enumerate(((316, 257), (713, 276), (768, 306), (867, 264), (868, 329), (777, 468), (411, 544), (473, 619)))
    )
    entities.extend(
        MobileEntity(f"load_entity_{i}", x, y, 11, 11, (181, 143, 47), EntityShape.DIAMOND, 15)
        for i, (x, y) in enumerate(((410, 475), (463, 492), (502, 621), (560, 653), (607, 648)))
    )
    entities.extend((
        MobileEntity("cyan_entity", 669, 202, 13, 33, (76, 220, 229)),
        MobileEntity("blue_entity", 675, 492, 35, 13, (53, 117, 199)),
    ))

    layout = FacilityLayout(1280, 720, zones, tuple(machines), tuple(stations), tuple(network), tuple(entities))
    layout.validate()
    return layout
