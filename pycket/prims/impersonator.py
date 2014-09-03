
from ..      import impersonators as imp
from ..      import values
from ..      import values_struct
from ..error import SchemeException
from .expose import expose, expose_val
from .equal  import equal_func, EqualInfo

# Used to find the first impersonator-property
def find_prop_start_index(args):
    for i, v in enumerate(args):
        if isinstance(v, imp.W_ImpPropertyDescriptor):
            return i
    return len(args)

def unpack_properties(args, name):
    idx = find_prop_start_index(args)
    args, props = args[:idx], args[idx:]
    prop_len = len(props)

    if prop_len % 2 != 0:
        raise SchemeException(name + ": not all properties have corresponding values")

    prop_keys = [props[i] for i in range(0, prop_len, 2)]
    prop_vals = [props[i] for i in range(1, prop_len, 2)]

    for k in prop_keys:
        if not isinstance(k, imp.W_ImpPropertyDescriptor):
            desc = "%s: %s is not a property descriptor" % (name, k.tostring())
            raise SchemeException(desc)

    return args, prop_keys, prop_vals

def unpack_vector_args(args, name):
    args, prop_keys, prop_vals = unpack_properties(args, name)
    if len(args) != 3:
        raise SchemeException(name + ": not given 3 required arguments")
    v, refh, seth = args
    if not isinstance(v, values.W_MVector):
        raise SchemeException(name + ": first arg not a vector")
    if not refh.iscallable() or not seth.iscallable:
        raise SchemeException(name + ": provided handler is not callable")

    return v, refh, seth, prop_keys, prop_vals

def unpack_procedure_args(args, name):
    args, prop_keys, prop_vals = unpack_properties(args, name)
    if len(args) != 2:
        raise SchemeException(name + ": not given 2 required arguments")
    proc, check = args
    if not proc.iscallable():
        raise SchemeException(name + ": first argument is not a procedure")
    if not check.iscallable():
        raise SchemeException(name + ": handler is not a procedure")
    return proc, check, prop_keys, prop_vals

def unpack_box_args(args, name):
    args, prop_keys, prop_vals = unpack_properties(args, name)
    if len(args) != 3:
        raise SchemeException(name + ": not given three required arguments")
    box, unboxh, seth = args
    if not unboxh.iscallable():
        raise SchemeException(name + ": supplied unbox handler is not callable")
    if not seth.iscallable():
        raise SchemeException(name + ": supplied set-box! handler is not callable")
    return box, unboxh, seth, prop_keys, prop_vals

@expose("impersonate-procedure")
def impersonate_procedure(args):
    proc, check, prop_keys, prop_vals = unpack_procedure_args(args, "impersonate-procedure")
    check.mark_non_loop()
    return imp.W_ImpProcedure(proc, check, prop_keys, prop_vals)

@expose("chaperone-procedure")
def chaperone_procedure(args):
    proc, check, prop_keys, prop_vals = unpack_procedure_args(args, "chaperone-procedure")
    check.mark_non_loop()
    return imp.W_ChpProcedure(proc, check, prop_keys, prop_vals)

@expose("impersonate-vector")
def impersonate_vector(args):
    v, refh, seth, prop_keys, prop_vals = unpack_vector_args(args, "impersonate-vector")
    if v.immutable():
        raise SchemeException("impersonate-vector: cannot impersonate immutable vector")
    refh.mark_non_loop()
    seth.mark_non_loop()
    return imp.W_ImpVector(v, refh, seth, prop_keys, prop_vals)

@expose("chaperone-vector")
def chaperone_vector(args):
    v, refh, seth, prop_keys, prop_vals = unpack_vector_args(args, "chaperone-vector")
    refh.mark_non_loop()
    seth.mark_non_loop()
    return imp.W_ChpVector(v, refh, seth, prop_keys, prop_vals)

# Need to check that fields are mutable
@expose("impersonate-struct")
def impersonate_struct(args):
    args, prop_keys, prop_vals = unpack_properties(args, "impersonate-struct")
    if len(args) < 1 or len(args) % 2 != 1:
        raise SchemeException("impersonate-struct: arity mismatch")
    if len(args) == 1:
        return args[0]

    struct, args = args[0], args[1:]

    if not isinstance(struct, values_struct.W_Struct):
        raise SchemeException("impersonate-struct: not given struct")

    struct_type = struct.struct_type()
    assert isinstance(struct_type, values_struct.W_StructType)

    # Consider storing immutables in an easier form in the structs implementation
    immutables = struct_type.immutables

    # Slicing would be nicer
    overrides = [args[i] for i in range(0, len(args), 2)]
    handlers  = [args[i] for i in range(1, len(args), 2)]

    for i in overrides:
        if not imp.valid_struct_proc(i):
            raise SchemeException("impersonate-struct: not given valid field accessor")
        elif (isinstance(i, values_struct.W_StructFieldMutator) and
                i.field.value in immutables):
            raise SchemeException("impersonate-struct: cannot impersonate immutable field")
        elif (isinstance(i, values_struct.W_StructFieldAccessor) and
                i.field.value in immutables):
            raise SchemeException("impersonate-struct: cannot impersonate immutable field")

    for i in handlers:
        if not i.iscallable():
            raise SchemeException("impersonate-struct: supplied hander is not a procedure")

    return imp.W_ImpStruct(struct, overrides, handlers, prop_keys, prop_vals)

