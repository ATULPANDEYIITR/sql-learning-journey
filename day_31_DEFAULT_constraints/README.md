# DEFAULT Constraints: Default Values, Generated Defaults, Timestamps, and UUID Defaults

## Topic Scope

A `DEFAULT` constraint defines what a database should store when an `INSERT` statement does not provide a value for a column. Defaults are particularly useful for establishing valid initial state, creating persistence metadata, recording creation time, and generating identifiers.

This topic contains several related mechanisms that should remain conceptually distinct:

- A **static default** supplies a fixed value such as `'pending'`, `0`, `true`, or `'USD'`.
- A **generated default** produces a new value when a row is created, such as a UUID.
- A **timestamp default** records creation time using a database or application clock.
- A **UUID default** establishes an identifier without requiring the caller to supply one.
- **Omission** means the column was not supplied and therefore allows a default to participate.
- **Explicit `NULL`** is a supplied value and normally remains `NULL` when the column permits it. A default should not be assumed to replace explicit `NULL`.

The implementations model these distinctions from application code through a persistence boundary.

---

## Static Default Values

A static default is appropriate when every newly inserted row should begin with the same value unless the caller explicitly overrides it.

Typical examples include:

| Column | Example default | Reason |
|---|---|---|
| `status` | `'pending'` | New workflow records need an initial state. |
| `quantity` | `1` | A single item is a meaningful initial quantity. |
| `priority` | `5` | A neutral operational priority can be established automatically. |
| `enabled` | `true` | Newly created resources can begin in an active state when the domain requires it. |
| `currency` | `'USD'` | A system can define a documented default currency for a specific operating context. |

The important design question is not whether a default can be supplied, but whether the default represents a valid business state.

A default should not be used to hide invalid required information. For example, automatically converting a missing customer identifier into an arbitrary identifier would produce a structurally valid row without producing a meaningful business record.

The Python implementation models static defaults through `create_order()`, `InventoryItem`, and the integrated `Order` class. The JavaScript implementation uses `createAccount()` and the `InMemoryTable` schema. The C++ case study uses repository status, priority, and enabled-state defaults.

---

## Default Application During INSERT

Consider a conceptual table with:

`status TEXT NOT NULL DEFAULT 'pending'`

An insert that supplies no `status` can receive `pending`.

An insert that supplies `status = 'confirmed'` explicitly overrides the default.

This distinction matters because the default is an insertion rule, not a universal assignment rule.

A simplified sequence is:

`INSERT request → determine supplied columns → resolve omitted columns → validate resulting row → persist row`

The Python SQLite example demonstrates this behavior using actual `CREATE TABLE` and `INSERT` statements.

The JavaScript `InMemoryTable` provides an application-level model of the same persistence boundary.

The C++ `RepositoryStore::insert()` method resolves each field according to its state before validating and storing the resulting `RepositoryRecord`.

---

## Omitted Values Versus Explicit NULL

This is one of the most important DEFAULT semantics.

Suppose a column conceptually has:

`description TEXT DEFAULT 'No description'`

An omitted description can receive the default.

An explicit `NULL` is different. If the column permits `NULL`, the stored value can remain `NULL`.

Therefore:

`column omitted` and `column supplied as NULL`

must not automatically be treated as equivalent.

The Python implementation makes this distinction through `simulate_insert()`. It treats an absent dictionary key as omission while allowing an explicit `None` only for nullable fields.

The JavaScript implementation uses the `MISSING` symbol to represent omission. This is necessary because JavaScript's ordinary `undefined` and `null` behavior does not automatically encode SQL insertion semantics.

The C++ implementation uses `OptionalValue<T>` with three states:

- `Omitted`
- `Null`
- `Value`

This is more precise than using `std::optional<T>` alone because ordinary `std::optional` distinguishes a value from no value but does not by itself distinguish "column was not included in the request" from "column was explicitly supplied as NULL."

---

## Generated Defaults

A generated default is evaluated for each newly created row.

An identifier generator is a common example:

`id = generate_uuid()`

The important property is that the generation operation must occur per record.

This is different from generating a value once when a program starts and reusing it:

`shared_id = generate_uuid()`

followed by assigning `shared_id` to every new record.

The latter would produce duplicate identifiers.

The Python `UserRecord` class uses `field(default_factory=generate_uuid)` so every instance receives a separate identifier.

The JavaScript implementation uses `crypto.randomUUID()` inside `createJob()` and `correctRecord()`.

The C++ implementation contains `generateUuidLikeId()` as a self-contained UUID-shaped generator for the case study.

