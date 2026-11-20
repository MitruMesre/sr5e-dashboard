use std::collections::HashSet;

#[derive(Hash, PartialEq, Eq)]
enum Skill {
    Automatics { level: u8 },
    Etiquette { level: u8 },
    Perception { level: u8 },
    Pistols { level: u8 },
    Running { level: u8 },
    UnarmedCombat { level: u8 },
}
struct Character {
    body: u32,
    agility: u32,
    reaction: u32,
    strength: u32,
    will: u32,
    logic: u32,
    intuition: u32,
    charisma: u32,
    essence: u32,
    skills: HashSet<Skill>,
    armor: u32,
}
impl Character {
    pub(crate) fn new(
        body: u32,
        agility: u32,
        reaction: u32,
        strength: u32,
        will: u32,
        logic: u32,
        intuition: u32,
        charisma: u32,
        essence: u32,
        skills: HashSet<Skill>,
        armor: u32,
    ) -> Self {
        Character {
            body,
            agility,
            reaction,
            strength,
            will,
            logic,
            intuition,
            charisma,
            essence,
            skills,
            armor,
        }
    }
    fn grunt() -> Self {
        Character {
            body: 4,
            agility: 4,
            reaction: 4,
            strength: 3,
            will: 3,
            logic: 2,
            intuition: 3,
            charisma: 3,
            essence: 6,
            skills: HashSet::from([
                Skill::Automatics { level: 3 },
                Skill::Etiquette { level: 3 },
                Skill::Perception { level: 2 },
                Skill::Pistols { level: 4 },
                Skill::Running { level: 4 },
                Skill::UnarmedCombat { level: 3 },
            ]),
            armor: 12,
            // todo: reset button (input element, type=reset) for grunt if stats are changeable
        }
    }
    fn dice_pool(&self, weapon_skill: Skill) -> u32 {
        // Agi 7 + longarms 6 + specialization(sniper rifles) 2 + laser sight 1

        // So thats attribute of 7,
        // skill of 6,
        // specialization (always adds +2, only one specialization can be applied to a dicepool at a time)
        // and a weapon attachment that adds 1
        todo!()
    }
}
