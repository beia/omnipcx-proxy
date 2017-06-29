def MessageParameters(_type, size, _has_crc=True):
    """ Decorator for simplifying the definition of protocol messages
    """
    def get_type(cls):
        return bytearray(_type, "ascii")

    def _wrapper(cls):
        cls.get_type = classmethod(get_type)
        return cls
    return _wrapper
