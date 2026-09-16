# SQL operators

SQL operators are expressions used to calculate values, compare values, combine conditions, test ranges and membership, negate conditions, and match text patterns. They are fundamental to `SELECT`, `WHERE`, `HAVING`, `JOIN`, `CASE`, subqueries, reporting queries, and application-level filtering.

This study uses three implementations:

- Python uses the standard-library `sqlite3` module to execute real SQL statements against an in-memory relational database.
- JavaScript uses an in-memory employee dataset to demonstrate the application-side meaning of SQL conditions, query construction, parameter binding concepts, and pattern matching.
- C++ develops an industry-style employee analytics search service that models filtering, validation, SQL generation, NULL handling, aggregation, security, and performance considerations.

The central operator families covered are arithmetic, comparison, logical, `BETWEEN`, `IN`, `NOT`, and `LIKE`. Closely related constructs such as `IS NULL`, `EXISTS`, `CASE`, `COALESCE`, and `HAVING` are included where they clarify the practical use of the requested operators.

## Topic introduction

An SQL expression produces a value. An operator defines how one or more expressions are combined or tested.

For example, the expression `salary * 1.10` calculates a value, while `salary >= 90000` produces a condition that can be used to select rows.

A complete filtering expression may combine several operators:

`salary BETWEEN 85000 AND 120000 AND city IN ('Delhi', 'Lucknow') AND active = 1`

This expression contains:

- `BETWEEN` for an inclusive salary range
- `AND` for combining conditions
- `IN` for membership
- `=` for comparison

SQL operators therefore form the basic vocabulary for expressing business rules inside database queries.

## Fundamental terminology

### Operand

An operand is a value or expression on which an operator acts.

In `salary + bonus`, both `salary` and `bonus` are operands.

### Operator

An operator specifies an operation.

Examples include:

- `+`
- `-`
- `*`
- `/`
- `=`
- `>`
- `AND`
- `OR`
- `BETWEEN`
- `IN`
- `LIKE`

### Expression

An expression is a combination of values, columns, functions, and operators that produces a result.

Examples:

`salary * 1.10`

`salary >= 90000`

`city IN ('Delhi', 'Pune')`

`salary > 90000 AND active = 1`

### Predicate

A predicate is an expression used as a condition, commonly in `WHERE`, `HAVING`, and `JOIN` conditions.

Examples:

`salary > 90000`

`city = 'Delhi'`

`salary BETWEEN 80000 AND 100000`

`employee_name LIKE 'A%'`

### Literal

A literal is a value written directly in SQL.

Examples include:

`90000`

`'Delhi'`

`1`

`3.14`

### NULL

`NULL` represents a missing, unknown, or unavailable value. It is not equivalent to zero, an empty string, or `FALSE`.

SQL requires special operators for testing NULL:

`IS NULL`

`IS NOT NULL`

## Arithmetic operators

Arithmetic operators calculate numeric values.

| Operator | Meaning | Example |
|---|---|---|
| `+` | Addition | `salary + bonus` |
| `-` | Subtraction | `salary - deduction` |
| `*` | Multiplication | `salary * 1.10` |
| `/` | Division | `salary / 12` |
| `%` | Remainder in supported dialects such as SQLite | `age % 2` |

Arithmetic expressions are useful in calculated columns, financial analysis, ratios, metrics, reporting, and projections.

For example:

`salary * 1.10`

calculates a salary after a hypothetical ten-percent increase.

A more realistic compensation calculation is:

`salary + COALESCE(bonus, 0)`

The Python implementation executes these calculations against the employee table.

### Arithmetic and filtering

Arithmetic can also appear inside a condition.

For example:

`salary * 1.10 > 100000`

This does not change the stored salary. It calculates a value and compares that calculated value with `100000`.

### Arithmetic with NULL

If `bonus` is `NULL`, an expression such as:

`salary + bonus`

normally evaluates to `NULL`.

If the application policy treats a missing bonus as zero, the query can explicitly state that rule:

`salary + COALESCE(bonus, 0)`

