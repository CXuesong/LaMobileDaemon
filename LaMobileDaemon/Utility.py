def byteLength(s : str) :
    l = 0
    for c in s :
        l += 1 if ord(c) <= 255 else 2
    return l

def truncateByBytes(s : str, length : int) :
    if length < 0 : raise ValueError("length")
    ind = 0
    for c in s :
        cl = 1 if ord(c) <= 255 else 2
        length -= cl
        if length < 0 : break
        ind += 1
    return s[:ind]