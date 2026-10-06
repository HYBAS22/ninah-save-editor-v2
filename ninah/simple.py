"""Simple-mode spec: player-friendly sections. Served by /api/simple, edited via /api/set.

Widget types: number | toggle | flag | select | text | readonly |
              idlist (character ids) | intlist | strlist |
              checklist (name->0/1) | nummap (name->number) | textmap (name->text)
"""
from . import gamedata as G

DAY = "DayNightController"
CONS = "ConsumablesController"
STATE = "StateObjectController"
CHARS = "CharactersManager"
END = "GameplayEndingManager"
EV = "GameEventsManager"
DLG = "DialogManager"
CLOSE = "CloseUpsController"
ROOMS = "RoomsManager"

CHAR_OPTS = [{"value": i, "label": n} for i, n in sorted(G.ECharacterType.items())]


def _res():
    sec = {"id": "res", "title": "Resources", "hint": "Food, drinks and useful things.", "fields": []}
    for name in G.EConsumable:
        label, hint = G.CONSUMABLE_LABEL[name]
        sec["fields"].append({"key": "Storage." + name, "label": label, "hint": hint,
                              "ctl": CONS, "path": "Storage." + name,
                              "widget": "number", "min": 0, "max": 999})
    sec["fields"] += [
        {"key": "DeficitItemDay", "label": "Deficit item day",
         "hint": "Day when the deficit item changes.", "ctl": CONS,
         "path": "DeficitItemDay", "widget": "number", "min": 0, "max": 30},
        {"key": "PovistkasUsed", "label": "Summons used",
         "hint": "How many draft summons were spent.", "ctl": CONS,
         "path": "PovistkasUsed", "widget": "number", "min": 0, "max": 99},
    ]
    return sec


GAME_SECTIONS = [
    {"id": "day", "title": "Day & energy", "hint": "Where you are in the story.",
     "fields": [
        {"key": "Day", "label": "Current day", "hint": "Travel to any day.",
         "ctl": DAY, "path": "Day", "widget": "number", "min": 1, "max": 30},
        {"key": "TimeOfDay", "label": "Time of day", "hint": "Switch day and night freely.",
         "ctl": DAY, "path": "TimeOfDay", "widget": "select",
         "options": [{"value": 0, "label": "Day"}, {"value": 1, "label": "Night"}]},
        {"key": "ExtraEnergySlots", "label": "Extra energy",
         "hint": "Bonus actions per day.", "ctl": DAY,
         "path": "ExtraEnergySlots", "widget": "number", "min": 0, "max": 10},
        {"key": "LastCourierOrderedDay", "label": "Last courier order (day)",
         "hint": "-1 means never.", "ctl": DAY,
         "path": "LastCourierOrderedDay", "widget": "number", "min": -1, "max": 30},
     ]},
    _res(),
    {"id": "house", "title": "House", "hint": "State of your apartment.",
     "fields": [
        {"key": "ObjectsStates", "label": "Objects", "hint": "",
         "ctl": STATE, "path": "ObjectsStates", "widget": "checklist",
         "labels": G.OBJECT_LABEL},
     ]},
    {"id": "people", "title": "People", "hint": "Who is inside, who was exiled…",
     "fields": [
        {"key": "CharactersInside", "label": "Inside right now",
         "hint": "Add or remove visitors.", "ctl": CHARS,
         "path": "CharactersInside", "widget": "idlist", "options": CHAR_OPTS},
        {"key": "ExiledCharacters", "label": "Exiled",
         "hint": "", "ctl": CHARS, "path": "ExiledCharacters",
         "widget": "idlist", "options": CHAR_OPTS},
        {"key": "KilledCharacters", "label": "Killed",
         "hint": "", "ctl": CHARS, "path": "KilledCharacters",
         "widget": "idlist", "options": CHAR_OPTS},
        {"key": "RefusedCharacters", "label": "Refused at the door",
         "hint": "", "ctl": CHARS, "path": "RefusedCharacters",
         "widget": "idlist", "options": CHAR_OPTS},
        {"key": "CharacterWithPovistka", "label": "Holding a summons",
         "hint": "", "ctl": CHARS, "path": "CharacterWithPovistka",
         "widget": "idlist", "options": CHAR_OPTS},
        {"key": "AreCharactersImposters", "label": "Who is NOT human ⚠ spoiler",
         "hint": "The game's main secret. You were warned.",
         "ctl": CHARS, "path": "AreCharactersImposters",
         "widget": "checklist", "spoiler": True},
        {"key": "FEMARating", "label": "FEMA rating",
         "hint": "Your standing with FEMA, per character.",
         "ctl": CHARS, "path": "FEMARating", "widget": "nummap", "step": 0.1},
     ]},
    {"id": "story", "title": "Story flags", "hint": "Endings, events, dialog variables.",
     "fields": [
        {"key": "ev.ProphetVisitsCount", "label": "Prophet visits",
         "hint": "", "ctl": EV, "path": "ProphetVisitsCount",
         "widget": "number", "min": 0, "max": 99},
        {"key": "ev.PriestVisitCount", "label": "Priest visits",
         "hint": "", "ctl": EV, "path": "PriestVisitCount",
         "widget": "number", "min": 0, "max": 99},
        {"key": "ev.MushromeaterVisitsCount", "label": "Mushroom-eater visits",
         "hint": "", "ctl": EV, "path": "MushromeaterVisitsCount",
         "widget": "number", "min": 0, "max": 99},
        {"key": "end.HatchOpened", "label": "Hatch opened",
         "hint": "", "ctl": END, "path": "HatchOpened", "widget": "toggle"},
        {"key": "end.HasEatenMushroom", "label": "Ate the mushroom",
         "hint": "", "ctl": END, "path": "HasEatenMushroom", "widget": "toggle"},
        {"key": "end.HasBegunCultists", "label": "Cultists storyline begun",
         "hint": "", "ctl": END, "path": "HasBegunCultists", "widget": "toggle"},
        {"key": "end.SavedCultists", "label": "Cultists saved",
         "hint": "", "ctl": END, "path": "SavedCultists", "widget": "toggle"},
        {"key": "yarn.bool", "label": "Conversation flags",
         "hint": "Internal dialog switches ($teethCheck etc.). For experiments.",
         "ctl": DLG, "path": "YarnBoolVariables", "widget": "checklist"},
        {"key": "yarn.float", "label": "Conversation numbers",
         "hint": "", "ctl": DLG, "path": "YarnFloatVariables",
         "widget": "nummap", "step": "any"},
        {"key": "yarn.str", "label": "Conversation texts",
         "hint": "", "ctl": DLG, "path": "YarnStringVariables",
         "widget": "textmap"},
     ]},
    {"id": "phone", "title": "Phone & TV", "hint": "Calls, subscribers, television.",
     "fields": [
        {"key": "HasOpenedRadio", "label": "Radio opened",
         "hint": "", "ctl": CLOSE, "path": "HasOpenedRadio", "widget": "toggle"},
        {"key": "PhoneNumbers", "label": "Known phone numbers",
         "hint": "", "ctl": CLOSE, "path": "PhoneNumbers", "widget": "textmap"},
        {"key": "WatchTVTimesToday", "label": "TV watched today (times)",
         "hint": "", "ctl": ROOMS, "path": "WatchTVTimesToday",
         "widget": "number", "min": 0, "max": 99},
        {"key": "BellyProgress", "label": "Belly progress",
         "hint": "", "ctl": ROOMS, "path": "BellyProgress",
         "widget": "number", "min": 0, "max": 99},
     ]},
]

