from poke_env.battle import AbstractBattle, MoveCategory
from poke_env.player import Player

"""
Define your team here. You can use the team builder on https://play.pokemonshowdown.com/teambuilder 

Create a team and then copy the text here. 

Make sure to keep the triple quotes around the team text.

Make sure to use the Uber Format
"""

team = """
Ribombee @ Focus Sash  
Ability: Shield Dust  
Tera Type: Ghost  
EVs: 252 SpA / 4 SpD / 252 Spe  
Timid Nature  
IVs: 0 Atk  
- Sticky Web  
- Psychic Noise  
- Moonblast  
- Stun Spore  

Koraidon @ Life Orb  
Ability: Orichalcum Pulse  
Shiny: Yes  
Tera Type: Fire  
EVs: 252 Atk / 4 Def / 252 Spe  
Jolly Nature  
- Collision Course  
- Flare Blitz  
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

Zacian-Crowned @ Rusted Sword  
Ability: Intrepid Sword  
EVs: 252 Atk / 4 SpD / 252 Spe  
Jolly Nature  
- Swords Dance  
- Behemoth Blade  
- Crunch  
- Wild Charge  

Kyogre @ Choice Specs  
Ability: Drizzle  
EVs: 248 HP / 164 Def / 80 SpA / 16 Spe  
Bold Nature  
IVs: 0 Atk  
- Origin Pulse  
- Ice Beam  
- Calm Mind  
- Thunder  

Ho-Oh @ Heavy-Duty Boots  
Ability: Regenerator  
EVs: 252 HP / 252 Def / 4 SpD  
Impish Nature  
- Sacred Fire  
- Brave Bird  
- Whirlwind  
- Recover   

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

        estimated_opp_max_hp = (opp.base_stats["hp"] * 2) + 204
        estimated_opp_max_spe = ((2 * opp.base_stats["spe"] + 31 + 252 // 4) + 5) * 1.1
        opp_is_faster = me.stats["spe"] < estimated_opp_max_spe if estimated_opp_max_spe else False

        if not battle.available_moves:
            return self.choose_random_move(battle)

        best_move = battle.available_moves[0]
        best_score = -1

        for move in battle.available_moves:

            

            damage = self.calculate_damage(move, me, opp, battle)
            # Calculate max possible HP of opponent based on base stats and perfect EVs/IVs
            damage_fraction = damage / estimated_opp_max_hp if estimated_opp_max_hp else 0

            # If a move can KO the opponent, prioritize it
            if damage_fraction >= opp.current_hp_fraction:
                return self.create_order(move)

            if damage > best_score:
                best_score = damage
                best_move = move

        if self.should_switch(me, opp, battle, opp_is_faster):
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
        return base_damage * stab * type_multiplier * move.expected_hits

    def should_switch(self, me, opp, battle, opp_is_faster):
        if not battle.available_switches:
            return False

        # If current pokemon only has resisted moves, consider switching
        for move in me.moves.values():
            if move.type not in me.types and move.type.damage_multiplier(opp.type_1, opp.type_2, type_chart=battle._data.type_chart) < 1:
                return True

        # If opponent type has natural STAB on us, consider switching
        if opp.type_1 is not None and self.is_super_effective(opp.type_1, me.type_1, me.type_2, battle):
            if opp.type_2 is None:
                return True
            elif opp.type_2 and self.is_super_effective(opp.type_2, me.type_1, me.type_2, battle):
                return True

        return False

    def pick_best_switch(self, battle):
        opp = battle.opponent_active_pokemon
        candidates = battle.available_switches

        best_candidate = None
        best_score = float("-inf")

        for pokemon in candidates:
            score = self.score_switch_candidate(pokemon, opp, battle)
            if score > best_score:
                best_score = score
                best_candidate = pokemon

        return best_candidate

    def score_switch_candidate(self, candidate, opp, battle):
        score = 0.0

        # Defensive: penalize being weak to opponent's types
        for opp_type in (opp.type_1, opp.type_2):
            if opp_type is None:
                continue
            multiplier = opp_type.damage_multiplier(
                candidate.type_1,
                candidate.type_2,
                type_chart=battle._data.type_chart
            )
            score -= multiplier

        # Offensive: reward having super effective moves against opponent
        for candidate_type in (candidate.type_1, candidate.type_2):
            if candidate_type is None:
                continue
            multiplier = candidate_type.damage_multiplier(
                opp.type_1,
                opp.type_2,
                type_chart=battle._data.type_chart
            )
            score += multiplier

        score += candidate.current_hp_fraction
        return score

    def teampreview(self, battle: AbstractBattle):
        """
        SET THE TEAM ORDER HERE
        """
        return "/team 1"

    def opponent_has_super_effective_move(self, opp, me, battle):
        for move in opp.moves.values():
            if move.base_power == 0:
                continue
            if self.is_super_effective(move.type, me.type_1, me.type_2, battle):
                return True
        return False

    def is_super_effective(self, src_type, type_1, type_2, battle):
        return src_type.damage_multiplier(
            type_1,
            type_2,
            type_chart=battle._data.type_chart,
        ) >= 2.0

    def move_goes_first(self, move, opp_is_faster):
        if move.priority > 0:
            return True
        return opp_is_faster