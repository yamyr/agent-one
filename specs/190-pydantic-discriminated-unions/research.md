# Research: Pydantic Discriminated Unions for Messages

## R1: Pydantic v2 Discriminated Union Pattern

**Decision**: Use `Annotated[Union[...], Field(discriminator="type")]` with `Literal` type fields on each subclass.

**Rationale**: This is the canonical Pydantic v2 pattern for tagged unions. The discriminator field (`type`) is already present in our message schema and takes one of five known string values. Pydantic automatically selects the correct model based on the discriminator value during validation, providing both construction-time safety and deserialization.

**Alternatives considered**:
- Custom `__init_subclass__` registry: More code, less standard, no Pydantic validation benefits.
- Single model with `type: MessageType` enum (no subclasses): Provides enum validation but not true type discrimination for deserialization.
- `model_validator` with manual dispatch: Unnecessary complexity when native discriminator support exists.

## R2: Serialization Compatibility (model_dump vs asdict)

**Decision**: Use `model_dump()` as the implementation of `to_dict()`. The output structure is identical to `dataclasses.asdict()` for flat models with primitive fields.

**Rationale**: Both `asdict()` and `model_dump()` produce `dict[str, Any]` with the same keys and values for models containing only primitive types (str, int, float, dict, None). The `ts` field (float), `tick` (int), `id` (str), `correlation_id` (str | None) all serialize identically. The `payload` (dict) is passed through without transformation by both methods.

**Alternatives considered**:
- `model_dump(mode="json")`: Converts to JSON-safe types, but changes float to str for some fields. Rejected.
- Custom serializer: Unnecessary since `model_dump()` already produces the correct output.

## R3: Default Factory Pattern for Pydantic

**Decision**: Use `Field(default_factory=...)` for `id`, `ts`, and `tick` fields.

**Rationale**: Pydantic v2's `Field(default_factory=...)` works identically to dataclass `field(default_factory=...)`. The `id` field uses `lambda: str(uuid4())`, `ts` uses `time.time`, and `tick` uses `world.get_tick()`. These are all callable factories that produce fresh values per instance.

**Alternatives considered**:
- `@model_validator(mode="before")`: Would work but adds unnecessary complexity for simple default generation.
- Class-level `__init__` override: Anti-pattern in Pydantic; breaks validation chain.

## R4: make_message() Factory Retention

**Decision**: Keep `make_message()` as a convenience factory that maps the `type` string argument to the appropriate typed constructor. This minimizes call-site changes while providing typed returns.

**Rationale**: The function is called ~50 times across 4 files. Many call sites pass `type` as a variable (e.g., `event_type = "command" if ... else "action"`). A factory that dispatches on the type string is the least disruptive migration path.

**Alternatives considered**:
- Replace every call site with direct typed constructors (e.g., `ActionMessage(...)`): Would require refactoring conditional type logic at many call sites. Too invasive for this iteration.
- Remove `make_message()` entirely: Would break the existing API contract unnecessarily.

## R5: BaseMessage as Abstract Base

**Decision**: Define `BaseMessage` as a concrete Pydantic `BaseModel` with `type: str` field, then override `type` in each subclass with a `Literal`. Do NOT make `BaseMessage` instantiable for external use — guide developers to typed subclasses.

**Rationale**: Pydantic v2 requires concrete base models for discriminated unions. The base model defines the common schema; subclasses narrow the `type` field. The `AnyMessage` union type is what consumers use for parsing.

**Alternatives considered**:
- ABC (Abstract Base Class): Pydantic models cannot be abstract in the traditional sense; `ABC` mixin causes issues with `model_validate`.
- No base class (repeat fields in each subclass): Violates DRY, makes maintenance harder.
