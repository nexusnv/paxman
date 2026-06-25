"""Public SPI re-exports for the Paxman API.

Re-exports the two key extension protocols:

* :class:`ContractAdapter` — implement to add support for a new
  contract format (e.g. Protobuf, Avro).
* :class:`Capability` — implement to add a new atomic extraction
  operation (e.g. OCR, barcode decoding).
"""

from paxman.capabilities.base import Capability
from paxman.contract.adapters.base import ContractAdapter

__all__ = [
    "Capability",
    "ContractAdapter",
]
