"""Testing if a build in Shadowrun 5th Edition is strong enough to reliably one-shot a grunt."""

import random
from dataclasses import dataclass
from typing import Final, Literal

import nextcord  # ty:ignore[unresolved-import]
from nextcord import Interaction, SlashOption  # ty:ignore[unresolved-import]
from nextcord.ext import commands  # ty:ignore[unresolved-import]

from apikeys import GUILD_IDS


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


def roll(*, num_dice: int, num_faces: int) -> int:
    """Return sum of dice rolls."""
    return sum(random.randint(1, num_faces) for _ in range(num_dice))


def roll_hits_ge(num_dice: int, *, num_faces: int = 6, target_ge: int = 5) -> int:
    """Return number of dice that hit or exceed target."""
    # Optional

    # Python 3.12 has random.binomialvariate(n, 1/3),
    # which replaces the per-die loop
    # when you run many simulations.
    # It's a speedup only, not a correctness fix.
    return sum(1 for _ in range(num_dice) if random.randint(1, num_faces) >= target_ge)


@dataclass(frozen=True)
class ExplosiveWeaponRadius:
    damage: int  # always positive
    armor_penetration: int  # usually negative
    blast_radius: int  # always positive

    def __post_init__(self):
        if self.blast_radius <= 0:
            raise ValueError("Blast must be positive.")
        if self.damage <= 0:
            raise ValueError("Damage must be positive.")


@dataclass(frozen=True)
class ExplosiveWeaponFalloff:
    damage: int  # always positive
    armor_penetration: int  # usually negative
    blast_falloff: int  # always negative

    def __post_init__(self):
        if self.blast_falloff > 0:
            raise ValueError("Blast must be negative.")
        if self.damage <= 0:
            raise ValueError("Damage must be positive.")


type ExplosiveWeapon = ExplosiveWeaponFalloff | ExplosiveWeaponRadius

AMMUNITION_TYPES: Final[dict[str, ExplosiveWeapon]] = {
    # grenades
    "Flash-bang": ExplosiveWeaponRadius(10, -4, 10),
    "Fragmentation Grenade": ExplosiveWeaponFalloff(18, 5, -1),
    "HE-Grenade": ExplosiveWeaponFalloff(16, -2, -2),
    # # rockets and missiles
    "Anti-Vehicle": ExplosiveWeaponFalloff(24, -4, -4),
    "Fragmentation Rocket/Missile": ExplosiveWeaponFalloff(23, 5, -1),
    "HE-Rocket/Missile": ExplosiveWeaponFalloff(21, -2, -2),
    # custom
    # "20 meter radius Emerald Splash": ExplosiveWeaponRadius(20, -2, 20),
    # "go the fuck to sleep": ExplosiveWeaponRadius(999_999_999, -12_000_000, 10),
    # "zeus/karthus/mephisto ult": ExplosiveWeaponRadius(15, -2, 10_000_000_000),
    # "brick": ExplosiveWeaponFalloff(15, -1, -999),
    # "Fireball": ExplosiveWeaponFalloff(30, 4, -2),
}

# { name: num scatter dice }
WEAPON_TYPES: Final[dict[str, int]] = {
    "Standard Grenade": 1,
    "Aerodynamic Grenade": 2,
    "Grenade Launcher": 3,
    "Missile Launcher": 4,
    "Rocket Launcher": 5,
}


@dataclass(frozen=True, slots=True, kw_only=True)
class GruntCheckResult:
    damage_dealt: int
    grunt_killed: bool
    hit_type: Literal["direct hit", "scatter hit", "miss"]


