# Mid-Level SQL Project: Sales Database and Revenue Analysis

## Project Scope

This project models a small but realistic sales operation using customers, products, orders, order items, inventory, order status, validation checks, and revenue reporting.

The central relationship is:

Customer → Orders → Order Items → Products → Revenue

The five implementations use the same business domain while applying different engineering approaches:

| File | Primary perspective |
|---|---|
| Python | In-memory sales workflow, validation, reporting, and file export |
| JavaScript | Event-driven sales processing and asynchronous report generation |
| C++17 | Repository-style sales engine with explicit state and inventory control |
| Java 17 | Enterprise domain model with records, immutable values, services, and policies |
| PostgreSQL | Relational persistence, constraints, triggers, transactions, views, and analytical SQL |

The project is deliberately focused on sales data rather than generic language syntax.

## Business Domain

The database represents four core business entities.

### Customers

A customer identifies the buyer and contains:

- Customer ID
- Name
- Email
- City
- Credit limit
- Creation timestamp

A customer can place many orders.

### Products

A product represents a saleable item and contains:

- Product ID
- Product name
- Category
- Unit price
- Available stock
- Active status

Products belong to categories such as Computers, Accessories, and Networking.

### Orders

An order records a customer purchase request.

Its state is one of:

- `PENDING`
- `PAID`
- `SHIPPED`
- `CANCELLED`

The implementations enforce meaningful state transitions rather than allowing arbitrary status changes.

The intended lifecycle is:

`PENDING → PAID → SHIPPED`

A pending or paid order may also become:

`PENDING → CANCELLED`

or:

`PAID → CANCELLED`

Shipped and cancelled orders are terminal states.

### Order Items

An order item connects an order to a product and stores:

- Product
- Quantity
- Unit price at the time of ordering

The stored unit price is important because current product pricing may change after an order is created. Historical order revenue should not depend on a later catalog price.

## Revenue Definition

Revenue analysis counts orders whose status is `PAID` or `SHIPPED`.

`PENDING` orders are not treated as completed sales.

`CANCELLED` orders do not contribute to revenue.

For an order:

`Order Revenue = Σ(quantity × historical unit price)`

For a customer:

`Customer Revenue = Σ(completed order revenue)`

For a product:

`Product Revenue = Σ(completed order item revenue)`

For a category:

`Category Revenue = Σ(completed product revenue in the category)`

This distinction prevents pending or cancelled transactions from inflating sales reports.

## Python Implementation

The Python implementation uses dataclasses to create explicit domain objects for customers, products, order items, and orders.

The `SalesDatabase` class acts as an in-memory repository. Dictionaries provide efficient lookup by numeric identifier.

Important mechanisms include:

- Customer and product validation
- Product stock validation
- Order creation
- Inventory reservation
- Order status transitions
- Inventory restoration after cancellation
- Revenue by category
- Revenue by customer
- Monthly revenue
- Top-product analysis
- Customer lifetime value
- CSV report generation
- JSON reporting
- Assertions for business-rule verification

The implementation validates all order lines before modifying stock. This prevents a partially processed order from reducing inventory when another line is invalid.

A temporary directory is used for report generation so the executable example does not require a fixed filesystem location.

The assertions test meaningful business behavior, including:

- Correct customer revenue
- Correct category revenue
- Correct top-product ordering
- Exclusion of cancelled orders
- Rejection of overselling
- Rejection of invalid order-state transitions

### Python Data Flow

`Customer/Product data`

→ `SalesDatabase`

→ `Order creation`

→ `Inventory reservation`

→ `Order status`

→ `Revenue analysis`

→ `CSV/JSON reporting`

## JavaScript Implementation

The JavaScript implementation takes an event-driven approach.

`SalesRepository` manages customers, products, and orders through `Map` collections. This provides direct identifier-based access without repeatedly scanning arrays.

`SalesEventBus` extends Node.js `EventEmitter`.

Important events include:

- `order.created`
- `order.statusChanged`

This separates order state changes from consumers that may react to those changes.

