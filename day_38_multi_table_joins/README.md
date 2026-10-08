# Multi-Table JOINs

## Scope

Multi-table JOINs combine rows from three or more relational tables through defined relationships. The central problem is not simply writing several `JOIN` keywords. The important work is identifying the relationship path, preserving the intended cardinality, choosing the correct join type, placing predicates correctly, and understanding how the database optimizer can execute the logical query.

The implementations in this project use a sales-order domain because it contains several realistic relationship patterns:

`Sales Region -> Customer -> Order -> Order Item -> Product`

This chain demonstrates one-to-many relationships, a bridge table, optional relationships, aggregation after joins, and queries that need attributes from several levels of a relational model.

The six deliverables deliberately approach the same relational subject from different technical perspectives:

| File | Primary perspective |
|---|---|
| Python | Executable relational workflow using SQLite and indexed lookups |
| JavaScript | Explicit join functions, array processing, grouping, and asynchronous repository behavior |
| C++ | Performance-oriented case study using hash indexes and explicit relationship traversal |
| Java | Immutable enterprise domain model with records, maps, streams, validation, and services |
| SQL | PostgreSQL relational schema, constraints, indexes, CTEs, aggregation, and query plans |
| README | Technical explanation of the relationship between join structure, cardinality, ordering, and query behavior |

## Relational Model

The example contains five tables.

### Sales regions

`sales_regions` represents the geographical or organizational grouping associated with a customer.

A region has a primary key, `region_id`, and a unique name. A region can have many customers, but each customer belongs to one region.

The relationship is:

`regions.region_id -> customers.region_id`

This is a one-to-many relationship.

### Customers

`customers` represents organizations purchasing products. Each customer stores a foreign key to its region.

The customer table is an intermediate relation in the larger join path. It connects regional information to order information.

The relationship is:

`customers.customer_id -> orders.customer_id`

A customer can have zero, one, or many orders.

### Orders

`orders` represents individual commercial transactions. The `status` field distinguishes placed, shipped, delivered, and cancelled orders.

An order belongs to exactly one customer in this model. One customer can therefore produce multiple order rows.

This distinction matters when aggregating because a customer-level result and an order-level result have different cardinalities.

### Products

`products` contains the catalogue of available products. The product price represents the current catalogue price, while `order_items.unit_price` records the price used for the specific transaction.

Keeping the transaction price on `order_items` is important because historical order values should not change merely because the catalogue price changes later.

### Order items

`order_items` is the associative table between orders and products.

An order can contain multiple products, and a product can appear in multiple orders. This creates a many-to-many relationship:

`orders <-> products`

The relationship is resolved through:

`orders -> order_items -> products`

The composite primary key `(order_id, product_id)` prevents the same product from appearing twice in the same order in this particular model.

## Why Three or More Tables Change the Problem

A two-table join usually has one direct relationship:

`customers -> orders`

A multi-table join creates a relationship path:

`regions -> customers -> orders -> order_items -> products`

Every additional table introduces another join condition and another opportunity for row multiplication or accidental row loss.

For example, one customer can have five orders, and one order can have ten line items. Joining the customer to the orders produces five rows for that customer. Joining those orders to their items can produce as many as fifty rows.

This is not duplicate data created by the database. It is the natural result of relational cardinality.

The correct question is therefore not "Why did the JOIN duplicate my customer?" but "What level of detail does the resulting relation represent?"

A result containing one row per order item legitimately repeats customer and order attributes.

## JOIN Mechanics

An inner join retains rows for which the join predicate succeeds on both sides.

A three-table query can be read logically as a sequence of relational transformations:

`customers JOIN orders JOIN order_items`

The first relationship matches customers to their orders. The second relationship matches each resulting order to its line items.

The final relation therefore contains line-level information associated with both the customer and order.

A five-table query extends that path:

`regions JOIN customers JOIN orders JOIN order_items JOIN products`

The join predicates must follow the foreign-key relationships:

