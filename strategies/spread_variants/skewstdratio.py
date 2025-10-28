from strategies.strategy import Strategy
from Greeks import Greeks
import math
from strategies.strategy import (
    Strategy,
    ThetaGamma,
    TG_STD3_2DTE_HedgebyForwards,
)
from datetime import datetime
from strategies import policy

class Skewstdratio(TG_STD3_2DTE_HedgebyForwards):
    def hedge(self, spot) -> None:
        super().hedge_point(spot)
    
    def hedge_point(self, spot) -> bool:
        return super().hedge_point(spot)
    
    def position_management(self, spot) -> None:
        print(self.context.atm_straddle_price(spot))
        
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        if (
            t
            > t.replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
        pass
        
        if self.context.strategy_args["Entry_Time"] == '1970-01-01 00:00:00':
            return
        
        # entry_time = list(map(int, self.context.strategy_args["Entry_Time"].split(":")))
        # entry_time = [entry_time[0][-2], entry_time[1], entry_time[2]]
        entry_time = list(map(int, self.context.strategy_args["Entry_Time"].split(":")))
        
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")

        print(self.context.strategy_args["Entry_Time"])
        # print()
        # print(self.context.strategy_args["Entry_Time"])
        # print()
        print(t)


        if (
            t
            < t.replace(hour=entry_time[0], minute=entry_time[1], second=entry_time[2], microsecond=0)
            ):
            return
        elif(
            t
            > t.replace(hour=entry_time[0], minute=entry_time[1], second=entry_time[2], microsecond=0)
            ):
            self.manage_position(spot)
            return
        else:
            self.take_position(spot)
        
        return 
    
    def take_position(self, spot):
        strike = self.context.strategy_args["Entry_Strike"]
        width = self.context.strategy_args["Width"]
        size = self.context.strategy_args["First_Leg_size"]
        shortspread = self.context.strategy_args["shortspread"]

        option_type = self.context.strategy_args["Option_Type"]
        # option_type = "CE"

        if option_type == "CE":
            call_first = int(strike)
            call_second = call_first + int(width)

            leg1_q = size
            leg2_q = 2*size

            first_leg_dir = -1 if shortspread else 1
            self.context.policy_variables["to_create_portfolio"] = {
                f"{call_first}{option_type}" : first_leg_dir*leg1_q,
                f"{call_second}{option_type}" : -first_leg_dir*leg2_q,
                # f"{put_third}{option_type}" : first_leg_dir*leg1_q,
            }
        else:

            put_first = int(strike)
            put_second = put_first - int(width)
            
            leg1_q = size
            leg2_q = 2*size

            first_leg_dir = -1 if shortspread else 1
            self.context.policy_variables["to_create_portfolio"] = {
                f"{put_first}{option_type}" : first_leg_dir*leg1_q,
                f"{put_second}{option_type}" : -first_leg_dir*leg2_q,
                # f"{put_third}{option_type}" : first_leg_dir*leg1_q,
            }

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.set_policy(policy.CustomPortfolioBuilder())

        self.context.strategy_args["SL"] = -20*size
        self.context.strategy_args["PB"] = 10*size

        pass

    def manage_position(self, spot) -> None:
        curr_pnl = self.context.PnL()

        if curr_pnl < self.context.strategy_args["SL"]:
            self.context.strategy_args["close_position"] = True
            return 
        
        if curr_pnl > self.context.strategy_args["PB"]:
            self.context.strategy_args["close_position"] = True
            return
        
        self.context.strategy_args["SL"] = max(self.context.strategy_args["SL"], curr_pnl - 15*self.context.strategy_args["First_Leg_size"])

        return

    def new_position_handler(self, spot) -> None:
        return
    
    def existing_position_handler(self, spot):
        return