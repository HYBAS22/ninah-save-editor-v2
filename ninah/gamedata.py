"""Game data mined from Managed/Assembly-CSharp.dll (.NET metadata, dnfile).

Source of truth for ids/names; labels here are the editor's friendly names.
Regenerate: see NINAH_SAVE_FORMAT_2026-10-05.md (enum mining notes).
"""

ECharacterType = {
    0: "Sanya", 1: "TV", 2: "Courier", 3: "Neighbour", 4: "Esenin",
    5: "Anxiety", 6: "Daughter", 7: "Cold", 8: "Fan", 9: "Prophet",
    10: "SuperFake", 11: "Widow", 12: "Scammer", 13: "Doc", 14: "Gasmask",
    15: "WolfHound", 16: "Hunter", 17: "NotTrue", 18: "Greatmother",
    19: "Sexy", 20: "Phone", 21: "Anger", 22: "Luka", 23: "FormerFema",
    24: "Foreigner", 25: "Alkonost", 26: "Blind", 27: "Marauder", 28: "Nun",
    29: "TaxiDriver", 30: "Firefighter", 31: "Fugitive", 32: "Teacher",
    33: "Edgar", 34: "Raskolnikov", 35: "GraveDigger", 36: "Provocateur",
    37: "Mother", 38: "Wifefema", 39: "Vigilante", 40: "Theorist",
    41: "Buddy", 42: "FortuneTeller", 43: "Dude", 44: "Bestson",
    45: "BigLebowski", 46: "Couple", 47: "Fatman", 48: "Wheelchair",
    49: "CultistOne", 50: "CultistTwo", 51: "CultistThree",
    52: "CultistPriest", 53: "Ballerina", 54: "Intruder",
    55: "MushroomEater", 56: "Miner", 57: "Sirin", 58: "Empty",
    59: "Twins", 60: "Player", 61: "Jacob", 62: "StaticBoy", 63: "Tourist",
    64: "Unstable", 65: "Rocker", 66: "Experienced", 67: "Jacket",
    68: "Tough", 69: "Bald", 70: "Nervous", 71: "Leper", 72: "Fairytaller",
    73: "FunnyGuy", 74: "Alt",
}
CHARACTER_NAME = ECharacterType
CHARACTER_ID = {v: k for k, v in ECharacterType.items()}

EConsumable = ["Bobeer", "Cigarette", "Coffee", "Enerjeka", "Pills",
               "Mushroom", "CatFood", "Povistka", "Kombucha", "Photo",
               "Cockroach"]

CONSUMABLE_LABEL = {
    "Bobeer": ("Beer", "For the drunk phone calls and… courage."),
    "Cigarette": ("Cigarettes", "Calm smoke. Probably."),
    "Coffee": ("Coffee", "Extra energy for the day."),
    "Enerjeka": ("Enerjeka", "Energy drink."),
    "Pills": ("Pills", "Just don't ask."),
    "Mushroom": ("Mushroom", "Suspicious mushroom. Very suspicious."),
    "CatFood": ("Cat food", "The cat must eat too."),
    "Povistka": ("Summons", "The draft notice. Handle with care."),
    "Kombucha": ("Kombucha", "Trendy tea."),
    "Photo": ("Photo", "A photo somebody wants."),
    "Cockroach": ("Cockroach", "Protein. Allegedly."),
}

OBJECT_LABEL = {
    "Carpet": ("Carpet", "Roll up the carpet by the door."),
    "Ground": ("Floorboards", "State of the floor."),
    "WindowBoardsTriggers": ("Window boards", "Boarded windows."),
    "PeepholeEndingTrigger": ("Peephole", "Did you peek?"),
    "HatchEnter": ("Hatch", "The hatch under… somewhere."),
    "Apple": ("Apple", "The mushroom apple."),
    "Clock": ("Clock", "The mushroom clock."),
    "Mushroom": ("Mushroom growth", "It's spreading."),
    "Mushroomlist": ("Mushroom list", "Notes about mushrooms."),
    "CultistsSheets": ("Cultist sheets", "Bedtime stories for cultists."),
    "Husband": ("Husband", "Somebody's husband situation."),
    "BathWater": ("Bath water", "Don't waste water."),
    "TunnelBlocker": ("Tunnel blocker", "Blocked passage."),
    "Beer1": ("Beer bottle 1", "First bottle stash."),
    "Beer2": ("Beer bottle 2", "Second bottle stash."),
    "BlackHole": ("Black hole", "Do not feed."),
    "HoleInteract": ("Hole interaction", "You touched the hole."),
}

TIME_OF_DAY = {0: "Day", 1: "Night"}

EEnding = ["TestEnding", "Basement", "BasementWithThem", "KilledBySuper",
           "Baby", "TheDeath", "Cult", "Killer", "FEMA", "Mushroom",
           "Intro", "Rage", "BasementAlone"]

PHONE_SUBSCRIBER = ["None", "Forrest", "FEMA", "Neighbour", "Psychics",
                    "AURACAM", "Extrasens", "BestSonFamily", "MothersHusband",
                    "AlkonostsHusband", "Daughter", "PhoneRoulette",
                    "AngersWife", "FEMARecruiter", "ForeignEmbassy",
                    "DaughtersFriend"]
