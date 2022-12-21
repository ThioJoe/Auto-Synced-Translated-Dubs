from typing import Any

def parse_bool(is_bool: Any):
    if type(is_bool) == str:
        if is_bool.lower() == 'true':
            return True
        elif is_bool.lower() == 'false':
            return False
    elif type(is_bool) == bool:
        return is_bool
    else:
        raise ValueError('Not a valid boolean string')