This is preferable to silently assuming that missing data is numerically equivalent to zero.

## Comparison operators

Comparison operators test relationships between values.

| Operator | Meaning |
|---|---|
| `=` | Equal |
| `<>` | Not equal |
| `!=` | Not equal in dialects that support it |
| `>` | Greater than |
| `<` | Less than |
| `>=` | Greater than or equal |
| `<=` | Less than or equal |

Examples:

`salary = 100000`

`salary <> 100000`

`salary > 100000`

`salary >= 100000`

`age < 40`

`age <= 40`

Comparison predicates are frequently used in `WHERE` clauses.

For example:

`SELECT employee_name, salary FROM employees WHERE salary > 100000`

selects employees whose salary is greater than `100000`.

### Equality in SQL and programming languages

SQL normally uses `=` for equality.

JavaScript uses `===` for strict equality.

C++ uses `==`.

This difference is important when translating business logic between database queries and application code.

## Logical operators

Logical operators combine or negate conditions.

### AND

`AND` requires all combined conditions to evaluate to `TRUE`.

Example:

`salary > 90000 AND age < 40`

An employee must satisfy both conditions.

### OR

`OR` requires at least one condition to be `TRUE`.

Example:

`city = 'Delhi' OR city = 'Lucknow'`

### NOT

`NOT` negates a condition.

Example:

`NOT (active = 1)`

can be used to identify inactive records.

### Combining logical operators

Real queries commonly combine all three:

`(city = 'Delhi' OR city = 'Lucknow') AND salary >= 90000`

The parentheses make the intended grouping explicit.

## Operator precedence

SQL expressions have precedence rules that determine how expressions are grouped when parentheses are absent.

A useful simplified model is:

1. arithmetic expressions
2. comparison expressions
3. `NOT`
4. `AND`
5. `OR`

The exact rules depend on the SQL dialect and operator family, so explicit parentheses are preferable when the business rule depends on grouping.

Consider:

`city = 'Delhi' OR city = 'Lucknow' AND salary >= 90000`

This is commonly interpreted as:

`city = 'Delhi' OR (city = 'Lucknow' AND salary >= 90000)`

It does not mean:

`(city = 'Delhi' OR city = 'Lucknow') AND salary >= 90000`

The second meaning should be written with parentheses.

The Python and C++ implementations deliberately demonstrate both forms.

## BETWEEN

`BETWEEN` tests whether a value falls inside an inclusive range.

Syntax:

`value BETWEEN lower AND upper`

For example:

`salary BETWEEN 80000 AND 100000`

is conceptually equivalent to:

`salary >= 80000 AND salary <= 100000`

The lower and upper boundaries are included.

Therefore:

`salary BETWEEN 80000 AND 100000`

matches a salary of exactly `80000` and exactly `100000`.

### NOT BETWEEN

`NOT BETWEEN` tests values outside the inclusive range.

Example:

`age NOT BETWEEN 30 AND 40`

selects values below `30` or above `40`, subject to SQL NULL semantics.

### BETWEEN and dates

`BETWEEN` is also used with dates and timestamps, but timestamp boundaries require careful design.

A condition such as:

`timestamp BETWEEN '2026-01-01' AND '2026-01-31'`

can be problematic when the timestamp contains a time component, because the upper boundary may represent midnight at the beginning of the final date.

A half-open interval is often clearer:

`timestamp >= '2026-01-01' AND timestamp < '2026-02-01'`

The correct implementation depends on the database, timestamp type, and application requirements.

## IN

`IN` tests membership in a collection of values.

Example:

`city IN ('Delhi', 'Lucknow', 'Mumbai')`

is conceptually similar to:

`city = 'Delhi' OR city = 'Lucknow' OR city = 'Mumbai'`

`IN` is usually more readable when several possible values are involved.

### NOT IN

`NOT IN` tests non-membership.

Example:

`department_id NOT IN (2, 3)`

selects rows whose department is not one of those values, subject to SQL NULL semantics.

### IN with subqueries

`IN` can use the result of another query.

The Python implementation demonstrates the pattern:

`department_id IN (SELECT department_id FROM departments WHERE ...)`

This is useful when membership depends on another table.

### Empty IN lists

Application code should handle empty collections deliberately.

An application receiving an empty list of cities needs a defined policy. It might mean:

- match no rows
- do not apply the city filter
- reject the request as invalid

Generating `IN ()` blindly is not portable across SQL dialects.

## NOT

`NOT` reverses a logical condition.

Examples:

`NOT (salary > 100000)`

`NOT (age BETWEEN 30 AND 40)`

`NOT (city IN ('Delhi', 'Mumbai'))`

`NOT` should not be confused with inequality in every situation. In particular, SQL's NULL behavior means that negating a condition involving NULL does not necessarily produce the intuitive opposite of a Boolean expression.

## LIKE

`LIKE` performs pattern matching for character data.

The two most important wildcard characters are:

| Wildcard | Meaning |
|---|---|
| `%` | Zero or more characters |
| `_` | Exactly one character |

Examples:

`employee_name LIKE 'A%'`

matches names beginning with `A`.

`employee_name LIKE '%a'`

matches values ending in `a`.

`employee_name LIKE '%an%'`

matches values containing `an`.

`employee_name LIKE '_a%'`

requires the second character to be `a`.

### LIKE versus equality

`=` compares values.

`LIKE` interprets wildcard characters as pattern syntax.

For example:

`name = 'A%'`

looks for the literal value `A%`.

`name LIKE 'A%'`

uses `%` as a wildcard and therefore matches values beginning with `A`.

### LIKE and case sensitivity

LIKE behavior is database-specific.

Collations, configuration, database engine, locale, and character set can affect matching behavior.

The Python implementation uses SQLite, while the JavaScript and C++ implementations provide educational pattern matching to make the wildcard behavior visible.

Production systems should verify the exact behavior of the selected database.

### LIKE and indexes

A pattern such as:

`name LIKE 'A%'`

has a known prefix and may be eligible for index-based optimization depending on the database and collation.

A pattern such as:

`name LIKE '%Engineer%'`

starts with a wildcard and is generally much harder for an ordinary B-tree index to optimize.

This distinction matters for large tables.

## NULL and three-valued logic

One of the most important SQL distinctions is that SQL conditions do not operate only with `TRUE` and `FALSE`.

They can produce:

- `TRUE`
- `FALSE`
- `UNKNOWN`

`NULL` usually represents an unknown or missing value.

Consider:

`bonus = NULL`

This is not the correct way to test for missing bonus data.

The correct expression is:

`bonus IS NULL`

Similarly:

`bonus IS NOT NULL`

tests whether the value is known to be non-NULL.

### Why `= NULL` is incorrect

Suppose `bonus` is NULL.

The expression:

`bonus = NULL`

does not evaluate to `TRUE`.

SQL treats NULL as unknown, so ordinary comparison operators do not provide a normal equality test for it.

### WHERE and UNKNOWN

A `WHERE` clause keeps rows where the condition evaluates to `TRUE`.

Rows producing `FALSE` or `UNKNOWN` are not returned.

This is why NULL can produce results that differ from ordinary two-valued Boolean logic.

### NOT and NULL

Consider a NULL value and:

`NOT (bonus > 1000)`

The expression `bonus > 1000` can be `UNKNOWN`. Negating `UNKNOWN` does not turn it into `TRUE`.

This is an important reason to design NULL handling explicitly.

## CASE with operators

`CASE` is not an operator from the requested list, but it is closely related because it allows operator-based conditions to produce classifications.

Example:

`CASE WHEN salary >= 120000 THEN 'High' WHEN salary >= 90000 THEN 'Medium' ELSE 'Entry' END`

The Python implementation uses CASE to create salary and performance bands.

This pattern is common in reporting and analytics.

## COALESCE and operator expressions

`COALESCE` is useful when arithmetic interacts with missing values.

For example:

`salary + COALESCE(bonus, 0)`

means that a missing bonus is treated as zero for this calculation.

The important design question is whether that is actually the desired business rule.

