from dataclasses import dataclass, field
from typing import Any

@dataclass
class Input:
    s: str = field(default_factory=input)
    i: int = 0

    def __bool__(self):
        '''
        >>> bool(Input('xy').advance(1))
        True
        >>> bool(Input('xy').advance(2))
        False
        '''
        return self.i < len(self.s)

    def curr(self, n=1):
        '''
        >>> Input('asdf').curr()
        'a'
        >>> Input('asdf').curr(2)
        'as'
        '''
        return self.s[self.i : self.i + n]
    
    def advance(self, n=1):
        '''
        >>> Input('asdf').advance()
        Input(s='asdf', i=1)
        >>> Input('asdf').advance(2)
        Input(s='asdf', i=2)
        '''
        return Input(self.s, self.i + n)
    
    def span(self, other):
        return Span(self.s, self.i, other.i)

@dataclass
class Span:
    s: str
    i: int
    j: int

    def content(self):
        return self.s[self.i : self.j]
    
    def span(self, other):
        if isinstance(other, Span):
            return Span(self.s, min(self.i, other.i), max(self.j, other.j))
        elif isinstance(other, Input):
            return Span(self.s, min(self.i, other.i), max(self.j, other.i))
        else:
            raise TypeError

@dataclass
class Parser:
    f: Any = None

    def __call__(self, s=None):
        if s is None:
            s = Input()
        elif isinstance(s, str):
            s = Input(s)
        return self.f(s)
    
    def __add__(self, other):
        '''
        >>> p = tag('x') + 'y'
        >>> p('z')
        >>> p('x')
        ('x', Input(s='x', i=1))
        >>> p('y') 
        ('y', Input(s='y', i=1))
        '''
        other = parser(other)
        @Parser
        def parse(s):
            return self(s) or other(s)
        return parse
    
    def __radd__(self, other):
        '''
        >>> p = 'x' + tag('y')
        >>> p('z')
        >>> p('x')
        ('x', Input(s='x', i=1))
        >>> p('y') 
        ('y', Input(s='y', i=1))
        '''
        other = parser(other)
        return other + self
    
    def __mul__(self, other):
        '''
        >>> p = tag('x') * 'y'
        >>> p('x')
        >>> p('y') 
        >>> p('xy')
        (('x', 'y'), Input(s='xy', i=2))
        '''
        other = parser(other)
        @Parser
        def parse(s):
            if r := self(s):
                x, s = r
                if r := other(s):
                    y, s = r
                    return (x, y), s
        return parse
    
    def __rmul__(self, other):
        '''
        >>> p = 'x' * tag('y') 
        >>> p('x')
        >>> p('y') 
        >>> p('xy')
        (('x', 'y'), Input(s='xy', i=2))
        '''
        other = parser(other)
        return other * self
    
    def __pow__(self, n):
        '''
        >>> p = tag('x') ** 5 
        >>> p('xxx')
        >>> p('xxxxx')
        (('x', 'x', 'x', 'x', 'x'), Input(s='xxxxx', i=5))
        '''
        if isinstance(n, int):
            if n >= 0:
                return seq(*(self for _ in range(n)))
            else:
                raise ValueError
        else:
            raise TypeError
    
    def __getitem__(self, other):
        '''
        >>> p = tag('x')[',']
        >>> p('x') 
        ((['x'], []), Input(s='x', i=1))
        >>> p('x,x')
        ((['x', 'x'], [',']), Input(s='x,x', i=3))
        >>> p('x,x,')
        ((['x', 'x'], [',', ',']), Input(s='x,x,', i=4))
        '''
        other = parser(other)
        @Parser
        def parse(s):
            xs = []
            ys = []
            while r := self(s):
                x, s = r
                xs.append(x)
                if r := other(s):
                    y, s = r
                    ys.append(y)
                else:
                    break
            return (xs, ys), s
        return parse
    
    def __lshift__(self, other):
        '''
        >>> p = tag('x') << 'y'
        >>> p('xy')
        ('x', Input(s='xy', i=2))
        '''
        return (self * other).left()
    
    def __rlshift__(self, other):
        '''
        >>> p = 'x' << tag('y')
        >>> p('xy')
        ('x', Input(s='xy', i=2))
        '''
        other = parser(other)
        return other << self
    
    def __rshift__(self, other):
        '''
        >>> p = tag('x') >> 'y'
        >>> p('xy')
        ('y', Input(s='xy', i=2))
        '''
        return (self * other).right()
    
    def __rrshift__(self, other):
        '''
        >>> p = 'x' >> tag('y')
        >>> p('xy')
        ('y', Input(s='xy', i=2))
        '''
        other = parser(other)
        return other >> self
    
    def __pos__(self):
        '''
        >>> p = +tag('x') 
        >>> p('x')
        ('x', Input(s='x', i=1))
        >>> p(' x') 
        ('x', Input(s=' x', i=2))
        >>> p('  x') 
        ('x', Input(s='  x', i=3))
        >>> p('x ') 
        ('x', Input(s='x ', i=1))
        '''
        return ws >> self
    
    def __neg__(self):
        '''
        >>> p = -tag('x')
        >>> p(' x')
        >>> p('x')
        ('x', Input(s='x', i=1))
        >>> p('x ')
        ('x', Input(s='x ', i=2))
        >>> p('x  ') 
        ('x', Input(s='x  ', i=3))
        '''
        return self << ws
    
    def optional(self):
        '''
        >>> p = tag('x').optional()
        >>> p('x')
        ('x', Input(s='x', i=1))
        >>> p('')
        (None, Input(s='', i=0))
        >>> p('y') 
        (None, Input(s='y', i=0))
        '''
        @Parser
        def parse(s):
            return self(s) or (None, s)
        return parse
    
    def many0(self):
        '''
        >>> p = tag('x').many0() 
        >>> p('')
        ([], Input(s='', i=0))
        >>> p('xxxx') 
        (['x', 'x', 'x', 'x'], Input(s='xxxx', i=4))
        >>> p('x')    
        (['x'], Input(s='x', i=1))
        '''
        @Parser
        def parse(s):
            xs = []
            while r := self(s):
                x, s = r
                xs.append(x)
            return xs, s
        return parse
    
    def many1(self):
        '''
        >>> p = tag('x').many1()
        >>> p('')
        >>> p('x')
        (['x'], Input(s='x', i=1))
        >>> p('xxx')
        (['x', 'x', 'x'], Input(s='xxx', i=3))
        '''
        return self.many0().pred(len)
    
    def map(self, f):
        '''
        >>> p = (tag('x') * 'y').map(lambda x: x[0])
        >>> p('x')
        >>> p('y')
        >>> p('xy')
        ('x', Input(s='xy', i=2))
        '''
        @Parser
        def parse(s):
            if r := self(s):
                x, s = r
                return f(x), s
        return parse
    
    def map_star(self, f):
        '''
        >>> @dataclass
        ... class Two:
        ...     x: Any
        ...     y: Any
        ... 
        >>> p = (tag('x') * 'y').map_star(Two)
        >>> p('x') 
        >>> p('y')
        >>> p('xy')
        (Two(x='x', y='y'), Input(s='xy', i=2))
        '''
        @Parser
        def parse(s):
            if r := self(s):
                x, s = r
                return f(*x), s
        return parse
    
    def pred(self, p):
        '''
        >>> p = (tag('x') + 'y').pred(lambda x: x != 'y') 
        >>> p('x')
        ('x', Input(s='x', i=1))
        >>> p('y')
        '''
        @Parser
        def parse(s):
            if r := self(s):
                x, s1 = r
                if p(x):
                    return x, s1
        return parse
    
    def index(self, i):
        '''
        >>> p1 = (tag('x') * 'y').index(0)
        >>> p1('x')
        >>> p1('y')
        >>> p1('xy')
        ('x', Input(s='xy', i=2))
        >>> p2 = (tag('x') * 'y').index(1)
        >>> p2('x')
        >>> p2('y')
        >>> p2('xy')
        ('y', Input(s='xy', i=2))
        '''
        return self.map(lambda x: x[i])
    
    def left(self):
        '''
        >>> p = tag('x') * 'y'  
        >>> p1 = p.left()
        >>> p1('xy')
        ('x', Input(s='xy', i=2))
        '''
        return self.index(0)
    
    def right(self):
        '''
        >>> p = tag('x') * 'y'
        >>> p2 = p.right()
        >>> p2('xy')
        ('y', Input(s='xy', i=2))
        '''
        return self.index(1)
    
    def spanned(self):
        '''
        >>> p = (tag('x') * 'y').spanned()
        >>> p('xy')
        ((('x', 'y'), Span(s='xy', i=0, j=2)), Input(s='xy', i=2))
        '''
        @Parser
        def parse(s):
            if r := self(s):
                x, s1 = r
                span = s.span(s1)
                return (x, span), s1
        return parse
    
    def span(self):
        '''
        >>> p = (tag('x') * 'y').span()
        >>> p('xy')
        (Span(s='xy', i=0, j=2), Input(s='xy', i=2))
        '''
        return self.spanned().right()
    
    def stringed(self):
        '''
        >>> p = (tag('x') * 'y').stringed()
        >>> p('xy')
        ((('x', 'y'), 'xy'), Input(s='xy', i=2))
        '''
        @Parser
        def parse(s):
            if r := self(s):
                x, s1 = r
                string = s.span(s1).content()
                return (x, string), s1
        return parse
    
    def string(self):
        '''
        >>> p = (tag('x') * 'y').string()
        >>> p('xy')
        ('xy', Input(s='xy', i=2))
        '''
        return self.stringed().right()
    
    def negate(self):
        '''
        >>> p = tag('x').negate() 
        >>> p('x')
        False
        >>> p('y')
        (None, Input(s='y', i=0))
        '''
        @Parser
        def parse(s):
            return (not self(s)) and (None, s)
        return parse