- region to customer through `region_id`
- customer to order through `customer_id`
- order to item through `order_id`
- item to product through `product_id`

A technically valid SQL query can still be logically wrong if one of these predicates uses an unrelated column.

## Join Order

Join order has two different meanings.

The first is the order in which relationships are written in SQL. For example:

`customers JOIN orders JOIN order_items`

The second is the physical order selected by the database optimizer.

For inner joins, relational algebra allows many equivalent rearrangements because inner join is associative and, under the relevant conditions, commutative. PostgreSQL can therefore transform the written query into a different execution plan.

The SQL text describes the logical result. The execution plan describes how the database intends to obtain it.

The Python, C++, and Java implementations make this distinction visible by explicitly choosing lookup structures. The PostgreSQL implementation uses `EXPLAIN` to inspect the optimizer's physical strategy.

The presence of an index can change the cost of a particular access path without changing the logical result.

## INNER JOIN Versus LEFT JOIN

An `INNER JOIN` answers a question such as:

"Which customers have matching orders?"

A `LEFT JOIN` answers a different question:

"Show every customer, together with matching orders when they exist."

This difference becomes important for zero-activity entities.

The customer-preserving query in the implementations uses a left join so that a customer with no order is not removed from the result.

The aggregation:

`COUNT(o.order_id)`

is intentionally different from:

`COUNT(*)`

With a left join, an unmatched customer still produces a result row containing NULL values on the right side. `COUNT(o.order_id)` counts only actual orders, whereas `COUNT(*)` counts the preserved customer row.

## Predicate Placement

Predicate location can change the meaning of an outer join.

Consider a customer-preserving query:

`LEFT JOIN orders ON orders.customer_id = customers.customer_id`

If a condition such as `orders.status = 'DELIVERED'` is placed in the `WHERE` clause, unmatched rows have `NULL` for the order status and fail the condition.

The result can therefore behave like an inner join for that condition.

Placing the condition in the `ON` clause instead:

`LEFT JOIN orders ON orders.customer_id = customers.customer_id AND orders.status = 'DELIVERED'`

preserves the left-side customer while restricting which order rows qualify as matches.

This distinction is one of the most important practical rules for multi-table outer joins.

## Cardinality and Row Multiplication

The order-to-item relationship is one-to-many.

Suppose an order contains three products. After joining `orders` to `order_items`, that order appears in three rows.

If the query then joins those rows to products, each line remains a separate row.

This becomes especially important when counting entities.

A query that uses:

`COUNT(o.order_id)`

after joining orders to order items may count an order once for every line item.

When the desired metric is the number of distinct orders, the appropriate expression is:

`COUNT(DISTINCT o.order_id)`

The SQL implementation explicitly demonstrates this distinction in customer revenue reporting.

## Aggregation After Multi-Table JOINs

Revenue is naturally a line-level calculation:

`quantity * unit_price`

Customer revenue is then the aggregate of those line values across the customer's qualifying orders.

The conceptual sequence is:

`order_items -> calculate line value -> join order status -> join customer -> aggregate customer`

Changing the sequence carelessly can produce incorrect results.

For example, aggregating orders before reaching `order_items` would not provide the line-level quantities needed for revenue calculation.

The CTE example creates an intermediate `order_totals` relation. That relation has one row per order, which can then safely be joined to customers and regions for higher-level reporting.

## Many-to-Many Relationships

The product and order relationship is not represented by placing a single `product_id` column directly on `orders`.

An order can contain many products, and a product can occur in many orders.

The bridge table solves this:

`orders -> order_items -> products`

`order_items` also stores attributes belonging to the relationship itself, especially `quantity` and the transaction-specific `unit_price`.

This is a common reason why bridge tables are more than simple technical connectors. They often represent a meaningful business event.

## Python Implementation

The Python program uses `sqlite3`, which is part of the standard library, so the program does not require an external package.

The schema creates the five relational tables and enables foreign-key enforcement.

