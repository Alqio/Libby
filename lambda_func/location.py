import json
import util
import location_utils


# Open the JSON file containing all restaurant information
_locations_json = 'locations.json'
with open(_locations_json, 'r') as fp:
    _locations = json.load(fp)

# Regex pattern for use in parser
_re_patt = r'(?P<location{}>.+)'

# Open the JSON file containing all sample utterances
_sample_utts = 'location_sample_utterances.json'
with open(_sample_utts, 'r') as fp:
    _samples = json.load(fp)

# Set all utterances to be regex patterns
for i in range(0, len(_samples)):
    _samples[i] = _samples[i].replace('{place}', _re_patt.format('')).replace('{place_two}', _re_patt.format('_two'))

# This is the threshold for the score is low, i.e. we are "uncertain" of the location (see: __existence_) 
_score_thres = 50


def _existence(name):
    """
    This function checks if the location can be found on disk,
    if not return None.
    :param name: the name of the location
    :return: the data of the name if it exists, otherwise None, along with its
             score
    """

    # Set the name to lowercase for easier matching
    name = name.lower()

    # First there is no match, which also is used as a default answer
    curr = None
    score = 0

    # Now go through all of our locations and find the best match
    for loc in _locations:
        location = _locations[loc]
        # We check with all aliases
        aliases = location['aliases']
        for al in aliases:
            # Here we use our _ratio_ function to look how closely these match
            temp = location_utils.ratio(al, name)
            # If the score is higher, change the candidate
            if temp > score:
                curr = location
                score = temp

    # And finally return the 'best' candidate along with its score
    return curr, score


def address(event):
    """
    This function returns the address of the location the user asks for.
    :param event: the input event from Amazon Lex
    :return: the response depending on the input event
    """

    # First create the default response
    addr = "Sorry, I could not find an address for that location"

    # Extract the name and data
    name, data, score = _process_name(event)

    # Check if there exists any corresponding data
    if not data:  # pragma: no cover
        return None  # we do not cover this as this will not happen with our current configuration of the JSON file

    # And finally check if this location has any address
    find_addr = data.get('address', None)
    if find_addr:
        # We also check whether the score for the location was low 
        # (i.e. uncertain)
        if score < _score_thres:
            return 'I am not certain if you meant {} (or something similar), but the ' \
                    'address of this location is {}'.format(data['aliases'][-1], find_addr)
        else:
            return 'The address of {} is {}'.format(name, find_addr)

    # And in a worst case scenario, we return the fail response
    return addr


def open_hours(event):
    """
    Simple function for returning opening hours of buildings,
    if they have them.
    :param event: the input event from Amazon Lex
    :return: a response depending on if the corresponding hours could be found
    """

    # This is the default answer if no hours could be found
    hours = 'Sorry, I could not find any opening hours for this location'

    # Extract the name and data
    name, data, score = _process_name(event)

    # Check if there actually existed any data in the first place
    if not data:  # pragma: no cover
        return None  # we do not cover this as this will not happen with our current configuration of the JSON file

    # And now check if the data includes any opening hours at all
    find_hours = data.get('opening_hours', None)
    if find_hours:
        # We format the opening hours properly
        find_hours = location_utils.parse_opening_hours(find_hours)

        # We also check whether the score for the location was
        # (i.e. uncertain)
        if score < _score_thres:
            return 'I am not certain if you meant {} (or something similar), but the ' \
                   'opening hours are the following: {}'.format(data['aliases'][-1], find_hours)
        else:
            return 'The opening hours for {} are the following: {}'.format(name, find_hours)

    # And in a worst case scenario, we return the fail response
    return hours