def grunt_check_explosives(
    dice_pool: int,
    num_scatter_dice: int,  # 1-5
    weapon: ExplosiveWeapon,
) -> GruntCheckResult:
    def calculate_damage(
        weapon: ExplosiveWeapon,
        *,
        negative_damage_from_scatter_falloff_decay: int = 0,
    ) -> int:
        resistance_hits = Grunt.damage_resistance_test(weapon.armor_penetration)
        return (
            weapon.damage - resistance_hits + negative_damage_from_scatter_falloff_decay
        )

    player_hits = roll_hits_ge(dice_pool)

    if player_hits >= 3:
        # direct hit
        damage = calculate_damage(weapon)
        return GruntCheckResult(
            damage_dealt=damage,
            grunt_killed=damage >= Grunt.health,
            hit_type="direct hit",
        )
    # miss; calculate scatter from explosion

    # flashbang
    if isinstance(weapon, ExplosiveWeaponRadius):
        scatter_radius_meters = (
            roll(num_dice=num_scatter_dice, num_faces=6) - player_hits
        )
        scatter_hits = scatter_radius_meters <= weapon.blast_radius
        if scatter_hits:
            # scatter hits
            damage = calculate_damage(weapon)
            return GruntCheckResult(
                damage_dealt=damage,
                grunt_killed=damage >= Grunt.health,
                hit_type="scatter hit",
            )
        # scatter misses, 0 damage, grunt survives
        return GruntCheckResult(
            damage_dealt=0,
            grunt_killed=False,
            hit_type="miss",
        )

    # anything but flashbang
    scatter_radius_meters = roll(num_dice=num_scatter_dice, num_faces=6) - player_hits
    damage_falloff_decay = (
        weapon.blast_falloff * scatter_radius_meters
    )  # always negative or 0

    damage = calculate_damage(
        weapon,
        negative_damage_from_scatter_falloff_decay=damage_falloff_decay,
    )
    if damage <= 0:
        # scatter misses, 0 damage, grunt survives
        return GruntCheckResult(
            damage_dealt=0,
            grunt_killed=False,
            hit_type="miss",
        )

    return GruntCheckResult(
        damage_dealt=damage,
        grunt_killed=damage >= Grunt.health,
        hit_type="scatter hit",
    )