The `five_table_join()` function demonstrates the complete relationship path from sales region to product. The query selects attributes from all five tables and excludes cancelled orders.

The `left_join_preserves_unmatched_rows()` function focuses on a different relational question. It keeps customers even when their order count is zero.

The `avoid_accidental_inner_join()` demonstration deliberately contrasts a right-side condition in `WHERE` with the same condition in the `ON` clause. This makes the semantic effect of predicate placement executable rather than purely theoretical.

The CTE example first calculates order totals and then joins that derived relation to customers and regions. This represents a useful pattern when an intermediate aggregate has its own business meaning.

The query-plan example uses SQLite's `EXPLAIN QUERY PLAN`. It emphasizes that written JOIN order does not necessarily equal physical execution order.

The transaction example demonstrates foreign-key failure. An order item referencing a nonexistent order is rejected and the transaction is rolled back.

Parameterized SQL is used for user-controlled values. The example avoids string concatenation so that external input cannot become SQL syntax.

## JavaScript Implementation

The JavaScript implementation takes a different approach from the Python program. Instead of depending on a database package, it implements explicit relational operations over arrays.

The `innerJoin()` function models matching rows from two relations.

The `leftJoin()` function preserves unmatched left-side rows and demonstrates how an outer join differs from an inner join.

The data model remains relational, but JavaScript objects make each row explicit. This makes the relationship traversal visible:

`regions -> customers -> orders -> orderItems -> products`

The `groupBy()` function provides the foundation for post-join aggregation.

The many-to-many product analysis uses `Set` to count distinct orders. This is important because multiple line items from the same order can otherwise inflate an order count.

The asynchronous repository example models a common JavaScript application pattern. Database drivers are usually asynchronous, so a real service often performs relational retrieval through promises rather than synchronous array operations.

The implementation also validates foreign-key-like relationships before processing. JavaScript arrays do not automatically enforce relational integrity, so application-level validation is necessary when the data is not protected by an actual database.

## C++ Case Study

The C++ program models a reporting engine that must traverse the complete five-table relationship efficiently.

Instead of repeatedly scanning every table, it constructs hash-based lookup maps such as:

`customerById`

`regionById`

`productById`

It also builds an index from order identifiers to order-item collections.

This changes the implementation strategy from repeated nested scans toward indexed relationship traversal.

The case study therefore demonstrates an important distinction between the logical JOIN and an implementation strategy. SQL expresses relationships declaratively. A lower-level implementation must choose actual data structures to resolve those relationships.

The `fiveTableJoin()` method walks from orders to customers, regions, order items, and products. Invalid relationships are treated as structural errors rather than silently producing misleading reports.

The revenue calculation intentionally aggregates after reaching line-level data.

The C++ left-join implementation preserves every customer and assigns an order count of zero when no matching order exists.

The program uses `unordered_map` for key-based lookup and `set` where distinct order identifiers are required.

The resulting approach is substantially different from the SQL implementation. SQL delegates physical execution to the database optimizer, while this C++ case study explicitly controls the lookup structures.

## Java Implementation

The Java implementation represents the relational domain through Java 17 records.

`Region`, `Customer`, `Product`, `Order`, and `OrderItem` are immutable domain values. This is useful for reporting because the joined records should not be mutated while traversing relationships.

The `OrderStatus` enum restricts order state to recognized values rather than allowing arbitrary status strings throughout the application.

`JoinService` owns reporting behavior. It constructs maps for foreign-key lookups and groups order items by order.

The service separates three concerns:

- constructing a detailed multi-table report
- calculating delivered customer revenue
- preserving customers in a left-join-style report

`DataValidator` verifies relationship integrity before reporting. The database would normally enforce these rules through foreign keys, but an enterprise application can also validate imported or externally supplied data before processing it.

Java streams are used for grouping and sorting where they make the aggregation readable. Explicit loops remain useful for relationship traversal where failure handling and several dependent lookups are involved.

