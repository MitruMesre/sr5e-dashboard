from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from math import comb
from typing import Final, Literal


class Grunt:
    health: Final = 10
    body: Final = 4
    armor: Final = 12
    intuition_plus_reaction: Final = 7

    @staticmethod
    def defense_test(
        defense_penalty: int,  # usually negative
    ):
        num_dice = max(
            Grunt.intuition_plus_reaction + defense_penalty,
            0,
        )  # minimum of 0
        return roll_hits_ge(num_dice)

    @staticmethod
    def damage_resistance_test(
        armor_penetration: int,  # usually negative
    ):
        net_armor = max(Grunt.armor + armor_penetration, 0)  # minimum of 0
        return roll_hits_ge(Grunt.body + net_armor)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExactGruntCheckResult:
    chance_to_hit: Fraction
    chance_to_kill: Fraction
    expected_damage: Fraction  # includes misses (a miss counts as 0 damage)

    @property
    def expected_damage_on_hit(self) -> Fraction:
        """Expected damage given that the attack hit (misses excluded)."""
        if self.chance_to_hit == 0:
            return Fraction(0)  # can never hit, so there is no "on hit" case
        return self.expected_damage / self.chance_to_hit

    def __str__(self):
        return (
            f"Chance to hit: {self.chance_to_hit:.2%}\n"
            f"Chance to kill: {self.chance_to_kill:.2%}\n"
            f"Expected damage on hit: {self.expected_damage_on_hit:.2f}"
        )


def hit_chance(*, num_faces: int, target_ge: int) -> Fraction:
    """Chance that a single die is >= the target."""
    hit_faces = max(0, min(num_faces, num_faces - target_ge + 1))
    return Fraction(hit_faces, num_faces)


def hits_pmf(
    num_dice: int,
    *,
    num_faces: int = 6,
    target_ge: int = 5,
) -> list[Fraction]:
    """pmf[k] = exact probability of exactly k hits."""
    n = max(num_dice, 0)
    p = hit_chance(num_faces=num_faces, target_ge=target_ge)
    q = 1 - p
    return [comb(n, k) * p**k * q ** (n - k) for k in range(n + 1)]


def sr5e_grunt_check_gun_exact(
    dice_pool: int,  # always positive
    defense_penalty: int,  # usually negative
    damage_value: int,  # always positive
    armor_penetration: int,  # usually negative
    accuracy: int,  # upper bound for player_hits, always positive
) -> ExactGruntCheckResult:
    """Calculate the odds of one-shotting a grunt with a gun."""
    # attack hits, with the limit applied (extra hits collapse onto the cap)
    # you can't get more hits than dice, so the cap never needs to exceed dice_pool
    max_hits = min(accuracy, dice_pool)
    num_hits_pmf = [Fraction(0)] * (max_hits + 1)
    for num_hits, probability in enumerate(hits_pmf(dice_pool)):
        num_hits_pmf[min(num_hits, max_hits)] += probability

    defense_hits_pmf = hits_pmf(Grunt.intuition_plus_reaction + defense_penalty)
    net_armor = max(Grunt.armor + armor_penetration, 0)  # minimum of 0
    resistance_hits_pmf = hits_pmf(Grunt.body + net_armor)

    chance_to_hit = Fraction(0)
    chance_to_kill = Fraction(0)
    expected_damage = Fraction(0)

    for (num_hits, probability_of_num_hits), (
        defense_hits,
        probability_of_defense_hits,
    ) in product(
        enumerate(num_hits_pmf),
        enumerate(defense_hits_pmf),
    ):
        if defense_hits >= num_hits:  # miss: ties go to the defender
            continue
        # todo: transposition table since the only difference between
        # loops is (num_hits - defense_hits), which has duplicates
        weight = probability_of_num_hits * probability_of_defense_hits
        chance_to_hit += weight
        modified_damage_value = damage_value + (num_hits - defense_hits)
        for resistance_hits, probability_of_resistance_hits in enumerate(
            resistance_hits_pmf,
        ):
            final_damage = max(
                0,
                modified_damage_value - resistance_hits,
            )  # minimum of 0
            expected_damage += weight * probability_of_resistance_hits * final_damage
            if final_damage >= Grunt.health:
                chance_to_kill += weight * probability_of_resistance_hits

    return ExactGruntCheckResult(
        chance_to_hit=chance_to_hit,
        chance_to_kill=chance_to_kill,
        expected_damage=expected_damage,
    )