A missing value and a zero value can have different meanings.

For example:

- `bonus = 0` may mean an employee was explicitly assigned no bonus.
- `bonus IS NULL` may mean the bonus has not yet been recorded.

Replacing NULL with zero should therefore be intentional.

## Operators with subqueries

Operators can use values produced by other queries.

For example:

`salary > (SELECT AVG(salary) FROM employees)`

compares every employee's salary with the overall average.

`IN` can also consume a subquery:

`department_id IN (SELECT department_id FROM departments WHERE department_name LIKE '%Engineering%')`

This allows the filter to depend on data in another table.

## EXISTS and NOT EXISTS

`EXISTS` is closely related to membership testing and is important in advanced SQL.

Example:

`EXISTS (SELECT 1 FROM employees WHERE ...)`

tests whether the subquery produces at least one row.

`NOT EXISTS` tests whether no matching row exists.

For anti-join style logic, `NOT EXISTS` can be preferable to `NOT IN` because NULL behavior can make `NOT IN` surprising when a subquery produces NULL values.

## Aggregation and HAVING

Operators appear at different stages of query processing.

`WHERE` filters rows before grouping.

`GROUP BY` forms groups.

Aggregate functions calculate values for those groups.

`HAVING` filters the resulting groups.

For example:

`HAVING AVG(salary) BETWEEN 80000 AND 120000`

uses `BETWEEN` after aggregation.

The Python implementation demonstrates this with departmental salary statistics.

## Python implementation

The Python program uses only the standard library and creates an in-memory SQLite database.

The database contains:

- departments
- employees
- salary
- bonus
- age
- city
- job title
- performance score
- email
- active status

This structure makes the operator examples realistic instead of reducing them to isolated expressions.

### Arithmetic

The Python implementation demonstrates:

`salary + COALESCE(bonus, 0)`

`salary * 12`

`salary / 12`

`salary * 0.10`

`age + 1`

These examples show that arithmetic operators can produce calculated columns.

### Comparison

The program executes real SQL queries using:

`>`

`<`

`>=`

`<=`

`=`

`<>`

### Logical filtering

The program demonstrates:

`AND`

`OR`

`NOT`

It also shows why parentheses are important when `AND` and `OR` appear together.

### BETWEEN

The Python implementation executes inclusive salary and age ranges.

It explicitly demonstrates that the boundaries are included.

### IN

The program uses `IN` with literal lists and a subquery.

This demonstrates both direct membership and data-driven membership.

### LIKE

The program executes patterns using `%` and `_`.

It also explains the performance difference between prefix searches and leading-wildcard searches.

### NULL

The program uses:

`IS NULL`

`IS NOT NULL`

and demonstrates `COALESCE`.

This makes SQL's NULL semantics directly observable.

### Parameterized queries

The Python code uses `?` placeholders:

`WHERE city = ? AND salary >= ?`

and passes values separately to `sqlite3`.

This is a critical security practice.

The SQL statement and data are kept separate rather than combining user input into SQL syntax.

### Dynamic filters

The Python implementation also builds a dynamic WHERE clause from trusted application-level conditions while keeping user values as parameters.

This is an important pattern for search interfaces.

## JavaScript implementation

The JavaScript file complements the Python implementation rather than simply reproducing database execution.

It focuses on the application layer.

The dataset is represented as JavaScript objects, allowing SQL concepts to be compared with JavaScript expressions.

### Comparison syntax

SQL:

`salary = 100000`

JavaScript:

`salary === 100000`

C++:

`salary == 100000`

The languages use different syntax even when the business rule is the same.

### Logical syntax

SQL:

`salary > 90000 AND active = 1`

JavaScript:

`salary > 90000 && active === true`

C++:

`salary > 90000 && active`

The JavaScript implementation demonstrates the application-side equivalent of SQL logical expressions.

### BETWEEN

JavaScript does not have a built-in SQL-style `BETWEEN` operator.

The file implements:

`value >= lower && value <= upper`

through a reusable `between()` function.