def parser(other):
    if isinstance(other, Parser):
        return other
    elif callable(other):
        return Parser(other)
    elif isinstance(other, str):
        return tag(other)
    else:
        raise TypeError

def tag(m):
    '''
    >>> tag('...')('')
    >>> tag('...')('...asdf')
    ('...', Input(s='...asdf', i=3))
    '''
    @Parser
    def parse(s):
        if s.curr(len(m)) == m:
            return m, s.advance(len(m))
    return parse

def seq(*ps):
    '''
    >>> seq('x', 'y', 'z')('xyz')
    (('x', 'y', 'z'), Input(s='xyz', i=3))
    '''
    ps = list(map(parser, ps))
    @Parser
    def parse(s):
        xs = []
        for p in ps:
            if (r := p(s)) is not None:
                x, s = r
                xs.append(x)
            else:
                return
        return tuple(xs), s
    return parse

def seqws(*ps):
    '''
    >>> p = seqws('x', 'y', 'z') 
    >>> p('xyz')
    (('x', 'y', 'z'), Input(s='xyz', i=3))
    >>> p('x y z') 
    (('x', 'y', 'z'), Input(s='x y z', i=5))
    >>> p('x y z ') 
    (('x', 'y', 'z'), Input(s='x y z ', i=6))
    >>> p('x  y  z  ') 
    (('x', 'y', 'z'), Input(s='x  y  z  ', i=9))
    '''
    return +seq(*(-parser(p) for p in ps))

def seqspanned(*ps):
    '''
    >>> p = seqspanned('x', 'y', 'z')
    >>> p('xy')
    >>> p('xyz') 
    ((Span(s='xyz', i=0, j=3), 'x', 'y', 'z'), Input(s='xyz', i=3))
    '''
    return seqws(*ps).spanned().map(lambda x: (x[1], *x[0]))

@Parser
def one(s):
    '''
    >>> one('x')
    ('x', Input(s='x', i=1))
    >>> one(Input('x').advance())
    '''
    if s:
        return s.curr(), s.advance()

def pred(p):
    '''
    >>> pred(str.isdigit)('xyz')
    >>> pred(str.isdigit)('1234')
    ('1', Input(s='1234', i=1))
    '''
    return one.pred(p)

alpha = pred(str.isalpha)
alnum = pred(str.isalnum)
digit = pred(str.isdigit)
lower = pred(str.islower)
upper = pred(str.isupper)
space = pred(str.isspace)

ws = space.many0()

def kw(m):
    return +-tag(m).span()
