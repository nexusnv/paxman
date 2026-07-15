"""The Dict DSL: contract parsing and serialization.

Re-exports the two DSL entry points so callers can use
`from paxman._dsl import parse_contract, serialize_contract`.
"""

from paxman._dsl.parser import parse_contract
from paxman._dsl.serializer import serialize_contract

__all__ = ["parse_contract", "serialize_contract"]
