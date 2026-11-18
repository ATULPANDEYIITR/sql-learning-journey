# Index Fundamentals: Why Indexes Exist, B-Tree Concepts, and Index Lookup

## 1. Introduction

A database index is a data structure that helps a database locate records without examining every row in a table.

Without an appropriate index, a database may perform a sequential scan. It reads table records and checks whether each record satisfies the query condition.

An index provides an alternative access path. It maintains information about indexed values and their corresponding table locations or row identifiers.

Indexes are particularly useful when:

- A table contains a large number of records.
- Queries frequently search using specific columns.
- Applications retrieve records using unique identifiers.
- Queries retrieve values within a range.
- Applications repeatedly sort or filter records.
- Several queries use the same search conditions.

An index does not automatically make every query faster. Maintaining an index consumes storage and adds work to operations that insert, update, or delete records.

The central engineering decision is to determine whether the improvement in data retrieval justifies the additional storage and maintenance cost.

## 2. How Database Tables Store Records

A relational database stores table records in data pages.

A table containing employee information might have the following structure:

| employee_id | employee_name | department | salary |
|---:|---|---|---:|
| 101 | Employee A | Engineering | 85000 |
| 102 | Employee B | Security | 92000 |
| 103 | Employee C | Research | 78000 |
| 104 | Employee D | Finance | 110000 |
| 105 | Employee E | Operations | 72000 |

Consider the query:

`SELECT * FROM employees WHERE employee_id = 104;`

The database needs to locate the record whose employee identifier is 104.

There are two fundamental access methods.

### 2.1 Sequential scan

A sequential scan examines table records until it finds the required record or reaches the end of the table.

For a table containing 10,000 records, an unsuccessful lookup can require examining all 10,000 records.

For an average uniformly distributed successful lookup, approximately half the records may be examined.

Time complexity:

- Average lookup: O(n).
- Worst-case lookup: O(n).
- Full-table retrieval: O(n).

Sequential scans are not inherently inefficient. They are often appropriate when a query needs most of the table.

### 2.2 Indexed lookup

An indexed lookup first searches the index structure.

The index identifies the corresponding table record. The database then retrieves the required data when it is not already available in the index.

For a balanced B-tree, lookup generally requires O(log n) tree navigation.

The actual cost also depends on:

- Index height.
- Data-page access.
- Cache availability.
- Number of matching records.
- Storage layout.
- Query selectivity.
- Whether an index-only scan is possible.

An indexed lookup is not necessarily one disk operation. It may require multiple index-page and table-page accesses.

## 3. Why Indexes Exist

The principal purpose of an index is to reduce the amount of data that must be examined to answer a query.

Consider a table containing one million employee records.

A query that retrieves one employee by identifier does not need to examine every employee when an appropriate index exists.

Indexes provide several practical benefits.

| Benefit | Explanation |
|---|---|
| Faster lookup | Locates matching records without scanning the complete table |
| Range retrieval | Supports conditions such as BETWEEN, greater than, and less than |
| Ordered retrieval | Can provide values in index order |
| Uniqueness enforcement | Prevents duplicate values in unique indexes |
| Join performance | Helps locate related records using join columns |
| Query efficiency | Reduces the amount of data processed for selective queries |

### 3.1 The cost of indexing

Indexes introduce additional responsibilities.

| Cost | Explanation |
|---|---|
| Storage | Index pages consume disk space |
| Insert operations | New index entries must be created |
| Update operations | Changes to indexed values may require index maintenance |
| Delete operations | Corresponding index entries must be maintained |
| Cache pressure | Large indexes compete for memory |
| Maintenance | Statistics, vacuuming, and rebuilding may be necessary |

Creating an index on every column is not a good database design strategy.

Indexes should support actual application query patterns.

## 4. B-Tree Fundamentals

A B-tree is a balanced search-tree structure designed to organize ordered keys efficiently.

It is widely used in relational database systems because it supports equality searches, range searches, and ordered retrieval.

Unlike a basic binary search tree, a B-tree node can contain multiple keys and multiple child references.

### 4.1 B-tree structure

A simplified B-tree can be represented as:

```text
                    [30 | 60]
                   /    |    \
                  /     |     \
          [10 | 20] [40 | 50] [70 | 80]

```markdown
The root contains ordered keys.

The child nodes contain keys within the ranges determined by their parent.

For example:

- Values below 30 are directed to the first child.
- Values between 30 and 60 are directed to the second child.
- Values above 60 are directed to the third child.

The structure keeps its leaves at the same depth.

