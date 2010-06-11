# numkit --- observables
# Copyright (c) 2010 Oliver Beckstein <orbeckst@gmail.com>
# Released under the "Modified BSD Licence" (see COPYING).
"""
:mod:`numkit.observables` --- Observables as quantities with errors
===================================================================

Example showing how to use :class:`QuantityWithError`:
   >>> from numkit.observables import QuantityWithError
   >>> a = QuantityWithError(2.0, 1.0)
   >>> a2 = QuantityWithError(2.0, 1.0)  # 2nd independent measurement of a
   >>> a3 = QuantityWithError(2.0, 1.0)  # 3rd independent measurement of a
   >>> b = QuantityWithError(-1, 0.5)
   >>> a+a
   4 (2)
   >>> a+a2
   4 (1.41421)
   >>> (a+a+a)/3
   2 (1)
   >>> (a+a2+a3)/3
   2 (0.57735)
   >>> a/b
   -2 (1.41421)

Note that each quantity has an identity: it makes a difference to the
error of a combined quantity such as a+a if the inputs are independent
measurements of the same.

.. autoclass:: QuantityWithError
   :members:

.. SeeAlso:: Various packages that describe quantities with units. 
"""

import numpy

class QID(frozenset):
    """Identity of a :class:`QuantityWithError`.

    The anonymous identity is ``None``, anything else is a
    :func:`frozenset`.
    """
    def __new__(cls, iterable=None):
        if iterable is None:
            self = None #super(QID,cls).__new__(cls)
        else:
            self = super(QID,cls).__new__(cls, asiterable(iterable))
        return self
    def union(self, x):        
        return super(QID, self).union(asiterable(x))  # hack...
    def __repr__(self):
        return "QID(%r)" % list(self)

