"""
Utilities for dealing with function, methods and function signatures.
"""

from future.utils import viewitems
from .py3 import textstring

import inspect
from types import MethodType



### Function arguments introspection ###

class FunctionSignature(object):
    """
    Description of a function signature, including name, argument names, default values, names of varg and kwarg arguments, class and object (for methods) and docstring.
    
    Args:
        arg_names (list): Names of the arguments.
        default (dict): Dictionary ``{name: value}`` of default values.
        varg_name (str): Name of ``*varg`` parameter (``None`` means no such parameter).
        kwarg_name (str): Name of ``**kwarg`` parameter (``None`` means no such parameter). 
        cls: Caller class, for methods.
        obj: Caller object, for methods.
        name (str): Function name.
        doc (str): Function docstring. 
    """
    def __init__(self, arg_names=None, defaults=None, varg_name=None, kwarg_name=None, cls=None, obj=None, name=None, doc=None):
        self.arg_names=arg_names or []
        self.defaults=defaults or {}
        self.varg_name=varg_name
        self.kwarg_name=kwarg_name
        self.cls=cls
        self.obj=obj
        self.name=name
        self.doc=doc
    def get_defaults_list(self):
        """
        Get list of default values for arguments in the order specified in the signature.
        """
        defaults_list=[]
        for arg in self.arg_names[::-1]:
            if arg in self.defaults:
                defaults_list.append(self.defaults[arg])
        return defaults_list[::-1]
    def signature(self, pass_order=None):
        """
        Get string containing a signature (arguments list) of the function (call or definition), including ``*vargs`` and ``**kwargs``.
        
        If `pass_order` is not ``None``, it specifies the order in which the arguments are passed.
        """
        if pass_order is None:
            args_sig=", ".join(self.arg_names)
        else:
            args_sig=", ".join(pass_order)
        varg_sig=("*"+self.varg_name) if self.varg_name else ""
        kwarg_sig=("**"+self.kwarg_name) if self.kwarg_name else ""
        sigs=[args_sig,varg_sig,kwarg_sig]
        sigs=[s for s in sigs if s!=""]
        return ", ".join(sigs)
    def wrap_function(self, func, pass_order=None):
        """
        Wrap a function `func` into a containing function with this signature.
        
        Sets function name, argument names, default values, object and class (for methods) and docstring.
        If `pass_order` is not ``None``, it determines the order in which the arguments are passed to the wrapped function.
        """
        eval_string="lambda {0}: _func_({1})".format(self.signature(),self.signature(pass_order))
        wrapped=eval(eval_string,{'_func_':func})
        wrapped.__defaults__=tuple(self.get_defaults_list())
        if self.doc:
            wrapped.__doc__=self.doc
        else:
            wrapped.__doc__=func.__doc__
        if self.name:
            wrapped.__name__=self.name
        else:
            wrapped.__name__=func.__name__
        if self.cls is not None:
            wrapped=MethodType(wrapped,self.obj,self.cls)
        return wrapped
    
    def mandatory_args_num(self):
        """
        Get minimal number of arguments which have to be passed to the function.
        
        The mandatory arguments are the ones which are not bound to caller object (i.e., not ``self``) and don't have default values.
        """
        mand_args=len(self.arg_names)-len(self.defaults)
        if self.obj is not None:
            return mand_args-1 if mand_args>0 else 0 
        else:
            return mand_args
    def max_args_num(self, include_positional=True, include_keywords=True):
        """
        Get maximal number of arguments which can be passed to the function.
        
        Args:
            include_positional (bool): If ``True`` and function accepts ``*vargs``, return ``None`` (unlimited number of arguments).
            include_keywords (bool): If ``True`` and function accepts ``**kwargs``, return ``None`` (unlimited number of arguments).
        """
        if (include_positional and self.varg_name is not None) or (include_keywords and self.kwarg_name is not None):
            return None
        if self.obj is not None:
            return len(self.arg_names)-1
        else:
            return len(self.arg_names)
    
    @staticmethod
    def from_function(func):
        """
        Get signature of the given function or method.
        """
        try:
            args=inspect.getargspec(func)
        except TypeError:
            func=func.__call__
            args=inspect.getargspec(func)
        defaults=args.defaults and dict(zip(args.args[::-1],args.defaults[::-1]))
        try:
            cls=func.__self__.__class__
            obj=func.__self__
            func=func.__func__
        except AttributeError:
            cls=None
            obj=None
        return FunctionSignature(args.args,defaults,args.varargs,args.keywords,cls,obj,func.__name__,func.__doc__)
    @staticmethod
    def merge(original, addition, add_place="front", merge_duplicates=True, overwrite=None):
        """
        Merge two signatures (used for wrapping functions).
        
        The arguments are combined:
            - if ``add_place=='front'``, the addition arguments are placed in the beginning, followed by original arguments not already listed;
            - if ``add_place=='back'``,  the original arguments are placed in the beginning, followed by addition arguments not already listed.
            
        The default values are joined, with the original values superseding the addition values.
        
        `overwrite` is a set or a list specifying which original parameters are overwritten by the addition.
        It includes ``'name'``, ``'doc'``, ``'cls'``, ``'obj'``, ``'varg_name'`` and ``'kwarg_name'``;
        the default value is {'varg_name','kwarg_name','doc'}
        
        Returns:
            tuple: ``(signature, pass_order)``
            
            `pass_order` is the order in which the arguments of the combined signature may be passed to the original signature;
            it may be different from the signature order is ``add_place=='front'``.
            If ``merge_duplicates==True``, duplicate entries in `pass_order` are omitted; otherwise, they're repeated.
        """
        overwrite=overwrite or {"kwarg_name","varg_name"}
        if add_place=="back":
            arg_names=original.arg_names+[a for a in addition.arg_names if not a in original.arg_names]
        elif add_place=="front":
            arg_names=addition.arg_names+[a for a in original.arg_names if not a in addition.arg_names]
        else:
            raise ValueError("unrecognized add_place: {0}".format(add_place))
        if merge_duplicates:
            pass_order=original.arg_names+[a for a in addition.arg_names if not a in original.arg_names]
        else:
            pass_order=original.arg_names+addition.arg_names
        defaults=addition.defaults.copy()
        defaults.update(original.defaults)
        varg_name =addition.varg_name  if "varg_name"  in overwrite else original.varg_name
        kwarg_name=addition.kwarg_name if "kwarg_name" in overwrite else original.kwarg_name
        name=addition.name if "name" in overwrite else original.name
        doc=addition.doc if ("doc" in overwrite or original.doc is None) else original.doc
        ow_cls="cls" in overwrite or ("obj" in overwrite and addition.obj is not None)
        cls=addition.cls if (ow_cls or original.cls is None) else original.cls
        obj=addition.obj if ("obj" in overwrite or original.obj is None) else original.obj
        return FunctionSignature(arg_names,defaults,varg_name,kwarg_name,cls,obj,name,doc),pass_order
    