This balanced structure prevents the tree from becoming a long chain.

### **4.2 Important B-tree terminology**

| Term | Meaning |
|---|---|
| Root | Topmost node |
| Internal node | Node containing keys and child references |
| Leaf | Node at the bottom level |
| Key | Indexed value used for searching |
| Child pointer | Reference to another node |
| Degree | A parameter controlling node capacity |
| Split | Operation that divides an overflowing node |
| Balanced tree | Tree whose leaves have equal depth |
| Tree height | Number of levels in the tree |

### **4.3 Multiple keys in one node**

A B-tree node can store multiple keys.

For a minimum degree `t`:

- Maximum keys per node: `2t - 1`.
- Minimum keys in a non-root node: `t - 1`.
- Maximum children: `2t`.
- Minimum children in a non-root internal node: `t`.

The root has special occupancy rules.

These properties help maintain a balanced structure.

### **4.4 Searching in a B-tree**

Suppose the requested employee identifier is 50.

The search process is:

1. Start at the root.
2. Compare the requested value with the keys in the root.
3. Determine the correct child interval.
4. Move to that child.
5. Repeat the comparison.
6. Stop when the key is found or the appropriate leaf is reached without a match.

Searching does not require checking every key in the complete tree.

### **4.5 Inserting into a B-tree**

Insertion maintains the ordering and balance of the structure.

The general process is:

1. Locate the appropriate leaf.
2. Insert the new key in sorted order.
3. Check whether the node exceeds its capacity.
4. Split an overflowing node.
5. Promote its middle key to the parent.
6. Split the parent if necessary.
7. Create a new root if the original root splits.

Splitting allows the tree to maintain its structural properties.

### **4.6 B-tree performance**

| Operation | Typical complexity |
|---|---|
| Search | O(log n) |
| Insert | O(log n) |
| Range retrieval | O(log n + k) |
| Ordered traversal | O(n) |

Here, `n` represents the number of indexed entries and `k` represents the number of matching range results.

A B-tree is particularly suitable for database systems because each node can contain many keys, reducing tree height and the number of page accesses.

## **5. Index Lookup**

Index lookup is the process of using an index to locate records satisfying a query condition.

Consider:

`SELECT * FROM employees WHERE employee_id = 7500;`

If `employee_id` has a suitable index, the database can search the index instead of examining every table record.

### **5.1 Equality lookup**

An equality lookup searches for a specific value.

Example:

`WHERE employee_id = 7500`

Common applications include:

- Employee identification.
- Customer identification.
- Product identification.
- Order identification.
- Transaction identification.

Primary keys and unique columns are common candidates for equality lookups.

### **5.2 Range lookup**

A range lookup retrieves records within a specified interval.

Example:

`WHERE salary BETWEEN 70000 AND 90000`

A B-tree maintains ordered values, making it suitable for range retrieval.

Other examples include:

- Dates between two dates.
- Transaction amounts above a threshold.
- Identifiers within an interval.
- Prices below a specified amount.

### **5.3 Ordered retrieval**

A B-tree index can support ordered retrieval.

Example:

`ORDER BY salary`

An appropriate index may allow the database to retrieve records in the required order without a separate sorting operation.

The optimizer considers whether using the index is cheaper than other available plans.

## **6. Index Lookup Versus Sequential Scan**

The following comparison explains the fundamental difference.

| Characteristic | Sequential scan | B-tree index lookup |
|---|---|---|
| Search method | Examine table records | Navigate ordered index entries |
| Data organization | Table storage order | Ordered index structure |
| Equality search | O(n) | O(log n) navigation |
| Range retrieval | Examine table records | Navigate to range and retrieve matches |
| Full-table retrieval | Often efficient | Often unnecessary |
| Additional storage | No separate index required | Index storage required |
| Insert overhead | Table insertion | Table and index maintenance |
| Update overhead | Depends on table operation | May include index maintenance |

An index is most useful when it allows the database to avoid examining a large amount of irrelevant data.

A sequential scan may be faster when:

- The table is small.
- Most records satisfy the query.
- The query needs nearly every column and row.
- Index traversal would cause many additional page accesses.

The query optimizer decides which access method is appropriate.

## **7. Types of Database Indexes**

Different index types solve different retrieval problems.

### **7.1 B-tree index**

B-tree is PostgreSQL's default index type.

It supports:

- Equality conditions.
- Range conditions.
- Ordered retrieval.
- Minimum and maximum searches.
- Many common join and filtering operations.

Example:

`CREATE INDEX idx_employee_salary ON employees (salary);`

### **7.2 Hash index**

A hash index uses a hash function to organize values.

It is primarily intended for equality comparisons.

It is not designed for ordered range retrieval.

Example:

`CREATE INDEX idx_employee_hash ON employees USING HASH (employee_id);`

### **7.3 Composite index**

A composite index contains more than one indexed column.

Example:

`CREATE INDEX idx_department_status ON employees (department_id, employment_status);`

This index is useful for queries that filter using the leading column and can also support conditions involving both columns.

Column order matters.

An index on `(department_id, employment_status)` is not equivalent to an index on `(employment_status, department_id)`.

### **7.4 Unique index**

A unique index prevents duplicate indexed values.

Example:

`CREATE UNIQUE INDEX idx_employee_email ON employees (email);`

It helps enforce data integrity while providing an indexed access path.

A unique constraint normally creates an associated unique index automatically in PostgreSQL.

### **7.5 Partial index**

A partial index contains only records satisfying a specified condition.

Example:

`CREATE INDEX idx_active_employees ON employees (department_id) WHERE employment_status = 'ACTIVE';`

It can reduce index size when queries repeatedly target a subset of records.

The query predicate must be compatible with the index predicate for the optimizer to use it.

### **7.6 Covering index**

A covering index contains the columns needed by a particular query.

In PostgreSQL, `INCLUDE` adds non-key columns to an index.

Example:

`CREATE INDEX idx_employee_department_covering ON employees (department_id) INCLUDE (employee_name, salary);`

This can support index-only scans.

An index-only scan is not guaranteed to avoid heap access. PostgreSQL also considers visibility information maintained through its visibility map.

## **8. Composite Index Fundamentals**

Composite indexes require particular attention to column order.

Consider:

`CREATE INDEX idx_department_status ON employees (department_id, employment_status);`

The index is ordered first by department and then by employment status within each department.

Its principal access patterns include:

| Query condition | Suitability |
|---|---|
| `department_id = 2` | Good |
| `department_id = 2 AND employment_status = 'ACTIVE'` | Good |
| `employment_status = 'ACTIVE'` | Not generally an efficient leading-column lookup |
| `department_id BETWEEN 1 AND 3` | Supported as a leading-column range |

The design should reflect actual filtering and sorting patterns.

PostgreSQL can sometimes use skip-scan strategies, depending on the version, index structure, statistics, and query conditions. The leading-column principle remains important when designing composite indexes.

## **9. Database Index Lookup Workflow**

A typical indexed query follows this logical sequence:

```text
Application Query
       |
       v
SQL Parser
       |
       v
Query Planner
       |
       v
Available Indexes and Table Statistics
       |
       v
Execution Plan Selection
       |
       +----------------------+
       |                      |
       v                      v
  Sequential Scan        Index Scan
                              |
                              v
                        B-tree Navigation
                              |
                              v
                        Matching Index Entry
                              |
                              v
                        Table Record Retrieval
                              |
                              v
                          Query Result
```

The actual execution plan depends on the database optimizer.

The existence of an index does not force the optimizer to use it.

## **10. Index Selectivity**

Selectivity describes how effectively a search condition narrows the number of matching records.

Consider a table containing 100,000 records.

A query retrieving one employee may have high selectivity because it returns very few records.

A query retrieving 90,000 employees has low selectivity because it returns most of the table.

This distinction affects index usefulness.

| Query | Expected index usefulness |
|---|---|
| Unique employee identifier | Very high |
| Specific email address | Very high |
| Small department subset | Potentially high |
| Most employees in the company | Often lower |
| Entire employee table | Usually low |

The optimizer uses statistics and estimated costs to compare available execution strategies.

## **11. Index Maintenance**

An index must remain consistent with its underlying table.

### **11.1 INSERT**

When a new indexed record is inserted, the corresponding index entry must also be created.

### **11.2 UPDATE**

Updating an indexed column may require changing its index entry.

Updating a non-indexed column may avoid direct index-entry changes, although PostgreSQL's HOT-update rules and other storage conditions also influence the result.

### **11.3 DELETE**

Deleting a record requires appropriate index maintenance.

PostgreSQL uses MVCC. Deleted or updated row versions may remain physically present until vacuuming makes their space reusable.

### **11.4 VACUUM**

`VACUUM` helps reclaim space occupied by dead tuples for reuse.

### **11.5 ANALYZE**

`ANALYZE` collects table statistics used by the query planner.