The implementation demonstrates how multi-table relational behavior can be represented through domain-oriented services instead of embedding every operation in one large method.

## SQL Data Model

The PostgreSQL implementation creates a dedicated schema so that the demonstration can be executed without polluting an existing default schema.

Foreign keys enforce the relationship graph:

`customers.region_id -> sales_regions.region_id`

`orders.customer_id -> customers.customer_id`

`order_items.order_id -> orders.order_id`

`order_items.product_id -> products.product_id`

Check constraints enforce positive quantities and prices and restrict order statuses to recognized values.

Indexes are created on foreign-key columns and frequently filtered order attributes. These indexes provide useful access paths for joins and filtering, although PostgreSQL may choose another strategy when its cost model determines that it is cheaper.

The SQL script inserts realistic data, including delivered, shipped, placed, and cancelled orders.

The queries then demonstrate:

- three-table joins
- five-table joins
- alternative written join orders
- customer-preserving left joins
- predicate placement for outer joins
- many-to-many aggregation
- CTE-based intermediate aggregation
- `COUNT(DISTINCT ...)`
- relationship-integrity validation
- query-plan inspection
- transactional foreign-key enforcement

## CTEs and Intermediate Relations

A common mistake in complex queries is attempting to calculate every business rule in one large SELECT expression.

A CTE can provide a named intermediate relation.

The `order_totals` CTE creates one row per order by joining orders to order items and calculating the total value.

The outer query then joins those order-level results to customers and regions.

This creates a useful boundary:

`order-level calculation -> customer-level relationship -> region-level reporting`

The CTE does not automatically guarantee better performance. Its main benefit in this example is expressing the relational stages clearly. PostgreSQL's optimizer can still make decisions about how the query executes.

## Common Multi-Table JOIN Errors

### Missing join predicates

A query such as:

`FROM customers CROSS JOIN orders`

produces combinations between the two relations unless constrained elsewhere.

For `N` customers and `M` orders, this can produce `N * M` rows.

A missing join condition is therefore not a cosmetic issue. It can completely change the cardinality of the result.

### Joining through the wrong key

A multi-table query should follow the actual relationship graph. Joining an order to a product directly when the relationship is represented by `order_items` bypasses the quantity and transaction-price information.

### Counting after one-to-many expansion

Joining orders to order items multiplies order rows. Entity counts therefore often require `COUNT(DISTINCT order_id)`.

### Filtering an outer join incorrectly

A right-side predicate in `WHERE` can eliminate NULL-extended rows and defeat the intended purpose of a `LEFT JOIN`.

### Selecting ambiguous column names

Columns such as `id`, `name`, and `status` are common in several tables. Table aliases make both the SQL and its meaning clearer:

`customers AS c`

`orders AS o`

`products AS p`

Qualified expressions such as `c.customer_name` also protect the query from ambiguity.

### Joining too many tables without defining the target grain

Before writing a large JOIN, identify what one result row represents.

Possible grains include:

- one row per customer
- one row per order
- one row per order item
- one row per product
- one row per customer and product
- one row per region

The correct JOIN and aggregation strategy depends on this grain.

## Performance Considerations

Multi-table JOIN performance depends on table cardinality, join selectivity, indexes, statistics, available memory, and the optimizer's chosen algorithm.

Foreign-key columns used frequently in joins are common candidates for indexes.

For this model, useful indexes include:

`customers(region_id)`

`orders(customer_id)`

`order_items(product_id)`

and a composite index on order status and date for queries that frequently restrict both attributes.

An index does not automatically make every query faster. Small tables can be cheaper to scan. An index also has storage and write-maintenance costs.

The PostgreSQL `EXPLAIN` query in the SQL file should be interpreted as an execution-plan diagnostic rather than as a guarantee that a particular join algorithm will always be selected.

Hash joins, nested-loop joins, and merge joins are physical execution strategies. They are implementation choices made by the database engine rather than different logical definitions of JOIN.

## Join Order and Optimizers