def where_is(event):
    """
    This function is used for finding the relative direction of certain location, like smokki for example.
    The function treats the Alvarin Aukio as a center point of Otaniemi, and checks whether the given place is in the
    north side, west side, etc of Otaniemi
    :param event: input event received from Amazon Lex
    :return: reponse for user (i.e. string)
    """

    slots = find_slots(event)
    if not slots:  # pragma: no cover
        # We keep this as future additions to the locations JSON file might trigger this
        return "Sorry, I could not find that place"

    # These are the coordinates of Alvarin aukio
    lat1, lon1 = 60.185739, 24.828786

    # Takes the latitude and longitude of the place given by user
    lat2, lon2 = slots[0]['lat'], slots[0]['lon']

    if not (lat2 and lon2):
        return "Sorry, I could not find where that is"

    # Takes the name of the place that user is looking for
    location_name = slots[0]['aliases'][-1]
    direction = location_utils.compass_point(lat1, lon1, lat2, lon2)
    distance = location_utils.distance(lat1, lon1, lat2, lon2)
    building = slots[0]['building']

    # In case user asks 'where is reima', the answer is 'reima is in dipoli'
    # this is more meaningful
    if building:
        return "{} is in the {}".format(location_name, building)

    # In case the place is in a distance of less than 100 metres, it's concidered to be "in the middle area"
    if distance <= 100:
        return "{} is in the middle area of Otaniemi".format(location_name)

    return "{} is in the {} area of Otaniemi".format(location_name, direction)


def find_slots(event):
    """
    Goes trough value of every slot in input event, and incase the value of slot is other than null, it then
    checks whether there exists object for such value and if does, it appends the returned json objects into the array
    which is then returned at the end
    :param event: input event from Amazon Lex
    :return: a JSON object(s) inside a list
    """

    slots = event['currentIntent']['slots']
    ret = []
    for slot in slots:
        if slots[slot]:
            slot_obj, score = _existence(slots[slot])
            if slot_obj:
                ret.append(slot_obj)

    if ret:
        return ret

    parsed = location_utils.parse_trans(event['inputTranscript'], _samples)
    existing_object, score = _existence(parsed)
    return [existing_object]


def direction_to(event):
    """
    Uses the information in event and tries to provide the user with info between the two points
    he or she has given to the libby
    :param event: the input event from Amazon Lex
    :return: a reponse to to the user about directions (string)
    """

    def helper(trans):
        """
        Little helper function to check whether user wants to get 'from a to b'
        or 'to a from b'
        :param trans: input transcript from Amazon Lex
        :return: a number being -1 or 1, depending on the ordering
        """
        word_array = reversed(trans.split(" "))
        for word in word_array:
            if word.lower() == "to":
                return 1
            if word.lower() == "from":
                return -1
        return 0

    user_input = event['inputTranscript']
    slot_values = find_slots(event)

    if len(slot_values) <= 1:
        return "Sorry, I could not find directions with these instructions"

    lat1, lon1 = slot_values[0]['lat'], slot_values[0]['lon']
    lat2, lon2 = slot_values[1]['lat'], slot_values[1]['lon']

    first_place, second_place = slot_values[0]['aliases'][-1], slot_values[1]['aliases'][-1]

    if not ((lat1 and lon1) and (lat2 and lon2)):
        return "Sorry I could not route from {} to {}".format(first_place, second_place)

    order = helper(user_input)
    distance = location_utils.distance(lat1, lon1, lat2, lon2)

    if first_place == slot_values[1]['building']:
        return "{} is in {}".format(second_place, first_place)
    if second_place == slot_values[0]['building']:
        return "{} is in {}".format(first_place, second_place)

    if order == -1:
        direction = location_utils.compass_point(lat1, lon1, lat2, lon2)
        return "{} is {} metres {} from {}".format(second_place, distance, direction, first_place)
    else:
        direction = location_utils.compass_point(lat2, lon2, lat1, lon1)
        return "{} is {} metres {} from {}".format(first_place, distance, direction, second_place)


