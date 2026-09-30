# UNIQUE and CHECK Constraints: Constraints, Business Rules, and Data Integrity

## Introduction

`UNIQUE` and `CHECK` constraints solve different data-integrity problems.

A `UNIQUE` constraint prevents two rows from occupying the same uniqueness key. It is appropriate when a value or combination of values identifies something that must not collide, such as a product SKU, customer email address, or the combination of an order and product.

A `CHECK` constraint evaluates whether values satisfy a defined predicate. It is appropriate for rules such as a price being non-negative, a quantity being positive, or a discount percentage remaining between 0 and 100.

Business rules are broader. Some can be expressed directly as `CHECK` or `UNIQUE` constraints, while others depend on multiple rows, state transitions, inventory, transactions, or external systems.

The three implementations in this repository deliberately separate these concepts rather than treating every validation rule as the same kind of constraint.

## Constraint Model

A useful distinction is:

| Mechanism | Primary question | Example |
| --- | --- | --- |
| `UNIQUE` | Can another row use this same key? | Can another product use SKU `LAP-001`? |
| `CHECK` | Does this row satisfy the allowed predicate? | Is `price >= 0`? |
| Business rule | Is this operation valid in the wider domain? | Can this order reserve the requested inventory? |

The database is the authoritative enforcement boundary for constraints that belong to persistent data integrity.

Application validation still has an important role. It can normalize input, provide immediate error messages, avoid unnecessary database work, and guide users toward valid data. It should not be treated as a replacement for database-level enforcement when concurrent operations can occur.

## UNIQUE Constraints

A `UNIQUE` constraint defines a uniqueness key.

A simple uniqueness rule might be represented conceptually as:

`UNIQUE(sku)`

This means two rows cannot have the same SKU under the database's uniqueness semantics.

The Python implementation creates this rule on the `products` table:

`sku TEXT NOT NULL UNIQUE`

The same schema gives customer email addresses uniqueness through:

`email TEXT NOT NULL UNIQUE`

These are different domain identifiers, but they have the same structural requirement: a concrete identifier cannot collide with another existing identifier.

### Composite UNIQUE Constraints

A composite constraint uses more than one column:

`UNIQUE(category, product_name)`

The Python program uses this rule for products. A product named `Pro 14` may exist in the `Laptop` category and another product named `Pro 14` may exist in the `Phone` category. The complete pair is the uniqueness key.

The important distinction is that the rule does not mean:

`UNIQUE(product_name)`

It means:

`UNIQUE(category, product_name)`

The JavaScript implementation models the same concept with a `UniqueConstraint` containing multiple fields. Its key-generation mechanism combines the normalized category and product name into a composite identity.

The C++ implementation uses an `unordered_set` to represent the same composite key in memory. This makes the case study substantially different from the Python SQLite implementation while preserving the same relational concept.

### Why Normalization Matters

A database may consider `User@Example.com` and `user@example.com` equal or different depending on the database, column type, collation, and comparison rules.

An application may also accidentally permit logically duplicated identifiers if it validates unnormalized input.

The JavaScript implementation explicitly trims and lowercases the fields used by its in-memory uniqueness model. In a production database, normalization and collation should be designed deliberately rather than assuming that application-side transformations and database comparison semantics are automatically identical.

### NULL and UNIQUE

`NULL` deserves special treatment.

In many relational database systems, a nullable `UNIQUE` column can contain multiple `NULL` values because `NULL` represents the absence or unknown state of a value rather than a concrete value that equals another `NULL`.

The Python implementation demonstrates this with a separate `nullable_demo` table.

If a business identifier must always exist and must also be unique, the typical schema is conceptually:

`external_reference TEXT NOT NULL UNIQUE`

`NOT NULL` and `UNIQUE` solve different problems:

- `NOT NULL` requires a value.
- `UNIQUE` prevents duplicate values.

Neither constraint should be assumed to provide the other's behavior.

## CHECK Constraints

A `CHECK` constraint defines a predicate that a row must satisfy.

The Python product table contains several examples:

`price NUMERIC NOT NULL CHECK (price >= 0)`

`stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0)`

`discount_percent NUMERIC NOT NULL CHECK (discount_percent >= 0 AND discount_percent <= 100)`

`status TEXT NOT NULL CHECK (status IN ('active', 'inactive'))`

These constraints express valid states for individual rows.

### Numeric Domain Rules

A price of `-500` is not a valid product price in this model. The `CHECK` constraint prevents it from entering the table.

Likewise, a stock quantity of `-2` is invalid and a discount of `101` percent is outside the allowed domain.