def getargsfrom(source, **merge_params):
    """
    Decorator factory.
    
    Returns decorator that conforms function signature to the source function.
    ``**merge_params`` are passed to the :func:`FunctionSignature.merge` method merging wrapped and source signature.
    
    The default behavior (conforming parameter names, default values args and kwargs names) is useful for wrapping universal functions like ``g(*args, **kwargs)``.
    
    Example::
    
        def f(x, y=2):
            return x+y
            
        @getargsfrom(f)
        def g(*args): # Now g has the same signature as f, including parameter names and default values.
            return prod(args)
    """
    add_sig=FunctionSignature.from_function(source)
    def wrapper(dest):
        orig_sig=FunctionSignature.from_function(dest)
        full_sig,pass_order=FunctionSignature.merge(orig_sig,add_sig,**merge_params)
        return full_sig.wrap_function(dest,pass_order=pass_order)
    return wrapper

def call_cut_args(func, *args, **kwargs):
    """
    Call `func` with the given arguments, omitting the ones that don't fit its signature.
    """
    sig=FunctionSignature.from_function(func)
    if sig.kwarg_name is not None:
        cut_kwargs=kwargs
    else:
        cut_kwargs={}
        for n,v in viewitems(kwargs):
            if n in sig.arg_names:
                cut_kwargs[n]=v
    max_args_num=sig.max_args_num()
    if max_args_num is None:
        return func(*args,**cut_kwargs)
    else:
        return func(*args[:max_args_num],**cut_kwargs)
        



### Functions for accessing object attributes ###

def getattr_call(obj, attr_name, *args, **vargs):
    """
    Call the getter for the attribute `attr_name` of `obj`.

    If the attribute is a property, pass ``*args`` and ``**kwargs`` to the getter (`fget`); otherwise, ignore them.
    """
    try:
        return getattr(type(obj),attr_name).fget(obj,*args,**vargs)
    except AttributeError:
        return getattr(obj,attr_name)
def setattr_call(obj, attr_name, *args, **vargs):
    """
    Call the setter for the attribute `attr_name` of `obj`.

    If the attribute is a propert, pass ``*args`` and ``**kwargs`` to the setter (`fset`);
    otherwise, the set value is assumed to be either the first argument, or the keyword argument with the name ``'value'``.
    """
    try:
        return getattr(type(obj),attr_name).fset(obj,*args,**vargs)
    except AttributeError:
        value=args[0] if len(args)>0 else vargs["value"]
        return setattr(obj,attr_name,value)