@expose("chaperone-struct")
def chaperone_struct(args):
    args, prop_keys, prop_vals = unpack_properties(args, "chaperone-struct")
    if len(args) < 1 or len(args) % 2 != 1:
        raise SchemeException("chaperone-struct: arity mismatch")
    if len(args) == 1:
        return args[0]

    struct, args = args[0], args[1:]

    if not isinstance(struct, values_struct.W_Struct):
        raise SchemeException("chaperone-struct: not given struct")

    # Slicing would be nicer
    overrides = [args[i] for i in range(0, len(args), 2)]
    handlers  = [args[i] for i in range(1, len(args), 2)]

    for i in overrides:
        if not imp.valid_struct_proc(i):
            raise SchemeException("chaperone-struct: not given valid field accessor")

    for i in handlers:
        if not i.iscallable():
            raise SchemeException("chaperone-struct: supplied hander is not a procedure")

    return imp.W_ChpStruct(struct, overrides, handlers, prop_keys, prop_vals)

@expose("chaperone-box")
def chaperone_box(args):
    b, unbox, set, prop_keys, prop_vals = unpack_box_args(args, "chaperone-box")
    unbox.mark_non_loop()
    set.mark_non_loop()
    return imp.W_ChpBox(b, unbox, set, prop_keys, prop_vals)

@expose("impersonate-box")
def impersonate_box(args):
    b, unbox, set, prop_keys, prop_vals = unpack_box_args(args, "impersonate-box")
    if b.immutable():
        raise SchemeException("Cannot impersonate immutable box")
    unbox.mark_non_loop()
    set.mark_non_loop()
    return imp.W_ImpBox(b, unbox, set, prop_keys, prop_vals)

@expose("chaperone-hash")
def chaperone_hash(args):
    # FIXME: not implemented
    return args[0]

@expose("impersonate-hash")
def chaperone_hash(args):
    # FIXME: not implemented
    return args[0]

@expose("chaperone-continuation-mark-key", [values.W_ContinuationMarkKey, values.W_Object])
def ccmk(cmk, f):
    return cmk

@expose("impersonate-continuation-mark-key", [values.W_ContinuationMarkKey, values.W_Object])
def icmk(cmk, f):
    return cmk

# TODO: This is not correct, based on Racket's internal implementation.
# The addition checking for immutablity should be done recursively, rather
# than at just the top level of the data structure.
# See: https://github.com/plt/racket/blob/106cd16d359c7cb594f4def8f427c55992d41a6d/racket/src/racket/src/bool.c
@expose("chaperone-of?", [values.W_Object, values.W_Object], simple=False)
def chaperone_of(a, b, env, cont):
    from ..interpreter import return_value
    config = EqualInfo(for_chaperone=EqualInfo.CHAPERONE)
    return equal_func(a, b, config, env, cont)

@expose("impersonator-of?", [values.W_Object, values.W_Object], simple=False)
def impersonator_of(a, b, env, cont):
    from ..interpreter import return_value
    config = EqualInfo(for_chaperone=EqualInfo.IMPERSONATOR)
    return equal_func(a, b, config, env, cont)

@expose("impersonator?", [values.W_Object])
def impersonator(x):
    return values.W_Bool.make(x.is_impersonator())

@expose("chaperone?", [values.W_Object])
def chaperone(x):
    return values.W_Bool.make(x.is_chaperone())

@expose("make-impersonator-property", [values.W_Symbol], simple=False)
def make_imp_prop(sym, env, cont):
    from ..interpreter import return_multi_vals
    name = sym.value
    prop = imp.W_ImpPropertyDescriptor(name)
    pred = imp.W_ImpPropertyPredicate(name)
    accs = imp.W_ImpPropertyAccessor(name)
    return return_multi_vals(values.Values.make([prop, pred, accs]), env, cont)

expose_val("impersonator-prop:application-mark", imp.w_impersonator_prop_application_mark)