The Python implementation intentionally attempts these writes and catches `sqlite3.IntegrityError`. This demonstrates that the validation is not merely documentation. SQLite actually rejects the invalid data.

### Enumerated State Rules

A `CHECK` constraint can restrict a text column to a known set of states.

The customer table uses:

`account_status TEXT NOT NULL CHECK (account_status IN ('active', 'suspended', 'closed'))`

This prevents an accidental value such as `pending-review` from entering the database when that state is not part of the defined model.

The rule is different from uniqueness. Multiple customers may legitimately have the `active` status. The requirement is not that the value be unique. The requirement is that every value belong to the permitted domain.

### CHECK Is Not a General Rule Engine

A `CHECK` constraint is well suited to row-local conditions.

Examples include:

`quantity > 0`

`price >= 0`

`discount_percent BETWEEN 0 AND 100`

A rule such as "the requested order quantity must not exceed current inventory" depends on another record and potentially on concurrent transactions. It is not equivalent to checking a single column in the order-item row.

The Python, JavaScript, and C++ implementations therefore distinguish row-level checks from broader business rules.

## Business Rules

Business rules describe valid behavior for the domain.

Some business rules can be directly represented by constraints.

For example:

- A product SKU must be unique.
- A product price cannot be negative.
- An order-item quantity must be positive.
- An order cannot contain the same product more than once.

Other rules involve state or relationships:

- An order cannot be submitted without an item.
- Requested quantity cannot exceed available inventory.
- An order total should correspond to its items.
- A state transition may only be allowed from a particular previous state.

The appropriate enforcement mechanism depends on the rule's scope.

A row-local invariant can often be enforced by `CHECK`. An identity collision can often be enforced by `UNIQUE`. A multi-row invariant may require a transaction, locking strategy, trigger, stored procedure, application service, or another database mechanism.

## Python Implementation

The Python implementation uses the standard-library `sqlite3` module, making the program executable without an external database server or third-party dependency.

The schema models a small commerce domain containing:

- customers
- products
- orders
- order items

The product table combines several constraint types. SKU uses a single-column `UNIQUE` constraint, while `(category, product_name)` uses a composite `UNIQUE` constraint.

The same product table contains `CHECK` predicates for price, stock, discount percentage, and status.

The order-item table adds:

`UNIQUE(order_id, product_id)`

This models the rule that a particular product should appear only once in an order.

### Transaction Demonstration

The Python program intentionally creates a transaction containing two order inserts. The first insert is valid, while the second violates `CHECK(total_amount >= 0)`.

The transaction fails and the successful-looking first insert does not remain as a partially committed operation.

This illustrates why constraint enforcement and transactions are related. A constraint identifies invalid data, while the transaction determines whether a group of related writes becomes one atomic unit.

### Application Validation and Database Enforcement

The Python program also performs application-level validation before attempting a database write.

This provides useful early feedback:

- malformed email input can be detected before a query
- empty names can be rejected immediately
- negative prices can be reported clearly
- invalid discount percentages can be identified before persistence

The database constraint still matters because a pre-check is not inherently atomic with the eventual insert.

Two concurrent application processes could both observe that an email appears available and then both attempt to insert it. The database `UNIQUE` constraint is what prevents both writes from creating the same unique identity.

### Conditional Uniqueness

The Python implementation demonstrates a partial unique index for active aliases.

The rule is effectively:

`UNIQUE(alias) WHERE active = 1`

This allows multiple inactive records with the same alias while preventing two active records from sharing it.

This pattern is useful when uniqueness applies only to a subset of records and the database supports partial or filtered indexes.

## JavaScript Implementation

The JavaScript file implements an in-memory constraint system instead of translating the Python SQLite schema.

`UniqueConstraint` receives one or more fields and constructs a uniqueness key. This makes the same class capable of modeling both:

`UNIQUE(sku)`

and:

`UNIQUE(category, productName)`

`CheckConstraint` stores a predicate and a human-readable description. Each product is evaluated against the configured checks.

This creates a clear separation between identity collision detection and value-domain validation.

### Event-Driven Processing

The JavaScript implementation uses Node.js `EventEmitter` to demonstrate how application code can react to validation results.

A successful product insertion emits `product:accepted`.

A rejected operation emits `constraint:violation`.

This is deliberately an application-layer representation. An event handler does not replace database constraints. It demonstrates where domain-level reactions can occur after a validation decision.

### Order Model

`ReviewableOrder` represents a different part of the domain.

It enforces that:

- quantities are positive integers
- the same product cannot be added twice
- requested quantity cannot exceed available stock
- an order cannot be submitted while empty

