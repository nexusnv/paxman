"""OpenAPI 3.x adapter — OpenAPI 3.x document ↔ ``CanonicalContract``.

Per `ADR-0007`, the V1 OpenAPI
adapter is **best-effort**: it supports the subset of OpenAPI 3.x
that the ``petstore_3_0.yaml`` fixture exercises, and **rejects**
everything else with a structured ``InvalidContractError``.

Hard caps:

- **No ``oneOf`` / ``anyOf`` / ``allOf``** — composition is V2.
  Reject with ``UNSUPPORTED_OPENAPI_FEATURE``.
- **``$ref`` resolution is best-effort.** ``$ref`` to
  ``#/components/schemas/<name>`` is inlined recursively with
  cycle detection (see ``_inline_refs_impl``). ``$ref`` to
  any other target (paths, external URLs) is rejected with
  ``UNSUPPORTED_OPENAPI_FEATURE``. Chained ``$ref`` chains
  (``A`` → ``B`` → ``A``) are detected and rejected with
  ``INVALID_REF``. This is the V1 simplification: a future
  sprint may add a fuller JSON Reference resolver.
- **No path operation parsing** — V1 only reads
  ``components.schemas``. ``paths`` / ``requestBody`` / ``parameters``
  / ``responses`` are accepted but ignored in V1.
- **No ``allOf``-style request body composition** — V2.

The V1 surface:

- :class:`OpenApiAdapter` — the :class:`ContractAdapter` implementation.
- :func:`adapt` / :func:`export` — the SPI methods.
- Delegates schema parsing to :class:`JsonSchemaAdapter` for
  individual schemas (this does
  **not** violate the import DAG because both adapters live in
  ``contract/adapters/`` as siblings).

Error model
-----------

Every error raised is :class:`paxman.errors.InvalidContractError`
with one of the following ``error_code`` values:

- ``UNSUPPORTED_OPENAPI_FEATURE`` — a V2-only feature was used
  (e.g., ``oneOf``).
- ``INVALID_OPENAPI_DOCUMENT`` — the document is not a valid
  OpenAPI 3.x dict.
- ``INVALID_OPENAPI_VERSION`` — ``openapi`` is missing or not in
  the supported set (``3.0.x``, ``3.1.x``).
- ``INVALID_FIELD`` — a schema is malformed.
- ``INVALID_REF`` — a ``$ref`` points to a non-existent schema.

V1 support matrix
-----------------

| OpenAPI 3.x feature              | V1 support     |
|----------------------------------|----------------|
| ``openapi: 3.0.x``               | yes            |
| ``openapi: 3.1.x``               | best-effort    |
| ``info.title`` (contract id)     | yes            |
| ``components.schemas`` (object)  | yes            |
| ``paths.*`` (operations)         | ignored        |
| ``$ref`` to ``components/schemas`` | best-effort  |
| ``$ref`` to ``paths/*``          | rejected       |
| ``oneOf`` / ``anyOf`` / ``allOf``| rejected       |
| ``requestBody``                  | ignored        |
| ``parameters``                   | ignored        |
| ``responses``                    | ignored        |
| ``discriminator``                | rejected       |
| ``nullable: true`` (3.0)         | mapped         |
| ``type: [string, null]`` (3.1)   | mapped         |
"""

from __future__ import annotations

import typing

import attrs

from paxman.contract.adapters.json_schema import JsonSchemaAdapter
from paxman.contract.canonical import CanonicalContract
from paxman.errors import InvalidContractError

__all__ = ["OpenApiAdapter"]


#: OpenAPI 3.x major.minor versions the V1 adapter accepts.
#: 3.1.0 is in "best-effort" territory (the V1 spec lists it as
#: future-only; we accept it because ``openapi-spec-validator``
#: validates it, and the constructs we map are the same as 3.0).
_SUPPORTED_OPENAPI_VERSIONS: typing.Final[frozenset[str]] = frozenset(
    {
        "3.0.0",
        "3.0.1",
        "3.0.2",
        "3.0.3",
        "3.1.0",
        "3.1.1",
    }
)

