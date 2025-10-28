from strategies.strategy import (
    Strategy,
    ThetaGamma,
    StraddlebyThree,
    TG_STD3_2DTE_HedgebyBuying,
)

from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class GammaLong_ATR(TG_STD3_2DTE_HedgebyBuying):
    def position_management(self, spot) -> None:
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        # entry_time = list(map(int, self.context.strategy_args["entry_position_time"].split(":")))
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))

        
        if (
            t
            > t.replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.total_pnl < self.context.strategy_args["stop_loss"]
            ):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            return
        
        self.check_trade_signal(spot)
        self.building_position(spot)
        # self.set_exit_conditions(spot)
        
        if self.context.strategy_args["position_created"] and self.exit_condition(spot):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            pass

    
    def building_position(self, spot):
        
        if (
            self.context.strategy_args["trade_signal"]
            and not self.context.strategy_args["position_created"]
            ):

            straddle_price, _ = self.context.atm_straddle_price(spot)
            std_dist = 1
            call_option = int(math.ceil((spot + std_dist*straddle_price)/ float(self.context.movement))) * self.context.movement 
            put_option = int(math.floor((spot - std_dist*straddle_price)/ float(self.context.movement))) * self.context.movement
            
            gcalc = Greeks()

            prices = self.context.get_current_price([
                f'{call_option}CE',
                f'{put_option}PE',
            ])

            ttm = self.context.timeToMaturity()

            IV = gcalc.Call_IV(spot, call_option, self.context.rfr, ttm, prices[0])
            delta_call = gcalc.delta('CE', spot, call_option, ttm, IV, self.context.rfr)
            
            IV = gcalc.Put_IV(spot, put_option, self.context.rfr, ttm, prices[1])
            delta_put = gcalc.delta('PE', spot, put_option, ttm, IV, self.context.rfr)

            ratio = abs(delta_put/delta_call)

            quantity_calls = self.context.strategy_args["demand"]
            quantity_puts = quantity_calls/ratio

            if self.context.strategy_args["Kind"] == "g":
                options_list = [f'{put_option}PE', f'{call_option}CE']
                is_sell_list = [False, False]
                quantity_list = [quantity_puts, quantity_calls]
            else:
                # directional gamma
                if abs(spot - self.context.high) < abs(spot - self.context.low):
                    options_list = [f'{call_option}CE']
                    is_sell_list = [False]
                    quantity_list = [self.context.strategy_args["demand"]]
                else:
                    options_list = [f'{put_option}PE']
                    is_sell_list = [False]
                    quantity_list = [self.context.strategy_args["demand"]]    


            self.context.make_orders(options_list, is_sell_list, quantity_list)

            self.context.strategy_args["position_created"] = True

            self.set_exit_conditions(spot)

            pass
        
    def set_exit_conditions(self, spot):
        tol = self.context.strategy_args["expected_ATR"]

        exit_dist = self.context.strategy_args["Exit_Dist"]

        atr_limit = self.context.strategy_args["expected_ATR"]*self.context.strategy_args["Range_Multiplier"]
        

        mapping = {
            "Entry" : atr_limit,
            "ATR" : self.context.high - self.context.low,
            "None" : math.inf,
        }

        Exit_Distance = mapping[self.context.strategy_args["Exit_Condition"]]*exit_dist
        
        
        # closer to top
        if abs(spot - self.context.high) < abs(spot - self.context.low):
            # self.context.strategy_args["top_exit"] = self.context.high + 0.5*atr_limit
            self.context.strategy_args["top_exit"] = math.inf
            
            # self.context.strategy_args["top_exit"] = self.context.high + 1.5 * Exit_Distance

            # self.context.strategy_args["bottom_exit"] = self.context.high - tol/3
            # self.context.strategy_args["bottom_exit"] = -math.inf
            self.context.strategy_args["bottom_exit"] = self.context.high - Exit_Distance
            # self.context.strategy_args["bottom_exit"] = -math.inf

        # closer to bottom
        else:
            # self.context.strategy_args["top_exit"] = self.context.low + tol/3
            self.context.strategy_args["top_exit"] = self.context.low + Exit_Distance
            # self.context.strategy_args["top_exit"] = math.inf
            # self.context.strategy_args["bottom_exit"] = self.context.low - 0.5*atr_limit
            self.context.strategy_args["bottom_exit"] = -math.inf

            # self.context.strategy_args["bottom_exit"] = self.context.low - 1.5*Exit_Distance
        
        pass

    def exit_condition(self, spot) -> bool:
        return (spot < self.context.strategy_args["bottom_exit"]) or (spot > self.context.strategy_args["top_exit"])
        pass
    
    def check_trade_signal(self, spot):
        atr =  self.context.high - self.context.low

        print(atr)
        print(self.context.strategy_args["expected_ATR"])

        has_breached_limit = atr > self.context.strategy_args["expected_ATR"]*self.context.strategy_args["Range_Multiplier"]

        current_IV = self.context.straddle_IV(spot)
        is_iv_unreacted =  current_IV < self.context.strategy_args["morning_IV"]*1.03
        
        
        defined_range = self.context.strategy_args["expected_ATR"]*self.context.strategy_args["Range_Multiplier"]

        is_beyond_limit = (
            (spot - self.context.low) > defined_range
            or (self.context.high - spot) > defined_range
        )
        
        if is_beyond_limit and is_iv_unreacted:
            self.context.strategy_args["trade_signal"] = True

        # if has_breached_limit:
        #     self.context.strategy_args["trade_signal"] = True

        pass
    
    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["position_created"] = False
        self.context.strategy_args["trade_signal"] = False
        


        current_IV = self.context.straddle_IV(spot)

        straddle_price, atm_option = self.context.atm_straddle_price(spot)
        
        # expected_ATR = math.sqrt(2/math.pi)

        expected_ATR = (current_IV/math.sqrt(365))*spot

        ttm = self.context.timeToMaturity()

        expected_ATR = (2*straddle_price)/math.sqrt(ttm)
        
        self.context.strategy_args["morning_IV"] = current_IV
        self.context.strategy_args["initial_spot"] = spot
        self.context.strategy_args["expected_ATR"] = expected_ATR
        pass
    
    def hedge(self, spot) -> None:
        strategy_args = self.context.strategy_args
        ref_IV = strategy_args["refIV"]
        hedge_amount = strategy_args["hedge_amount"]

        hedge_amount = 0.33

        if self.context.greeks["portfolio_delta"] > 0:
            self.context.hedge_by_selling_calls(
                spot, self.context.greeks["portfolio_delta"]*hedge_amount, ref_IV
            )
        else:
            self.context.hedge_by_selling_puts(
                spot, self.context.greeks["portfolio_delta"]*hedge_amount, ref_IV
            )
        pass

    def hedge_point(self, spot) -> bool:
        return False
        greeks = self.context.greeks
        straddle_price, _ = self.context.atm_straddle_price(spot)

        try:
            points_out = abs(greeks["portfolio_delta"] / greeks["portfolio_gamma"])
            hedge_point = straddle_price / 4
            hedge_point *= self.context.strategy_args["hedge_point_multiplier"]
        except ZeroDivisionError as e:
            print(e)
            points_out = self.zero_gamma_handler(greeks["portfolio_delta"])
            hedge_point = self.zero_gamma_handler(greeks["portfolio_theta"] / 2)

        print(f"Points Out: {points_out  :.2f}", flush=True)
        print(f"Hedge Point: {hedge_point  :.2f}", flush=True)
        
        return points_out > hedge_point