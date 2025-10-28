from strategies.strategy import Strategy, StraddlebyThree
from Greeks import Greeks
from datetime import datetime
import math
from strategies import policy


class TwoFiveSpreads(Strategy):
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

        if (
            abs(self.context.greeks["portfolio_delta"]) > 1000
            and self.context.greeks["portfolio_gamma"] < 0
        ):
            # print("Hedge")
            self.new_position_handler(spot)
            pass

        if (
            t
            > t.replace(
                hour=2,
                minute=30,
                second=0,
                microsecond=0,
            )
        ):
            self.context.demand = 0
        pass

    def hedge(self, spot) -> None:
        pass

    def hedge_point(self, spot) -> bool:
        pass

    def existing_position_handler(self, spot):
        pass

    def new_position_handler(self, spot) -> None:
        self.context.demand = 6000

        opt_c1 = self.find_delta_opt(spot, 0.4, "CE")
        opt_c2 = self.find_second_option(spot, opt_c1, "CE", 0.4)

        opt_p1 = self.find_delta_opt(spot, 0.4, "PE")
        opt_p2 = self.find_second_option(spot, opt_p1, "PE", 0.4)

        # print(opt_c1, opt_c2, opt_p1, opt_p2)
        # print(self.context.get_current_price([
        #     f"{opt_c1}CE",
        #     f"{opt_c2}CE",
        #     f"{opt_p1}PE",
        #     f"{opt_p2}PE",
        # ]))
        # print(opt_c1, opt_c2, opt_p1, opt_p2)



        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.policy_variables["to_create_portfolio"] = {
            f"{opt_c1}CE" : -self.context.demand,
            f"{opt_c2}CE" : self.context.demand*2.5,
            f"{opt_p1}PE" : -self.context.demand,
            f"{opt_p2}PE" : self.context.demand*2.5,
        }

        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        self.context.set_policy(policy.CustomPortfolioBuilder())

        pass

    def find_delta_opt(self, spot, req_delta, option_type):
        straddle_price, atm_option = self.context.atm_straddle_price(spot)

        
        strike_gap = self.context.movement * (1 if option_type == "CE" else -1)

        gcalc = Greeks()
        ttm = self.context.timeToMaturity()

        min_diff = math.inf
        min_diff_strike = None

        for i in range(20):
            strike = atm_option + strike_gap * (i + 1)

            price = self.context.get_current_price([f"{strike}{option_type}"])[0]
            # IV = self.context.straddle_IV(spot)
            
            if option_type == "CE":
                IV = gcalc.Call_IV(spot, strike, self.context.rfr, ttm, price)
            else:
                IV = gcalc.Put_IV(spot, strike, self.context.rfr, ttm, price)
            
            delta = abs(gcalc.delta(option_type, spot, strike, ttm, IV, self.context.rfr))

            print(strike)
            print(option_type)
            print(delta)

            if abs(delta - req_delta) < min_diff:
                min_diff = abs(delta - req_delta)
                min_diff_strike = strike
                continue

            
            if abs(delta - req_delta) > min_diff:
                break

        
        return min_diff_strike
        pass

    def find_second_option(self, spot, strike_opt1, option_type, ratio):
        p1 = self.context.get_current_price([f"{strike_opt1}{option_type}"])[0]
        # print(p1)
        req_price = ratio*p1
        # print(req_price)

        strike_gap = self.context.movement * (1 if option_type == "CE" else -1)
        gcalc = Greeks()
        ttm = self.context.timeToMaturity()

        min_diff = math.inf
        min_diff_strike = None

        for i in range(20):
            strike = strike_opt1 + strike_gap * (i + 1)
            price = self.context.get_current_price([f"{strike}{option_type}"])[0]

            # print(price)
            # print(req_price)
            # print(min_diff)

            if abs(price - req_price) < min_diff:
                min_diff = abs(price - req_price)
                min_diff_strike = strike
                continue

            
            if abs(price - req_price) > min_diff:
                break

            pass
        
        
        return min_diff_strike