def info(event):
    """
    This function returns general information about the location.
    It extracts the _info_ slot from the JSON file containing all locations,
    if such exists.
    :param event: the input event from Aamzon Lex
    :return: info about the location, if such exists
    """

    # Extract the name and data
    name, data, score = _process_name(event)

    # To be absolutely of no crashing, we have to check if the data exists
    if not data:  # pragma: no cover
        return None  # we do not cover this as this will not happen with our current configuration of the JSON file

    # This is the 'fail' response we give the user
    resp = 'Unfortunately I am not able to find any information about {}' \
           ' but try to ask me something else about it'.format(name)

    if score < _score_thres:
        data_info = data.get('info', None)
        if data_info:
            return 'I am not certain if you meant {} (or something similar), ' \
                    'but this is the info I found: {}'.format(data['aliases'][-1], data_info)

    return data.get('info', resp)


def _return_name(event):
    """
    This function simply returns the name of the location found in the query,
    if it exists.
    If the slot does not exist the function simply returns None.
    :param event: the input event from Amazon Lex
    :return: the slot value if it exists, otherwise None
    """

    # Extract the _slots_ from the input event
    slots = event['currentIntent']['slots']
    val = None

    # This for-loop just checks wether the slot exists
    for slot in slots:
        temp = slots[slot]
        if temp:
            val = temp

    return val


def _checker(trans, place, place_two):
    """
    This function finds the correct function for the answer.
    E.g. if the query of the user contains address the query is routed to the
    'address' function that finds the address.
    :param trans: the inputTranscript from the input data from Amazon Lex
    :return: the function dependent on the inputTranscript
    """

    # Here we replace each name (if they were found) to ensure that we are 
    # strictly checking the transcript for additional information, and not
    # mistakenly with the name (e.g. 'open' in 'open innovation house')
    trans = trans.replace(place, '').replace(place_two, '').lower()

    def helper(strings):
        """
        Helper function for checking if a any from list of strings are
        contained in the inputTranscript.
        :param strings: a list of strings that correspond to a certain function
        :return: a boolean value if any elements exist in the string
        """
        for st in strings:
            if st in trans:
                return True
        return False

    # Create a list with strings that should lead to the address function
    # being used
    address_str = ['address', 'location']

    if helper(address_str):
        return address
    if 'open' in trans:
        return open_hours
    if 'where is' in trans:
        return where_is
    if 'from' in trans and 'to' in trans:
        return direction_to
    return info


def _process_name(event):
    """
    Helper function for some of the functions above.
    It first checks if data can be found from the input slot value of the event,
    if it cannot it will give it to the parser to check if we can manually
    extract the location's name.
    After this it tries to extract the data that we have for the location, by
    help from the __existence_ function defined above.
    :param event: the input event from Amazon Lex
    :return: name, corresponding data, and score of the location
    """

    # First check if we can find the name through the slot value
    name = _return_name(event)
    # If not, check with the parser
    if not name:
        name = location_utils.parse_trans(event['inputTranscript'].lower(), _samples)
    # And then try to extract the data from our local JSON file
    data, score = _existence(name)

    # And return both the name (for future referencing) along with its data
    return name, data, score


def location_handler(event):
    """
    This is the handler function for the Location intent.
    :param event: the input event (data) received from AWS Lex
    :return: an ElicitIntent reponse
    """

    # Extract the inputTranscript from the input event
    trans = event['inputTranscript']

    # Also extract the slot values, in case we have to check for something in them 
    place = event['currentIntent']['slots'].get('place', '')
    place_two = event['currentIntent']['slots'].get('place_two', '')

    # Also, to be sure, we are checking in case they were assigned 'null' in the JSON file
    if not place:
        place = ''
    if not place_two:
        place_two = ''

    # And send it to the checker to find the right function for handling
    func = _checker(trans, place, place_two)

    # Save the response from the function
    ans = func(event)

    # Default answer if all failed
    if not ans:  # pragma: no cover
        # We are not convering this in the tests as this would require unproper JSON files to begin with.
        # Currently we have everything configured as we want, so simulating this would be a little hard.
        ans = "Unfortunately I can't seem to find the location"

    return util.close({}, 'Fulfilled', ans)
