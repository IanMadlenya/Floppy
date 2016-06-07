FLOPPYTYPES = {}


class MetaType(type):
    def __new__(cls, name, bases, classdict):
        result = type.__new__(cls, name, bases, classdict)
        # result.__dict__['Input'] = result._addInput
        FLOPPYTYPES[name] = result
        return result


class Type(object, metaclass=MetaType):
    color = (255, 255, 255)


# class FInt(Type):
#     color = (0, 115, 130)
#
#
# class FList(Type):
#     color = (0, 115, 130)

class Atom(Type):
    color = (204, 0, 204)