This corresponds to the inclusive SQL meaning of `BETWEEN`.

### IN

JavaScript provides collection methods such as `includes()` and `Set.has()`.

For repeated membership testing, the implementation demonstrates `Set.has()`.

This is a useful application-level distinction from SQL's `IN`.

### LIKE

JavaScript does not have SQL's `LIKE` operator.

The implementation converts the common SQL wildcard rules into a regular expression:

- `%` becomes zero or more characters.
- `_` becomes exactly one character.

This demonstrates the underlying concept of pattern matching.

It is an educational implementation and should not be considered a complete implementation of every SQL dialect's LIKE semantics, including all escaping, collation, locale, and database-specific behavior.

### Parameterized SQL construction

The JavaScript implementation generates SQL such as:

`WHERE salary >= ? AND city IN (?, ?)`

and keeps the values in a separate parameter array.

This reflects how application code should interact with a database driver that supports parameter binding.

Simply placing `?` into a string is not enough by itself. The actual database library must bind the parameters separately.

### Dynamic filtering

The JavaScript implementation accepts a filter object containing:

- minimum salary
- maximum salary
- active-only status
- name pattern
- allowed cities

It converts those rules into parameterized SQL structure while separately evaluating the same business rules against the local dataset.

This makes the distinction between SQL query construction and application-side business logic explicit.

## C++ case study

The C++ program models an employee analytics and search service.

The case study contains:

- an employee data model
- search criteria
- range filtering
- membership filtering
- pattern matching
- NULL-like optional values
- SQL query generation
- validation
- aggregation
- security considerations
- performance discussion

The design uses standard C++17 library components and does not require an external SQL library.

### Employee model

The `Employee` structure contains:

- ID
- name
- department
- salary
- optional bonus
- age
- city
- title
- optional performance score
- active status

`std::optional` is used to represent potentially missing values.

This corresponds conceptually to SQL NULL.

### Search criteria

The `SearchCriteria` structure represents application-level filtering requirements.

It contains optional salary boundaries, a city set, a LIKE pattern, a performance threshold, an active-only flag, and an exclusion rule.

This models how a real API or application service might receive search requirements before converting them into a database query.

### Query construction

The C++ implementation produces parameterized SQL containing expressions such as:

`salary >= ?`

`salary <= ?`

`city IN (?, ?, ?)`

`employee_name LIKE ?`

`performance_score >= ?`

`active = ?`

`NOT (department = ?)`

The SQL syntax is kept separate from the parameter values.

This separation is central to secure database programming.

### Application-level evaluation

The `matchesCriteria()` function evaluates the same business rules against the in-memory employee collection.

It demonstrates:

- comparisons
- AND
- OR
- NOT
- inclusive ranges
- membership
- LIKE
- missing values

The application-side implementation is not a replacement for a database query engine. It is a case-study representation of the logic an application might use before or after database retrieval.

### LIKE implementation

The C++ program implements a small recursive matcher supporting:

- `%`
- `_`
- case-insensitive character comparison for the demonstration

This makes wildcard semantics visible without external dependencies.

The implementation is intentionally educational. A production system should use the database engine's optimized pattern-matching facilities or a carefully engineered library rather than treating this recursive matcher as a general SQL implementation.

### NULL representation

C++ uses:

`std::optional<double>`

for the optional bonus and performance fields.

For example:

`!employee.bonus.has_value()`

corresponds conceptually to:

`bonus IS NULL`

and:

`employee.bonus.has_value()`

corresponds conceptually to:

`bonus IS NOT NULL`

The exact semantics are different because C++ optional values and SQL NULL belong to different type systems, but the representation is useful for modeling missing database values.

### Aggregation

The case study groups active employees by department and calculates:

- employee count
- total salary
- average salary

It then applies an inclusive range condition to the average salary.

This corresponds conceptually to a SQL query using:

`GROUP BY department`

and:

`HAVING AVG(salary) BETWEEN 80000 AND 120000`

## Important distinctions between the three implementations

