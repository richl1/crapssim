"""My Strategies"""

import typing

from crapssim.bet import Come, DontCome, DontPass, Field, PassLine, Place
from crapssim.strategy.odds import (
    DontPassOddsMultiplier,
    OddsMultiplier,
    PassLineOddsMultiplier,
)
from crapssim.strategy.single_bet import (
    BetCome,
    BetDontPass,
    BetField,
    BetPassLine,
    BetPlace,
    StrategyMode,
)
from crapssim.strategy.tools import (
    AddIfNotBet,
    AddIfPointOff,
    AddIfPointOn,
    AddIfTrue,
    AggregateStrategy,
    CountStrategy,
    Player,
    RemoveByType,
    RemoveIfTrue,
    Strategy,
    Table,
    WinProgression,
)

class HeatSeeker(Strategy):
    """HeatSeeker Strategy Rules:
    1. Bet not more than 6 units per shooter
    2. Bet 1st Come bet after Pass point is set by other players
    3. If Come/Pass points = 6/8, remove the Place bet
    4. Bet new Come/Pass/Place (6/8) bets under these rules:
        a. Never have move that 4 Come, Pass, and Place bets
        b. Never have > 3 units "at_risk" if a seven rolls: at_risk = 
                +sum of Come/Pass contract bets
                +sum of Place bets
                - 1 (if won +1 or more for this shooter)
                - 1 (if new bet includes Come or Pass)
        d. Prefer new 6/8 place bets to new Come/Pass bets.
        e. Remove Place bets to meet "at_risk" rule
    """
    def __init__(
        self,
        pass_come_amount: float = 5,
        six_eight_amount: float = 6,
        ):
        
        super().__init__()
        self.pass_come_amount = float(pass_come_amount)
        self.six_eight_amount = float(six_eight_amount)
        self.shooter_budget: float = 6 * self.pass_come_amount
        self.bankroll_new_shooter: float = 0

    def completed(self, player: Player) -> bool:
        """The strategy is completed if the player has no bets on the table, and the players
        bankroll is too low to make any of the other bets.

        Parameters
        ----------
        player
            The Player whose bankroll and bets to check.

        Returns
        -------
        True if the strategy can't continue, otherwise False.
        """
        return (
            len(player.bets) == 0
            and player.bankroll < self.pass_come_amount
            and player.bankroll < self.six_eight_amount
        )    
    
    def get_pass_line_come_points(self, player: Player) -> list[int]:
        """Get the point number (or the table point number in the case of PassLine) for any PassLine
        or Come bets on the table.

        Parameters
        ----------
        player
            The player to check the bets for.

        Returns
        -------
        A list of integers of the points for the PassLine and Come bets.
        """
        pass_line_come_points = []
        for number in (4, 5, 6, 8, 9, 10):
            if (
                player.table.point.number == number
                and PassLine(self.pass_come_amount) in player.bets
            ):
                pass_line_come_points.append(number)
            elif Come(self.pass_come_amount, number) in player.bets:
                pass_line_come_points.append(number)
        return pass_line_come_points

    def update_bets(self, player: Player, table: Table) -> None:
        """If the player has less than 2 PassLine and Come bets, make the bet (depending on whether
        the point is on or off.) If the point is on, place the 6 and 8 unless there is a PassLine or
        Come bet with those then move them to the 5 or 9.

        Parameters
        ----------
        player
            The player to check on and make the bets for.
        """
        
        # Remove all Place bets.  Will add back later if allowed.
        # This simplifies the code by reducing the match - case conditions.
        for x in player.bets:
            if isinstance(x, (Place)):
                player.remove_bet(x)        

        points_bet = self.get_pass_line_come_points(player)
        pass_come_count = len(points_bet)

        # No bets on new shooter's 1st roll
        # Save the bankroll at Shooter's 1st roll to enforce per-shooter budget -- TBD
        if table.new_shooter:   
            self.bankroll_new_shooter = player.bankroll
            if player.bankroll >= 6 * self.pass_come_amount:
                self.shooter_budget = 6 * self.pass_come_amount
            else:
                self.shooter_budget = player.bankroll
            return  
        
        match pass_come_count:
            case 0 | 1:
            # Add up to 3 new bets: Come/PassLine and 6 and/or 8 where not a point
                BetCome(self.pass_come_amount, StrategyMode.ADD_IF_POINT_ON)
                BetPassLine(self.pass_come_amount, StrategyMode.ADD_IF_POINT_OFF)

                if (6 not in points_bet):   #Place the 6 if not a point
                    BetPlace({6: self.six_eight_amount}, skip_point=False).update_bets(player)
                if (8 not in points_bet):   #Place the 8 if not a point
                    BetPlace({8: self.six_eight_amount}, skip_point=False).update_bets(player)
                return
            
            case 2: #Add up to 2 new bets
                place_count = 0
                #prefer to Place 6 or 8 before Come/ PassLine
                if (6 not in points_bet) or (8 not in points_bet):
                    if (6 not in points_bet):
                        BetPlace({6: self.six_eight_amount}, skip_point=False).update_bets(player)
                        place_count += 1    
                    elif (8 not in points_bet):
                        BetPlace({8: self.six_eight_amount}, skip_point=False).update_bets(player)
                        place_count += 1
                    return  
                
                if place_count <= 1:    #Add a Come/PassLine bet too if 0 or 1 Place bets made.
                    BetCome(self.pass_come_amount, StrategyMode.ADD_IF_POINT_ON)
                    BetPassLine(self.pass_come_amount, StrategyMode.ADD_IF_POINT_OFF)
                    return
            
            case 3: # Add a Come/PassLine bet -- allowed since it wins on a 7 and up to 4 points are allowed.
                    # Adding a Place bet is not allowed because > 3 units at risk
                BetCome(self.pass_come_amount, StrategyMode.ADD_IF_POINT_ON)
                BetPassLine(self.pass_come_amount, StrategyMode.ADD_IF_POINT_OFF)
                return
            
            case 4 : # No new bets - Max 4 points covered.
                return
            
            case 5 : # This case should never run.  TBD raise an exemption
                return
        
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(pass_come_amount={self.pass_come_amount}, "
            f"six_eight_amount={self.six_eight_amount}, "
        )

   