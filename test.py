import json
defaultRoutineActions = [
    {
        "actions":{
                "speakText":{
                    "text":"Good Morning",
                    "delay":"0"
                },
                "speakDateAndTime":{
                    "delay":"0"
                },
                "speakTemperature":{
                    "delay":"0"
                }
        },
    },
    {
        "actions":{
                "speakText":{
                    "text":"Good Evening",
                    "delay":"0"
                }
        }
    },
    {
        "actions":{
                "speakText":{
                    "text":"Good Night",
                    "delay":"0"
                }
        }
    },
    {
        "actions":{
                "speakTemperature":{
                    "delay":"0"
                }
        }
    },
    {
        "actions":{
                "speakDateAndTime":{
                    "delay":"0"
                }
        }
    },
    {
        "actions":{
               "turnallon":{
                   "delay":"0"
               }
        }
    },
    {
        "actions":{
               "turnalloff":{
                   "delay":"0"
               }
        }
    }
]


tup0 = ("good morning", "morning")
tup1 = ("good evening", "evening")
tup2 = ("good night", "night")
tup3 = ("temperature", "what's the temperature", "how hot is it?", "weather", "weather conditions")
tup4 = ("date", "time", "whats the date", "todays date", "current time")
tup5 = ("let there be light")
tup6 = ("turn off all lights", "darkness")

defaultRoutines = {}
defaultRoutines[tup0] = defaultRoutineActions[0]
defaultRoutines[tup1] = defaultRoutineActions[1]
defaultRoutines[tup2] = defaultRoutineActions[2]
defaultRoutines[tup3] = defaultRoutineActions[3]
defaultRoutines[tup4] = defaultRoutineActions[4]
defaultRoutines[tup5] = defaultRoutineActions[5]
defaultRoutines[tup6] = defaultRoutineActions[6]



file = open("predefRoutines.json", "w");
json.dump(defaultRoutines, file)
file.close();