def delattr_call(obj, attr_name, *args, **vargs):
    """
    Call the deleter for the attribute `attr_name` of `obj`.

    If the attribute is a property, pass ``*args`` and ``**kwargs`` to the deleter (`fdel`); otherwise, ignore them.
    """
    try:
        return getattr(type(obj),attr_name).fdel(obj,*args,**vargs)
    except AttributeError:
        return delattr(obj,attr_name)



### Universal wrappers for object calls (includes methods, attributes and properties) ###

class IObjectCall(object):
    """
    Universal interface for object method call (makes methods, attributes and properties look like methods).
    
    Should be called with an object as a first argument.
    """
    def __init__(self):
        object.__init__(self)
    def __call__(self, obj, *args, **vargs):
        raise NotImplementedError("IEventCallback.__call__")
    
class MethodObjectCall(IObjectCall):
    """
    Object call created from an object method.
    
    Args:
        method: Either a method object or a method name which is used for the call.
    """
    def __init__(self, method):
        IObjectCall.__init__(self)
        self.method=method
        self.named=isinstance(method,textstring)
    def __call__(self, obj, *args, **vargs):
        """
        Call this method for the object `obj` with the given arguments.
        """
        if self.named:
            return getattr(obj,self.method)(*args,**vargs)
        else:
            return self.method(obj,*args,**vargs)
class AttrObjectCall(IObjectCall):
    """
    Object call created from an object attribute (makes attributes and properties look like methods).
    
    Args:
        name (str): Attribute name.
        as_getter (bool): If ``True``, call the getter when invoked; otherwise, call the setter.
    
    If an attribute is a simple attribute, than getter gets no arguments and setter gets one argument
    (either the first argument, or the keyword argument named ``'value'``).
    If it's a property, pass all the parameters to the property call.
    """
    def __init__(self, name, as_getter):
        IObjectCall.__init__(self)
        self.name=name
        self.as_getter=as_getter
    def __call__(self, obj, *args, **vargs):
        """
        Access this attribute of the object `obj`.

        If it is a simple attribute, than the getter gets no arguments and the setter gets one argument
        (either thw first argument, or thw keyword argument named ``'value'``).
        If it's a property, pass all the parameters to the property call (`fget` or `fset`).
        """
        if self.as_getter:
            try:
                return getattr(type(obj),self.name).fget(obj,*args,**vargs)
            except AttributeError:
                return getattr(obj,self.name)
        else:
            try:
                return getattr(type(obj),self.name).fset(obj,*args,**vargs)
            except AttributeError:
                value=args[0] if len(args)>0 else vargs["value"]
                return setattr(obj,self.name,value)



### Universal interfaces for object properties (includes methods, attributes and properties) ###

class IObjectProperty(object):
    """
    Universal interface for an object property (makes methods, attributes and properties look like properties).
    
    Can be used to get, set or remove a property.
    """
    def __init__(self):
        object.__init__(self)
    def __call__(self, obj, *args):
        if len(args)==0:
            return self.get(obj)
        else:
            return self.set(obj,args[0])
    def get(self, obj, params=None):
        raise NotImplementedError("IObjectProperty.get")
    def set(self, obj, value):
        raise NotImplementedError("IObjectProperty.set")
    def rem(self, obj, params=None):
        raise NotImplementedError("IObjectProperty.rem")
    
class MethodObjectProperty(IObjectProperty):
    """
    Object property created from object methods (makes methods look like properties).
    
    Args:
        getter (Callable): Method invoked on ``get()``. If ``None``, raise :exc:`RuntimeError` when called.
        setter (Callable): Method invoked on ``set()``. If ``None``, raise :exc:`RuntimeError` when called.
        remover (Callable): Method invoked on ``rem()``. If ``None``, raise :exc:`RuntimeError` when called.
        expand_tuple (bool): If ``True`` and if the first argument in the method call is a tuple,
            expand it as an argument list for the underlying function call.
    """
    def __init__(self, getter=None, setter=None, remover=None, expand_tuple=True):
        IObjectProperty.__init__(self)
        self.setter=MethodObjectCall(setter) if setter else None
        self.getter=MethodObjectCall(getter) if getter else None
        self.remover=MethodObjectCall(remover) if remover else None
        self.expand_tuple=expand_tuple
    def get(self, obj, params=None):
        if self.getter:
            if params is not None:
                if self.expand_tuple and isinstance(params,tuple):
                    return self.getter(obj,*params)
                return self.getter(obj,params)
            return self.getter(obj)
        raise RuntimeError("getter is not supplied")
    def set(self, obj, value):
        if self.setter:
            if self.expand_tuple and isinstance(value,tuple):
                return self.setter(obj,*value)
            else:
                return self.setter(obj,value)
        raise RuntimeError("setter is not supplied")
    def rem(self, obj, params=None):
        if self.remover:
            if params is not None:
                if self.expand_tuple and isinstance(params,tuple):
                    return self.remover(obj,*params)
                return self.remover(obj,params)
            return self.remover(obj, *params)
        raise RuntimeError("remover is not supplied")
