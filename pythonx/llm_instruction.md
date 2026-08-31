## Package Boundaries

Internal implementation modules must not be imported directly from
outside their package.

A package may expose multiple explicit external boundaries:

- `__init__.py`: API for ordinary package users.
- `contract.py` or `contract/`: API required by extension authors.

`contract` is not merely an implementation detail. It explicitly marks
the concepts that extension authors are allowed and expected to depend on.

Therefore, an external module may import from a `contract` package even
when that package is not part of the ordinary user-facing API.

Other internal modules remain implementation details unless explicitly
designated as public.
