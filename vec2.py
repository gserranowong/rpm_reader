class Vec2:
    __slots__ = ("x", "y")  # saves memory (important on Pico)

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        if not isinstance(other, Vec2):
            return NotImplemented
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        if not isinstance(other, Vec2):
            return NotImplemented
        return Vec2(self.x - other.x, self.y - other.y)
    
     # --- indexing ---
    def __getitem__(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        raise IndexError("Vec2 index out of range")

    def __setitem__(self, index, value):
        if index == 0:
            self.x = value
        elif index == 1:
            self.y = value
        else:
            raise IndexError("Vec2 index out of range")
        
    # --- arithmetic ---
    def __add__(self, other):
        if not isinstance(other, Vec2):
            return NotImplemented
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        if not isinstance(other, Vec2):
            return NotImplemented
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, k):
        if isinstance(k, (int, float)):
            return Vec2(self.x * k, self.y * k)
        return NotImplemented

    def __rmul__(self, k):
        return self.__mul__(k)  # supports: 3 * v
    
    def __truediv__(self, k):
        if isinstance(k, (int, float)):
            if k == 0:
                raise ZeroDivisionError("division by zero")

            x = self.x / k
            y = self.y / k

            # if both results are whole numbers → cast back to int
            if isinstance(self.x, int) and isinstance(self.y, int) and isinstance(k, int):
                if x == int(x) and y == int(y):
                    return Vec2(int(x), int(y))

            return Vec2(x, y)

        return NotImplemented

    def __itruediv__(self, k):
        if isinstance(k, (int, float)):
            if k == 0:
                raise ZeroDivisionError("division by zero")
            self.x /= k
            self.y /= k
            return self
        return NotImplemented

    def __repr__(self):
        return f"Vec2({self.x}, {self.y})"
    
    