CONS_OPTS = [{"value": i, "label": n}
             for i, n in [(0, "Bobeer"), (1, "Cigarette"), (2, "Coffee"),
                          (3, "Enerjeka"), (4, "Pills"), (5, "Mushroom"),
                          (6, "CatFood"), (7, "Povistka"), (8, "Kombucha"),
                          (9, "Photo"), (100, "Cockroach")]]

META_SECTIONS = [
    {"id": "meta", "title": "Meta progress", "hint": "Across all playthroughs.",
     "fields": [
        {"key": "EndingsReachedCount", "label": "Endings reached",
         "hint": "How many times each ending was seen.", "ctl": "_meta",
         "path": "EndingsReachedCount", "widget": "nummap", "step": 1},
        {"key": "MetCharacters", "label": "Characters met",
         "hint": "Meet-counts per character.", "ctl": "_meta",
         "path": "MetCharacters", "widget": "nummap", "step": 1},
        {"key": "UnseenWindows", "label": "Unseen windows",
         "hint": "Window-peeking checklist.", "ctl": "_meta",
         "path": "UnseenWindows", "widget": "intlist"},
        {"key": "UsedConsumables", "label": "Consumables ever used",
         "hint": "", "ctl": "_meta", "path": "UsedConsumables",
         "widget": "idlist", "options": CONS_OPTS},
        {"key": "_killedImposters", "label": "Impostors killed (total)",
         "hint": "", "ctl": "_meta", "path": "_killedImposters",
         "widget": "idlist", "options": CHAR_OPTS},
        {"key": "_killedInnocents", "label": "Innocents killed (total)",
         "hint": "", "ctl": "_meta", "path": "_killedInnocents",
         "widget": "idlist", "options": CHAR_OPTS},
        {"key": "HasCompletedLookAllWindows", "label": "Looked through all windows",
         "hint": "", "ctl": "_meta", "path": "HasCompletedLookAllWindows",
         "widget": "toggle"},
        {"key": "WatchedTV", "label": "TV shows watched",
         "hint": "", "ctl": "_meta", "path": "WatchedTV", "widget": "strlist"},
     ]},
]


def sections_for(kind):
    return META_SECTIONS if kind == "meta" else GAME_SECTIONS
