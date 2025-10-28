from strategies.strategy import Strategy
from Greeks import Greeks
import math

class DeltaNeutralBundle_ExecAlgo(Strategy):
    def hedge(self, spot) -> None:
        return super().hedge(spot)
    
    def hedge_point(self, spot) -> bool:
        return super().hedge_point(spot)
    
    def position_management(self, spot) -> None:
        main_order_dict = {}
        number_of_bundles = len(self.context.strategy_args["option_bundle"])
        for bundle_index in range(number_of_bundles):
            result = self.check_build_or_exit(spot, bundle_index)
            if result == 0:
                continue
            add = True if result == 1 else False
            order_dict = self.get_orders_for_bundle(spot, bundle_index, add)
            self.add_orders_to_bundle_pf(order_dict, bundle_index)
            main_order_dict = self.merge_dictionaries(main_order_dict, order_dict)
            pass
        
        options = []
        quantities = []
        sell = []
        for option in main_order_dict.keys():
            options.append(option)
            quantities.append(abs(main_order_dict[option]))
            sell.append(main_order_dict[option] < 0)
        

        self.context.make_orders(options, sell, quantities)
        return
    
    def merge_dictionaries(self, main_dict : dict, new_dict : dict):
        for option in new_dict.keys():
            main_dict[option] = main_dict.get(option, 0) + new_dict[option]
        return main_dict
    
    def add_orders_to_bundle_pf(self, orders_for_bundle, bundle_index):
        for option in orders_for_bundle.keys():
            self.context.strategy_args["option_bundle_portfolio"][bundle_index][option] = \
            self.context.strategy_args["option_bundle_portfolio"][bundle_index].get(option, 0) + \
            orders_for_bundle[option]
        pass

    def new_position_handler(self, spot) -> None:
        self.context.strategy_args["option_bundle"] : list[dict] = []
        self.context.strategy_args["option_bundle_portfolio"] : list[dict] = []
        self.context.strategy_args["option_bundle_open"] : list[dict] = []
        return
    
    def existing_position_handler(self, spot):
        return self.new_position_handler(spot)
    

    def check_build_or_exit(self, spot, bundle_index):
        specifications = self.context.strategy_args["option_bundle"][bundle_index]
        """
        Option 1 price
        Option 2 price

        Build when: 
            Option 1 Price - Option 2 Price > Build Price
        
        Exit when:
            Option 1 Price - Option 2 Price < Exit Price
            or
            Switch is off

        returns:
            1 for add
            0 for nothing
            -1 for exit
        """
        option1 = specifications["option1"]
        option2 = specifications["option2"]
        build_price = specifications["build_price"]
        exit_price = specifications["exit_price"]
        
        p_option1, p_option2 = self.context.get_current_price([option1,option2])

        if not self.context.strategy_args["option_bundle_open"][bundle_index]:
            return -1
        if p_option1 - p_option2 > build_price:
            return 1
        if p_option1 - p_option2 < exit_price:
            return -1
        return 0

    def get_orders_for_bundle(self, spot, bundle_index, add : bool) -> dict:
        specifications = self.context.strategy_args["option_bundle"][bundle_index]
        if not add:
            return self.exit_position_orders(bundle_index)
        
        gcalc = Greeks()
        
        option1 = specifications["option1"]
        strike1 = int(option1[:-2])
        type1 = option1[-2:]
        option2 = specifications["option2"]
        strike2 = int(option2[:-2])
        type2 = option2[-2:]
        option_hedge = specifications["option_hedge"]
        strike_hedge = int(option_hedge[:-2])
        type_hedge = option_hedge[-2:]
        
        qty1 = specifications["qty1"]
        qty2 = specifications["qty2"]

        # subtract already done
        existingpf : dict = self.context.strategy_args["option_bundle_portfolio"][bundle_index]

        IV = self.context.straddle_IV(spot)

        ttm = self.context.timeToMaturity()
        del1 = gcalc.delta(type1, spot, strike1, ttm, IV, self.context.rfr)*qty1
        del2 = gcalc.delta(type2, spot, strike2, ttm, IV, self.context.rfr)*qty2

        del_hedge = gcalc.delta(type_hedge, spot, strike_hedge, ttm, IV, self.context.rfr)

        qty_hedge = -(del1 + del2)/del_hedge


        # Remove existing quantities for normalisation
        qty1 = qty1 - existingpf.get(option1, 0)
        qty2 = qty2 - existingpf.get(option2, 0)
        qty_hedge = qty_hedge - existingpf.get(option_hedge, 0)

        quantities = [abs(qty1), abs(qty2), abs(qty_hedge)]

        options = [option1, option2, option_hedge]
        sell = [
            qty1 < 0,
            qty2 < 0,
            qty_hedge < 0,
        ]
        quantities = self.normalise_quantities(quantities)
        
        if sum(quantities) == 0:
            return {}
        
        temp_dict = self.convert_orders_to_dict(options, quantities, sell)
        
        return temp_dict

    def exit_position_orders(self, bundle_index) -> dict:
        pf = self.context.strategy_args["option_bundle_portfolio"][bundle_index]
        
        options = []
        quantities = []
        sell = []

        for option in pf.keys():
            options.append(option)
            quantities.append(abs(pf[option]))
            sell.append(pf[option] > 0)
            pass

        quantities = self.normalise_quantities(quantities)

        if sum(quantities) == 0:
            return {}
        
        temp_dict = self.convert_orders_to_dict(options, quantities, sell)

        return temp_dict
    
    def convert_orders_to_dict(self, options, quantities, sell) -> dict:
        temp_dict = {}
        for i, option in enumerate(options):
            temp_dict[option] = quantities[i] *(-1 if sell[i] else 1)
        
        return temp_dict

    
    def normalise_quantities(self, quantities):
        maximum_number_of_lots_per_cycle = self.context.strategy_args[
            "lots_per_bundle_per_cycle"
        ]
        
        lot_size = self.context.lot_size
        maximum_quantity = 0
        
        for q in quantities:
            maximum_quantity = max(maximum_quantity, abs(q))
        
        if maximum_quantity == 0:
            return []
        multiplier = maximum_number_of_lots_per_cycle*lot_size/maximum_quantity
        
        # never increase position size more than double
        # Also useful when fully closing position sizes
        if multiplier > 1:
            multiplier = 1
        
        new_quantities = []
        for quantity in quantities:
            q = quantity*multiplier
            q = (int(q/lot_size))*lot_size
            new_quantities.append(q)
        
        return new_quantities