The first and second rules map naturally to constraint concepts.

The inventory rule is a broader business rule because it depends on product state.

The empty-order rule is a state-transition rule because it depends on the order's current contents and requested transition.

## C++ Case Study

The C++ program implements an inventory catalog and order-processing case study.

The architecture contains:

`ConstraintEngine`

This component evaluates product uniqueness and row-level checks.

`InventoryCatalog`

This component stores products and commits only records that pass validation.

`Order`

This component represents order state and evaluates order-item rules and higher-level business rules.

### Product Uniqueness

The C++ catalog maintains an `unordered_map` for SKU lookup and an `unordered_set` for composite `(category, name)` keys.

This provides an efficient in-memory representation of the uniqueness requirements.

The map allows fast detection of an existing SKU, while the set allows fast detection of a category/name collision.

The exact performance characteristics of a production database index differ from this in-memory model, but the data structure demonstrates why uniqueness enforcement normally requires an efficient lookup structure.

### Product CHECK Rules

The C++ `ConstraintEngine` evaluates:

- price must be non-negative
- stock must be non-negative
- discount must be between 0 and 100
- status must be `active` or `inactive`
- required identity fields cannot be empty

These are structurally similar to SQL `CHECK` constraints because each rule evaluates the current product's values.

### Order-Level Uniqueness

The order maintains a vector of items and checks whether the product ID already exists before adding another item.

This represents:

`UNIQUE(order_id, product_id)`

The uniqueness key is not the product alone. A product can exist in many different orders. It is the combination of the order identity and product identity that must not repeat.

### Inventory as a Business Rule

Inventory availability is treated differently.

The program checks whether:

`requested quantity <= product stock`

This rule requires information outside the new order-item values.

In a real database-backed system, concurrency is important. A simple application read followed by a later update can suffer from races when multiple orders attempt to consume the same inventory. A production implementation needs a transaction and a concurrency strategy appropriate to the database isolation model.

## Constraint Ordering

An application often performs several kinds of validation before a write.

A useful conceptual sequence is:

- normalize values that have defined canonical forms
- validate basic input requirements
- check application-level constraints that improve user feedback
- attempt the database operation
- handle database constraint violations as authoritative outcomes

The sequence does not mean every application must manually query for every `UNIQUE` conflict.

A query such as "does this email already exist?" can improve the error message, but the final insert must still handle a uniqueness violation because another transaction can change the state between the check and the write.

## Error Handling

Constraint violations should be treated as expected data events rather than mysterious application failures.

Typical categories include:

| Failure | Appropriate interpretation |
| --- | --- |
| Duplicate SKU | `UNIQUE` conflict |
| Duplicate `(category, name)` | Composite `UNIQUE` conflict |
| Negative price | `CHECK` violation |
| Discount above 100 | `CHECK` violation |
| Duplicate product in an order | Composite uniqueness conflict |
| Quantity greater than inventory | Business-rule violation |
| Empty order submission | State/business-rule violation |

The distinction is useful because the response can differ.

A duplicate SKU may result in a "SKU already exists" message. A negative price is an invalid value. An inventory conflict may require a fresh inventory read or a different order quantity.

## Edge Cases

### Case and Whitespace

Whether `ABC-001` and `abc-001` are considered the same identifier depends on normalization and database comparison rules.

An application should define canonicalization deliberately for identifiers where case-insensitive identity is required.

### NULL

Nullable unique columns require explicit consideration because database systems can treat `NULL` differently from ordinary values.

If a field represents a required business identifier, using both `NOT NULL` and `UNIQUE` makes the intent clearer.

### Composite Keys

Composite uniqueness must be evaluated as the complete combination.

`UNIQUE(category, product_name)` does not prohibit the same product name from appearing in another category.

### Floating-Point Values

A business rule involving money should not casually depend on binary floating-point equality.

The C++ case study uses `double` for readability, but a production financial system would normally use a decimal-capable database representation or integer minor units such as cents or paise, depending on the domain requirements.

### Empty Strings

`NOT NULL` does not necessarily prevent an empty string.

A value such as `''` is not the same thing as SQL `NULL`.

If an identifier must contain meaningful text, the schema or application must define and enforce that requirement explicitly.

## Constraints and Concurrency

A major reason to enforce uniqueness at the database layer is concurrency.

Consider two processes trying to create the same SKU:

Process A checks whether `LAP-500` exists and receives "no."

Process B checks whether `LAP-500` exists and also receives "no."

Both processes then attempt to insert the SKU.

A pre-check alone cannot guarantee uniqueness. The database's unique index or constraint is designed to arbitrate the concurrent writes.