class QuantityWithError(object):
    """Number with error and basic error propagation arithmetic.

    The quantity is assumed to be a mean of an observable
    (:attr:`~QuantityWithError.value`) with an associated (Gaussian) error
    :attr:`~QuantityWithError.error` (which is the sqrt of the variance
    :attr:`~QuantityWithError.variance` of the data).

    The covariance is not taken into account in the `error
    propagation`_ (i.e. all quantities are assumed to be uncorrelated)
    with the exception of the case of binary relations of the quantity
    with itself. For instance, a*a is correctly interpreted as
    a**2). However, this behaviour is not guaranteed to work for any
    complicated expression.

    When combining with pure numbers you have to wrap these numbers if
    they are to the left of a :class:`QuantityWithError`, e.g.
      >>> a = QuantityWithError(2.0, 1.0)
      >>> 1/a
      TypeError
      >>> QuantityWithError(1.0)/a
      0.5 (0.25)

    .. _error propagation: http://mathworld.wolfram.com/ErrorPropagation.html
    """
    # A quantity has a unique id which is conserved through operations with
    # itself. "Sameness" of two quantities is tested on this id with
    # :meth:`QuantityWithError.isSame`.
    #
    # NOTE: identity is currently implemented with python id() so it is only unique
    #       within a single python session; for persistence one has to do something
    #       else, e.g. add the data and hash.

    # TODO: Use full formulae with covariance whenever two quantities are 
    #       used that have a covariance defined; will allow to ditch the
    #       special casing of 'if other is self'.
    # TODO: Use variances throughout instead of errors.
    # TODO: special case operations with scalars: conserve the qid during those
    #       operations.
    # TODO: Add qid-conservation to special case "self"-operations.
    def __init__(self, value, error=None, qid=None, **kwargs):
        # value can be another QuantityWithError instance
        val,err,otherqid = self._astuple(value)  # use data of other instances
        if not error is None:
            pass            # kwargs take precedence over any other error
        elif err != 0:      
            error = err     # get from other instance
        else:
            error = 0       # default for a quantity WITHOUT error
        self.value = val
        self.variance = error**2

        # Identity of a quantity: qid
        # - quantities without error have empty qid
        # - new quantities with error start with a unique id
        # - quantities that came from arithmetic between QWEs accumulate all 
        #   unique qids ("identity is their history")
        # - qid is implemented as a frozenset

        _qid = set()           # identity accumulates in qid, i.e. flattened history
        qid = qid or otherqid  # kwargs qid takes precedence; otherqid is likely None
        if qid is None and error != 0:  # generate qid for quantities WITH error
            qid = id(self)              # unique new id
        _qid.update([q for q in asiterable(qid) if not q is None]) 
        self.qid = QID(_qid)       # freeze so that we can use it as a key
        del _qid

        # TODO: covariance will need to be updated from other
        self.covariance = {self.qid: self.variance} # record covariances with other
        self.confidence = kwargs.pop('confidence', 0.99)   # for comparisons/not used yet

    def error():
        """Error of a quantity as sqrt of the variance."""
        def fget(self):
            return numpy.sqrt(self.variance)
        def fset(self, x):
            self.variance = x*x
        return locals()
    error = property(**error())

    def isSame(self, other):
        """True if *other* is the same observable.

        Also True if *other* was derived from *self* without using any
        other independent quantities with errors.
        """
        try:
            return self.qid == other.qid
        except AttributeError:
            pass
        return False

    def _dist(self, x, y):
        return numpy.sqrt(x*x + y*y)

    @staticmethod
    def asQuantityWithError(other):
        """Return a :class:`QuantityWithError`.

        If the input is already a :class:`QuantityWithError` then it is
        returned itself. This is important because a new quantity x' would be
        considered independent from the original one x and thus lead to
        different error estimates for quantities such as x*x versus x*x'.
        """
        if isinstance(other, QuantityWithError):
            return other
        return QuantityWithError(*QuantityWithError._astuple(other))

    @staticmethod
    def _astuple(other):
        try:
            val = other.value
            err = other.error
            qid = other.qid
        except AttributeError:
            val = other
            err = 0
            qid = QID()  # empty for quantities without error
        return val, err, qid 

    def astuple(self):
        """Return tuple (value,error)."""
        return self.value, self.error

    def __repr__(self):
        return "%g (%g)" % self.astuple()

    # NOTE: all the special casing should really be done with the covariance
    # formulae. Also, check that a+a+a etc produces sensible output...

    def __add__(self, other):
        val,err,qid = self._astuple(other)
        if self.isSame(other):
            return QuantityWithError(self.value + val, numpy.abs(self.error+err), qid=self.qid)
        return QuantityWithError(self.value + val, self._dist(self.error, err), qid=self.qid.union(qid))

    def __sub__(self, other):
        val,err,qid = self._astuple(other)
        if self.isSame(other):
            # error should come out as 0 for a-a
            return QuantityWithError(self.value - val, numpy.abs(self.error-err), qid=self.qid)
        return QuantityWithError(self.value - val, self._dist(self.error, err), qid=self.qid.union(qid))

    def __mul__(self, other):
        val,err,qid = self._astuple(other)
        if self.isSame(other):
            # TODO: error not correct in the general case (?)
            return QuantityWithError(self.value * val, numpy.abs(self.error*err), qid=self.qid)
        error = self._dist(val*self.error, err*self.value)
        return QuantityWithError(self.value * val, error=error, qid=self.qid.union(qid))

    def __div__(self, other):
        val,err,qid = self._astuple(other)
        if self.isSame(other):
            # TODO: error not correct in the general case
            return QuantityWithError(self.value/val, 0, qid=self.qid)
        error = self._dist(self.error/val, err*self.value/val**2)
        return QuantityWithError(self.value/val, error=error, qid=self.qid.union(qid))

    def __neg__(self):
        return QuantityWithError(-self.value, error=self.error, qid=self.qid)

    def __pow__(self, other, z=None):
        if not z is None:
            raise NotImplementedError("only pow(self, y) implemented, not pow(self,y,z)")
        x,dx = self.value, self.error
        y,dy,yqid = self._astuple(other)
        if self.isSame(other):
            # not sure if error correct for a**a**a ...
            f = numpy.power(x, y)
            error = numpy.abs(dx*f*(1+numpy.log(x)))
            qid = self.qid
        else:
            f = numpy.power(x,y)
            error = self._dist(dx*f*y/x, dy*f*numpy.log(x))
            qid = [self.qid, yqid]
        return QuantityWithError(f, error, qid=qid)
        
    def __abs__(self):
        return QuantityWithError(self.value.__abs__(), self.error, qid=self.qid)
    
    def __cmp__(self, other):
        """x.__cmp__(other) <==> cmp(x.value,other.value)"""
        # make comparison error-aware, i.e. "==" for a given confidence interval
        val,err,qid = self._astuple(other)
        result = cmp(self.value, val)
        return result
                                      
    def __coerce__(self, other):
        return self, self.asQuantityWithError(other)

    def copy(self):
        """Create a new quantity with the same value and error."""
        return QuantityWithError(self.value, self.error)

    def deepcopy(self):
        """Create an exact copy with the same identity."""
        return QuantityWithError(self.value, self.error, qid=self.qid, confidence=self.confidence)


def iterable(obj):
    """Returns ``True`` if *obj* can be iterated over and is *not* a  string."""
    if type(obj) is str:
        return False    # avoid iterating over characters of a string

    if hasattr(obj, 'next'):
        return True    # any iterator will do 
    try: 
        len(obj)       # anything else that might work
    except TypeError: 
        return False
    return True

def asiterable(obj):
    """Returns obj so that it can be iterated over; a string is *not* treated as iterable"""
    if not iterable(obj):
        obj = [obj]
    return obj