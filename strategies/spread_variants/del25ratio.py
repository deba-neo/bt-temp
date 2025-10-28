from strategies.strategy import (
    Strategy,
    StraddlebyThree_HedgebyForwards,
)
from Greeks import Greeks
import math
from strategies import policy
from datetime import datetime

class Del25Ratio(StraddlebyThree_HedgebyForwards):
    # def hedge(self, spot) -> None:
    #     self.take_position(spot, is_hedge= True)
    #     pass
    
    # def hedge_point(self, spot) -> bool:
    #     if abs(self.context.greeks["portfolio_gamma"]) < abs(0.5*self.context.strategy_args["gamma_initial"]):
    #         return False
        
    #     else:
    #         super().hedge_point(spot)
    
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
        
        self.context.strategy_args["refIV"] = self.context.straddle_IV(spot)
        pass

    def take_position(self, spot, is_hedge = False):
        option_type = "CE"
        shortspread = True

        option_type = self.context.strategy_args["option_type"]
        shortspread = (self.context.strategy_args["shortspread"] == "sell")
        shortspread = True

        call_first, put_first = self.find_delta_strike(spot, 0.20)
        call_second, put_second = self.find_delta_strike(spot, 0.10)
        # call_third, put_third = self.find_delta_strike(spot, 0.07)

        atm_straddle_price, atm_strike = self.context.atm_straddle_price(spot)
        
        leg1_q = self.context.demand
        leg2_q = 2*leg1_q


        first_leg_dir = -1 if shortspread else 1
        if option_type == "CE":
            self.context.policy_variables["to_create_portfolio"] = {
                f"{call_first}{option_type}" : first_leg_dir*leg1_q,
                f"{call_second}{option_type}" : -first_leg_dir*leg2_q,
                # f"{call_third}{option_type}" : first_leg_dir*leg1_q,
            }        
        else:
            self.context.policy_variables["to_create_portfolio"] = {
                f"{put_first}{option_type}" : first_leg_dir*leg1_q,
                f"{put_second}{option_type}" : -first_leg_dir*leg2_q,
                # f"{put_third}{option_type}" : first_leg_dir*leg1_q,
            }

        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        self.context.set_policy(policy.CustomPortfolioBuilder())
        # return
        if is_hedge:
            return
        
        gcalc = Greeks()
        ttm = self.context.timeToMaturity()


        if option_type == "CE":
            prices = self.context.get_current_price([f"{call_first}{option_type}", f"{call_second}{option_type}"])

            option1_IV = gcalc.IV(spot, call_first, self.context.rfr, ttm, prices[0], "CE")
            option2_IV = gcalc.IV(spot, call_second, self.context.rfr, ttm, prices[1], "CE")
            
            th1 = gcalc.theta("CE", spot, call_first, ttm, option1_IV, self.context.rfr)
            vg1 = gcalc.vega("CE", spot, call_first, ttm, option1_IV, self.context.rfr)
            gm1 = gcalc.gamma("CE", spot, call_first, ttm, option1_IV, self.context.rfr)
            th2 = gcalc.theta("CE", spot, call_second, ttm, option2_IV, self.context.rfr)
            vg2 = gcalc.vega("CE", spot, call_second, ttm, option2_IV, self.context.rfr)
            gm2 = gcalc.gamma("CE", spot, call_second, ttm, option2_IV, self.context.rfr)
            


        else:
            prices = self.context.get_current_price([f"{put_first}{option_type}", f"{put_second}{option_type}"])

            option1_IV = gcalc.IV(spot, put_first, self.context.rfr, ttm, prices[0], "PE")
            option2_IV = gcalc.IV(spot, put_second, self.context.rfr, ttm, prices[1], "PE")

            th1 = gcalc.theta("PE", spot, put_first, ttm, option1_IV, self.context.rfr)
            vg1 = gcalc.vega("PE", spot, put_first, ttm, option1_IV, self.context.rfr)
            gm1 = gcalc.gamma("PE", spot, put_first, ttm, option1_IV, self.context.rfr)
            th2 = gcalc.theta("PE", spot, put_second, ttm, option2_IV, self.context.rfr)
            vg2 = gcalc.vega("PE", spot, put_second, ttm, option2_IV, self.context.rfr)
            gm2 = gcalc.gamma("PE", spot, put_second, ttm, option2_IV, self.context.rfr)
        
        
        
        if shortspread:
            # theta based SL/PB
            theta = leg1_q*th1 - leg2_q*th2

            # self.context.strategy_args["stop_loss"] = self.context.PnL() - abs(2*theta)
            # self.context.strategy_args["profit_book"] = self.context.PnL() + abs(1*theta)

            self.context.strategy_args["gamma_initial"] = leg1_q*gm1 - leg2_q*gm2
        else:
            # vega based SL/PB
            vega = -leg1_q*vg1 + leg2_q*vg2
            theta = -leg1_q*th1 + leg2_q*th2
            self.context.strategy_args["stop_loss"] = self.context.PnL() - abs(1*vega)
            self.context.strategy_args["profit_book"] = self.context.PnL() + abs(2*vega)

            # self.context.strategy_args["stop_loss"] = self.context.PnL() - abs(0.75*theta)
            # self.context.strategy_args["profit_book"] = self.context.PnL() + abs(1.5*theta)

            self.context.strategy_args["gamma_initial"] = -leg1_q*gm1 + leg2_q*gm2

        print(f"SL: {self.context.strategy_args['stop_loss']}")
        print(f"PB: {self.context.strategy_args['profit_book']}")
        
        # if option_type == "CE":
        #     options_list = [f'{call_first}{option_type}', f'{call_second}{option_type}', f'{call_third}{option_type}']
        #     is_sell_list = [(not shortspread), shortspread, (not shortspread)]
        #     quantity_list = [leg1_q, 2*leg1_q, leg1_q]
        # else:
        #     options_list = [f'{put_first}{option_type}', f'{put_second}{option_type}', f'{put_third}{option_type}']
        #     is_sell_list = [(not shortspread), shortspread, (not shortspread)]
        #     quantity_list = [leg1_q, 2*leg1_q, leg1_q]
        
        # if option_type == "CE":
        #     options_list = [f'{call_first}{option_type}', f'{call_second}{option_type}', f'{call_third}{option_type}']
        #     is_sell_list = [(not shortspread), shortspread, (not shortspread)]
        #     quantity_list = [leg1_q, 2*leg1_q, leg1_q]
        # else:
        #     options_list = [f'{put_first}{option_type}', f'{put_second}{option_type}', f'{put_third}{option_type}']
        #     is_sell_list = [(not shortspread), shortspread, (not shortspread)]
        #     quantity_list = [leg1_q, 2*leg1_q, leg1_q]
        
        # if option_type == "CE":
        #     options_list = [f'{call_first}{option_type}', f'{call_second}{option_type}']
        #     is_sell_list = [(not shortspread), shortspread]
        #     quantity_list = [leg1_q, 2*leg1_q]
        # else:
        #     options_list = [f'{put_first}{option_type}', f'{put_second}{option_type}',]
        #     is_sell_list = [(not shortspread), shortspread]
        #     quantity_list = [leg1_q, 2*leg1_q]

        # if option_type == "CE":
        #     options_list = [f'{atm_strike}{option_type}', f'{call_30del}{option_type}']
        #     is_sell_list = [(not shortspread), shortspread]
        #     quantity_list = [leg1_q, 2*leg1_q]
        # else:
        #     options_list = [f'{atm_strike}{option_type}', f'{put_30del}{option_type}',]
        #     is_sell_list = [(not shortspread), shortspread]
        #     quantity_list = [leg1_q, 2*leg1_q]
        
        
        # self.context.make_orders(options_list, is_sell_list, quantity_list)


        pass

    
    def find_delta_strike(self, spot, delta):
        gcalc = Greeks()

        atm_straddle_price, atm_strike = self.context.atm_straddle_price(spot)
        atm_IV = self.context.straddle_IV(spot)

        put_deltas_and_ivs = []
        call_deltas_and_ivs = []
        
        n = 20
        m = 0
        # calls, call_prices = self.context.get_n_otm_call_prices(atm_strike, n)
        # puts, put_prices = self.context.get_n_otm_put_prices(atm_strike, n)

        calls, call_prices = self.context.get_n_call_prices(atm_strike, n, m)
        puts, put_prices = self.context.get_n_put_prices(atm_strike, n, m)

        tte = self.context.timeToMaturity()

        for i, strike in enumerate(calls):
            option_price = call_prices[i]

            option_IV = gcalc.Call_IV(spot, strike, 0, tte, option_price)
            option_delta = gcalc.delta("CE", spot, strike, tte, option_IV, 0)
            call_deltas_and_ivs.append((option_delta, option_IV))
        
        for i, strike in enumerate(puts):
            option_price = put_prices[i]

            option_IV = gcalc.Put_IV(spot, strike, 0, tte, option_price)
            option_delta = gcalc.delta("PE", spot, strike, tte, option_IV, 0)
            put_deltas_and_ivs.append((option_delta, option_IV))

        
        min_diff = math.inf
        put_min_diff = None
        for i, (put_delta, put_iv) in enumerate(put_deltas_and_ivs):
            try:
                if abs(abs(put_delta) - delta) < min_diff:
                    min_diff = abs(abs(put_delta) - delta)
                    put_min_diff = puts[i]
            except Exception as e:
                pass
            pass

        min_diff = math.inf
        call_min_diff = None
        for i, (call_delta, call_iv) in enumerate(call_deltas_and_ivs):
            try:
                if abs(abs(call_delta) - delta) < min_diff:
                    min_diff = abs(abs(call_delta) - delta)
                    call_min_diff = calls[i]
            except Exception as e:
                pass
            pass
        

        return call_min_diff, put_min_diff
        
    
    def new_position_handler(self, spot) -> None:
        self.take_position(spot)
        return 
    
    def existing_position_handler(self, spot):
        return