#: Subset of supported OpenAPI versions that follow the 3.1 spec.
#: 3.1 documents have native JSON Schema 2020-12 alignment, a
#: ``$defs`` block, a top-level ``webhooks`` map, and 3.1
#: path-item ``parameters`` merge semantics.
_OPENAPI_3_1_VERSIONS: typing.Final[frozenset[str]] = frozenset({"3.1.0", "3.1.1"})

#: Subset of supported OpenAPI versions that follow the 3.0 spec.
#: 3.0 documents use the custom "Schema Object", not native JSON
#: Schema; ``$ref`` lives only in ``#/components/schemas/<name>``.
_OPENAPI_3_0_VERSIONS: typing.Final[frozenset[str]] = frozenset(
    {"3.0.0", "3.0.1", "3.0.2", "3.0.3"}
)

#: The set of OpenAPI 3.1 ``jsonSchemaDialect`` values we accept.
#: Mirrors the JSON Schema adapter's supported drafts but is restricted
#: to the JSON Schema 2020-12 family (the only family 3.1 aligns with).
_SUPPORTED_OPENAPI_DIALECTS: typing.Final[frozenset[str]] = frozenset(
    {
        "https://json-schema.org/draft/2020-12/schema",
    }
)

#: The JSON Schema sub-keyword we use to mark an inline schema as
#: "MONEY" inside an OpenAPI document. Mirrors the JSON Schema
#: adapter's convention.
_PAXMAN_TYPE_KEY: typing.Final[str] = "x-paxman-type"

#: The OpenAPI-specific extension key that flags a property as
#: the discriminator. Per the OpenAPI 3.0 spec, ``discriminator``
#: is only meaningful inside ``oneOf`` / ``anyOf`` / ``allOf``,
#: which V1 rejects — but we still reject the keyword
#: defensively.
_DISCRIMINATOR_KEY: typing.Final[str] = "discriminator"


