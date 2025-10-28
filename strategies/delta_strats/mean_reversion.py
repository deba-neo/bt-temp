from strategies.strategy import Strategy
from Greeks import Greeks
from datetime import datetime
import math
from strategies import policy


class MeanReversion(Strategy):
    def hedge(self, spot) -> None:
        pass
    
    def hedge_point(self, spot) -> bool:
        pass
    
    def new_position_handler(self, spot) -> None:
        pass
    
    def existing_position_handler(self, spot):
        pass
    
    
    
    
    def position_management(self, spot) -> None:
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
            return
        
        
        
        pass
    
    def compute_mean(self, spot):
        pass

    def define_entry_points(self, spot):
        pass

    def define_exit_points(self, spot):
        pass