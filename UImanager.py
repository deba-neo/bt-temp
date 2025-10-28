from BaseStraddle import BaseStraddle
from strategies import strategy, policy

from strategies.custom import (
    rollingstraddle,
    smartstraddle,
)
import warnings


class UIManager(object):
    """
    All UI Related Management Functions
    """
    def __init__(self, traders : list[BaseStraddle], strategy_mapper) -> None:
        # self.traders = {}

        # for i in range(len(traders)):
        #     self.traders[names[i]] = traders[i]
        #     pass

        self.traders = traders
        self.strategy_mapper = strategy_mapper

        self.function_mapper : dict[str, function] = {
            "set_new_target" : self.set_new_target,
            "decrease_size" : self.decrease_size,
            "increase_size" : self.increase_size,
            "change_demand" : self.change_demand,
            "update_ref_IV" : self.update_ref_IV,
            "ref_IV_toggle" : self.ref_IV_toggle,
            "change_strategy" : self.change_strategy,
            "change_expected_close" : self.change_expected_close,
            "change_expected_closing_IV" : self.change_expected_closing_IV,
            "update_strategy_args_items" : self.update_strategy_args_items,
            "close_position" : self.close_position,
            "open_position" : self.open_position,
            "turnoff_bundle" : self.turnoff_bundle,
            "turnon_bundle" : self.turnon_bundle,
            "add_option_bundle": self.add_option_bundle,
            "modify_option_bundle" : self.modify_option_bundle,
        }
        pass

    def config_reader(self, message):
        func = self.function_mapper[message["objective"]]
        trader = self.traders[message["name"]]
        try:
            func(message, trader)
        except Exception as e:
            warnings.warn("Invalid Input")
            pass
        pass

    def change_strategy(self, configs, trader : BaseStraddle):
        strat = configs["new_strategy"]
        trader.set_strategy(self.strategy_mapper[strat]())
        pass

    def change_demand(self, configs, trader : BaseStraddle):
        trader.demand = configs["demand"]
        pass

    def initial_option_ratio(self, configs):
        """
        List of options to begin with
        ATM : starts at atm
        Standing leg: sets standing leg for limit order
        """
        pass

    def add_option_list(self, configs):
        pass

    def ref_IV_toggle(self, configs, trader : BaseStraddle):
        trader.strategy_args["IVCalc"] = configs["IVCalc"]
        pass

    def set_build_IV(self, configs):
        pass

    def update_ref_IV(self, configs, trader : BaseStraddle):
        trader.strategy_args["refIV"] = configs["refIV"]
        pass

    def decrease_size(self, configs, trader : BaseStraddle):
        """
        Interfact into the destructor policy from the UI
        """
        trader.policy_variables["target"] = configs["target"]
        trader.policy_variables["lots_per_cycle"] = configs["lots_per_cycle"]


        if configs["target"] == "size":
            trader.policy_variables["size_target"] = configs["size_target"]
            trader.set_policy(policy.Destructor())
            pass
        elif configs["target"] == "theta":
            trader.policy_variables["theta_target"] = configs["theta_target"]
            trader.set_policy(policy.ThetaDestructor())
            pass
        elif configs["target"] == "vega":
            trader.policy_variables["vega_target"] = configs["vega_target"]
            trader.set_policy(policy.VegaDestructor())
            pass
        pass

    def increase_size(self, configs, trader : BaseStraddle):
        """
        Interfact into the destructor policy from the UI
        """
        trader.policy_variables["target"] = configs["target"]
        trader.policy_variables["lots_per_cycle"] = configs["lots_per_cycle"]


        if configs["target"] == "size":
            trader.policy_variables["size_target"] = configs["size_target"]
            trader.set_policy(policy.Constructor())
            pass
        elif configs["target"] == "theta":
            trader.policy_variables["theta_target"] = configs["theta_target"]
            trader.set_policy(policy.ThetaConstructor())
            pass
        elif configs["target"] == "vega":
            trader.policy_variables["vega_target"] = configs["vega_target"]
            trader.set_policy(policy.VegaConstructor())
            pass
        pass
    
    def set_new_target(self, configs, trader : BaseStraddle):
        """
        Sets Theta or Vega target and options are bought accordingly
        """
        # policy_variables["lots_per_cycle"] = configs["lots_per_cycle"]
        trader.demand = configs["lots_per_cycle"]*trader.lot_size
        trader.policy_variables["target"] = configs["target"]

        if configs["target"] == "size":
            trader.policy_variables["size_target"] = configs["size_target"]
            trader.set_policy(policy.ATMBuiler())
            pass
        elif configs["target"] == "theta":
            trader.policy_variables["theta_target"] = configs["theta_target"]
            trader.set_policy(policy.ATMThetaBuiler())
            pass
        elif configs["target"] == "vega":
            trader.policy_variables["vega_target"] = configs["vega_target"]
            trader.set_policy(policy.ATMVegaBuiler())
            pass
        pass

    def limit_order_choice(self, configs):
        """
        Best ask, bid
        """
        pass

    def square_off_size(self, configs, trader : BaseStraddle):
        """
        Theta, Vega, %
        """
        square_off_percent = configs["square_off_percent"]
        size = trader.full_portfolio_size()
        new_size = size*(100-square_off_percent)/100

        configs["target"] = "size"
        configs["size_target"] = new_size
        
        self.decrease_size(configs, trader)
        pass

    def change_expected_close(self, configs, trader : BaseStraddle):
        """
        Only for Smart Straddles, updates the expected close parameter
        """
        trader.strategy_args["expected_close"] = configs["expected_close"]
        pass
    
    def change_expected_closing_IV(self, configs, trader : BaseStraddle):
        """
        Only for Smart Straddles, updates the expected close parameter
        """
        trader.strategy_args["expected_closing_IV"] = configs["expected_closing_IV"]
        pass
    
    def update_strategy_args_items(self, configs : dict, trader : BaseStraddle):
        """
        Update multiple items in strategy args
        Keys present in configs will get updated
        """
        for key in configs.keys():
            if key == "objective" or key == "name":
                continue
            trader.strategy_args[key] = configs[key]
    
    def close_position(self, configs : dict, trader : BaseStraddle):
        trader.strategy_args["close_position"] = True
        pass

    def open_position(self, configs : dict, trader : BaseStraddle):
        trader.strategy_args["close_position"] = False
        pass
    
    def hedge_choice(self, configs):
        """
        Buy, Sell, IV, [Hedge IV?]
        """
        pass

    """
    DeltaNeutralBundle_ExecAlgo
    UI Methods
    """
    def turnoff_bundle(self, configs, trader : BaseStraddle):
        """
        Square off and not build a bundle
        """
        index = configs["index"]
        trader.strategy_args["option_bundle_open"][index] = False

    def turnon_bundle(self, configs, trader : BaseStraddle):
        """
        Square off and not build a bundle
        """
        index = configs["index"]
        trader.strategy_args["option_bundle_open"][index] = True

    def add_option_bundle(self, configs: dict, trader : BaseStraddle):
        try:
            option1 = configs["option1"]
            option2 = configs["option2"]
            option_hedge = configs["option_hedge"]
            build_price = configs["build_price"]
            exit_price = configs["exit_price"]
            qty1 = configs["qty1"]
            qty2 = configs["qty2"]
        except KeyError:
            warnings.warn("Invalid Input")
            return

        trader.strategy_args["option_bundle"].append(configs)
        trader.strategy_args["option_bundle_portfolio"].append({})
        trader.strategy_args["option_bundle_open"].append(True)
        pass

    def modify_option_bundle(self, configs: dict, trader : BaseStraddle):
        index = configs["index"]
        for key in configs.keys():
            if key == "objective" or key == "name" or key == "index":
                continue
            trader.strategy_args["option_bundle"][index][key] = configs[key]
        pass

    """
    
    """