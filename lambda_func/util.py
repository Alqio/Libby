# --------------- Helpers that build all of the responses ----------------------


def close(sessionAttributes, fulfillmentState, message):
    return {
        'sessionAttributes': sessionAttributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillmentState,
            'message': message
        }
    }


def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Hi! I'm Libby and I'm here to help you choose what you want to order from Robert's Coffee or" \
                    " to know what kind of weather there is outside. Start by asking about the weather, or about Robert's" \
                    "Coffee."
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "Start by asking about the weather, or about Robert's Coffee."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def unhandled_request():
    card_title = "Unhandled"
    speech_output = "Sorry I don't know that one."
    # Setting this to true ends the session and exits the skill.
    should_end_session = False
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def handle_session_end_request():
    message = {
        'contentType': 'PlainText',
        'content': "Hope you found what you were looking for"
    }
    return close({}, 'Fulfilled', message)


"""
Takes list of strings as a parameter and parses it's elements to sound better in Alexa's speech. For example: 
4.50 -> 4 euros 50 cents  and 4.00 -> 4 euros
"""


def parse_prices(prices):
    res = []
    for s in prices:
        price = list(s)
        if s[2] == '0':
            s = s[0]
            res.append(s + " euros")
        elif is_number(s):
            for i in range(0, len(price)):
                if (price[i] == '.'):
                    price[i] = ' euros '
            res.append("".join(price) + " cents")
        else:
            res.append(s)
    return res


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False