@attrs.frozen(slots=True)
class OpenApiAdapter:
    """Adapter for OpenAPI 3.x documents.

    Pure and stateless. Same input dict → same
    :class:`CanonicalContract`.

    The adapter reads ``components.schemas`` (one
    :class:`CanonicalContract` per top-level schema) and treats
    the **first** schema as the contract body. (Multi-schema
    documents are V2 territory; the V1 contract model is a
    single canonical contract per ``adapt()`` call.)

    Attributes:
        This class has no fields. All methods are pure functions
        of their arguments.
    """

    @property
    def format_id(self) -> str:
        """The adapter's format identifier."""
        return "openapi:3.x"

    # ----- adapt ---------------------------------------------------------

    def adapt(self, external: typing.Any) -> CanonicalContract:
        """Translate an OpenAPI 3.x dict into a :class:`CanonicalContract`.

        The adapter:

        1. Validates the top-level shape (``openapi`` is present
           and in the supported set; ``components.schemas`` is a
           dict).
        2. Rejects V2-only keywords at the top level (``oneOf``,
           ``anyOf``, ``allOf``, ``discriminator``).
        3. Picks the **first** schema in ``components.schemas``
           as the contract body and delegates per-property
           parsing to :class:`JsonSchemaAdapter`.
        4. Resolves intra-document ``$ref`` pointers best-effort
           (inlining the referenced schema if it is in
           ``components.schemas``).

        Args:
            external: An OpenAPI 3.x document (Python ``dict``).

        Returns:
            A :class:`CanonicalContract` representing the first
            schema in ``components.schemas``. ``paths`` is
            ignored.

        Raises:
            InvalidContractError: If the document is not a valid
                OpenAPI 3.x dict, or uses a V2-only feature, or
                a ``$ref`` cannot be resolved.
        """
        if not isinstance(external, dict):
            raise InvalidContractError(
                f"OpenAPI adapter requires a dict, got {type(external).__name__}",
                error_code="INVALID_OPENAPI_DOCUMENT",
                context={"got_type": type(external).__name__},
            )

        # --- Version check -------------------------------------------------
        version = external.get("openapi")
        if version is None:
            raise InvalidContractError(
                "OpenAPI document is missing the 'openapi' version field",
                error_code="INVALID_OPENAPI_VERSION",
                context={"got_keys": sorted(external.keys())},
            )
        if not isinstance(version, str):
            raise InvalidContractError(
                f"OpenAPI 'openapi' field must be a str, got {type(version).__name__}",
                error_code="INVALID_OPENAPI_VERSION",
                context={"version": repr(version)},
            )
        if version not in _SUPPORTED_OPENAPI_VERSIONS:
            raise InvalidContractError(
                f"OpenAPI version {version!r} is not supported by the V1 adapter "
                f"(supported: {sorted(_SUPPORTED_OPENAPI_VERSIONS)})",
                error_code="INVALID_OPENAPI_VERSION",
                context={"version": version, "supported": sorted(_SUPPORTED_OPENAPI_VERSIONS)},
            )

        # --- Top-level reject list (V2 features) ---------------------------
        for keyword in ("oneOf", "anyOf", "allOf", _DISCRIMINATOR_KEY):
            if keyword in external:
                raise InvalidContractError(
                    f"OpenAPI document uses V2-only keyword {keyword!r}; "
                    "the V1 adapter does not support it",
                    error_code="UNSUPPORTED_OPENAPI_FEATURE",
                    context={"keyword": keyword},
                )

        # --- components.schemas check -------------------------------------
        components = external.get("components", {})
        if not isinstance(components, dict):
            raise InvalidContractError(
                "OpenAPI 'components' must be a dict",
                error_code="INVALID_OPENAPI_DOCUMENT",
                context={"got_type": type(components).__name__},
            )
        schemas = components.get("schemas", {})
        if not isinstance(schemas, dict):
            raise InvalidContractError(
                "OpenAPI 'components.schemas' must be a dict",
                error_code="INVALID_OPENAPI_DOCUMENT",
                context={"got_type": type(schemas).__name__},
            )
        if not schemas:
            raise InvalidContractError(
                "OpenAPI 'components.schemas' is empty; nothing to adapt",
                error_code="INVALID_OPENAPI_DOCUMENT",
                context={},
            )

        # --- Pick the first schema as the contract body -------------------
        # V1 limitation: multi-schema documents are flattened to a
        # single canonical contract. The order is the dict's
        # insertion order (Python guarantees it since 3.7), so
        # the same input always picks the same schema.
        schema_name, schema_def = next(iter(schemas.items()))
        if not isinstance(schema_def, dict):
            raise InvalidContractError(
                f"schema {schema_name!r} in components.schemas is not a dict",
                error_code="INVALID_FIELD",
                context={"schema_name": schema_name},
            )

        # --- Per-schema reject list (V2 features) -------------------------
        for keyword in ("oneOf", "anyOf", "allOf", _DISCRIMINATOR_KEY):
            if keyword in schema_def:
                raise InvalidContractError(
                    f"OpenAPI schema {schema_name!r} uses V2-only keyword "
                    f"{keyword!r}; the V1 adapter does not support it",
                    error_code="UNSUPPORTED_OPENAPI_FEATURE",
                    context={"schema_name": schema_name, "keyword": keyword},
                )

        # --- Read 3.1 inputs (best-effort) ---------------------------------
        is_3_1 = _is_openapi_3_1(version)
        # 3.0 documents do not define ``jsonSchemaDialect`` per spec, so
        # we skip the reader entirely (which would otherwise raise on a
        # non-string value). For 3.1 we read the field and validate it
        # against the supported dialect set.
        dialect = _read_json_schema_dialect(external) if is_3_1 else None
        if dialect is not None and dialect not in _SUPPORTED_OPENAPI_DIALECTS:
            raise InvalidContractError(
                f"OpenAPI 3.1 'jsonSchemaDialect'={dialect!r} is not in the supported set",
                error_code="INVALID_JSON_SCHEMA_DIALECT",
                context={"dialect": dialect},
            )
        # Same for ``$defs``: 3.0 documents cannot use it, so we skip
        # the reader (which would also raise on a non-dict value).
        defs = _read_defs(external) if is_3_1 else {}

        # --- Inline $ref resolution (best-effort) -------------------------
        # V1.1.0 supports both ``#/components/schemas/<name>`` (3.0) and
        # ``#/$defs/<name>`` (3.1). A ref using one prefix in a
        # document declared as the other version is rejected with
        # ``INVALID_REF`` (mismatched) by the walker.
        inlined_schema = self._inline_refs(
            schema_def,
            components_schemas=schemas,
            defs=defs,
            schema_name=schema_name,
            document_version=version,
        )

        # --- Build a JSON Schema-shaped dict for the JSON Schema adapter.
        # The JSON Schema adapter expects a top-level ``object`` with
        # ``properties`` + ``required``. OpenAPI 3.x uses the same
        # shape for ``components.schemas`` entries; we copy the
        # relevant keys.
        contract_id = self._extract_contract_id(external, schema_name)
        json_schema_doc: dict[str, typing.Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": contract_id,
            "type": inlined_schema.get("type", "object"),
            "properties": inlined_schema.get("properties", {}),
        }
        if "required" in inlined_schema:
            json_schema_doc["required"] = inlined_schema["required"]
        # Carry the ``description`` over (matches JSON Schema
        # adapter's behavior).
        if "description" in inlined_schema:
            json_schema_doc["description"] = inlined_schema["description"]
        # Carry MONEY-extension properties.
        if inlined_schema.get(_PAXMAN_TYPE_KEY) == "MONEY":
            json_schema_doc[_PAXMAN_TYPE_KEY] = "MONEY"

        # Translate OpenAPI 3.0 ``nullable: true`` on each property
        # to JSON Schema ``type: [type, "null"]``. The JSON Schema
        # adapter only knows the 3.1 nullable form, so we normalize
        # 3.0 -> 3.1 here before delegating.
        json_schema_doc["properties"] = {
            name: _translate_nullable_3_0_to_3_1(prop)
            for name, prop in json_schema_doc["properties"].items()
        }

        # --- Delegate to the JSON Schema adapter -------------------------
        # The JSON Schema adapter lives in ``contract/adapters/`` as a
        # sibling of the OpenAPI adapter. This is NOT a DAG violation:
        # the ``contract`` subsystem can import from any of its
        # submodules. This is the
        # intended delegation pattern.
        json_adapter = JsonSchemaAdapter()
        return json_adapter.adapt(json_schema_doc, schema_dialect=dialect)

    # ----- export --------------------------------------------------------

    def export(self, canonical: CanonicalContract) -> dict[str, typing.Any]:
        """Translate a :class:`CanonicalContract` back into an OpenAPI 3.0.3 dict.

        The export uses :class:`JsonSchemaAdapter` to produce a
        JSON Schema dict, then wraps it in a minimal OpenAPI
        envelope with ``openapi: 3.0.3`` and a
        ``components.schemas`` entry.

        Args:
            canonical: The :class:`CanonicalContract` to export.

        Returns:
            An OpenAPI 3.0.3 document (Python ``dict``) with one
            schema in ``components.schemas``.
        """
        if not isinstance(canonical, CanonicalContract):
            raise InvalidContractError(
                f"export expects CanonicalContract, got {type(canonical).__name__}",
                error_code="INVALID_FIELD",
                context={"got_type": type(canonical).__name__},
            )
        json_adapter = JsonSchemaAdapter()
        json_doc = json_adapter.export(canonical)
        # The JSON Schema adapter returns a full object with
        # ``$schema``, ``title``, ``type``, ``properties``, and
        # (optionally) ``required``. We strip the JSON-Schema
        # envelope and re-wrap as an OpenAPI schema.
        properties = json_doc.get("properties", {})
        required = json_doc.get("required", [])
        description = json_doc.get("description")

        schema: dict[str, typing.Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        if description is not None:
            schema["description"] = description
        # Carry MONEY extension.
        if json_doc.get(_PAXMAN_TYPE_KEY) == "MONEY":
            schema[_PAXMAN_TYPE_KEY] = "MONEY"

        return {
            "openapi": "3.0.3",
            "info": {
                "title": canonical.id,
                "version": "1.0.0",
            },
            "paths": {},
            "components": {
                "schemas": {
                    canonical.id: schema,
                },
            },
        }

    # =====================================================================
    # Internal helpers
    # =====================================================================

    @staticmethod
    def _extract_contract_id(external: dict[str, typing.Any], schema_name: str) -> str:
        """Extract the contract id from ``info.title`` or fall back to the schema name."""
        info = external.get("info", {})
        if isinstance(info, dict):
            title = info.get("title")
            if isinstance(title, str) and title:
                return title
        return schema_name

    @staticmethod
    def _merge_path_parameters(
        operation_params: typing.Iterable[dict[str, typing.Any]],
        path_item_params: typing.Iterable[dict[str, typing.Any]],
        *,
        version: str,
    ) -> list[dict[str, typing.Any]]:
        """Merge or append path-item-level ``parameters`` to operation-level ones.

        - OpenAPI 3.0.x semantics: ``parameters`` from the path item
          are **appended** to the operation-level list (no dedup).
          This is the V1.0.0 behavior and matches the OAS 3.0 spec.
        - OpenAPI 3.1.x semantics: ``parameters`` are **merged** by
          the ``(name, in)`` tuple, with the operation-level entry
          winning on collision. Path-item entries with new
          ``(name, in)`` pairs are appended.

        This helper is a pure function; V1.1.0 does not call it
        end-to-end (paths are still ignored per non-goal N3). It is
        shipped and unit-tested to lock the semantics for V2.0.
        """
        op_list = list(operation_params)
        path_list = list(path_item_params)
        if _is_openapi_3_1(version):
            # 3.1 merge: operation-level wins on (name, in) collision.
            op_keys: set[tuple[str, str]] = {
                (p["name"], p["in"])
                for p in op_list
                if isinstance(p, dict) and "name" in p and "in" in p
            }
            out = list(op_list)
            for p in path_list:
                if not isinstance(p, dict):
                    out.append(p)
                    continue
                key = (p.get("name"), p.get("in"))
                if key in op_keys:
                    continue  # operation-level wins; skip
                out.append(p)
            return out
        # 3.0 append.
        return op_list + path_list

    @staticmethod
    def _inline_refs(
        schema: dict[str, typing.Any],
        *,
        components_schemas: dict[str, typing.Any],
        defs: dict[str, typing.Any],
        schema_name: str,
        document_version: str,
    ) -> dict[str, typing.Any]:
        """Replace ``$ref`` pointers in *schema* with the referenced subschema.

        Supports the two V1.1.0 prefixes:

        - ``#/components/schemas/<name>`` — the OpenAPI 3.0 location.
        - ``#/$defs/<name>`` — the OpenAPI 3.1 location.

        A ref whose prefix does not match the document's version is
        rejected with ``INVALID_REF`` (and a ``mismatched`` message) so
        that 3.0↔3.1 schema mixing is caught early. External refs
        (``https://…``, ``./other.yaml``), path refs (``#/paths/…``),
        and pointer refs to non-existent targets are rejected with
        ``UNSUPPORTED_OPENAPI_FEATURE`` / ``INVALID_REF``.

        Cycle detection is preserved: a ``$ref`` chain (``A`` → ``B`` →
        ``A``) raises ``INVALID_REF``. The seen-set is keyed on the
        *fully-qualified pointer* (``components/X`` vs ``defs/X``) so
        the two namespaces cannot collide.

        Args:
            schema: The schema to walk.
            components_schemas: The full ``components.schemas`` dict.
            defs: The full ``$defs`` dict (may be empty).
            schema_name: The current schema's name (diagnostic context).
            document_version: The OpenAPI version string (e.g. ``"3.0.3"``
                or ``"3.1.0"``); used to enforce that the ref
                namespace matches the document's declared version.

        Returns:
            A new dict with all resolvable ``$ref`` keys replaced by
            the inlined subschema.

        Raises:
            InvalidContractError: ``UNSUPPORTED_OPENAPI_FEATURE`` or
                ``INVALID_REF`` for unresolvable / mismatched refs.
        """
        result = OpenApiAdapter._inline_refs_impl(
            schema,
            components_schemas=components_schemas,
            defs=defs,
            schema_name=schema_name,
            document_version=document_version,
            _seen=frozenset(),
        )
        if not isinstance(result, dict):
            return dict(schema)
        return result

    @staticmethod
    def _inline_refs_impl(
        schema: typing.Any,
        *,
        components_schemas: dict[str, typing.Any],
        defs: dict[str, typing.Any],
        schema_name: str,
        document_version: str,
        _seen: frozenset[str],
    ) -> typing.Any:
        """Recursive helper for :meth:`_inline_refs`.

        Args:
            document_version: The OpenAPI version string of the
                enclosing document (e.g. ``"3.0.3"`` or ``"3.1.0"``).
                Used to enforce that a ref's namespace matches the
                document's declared version.
        """
        if isinstance(schema, list):
            return [
                OpenApiAdapter._inline_refs_impl(
                    item,
                    components_schemas=components_schemas,
                    defs=defs,
                    schema_name=schema_name,
                    document_version=document_version,
                    _seen=_seen,
                )
                for item in schema
            ]
        if not isinstance(schema, dict):
            return schema
        if "$ref" in schema:
            ref = schema["$ref"]
            if not isinstance(ref, str):
                raise InvalidContractError(
                    f"schema {schema_name!r} has a non-string $ref",
                    error_code="INVALID_REF",
                    context={"ref": repr(ref), "schema_name": schema_name},
                )
            comp_prefix = "#/components/schemas/"
            defs_prefix = "#/$defs/"
            if ref.startswith(comp_prefix):
                target_name = ref[len(comp_prefix) :]
                namespace = "components"
                target_table = components_schemas
            elif ref.startswith(defs_prefix):
                target_name = ref[len(defs_prefix) :]
                namespace = "defs"
                target_table = defs
            else:
                raise InvalidContractError(
                    f"schema {schema_name!r} $ref={ref!r} is not supported by the V1.1.0 "
                    f"adapter (only {comp_prefix}* and {defs_prefix}* are allowed)",
                    error_code="UNSUPPORTED_OPENAPI_FEATURE",
                    context={"ref": ref, "schema_name": schema_name},
                )
            # V1.1.0 namespace / version guard: a ref's prefix must
            # match the document's declared OpenAPI version. A
            # 3.0 document cannot use ``#/$defs/``; a 3.1
            # document cannot use ``#/components/schemas/`` for
            # shared subschemas (the components.schemas block in
            # 3.1 is reserved for the OpenAPI component model —
            # it is still legal, so we are permissive on the
            # 3.1 side: a 3.1 doc may use either prefix).
            if namespace == "defs" and not _is_openapi_3_1(document_version):
                raise InvalidContractError(
                    f"schema {schema_name!r} $ref={ref!r} is mismatched: "
                    f"document declares OpenAPI {document_version!r} "
                    f"but ref uses the 3.1-only $defs namespace",
                    error_code="INVALID_REF",
                    context={
                        "ref": ref,
                        "schema_name": schema_name,
                        "target": target_name,
                        "namespace": namespace,
                        "document_version": document_version,
                    },
                )
            seen_key = f"{namespace}/{target_name}"
            if seen_key in _seen:
                raise InvalidContractError(
                    f"schema {schema_name!r} $ref={ref!r} forms a cycle (seen: {sorted(_seen)})",
                    error_code="INVALID_REF",
                    context={
                        "ref": ref,
                        "schema_name": schema_name,
                        "target": target_name,
                        "namespace": namespace,
                        "seen": sorted(_seen),
                    },
                )
            if target_name not in target_table:
                raise InvalidContractError(
                    f"schema {schema_name!r} $ref={ref!r} does not resolve "
                    f"(no such schema in {namespace})",
                    error_code="INVALID_REF",
                    context={
                        "ref": ref,
                        "schema_name": schema_name,
                        "target": target_name,
                        "namespace": namespace,
                    },
                )
            target = target_table[target_name]
            if not isinstance(target, dict):
                raise InvalidContractError(
                    f"schema {schema_name!r} $ref={ref!r} points to a non-dict schema",
                    error_code="INVALID_REF",
                    context={
                        "ref": ref,
                        "schema_name": schema_name,
                        "target": target_name,
                        "namespace": namespace,
                    },
                )
            # JSON Schema 2020-12 (and OpenAPI 3.1) allow sibling
            # keywords next to ``$ref``. Per the spec, the siblings
            # *override* the target on a per-key basis. We merge
            # the inlined target with the siblings, recursing on
            # the target first (so a $ref inside the target is
            # also inlined) and then overlaying the siblings.
            # V1.0.0 silently dropped siblings; V1.1.0 preserves
            # them. ``$ref`` itself is removed from the output.
            siblings = {k: v for k, v in schema.items() if k != "$ref"}
            inlined_target = OpenApiAdapter._inline_refs_impl(
                target,
                components_schemas=components_schemas,
                defs=defs,
                schema_name=target_name,
                document_version=document_version,
                _seen=_seen | {seen_key},
            )
            # Merge: start from the inlined target, overlay siblings.
            if not isinstance(inlined_target, dict):
                return inlined_target
            merged: dict[str, typing.Any] = dict(inlined_target)
            merged.update(siblings)
            return merged
        # No $ref at this level. Walk into ``properties`` and ``items``.
        out = dict(schema)
        if "properties" in out and isinstance(out["properties"], dict):
            out["properties"] = {
                k: OpenApiAdapter._inline_refs_impl(
                    v,
                    components_schemas=components_schemas,
                    defs=defs,
                    schema_name=schema_name,
                    document_version=document_version,
                    _seen=_seen,
                )
                for k, v in out["properties"].items()
            }
        if "items" in out:
            out["items"] = OpenApiAdapter._inline_refs_impl(
                out["items"],
                components_schemas=components_schemas,
                defs=defs,
                schema_name=schema_name,
                document_version=document_version,
                _seen=_seen,
            )
        return out


def _translate_nullable_3_0_to_3_1(prop: object) -> dict[str, typing.Any]:
    """Translate OpenAPI 3.0 ``nullable: true`` to JSON Schema ``type: [type, "null"]``.

    OpenAPI 3.0 uses ``nullable: true`` as a sibling of ``type``; OpenAPI 3.1
    (and JSON Schema 2020-12) use ``type`` as a list containing ``"null"``.
    The V1 JSON Schema adapter only understands the 3.1 form, so this
    helper normalizes 3.0 properties before delegation.

    Args:
        prop: A property dict (or other value) from an OpenAPI schema's
            ``properties`` map. Non-dicts are returned unchanged.

    Returns:
        A new dict with ``nullable: true`` translated to a list ``type``,
        or the input unchanged if no translation is needed.
    """
    if not isinstance(prop, dict):
        return prop  # type: ignore[return-value]
    if prop.get("nullable") is not True:
        return prop
    out = {k: v for k, v in prop.items() if k != "nullable"}
    type_value = out.get("type")
    if isinstance(type_value, str):
        out["type"] = [type_value, "null"]
    elif isinstance(type_value, list) and "null" not in type_value:
        out["type"] = [*type_value, "null"]
    return out


# Self-register.
def _register_on_import() -> None:
    from paxman.contract import registry

    registry.register(OpenApiAdapter(), replace=True)


def _is_openapi_3_1(version: str) -> bool:
    """Return ``True`` iff *version* is a 3.1.x OpenAPI document."""
    return version in _OPENAPI_3_1_VERSIONS


def _read_json_schema_dialect(external: dict[str, typing.Any]) -> str | None:
    """Return the document's declared ``jsonSchemaDialect``, or ``None``.

    OpenAPI 3.1 lets a document declare a JSON Schema dialect. V1
    does not dispatch on the value — the V1 JSON Schema adapter
    already targets draft 2020-12 — but the value is **validated**
    and forwarded to the JSON Schema adapter so that ``$schema`` is
    populated correctly on export.

    Raises:
        InvalidContractError: ``INVALID_JSON_SCHEMA_DIALECT`` if the
            value is not a string.
    """
    dialect = external.get("jsonSchemaDialect")
    if dialect is None:
        return None
    if not isinstance(dialect, str):
        raise InvalidContractError(
            f"OpenAPI 'jsonSchemaDialect' must be a str, got {type(dialect).__name__}",
            error_code="INVALID_JSON_SCHEMA_DIALECT",
            context={"got_type": type(dialect).__name__},
        )
    return dialect


def _read_defs(external: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """Return the document's ``$defs`` map, or ``{}`` if absent.

    OpenAPI 3.1 documents may declare a root-level ``$defs`` block;
    V1 reads it as a sibling namespace for ``$ref`` resolution. The
    value is always a dict; a non-dict raises.

    Raises:
        InvalidContractError: ``INVALID_DEF`` if ``$defs`` is not a
            dict.
    """
    defs = external.get("$defs")
    if defs is None:
        return {}
    if not isinstance(defs, dict):
        raise InvalidContractError(
            f"OpenAPI '$defs' must be a dict, got {type(defs).__name__}",
            error_code="INVALID_DEF",
            context={"got_type": type(defs).__name__},
        )
    return defs


_register_on_import()