The implementation also uses asynchronous filesystem operations through Node.js `fs/promises`.

The generated CSV report is written asynchronously after the analytical operations complete.

Validation protects:

- Customer identifiers
- Customer email values
- Product prices
- Product stock
- Order identifiers
- Product existence
- Requested quantities
- Inventory availability
- Status transitions

The implementation explicitly checks that rejected orders do not change stock. This is an important transactional property even though the JavaScript version is intentionally an in-memory model rather than a database transaction system.

### JavaScript Event Flow

`createOrder()`

→ `order.created`

→ `changeStatus()`

→ `order.statusChanged`

→ reporting

The event mechanism makes the implementation suitable for applications where logging, notifications, metrics, or downstream processing may subscribe to sales events.

## C++17 Implementation

The C++17 implementation represents the sales system as a compact domain engine.

The `SalesEngine` class owns:

- Customers
- Products
- Orders

Hash maps provide efficient lookup by identifier.

A `std::map` is used during some analytical aggregation where deterministic key ordering is useful before revenue sorting is applied.

The implementation explicitly models order state through `enum class OrderStatus`.

Important operations include:

- Customer registration
- Product registration
- Order creation
- Inventory validation
- Inventory reservation
- State transitions
- Cancellation and stock restoration
- Completed-order filtering
- Category revenue
- Customer revenue
- Total revenue

The order creation algorithm performs validation before inventory mutation.

For `L` order lines, order creation is approximately `O(L)` with hash-map lookup expected to be constant time.

Revenue aggregation is proportional to the number of processed order lines.

The program also verifies that a rejected order does not change inventory.

C++ exception handling separates business failures represented by `SalesException` from unexpected standard exceptions.

## Java 17 Implementation

The Java implementation emphasizes enterprise-style domain modeling.

Java records are used for immutable value-oriented objects:

- `Customer`
- `Product`
- `OrderLine`

`Order` remains a class because its lifecycle state changes.

The `RevenuePolicy` interface separates the definition of completed revenue from the service that performs sales operations.

`CompletedSalesPolicy` defines `PAID` and `SHIPPED` as revenue-producing states.

This creates a clear separation:

`Domain data`

→ `Policy`

→ `SalesService`

→ `Revenue analysis`

The service explicitly handles:

- Customer registration
- Product registration
- Order creation
- Inventory reduction
- Order state transitions
- Cancellation
- Inventory restoration
- Revenue calculation
- Category aggregation
- Customer aggregation

`BigDecimal` is used instead of floating-point values for monetary calculations. This avoids the binary floating-point precision problems that can occur when financial values are represented with `double`.

Java's switch expressions make order-state transitions explicit.

Immutable records also reduce accidental modification of customer and product data. When stock changes, a new `Product` record is stored with the updated quantity.

## PostgreSQL Relational Model

The PostgreSQL implementation provides persistent relational modeling.

The main tables are:

| Table | Purpose |
|---|---|
| `customers` | Buyer accounts |
| `products` | Product catalog and inventory |
| `orders` | Sales transactions and lifecycle state |
| `order_items` | Products and quantities belonging to orders |
| `status_checks` | Automated validation results |
| `sales_audit` | Order status history |

The relational structure is:

`customers 1 ─── N orders`

`orders 1 ─── N order_items`

`products 1 ─── N order_items`

`orders 1 ─── N status_checks`

`orders 1 ─── N sales_audit`

Foreign keys enforce these relationships at the database layer.

## Database Integrity

The PostgreSQL script uses multiple levels of validation.

### Primary Keys

Identifiers are protected with primary keys.

This prevents duplicate entity identifiers.

### Foreign Keys

Orders cannot reference nonexistent customers.

Order items cannot reference nonexistent orders or products.

Status checks cannot reference nonexistent orders.

### Unique Constraints

Customer email addresses are unique.

A product name/category pair is unique.

An order cannot contain the same product twice because `(order_id, product_id)` is unique.

A status check name can occur only once for a particular order.

### Check Constraints