The C++ implementation deliberately identifies this as a demonstration generator rather than presenting it as a replacement for a production UUID library or database-native UUID mechanism.

---

## Timestamp Defaults

Creation timestamps are dynamic defaults because the value depends on when the row is created.

A timestamp should therefore be evaluated at record creation rather than when application code is loaded.

The Python implementation uses:

`datetime.now(timezone.utc)`

through `utc_now()`.

The JavaScript implementation uses:

`new Date().toISOString()`

through `utcTimestamp()`.

The C++ implementation uses `std::chrono::system_clock` and formats the result as a UTC timestamp.

UTC is useful for persisted timestamps because it gives records a common temporal reference independent of the server's local timezone. Applications can convert the stored timestamp into a user's local timezone when displaying it.

### Timestamp ownership

Timestamp ownership should be deliberate.

A database-owned creation timestamp can be preferable when the persistence layer must be authoritative about when a row was actually stored.

An application-owned timestamp can be useful when the application needs the value before persistence, such as when an identifier and timestamp must be included in an event emitted before a database operation.

The important architectural distinction is whether the timestamp represents application-observed time or persistence-system time.

---

## UUID Defaults

UUIDs are useful when identifiers need to be generated without relying on a sequential database integer.

A UUID-based identifier can be generated in the application:

`crypto.randomUUID()`

or through a database-supported UUID mechanism.

The choice is an ownership decision.

### Application-owned UUID

Application-side generation is useful when the identifier must exist before persistence.

Examples include:

- constructing an event that references the new entity,
- returning an identifier before a database round trip,
- correlating logs and application operations,
- preparing related objects before a transaction is committed.

The Python and JavaScript implementations demonstrate this pattern.

### Database-owned UUID

Database-side generation can centralize identifier creation when multiple applications write to the same database.

This can reduce the risk of different clients implementing incompatible identifier policies.

The actual syntax for UUID generation differs between database engines, so the database-specific expression should be treated as part of the schema design rather than assumed to be portable SQL.

---

## Python Implementation

The Python program develops a complete default-resolution model and then connects the concepts to a real SQLite database.

The early `create_order()` function demonstrates static defaults while preserving validation of quantity, status, and currency.

`UserRecord` demonstrates per-instance UUID generation through `default_factory`. This is particularly important because a UUID must be generated independently for every object.

`AuditRecord` demonstrates timestamp defaults and uses timezone-aware UTC timestamps.

`simulate_insert()` explicitly distinguishes omission from explicit `None`, making the difference between a missing value and `NULL` visible in executable behavior.

The SQLite section creates actual tables with definitions such as:

`status TEXT NOT NULL DEFAULT 'pending'`

and:

`created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`

This part moves the example from an application-level simulation into actual database behavior.

The program also demonstrates `DEFAULT VALUES`, where all columns with defaults can be populated without explicitly naming individual values.

The integrated `Order` class combines:

- a generated UUID,
- a static status default,
- a static currency default,
- a dynamic timestamp,
- an active-state default,
- business validation,
- state transitions.

The migration example demonstrates that changing a default is not equivalent to changing historical records. The program rebuilds a SQLite table to change the schema policy and separately demonstrates the distinction between existing data and future inserts.

---

## JavaScript Implementation

The JavaScript implementation emphasizes runtime behavior and persistence abstractions.

`createAccount()` demonstrates static defaults using object construction.

The `MISSING` symbol is used because JavaScript needs an explicit representation for "this field was not supplied" when modeling SQL behavior. This prevents the implementation from incorrectly treating omission and explicit `null` as identical.

`generateUuid()` uses Node.js's built-in `crypto.randomUUID()`, providing a production-relevant standard-library mechanism for UUID generation.

`utcTimestamp()` uses JavaScript's ISO timestamp representation, which is naturally suitable for serializing UTC timestamps.

`InMemoryTable` models a persistence layer with column definitions containing:

- required status,
- nullability,
- default generation,
- validation.

This provides a useful representation of how an application might resolve defaults before a database write.

`DefaultAwareRepository` adds an event-driven perspective. Once a record has been constructed with its defaults, an `inserted` event is emitted. This demonstrates a JavaScript-specific relationship between persistence behavior and event-driven application architecture.

The migration model demonstrates an important rule: changing the default used by future inserts does not inherently rewrite old records. A separate migration function is required when historical data must be changed.

The update example also shows that INSERT defaults should not be confused with UPDATE behavior. Updating one property leaves unrelated existing properties unchanged unless the update explicitly modifies them.