| Concept | SQL | Python | JavaScript | C++ |
|---|---|---|---|---|
| Equality | `=` | SQL `=` through SQLite | `===` | `==` |
| Inequality | `<>` / `!=` | SQL syntax | `!==` | `!=` |
| AND | `AND` | SQL syntax | `&&` | `&&` |
| OR | `OR` | SQL syntax | `||` | `||` |
| NOT | `NOT` | SQL syntax | `!` | `!` |
| BETWEEN | `BETWEEN` | SQL syntax | custom function | custom function |
| IN | `IN` | SQL syntax | `Set.has()` / `includes()` | set lookup |
| LIKE | `LIKE` | SQL syntax | custom matcher | custom matcher |
| NULL test | `IS NULL` | SQL syntax | `=== null` for local model | `std::optional` |
| Missing-value fallback | `COALESCE` | `COALESCE` in SQL | `??` | `value_or()` |
| Parameter binding | Database API | `sqlite3` parameters | database-driver feature | database-driver feature |

These are conceptual correspondences, not interchangeable syntax.

## Edge cases

### Range boundaries

`BETWEEN` is inclusive.

`value BETWEEN 10 AND 20`

includes both `10` and `20`.

### NULL comparisons

`column = NULL` is not a NULL test.

Use:

`column IS NULL`

### NOT IN and NULL

Consider:

`value NOT IN (1, 2, NULL)`

SQL's three-valued logic can cause the result to become `UNKNOWN`.

This is particularly important when `NOT IN` uses a subquery whose result may contain NULL.

`NOT EXISTS` is often a safer design for anti-join conditions.

### Empty IN collections

Application code should define what an empty collection means before constructing an SQL `IN` expression.

### LIKE wildcards

`%` can match zero or more characters.

`_` matches exactly one character.

If literal wildcard characters must be searched for, the database-specific escape mechanism must be used correctly.

### Floating-point equality

Exact equality with calculated floating-point values can be unreliable.

For example, repeatedly calculating percentages or ratios using binary floating-point representations may produce tiny differences.

Financial applications should use appropriate fixed-precision numeric types and database types.

### Division by zero

Division-by-zero behavior is database-specific.

Production queries should prevent invalid denominators rather than relying on a particular database's error or NULL behavior.

### Date and timestamp ranges

Inclusive `BETWEEN` conditions require careful handling when the column includes a time component.

Half-open intervals are often clearer for timestamp ranges.

## Common mistakes

### Using `=` instead of `LIKE`

Incorrect when wildcard matching is required:

`name = 'A%'`

Pattern matching:

`name LIKE 'A%'`

### Using `= NULL`

Incorrect:

`bonus = NULL`

Correct:

`bonus IS NULL`

### Forgetting parentheses

Ambiguous:

`city = 'Delhi' OR city = 'Lucknow' AND salary > 90000`

Clear:

`(city = 'Delhi' OR city = 'Lucknow') AND salary > 90000`

### Assuming BETWEEN is exclusive

`BETWEEN` includes both endpoints.

### Treating NOT IN as always equivalent to repeated inequality

NULL can change the result.

### Concatenating user input into SQL

Unsafe application design can turn data into SQL syntax.

The safe pattern is parameter binding.

### Assuming LIKE is always case-sensitive or always case-insensitive

Behavior depends on database configuration and collation.

### Assuming an index will always be used

The database optimizer decides how to execute a query.

Indexes, statistics, cardinality, selectivity, query structure, and database-specific rules all affect the execution plan.

## Parameterized SQL

Parameterized SQL separates query structure from values.

Conceptually:

`SELECT employee_name FROM employees WHERE city = ? AND salary >= ?`

with parameters:

`['Delhi', 90000]`

The database driver binds the values independently.

This protects against SQL injection when used correctly.

### Why string concatenation is dangerous

An unsafe pattern constructs SQL by inserting raw user input into the statement.

For example, an application that directly inserts a user-provided city into:

`WHERE city = '...'`

can allow input containing SQL syntax to alter the query.

The correct approach is to use a parameterized statement supported by the database driver.

### Dynamic identifiers