class AttrObjectProperty(IObjectProperty):
    """
    Object property created from object attribute. Works with attributes or properties.
    
    Args:
        name (str): Attribute name.
        use_getter (bool): If ``False``, raise :exc:`RuntimeError` when calling ``get`` method.
        use_setter (bool): If ``False``, raise :exc:`RuntimeError` when calling ``set`` method.
        use_remover (bool): If ``False``, raise :exc:`RuntimeError` when calling ``rem`` method.
        expand_tuple (bool): If ``True`` and if the first argument in the method call is a tuple,
            expand it as an argument list for the underlying function call.
    """
    def __init__(self, name, use_getter=True, use_setter=True, use_remover=True, expand_tuple=True):
        IObjectProperty.__init__(self)
        self.name=name
        self.use_getter=use_getter
        self.use_setter=use_setter
        self.use_remover=use_remover
        self.expand_tuple=expand_tuple
    def get(self, obj, params=None):
        if self.use_getter:
            try:
                if params is None:
                    return getattr(type(obj),self.name).fget(obj)
                elif self.expand_tuple and isinstance(params,tuple):
                    return getattr(type(obj),self.name).fget(obj,*params)
                else:
                    return getattr(type(obj),self.name).fget(obj,params)
            except AttributeError:
                return getattr(obj,self.name)
        raise RuntimeError("getter is not supplied")
    def set(self, obj, value):
        if self.use_setter:
            try:
                if self.expand_tuple and isinstance(value,tuple):
                    return getattr(type(obj),self.name).fset(obj,*value)
                else:
                    return getattr(type(obj),self.name).fset(obj,value)
            except AttributeError:
                if self.expand_tuple and isinstance(value,tuple):
                    return setattr(obj,self.name,value[0])
                return setattr(obj,self.name,value)
        raise RuntimeError("setter is not supplied")
    def rem(self, obj, params=None):
        if self.use_remover:
            try:
                if params is None:
                    return getattr(type(obj),self.name).fdel(obj)
                elif self.expand_tuple and isinstance(params,tuple):
                    return getattr(type(obj),self.name).fdel(obj,*params)
                else:
                    return getattr(type(obj),self.name).fdel(obj,params)
            except AttributeError:
                return delattr(obj,self.name)
        raise RuntimeError("remover is not supplied")

def empty_object_property(value=None):
    """
    Dummy property which does nothing and returns `value` on `get` (``None`` by default).
    """
    return MethodObjectProperty(lambda *_, **__:value, lambda *_, **__:None, lambda *_, **__:None)

def obj_prop(*args, **kwargs):
    """
    Build an object property wrapper.
    
    If no arguments (or a single ``None`` argument) are suppled, return a dummy property.
    If one argument is supplied, return :class:`AttrObjectProperty` for a property with a given name.
    Otherwise, return :class:`MethodObjectProperty` property.
    """
    if len(args)==0:
        return empty_object_property()
    if len(args)==1:
        if args[0] is None: # empty property
            return empty_object_property()
        return AttrObjectProperty(args[0],**kwargs)
    elif len(args)<=3:
        return MethodObjectProperty(*args,**kwargs)
    else:
        raise ValueError("invalid number of arguments")
def as_obj_prop(value):
    """
    Turn value into an object property using :func:`obj_prop` function.
    
    If it's already :class:`IObjectProperty`, return unchanged.
    If `value` is a tuple, expand as an argument list.
    """
    if isinstance(value,IObjectProperty):
        return value
    if isinstance(value,tuple):
        return obj_prop(*value)
    if isinstance(value,textstring):
        return obj_prop(value)
    return value




##### Delayed definition #####

def delaydef(gen):
    """
    Wrapper for a delayed definition of a function inside of a module.
    
    Useful if defining a function is computationally costly.
    The wrapped function should be a generator of the target function rather than the function itself.
    
    On the first call the generator is executed to define the target function, which is then substituted for all subsequent calls.
    """
    @getargsfrom(gen)
    def wrapped(*args, **kwargs):
        func=gen()
        globals()[gen.__name__]=func
        return func(*args,**kwargs)
    return wrapped