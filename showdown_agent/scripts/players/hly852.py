from poke_env.battle import AbstractBattle, MoveCategory
from poke_env.player import Player

"""
Define your team here. You can use the team builder on https://play.pokemonshowdown.com/teambuilder 

Create a team and then copy the text here. 

Make sure to keep the triple quotes around the team text.

Make sure to use the Uber Format
"""

team = """
Archaludon @ Leftovers  
Ability: Stamina  
Shiny: Yes  
Tera Type: Steel  
EVs: 252 HP / 204 Def / 52 SpD  
Bold Nature  
IVs: 0 Atk  
- Flash Cannon  
- Body Press  
- Protect  
- Stealth Rock  

Urshifu-Rapid-Strike @ Choice Band  
Ability: Unseen Fist  
Tera Type: Fighting
EVs: 252 Atk / 4 Def / 252 Spe  
Adamant Nature  
- Surging Strikes  
- Aqua Jet  
- U-turn  
- Close Combat  

Koraidon @ Life Orb  
Ability: Orichalcum Pulse  
Shiny: Yes  
Tera Type: Fighting  
EVs: 252 Atk / 4 Def / 252 Spe  
Jolly Nature  
- Low Kick  
- Scale Shot  
- Swords Dance  
- Flame Charge  

Flutter Mane @ Choice Specs  
Ability: Protosynthesis  
Shiny: Yes  
Tera Type: Ghost  
EVs: 252 SpA / 4 SpD / 252 Spe  
Timid Nature  
IVs: 0 Atk  
- Shadow Ball  
- Moonblast  
- Psyshock  
- Power Gem  

Ogerpon-Hearthflame @ Hearthflame Mask  
Ability: Mold Breaker  
Tera Type: Fire  
EVs: 252 Atk / 4 SpD / 252 Spe  
Jolly Nature  
- Swords Dance  
- Ivy Cudgel  
- Horn Leech  
- Trailblaze  

Ursaluna-Bloodmoon @ Leftovers  
Ability: Mind's Eye  
Tera Type: Ground  
EVs: 4 Def / 252 SpA / 252 Spe  
Modest Nature  
IVs: 0 Atk  
- Calm Mind  
- Blood Moon  
- Earth Power  
- Moonlight  

"""

class CustomAgent(Player):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, team=team, **kwargs)

    def choose_move(self, battle: AbstractBattle):
        """
        DO NOT EDIT THIS FUNCTION.
        """
        me = battle.active_pokemon
        opp = battle.opponent_active_pokemon

        if me is None or opp is None:
            return self.choose_random_move(battle)

        return self._choose_move(battle)

    def _choose_move(self, battle: AbstractBattle):
        """
        DO EDIT THIS FUNCTION
        """
        me = battle.active_pokemon
        opp = battle.opponent_active_pokemon

        if not battle.available_moves:
            return self.choose_random_move(battle)

        best_move = battle.available_moves[0]
        best_score = -1

        for move in battle.available_moves:
            damage = self.calculate_damage(move, me, opp, battle)
            # Calculate max possible HP of opponent based on base stats and perfect EVs/IVs
            estimated_opp_max_hp = (opp.base_stats["hp"] * 2) + 204
            damage_fraction = damage / estimated_opp_max_hp if estimated_opp_max_hp else 0

            # If a move can KO the opponent, prioritize it
            if damage_fraction >= opp.current_hp_fraction:
                return self.create_order(move)

            if damage > best_score:
                best_score = damage
                best_move = move

        if self.should_switch(me, opp, battle, best_move):
            switch_target = self.pick_best_switch(battle)
            if switch_target:
                return self.create_order(switch_target)

        return self.create_order(best_move)


    def calculate_damage(self, move, user, target, battle):
        if move.base_power == 0:
            return 0.0

        level = user.level
        if move.category == MoveCategory.PHYSICAL:
            attack_stat = user.stats["atk"]
            defense_stat = target.base_stats["def"]
        else:
            attack_stat = user.stats["spa"]
            defense_stat = target.base_stats["spd"]

        if defense_stat is None or attack_stat is None:
            return 0.0

        power = move.base_power
        stab = 1.5 if move.type in user.types else 1.0
        type_multiplier = move.type.damage_multiplier(
            target.type_1, 
            target.type_2, 
            type_chart=battle._data.type_chart
        )

        base_damage = (((2 * level / 5 + 2) * power * attack_stat / defense_stat ) / 50 + 2)
        return base_damage * stab * type_multiplier

    def should_switch(self, me, opp, battle, best_move):
        if not battle.available_switches:
            print("No available switches.")
            return False

        print("Turn {}: Opponent's moves: {}".format(battle.turn, opp.moves))
        
        
        return me.current_hp_fraction < 0.25

    def pick_best_switch(self, battle):
        return max(battle.available_switches, key=lambda mon: mon.current_hp_fraction)

    def teampreview(self, battle: AbstractBattle):
        """
        SET THE TEAM ORDER HERE
        """
        return "/team 1"
