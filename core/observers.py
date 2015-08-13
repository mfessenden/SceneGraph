#!/usr/bin/env python
import weakref
import functools


INSTANCE_OBSERVER_ATTR = "_observed__observers"


class ObserverFunction(object):
    """
    I wrap a function which is registered as an observer.
    
    I use a weak reference to the observing function so that being an observer
    does not prevent garbage collection of the observing function.
    """

    def __init__(self, func, identify_observed, weakref_info):
        # For some reason, if we put the update_wrapper after we make the
        # weak reference to func, the call to weakref.ref returns a function
        # instead of a weak ref. So, don't move the next line chomp, chomp...
        functools.update_wrapper(self, func)
        self.identify_observed = identify_observed
        key, d = weakref_info
        self.func_wr = weakref.ref(func, CleanupHandler(key, d))
    
    def __call__(self, observed_obj, *arg, **kw):
        """Call the function I wrap.

        Args:
            *arg: The arguments passed to me by the observed object.
            **kw: The keyword args passed to me by the observed object.
            observed_obj: The observed object which called me.

        Returns:
            Whatever the function I wrap returns.
        """

        if self.identify_observed:
            return self.func_wr()(observed_obj, *arg, **kw)
        else:
            return self.func_wr()(*arg, **kw)


class ObserverBoundMethod(object):
    """I wrap a bound method which is registered as an observer.

    I use a weak reference to the observing bound method's instance so that
    being an observer does not prevent garbage collection of that instance.
    """

    def __init__(self, inst, method_name, identify_observed, weakref_info):
        """Initialize an ObserverBoundMethod.

        Args:
            inst: the object to which the bound method I wrap is bound.
            method_name: the name of the method I wrap.
            identify_observed: boolean indicating whether or not I will pass
                the observed object as the first argument to the function I
                wrap. True means pass the observed object, False means do not
                pass the observed objec.
            weakref_info: Tuple of (key, dict) where dict is the dictionary
                which is keeping track of my role as an observer and key is
                the key in that dict which maps to me. When the function I wrap
                is finalized, I use this information to delete myself from the
                dictionary.
        """

        self.identify_observed = identify_observed
        key, d = weakref_info
        self.inst = weakref.ref(inst, CleanupHandler(key, d))
        self.method_name = method_name
    
    def __call__(self, observed_obj, *arg, **kw):
        """Call the function I wrap.

        Args:
            *arg: The arguments passed to me by the observed object.
            **kw: The keyword args passed to me by the observed object.
            observed_obj: The observed object which called me.

        Returns:
            Whatever the function I wrap returns.
        """

        bound_method = getattr(self.inst(), self.method_name)
        if self.identify_observed:
            return bound_method(observed_obj, *arg, **kw)
        else:
            return bound_method(*arg, **kw)


