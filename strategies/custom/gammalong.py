from strategies.strategy import Strategy, ThetaGamma, StraddlebyThree
from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class GammaLong(StraddlebyThree):
    def position_management(self, spot) -> None:
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
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
        
        current_tranche = self.context.strategy_args["current_tranche"]
        entry_points = self.context.strategy_args["entry_points"]
        exit_points = self.context.strategy_args["exit_points"]

        if self.context.full_portfolio_size() > self.context.strategy_args[f"position_size_limit_{current_tranche}"]:
            self.context.policy_variables["size_target"] = self.context.strategy_args[
                f"position_size_limit_{current_tranche}"
            ]
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            return
        
        current_straddle_price = self.context.atm_straddle_price(spot)[0]
        expected_close = self.context.strategy_args["expected_close"]

        vol = self.context.straddle_IV(spot)
        tte = self.context.timeToMaturity()
        time_in_day = tte - math.floor(tte)
        projected_gain = current_straddle_price - expected_close
        projected_gain /= time_in_day

        normalised_entry_point = entry_points[current_tranche]*spot*vol
        normalised_exit_point = exit_points[current_tranche]*spot*vol

        print("Current Tranche: ", current_tranche)
        print("Projected Gain: ", projected_gain)
        print("Normalised Entry Point: ", normalised_entry_point)
        print("Normalised Exit Point: ", normalised_exit_point)
        
        if projected_gain < normalised_entry_point:
            current_tranche = min(current_tranche+1, 3)
            self.context.strategy_args["current_tranche"] = current_tranche
            # set new target
            self.context.policy_variables["size_target"] = self.context.strategy_args[
                f"tranche_{current_tranche}_target"
            ]
            # self.context.set_policy(policy.ATMBuiler())
            self.context.set_policy(policy.ATMStraddleBuyer())

        elif projected_gain > normalised_exit_point:
            current_tranche = max(current_tranche-1, 0)
            self.context.strategy_args["current_tranche"] = current_tranche
            # set new target
            self.context.policy_variables["size_target"] = self.context.strategy_args[
                f"tranche_{current_tranche}_target"
            ]
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
    
    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["current_tranche"] = 0

        tranche1 = self.context.strategy_args["tranche1"]
        tranche2 = self.context.strategy_args["tranche2"]
        tranche3 = self.context.strategy_args["tranche3"]
        
        self.context.strategy_args["entry_points"] = [tranche1, tranche2, tranche3, tranche3*1.5]
        self.set_exit_positions(tranche1, tranche2, tranche3)
        

    def set_exit_positions(self, tranche1, tranche2, tranche3):
        self.context.strategy_args["exit_points"] = [0, tranche1*2, tranche1, tranche2]

    def hedge(self, spot) -> None:
        movement = self.context.movement
        position = int(round(spot / float(movement))) * movement

        current_tranche = self.context.strategy_args["current_tranche"]
        quantity = self.context.strategy_args[
                f"tranche_{current_tranche}_target"
            ]
        
        quantity = quantity/2


        options = [f"{position}CE", f"{position}PE"]
        sell = [False, False]
        quantities = [quantity, quantity]

        for key, value in self.context.portfolio.items():
            options.append(key)
            sell.append((True if value > 0 else False))
            quantities.append(abs(value))

        self.context.make_orders_in_multiple_cycles(
            options,
            sell,
            quantities,
            self.context.strategy_args["construction_lots_per_cycle"]
        )
        return
    


class GammaLong_DayEnd(Strategy):
    def position_management(self, spot) -> None:
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        entry_time = list(map(int, self.context.strategy_args["entry_position_time"].split(":")))
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
        
        if (
            t
            > t.replace(hour=entry_time[0], minute=entry_time[1], second=entry_time[2], microsecond=0)
            and not self.context.strategy_args["position_created"]
            ):
            strikes_away = 1
            call_option = int(math.ceil(spot / float(self.context.movement))) * self.context.movement + self.context.movement*(strikes_away-1) 
            put_option = int(math.floor(spot / float(self.context.movement))) * self.context.movement - self.context.movement*(strikes_away-1)
            # self.context.otm_strangle_long(spot, self.context.strategy_args["demand"], 1)

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

            options_list = [f'{put_option}PE', f'{call_option}CE']
            is_sell_list = [False, False]
            quantity_list = [quantity_puts, quantity_calls]

            self.context.make_orders(options_list, is_sell_list, quantity_list)

            self.context.strategy_args["position_created"] = True
            pass
        
    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["position_created"] = False
        # if self.context.timeToMaturity() > 1:
        #     self.context.strategy_args["demand"] = 0
        pass

    def hedge(self, spot) -> None:
        pass

    def hedge_point(self, spot) -> bool:
        return False
    
    def existing_position_handler(self, spot):
        pass
    pass







class DTE0_Stalling_Straddle(Strategy):
    def position_management(self, spot) -> None:
        self.record_straddle_price(spot)

        pass

    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["position_created"] = False
        if self.context.timeToMaturity() > 1:
            self.context.strategy_args["demand"] = 0
        
        self.context.strategy_args["straddle_price_history"] = []
        pass

    def record_straddle_price(self, spot) -> None:
        current_price, _ = self.context.atm_straddle_price(spot)
        required_data_points = self.context.strategy_args["Number_of_minutes"]*self.context.strategy_args["Minute_Resolution"]

        # if len(self.context.strategy_args["straddle_price_history"]) < required_data_points:
        self.context.strategy_args["straddle_price_history"].append((datetime.now(), current_price))
        pass
    
    def check_entry_condition(self, spot) -> None:
        current_price, _ = self.context.atm_straddle_price(spot)
        

    def enter(self, spot) -> None:
        pass

    def exit(self, spot) -> None:
        pass

    def hedge(self, spot) -> None:
        pass

    def hedge_point(self, spot) -> bool:
        return False
    
    def existing_position_handler(self, spot):
        pass
    pass