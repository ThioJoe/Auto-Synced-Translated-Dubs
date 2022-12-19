def parseBool(string):
    if type(string) == str:
        if string.lower() == 'true':
            return True
        elif string.lower() == 'false':
            return False
    elif type(string) == bool:
        if string == True:
            return True
        elif string == False:
            return False
    else:
        raise ValueError('Not a valid boolean string')
