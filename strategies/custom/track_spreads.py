from strategies.strategy import Strategy, StraddlebyThree
from Greeks import Greeks
from datetime import datetime
import math
from strategies import policy


class Dynamic_Ratio_Spreads(StraddlebyThree):
    def hedge(self, spot) -> None:
        options = []
        for option in list(self.context.portfolio.keys()):
            if self.context.portfolio[option] != 0 and option[-2:] == "CE":
                options.append(int(option[:-2]))

        min_strike = min(options)

        tte = self.context.timeToMaturity()
        IV = self.context.straddle_IV(spot)

        gcalc = Greeks()

        d1 = gcalc.delta("CE", spot, min_strike, tte, IV, self.context.rfr)
        d = self.context.greeks["portfolio_delta"]

        q = -d / d1

        options = [f"{min_strike}CE"]
        sell = [True if q < 0 else False]
        quantities = [abs(q)]

        self.context.make_orders_in_multiple_cycles(
            options,
            sell,
            quantities,
            self.context.strategy_args["construction_lots_per_cycle"],
        )

        pass

    def hedge_point(self, spot) -> bool:
        return False

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

        if self.context.strategy_args["trade_SL"]:
            if self.context.full_portfolio_size() == 0:
                self.context.strategy_args["trade_SL"] = False
                self.context.strategy_args["is_spread_out"] = False
                pass
            else:
                self.cut_one_cycle(spot)
            return

        is_spread_out = self.context.strategy_args["is_spread_out"]

        # self.put_spreads(spot)

        if is_spread_out:
            self.manage_current_spread(spot)
            return

        self.monitor_all_spreads(spot)
        pass

    def put_spreads(self, spot):

        is_spread_out = self.context.strategy_args["is_put_spread_out"]

        if is_spread_out:
            self.manage_current_spread(spot, putside=True)
            return

        self.monitor_all_spreads(spot, putside=True)

        pass

    def manage_delta(self, spot, putside=False):
        required_opts = "PE" if putside else "CE"

        options = []
        for option in list(self.context.portfolio.keys()):
            if self.context.portfolio[option] != 0 and option[-2:] == required_opts:
                options.append(option)

        tte = self.context.timeToMaturity()

        gcalc = Greeks()

        prices = self.context.get_current_price(options)

        total_gamma = 0
        total_delta = 0
        for i, option in enumerate(options):
            IV_func = gcalc.Put_IV if putside else gcalc.Call_IV
            IV = IV_func(spot, int(option[:-2]), self.context.rfr, tte, prices[i])
            delta = gcalc.delta(
                required_opts, spot, int(option[:-2]), tte, IV, self.context.rfr
            )
            total_delta += delta * self.context.portfolio[option]

            gamma = gcalc.gamma(
                required_opts, spot, int(option[:-2]), tte, IV, self.context.rfr
            )
            total_gamma += gamma * self.context.portfolio[option]

        straddle_price, _ = self.context.atm_straddle_price(spot)
        hedge_point = straddle_price / 3
        hedge_point *= self.context.strategy_args["hedge_point_multiplier"]

        try:
            points_out = abs(total_delta / total_gamma)
        except ZeroDivisionError as e:
            return

        if not points_out > hedge_point:
            return

        closer_option = (
            options[0] if self.context.portfolio[options[0]] > 0 else options[1]
        )

        closer_option_price = self.context.get_current_price([closer_option])
        IV = IV_func(spot, int(closer_option[:-2]), self.context.rfr, tte, closer_option_price)

        d1 = gcalc.delta(required_opts, spot, int(closer_option[:-2]), tte, IV, self.context.rfr)
        d = total_delta

        q = (-d / d1)/2

        options = [closer_option]
        sell = [True if q < 0 else False]
        quantities = [abs(q)]

        self.context.make_orders_in_multiple_cycles(
            options,
            sell,
            quantities,
            self.context.strategy_args["construction_lots_per_cycle"],
        )

        pass

    def manage_current_spread(self, spot, putside=False):
        
        if not putside:
            current_spread_width = self.context.strategy_args["current_spread_width"]
            strike = self.context.strategy_args["current_spread_strike"]
        else:
            current_spread_width = self.context.strategy_args["current_put_spread_width"]
            strike = self.context.strategy_args["current_put_spread_strike"]
        
        spread_list = [current_spread_width]
        straddle_price, atm_strike = self.context.atm_straddle_price(spot)

        edge_by_spread, strike_of_spread = self.edge_for_spreads(
            spot, spread_list, atm_strike, putside
        )
        edge = edge_by_spread[current_spread_width]

        print(edge_by_spread)
        print(strike_of_spread)

        self.manage_delta(spot, putside)

        # if edge < 0:
        #     self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
        #     self.context.policy_variables["size_target"] = 0
        #     self.context.set_policy(policy.Destructor())

        #     self.context.strategy_args["current_tranche"] = 0

        #     self.context.strategy_args["is_spread_out"] = False

        #     pass

        return
        current_tranche = self.context.strategy_args["current_tranche"]

        # for
        # tranche  0    1    2
        entries = [1, 2, math.inf]
        exits = [0, 1 / 3, 1]

        entry_point = entries[current_tranche]
        exit_point = exits[current_tranche]

        if current_tranche == 2 and edge < 1:
            self.context.strategy_args["trade_SL"] = True
            self.cut_one_cycle(spot)
            return

        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")

        if edge > entry_point:
            if t > t.replace(hour=14, minute=30, second=0, microsecond=0):
                return

            current_tranche = min(current_tranche + 1, 2)
            self.context.strategy_args["current_tranche"] = current_tranche

            # build 1 lot
            dd = self.context.strategy_args[f"tranche{current_tranche}_size"]
            self.build_to_size(spot, strike, strike + current_spread_width, dd)

        elif edge < exit_point:
            current_tranche = max(current_tranche - 1, 0)
            self.context.strategy_args["current_tranche"] = current_tranche

            # cut 1 lot
            dd = self.context.strategy_args[f"tranche{current_tranche}_size"]
            self.cut_to_size(spot, strike, strike + current_spread_width, dd)

        pass

    def build_one_cycle(self, spot, strike_buy, strike_sell):
        pass

    def cut_one_cycle(self, spot):
        pass

    def build_to_size(self, spot, strike_buy, strike_sell, size, putside=False):
        gcalc = Greeks()

        tte = self.context.timeToMaturity()
        IV = self.context.straddle_IV(spot)

        if not putside:
            prices = self.context.get_current_price([f"{strike_buy}CE", f"{strike_sell}CE"])
            IV1 = gcalc.Call_IV(spot, strike_buy, self.context.rfr, tte, prices[0])
            d1 = gcalc.delta("CE", spot, strike_buy, tte, IV1, self.context.rfr)
            IV2 = gcalc.Call_IV(spot, strike_sell, self.context.rfr, tte, prices[1])
            d2 = gcalc.delta("CE", spot, strike_sell, tte, IV2, self.context.rfr)

            d = d1 * size - 2 * size * d2

            q = -d / d1

            self.context.policy_variables["lots_per_cycle"] = (
                self.context.strategy_args["construction_lots_per_cycle"]
            )
            self.context.policy_variables["to_create_portfolio"] = {
                f"{strike_buy}CE": -(size + q),
                f"{strike_sell}CE": 2 * size,
            }

        else:
            prices = self.context.get_current_price([f"{strike_buy}PE", f"{strike_sell}PE"])
            IV1 = gcalc.Put_IV(spot, strike_buy, self.context.rfr, tte, prices[0])
            d1 = gcalc.delta("PE", spot, strike_buy, tte, IV1, self.context.rfr)
            IV2 = gcalc.Put_IV(spot, strike_sell, self.context.rfr, tte, prices[1])
            d2 = gcalc.delta("PE", spot, strike_sell, tte, IV2, self.context.rfr)

            d = d1 * size - 2 * size * d2

            q = -d / d1

            self.context.policy_variables["lots_per_cycle"] = (
                self.context.strategy_args["construction_lots_per_cycle"]
            )
            self.context.policy_variables["to_create_portfolio"] = {
                f"{strike_buy}PE": -(size + q),
                f"{strike_sell}PE": 2 * size,
            }

        self.context.set_policy(policy.CustomPortfolioBuilder())
        pass

    def cut_to_size(self, spot, strike_buy, strike_sell, size):

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args[
            "construction_lots_per_cycle"
        ]
        self.context.policy_variables["to_create_portfolio"] = {
            f"{strike_buy}CE": -size,
            f"{strike_sell}CE": 2 * size,
        }

        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = (
                self.context.policy_variables["to_create_portfolio"].get(key, 0) + value
            )

        self.context.set_policy(policy.CustomPortfolioBuilder())
        pass

    def monitor_all_spreads(self, spot, putside=False):
        ttm = self.context.timeToMaturity()
        dte = math.ceil(ttm)

        straddle_price, strike = self.context.atm_straddle_price(spot)
        strike_gap = self.context.movement

        # spread_list : list = self.context.strategy_args["spread_list"]
        spread_list = [
            int(math.ceil((straddle_price / strike_gap) / 2) * strike_gap),
            # int(math.ceil((straddle_price/strike_gap)*2/3)*strike_gap)
        ]

        edge_by_spread, strike_of_spread = self.edge_for_spreads(
            spot, spread_list, strike, putside
        )

        best_edge = -math.inf
        best_spread = None
        for spread in spread_list:
            if edge_by_spread[spread] > best_edge:
                best_edge = edge_by_spread[spread]
                best_spread = spread

        print(edge_by_spread)
        print(strike_of_spread)

        if best_edge > 1:
            if not putside:
                self.context.strategy_args["current_spread_width"] = best_spread
                self.context.strategy_args["current_spread_strike"] = strike_of_spread[
                    best_spread
                ]
            else:
                self.context.strategy_args["current_put_spread_width"] = best_spread
                self.context.strategy_args["current_put_spread_strike"] = strike_of_spread[
                    best_spread
                ]
            
            self.context.strategy_args["current_tranche"] = 1
            if not putside:
                self.context.strategy_args["is_spread_out"] = True
            else:
                self.context.strategy_args["is_put_spread_out"] = True

            st = strike_of_spread[best_spread]

            # dd = self.context.strategy_args["tranche1_size"]
            dd = self.context.demand

            if not putside:
                self.build_to_size(spot, st, st + best_spread, dd, putside)
            else:
                self.build_to_size(spot, st, st - best_spread, dd, putside)

        pass

    def edge_for_spreads(self, spot, spread_list, strike, putside=False):

        strike_gap = self.context.movement
        if not putside:
            strikes, prices = self.context.get_n_otm_call_prices(strike, 10)
        else:
            strikes, prices = self.context.get_n_otm_put_prices(strike, 10)

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

    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["current_tranche"] = 0
        self.context.strategy_args["trade_SL"] = False
        self.context.strategy_args["is_spread_out"] = False
        self.context.strategy_args["is_put_spread_out"] = False

        pass

    def existing_position_handler(self, spot):
        try:
            current_tranche = self.context.strategy_args["current_tranche"]
        except:
            current_tranche = 0

        self.new_position_handler(spot)
        self.context.strategy_args["current_tranche"] = current_tranche