The database rejects:

- Negative stock
- Negative credit limits
- Non-positive product prices
- Non-positive quantities
- Invalid order states
- Empty customer names
- Invalid basic email structure

These rules remain active even if another application bypasses application-level validation.

## Triggers

Three important trigger mechanisms are included.

### Order Item Price Validation

The trigger checks that the referenced product exists and that the stored historical order price is valid.

### Order Status Audit

Every actual status change creates a record in `sales_audit`.

This provides an operational history of state changes.

### Status Transition Enforcement

The trigger prevents illegal transitions such as:

`SHIPPED → PAID`

or:

`CANCELLED → PENDING`

This puts an important workflow rule directly inside the database.

## Transactional Inventory Allocation

The `create_sales_order` PostgreSQL function demonstrates transactional sales creation.

It:

1. Validates the requested quantity.
2. Locks the product row with `FOR UPDATE`.
3. Checks available inventory.
4. Verifies the customer.
5. Creates the order.
6. Creates the order item.
7. Reduces product stock.

The row lock prevents concurrent transactions from allocating the same stock based on an outdated quantity.

The operation is intended to run inside a PostgreSQL transaction.

The sequence is:

`BEGIN`

→ lock product

→ validate stock

→ create order

→ create order item

→ reduce stock

→ `COMMIT`

If an error occurs before commit, PostgreSQL can roll the transaction back.

## Analytical Queries

The SQL script includes several types of analysis.

### Completed Order Revenue

The `completed_order_revenue` view calculates revenue for each completed order.

This creates a reusable reporting layer rather than repeating the same joins in every query.

### Customer Revenue Ranking

Customer revenue is aggregated and ranked with a window function.

This supports questions such as:

- Which customer generates the most revenue?
- How many completed orders does each customer have?
- What is the customer's revenue rank?

### Product Performance

Product analysis calculates:

- Units sold
- Revenue
- Product category

Products without completed sales remain visible because the query uses outer joins.

### Monthly Revenue

Revenue is grouped by month to expose sales trends.

The order date is truncated to the month before aggregation.

### Category Revenue Share

A common table expression calculates category revenue first.

A window function then calculates each category's percentage of total revenue.

This separates the aggregation step from the percentage calculation.

## Workflow Validation

The `status_checks` table models operational checks associated with an order.

Example checks include:

- Payment verification
- Inventory verification
- Fraud screening

Possible check states are:

- `PENDING`
- `PASSED`
- `FAILED`

This allows reporting to identify orders with incomplete or failed validation.

The order itself represents the business transaction state, while status checks represent supporting validation results. They are intentionally separate concepts.

## Revenue Eligibility

The project distinguishes between transaction state and analytical eligibility.

An order may exist in the system without contributing to completed revenue.

The rule is:

| Order state | Included in completed revenue |
|---|---:|
| `PENDING` | No |
| `PAID` | Yes |
| `SHIPPED` | Yes |
| `CANCELLED` | No |

This prevents operational records from being confused with recognized sales in analytical queries.

## Inventory and Cancellation

Inventory is reserved when an order is created.

If an order is cancelled, its quantities are restored.

For example:

`Stock = 40`

`Order quantity = 2`

`Stock after reservation = 38`

If the order is cancelled:

`Stock after restoration = 40`

The implementations treat this as a state-sensitive operation rather than simply deleting the order.

The PostgreSQL implementation provides the strongest transactional protection because row locks and transaction boundaries are handled by the database.

## Monetary Precision

Financial calculations use different mechanisms according to the implementation.

| Implementation | Monetary representation |
|---|---|
| Python | `Decimal` |
| JavaScript | Rounded numeric values |
| C++17 | Rounded `double` values |
| Java 17 | `BigDecimal` |
| PostgreSQL | `NUMERIC(14,2)` |

The PostgreSQL and Java implementations provide the strongest decimal-oriented representation for persistent financial values.

For production financial systems, decimal arithmetic should be preferred over binary floating-point calculations.

## Security and Data Integrity

