from pycket.error import SchemeException
from rpython.tool.pairtype import extendabletype
from rpython.rlib  import jit

class W_Object(object):
    __metaclass__ = extendabletype
    _attrs_ = []
    errorname = "%%%%unreachable%%%%"
    def __init__(self):
        raise NotImplementedError("abstract base class")
    def tostring(self):
        return str(self)
    def call(self, args, env, cont):
        raise SchemeException("%s is not callable" % self.tostring())

class W_Cell(W_Object): # not the same as Racket's box
    def __init__(self, v):
        assert not isinstance(v, W_Cell)
        self.value = v

class W_List(W_Object):
    errorname = "list"
    def __init__(self):
        raise NotImplementedError("abstract base class")

class W_Cons(W_List):
    errorname = "pair"
    def __init__(self, a, d):
        self.car = a
        self.cdr = d
    def tostring(self):
        return "(%s . %s)"%(self.car.tostring(), self.cdr.tostring())

class W_Number(W_Object):
    errorname = "number"
    def __init__(self):
        raise NotImplementedError("abstract base class")


class W_Fixnum(W_Number):
    _immutable_fields_ = ["value"]
    errorname = "fixnum"
    def tostring(self):
        return str(self.value)
    def __init__(self, val):
        self.value = val

class W_Flonum(W_Number):
    _immutable_fields_ = ["value"]
    def tostring(self):
        return str(self.value)
    def __init__(self, val):
        self.value = val

class W_Bignum(W_Number):
    _immutable_fields_ = ["value"]
    def tostring(self):
        return str(self.value)
    def __init__(self, val):
        self.value = val

class W_Void(W_Object):
    def __init__(self): pass
    def tostring(self):
        return "#<void>"

class W_Null(W_List):
    def __init__(self): pass
    def tostring(self): return "()"

w_void = W_Void()
w_null = W_Null()

class W_Bool(W_Object):
    _immutable_fields_ = ["value"]
    @staticmethod
    def make(b):
        if b: return w_true
        else: return w_false
    def __init__(self, val):
        self.value = val
    def tostring(self):
        if self.value: return "#t"
        else: return "#f"

w_false = W_Bool(False)
w_true = W_Bool(True)

class W_String(W_Object):
    def __init__(self, val):
        self.value = val
    def tostring(self):
        return self.value

class W_Symbol(W_Object):
    _immutable_fields_ = ["value"]
    all_symbols = {}
    @staticmethod
    def make(string):
        # This assert statement makes the lowering phase of rpython break...
        # Maybe comment back in and check for bug.
        #assert isinstance(string, str)
        if string in W_Symbol.all_symbols:
            return W_Symbol.all_symbols[string]
        else:
            W_Symbol.all_symbols[string] = w_result = W_Symbol(string)
            return w_result
    def __repr__(self):
        return self.value
    def __init__(self, val):
        self.value = val
    def tostring(self):
        return "'%s"%self.value

class W_Procedure(W_Object):
    errorname = "procedure"
    def __init__(self):
        raise NotImplementedError("abstract base class")

class W_SimplePrim(W_Procedure):
    _immutable_fields_ = ["name", "code"]
    def __init__ (self, name, code):
        self.name = name
        self.code = code

    def call(self, args, env, cont):
        from pycket.interpreter import return_value
        jit.promote(self)
        #print self.name
        return return_value(self.code(args), env, cont)
    
    def tostring(self):
        return "SimplePrim<%s>" % self.name

class W_Prim(W_Procedure):
    _immutable_fields_ = ["name", "code"]
    def __init__ (self, name, code):
        self.name = name
        self.code = code

    def call(self, args, env, cont):
        jit.promote(self)
        return self.code(args, env, cont)
    
    def tostring(self):
        return "Prim<%s>" % self.name

def to_list(l): return to_improper(l, w_null)

def to_improper(l, v):
    if not l:
        return v
    else:
        return W_Cons(l[0], to_improper(l[1:], v))

class W_Continuation(W_Procedure):
    _immutable_fields_ = ["cont"]
    def __init__ (self, cont):
        self.cont = cont
    def call(self, args, env, cont):
        from pycket.interpreter import return_value
        a, = args # FIXME: multiple values
        return return_value(a, env, self.cont)

class W_Closure(W_Procedure):
    _immutable_fields_ = ["lam", "env"]
    @jit.unroll_safe
    def __init__ (self, lam, env):
        from pycket.interpreter import ConsEnv
        self.lam = lam
        vals = [env.lookup(i, lam.enclosing_env_structure)
                    for i in lam.frees.elems]
        self.env = ConsEnv.make(vals, lam.frees, env.toplevel_env, env.toplevel_env)
    def call(self, args, env, cont):
        from pycket.interpreter import ConsEnv
        lam = jit.promote(self.lam)
        fmls_len = len(lam.formals)
        args_len = len(args)
        if fmls_len != args_len and not lam.rest:
            raise SchemeException("wrong number of arguments to %s, expected %s but got %s"%(self.tostring(), fmls_len,args_len))
        if fmls_len > args_len:
            raise SchemeException("wrong number of arguments to %s, expected at least %s but got %s"%(self.tostring(), fmls_len,args_len))
        if lam.rest:
            actuals = args[0:fmls_len] + [to_list(args[fmls_len:])]
        else:
            actuals = args
        # specialize on the fact that often we end up executing in the same
        # environment
        if isinstance(env, ConsEnv) and env.prev is self.env:
            prev = env.prev
        else:
            prev = self.env
        return lam.make_begin_cont(
                          ConsEnv.make(actuals, lam.args, prev, self.env.toplevel_env),
                          cont)


