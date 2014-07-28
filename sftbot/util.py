def try_decode(line, preferredcodec):
    try:
        return line.decode(preferredcodec)
    except:
        pass

    try:
        if preferredcodec != 'utf-8':
            return line.decode('utf-8')
    except:
        pass

    try:
        if preferredcodec != 'latin-1':
            return line.decode('latin-1')
    except:
        pass

    try:
        return line.decode('utf-8', errors='ignore')
    except:
        # how could this even possibly fail?
        pass

    try:
        # last chance, seriously
        return line.decode('ascii', errors='ignore')
    except:
        pass

    # screw you and your retarded line.
    return "[decoding error]"


def try_encode(line, preferredcodec):
    try:
        return line.encode(preferredcodec, errors='ignore')
    except:
        pass

    try:
        return line.encode('utf-8', errors='ignore')
    except:
        pass

    try:
        return line.encode('ascii', errors='ignore')
    except:
        pass

    return "[encoding error]"