The project focuses on application and database integrity rather than authentication.

Relevant controls include:

- Identifier validation
- Email validation
- Positive quantities
- Positive prices
- Non-negative stock
- Foreign-key enforcement
- Unique business keys
- Controlled status transitions
- Row locking during inventory allocation
- Transactional updates
- Historical unit prices
- Audit records
- No dynamic SQL construction from user-provided values

The PostgreSQL implementation uses parameterized function arguments rather than constructing SQL strings from input.

Customer email addresses and other business data should still be protected through appropriate database permissions and application access controls in a production deployment.

## Performance Considerations

The in-memory implementations use maps for identifier lookup.

This avoids repeatedly scanning complete customer or product collections.

The PostgreSQL implementation indexes:

- Customer/date order searches
- Order status/date reporting
- Product references in order items
- Product categories
- Status-check lookups by order

Indexes are not added to every column because each additional index introduces storage and write-maintenance cost.

Analytical queries aggregate order items, so the `order_items(product_id)` index is useful for product-focused reporting.

Date and status indexes support common operational reporting patterns.

## Edge Cases Covered

The implementations account for several failure conditions:

- Duplicate customer identifiers
- Duplicate product identifiers
- Duplicate order identifiers
- Missing customers
- Missing products
- Empty orders
- Zero or negative quantities
- Negative stock
- Invalid product prices
- Insufficient inventory
- Invalid status transitions
- Cancellation and stock restoration
- Cancelled orders excluded from revenue
- Invalid customer email values
- Invalid monetary values
- Orders with incomplete validation checks
- Concurrent inventory allocation in PostgreSQL

## Cross-Implementation Comparison

| Concern | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Entity validation | Explicit exceptions | Custom errors | Exceptions | Domain exceptions | Constraints |
| ID lookup | Dictionaries | Maps | Hash maps | Hash maps | Indexed keys |
| State model | Enum | Strings and transition map | `enum class` | Enum and service policy | Check + trigger |
| Revenue | `Decimal` | Rounded numbers | Rounded values | `BigDecimal` | `NUMERIC` |
| Inventory | In-memory | In-memory | Engine state | Service state | Transaction + row lock |
| Reporting | CSV + JSON | Async CSV | Console | Console | Views + SQL |
| Events | Direct operations | EventEmitter | Direct operations | Service methods | Triggers |
| Audit | Assertions/reporting | Events | State transitions | Explicit state | Audit table |

## File Execution

### Python

Run the Python file with Python 3:

`python sales_database.py`

The program prints revenue reports and creates a temporary CSV report.

### JavaScript

Run the JavaScript file with Node.js:

`node sales_database.js`

The program demonstrates event emission, validation, analytical output, and asynchronous CSV generation.

### C++17

Compile with a C++17-compatible compiler:

`g++ -std=c++17 -O2 sales_engine.cpp -o sales_engine`

Then run:

`./sales_engine`

On Windows with MinGW, the executable can be launched as `sales_engine.exe`.

### Java 17

Compile:

`javac SalesGovernanceDemo.java`

Run:

`java SalesGovernanceDemo`

### PostgreSQL

Execute the SQL script against a PostgreSQL database.

The script creates and recreates the `sales_demo` schema, loads sample data, defines functions, triggers, views, indexes, analytical queries, and transactional examples.

## Practical Workflow

A normal sales transaction follows this model:

`Customer`

→ selects `Product`

→ creates `Order`

→ validates `Order Items`

→ reserves `Inventory`

→ validates payment and other checks

→ moves order to `PAID`

→ moves order to `SHIPPED`

→ contributes to revenue reporting

A failed transaction follows a different path:

`Customer`

→ requests order

→ validation fails

→ order is rejected

→ inventory remains unchanged

A cancellation follows:

`Order`

→ inventory reserved

→ order cancelled

→ inventory restored

→ excluded from completed revenue

This separation between operational state, inventory state, validation results, and analytical revenue makes the model suitable for mid-level SQL practice and small sales-management systems.
