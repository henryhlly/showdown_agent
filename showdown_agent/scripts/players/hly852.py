import math

from poke_env.battle import AbstractBattle, MoveCategory, SideCondition, PokemonType
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

Flutter Mane @ Life Orb 
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
- Play Rough  
- Behemoth Blade  
- Crunch  
- Wild Charge  

Kyogre @ Heavy Duty Boots
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
- Earthquake 
- Recover   

"""

class CustomAgent(Player):

    HAZARD_CONDITIONS = {
        "stealthrock": SideCondition.STEALTH_ROCK,
        "spikes": SideCondition.SPIKES,
        "toxicspikes": SideCondition.TOXIC_SPIKES,
        "stickyweb": SideCondition.STICKY_WEB,
    }

    POWDER_MOVES = {
        "stunspore", "sleeppowder", "poisonpowder", "spore", "cottonspore", "rage powder"
    }

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
            if move.base_power > 0:
                score = self.calculate_move_score(move, me, opp, battle)
            else:
                score = self.calculate_status_score(move, me, opp, battle)
            
            if score > best_score:
                best_score = score
                best_move = move

            # Logging for debugging purposes and analysis
        #     print(f"{move.id}: {score}")
        # print("================================")

        if best_score < 100 and self.should_switch(me, opp, battle):
            switch_target = self.pick_best_switch(battle)
            if switch_target:
                return self.create_order(switch_target)

        return self.create_order(best_move)

    def calculate_damage(self, move, user, target, battle):
        if move.base_power == 0:
            return 0

        level = user.level
        if move.category == MoveCategory.PHYSICAL:
            attack_stat = user.stats["atk"]
            defense_stat = ((2 * target.base_stats["def"]) + 5)
        else:
            attack_stat = user.stats["spa"]
            defense_stat = ((2 * target.base_stats["spd"]) + 5)

        if defense_stat is None or attack_stat is None:
            return 0

        power = move.base_power
        stab = 1.5 if move.type in user.types else 1.0
        type_multiplier = move.type.damage_multiplier(
            target.type_1, 
            target.type_2, 
            type_chart=battle._data.type_chart
        )

        base_damage = (((2 * level / 5 + 2) * power * (attack_stat / defense_stat)) / 50 + 2)
        return base_damage * stab * type_multiplier * move.expected_hits * 0.925

    def calculate_move_score(self, move, user, target, battle):
        estimated_target_hp = (target.base_stats["hp"] * 2) + 204

        damage = self.calculate_damage(move, user, target, battle)
        # Calculate max possible HP of opponent based on base stats and perfect EVs/IVs
        damage_fraction = damage / estimated_target_hp if estimated_target_hp else 0
        score = damage_fraction * 100

        # If a move can KO the opponent, prioritize it (1.15 is safety buffer)
        if damage_fraction >= target.current_hp_fraction * 1.15:
            score += 100

        return math.floor(score)

    def calculate_status_score(self, move, user, target, battle):
        if self.is_blocked_by_special_immunity(move, target):
            return 0

        # Hazards
        if move.id in self.HAZARD_CONDITIONS:
            if not battle.opponent_side_conditions.get(self.HAZARD_CONDITIONS[move.id]):
                return 200
            return 0

        # Boosts
        if move.boosts:
            if user.current_hp_fraction > 0.6 and not user.boosts:
                return 70
            return 20

        # Status
        if move.status is not None:
            if target.status is not None:
                return 0
            return 80

        # Recovery
        if move.id in ("recover", "roost", "moonlight", "softboiled"):
            missing_hp = 1 - user.current_hp_fraction
            return math.floor(100 * missing_hp)

        return -1

    def should_switch(self, me, opp, battle):
        if not battle.available_switches:
            return False

        no_good_moves = True
        for move in me.moves.values():
            if move.type in me.types or move.type.damage_multiplier(opp.type_1, opp.type_2, type_chart=battle._data.type_chart) > 1:
                no_good_moves = False
                break

        # If current pokemon only has resisted moves, switch
        if no_good_moves:
            return True

        # If opponent type has natural STAB on us, switch
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

        # Offensive: reward having STAB against opponent
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

    def is_super_effective(self, src_type, type_1, type_2, battle):
        return src_type.damage_multiplier(
            type_1,
            type_2,
            type_chart=battle._data.type_chart,
        ) >= 2.0

    def is_blocked_by_special_immunity(self, move, target):
        if move.status is None:
            return False
        
        # Powder moves (Grass is immune)
        if move.id in self.POWDER_MOVES:
            if PokemonType.GRASS in target.types:
                return True

        # Paralysis (Electric is immune)
        if move.status.name == "PAR" and PokemonType.ELECTRIC in target.types:
            return True

        # Poison/Toxic (Poison and Steel is immune)
        if move.status.name in ("PSN", "TOX"):
            if PokemonType.POISON in target.types or PokemonType.STEEL in target.types:
                return True

        # Burn (Fire is immune)
        if move.status.name == "BRN" and PokemonType.FIRE in target.types:
            return True

        return False

    def teampreview(self, battle: AbstractBattle):
        """
        SET THE TEAM ORDER HERE
        """
        return "/team 1"