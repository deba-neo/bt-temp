from strategies.strategy import Strategy, StraddlebyThree
from Greeks import Greeks
from datetime import datetime
import math
from strategies import policy


class Dynamic_Ratio_Spreads(StraddlebyThree):

    def position_management(self, spot) -> None:
        close_time = list(
            map(int, self.context.strategy_args["close_position_time"].split(":"))
        )
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        if (
            t
            > t.replace(
                hour=close_time[0],
                minute=close_time[1],
                second=close_time[2],
                microsecond=0,
            )
            or self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss
        ):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = (
                self.context.strategy_args["destruction_lots_per_cycle"]
            )

            self.context.set_policy(policy.Destructor())
            self.context.strategy_args["demand"] = 0
            return

        self.position_management_call_side(spot)
        self.position_management_put_side(spot)

    def position_management_call_side(self, spot) -> None:
        is_spread_out = self.context.strategy_args["is_call_spread_out"]

        if is_spread_out:
            self.manage_current_spread(spot, putside=False)
            return
        pass

    def position_management_put_side(self, spot) -> None:
        is_spread_out = self.context.strategy_args["is_put_spread_out"]

        if is_spread_out:
            self.manage_current_spread(spot, putside=True)
            return
        pass

    def manage_current_spread(self, spot, putside):
        """
        putside = True if put side spread otherwise true
        """

        current_spread_width = self.context.strategy_args["current_spread_width"]
        spread_list = [current_spread_width]
        straddle_price, atm_strike = self.context.atm_straddle_price(spot)
        strike = self.context.strategy_args["current_spread_strike"]

        edge_by_spread, strike_of_spread = self.edge_for_spreads(
            spot, spread_list, atm_strike
        )
        edge = edge_by_spread[current_spread_width]

        print(edge_by_spread)
        print(strike_of_spread)

        if edge < 0:
            self.context.policy_variables["lots_per_cycle"] = (
                self.context.strategy_args["destruction_lots_per_cycle"]
            )
            self.context.policy_variables["size_target"] = 0
            self.context.set_policy(policy.Destructor())

            self.context.strategy_args["current_tranche"] = 0

            self.context.strategy_args["is_spread_out"] = False

            pass

        return

    def edge_for_spreads(self, spot, spread_list, strike, putside=False):

        strike_gap = self.context.movement
        if not putside:
            strikes, prices = self.context.get_n_otm_call_prices(strike, 15)
        else:
            strikes, prices = self.context.get_n_otm_put_prices(strike, 15)

        strike_to_price = dict(zip(strikes, prices))
        # print(strikes)

        price_of_spread = {}
        strike_of_spread = {}
        # for every x points
        for spread in spread_list:
            max_price = -math.inf
            spread_strike = None
            # for every x point spread
            for strike in strikes:
                if not putside:
                    strike2 = strike + spread
                    if strike2 > strikes[-1]:
                        break
                else:
                    strike2 = strike - spread
                    if strike2 < strikes[-1]:
                        break

                spread_price = strike_to_price[strike] - 2 * strike_to_price[strike2]
                # print(f"strike {strike}")
                # print(f"strike2 {strike2}")
                # print(f"strike_to_price[strike] {strike_to_price[strike]}")
                # print(f"strike_to_price[strike2] {strike_to_price[strike2]}")
                # print(f"spread_price {spread_price}")

                if spread_price > max_price:
                    max_price = spread_price
                    spread_strike = strike

            price_of_spread[spread] = max_price
            strike_of_spread[spread] = spread_strike

        # print(price_of_spread)

        if not putside:
            expected_closes = self.context.strategy_args["spread_closing_dict"]
        else:
            expected_closes = self.context.strategy_args["put_spread_closing_dict"]

        edge_by_spread = {}
        for spread in spread_list:
            edge = None
            spread_price = price_of_spread[spread]
            if spread_price < 0:
                edge = 0
            else:
                expected_close = expected_closes[spread]

                bottom = 0

                risk = spread_price - bottom
                reward = expected_close - spread_price

                edge = reward / (risk + 0.001)

            edge_by_spread[spread] = edge

        return edge_by_spread, strike_of_spread

    pass
