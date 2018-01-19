from . import util
import json

"""
help_answer return the help answer depend which help is asking. If user use
only word "help" the answer is the basic Libby answer other way the answer is
from the "help.json" -file. Where is all the help which are useful.
"""


def help_answer(intent):
    if intent['slots']['what'] is None:
        message = "Hi! I'm Libby help. If you want to get more help, " \
                  "ask weather or roberts coffee help."
        return util.elicit_intent({}, message)
    else:
        data = json.load(open('help.json'))
        name = intent['slots']['what']
        message = data[name]
        return util.elicit_intent({}, message)