Parameters normally represent values, not arbitrary SQL identifiers.

For example, a database driver generally cannot safely treat:

`ORDER BY ?`

as a dynamic column-name mechanism.

If an application allows users to select a sort field, it should map approved application-level names to trusted SQL identifiers.

## Performance considerations

Operator syntax does not determine performance by itself.

The database engine evaluates the query using an optimizer and execution plan.

### Indexes

Indexes can improve filtering for appropriate columns.

For example, an index on `salary` can help queries that frequently search salary ranges.

The Python implementation creates a salary index and displays SQLite's query plan.

### Index trade-offs

Indexes have costs:

- storage consumption
- additional work during inserts
- additional work during updates
- additional work during deletes
- maintenance complexity

Indexing every column is not a good general strategy.

### Selectivity

A selective predicate eliminates a large proportion of possible rows.

For example, filtering a large table for a rare salary range can be more selective than filtering on a column where almost every row has the same value.

### Composite indexes

When several columns are frequently filtered together, a composite index can be useful.

The order of columns in a composite index matters.

The correct order depends on the database workload and query patterns.

### LIKE performance

A prefix pattern such as:

`name LIKE 'A%'`

can be more index-friendly than:

`name LIKE '%A%'`

because the second expression has no fixed starting prefix.

### Application-side membership

The JavaScript implementation demonstrates `Set.has()` for collection membership.

The C++ implementation uses `std::unordered_set`.

These provide efficient average membership lookup for application-level collections.

This should not be confused with database `IN` performance, which depends on the database optimizer, indexes, query plan, data distribution, and number of values.

## Security considerations

SQL operators are not themselves a security vulnerability.

The primary risk comes from unsafe query construction.

Important practices include:

- use parameterized queries
- validate user input
- use allowlists for dynamic SQL identifiers
- avoid raw string interpolation for values
- use least-privilege database accounts
- avoid exposing sensitive database errors
- avoid logging credentials or secrets
- consider the performance implications of user-controlled LIKE patterns
- apply pagination to large result sets
- validate filter ranges and collection sizes

A search endpoint that accepts arbitrary LIKE patterns can also become a performance concern even when it is protected against injection.

Security therefore includes both correctness and resource-management considerations.

## Implementation considerations

A production SQL filtering service should distinguish between:

- user input
- validated application data
- SQL syntax
- bound SQL parameters
- database execution
- returned domain objects

A useful architectural boundary is:

`request -> validation -> filter model -> parameterized query -> database -> domain results`

This separation makes the system easier to test and reduces the risk that untrusted data becomes executable SQL syntax.

## Real-world applications

SQL operators appear throughout practical systems.

### Financial systems

Arithmetic operators are used for:

- revenue calculations
- profit calculations
- tax calculations
- interest calculations
- portfolio metrics
- ratios

Comparison and range operators support:

- risk thresholds
- transaction limits
- eligibility rules
- date ranges

### Human resources

Operators support:

- salary bands
- age ranges
- department filters
- active employee searches
- performance classifications

### E-commerce

Operators are used for:

- price ranges
- category membership
- stock thresholds
- product searches
- customer segmentation

### Security systems

Operators support:

- risk thresholds
- event filtering
- IP or category membership
- time-window analysis
- rule-based detection

### Analytics

Operators are fundamental to:

- segmentation
- KPI calculation
- report filtering
- cohort selection
- anomaly detection
- conditional aggregation

### Web applications

Application code often translates user filters into SQL predicates.

A product search page might produce conditions involving:

`BETWEEN`

`IN`

`LIKE`

`AND`

`OR`

and comparison operators.

## Conceptual query-processing perspective

A simplified SQL query can be viewed as a sequence of logical operations:

`FROM`

identifies the source rows.

`WHERE`

filters rows using predicates.

`GROUP BY`

forms groups.

Aggregate functions calculate group-level values.

`HAVING`

filters groups.

`SELECT`

defines the resulting expressions and columns.

`ORDER BY`

sorts the result.

`LIMIT`

restricts the final number of returned rows.

