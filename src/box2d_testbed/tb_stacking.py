# tb_stacking.py

import math

from .base_test import BaseTest, UI
from box2d import Vec2


class CardHouse(BaseTest, category="Stacking", name="Card House"):
    """A house of cards built from very thin, high-friction boxes.

    The cards are 1mm thick, so this leans hard on the solver: any drift in
    contact handling collapses the structure.
    """

    rows = UI.int(5, min=1, max=8)

    def setup(self):
        self.app_state.center = Vec2(0.75, 0.9)
        self.app_state.zoom = 25.0 * 0.05

        self.world.new_body().static().position(0, -2).box(80, 4, friction=0.7).build()

        card_height = 0.2
        card_thickness = 0.001
        lean = math.radians(25)
        cards = (
            self.world.new_body()
            .dynamic()
            .box(2 * card_thickness, 2 * card_height, friction=0.7)
        )

        y = card_height - 0.02
        for row in range(self.rows, 0, -1):
            x = 0.175 * (self.rows - row)
            for i in range(row):
                # The flat card resting on top of the pair below it.
                if i != row - 1:
                    cards.position(x + 0.25, y + card_height - 0.015).rotation(
                        0.5 * math.pi
                    ).build()

                # The two leaning cards forming this cell.
                cards.position(x, y).rotation(-lean).build()
                x += 0.175
                cards.position(x, y).rotation(lean).build()
                x += 0.175

            y += card_height * 2.0 - 0.03

    @rows.callback
    def on_rows_change(self, key, value):
        for body in self.world.bodies:
            body.destroy()
        self.setup()
