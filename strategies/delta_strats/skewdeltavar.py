from strategies.strategy import Strategy
from Greeks import Greeks
from datetime import datetime
import math
from strategies import policy


class Delta_Skew_Var(Strategy):
    def hedge(self, spot) -> None:
        pass
    
    def hedge_point(self, spot) -> bool:
        return False
    
    def position_management(self, spot) -> None:
        # if self.context.timeToMaturity() > 1:
        #     return

        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")
        if (
            t
            > t.replace(hour=close_time[0], minute=close_time[1], second=close_time[2], microsecond=0)
            or \
                self.context.strategy_args["close_position"]
            or self.context.hit_stop_loss
        ):
            self.context.policy_variables["size_target"] = 0
            self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            self.context.set_policy(policy.Destructor())
            self.context.strategy_args["demand"] = 0
            return 
        
        if self.context.full_portfolio_size() > 0:
            options = []

            for option in list(self.context.portfolio.keys()):
                if self.context.portfolio[option] != 0:
                    options.append(option)
                    pass
                pass
            
            if options[0][-2:] == "CE":
                delta_long = False
            else:
                delta_long = True

            
            # if self.context.total_pnl > self.context.strategy_args.get("profit_book", math.inf):
            #     self.context.policy_variables["size_target"] = 0
            #     self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            #     self.context.set_policy(policy.Destructor())
            #     return
            
            # check if edge remains distance
            # z_score, entry_point = self.find_edge(spot)
            # if delta_long:
            #     if z_score < 0.5:
            #         self.context.policy_variables["size_target"] = 0
            #         self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            #         self.context.set_policy(policy.Destructor())
            #         return
            #         # self.kill_position()
            # else:
            #     if z_score > -0.5:
            #         self.context.policy_variables["size_target"] = 0
            #         self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["destruction_lots_per_cycle"]
            #         self.context.set_policy(policy.Destructor())
            #         return
            #     pass
            
            distance_of_spread = min(abs(int(options[0][:-2]) - spot), abs(int(options[1][:-2]) - spot))
            
            print(distance_of_spread)

            straddle_price, atm_option = self.context.atm_straddle_price(spot)
            
            print(straddle_price)

            # print(self.context.strategy_args["stop_loss"])
            # print(self.context.strategy_args["profit_book"])

            if straddle_price < self.context.movement or self.context.timeToMaturity() > 1:
                return
            
            if distance_of_spread > 2*straddle_price:
                
                self.build_position(spot, delta_long)
                return
            else:
                return
        
        t = datetime.strptime(str(self.context.MD.current_time), "%Y-%m-%d %H:%M:%S")

        # if t > t.replace(hour=14, minute=30, second=0, microsecond=0):
        #     return
        straddle_price, atm_option = self.context.atm_straddle_price(spot)
        if straddle_price < self.context.movement:
                return
        
        z_score, entry_point = self.find_edge(spot)

        if abs(z_score) > entry_point:
            delta_long = z_score > 0
            self.build_position(spot, delta_long)

    def find_edge(self, spot):
        current_average = self.track_all_skew(spot)

        usual_average = self.context.strategy_args["Skew_Mean"]
        usual_std = self.context.strategy_args["Skew_Std"]

        print(current_average)
        print(usual_average)
        print(usual_std)
        entry_point = self.context.strategy_args["Entry Point"]

        # entry_point = 0.5
        
        z_score = (current_average - usual_average)/usual_std
        print(z_score)

        return z_score, entry_point
        pass
            

    def build_position(self, spot, delta_long):
        atm_straddle_price, atm_strike = self.context.atm_straddle_price(spot)
        strike_gap = self.context.movement
        IV = self.context.straddle_IV(spot)

        gcalc = Greeks()
        ttm = self.context.timeToMaturity()

        size = self.context.strategy_args["demand"]

        # selling spreads
        if not delta_long:
            atm_strike = spot
            # strike_buy = int(math.floor((atm_strike + atm_straddle_price)/strike_gap)*strike_gap)
            strike_buy = int(math.ceil((atm_strike + atm_straddle_price)/strike_gap)*strike_gap)
            strike_sell = int(math.ceil((atm_strike + 2*atm_straddle_price)/strike_gap)*strike_gap)
            option_buy = f"{strike_sell}CE"
            option_sell = f"{strike_buy}CE"
            
            prices = self.context.get_current_price([option_buy, option_sell])
            rtv = prices[0] - prices[1]
            
            IV1 = gcalc.Call_IV(spot, strike_sell, self.context.rfr, ttm, prices[0])
            th1 = gcalc.theta("CE", spot, strike_sell, ttm, IV1, self.context.rfr)
            v1 = gcalc.vega("CE", spot, strike_sell, ttm, IV1, self.context.rfr)

            IV2 = gcalc.Call_IV(spot, strike_buy, self.context.rfr, ttm, prices[1])
            th2 = gcalc.theta("CE", spot, strike_buy, ttm, IV2, self.context.rfr)
            v2 = gcalc.vega("CE", spot, strike_buy, ttm, IV2, self.context.rfr)

            theta = th1 - th2
            vega = v1 - v2

        else:
            atm_strike = spot
            # strike_buy = int(math.ceil((atm_strike - atm_straddle_price)/strike_gap)*strike_gap)
            strike_buy = int(math.floor((atm_strike - atm_straddle_price)/strike_gap)*strike_gap)
            strike_sell = int(math.floor((atm_strike - 2*atm_straddle_price)/strike_gap)*strike_gap)
            option_buy = f"{strike_sell}PE"
            option_sell = f"{strike_buy}PE"
            
            prices = self.context.get_current_price([option_buy, option_sell])
            rtv = prices[0] - prices[1]

            IV1 = gcalc.Put_IV(spot, strike_buy, self.context.rfr, ttm, prices[0])
            th1 = gcalc.theta("PE", spot, strike_buy, ttm, IV1, self.context.rfr)
            v1 = gcalc.vega("PE", spot, strike_buy, ttm, IV1, self.context.rfr)

            IV2 = gcalc.Put_IV(spot, strike_sell, self.context.rfr, ttm, prices[1])
            th2 = gcalc.theta("PE", spot, strike_sell, ttm, IV2, self.context.rfr)
            v2 = gcalc.vega("PE", spot, strike_sell, ttm, IV2, self.context.rfr)

            theta = th1 - th2
            vega = v1 - v2
        if ttm < 1:
            self.context.strategy_args["stop_loss"] = self.context.PnL() - abs(2*rtv)*size
        else:
            self.context.strategy_args["stop_loss"] = self.context.PnL() - abs(4*theta)*size
            self.context.strategy_args["profit_book"] = self.context.PnL() + abs(2*theta)*size

            # self.context.strategy_args["stop_loss"] = self.context.PnL() - abs(2*vega)*size
            # self.context.strategy_args["profit_book"] = self.context.PnL() + abs(1*vega)*size

        # if not delta_long:
        #     option_buy = f"{atm_strike}PE"
        #     option_sell = f"{atm_strike}CE"
        # else:
        #     option_buy = f"{atm_strike}CE"
        #     option_sell = f"{atm_strike}PE"

        # self.context.strategy_args["stop_loss"] = - math.inf
        # self.context.strategy_args["profit_book"] = math.inf
        
        # Clear Current Portfolio

        self.context.policy_variables["lots_per_cycle"] = self.context.strategy_args["construction_lots_per_cycle"]
        size = self.context.strategy_args["demand"]

        self.context.policy_variables["to_create_portfolio"] = {
            option_buy : -size,
            option_sell : size,
        }

        # print(self.context.policy_variables["to_create_portfolio"])

        for key, value in self.context.portfolio.items():
            self.context.policy_variables["to_create_portfolio"][key] = self.context.policy_variables["to_create_portfolio"].get(key, 0) + value        

        # print(self.context.policy_variables["to_create_portfolio"])

        self.context.set_policy(policy.CustomPortfolioBuilder())


        pass


    def track_all_skew(self, spot):
        gcalc = Greeks()

        atm_straddle_price, atm_strike = self.context.atm_straddle_price(spot)
        atm_IV = self.context.straddle_IV(spot)

        required_deltas = list(map(lambda x:x/100, [*range(10,50,3)]))

        put_deltas_and_ivs = []
        call_deltas_and_ivs = []
        
        n = 15
        calls, call_prices = self.context.get_n_otm_call_prices(atm_strike, n)
        puts, put_prices = self.context.get_n_otm_put_prices(atm_strike, n)

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


        ratios = []
        for delta in required_deltas:
            min_diff = math.inf
            put_min_diff_iv = None
            for put_delta, put_iv in put_deltas_and_ivs:
                try:
                    if abs(abs(put_delta) - delta) < min_diff:
                        min_diff = abs(abs(put_delta) - delta)
                        put_min_diff_iv = put_iv
                except Exception as e:
                    pass
                pass

            min_diff = math.inf
            call_min_diff_iv = None
            for call_delta, call_iv in call_deltas_and_ivs:
                try:
                    if abs(abs(call_delta) - delta) < min_diff:
                        min_diff = abs(abs(call_delta) - delta)
                        call_min_diff_iv = call_iv
                except Exception as e:
                    pass
                pass
            
            try:
                ratio = put_min_diff_iv/call_min_diff_iv
                ratios.append(ratio)
            except Exception:
                ratio = 0
            
        return sum(ratios)/len(ratios)
        pass

    def new_position_handler(self, spot) -> None:
        
        pass

    def existing_position_handler(self, spot):
        
        self.new_position_handler(spot)