class ObservableFunction(object):
    """A function which can be observed.

    I wrap a function and allow other callables to register as observers of it.
    If you have a function func, then ObservableFunction(func) is a wrapper
    around func which can accept observers.

    Add and remove observers using:

    add_observer(observer)
        registers observer to be called whenever I am called

    discard_observer(observer)
        Removes an observer from the set of observers.

    Attributes:
        func: The function I wrap.
        observers: Dict mapping keys unique to each observer to that observer.
            If this sounds like a job better served by a set, you're probably
            right and making that change is planned. It's delicate because it
            requires making sure the observer objects are hashable and have a
            proper notion of equality.
    """

    def __init__(self, func):
        """Initialize an ObservableFunction.

        Args:
            func: The function I wrap.
        """

        functools.update_wrapper(self, func)
        self.func = func
        self.observers = {}  # observer key -> observer

    def add_observer(self, observer, identify_observed=False):
        """Register an observer to observe me.

        Args:
            observer: The callable to register as an observer.
            identify_observed: If True, then the observer will get myself
                passed as an additional first argument whenever it is invoked.
                See ObserverFunction and ObserverBoundMethod to see how this
                works.

        Returns:
            True if the observer was added, False otherwise.

        The observing function or method will be called whenever I am called,
        and with the same arguments and keyword arguments.

        If a bound method or function has already been registered as an
        observer, trying to add it again does nothing. In other words, there is
        no way to sign up an observer to be called back multiple times. This
        was a conscious design choice which users are invited to complain about
        if there is a compelling use case where this is inconvenient.
        """

        # If the observer is a bound method,
        if hasattr(observer, "__self__"):
            result = self._add_bound_method(observer, identify_observed)
        # Otherwise, assume observer is a normal function.
        else:
            result = self._add_function(observer, identify_observed)
        return result

    def _add_function(self, func, identify_observed):
        """Add a function as an observer.

        Args:
            func: The function to register as an observer.
            identify_observed: See docstring for add_observer.

        Returns:
            True if the function is added, otherwise False.
        """

        key = self.make_key(func)
        if key not in self.observers:
            self.observers[key] = ObserverFunction(
                func, identify_observed, (key, self.observers))
            return True
        else:
            return False

    def _add_bound_method(self, bound_method, identify_observed):
        """Add an bound method as an observer.

        Args:
            bound_method: The bound method to add as an observer.
            identify_observed: See the docstring for add_observer.

        Returns:
            True if the bound method is added, otherwise False.
        """

        inst = bound_method.__self__
        method_name = bound_method.__name__
        key = self.make_key(bound_method)
        if key not in self.observers:
            self.observers[key] = ObserverBoundMethod(
                inst, method_name, identify_observed, (key, self.observers))
            return True
        else:
            return False

    def discard_observer(self, observer):
        """Un-register an observer.

        Args:
            observer: The observer to un-register.

        Returns true if an observer was removed, otherwise False.
        """
        discarded = False
        key = self.make_key(observer)
        if key in self.observers:
            del self.observers[key]
            discarded = True
        return discarded

    @staticmethod
    def make_key(observer):
        """Construct a unique, hashable, immutable key for an observer."""

        if hasattr(observer, "__self__"):
            inst = observer.__self__
            method_name = observer.__name__
            key = (id(inst), method_name)
        else:
            key = id(observer)
        return key

    def __call__(self, *arg, **kw):
        """Invoke the callable which I proxy, and all of my observers.

        The observers are called with the same *args and **kw as the main
        callable.

        Args:
            *arg: The arguments you want to pass to the callable which I wrap.
            **kw: The keyword args you want to pass to the callable I wrap.

        Returns:
            Whatever the wrapped callable returns.

        Note:
        I think it is possible for observers to disappear while we execute
        them. It might be better to make strong references to all
        observers before we start callback execution, since we don't keep
        strong references elsewhere.
        """
        result = self.func(*arg, **kw)
        for key in self.observers:
            self.observers[key](self, *arg, **kw)
        return result


class ObservableBoundMethod(ObservableFunction):
    """I wrap a bound method and allow observers to be registered."""

    def __init__(self, func, inst, observers):
        """Initialize an ObservableBoundMethod.

        Args:
            func: The function (i.e. unbound method) I wrap.
            inst: The instance to which I am bound.
            observers: Dict mapping keys unique to each observer to that
                observer. This dict comes from the descriptor which generates
                this ObservableBoundMethod instance. In this way, multiple
                instances of ObservableBoundMethod with the same underlying
                object instance and method all add, remove, and call observers
                from the same collection.
                If you think this dict should probably be a set instead then
                you probably grok this module.
        """

        self.func = func
        functools.update_wrapper(self, func)
        self.inst = inst
        self.observers = observers

    def __call__(self, *arg, **kw):
        """Invoke the bound method I wrap, and all of my observers.

        The observers are called with the same *args and **kw as the bound
        method I wrap.

        Args:
            *arg: The arguments you want to pass to the callable which I wrap.
            **kw: The keyword args you want to pass to the callable I wrap.

        Returns:
            Whatever the wrapped bound method returns.

        Note:
        I think it is possible for observers to disappear while we execute
        them. It might be better to make strong references to all
        observers before we start callback execution, since we don't keep
        strong references elsewhere.
        """

        result = self.func(self.inst, *arg, **kw)
        for key in self.observers:
            self.observers[key](self, *arg, **kw)
        return result

    def __eq__(self, other):
        """Check equality of this bound method with another."""

        return all((
            self.inst == other.inst,
            self.func == other.func))

    @property
    def __self__(self):
        """The instance to which I'm bound."""

        return self.inst


# The following two classes are descriptors which manage access to observable
# methods. Suppose you have a class Foo with method bar. Now suppose you have
# an instance my_foo of Foo. When python sees my_foo.bar it creates a bound
# method and gives it to you. You can't register observers on normal bound
# methods. Therefore, we use descriptors to intercept the .bar access. The
# descriptor creates a wrapper around the usual bound method, a wrapper which
# can accept observers. This wrapper is ObservableBoundMethod.
# Now, how do we keep track of registered observers? We can't just store them
# as attributes of the ObservableBoundMethod because the ObservableBoundMethod
# doesn't necessarily live very long. If we do
# my_foo.bar.add_observer(some_observer)
# and then later call my_foo.bar(...), the ObservableBoundMethod active in
# those two cases are not the same object. Therefore, we must persist the
# observers somewhere else. An obvious option is to store the observers as an
# attribute of my_foo. This strategy is implemented in
# ObservableMethodManager_PersistOnInstances. The other strategy is to persist
# the observers within the descriptor itself. In this strategy, the descriptor
# holds a dict mapping instance id's to sets of observers. This strategy is
# implemented in ObservableMethodManager_PersistOnDescriptor.


