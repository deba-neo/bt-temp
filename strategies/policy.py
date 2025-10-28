from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # Only imports the below statements during type checking
    from BaseStraddle import BaseStraddle
from abc import ABC, abstractmethod
import math

"""
Default Policy Base
"""


class Policy(ABC):
    @property
    def context(self) -> BaseStraddle:
        return self._context

    @context.setter
    def context(self, context: BaseStraddle) -> None:
        self._context = context

    @abstractmethod
    def execute_policy(self, spot) -> None:
        pass


class DefaultPolicy(Policy):
    def execute_policy(self, spot) -> None:
        pass

    pass


"""
General Size Constructor Class
3 Targets : 
    - Size
    - Theta
    - Vega

"""


class Constructor(Policy):
    """
    Set lots_per_cycle
    """

    def execute_policy(self, spot) -> None:
        if self.is_target_reached():
            self.context.set_policy(DefaultPolicy())
            return
        
        self.context.change_position_size(
            self.context.policy_variables["lots_per_cycle"], decrease=False
        )


        pass

    def is_target_reached(self) -> bool:
        # target_function : function = self.context.policy_variables["target_function"]
        # progress_function : function = self.context.policy_variables["progress_function"]
        if (
            self.context.full_portfolio_size()
            >= self.context.policy_variables["size_target"]
        ):
            return True
        return False

    pass


class ThetaConstructor(Constructor):
    def is_target_reached(self) -> bool:
        if (
            self.context.greeks["portfolio_theta"]
            >= self.context.policy_variables["theta_target"]
        ):
            return True
        return False

    pass


class VegaConstructor(Constructor):
    def is_target_reached(self) -> bool:
        if (
            self.context.greeks["portfolio_vega"]
            <= self.context.policy_variables["vega_target"]
        ):
            return True
        return False

    pass


"""
General Size Destructor Class

3 Targets : 
    - Size
    - Theta
    - Vega

"""


class Destructor(Policy):
    def execute_policy(self, spot) -> None:
        if self.is_target_reached():
            self.context.set_policy(DefaultPolicy())
            return

        self.context.change_position_size(
            self.context.policy_variables["lots_per_cycle"], decrease=True
        )


        pass

    def is_target_reached(self) -> bool:
        if (
            self.context.full_portfolio_size()
            <= self.context.policy_variables["size_target"]
        ):
            return True
        return False


class ThetaDestructor(Destructor):
    def is_target_reached(self) -> bool:
        if (
            self.context.greeks["portfolio_theta"]
            <= self.context.policy_variables["theta_target"]
        ):
            return True
        return False

    pass


class VegaDestructor(Destructor):
    def is_target_reached(self) -> bool:
        if (
            self.context.greeks["portfolio_vega"]
            >= self.context.policy_variables["vega_target"]
        ):
            return True
        return False

    pass


"""
ATM Options Builder Class

Builds by buying ATM straddles only
Wings 

3 Targets : 
    - Size
    - Theta
    - Vega

"""


class ATMBuiler(Policy):
    def execute_policy(self, spot) -> None:
        if self.is_target_reached():
            self.context.set_policy(DefaultPolicy())
            return
        
        straddle_price, _ = self.context.atm_straddle_price(spot)
        movement = self.context.movement
        position = int(round(spot / float(movement))) * movement

        if not self.context.strategy_args["wings"]:
            left = self.context.policy_variables["size_target"] - self.context.full_portfolio_size()
            left = left/2
            if left < self.context.lot_size:
                self.context.set_policy(DefaultPolicy())
            
            self.context.naked_straddle(position, spot, left)
            return
        
        self.context.wings = (
            int(
                round(
                    self.context.strategy_args["wings"]
                    * straddle_price
                    / float(movement)
                )
            )
            * movement
        )

        self.context.strangle_with_wings(position, spot)


        pass

    def is_target_reached(self) -> bool:
        if (
            self.context.full_portfolio_size()
            >= self.context.policy_variables["size_target"]
        ):
            return True
        return False

    pass


class ATMThetaBuiler(ATMBuiler):
    def is_target_reached(self) -> bool:
        if (
            self.context.greeks["portfolio_theta"]
            >= self.context.policy_variables["theta_target"]
        ):
            return True
        return False


class ATMVegaBuiler(ATMBuiler):
    def is_target_reached(self) -> bool:
        if (
            self.context.greeks["portfolio_vega"]
            <= self.context.policy_variables["vega_target"]
        ):
            return True
        return False


"""
Specific Options Builder Class

Builds by buying selected options only
Wings 

3 Targets : 
    - Size
    - Theta
    - Vega

"""


class OptionBuiler(Policy):
    def execute_policy(self, spot):
        self.context.portfolio.update()
        return

    pass



"""
CustomPortfolioBuilder

Serves as:
 - Rolling Straddle Hedger/Creator
 - DeltaGamma Hedger

Functioning :
 - Cuts down a theoretical portfolio ["to_create_portfolio"] down to 0
 - This reflects as subtraction from actual portfolio
 - Used policy lots_per_cycle for speed of creation
 - Stops when theoretical portfolio is 0

 Example : 
    theoretical portfolio : {500CE:1000}
    changes in real portfolio : {500CE:-1000}
"""

class CustomPortfolioBuilder(Policy):
    def execute_policy(self, spot) -> None:
        if self.is_target_reached():
            self.context.set_policy(DefaultPolicy())
            return
        
        o,s,q = self.context.change_position_size(
            maximum_number_of_lots_per_cycle=self.context.policy_variables["lots_per_cycle"],
            decrease=True,
            portfolio=self.context.policy_variables["to_create_portfolio"]
        )
        n = len(o)
        for i in range(n):
            self.context.policy_variables["to_create_portfolio"][o[i]] -= q[i] if s[i] == True else -q[i]
    
    def is_target_reached(self):
        # print(self.context.policy_variables["to_create_portfolio"])
        print(self.context.policy_variables["to_create_portfolio"])
        for key, value in self.context.policy_variables["to_create_portfolio"].items():
            if math.floor(abs(value)/self.context.lot_size) != 0:
                return False
        return True
    

"""
Specific Options Builder Class

Builds by buying selected options only
Wings 

3 Targets : 
    - Size
    - Theta
    - Vega

"""


class ATMStraddleBuyer(Policy):
    def execute_policy(self, spot):
        if self.is_target_reached():
            self.context.set_policy(DefaultPolicy())
            return
        
        movement = self.context.movement
        position = int(round(spot / float(movement))) * movement
        
        self.context.strangle_long(position, spot)
        return

    def is_target_reached(self) -> bool:
        if (
            self.context.full_portfolio_size()
            >= self.context.policy_variables["size_target"]
        ):
            return True
        return False