### **11.6 REINDEX**

`REINDEX` rebuilds an index.

It can be useful when an index needs rebuilding or maintenance.

These operations have different purposes and should not be treated as interchangeable.

## **12. Understanding Query Execution Plans**

PostgreSQL provides `EXPLAIN` and `EXPLAIN ANALYZE` for examining query execution.

Example:

`EXPLAIN SELECT * FROM employees WHERE employee_id = 7500;`

This displays the planned execution strategy.

`EXPLAIN ANALYZE` executes the query and reports actual execution measurements.

Example:

`EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM employees WHERE employee_id = 7500;`

Important plan terms include:

| Term | Meaning |
|---|---|
| Seq Scan | Reads table pages sequentially |
| Index Scan | Uses an index and retrieves matching table records |
| Index Only Scan | Retrieves required values from the index when visibility conditions permit |
| Bitmap Index Scan | Collects matching row locations through an index |
| Bitmap Heap Scan | Retrieves table records using a bitmap of row locations |
| Nested Loop | Executes one input repeatedly against another |
| Hash Join | Uses a hash structure to join relations |
| Cost | Estimated planner cost |
| Actual Time | Measured execution time |
| Rows | Estimated or actual number of returned rows |
| Buffers | Information about shared and temporary buffer activity |

Do not evaluate an index only by looking at whether an index scan appears in a plan.

Also examine:

- Actual execution time.
- Estimated versus actual rows.
- Shared buffer hits.
- Disk reads.
- Rows removed by filters.
- Index size.
- Write activity.
- Query frequency.

A forced index scan is not evidence that an index is beneficial in normal production conditions.

## **13. Implementation Analysis Across the Five Source Files**

The five implementations demonstrate related concepts through different engineering approaches.

| File | Main implementation | Distinct focus |
|---|---|---|
| Python | B-tree and employee repository | Tree operations, validation, lookup comparison |
| JavaScript | Event-driven ordered index | Binary search, events, asynchronous query execution |
| C++17 | B-tree governance and repository engine | Explicit node ownership and STL-based operations |
| Java 17 | Enterprise repository service | Records, policy objects, immutable entities, concurrency |
| PostgreSQL | Relational schema and index workflow | Real database indexes, execution plans, statistics |

### **13.1 Python implementation**

The Python implementation defines a B-tree with a configurable minimum degree.

It implements:

- Node creation.
- Key insertion.
- Node splitting.
- Point lookup.
- Ordered traversal.
- Range retrieval.
- Structural validation.

The `EmployeeTable` separates record storage from the primary index.

The index locates the employee identifier, while the dictionary retrieves the corresponding employee object.

The implementation also compares sequential lookup and indexed lookup.

Deletion is deliberately not implemented because a correct B-tree deletion algorithm requires additional balancing operations. The example rejects deletion rather than leaving inconsistent table and index states.

### **13.2 JavaScript implementation**

The JavaScript implementation uses an ordered array and binary search.

Its `OrderedIndex` class provides:

- Binary-search-based insertion positions.
- Point lookup.
- Range retrieval.
- Index removal.
- Integrity checks.

The `EmployeeRepository` maintains multiple access paths.

The primary identifier index supports direct retrieval. A department map supports department-based retrieval.

The `QueryEngine` uses asynchronous execution and events to represent query lifecycle activity.

The implementation is an educational ordered-index model. Its sorted array is not a disk-based B-tree. Insertion and removal require shifting array elements and therefore have O(n) worst-case cost.

### **13.3 C++17 implementation**

The C++ program implements a B-tree using:

- Classes.
- Structures.
- Vectors.
- Unique pointers.
- Standard algorithms.
- Exception handling.

`unique_ptr` manages node ownership and prevents accidental copying of dynamically allocated child nodes.

The repository maintains a B-tree index separately from its employee records.

The implementation validates index structure and compares lookup methods.

It uses an explicit deletion limitation to avoid incorrect index maintenance.

### **13.4 Java 17 implementation**

The Java implementation models an enterprise-oriented repository.

It includes:

- Records for immutable employee data.
- A B-tree implementation.
- An index policy interface.
- A query planning result.
- Repository-level validation.
- Concurrent read execution.
- Index integrity verification.

The `DefaultIndexPolicy` distinguishes point lookup, range lookup, and full-table retrieval.

The example also uses synchronized repository operations to protect shared state.

Its deletion operation is rejected because the teaching B-tree does not implement deletion rebalancing.

### **13.5 PostgreSQL implementation**