class ObservableMethodManager_PersistOnInstances(object):
    """I manage access to observable methods.

    When accessed through an instance I return an ObservableBoundMethod.
    When accessed through a class I return an ObservableUnboundMethod.

    When an instance accesses me, I create an ObservableBoundMethod for that
    instance and return it.
    """

    def __init__(self, func):
        """Initialize an ObservableMethodManager_PersistOnInstances.

        Args:
            func: the function (i.e.unbound method) I manage.
        """

        self._func = func
        self._unbound_method = ObservableUnboundMethod(self)

    def __get__(self, inst, cls):
        """Return an ObservableBoundMethod or ObservableUnboundMethod.

        If accessed by instance, I return an ObservableBoundMethod which
        handles that instance. If accessed by class I return an
        ObservableUnboundMethod.

        Args:
            inst: The instance through which I was accessed. This will be None
                if I was accessed through the class, i.e. as an unbound method.
            cls: The class through which I was accessed.
        """

        if inst is None:
            return self._unbound_method
        else:
            if not hasattr(inst, INSTANCE_OBSERVER_ATTR):
                d = {}
                setattr(inst, INSTANCE_OBSERVER_ATTR, d)
            else:
                d = getattr(inst, INSTANCE_OBSERVER_ATTR)
            observers = d.setdefault(self._func.__name__, {})
        return ObservableBoundMethod(self._func, inst, observers)

    def __set__(self, inst, val):
        """Disallow setting because we don't guarantee behavior."""

        raise RuntimeError("Assignment not supported")


class ObservableMethodManager_PersistOnDescriptor(object):
    """I manage access to observable methods.

    When accessed through an instance I return an ObservableBoundMethod.
    When accessed through a class I return an ObservableUnboundMethod.

    Instead of storing observers as attributes on the instances whose bound
    method is being observed, I store them here.

    I store no strong references to the instances I manage. This guarantees
    that I don't prevent garbage collection of those instances.

    When an instance accesses me, I create an ObservableBoundMethod for that
    instance and return it. Observers added to that ObservableBoundMethod, are
    persisted by me, not as attributes of the instances.
    """
    # We persist the observers here because if we try to persist them inside
    # the ObservableBoundMethods then we have to persist the
    # ObservableBoundMethods. That would be bad, because then the reference to
    # the inst inside the ObservableBoundMethod would be persisted and would
    # prevent garbage collection of the inst. We can't use a weak ref to fix
    # this because the ObservableBoundMethod _should_ prevent garbage
    # collection of the inst as long as the ObservableBoundMethod is alive. If
    # this doesn't make sense draw a picture of what references what and it
    # will become clear.
    # The other option is to persist the observers as attributes of the
    # instances themselves. This may be a better option than what we're doing
    # here, because it simplifies the code and makes pickling easier.
    def __init__(self, func):
        """
        Initialize me.
        
        func is the function I will give to the ObservableBoundMethods I
        create.
        """
        self._func = func
        self._unbound_method = ObservableUnboundMethod(self)
        # instance id -> (inst weak ref, observers)
        self.instances = {}

    def __get__(self, inst, cls):
        """
        If accessed by instance I return an ObservableBoundMethod which handles
        that instance.
        
        If accessed by class I return an ObservableUnboundMethod.
        """
        if inst is None:
            return self._unbound_method
        # Only weak references to instances are stored. This guarantees that
        # the descriptor cannot prevent the instances it manages from being
        # garbage collected.
        # We can't use a WeakKeyDict because not all instances are hashable.
        # Instead we use the instance's id as a key which maps to a tuple of a
        # weak ref to the instance, and the observers for that instance. The
        # weak ref has an expiration callback set up to clear the dict entry
        # when the instance is finalized.
        inst_id = id(inst)
        if inst_id in self.instances:
            wr, observers = self.instances[inst_id]
            if wr() is None:
                msg = "Unreachable: instance id=%d not cleaned up"%(inst_id,)
                raise RuntimeError(msg)
        else:
            wr = weakref.ref(inst, CleanupHandler(inst_id, self.instances))
            observers = {}
            self.instances[inst_id] = (wr, observers)
        return ObservableBoundMethod(self._func, inst, observers)

    def __set__(self, inst, val):
        """Disallow setting because we don't guarantee behavior."""
        raise RuntimeError("Assignment not supported")


