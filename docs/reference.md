# API Reference

This page documents the public surface of the `tierproxy` package. All
symbols listed here are stable and follow semantic versioning; anything
inside `tierproxy._internal` or modules prefixed with `_` is private and may
change between releases.

## Client

```{eval-rst}
.. autoclass:: tierproxy.TierProxy
   :members:
   :inherited-members:
```

```{eval-rst}
.. autoclass:: tierproxy.AsyncTierProxy
   :members:
   :inherited-members:
```

## Resources

```{eval-rst}
.. automodule:: tierproxy.resources.me
   :members:
```

```{eval-rst}
.. automodule:: tierproxy.resources.usage
   :members:
```

```{eval-rst}
.. automodule:: tierproxy.resources.health
   :members:
```

## Proxy URL builder & selector

```{eval-rst}
.. automodule:: tierproxy.proxy.url_builder
   :members:
```

```{eval-rst}
.. automodule:: tierproxy.proxy.selector
   :members:
```

## Retry policy

```{eval-rst}
.. automodule:: tierproxy.retry
   :members:
```

## Exceptions

```{eval-rst}
.. automodule:: tierproxy.errors
   :members:
   :show-inheritance:
```
