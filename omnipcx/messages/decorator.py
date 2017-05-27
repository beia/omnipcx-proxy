def MessageParameters(_type, size, _has_crc=True):
    """ Decorator for simplifying the definition of protocol messages
    """
    def get_type(cls):
        return _type

    def get_size(cls):
        return size

    def has_crc(cls):
        return _has_crc

    def _wrapper(cls):
        cls.get_type = classmethod(get_type)
        cls.has_crc = classmethod(has_crc)
        cls.get_size = classmethod(get_size)
        return cls
    return _wrapper
