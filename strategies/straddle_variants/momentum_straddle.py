from strategies.strategy import (
    Strategy,
    StraddlebyThree,
    ThetaGamma,
    TG_STD3_2DTE,
    TG_STD3_2DTE_HedgebyBuying,
    ThetaGamma_HedgebyBuying
)
from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class MomentumStraddle(TG_STD3_2DTE_HedgebyBuying):
    def hedge_point(self, spot) -> bool:
        # greeks = self.context.greeks
        # if greeks["portfolio_gamma"] > 0:
        #     return False
        
        # return super().hedge_point(spot)
        return False
        pass
    
    def position_management(self, spot) -> None:

        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        if (
            t
            > t.replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss
            or self.context.total_pnl > self.context.strategy_args.get("profit_book", math.inf)
        ):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            return
        
        
        
        options = []
        IVs = self.context.get_IVs(spot, options)
        atm_IV = self.context.straddle_IV(spot)
        IVs = [atm_IV]

        data = []
        data.append(spot) 
        data.extend(IVs)
        
        self.context.strategy_args["DataStorage"].append(data)


        position = len(self.context.strategy_args["DataStorage"])
        
        if position in self.context.strategy_args["short entry times"]:
            self.enter_position(spot)
            pass
        elif position in self.context.strategy_args["short exit times"]:
            self.exit_position(spot)
            pass
        else:
            pass
            
        
        pass
    
    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["DataStorage"] = []

        self.context.strategy_args["short entry times"]
        self.context.strategy_args["short exit times"]

        self.context.strategy_args["overall_trade_stats"] = []

        pass

    def enter_position(self, spot) -> None:
        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]

        opt = self.context.atm_straddle_price(spot)[1]
        q = ((self.context.strategy_args["demand"]/2)//self.context.lot_size)*self.context.lot_size*2

        call_strike, put_strike = self.context.find_delta_strike(spot, 0.25)
        
        self.context.policy_variables["to_create_portfolio"] = {
            f"{opt+self.context.movement}CE" : q,
            f"{opt+self.context.movement}PE" : q,
        }

        self.context.set_policy(policy.CustomPortfolioBuilder())
        
        # self.context.policy_variables["size_target"] = ((self.context.strategy_args["demand"]/2)//self.context.lot_size)*self.context.lot_size*2
        # print(self.context.policy_variables["size_target"])
        # self.context.set_policy(policy.ATMBuiler())

        self.context.strategy_args["single_trade_stats"]= {
            "entry_vol" : self.context.straddle_IV(spot),
            "entry_straddle_price" : self.context.atm_straddle_price(spot)[0],
            "entry_time" : self.context.MD.current_time,
            "entry_PNL" : self.context.total_pnl,
        }
        pass

    def exit_position(self, spot) -> None:
        self.context.policy_variables["size_target"] = 0
        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
        self.context.set_policy(policy.Destructor())

        trade_statistics = {
            "exit_vol" : self.context.straddle_IV(spot),
            "exit_straddle_price" : self.context.atm_straddle_price(spot)[0],
            "exit_time" : self.context.MD.current_time,
            "net_PNL" : self.context.total_pnl - self.context.strategy_args["single_trade_stats"]["entry_PNL"],
        }

        starting_stats : dict = self.context.strategy_args["single_trade_stats"].copy()

        starting_stats.update(trade_statistics)

        self.context.strategy_args["overall_trade_stats"].append(starting_stats)

        self.context.strategy_args["single_trade_stats"] = {} 


        pass