def grunt_check_gun(
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
    player_hits = min(player_hits, accuracy)  # capped by accuracy
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


def grunt_check_indirect_spell(
    force: int,  # always positive
    dice_pool: int,  # always positive
    radius_type: str,  # not implemented, only matters for scatter
    grunt_health: int = 10,
) -> GruntCheckResult:
    player_hits = roll_hits_ge(dice_pool)
    hit = player_hits >= 3
    if hit:
        net_hits = player_hits - 3
        damage = net_hits + force
        armor_penetration = -force
        resistance_hits = Grunt.damage_resistance_test(armor_penetration)
        net_damage = damage - resistance_hits
        return GruntCheckResult(
            damage_dealt=net_damage,
            grunt_killed=net_damage >= grunt_health,
            hit_type="direct hit",
        )
    # miss
    # TODO: scatter
    num_scatter_dice = 2
    return GruntCheckResult(damage_dealt=0, grunt_killed=False, hit_type="miss")


class ShadowrunGruntCheck(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.bot = client
        self.test_count = 10_000

    @nextcord.slash_command(
        name="sr5e_grunt_check",
        description="Check if the build is strong enough to be allowed to exist.",
        guild_ids=GUILD_IDS,
    )
    async def sr5e_grunt_check(
        self,
        interaction: Interaction[commands.Bot],
        damage_value: int,
        defense_penalty: int,
        armor_pierce: int,
        die_pool: int = SlashOption(min_value=0, max_value=999),
        accuracy: int = SlashOption(min_value=0, max_value=999),
    ):
        await interaction.response.defer()
        num_kills = sum(
            1
            if grunt_check_gun(
                die_pool,
                defense_penalty,
                damage_value,
                armor_pierce,
                accuracy,
            ).grunt_killed
            else 0
            for _ in range(self.test_count)
        )
        await interaction.followup.send(
            f"die_pool: {die_pool:,}\n"
            f"defense_penalty: {defense_penalty:,} {'(should probably be negative)' if defense_penalty > 0 else ''}\n"
            f"damage_value: {damage_value:,} {'(should probably be positive)' if damage_value < 0 else ''}\n"
            f"armor_pierce: {armor_pierce:,} {'(should probably be negative)' if armor_pierce > 0 else ''}\n"
            f"accuracy: {accuracy:,}\n"
            f"Success rate estimate: {num_kills / self.test_count * 100:.2f}% "
            f"({num_kills:,} out of {self.test_count:,})",
        )

    @nextcord.slash_command(
        name="sr5e_grunt_check_explosive",
        description="Check if the build is strong enough to be allowed to exist.",
        guild_ids=GUILD_IDS,
    )
    async def sr5e_grunt_check_explosive(
        self,
        interaction: Interaction[commands.Bot],
        die_pool: int,
        weapon: str = SlashOption(choices=WEAPON_TYPES.keys()),
        ammunition: str = SlashOption(choices=AMMUNITION_TYPES.keys()),
    ):
        await interaction.response.defer()
        num_scatter_dice = WEAPON_TYPES[weapon]

        num_direct_hits = 0
        num_direct_hits_kills = 0
        num_scatter_hits = 0
        num_scatter_hits_kills = 0
        num_misses = 0
        for _ in range(self.test_count):
            result = grunt_check_explosives(
                die_pool,
                num_scatter_dice,
                AMMUNITION_TYPES[ammunition],
            )
            if result.hit_type == "direct hit":
                num_direct_hits += 1
                if result.grunt_killed:
                    num_direct_hits_kills += 1
            elif result.hit_type == "scatter hit":
                num_scatter_hits += 1
                if result.grunt_killed:
                    num_scatter_hits_kills += 1
            else:
                num_misses += 1
        num_kills = num_direct_hits_kills + num_scatter_hits_kills
        verb = (
            "kills"
            if ammunition not in {"Flash-bang", "go the fuck to sleep"}
            else "stuns"
        )
        await interaction.followup.send(
            f"die_pool: {die_pool:,}\n"
            f"weapon: {weapon} "
            f"(num_scatter_dice: {num_scatter_dice:,})\n"
            f"ammunition: {ammunition}\n"
            f"\n"
            f"Direct hits estimate: {num_direct_hits / self.test_count * 100:.2f}% "
            f"({num_direct_hits:,} out of {self.test_count:,}) "
            f"({verb} {num_direct_hits_kills:,} out of {num_direct_hits:,})\n"
            f"Scatter hits estimate: {num_scatter_hits / self.test_count * 100:.2f}% "
            f"({num_scatter_hits:,} out of {self.test_count:,}) "
            f"({verb} {num_scatter_hits_kills:,} out of {num_scatter_hits:,})\n"
            f"Misses estimate: {num_misses / self.test_count * 100:.2f}% "
            f"({num_misses:,} out of {self.test_count:,})\n"
            f"\n"
            f"**"
            f"Success rate estimate: {num_kills / self.test_count * 100:.2f}% "
            f"({num_kills:,} out of {self.test_count:,})"
            f"**"
        )

    @nextcord.slash_command(
        name="sr5e_grunt_check_indirect_spell",
        description="Check if the build is strong enough to be allowed to exist.",
        guild_ids=GUILD_IDS,
    )
    async def sr5e_grunt_check_indirect_spell(
        self,
        interaction: Interaction[commands.Bot],
        die_pool: int = SlashOption(min_value=1),
        force: int = SlashOption(min_value=1),
        radius_type: str = SlashOption(choices=["Force"]),
    ) -> None:
        await interaction.response.defer()
        num_kills = sum(
            grunt_check_indirect_spell(
                force,
                die_pool,
                radius_type,
            ).grunt_killed
            for _ in range(self.test_count)
        )
        await interaction.followup.send(
            f"die_pool: {die_pool:,}\n"
            f"force: {force:,}\n"
            f"radius_type: {radius_type}\n"
            f"Success rate estimate: {num_kills / self.test_count * 100:.2f}% "
            f"({num_kills:,} out of {self.test_count:,})"
            f"\nTODO: scatter (currently a miss is just a miss)"
        )


def setup(client: commands.Bot) -> None:
    client.add_cog(ShadowrunGruntCheck(client))
