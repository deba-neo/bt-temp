from strategies.strategy import Strategy
from Greeks import Greeks
import math
from datetime import datetime
from strategies import policy

class TwoLegSpread(Strategy):
    def hedge(self, spot) -> None:
        pass
    
    def hedge_point(self, spot) -> bool:
        return False
    
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
            self.context.strategy_args["demand"] = 0
        return 
        return
    
    def new_position_handler(self, spot) -> None:
        leg1 = self.context.strategy_args["leg1"]
        leg2 = self.context.strategy_args["leg2"]
        leg1_buy = self.context.strategy_args["leg1_buy"]
        leg2_buy = self.context.strategy_args["leg2_buy"]
        leg1_qty = self.context.strategy_args["leg1_qty"]
        leg2_qty = self.context.strategy_args["leg2_qty"]
        spread_type = self.context.strategy_args["spread_type"]

        std_price, atm_opt = self.context.atm_straddle_price(spot)
        std_price_rounded = int(round(std_price / float(self.context.movement))) * self.context.movement

        if spread_type == "CE":
            leg1_option = atm_opt+std_price_rounded*leg1
            leg2_option = atm_opt+std_price_rounded*leg2
        else:
            leg1_option = atm_opt-std_price_rounded*leg1
            leg2_option = atm_opt-std_price_rounded*leg2

        if self.context.timeToMaturity() > 4:
            leg1_option = int(round(leg1_option / 500.0)) * 500
            leg2_option = int(round(leg2_option / 500.0)) * 500

        options = [
            f"{leg1_option}{spread_type}",
            f"{leg2_option}{spread_type}"
        ]
        sell = [leg1_buy, leg2_buy]
        q = [leg1_qty, leg2_qty]
        self.context.make_orders(options, sell, q)
        return
    
    def existing_position_handler(self, spot):
        return