The application should therefore be prepared to catch a uniqueness violation even when it performed an earlier existence check.

The same principle applies to other constraints that must remain true under concurrent writes.

## Performance Considerations

`UNIQUE` constraints normally require an index-like structure so the database can efficiently detect collisions.

Indexes improve lookup and constraint enforcement but also impose costs:

- inserts and updates may need to maintain the index
- additional storage is required
- indexed columns influence write performance
- composite index order affects query usefulness

The C++ case study uses hash-based structures to make the lookup concept explicit. Real relational databases use database-specific index structures and query-planning strategies.

`CHECK` predicates are generally different. A simple row-local check such as `price >= 0` does not require a uniqueness index because the database evaluates the predicate for the row being inserted or updated.

## Security Considerations

Constraints are data-integrity mechanisms, not SQL-injection defenses.

Parameterized SQL should still be used for database operations.

For example, application code should bind an email as a parameter rather than constructing SQL by concatenating user input.

Constraint names and error messages should also be handled carefully in externally exposed APIs. Internal database details can reveal schema information that does not need to be sent directly to untrusted clients.

## Common Design Mistakes

### Using Application Checks Without Database Constraints

Checking for an existing value in application code and then inserting it is not sufficient for concurrent workloads.

The database should enforce the invariant when the rule belongs to persistent data integrity.

### Making a Value UNIQUE When the Domain Requires a Composite Key

If two categories may legitimately contain products with the same name, `UNIQUE(product_name)` is too restrictive.

`UNIQUE(category, product_name)` expresses the actual identity requirement.

### Using CHECK for Cross-Row Rules

A row-level `CHECK` is not a general-purpose substitute for transaction-aware business logic.

Inventory reservation, aggregate limits, and other cross-row conditions require mechanisms appropriate to their consistency requirements.

### Assuming NOT NULL Means Non-Empty

`NOT NULL` rejects SQL `NULL`, not necessarily empty text.

If an empty identifier is invalid, that rule must be represented explicitly.

### Treating Validation as the Same as Enforcement

Client-side validation, API validation, service validation, and database constraints operate at different layers.

They can complement one another, but they have different guarantees.

## Practical Relationship Between the Three Concepts

The three concepts form a useful hierarchy.

`UNIQUE` protects identity boundaries.

For example, one SKU should not identify two different products.

`CHECK` protects value boundaries.

For example, a product discount must remain between 0 and 100.

Business rules protect behavioral and relational boundaries.

For example, an order should not consume more inventory than is available.

A mature design places each rule at the layer capable of enforcing it correctly. Simple row invariants belong close to the data. Cross-row and stateful rules require transaction-aware logic when their correctness depends on changing shared state.

## Implementation Comparison

| Concern | Python | JavaScript | C++ |
| --- | --- | --- | --- |
| Persistent constraint enforcement | SQLite | In-memory model | In-memory model |
| Simple UNIQUE | SQLite column constraint | `UniqueConstraint` | `unordered_map` |
| Composite UNIQUE | SQLite table constraint | Multi-field key | `unordered_set` composite key |
| CHECK | SQLite `CHECK` expressions | Predicate objects | Validation methods |
| Transactions | SQLite transaction context | Not simulated as persistence | Domain-level operation flow |
| NULL behavior | Demonstrated with SQLite | Explicitly modeled | Not central to the case study |
| Conditional uniqueness | SQLite partial unique index | Not implemented as a database feature | Not implemented as a database feature |
| Cross-entity business rules | Order/inventory examples | Order/inventory examples | Order/inventory case study |
| External dependencies | None | Node.js runtime only | C++17 standard library |

The implementations are intentionally not line-by-line translations. Each language emphasizes a different technical representation of the same integrity concepts.

## Production Considerations

A production schema should define the business invariant first and then select the appropriate enforcement mechanism.

For an identifier such as a customer email or product SKU, determine whether uniqueness is global, scoped to a tenant, conditional on a state, or dependent on normalized representation.

For numeric fields, define valid ranges and decide whether precision requirements make integer minor units or decimal database types preferable.

For state values, define the permitted states and determine whether additional state-transition rules need enforcement outside a simple `CHECK`.

For multi-row rules, determine the transaction boundary and concurrency behavior before implementing the rule.

For application code, treat database constraint violations as expected outcomes that require controlled error handling rather than assuming validation performed earlier in the request lifecycle guarantees success.

The resulting system is strongest when `UNIQUE` protects identity, `CHECK` protects row-level value validity, and broader business rules are enforced by transaction-aware domain logic where necessary.
