use rand::RngExt;
use thousands::Separable;

fn main() {
    let mut rng = rand::rng();
    let atk = Attacker { dice_pool: 10 };
    let weapon = Weapon {
        defense_penalty: 0,
        damage_value: 10,
        armor_penetration: -2,
        accuracy: 6,
    };
    let grunt = Grunt::default();

    let result = (0..10_000)
        .map(|_| grunt_check_simulation(&mut rng, &atk, &weapon, &grunt))
        .filter(|result| result.grunt_status == GruntStatus::Dead)
        .count();
    println!(
        "killed {} out of 10,000 grunts.",
        result.separate_with_commas()
    );
    // should be around 1,077
}

struct Attacker {
    dice_pool: u64,
}

struct Grunt {
    body: u64,
    willpower: u64,
    armor: u64,
    intuition_plus_reaction: u64,
}

impl Grunt {
    fn health(&self) -> u64 {
        let base = self.body.max(self.willpower);
        base.div_ceil(2) + 8
    }
    fn defense_test(&self, rng: &mut impl rand::Rng, defense_penalty: i64) -> u64 {
        let num_dice = (self.intuition_plus_reaction as i128)
            .saturating_add(defense_penalty as i128)
            .clamp(0, u64::MAX as i128) as u64;
        roll_hits_ge(rng, num_dice, 6, 5)
    }
    fn damage_resistance_test(&self, rng: &mut impl rand::Rng, armor_penetration: i64) -> u64 {
        let net_armor = (self.armor as i128)
            .saturating_add(armor_penetration as i128)
            .clamp(0, u64::MAX as i128) as u64;
        roll_hits_ge(rng, self.body + net_armor, 6, 5)
    }
}
impl Default for Grunt {
    fn default() -> Self {
        Self {
            body: 4,
            willpower: 4,
            armor: 12,
            intuition_plus_reaction: 7,
        }
    }
}

struct Weapon {
    defense_penalty: i64,
    damage_value: u64,
    armor_penetration: i64,
    accuracy: u64,
}

fn roll_hits_ge(rng: &mut impl rand::Rng, num_dice: u64, num_faces: u64, target_ge: u64) -> u64 {
    // todo: naive implementation
    (0..num_dice)
        .map(|_| rng.random_range(1..=num_faces))
        .filter(|&roll| roll >= target_ge)
        .count() as u64
}

#[derive(PartialEq, Eq)]
enum GruntStatus {
    Alive,
    Stunned,
    Dead,
}
enum HitType {
    DirectHit,
    ScatterHit,
    Miss,
}
struct GruntCheckResult {
    damage_dealt: u64,
    grunt_status: GruntStatus,
    hit_type: HitType,
}
impl std::fmt::Display for GruntCheckResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        todo!()
        // stats i want eventually, maybe from a compiled MultipleGruntCheckResults
        // or output from the exact "exhaustive enumeration over PMF rolls"

        // chance to directly hit:
        // chance to kill on direct hit:
        // expected damage on direct hit:

        // chance to hit with scatter:
        // chance to kill with scatter:
        // expected scatter damage on direct miss:

        // chance to miss:

        // overall chance to kill (including misses):
        // overall expected damage (ignoring misses):
    }
}

/// Simulate a single attack on a grunt, with the objective of one-shotting it.
fn grunt_check_simulation(
    rng: &mut impl rand::Rng,
    attacker: &Attacker,
    weapon: &Weapon,
    grunt: &Grunt,
) -> GruntCheckResult {
    // for guns
    let player_hits = roll_hits_ge(rng, attacker.dice_pool, 6, 5);
    let player_hits = player_hits.min(weapon.accuracy); // capped by accuracy
    let defense_hits = grunt.defense_test(rng, weapon.defense_penalty);

    if defense_hits >= player_hits {
        // miss
        return GruntCheckResult {
            damage_dealt: 0,
            grunt_status: GruntStatus::Alive,
            hit_type: HitType::Miss,
        };
    }

    let net_hits = player_hits - defense_hits;

    let modified_damage_value = weapon.damage_value + net_hits;
    let resistance_hits = grunt.damage_resistance_test(rng, weapon.armor_penetration);
    let final_damage = modified_damage_value.saturating_sub(resistance_hits);

    let grunt_status = match grunt.health().cmp(&final_damage) {
        std::cmp::Ordering::Less | std::cmp::Ordering::Equal => GruntStatus::Dead,
        std::cmp::Ordering::Greater => GruntStatus::Alive,
    };

    GruntCheckResult {
        damage_dealt: final_damage,
        grunt_status,
        hit_type: HitType::DirectHit,
    }
}
