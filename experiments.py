import builtins
import json
from typing import Optional, Literal, Final

print("s"*5)
a1 = {}
b1 = a1.keys()
a2 = {}
b2 = a2.keys()

# print(json.dump({1: "1", 2: "2"}))
a1[1] = "1"
a2[2] = "2"
c = a1 | a2
print(c)
a1[3] = "3"
a2[4] = "4"
print(c)

l = list()
l.insert(0, "sd")
l.insert(1, "as")
print(l)
l.pop(0)
print(l)

print(" \n\t".isspace())
print(all([]))
print(a1)
print(set(a1))

print("123".isdigit())
print("-123".isdigit())
print("0".isdigit())


class A:
    def __init__(self, a, b):
        self.b = b
        self.a = a

Optional
Final

def my_func(x: Literal["s", "gh"]):
    pass

my_func("gh4")

x: Final = 0
x = 5

print(str.__name__)


def my_func(type):
    print(type)
    print(builtins.type("dfd"))


my_func("sfdfd")

convertion_rule = lambda x: x+1
print(convertion_rule(4))
# print([1, 2, 3][3])

def f(x):
    return x or None
print(f(1))
print(f(""))
print((1,2) == (1,2))
