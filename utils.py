class ParserError(ValueError):
    pass

class MyUnicode(unicode):
    def __new__(cls, data, quot):
        self = super(MyUnicode, cls).__new__(cls, data)
        self.quoting = quot
        return self
    def __copy__(self):
        return MyUnicode(self, quot)

class MyString(str):
    def __new__(cls, data, quot):
        self = super(MyString, cls).__new__(cls, data)
        self.quoting = quot
        return self
    def __copy__(self):
        return MyString(self, quot)