The SQL implementation uses a real PostgreSQL database.

It includes:

- Relational tables.
- Primary keys.
- Foreign keys.
- Unique constraints.
- Check constraints.
- B-tree indexes.
- Composite indexes.
- Covering indexes.
- Partial indexes.
- Functions.
- Views.
- CTEs.
- Transaction handling.
- Execution-plan analysis.
- Index statistics.

Unlike the in-memory implementations, PostgreSQL manages actual database pages, index structures, transaction visibility, and concurrent database operations.

The optimizer determines whether an index is appropriate for a particular query.

## **14. Practical Index Design Rules**

The following principles are useful when designing database indexes.

| Situation | Design consideration |
|---|---|
| Frequent primary-key lookup | Use a primary key |
| Frequent unique-value lookup | Consider a unique constraint |
| Frequent equality and range searches | Consider B-tree |
| Multiple filtering columns | Consider a composite index |
| Queries target a small subset | Consider a partial index |
| Queries retrieve only indexed values | Consider a covering index |
| Small table | Sequential scan may be sufficient |
| Frequent updates | Evaluate index maintenance costs |
| Large number of indexes | Review storage and write overhead |
| Unused index | Investigate whether it should be retained |

A useful index design process is:

1. Identify frequently executed queries.
2. Identify their filtering conditions.
3. Identify sorting and joining requirements.
4. Examine existing indexes.
5. Create a candidate index.
6. Run `ANALYZE`.
7. Inspect the execution plan.
8. Measure actual query performance.
9. Evaluate storage and write overhead.
10. Retain indexes that provide measurable operational value.

## **15. Security and Reliability Considerations**

Indexes are performance structures, not substitutes for security controls.

Important considerations include:

- Use parameterized SQL queries to prevent SQL injection.
- Apply database permissions according to application responsibilities.
- Enforce uniqueness and validity through database constraints.
- Use transactions for related table and index changes.
- Avoid exposing sensitive information through unrestricted diagnostic logs.
- Monitor database storage consumption.
- Validate query inputs before execution.
- Avoid creating unnecessary indexes on sensitive or high-write tables.
- Protect database backups and index-containing storage.
- Monitor long-running queries and index maintenance operations.

PostgreSQL maintains index consistency as part of its transactional storage mechanisms. Application-level index simulations must explicitly maintain consistency between their records and index structures.

## **16. Limitations of the Demonstrations**

These implementations focus on fundamental index behavior rather than complete database storage engines.

| Implementation | Limitation |
|---|---|
| Python | B-tree deletion is not implemented |
| JavaScript | Ordered array is used instead of a disk-based B-tree |
| C++17 | B-tree deletion and persistent storage are not implemented |
| Java 17 | B-tree deletion is not implemented |
| PostgreSQL | Query plans and performance depend on the actual database environment |

The in-memory programs do not reproduce database page layouts, buffer pools, write-ahead logging, MVCC, crash recovery, or disk-level index management.

PostgreSQL provides these database-level mechanisms.

## **17. Complexity Reference**

Let:

- `n` represent the number of indexed records.
- `k` represent the number of records returned by a range query.

| Operation | Sequential scan | Balanced B-tree |
|---|---|---|
| Point lookup | O(n) | O(log n) |
| Range retrieval | O(n) | O(log n + k) |
| Ordered traversal | O(n) | O(n) |
| Index construction | Not applicable | O(n log n) for repeated insertion |
| Insert | O(1) table append in a simplified model | O(log n) |
| Search all records | O(n) | O(n) |

These are algorithmic models, not guaranteed database execution times.

Actual database performance depends on page sizes, cache behavior, data distribution, storage latency, index structure, and optimizer decisions.

## **18. Key Technical Distinctions**

| Concept | Purpose |
|---|---|
| Table | Stores the actual relational records |
| Index | Provides an additional access path to records |
| B-tree | Maintains ordered keys in a balanced tree |
| Index lookup | Locates records through an index |
| Sequential scan | Examines table records directly |
| Composite index | Organizes multiple indexed columns |
| Unique index | Enforces uniqueness |
| Partial index | Indexes records satisfying a condition |
| Covering index | Stores additional values to support retrieval |
| Query planner | Selects an execution strategy |
| ANALYZE | Collects statistics for planning |
| VACUUM | Manages dead-tuple storage and reuse |
| REINDEX | Rebuilds an index |

The most important distinction is that an index is an additional data structure maintained alongside the table. It improves selected retrieval operations but introduces storage and write-maintenance costs.
```