Operators participate throughout these stages.

For example:

`WHERE salary BETWEEN 80000 AND 100000`

filters rows.

`HAVING AVG(salary) >= 90000`

filters groups.

`ORDER BY salary * 1.10 DESC`

uses an arithmetic expression to determine ordering.

## Best practices

Use explicit parentheses for complex logical expressions.

Use `IS NULL` and `IS NOT NULL` for NULL tests.

Use parameterized queries for values supplied by applications.

Use `BETWEEN` when an inclusive range clearly expresses the requirement.

Use `IN` when testing membership in a defined collection.

Use `LIKE` for pattern matching rather than trying to reproduce wildcard behavior with multiple equality expressions.

Define behavior for empty filter collections.

Treat timestamp ranges carefully.

Choose numeric types appropriate to the domain.

Do not assume identical SQL semantics across database engines.

Measure query performance using the actual database engine and representative data.

Keep business rules and SQL construction clearly separated in application architecture.

## Limitations

The Python implementation uses SQLite, so its behavior represents SQLite rather than every SQL dialect.

Different databases can differ in:

- operator precedence details
- implicit type conversion
- string comparison
- collation
- NULL behavior in specific constructs
- date and time handling
- arithmetic behavior
- index optimization
- LIKE behavior
- query-planning strategies

The JavaScript implementation does not execute SQL against a real database. Its purpose is to demonstrate the application-side representation of SQL conditions and safe query construction.

The C++ implementation is a self-contained case study rather than a database engine. Its recursive LIKE matcher demonstrates wildcard semantics but does not implement every feature of production SQL pattern matching.

These limitations are intentional because the three implementations focus on different layers of the same technical subject.

## Files and execution

The Python implementation requires Python 3 with the standard `sqlite3` module.

The JavaScript implementation requires a modern Node.js runtime.

The C++ implementation requires a compiler supporting C++17 or later.

The three programs use only standard or built-in facilities and do not require external packages for their core demonstrations.

## Key operator reference

| Operator | Purpose | Example |
|---|---|---|
| `+` | Addition | `salary + bonus` |
| `-` | Subtraction | `salary - deduction` |
| `*` | Multiplication | `salary * 1.10` |
| `/` | Division | `salary / 12` |
| `%` | Remainder | `age % 2` |
| `=` | Equality | `city = 'Delhi'` |
| `<>` | Inequality | `salary <> 100000` |
| `!=` | Inequality where supported | `salary != 100000` |
| `>` | Greater than | `salary > 90000` |
| `<` | Less than | `age < 40` |
| `>=` | Greater/equal | `salary >= 90000` |
| `<=` | Less/equal | `age <= 40` |
| `AND` | All conditions | `salary > 80000 AND active = 1` |
| `OR` | At least one condition | `city = 'Delhi' OR city = 'Pune'` |
| `NOT` | Negation | `NOT active = 1` |
| `BETWEEN` | Inclusive range | `salary BETWEEN 80000 AND 100000` |
| `NOT BETWEEN` | Outside inclusive range | `age NOT BETWEEN 30 AND 40` |
| `IN` | Membership | `city IN ('Delhi', 'Pune')` |
| `NOT IN` | Non-membership | `city NOT IN ('Delhi', 'Pune')` |
| `LIKE` | Pattern matching | `name LIKE 'A%'` |
| `IS NULL` | Missing/unknown value | `bonus IS NULL` |
| `IS NOT NULL` | Non-NULL value | `bonus IS NOT NULL` |

## Core distinctions

Arithmetic operators calculate values.

Comparison operators test relationships.

Logical operators combine or negate conditions.

`BETWEEN` expresses an inclusive range.

`IN` expresses membership.

`NOT` negates a condition.

`LIKE` expresses text-pattern matching.

`IS NULL` and `IS NOT NULL` handle missing values.

Parameterized queries separate SQL structure from external values.

The Python implementation demonstrates these concepts through actual SQL execution, the JavaScript implementation connects them to application-level logic and query construction, and the C++ implementation develops them into a complete rule-based analytics case study.
