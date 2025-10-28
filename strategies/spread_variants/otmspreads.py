from strategies.strategy import (
    Strategy,
    ThetaGamma,
    TG_STD3_2DTE_HedgebyForwards,
)
from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class OTMSpreads(TG_STD3_2DTE_HedgebyForwards):
    # def hedge(self, spot) -> None:
        # strategy_args = self.context.strategy_args
        # ref_IV = strategy_args["refIV"]
        # hedge_amount = strategy_args["hedge_amount"]

        # self.context.hedge_by_atm_forwards(
        #     spot, self.context.greeks["portfolio_delta"]*hedge_amount, ref_IV
        # )
    
    # def hedge_point(self, spot) -> bool:
        # if abs(self.context.greeks["portfolio_delta"]) > 0.05*self.context.strategy_args["demand"]:
        #     return True
        # return False
    
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
        return
    

    def take_position(self, spot):
        # option_type = "CE"
        gcalc = Greeks()

        option_type = self.context.strategy_args["option_type"]

        leg1_q = self.context.strategy_args["demand"]
        leg2_q = 2*leg1_q

        straddle_price, atm_option = self.context.atm_straddle_price(spot)     

        # call_second, put_second = self.context.find_delta_strike(spot, 0.10)
        # call_first, put_first = self.context.find_delta_strike(spot, 0.20)
        # call_second, put_second = self.context.find_delta_strike(spot, 0.10)

        # print(call_first)
        # print(call_second)
        ttm = self.context.timeToMaturity()
        
        shortspread = True
        first_leg_dir = -1 if shortspread else 1

        if option_type == "CE":
            # call_first = int(round((spot+straddle_price) / float(self.context.movement))) * self.context.movement
            # call_price = self.context.get_current_price([
            #     f"{call_first}CE",
            # ])[0]
            
            # call_iv = gcalc.IV(
            #     spot, call_first, self.context.rfr, ttm, call_price, "CE"
            # )

            # call_delta = gcalc.delta(
            #     "CE", spot, call_first, ttm, call_iv, self.context.rfr
            # )
            
            call_first, _ = self.context.find_delta_strike(spot, 0.2)
            # call_second, _ = self.context.find_delta_strike(spot, call_delta/2)
            call_second, _ = self.context.find_delta_strike(spot, 0.1)

            # width = self.context.strategy_args["width"]
            # call_second = int(round((spot+straddle_price+width) / float(self.context.movement))) * self.context.movement

            self.context.policy_variables["to_create_portfolio"] = {
                f"{call_first}{option_type}" : first_leg_dir*leg1_q,
                f"{call_second}{option_type}" : -first_leg_dir*leg2_q,
            }
            
            self.context.policy_variables["hedging_option"] = f"{call_first}CE"
        else:
            put_first = int(round((spot-straddle_price) / float(self.context.movement))) * self.context.movement
            put_price = self.context.get_current_price([
                f"{put_first}PE",
            ])[0]

            put_iv = gcalc.IV(
                spot, put_first, self.context.rfr, ttm, put_price, "PE"
            )

            put_delta = gcalc.delta(
                "PE", spot, put_first, ttm, put_iv, self.context.rfr
            )

            _, put_second = self.context.find_delta_strike(spot, put_delta/2)

            self.context.policy_variables["to_create_portfolio"] = {
                f"{put_first}{option_type}" : first_leg_dir*leg1_q,
                f"{put_second}{option_type}" : -first_leg_dir*leg2_q,
            }

            self.context.policy_variables["hedging_option"] = f"{put_first}PE"


        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        print(self.context.policy_variables["to_create_portfolio"])
        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.set_policy(policy.CustomPortfolioBuilder())
        
        pass

    
    def new_position_handler(self, spot) -> None:
        self.take_position(spot)
        return
    
    def existing_position_handler(self, spot):
        pass
        return
    
class OTMSpreads_FirstLegHedge(OTMSpreads):
    hedge_strike = None
    def hedge(self, spot) -> None:
        
        hedging_option = self.context.policy_variables["hedging_option"]
        hedge_strike = int(hedging_option[:-2])
        hedge_option_type = hedging_option[-2:]

        hedge_amount = self.context.strategy_args["hedge_amount"]

        hedge_option_price = self.context.get_current_price([
            hedging_option,
        ])[0]
        gcalc = Greeks()
        ttm = self.context.timeToMaturity()
        hedge_option_iv = gcalc.IV(
            spot, hedge_strike, self.context.rfr, ttm, hedge_option_price, hedge_option_type
        )
        hedge_option_delta = gcalc.delta(
            hedge_option_type, spot, hedge_strike, ttm, hedge_option_iv, self.context.rfr
        )

        required_delta = -self.context.greeks["portfolio_delta"]*hedge_amount

        hedge_amount = required_delta / hedge_option_delta



        self.context.policy_variables["to_create_portfolio"][hedging_option] = self.context.policy_variables["to_create_portfolio"].get(hedging_option, 0) + (-hedge_amount)

        # self.context.policy_variables["to_create_portfolio"] = {
        #     hedging_option: hedge_amount,
        # }

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.set_policy(policy.CustomPortfolioBuilder())


class OTMSpreads_ExitSignal(OTMSpreads):
    def position_management(self, spot) -> None:
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        print(close_time)
        if self.context.strategy_args["Entry_Time"] == '1970-01-01 00:00:00':
            exit_time = close_time.copy()
            pass
        else:
            exit_time = list(map(int, self.context.strategy_args["Entry_Time"].split(":")))

        
        print(self.context.strategy_args["Entry_Time"])
        # print()
        print(t)

        if (
            t
            > t.replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss
            or self.context.total_pnl > self.context.strategy_args.get("profit_book", math.inf)
            or t
            > t.replace(hour=exit_time[0], minute=exit_time[1], second=exit_time[2], microsecond=0)
        ):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            return
        
    