---

## C++ Repository Metadata Case Study

The C++ implementation models a repository metadata service.

A repository has fields such as:

- `id`
- `name`
- `status`
- `priority`
- `enabled`
- `description`
- `createdAt`

The persistence model uses different default policies for these fields.

The repository identifier is generated when the caller omits it.

The repository status defaults to `active`.

Priority defaults to `5`.

Enabled defaults to `true`.

Creation time is generated at persistence time.

Description is nullable and has no textual default, allowing the implementation to demonstrate the difference between an omitted nullable field and a field with an actual default.

### Three-state input model

`OptionalValue<T>` is central to the case study.

It represents:

`Omitted`

`Null`

`Value`

This makes the C++ model closer to database semantics than a simple value-or-no-value representation.

For a non-nullable field such as `status`, an omitted value invokes the default while an explicit NULL causes an error.

For nullable `description`, omission produces `NULL` because there is no default, while explicit NULL also remains NULL.

### Validation

The store validates the resolved record rather than assuming that a default makes the record automatically correct.

For example, priority must remain between `0` and `100`.

This demonstrates an important design principle:

**A DEFAULT establishes a starting value; validation establishes whether the resulting value is allowed.**

### UPDATE behavior

`updatePriority()` explicitly changes an existing priority.

The method does not reapply the INSERT default.

This models the database distinction between insertion-time defaults and later updates.

### Transaction-like batch processing

`TransactionalRepositoryStore` demonstrates batch behavior.

If one record fails validation, the model restores the previous state rather than leaving only part of the batch inserted.

A real relational database would normally provide transaction and rollback mechanisms directly. The C++ snapshot is an educational representation of the same atomicity requirement rather than a replacement for database transactions.

---

## Default Ownership

Default ownership should be documented because the same logical default can be implemented at different layers.

| Value | Possible owner | Important design question |
|---|---|---|
| `status = 'pending'` | Database | Should every writer receive the same initial state automatically? |
| `created_at = current time` | Database | Should persistence time be authoritative? |
| `id = UUID` | Application | Does the application need the ID before the insert? |
| `id = UUID` | Database | Should all writers use one centralized identifier policy? |
| `enabled = true` | Database | Is activation really the correct initial state for every writer? |

Database-owned defaults are valuable when many independent writers must share the same persistence policy.

Application-owned defaults are useful when the application must know the generated value before persistence or when the value participates in application logic before the INSERT.

Duplicating the same default policy in several applications can create drift. If one service changes its application default while another continues using the old value, the database can receive inconsistent initial states.

---

## Defaults and Validation

Defaults should produce valid initial values, but they should not be treated as a replacement for validation.

For example, an order might define:

`quantity DEFAULT 1`

That does not mean a supplied quantity of `-5` should be accepted.

Similarly:

`status DEFAULT 'pending'`

does not mean every arbitrary status string should be accepted when explicitly supplied.

A robust persistence path therefore resembles:

`request → omission/default resolution → validation → persistence`

rather than:

`request → blindly fill missing fields → persistence`

The Python, JavaScript, and C++ implementations all validate after resolving defaults.

---

## Defaults and Migrations

Changing a default is primarily a schema-policy change.

Suppose the original schema uses:

`state DEFAULT 'pending'`

and a later schema uses:

`state DEFAULT 'queued'`

A new insert can receive `queued`, while an existing row containing `pending` normally remains `pending`.

If historical records must also move to `queued`, that is a separate data migration.

This distinction is critical because automatically rewriting historical values could destroy meaningful historical state.

The implementations deliberately separate:

- changing the default for future records,
- migrating existing records.

A production migration should define whether existing data is intentionally transformed and should account for constraints, indexes, concurrent writes, rollback behavior, and application compatibility.

---

## Default Expressions

A default can be a literal or a database-supported expression, depending on the database engine.

Common conceptual forms include:

`DEFAULT 0`

`DEFAULT 'pending'`

`DEFAULT TRUE`

`DEFAULT CURRENT_TIMESTAMP`

Database-specific UUID generation expressions may also be available.

Default-expression support is not completely portable across database systems. A schema designed for one database should therefore be checked against the actual target engine rather than assuming that every expression is standard across PostgreSQL, MySQL, SQLite, SQL Server, and other systems.

---

## DEFAULT and NULLability

These properties answer different questions.

A `DEFAULT` answers:

**What should happen when the column is omitted during insertion?**

Nullability answers:

**Is NULL an allowed stored value?**

Therefore, a column can be:

- non-nullable with a default,
- nullable with a default,
- non-nullable without a default,
- nullable without a default.

For example:

`status TEXT NOT NULL DEFAULT 'pending'`

requires a meaningful status for every stored row and provides one automatically when omitted.

By contrast:

`description TEXT DEFAULT 'No description'`

can still permit explicit NULL if the column remains nullable.

The combination of default and nullability should match the domain semantics rather than being selected independently.

---

## Common Failure Modes

### Treating NULL as the same as omission

An API may interpret `null` as "use the default" while the database interprets explicit NULL as an actual value. This mismatch can produce surprising persistence behavior.

The solution is to define the API contract explicitly.

### Generating one UUID for many rows

Generating a UUID once during application initialization and reusing it creates duplicate identifiers.

Generated values must be evaluated per record.

### Generating timestamps at module initialization

A timestamp stored in a module-level variable can cause every subsequent record to receive the same creation time.

Timestamp generation belongs at record creation or persistence time.

### Assuming a default validates user input

Defaults only handle omitted values. Explicit invalid values still require validation.

### Assuming a changed default updates existing rows

Schema defaults normally affect future insert operations. Historical data requires a deliberate migration.

### Duplicating database defaults in multiple services

Multiple application-side implementations of the same default can diverge. Centralizing important persistence rules can prevent inconsistent data.

### Using a local timezone for persisted creation timestamps

Different servers may run in different timezones. UTC provides a common storage representation and reduces ambiguity.

---

## Performance Considerations

Literal defaults are generally inexpensive because they do not require complex computation.

Dynamic defaults such as timestamps execute once per inserted row.

UUID generation is also normally inexpensive, but identifier size and ordering can influence storage and index behavior. Randomly distributed identifiers can have different index locality characteristics from sequential integer identifiers.

For high-volume systems, identifier design should therefore consider:

- index structure,
- storage size,
- insertion locality,
- distributed generation,
- collision guarantees,
- database-native UUID support,
- application requirements for pre-persistence identifiers.

Default expressions that perform expensive computation should be treated carefully because they execute as part of record creation.

---

## Security Considerations

Defaults are not authorization mechanisms.

A default role such as `member` can establish an initial identity state, but an application must still verify authorization when an operation is requested.

Similarly, an `enabled DEFAULT true` rule should not be interpreted as permission to access every system resource.

Generated identifiers should be treated as identifiers, not authorization secrets.

If a system needs a secret token, it should use an appropriate cryptographic secret-generation mechanism and enforce access controls independently of the token's default-generation behavior.

---

## Testing DEFAULT Behavior

Default-related tests should verify at least these distinct paths:

| Scenario | Expected behavior |
|---|---|
| Column omitted | Default is applied when one exists. |
| Explicit valid value | Explicit value replaces the default. |
| Explicit NULL on nullable column | NULL remains NULL. |
| Explicit NULL on non-nullable column | Insert is rejected. |
| Two records with UUID defaults | Identifiers differ. |
| Two records with timestamp defaults | Timestamps are generated independently. |
| Invalid explicit value | Validation rejects it. |
| Default changed | Future records use the new policy. |
| Existing historical data | Existing values remain unchanged unless explicitly migrated. |
| UPDATE without changing a defaulted column | Existing stored value remains unchanged. |

These tests expose semantic errors that a single happy-path insert would miss.

---

## Debugging Default Behavior

When debugging a default, inspect the actual INSERT payload and the persisted result separately.

A final row alone may not reveal whether a value was:

- supplied by the application,
- supplied by a database default,
- generated by a trigger,
- generated by an ORM,
- or populated during a later migration.

Logging should therefore be designed around the persistence boundary.

For generated timestamps and UUIDs, logs can include correlation identifiers and event metadata without treating those generated values as interchangeable with user-supplied fields.

---

## Production Design Principles

A production schema should define defaults according to ownership and business meaning.

Use static defaults when a stable initial value is genuinely valid.

Use generated defaults when every new row needs an independent value.

Use database timestamps when the database should be authoritative about persistence time.

Use application-generated UUIDs when the identifier must be available before persistence.

Use database-generated UUIDs when centralized identifier ownership is more appropriate.

Keep NULLability separate from default semantics.

Validate explicit values even when defaults exist.

Treat default changes as schema changes and historical data changes as separate migrations.

Document whether a default belongs to the database, application, ORM, or another persistence layer.

The Python, JavaScript, and C++ implementations deliberately model these ownership boundaries rather than treating every default as merely a language-level fallback.
