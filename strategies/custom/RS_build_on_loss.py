from strategies.strategy import (
    Strategy,
    StraddlebyThree,
    ThetaGamma,
    TG_STD3_2DTE,
    ThetaGamma_HedgebyBuying,
)

from strategies.custom.rollingstraddle import (
    RollingStraddle,
)

from strategies import policy
from Greeks import Greeks
import math
from datetime import datetime


class RS_BuildOnLoss(RollingStraddle):
    def new_position_handler(self, spot) -> None:
        super().new_position_handler(spot)
        self.context.strategy_args["Neg-0.5-Hit"] = False
        self.context.strategy_args["Pos-0.5-Hit"] = False
        self.context.strategy_args["Neg-1-Hit"] = False
        self.context.strategy_args["Pos-1-Hit"] = False
        self.context.strategy_args["Neg-1.5-Hit"] = False
        self.context.strategy_args["Pos-1.5-Hit"] = False
        self.context.strategy_args["Neg-2-Hit"] = False
        self.context.strategy_args["Pos-2-Hit"] = False

        self.context.strategy_args["Neg-0.5-PNL"] = 0
        self.context.strategy_args["Pos-0.5-PNL"] = 0
        self.context.strategy_args["Neg-1-PNL"] = 0
        self.context.strategy_args["Pos-1-PNL"] = 0
        self.context.strategy_args["Neg-1.5-PNL"] = 0
        self.context.strategy_args["Pos-1.5-PNL"] = 0
        self.context.strategy_args["Neg-2-PNL"] = 0
        self.context.strategy_args["Pos-2-PNL"] = 0

        # self.context.strategy_args["Neg-0.5-Hit_Time"] = 0
        # self.context.strategy_args["Pos-0.5-Hit_Time"] = 0
        # self.context.strategy_args["Neg-1-Hit_Time"] = 0
        # self.context.strategy_args["Pos-1-Hit_Time"] = 0
        # self.context.strategy_args["Neg-1.5-Hit_Time"] = 0
        # self.context.strategy_args["Pos-1.5-Hit_Time"] = 0
        # self.context.strategy_args["Neg-2-Hit_Time"] = 0
        # self.context.strategy_args["Pos-2-Hit_Time"] = 0
        pass

    def position_management(self, spot) -> None:
        close_time = list(map(int, self.context.strategy_args["close_position_time"].split(":")))
        print(f"CATR: {self.context.high - self.context.low}")
        print(f"Max ATR: {self.context.strategy_args['expected_ATR']*0.8}")

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

            cpnl = self.context.total_pnl
            cpnl_p = cpnl / 100000

            self.context.strategy_args["final_outs"] = [
                self.context.strategy_args.get("Neg-0.5-PNL-final", (cpnl - self.context.strategy_args["Neg-0.5-PNL"])) *(1 if self.context.strategy_args["Neg-0.5-Hit"] else 0),
                self.context.strategy_args.get("Neg-1-PNL-final"  , (cpnl - self.context.strategy_args["Neg-1-PNL"  ])) *(1 if self.context.strategy_args["Neg-1-Hit"  ] else 0),
                self.context.strategy_args.get("Neg-1.5-PNL-final", (cpnl - self.context.strategy_args["Neg-1.5-PNL"])) *(1 if self.context.strategy_args["Neg-1.5-Hit"] else 0),
                self.context.strategy_args.get("Neg-2-PNL-final"  , (cpnl - self.context.strategy_args["Neg-2-PNL"  ])) *(1 if self.context.strategy_args["Neg-2-Hit"  ] else 0),
                self.context.strategy_args.get("Pos-0.5-PNL-final", (cpnl - self.context.strategy_args["Pos-0.5-PNL"])) *(1 if self.context.strategy_args["Pos-0.5-Hit"] else 0),
                self.context.strategy_args.get("Pos-1-PNL-final"  , (cpnl - self.context.strategy_args["Pos-1-PNL"  ])) *(1 if self.context.strategy_args["Pos-1-Hit"  ] else 0),
                self.context.strategy_args.get("Pos-1.5-PNL-final", (cpnl - self.context.strategy_args["Pos-1.5-PNL"])) *(1 if self.context.strategy_args["Pos-1.5-Hit"] else 0),
                self.context.strategy_args.get("Pos-2-PNL-final"  , (cpnl - self.context.strategy_args["Pos-2-PNL"  ])) *(1 if self.context.strategy_args["Pos-2-Hit"  ] else 0),
            ]

        cpnl = self.context.total_pnl
        cpnl_p = cpnl / 100000

        if not self.context.strategy_args["Neg-0.5-Hit"] and cpnl_p < -0.5:
            self.context.strategy_args["Neg-0.5-Hit"] = True
            self.context.strategy_args["Neg-0.5-PNL"] = cpnl

        if not self.context.strategy_args["Neg-1-Hit"] and cpnl_p < -1:
            self.context.strategy_args["Neg-1-Hit"] = True
            self.context.strategy_args["Neg-1-PNL"] = cpnl

        if not self.context.strategy_args["Neg-1.5-Hit"] and cpnl_p < -1.5:
            self.context.strategy_args["Neg-1.5-Hit"] = True
            self.context.strategy_args["Neg-1.5-PNL"] = cpnl

        if not self.context.strategy_args["Neg-2-Hit"] and cpnl_p < -2:
            self.context.strategy_args["Neg-2-Hit"] = True
            self.context.strategy_args["Neg-2-PNL"] = cpnl

        if not self.context.strategy_args["Pos-0.5-Hit"] and cpnl_p > 0.5:
            self.context.strategy_args["Pos-0.5-Hit"] = True
            self.context.strategy_args["Pos-0.5-PNL"] = cpnl

        if not self.context.strategy_args["Pos-1-Hit"] and cpnl_p > 1:
            self.context.strategy_args["Pos-1-Hit"] = True
            self.context.strategy_args["Pos-1-PNL"] = cpnl

        if not self.context.strategy_args["Pos-1.5-Hit"] and cpnl_p > 1.5:
            self.context.strategy_args["Pos-1.5-Hit"] = True
            self.context.strategy_args["Pos-1.5-PNL"] = cpnl

        if not self.context.strategy_args["Pos-2-Hit"] and cpnl_p > 2:
            self.context.strategy_args["Pos-2-Hit"] = True
            self.context.strategy_args["Pos-2-PNL"] = cpnl





        if self.context.strategy_args["Neg-0.5-Hit"] and cpnl - self.context.strategy_args["Neg-0.5-PNL"] < self.context.strategy_args["SL_from_entry"] :
            self.context.strategy_args["Neg-0.5-PNL-final"] = cpnl - self.context.strategy_args["Neg-0.5-PNL"]

        if self.context.strategy_args["Neg-1-Hit"] and cpnl - self.context.strategy_args["Neg-1-PNL"] < self.context.strategy_args["SL_from_entry"] :
            self.context.strategy_args["Neg-1-PNL-final"] = cpnl - self.context.strategy_args["Neg-1-PNL"]

        if self.context.strategy_args["Neg-1.5-Hit"] and cpnl - self.context.strategy_args["Neg-1.5-PNL"] < self.context.strategy_args["SL_from_entry"] :
            self.context.strategy_args["Neg-1.5-PNL-final"] = cpnl - self.context.strategy_args["Neg-1.5-PNL"]

        if self.context.strategy_args["Neg-2-Hit"] and cpnl - self.context.strategy_args["Neg-2-PNL"] < self.context.strategy_args["SL_from_entry"] :
            self.context.strategy_args["Neg-2-PNL-final"] = cpnl - self.context.strategy_args["Neg-2-PNL"]

        if self.context.strategy_args["Pos-0.5-Hit"] and cpnl - self.context.strategy_args["Pos-0.5-PNL"] < self.context.strategy_args["SL_from_entry"] :
            self.context.strategy_args["Pos-0.5-PNL-final"] = cpnl - self.context.strategy_args["Pos-0.5-PNL"]

        if self.context.strategy_args["Pos-1-Hit"] and cpnl - self.context.strategy_args["Pos-1-PNL"] < self.context.strategy_args["SL_from_entry"] :
            self.context.strategy_args["Pos-1-PNL-final"] = cpnl - self.context.strategy_args["Pos-1-PNL"]

        if self.context.strategy_args["Pos-1.5-Hit"] and cpnl - self.context.strategy_args["Pos-1.5-PNL"] < self.context.strategy_args["SL_from_entry"] :
            self.context.strategy_args["Pos-1.5-PNL-final"] = cpnl - self.context.strategy_args["Pos-1.5-PNL"]

        if self.context.strategy_args["Pos-2-Hit"] and cpnl - self.context.strategy_args["Pos-2-PNL"] < self.context.strategy_args["SL_from_entry"] :
            self.context.strategy_args["Pos-2-PNL-final"] = cpnl - self.context.strategy_args["Pos-2-PNL"]

        pass

    
class RS_BuildOnLoss_FullTracker(RollingStraddle):
    def new_position_handler(self, spot) -> None:
        super().new_position_handler(spot)
        self.context.strategy_args["DataStorage"] = []
    
    def position_management(self, spot) -> None:
        super().position_management(spot)
        self.context.strategy_args["DataStorage"].append(self.context.total_pnl)
        pass