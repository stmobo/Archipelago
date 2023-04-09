from __future__ import annotations

import typing

from Options import Choice, Option, Range, Toggle


class Route(Choice):
    """Sets choice of route."""

    display_name = "Route"
    option_eirika = 0
    option_ephraim = 1
    default = option_eirika

class RandomizedRecruitment(Toggle):
    display_name = "Randomize Recruitment Order"

class CrossGenderRandomization(Toggle):
    display_name = "Disable Cross-Gender Character Assignments"


fe8_options: typing.Dict[str, typing.Type[Option]] = {
    "route": Route,
    "randomized_recruitment": RandomizedRecruitment,
    "disable_crossgender_recruitment": CrossGenderRandomization,
}