if __name__ == "__main__":  # tests
    import random

    @dataclass(frozen=True, slots=True, kw_only=True)
    class GruntCheckResult:
        damage_dealt: int
        grunt_killed: bool
        hit_type: Literal["direct hit", "scatter hit", "miss"]

    def roll_hits_ge(num_dice: int, *, num_faces: int = 6, target_ge: int = 5) -> int:
        """Return number of dice that hit or exceed target."""
        return sum(
            1 for _ in range(num_dice) if random.randint(1, num_faces) >= target_ge
        )

    def sr5e_grunt_check_gun(
        dice_pool: int,  # always positive
        defense_penalty: int,  # usually negative
        damage_value: int,
        armor_penetration: int,  # usually negative
        accuracy: int,  # upper bound for player_hits
    ) -> GruntCheckResult:
        """Simulate an attack on a grunt, with the objective of one-shotting it."""
        if damage_value < 0:
            raise ValueError("damage_value must be positive")

        player_hits = roll_hits_ge(dice_pool)
        player_hits = min(player_hits, accuracy)
        defense_hits = Grunt.defense_test(defense_penalty)

        if defense_hits >= player_hits:  # miss
            return GruntCheckResult(damage_dealt=0, grunt_killed=False, hit_type="miss")

        net_hits = player_hits - defense_hits

        modified_damage_value = damage_value + net_hits
        resistance_hits = Grunt.damage_resistance_test(armor_penetration)
        final_damage = modified_damage_value - resistance_hits

        killed_grunt = final_damage >= Grunt.health
        return GruntCheckResult(
            damage_dealt=max(0, final_damage),  # never log negative
            grunt_killed=killed_grunt,
            hit_type="direct hit",
        )

    # --- hit_chance / hits_pmf basics ---
    assert hit_chance(num_faces=6, target_ge=5) == Fraction(1, 3)
    assert hit_chance(num_faces=6, target_ge=1) == 1  # every face hits
    assert hit_chance(num_faces=6, target_ge=7) == 0  # no face hits

    assert hits_pmf(0) == [1]
    assert hits_pmf(-3) == [1]  # negative pool behaves like 0 dice
    assert hits_pmf(2) == [Fraction(4, 9), Fraction(4, 9), Fraction(1, 9)]
    for n in range(0, 30):
        assert sum(hits_pmf(n)) == 1

    # --- exact function: deterministic edge cases ---
    # no attack dice -> can never hit
    r = sr5e_grunt_check_gun_exact(0, 0, 9, 0, 7)
    assert r.chance_to_hit == 0 and r.chance_to_kill == 0
    assert r.expected_damage == 0 and r.expected_damage_on_hit == 0

    # accuracy 0 -> every hit is capped to 0, so it never beats the defense
    r = sr5e_grunt_check_gun_exact(12, 0, 9, 0, 0)
    assert r.chance_to_hit == 0

    # grunt has 0 defense dice (7 - 7), so one attack die hits with p = 1/3
    r = sr5e_grunt_check_gun_exact(1, -7, 9, 0, 5)
    assert r.chance_to_hit == Fraction(1, 3)

    # huge DV: the resistance test can't save the grunt, so kill == hit
    r = sr5e_grunt_check_gun_exact(6, -2, 100, 0, 6)
    assert r.chance_to_kill == r.chance_to_hit

    # general sanity: probabilities are valid and kill implies hit
    r = sr5e_grunt_check_gun_exact(12, -2, 9, -4, 7)
    assert 0 <= r.chance_to_kill <= r.chance_to_hit <= 1
    assert r.expected_damage_on_hit >= r.expected_damage  # dividing by p <= 1

    # --- exact vs Monte Carlo (loose tolerance, fixed seed) ---
    random.seed(0)
    runs = 20_000
    args = (12, -2, 9, -4, 7)
    sims = [sr5e_grunt_check_gun(*args) for _ in range(runs)]
    exact = sr5e_grunt_check_gun_exact(*args)

    sim_hit = sum(s.hit_type != "miss" for s in sims) / runs
    sim_kill = sum(s.grunt_killed for s in sims) / runs
    hits = [s.damage_dealt for s in sims if s.hit_type != "miss"]
    sim_dmg_on_hit = sum(hits) / len(hits)

    assert abs(sim_hit - float(exact.chance_to_hit)) < 0.02
    assert abs(sim_kill - float(exact.chance_to_kill)) < 0.02
    assert abs(sim_dmg_on_hit - float(exact.expected_damage_on_hit)) < 0.3

    # a huge accuracy is the same as "no limit" (accuracy == dice_pool)
    a = sr5e_grunt_check_gun_exact(12, -2, 9, -4, 999)
    b = sr5e_grunt_check_gun_exact(12, -2, 9, -4, 12)
    assert a == b

    print(exact)
    print("all checks passed")

if __name__ != "__main__":  # bot
    import nextcord  # ty:ignore[unresolved-import]
    from nextcord import Interaction, SlashOption  # ty:ignore[unresolved-import]
    from nextcord.ext import commands  # ty:ignore[unresolved-import]

    from apikeys import GUILD_IDS

    class ShadowrunGruntCheckExact(commands.Cog):
        def __init__(self, client: commands.Bot) -> None:
            self.bot = client

        @nextcord.slash_command(
            name="sr5e_grunt_check_exact",
            description="Check if the build is strong enough to be allowed to exist.",
            guild_ids=GUILD_IDS,
        )
        async def sr5e_grunt_check(
            self,
            interaction: Interaction[commands.Bot],
            dice_pool: int = SlashOption(min_value=0, max_value=99),
            defense_penalty: int = SlashOption(
                description="Usually negative.",
                min_value=-99,
                max_value=99,
            ),
            damage_value: int = SlashOption(min_value=0, max_value=99),
            armor_penetration: int = SlashOption(
                description="Usually negative.",
                min_value=-99,
                max_value=99,
            ),
            accuracy: int = SlashOption(min_value=0, max_value=99),
        ):
            await interaction.response.defer()
            result = sr5e_grunt_check_gun_exact(
                dice_pool,
                defense_penalty,
                damage_value,
                armor_penetration,
                accuracy,
            )
            await interaction.followup.send(
                f"dice_pool: {dice_pool:,}\n"
                f"defense_penalty: {defense_penalty:,}\n"
                f"damage_value: {damage_value:,}\n"
                f"armor_penetration: {armor_penetration:,}\n"
                f"accuracy: {accuracy:,}\n\n"
                f"{result}",
            )

    def setup(client: commands.Bot) -> None:
        client.add_cog(ShadowrunGruntCheckExact(client))