class ObservableUnboundMethod(object):
    """
    Wrapper for an unbound version of an observable method.
    """
    def __init__(self, manager):
        """
        Create an ObservableUnboundMethod.
        
        manager is the descriptor in charge of this method. See
        ObservableMethodManager.
        """
        self._manager = manager
        functools.update_wrapper(self, manager._func)

    def __call__(self, obj, *arg, **kw):
        """
        Call the unbound method.
        
        We essentially build a bound method and call that. This ensures that
        the code for managing observers is invoked in the same was as it would
        be for a bound method.
        """
        bound_method = self._manager.__get__(obj, obj.__class__)
        return bound_method(*arg, **kw)


class CleanupHandler(object):
    """
    I manage removal of weak references from their storage points.
    
    Use me as a weakref.ref callback to remove an object's id from a dict
    when that object is garbage collected.
    """
    def __init__(self, key, d):
        """
        Initialize a cleanup handler.
        
        key is the key we will delete.
        d is the dict from which we will delete it.
        """
        self.key = key
        self.d = d

    def __call__(self, wr):
        """
        Remove an entry from the dict.
        
        When a weak ref's object expires, the CleanupHandler is called,
        which invokes this method.
        """
        if self.key in self.d:
            del self.d[self.key]


def observable_function(func):
    """
    I turn a function into something that can be observed by other callables.
    
    Use me as a decorator on a function, like this:
    
    @observable_function
    def my_func(x):
        print("my_func called with arg: %s"%(x,))
    
    Now other functions and methods can sign up to get notified when my_func is
    called:
    
    def callback(x):
        print("callback called with arg: %s"%(x,))
    
    class Foo(object):
        def bar(self, x):
            print("Foo object's .bar called with arg: %s"%(x,))
    
    f = Foo()
    my_func.add_observer(callback)
    my_func.add_observer(f.bar)
    my_func('banana')
    
    >>> my_func called with arg: banana
    >>> callback called with arg: banana
    >>> Foo object's .bar called with arg: banana
    
    Unregister observers like this:
    
    my_func.discard_observer(callback)
    """
    return ObservableFunction(func)


def observable_method(func, strategy='instances'):
    """
    I turn a method into something that can be observed by other callables.
    
    You can use me as a decorator on a method, like this:
    
    class Foo(object):
        __init__(self, name):
            self.name = name
        
        @observable_method
        def bar(self, x):
            print("%s called bar with arg: %s"%(self.name, x))
    
    Now other functions and methods can sign up to get notified when my_func is
    called:
    
    def observer(x):
        print("observer called with arg: %s"%(x,))
    
    a = Foo('a')
    b = Foo('b')
    a.bar.add_observer(observer)
    a.bar.add_observer(b.bar)
    a.bar('banana')
    >>> a called bar with arg: banana
    >>> b called bar with arg: banana
    >>> observer called with arg: banana
    
    Note that bar can be an observer as well as observed.
    
    Unregister observers like this:
    
    a.bar.discard_observer(observer)
    
    Args:
        func: The function (i.e. unbound method) to be made observable.
        strategy: This argument requires some background explanation. When
            observers are registered to a bound method, we need to store those
            observers so that we can call them when the observed method is
            called. There are two ways to do this as explained below. In any
            case, access to the observable method is managed by a descriptor,
            and we select which strategy we use for storing observers by using
            one descriptor or another. The strategy argument selects the
            descriptor used.

            The first strategy is to give each instance of the class containing
            the decorated method an attribute whose value is a collection of
            observers for each of its observable methods. This is the default
            strategy and is implemented in
            ObservableMethodManager_PersistOnInstances.
            The advantages of this strategy are that the code is very simple
            and pickling the observers along with the instance owning the
            observable methods is easier.

            The other strategy is to persist the observers for each instance
            inside the descriptor which manages access to that method. This
            strategy is implemented in
            ObservableMethodManager_PersistOnDescriptor.
            The advantage(?) of this strategy is that the observer framework
            doesn't paste any data onto the instances which have observable
            methods. It's not entirely clear that this is actually useful but
            we include it as an option.

            For the simpler strategy in which we store the observers in the
            instances, just use me as a decorator. If you want the alternate
            strategy in which the observers are stored in the descriptor,
            call me explicitly on the function (unbound method) you want to
            make observable and set strategy='descriptor'.
    """
    if strategy == 'instances':
        return ObservableMethodManager_PersistOnInstances(func)
    elif strategy == 'descriptor':
        return ObservableMethodManager_PersistOnDescriptor(func)
    else:
        raise ValueError("Strategy %s not recognized"%(strategy,))