For inner joins, the optimizer can often reorder operations while preserving the logical result.

Suppose the logical query is:

`regions -> customers -> orders -> order_items -> products`

The physical execution might begin with a selective product or order condition, use an index to find matching rows, and only later access another table.

The SQL developer should therefore focus first on expressing correct relationships and predicates.

When performance is a concern, execution plans should be inspected rather than assuming that the textual order controls the physical order.

Outer joins introduce stronger semantic constraints because the preservation of unmatched rows matters. Consequently, not every reordering that is valid for inner joins is valid for outer joins.

## Practical Relationship Pattern

A reliable way to design a complex JOIN is to draw the relationship path before writing the SELECT.

For this project:

`Region`
`  |`
`  +-- Customer`
`       |`
`       +-- Order`
`            |`
`            +-- Order Item`
`                   |`
`                   +-- Product`

Every arrow represents a specific key relationship.

The resulting SQL should make those relationships explicit through `ON` predicates.

The number of tables is not itself the source of complexity. The real complexity comes from the combination of relationship cardinality, optional rows, filtering, aggregation, and the desired result grain.

## Transactions and Integrity

The SQL implementation places relationship integrity in the database through foreign keys.

An invalid order item cannot reference a nonexistent order.

This is stronger than relying only on application logic because every client of the database is subject to the same relational constraint.

The transaction example deliberately attempts an invalid foreign-key insert and rolls it back.

A production relational design should keep invariants that belong to the database at the database layer. Application validation can still provide early and user-friendly error handling, but it should not be the only protection for core relational integrity.

## Security Considerations

Multi-table queries often receive filters from web applications, APIs, reports, and administrative interfaces.

Parameterization is therefore essential.

The Python example passes the customer identifier as a SQL parameter rather than concatenating it into the query.

The same principle applies to PostgreSQL clients, Java database access, JavaScript database drivers, and other application layers.

Least-privilege database accounts are also important. A reporting service that only needs SELECT access should not automatically receive unrestricted schema modification privileges.

Complex JOINs can also become a denial-of-service concern when unbounded queries cause large intermediate relations. Application-level pagination, restrictive filters, appropriate indexes, and query timeouts can reduce this risk.

## Debugging Multi-Table JOINs

When a query returns unexpected rows, inspect the relationship path incrementally.

Start with the first relationship:

`customers JOIN orders`

Check the row count.

Add `order_items` and inspect how the count changes.

Add `products` and verify that every line has a matching product.

Only after the relationship path is correct should aggregation be introduced.

Useful diagnostic columns include primary keys and foreign keys. During debugging, selecting identifiers such as `customer_id`, `order_id`, `product_id`, and `region_id` makes unintended multiplication easier to detect.

A particularly useful test is comparing:

`COUNT(*)`

with:

`COUNT(DISTINCT order_id)`

If the values differ substantially after an order-to-item join, the difference is evidence of one-to-many expansion rather than necessarily a data error.

## Design Distinction

A multi-table JOIN is not simply a longer version of a two-table JOIN.

A three-table or five-table query must preserve a coherent relational path.

The central distinctions demonstrated by the implementations are:

| Concern | Technical meaning |
|---|---|
| Join relationship | Defines which rows can be combined |
| Join type | Determines whether unmatched rows survive |
| Join order | Describes logical composition while the optimizer may choose physical execution order |
| Cardinality | Determines how many result rows each source row can produce |
| Bridge table | Represents many-to-many relationships |
| Predicate placement | Can change outer-join semantics |
| Aggregation | Changes result grain and must account for row multiplication |
| Indexing | Provides possible efficient access paths |
| Constraints | Protect relationships and valid values |
| Query plan | Shows how the database intends to execute the logical query |

The implementations are intentionally complementary: the SQL version expresses relational logic declaratively, the Python version demonstrates executable database behavior, the JavaScript version exposes join operations directly, the C++ version emphasizes explicit indexed traversal, and the Java version models the same relationships through immutable enterprise domain types.
