/*
    PostgreSQL DISTINCT and DISTINCT ON
    ====================================

    C++17 case study: an order-history reporting engine

    Scenario
    --------
    An e-commerce analytics system stores multiple orders for every customer.
    A reporting API needs to answer several questions:

      1. Which cities occur in the customer data?
      2. Which customer/city combinations are unique?
      3. What is the latest order for every customer?
      4. How should ties be resolved?
      5. Why is DISTINCT different from selecting one row per group?
      6. What is the equivalent conceptual behavior of PostgreSQL DISTINCT ON?
      7. When is ROW_NUMBER() a better conceptual alternative?

    This program is intentionally self-contained and uses the C++ standard
    library only. It models the logical behavior of PostgreSQL constructs.
    It does not pretend to implement PostgreSQL's query planner or executor.

    PostgreSQL SQL represented by this case study:

        SELECT DISTINCT city
        FROM customers;

    and:

        SELECT DISTINCT ON (customer_id)
               customer_id,
               order_id,
               order_date,
               total_amount
        FROM orders
        ORDER BY customer_id,
                 order_date DESC,
                 order_id DESC;

    Compile:

        g++ -std=c++17 -O2 main.cpp -o distinct_case_study

    Run:

        ./distinct_case_study
*/

#include <algorithm>
#include <cassert>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_set>
#include <utility>
#include <vector>

using namespace std;


// ============================================================================
// Section 1: Domain model
// ============================================================================

struct Customer {
    int customerId;
    string name;
    optional<string> city;
};

struct Order {
    int customerId;
    int orderId;
    string orderDate;
    double totalAmount;
};

struct PriceObservation {
    int productId;
    string productName;
    double price;
    string observedAt;
};


// ============================================================================
// Section 2: Output helpers
// ============================================================================

void printTitle(const string& title) {
    cout << "\n" << string(78, '=') << "\n";
    cout << title << "\n";
    cout << string(78, '=') << "\n";
}

void printOrder(const Order& order) {
    cout << "customer_id=" << order.customerId
         << ", order_id=" << order.orderId
         << ", order_date=" << order.orderDate
         << ", total_amount=" << fixed << setprecision(2)
         << order.totalAmount << '\n';
}

void printCustomer(const Customer& customer) {
    cout << "customer_id=" << customer.customerId
         << ", name=" << customer.name
         << ", city=";

    if (customer.city.has_value()) {
        cout << *customer.city;
    } else {
        cout << "NULL";
    }

    cout << '\n';
}


// ============================================================================
// Section 3: SQL DISTINCT equivalent for primitive values
// ============================================================================

vector<string> distinctStrings(const vector<string>& values) {
    /*
        PostgreSQL:

            SELECT DISTINCT city
            FROM customers;

        The set stores values already emitted.

        std::set gives deterministic sorted output. PostgreSQL itself does
        not guarantee ordering without ORDER BY. Therefore the sorting here
        is an implementation choice for readable program output, not a claim
        about PostgreSQL's natural result order.
    */

    set<string> uniqueValues(values.begin(), values.end());

    return vector<string>(uniqueValues.begin(), uniqueValues.end());
}

void demoBasicDistinct() {
    printTitle("1. SELECT DISTINCT");

    vector<string> cities = {
        "Delhi",
        "Mumbai",
        "Delhi",
        "Lucknow",
        "Mumbai",
        "Delhi"
    };

    cout << "Input:\n";

    for (const auto& city : cities) {
        cout << "  " << city << '\n';
    }

    auto uniqueCities = distinctStrings(cities);

    cout << "\nUnique values:\n";

    for (const auto& city : uniqueCities) {
        cout << "  " << city << '\n';
    }
}


// ============================================================================
// Section 4: Composite DISTINCT
// ============================================================================

struct CustomerCityKey {
    string name;
    string city;

    bool operator<(const CustomerCityKey& other) const {
        return tie(name, city) < tie(other.name, other.city);
    }
};

vector<CustomerCityKey> distinctCustomerCity(
    const vector<CustomerCityKey>& rows
) {
    set<CustomerCityKey> uniqueRows(rows.begin(), rows.end());

    return vector<CustomerCityKey>(
        uniqueRows.begin(),
        uniqueRows.end()
    );
}

void demoCompositeDistinct() {
    printTitle("2. DISTINCT over multiple columns");

    vector<CustomerCityKey> rows = {
        {"Alice", "Delhi"},
        {"Alice", "Delhi"},
        {"Alice", "Mumbai"},
        {"Bob", "Delhi"},
        {"Bob", "Delhi"},
        {"Bob", "Mumbai"}
    };

    auto result = distinctCustomerCity(rows);

    cout << "Unique (name, city) combinations:\n";

    for (const auto& row : result) {
        cout << "  (" << row.name << ", " << row.city << ")\n";
    }

    cout << R"(
PostgreSQL:

SELECT DISTINCT name, city
FROM customers;

The complete selected tuple determines uniqueness.
)";
}


// ============================================================================
// Section 5: GROUP BY comparison
// ============================================================================

map<string, size_t> countOrdersByCity(
    const vector<pair<int, string>>& orders
) {
    map<string, size_t> counts;

    for (const auto& order : orders) {
        ++counts[order.second];
    }

    return counts;
}

void demoGroupByComparison() {
    printTitle("3. DISTINCT versus GROUP BY");

    vector<pair<int, string>> orders = {
        {1001, "Delhi"},
        {1002, "Delhi"},
        {1003, "Mumbai"},
        {1004, "Delhi"},
        {1005, "Mumbai"}
    };

    set<string> distinctCities;

    for (const auto& order : orders) {
        distinctCities.insert(order.second);
    }

    cout << "DISTINCT city:\n";

    for (const auto& city : distinctCities) {
        cout << "  " << city << '\n';
    }

    auto counts = countOrdersByCity(orders);

    cout << "\nGROUP BY city, COUNT(*):\n";

    for (const auto& [city, count] : counts) {
        cout << "  " << city << " -> " << count << '\n';
    }

    cout << R"(
DISTINCT identifies unique projected rows.

GROUP BY creates groups and is normally used with aggregate operations.
)";
}


// ============================================================================
// Section 6: PostgreSQL DISTINCT ON implementation
// ============================================================================

vector<Order> distinctOnCustomer(
    vector<Order> orders
) {
    /*
        PostgreSQL query modeled here:

        SELECT DISTINCT ON (customer_id)
               customer_id,
               order_id,
               order_date,
               total_amount
        FROM orders
        ORDER BY customer_id,
                 order_date DESC,
                 order_id DESC;

        The critical idea is:

            1. Sort rows by the DISTINCT ON group key.
            2. Sort each group according to the desired preference.
            3. Keep the first row of each group.

        This is the logical behavior that DISTINCT ON expresses.
    */

    sort(
        orders.begin(),
        orders.end(),
        [](const Order& left, const Order& right) {
            if (left.customerId != right.customerId) {
                return left.customerId < right.customerId;
            }

            if (left.orderDate != right.orderDate) {
                return left.orderDate > right.orderDate;
            }

            return left.orderId > right.orderId;
        }
    );

    vector<Order> result;
    set<int> seenCustomers;

    for (const auto& order : orders) {
        if (seenCustomers.insert(order.customerId).second) {
            result.push_back(order);
        }
    }

    return result;
}

void demoLatestOrder() {
    printTitle("4. Latest order per customer using DISTINCT ON semantics");

    vector<Order> orders = {
        {1, 1001, "2026-09-10", 1500.00},
        {1, 1002, "2026-09-14", 2400.00},
        {2, 2001, "2026-09-12", 900.00},
        {2, 2002, "2026-09-15", 1200.00},
        {3, 3001, "2026-09-13", 1800.00}
    };

    cout << "Source orders:\n";

    for (const auto& order : orders) {
        printOrder(order);
    }

    auto latestOrders = distinctOnCustomer(orders);

    cout << "\nLatest order per customer:\n";

    for (const auto& order : latestOrders) {
        printOrder(order);
    }

    cout << R"(
PostgreSQL:

SELECT DISTINCT ON (customer_id)
       customer_id,
       order_id,
       order_date,
       total_amount
FROM orders
ORDER BY customer_id,
         order_date DESC,
         order_id DESC;
)";
}


// ============================================================================
// Section 7: Tie-breaking
// ============================================================================

void demoTieBreaking() {
    printTitle("5. Deterministic tie-breaking");

    vector<Order> orders = {
        {1, 1001, "2026-09-15", 500.00},
        {1, 1002, "2026-09-15", 700.00},
        {1, 1000, "2026-09-14", 300.00},
        {2, 2001, "2026-09-12", 900.00},
        {2, 2002, "2026-09-12", 950.00}
    };

    auto result = distinctOnCustomer(orders);

    cout << "Selected rows:\n";

    for (const auto& order : result) {
        printOrder(order);
    }

    cout << R"(
The ordering contains:

    customer_id ASC
    order_date DESC
    order_id DESC

If two orders share the same date, order_id determines the winner.

Without an explicit tie-breaker, multiple rows may be equally preferred.
Production reporting often needs deterministic behavior.
)";
}


// ============================================================================
// Section 8: Generic DISTINCT ON implementation
// ============================================================================

template <typename Row, typename Key, typename KeyExtractor>
vector<Row> distinctOnOrdered(
    const vector<Row>& alreadyOrderedRows,
    KeyExtractor keyExtractor
) {
    set<Key> seen;
    vector<Row> result;

    for (const auto& row : alreadyOrderedRows) {
        Key key = keyExtractor(row);

        if (seen.insert(key).second) {
            result.push_back(row);
        }
    }

    return result;
}

void demoGenericDistinctOn() {
    printTitle("6. Generic one-row-per-group algorithm");

    vector<Order> rows = {
        {1, 1002, "2026-09-14", 2400.00},
        {1, 1001, "2026-09-10", 1500.00},
        {2, 2002, "2026-09-15", 1200.00},
        {2, 2001, "2026-09-12", 900.00}
    };

    /*
        The rows are already ordered by:

            customer_id ASC
            order_date DESC
            order_id DESC

        Therefore the first row for every customer is the preferred row.
    */

    auto result = distinctOnOrdered<Order, int>(
        rows,
        [](const Order& order) {
            return order.customerId;
        }
    );

    for (const auto& order : result) {
        printOrder(order);
    }
}


// ============================================================================
// Section 9: Window function alternative
// ============================================================================

struct RankedOrder {
    Order order;
    size_t rowNumber;
};

vector<RankedOrder> rankOrdersByCustomer(
    vector<Order> orders
) {
    sort(
        orders.begin(),
        orders.end(),
        [](const Order& left, const Order& right) {
            if (left.customerId != right.customerId) {
                return left.customerId < right.customerId;
            }

            if (left.orderDate != right.orderDate) {
                return left.orderDate > right.orderDate;
            }

            return left.orderId > right.orderId;
        }
    );

    vector<RankedOrder> result;

    int currentCustomer = -1;
    size_t currentRank = 0;

    for (const auto& order : orders) {
        if (order.customerId != currentCustomer) {
            currentCustomer = order.customerId;
            currentRank = 1;
        } else {
            ++currentRank;
        }

        result.push_back({order, currentRank});
    }

    return result;
}

void demoRowNumberAlternative() {
    printTitle("7. ROW_NUMBER() conceptual alternative");

    vector<Order> orders = {
        {1, 1001, "2026-09-10", 1500.00},
        {1, 1002, "2026-09-14", 2400.00},
        {2, 2001, "2026-09-12", 900.00},
        {2, 2002, "2026-09-15", 1200.00}
    };

    auto ranked = rankOrdersByCustomer(orders);

    cout << "All ranked rows:\n";

    for (const auto& item : ranked) {
        cout << "row_number=" << item.rowNumber << " ";
        printOrder(item.order);
    }

    cout << "\nRows where row_number = 1:\n";

    for (const auto& item : ranked) {
        if (item.rowNumber == 1) {
            printOrder(item.order);
        }
    }

    cout << R"(
PostgreSQL:

ROW_NUMBER() OVER (
    PARTITION BY customer_id
    ORDER BY order_date DESC, order_id DESC
)

is more general than DISTINCT ON because the ranking number remains available.
)";
}


// ============================================================================
// Section 10: JOIN multiplicity
// ============================================================================

struct CustomerOrderView {
    int customerId;
    string customerName;
    int orderId;

    bool operator<(const CustomerOrderView& other) const {
        return tie(customerId, customerName, orderId)
             < tie(other.customerId, other.customerName, other.orderId);
    }
};

void demoJoinMultiplicity() {
    printTitle("8. DISTINCT should not hide an incorrect JOIN");

    vector<Customer> customers = {
        {1, "Alice", string("Delhi")},
        {2, "Bob", string("Mumbai")}
    };

    vector<Order> orders = {
        {1, 1001, "2026-09-10", 500.00},
        {1, 1002, "2026-09-14", 700.00},
        {2, 2001, "2026-09-12", 900.00}
    };

    vector<CustomerOrderView> joined;

    for (const auto& customer : customers) {
        for (const auto& order : orders) {
            if (customer.customerId == order.customerId) {
                joined.push_back({
                    customer.customerId,
                    customer.name,
                    order.orderId
                });
            }
        }
    }

    cout << "One-to-many JOIN output:\n";

    for (const auto& row : joined) {
        cout << "  " << row.customerName
             << " -> order " << row.orderId << '\n';
    }

    set<pair<int, string>> uniqueCustomers;

    for (const auto& row : joined) {
        uniqueCustomers.insert({row.customerId, row.customerName});
    }

    cout << "\nProjected unique customers:\n";

    for (const auto& [id, name] : uniqueCustomers) {
        cout << "  " << id << " -> " << name << '\n';
    }

    cout << R"(
If the required output is one customer per row, the DISTINCT projection may
be correct.

If the required output is every order, removing duplicates would be wrong.

DISTINCT should express a business requirement, not conceal accidental JOIN
multiplicity.
)";
}


// ============================================================================
// Section 11: NULL model
// ============================================================================

void demoNullConcept() {
    printTitle("9. NULL and DISTINCT");

    vector<Customer> customers = {
        {1, "Alice", nullopt},
        {2, "Bob", string("Delhi")},
        {3, "Carol", nullopt},
        {4, "Dave", string("Delhi")}
    };

    set<optional<string>> distinctCities;

    for (const auto& customer : customers) {
        distinctCities.insert(customer.city);
    }

    cout << "Conceptual distinct cities:\n";

    for (const auto& city : distinctCities) {
        if (city.has_value()) {
            cout << "  " << *city << '\n';
        } else {
            cout << "  NULL\n";
        }
    }

    cout << R"(
Multiple NULL values belong to one duplicate-elimination group for DISTINCT.

This should not be confused with normal SQL equality:

    NULL = NULL

does not evaluate to TRUE.

SQL's NULL semantics are based on three-valued logic, while duplicate
elimination has its own grouping behavior.
)";
}


// ============================================================================
// Section 12: Composite DISTINCT ON
// ============================================================================

struct ProductPriceKey {
    string region;
    int productId;

    bool operator<(const ProductPriceKey& other) const {
        return tie(region, productId)
             < tie(other.region, other.productId);
    }
};

vector<PriceObservation> latestPricePerRegionAndProduct(
    vector<PriceObservation> rows
) {
    /*
        The example uses productId as the group key. A real composite-key
        example would include region as another field. The separate key type
        above demonstrates how C++ can model composite database keys.
    */

    sort(
        rows.begin(),
        rows.end(),
        [](const PriceObservation& left,
           const PriceObservation& right) {
            if (left.productId != right.productId) {
                return left.productId < right.productId;
            }

            return left.observedAt > right.observedAt;
        }
    );

    return distinctOnOrdered<PriceObservation, int>(
        rows,
        [](const PriceObservation& row) {
            return row.productId;
        }
    );
}

void demoLatestPrice() {
    printTitle("10. Latest product price");

    vector<PriceObservation> observations = {
        {10, "Laptop", 70000.00, "2026-09-10"},
        {10, "Laptop", 68000.00, "2026-09-14"},
        {20, "Phone", 30000.00, "2026-09-12"},
        {20, "Phone", 29500.00, "2026-09-15"}
    };

    auto latest = latestPricePerRegionAndProduct(observations);

    for (const auto& price : latest) {
        cout << "product_id=" << price.productId
             << ", product=" << price.productName
             << ", price=" << fixed << setprecision(2)
             << price.price
             << ", observed_at=" << price.observedAt
             << '\n';
    }

    cout << R"(
PostgreSQL pattern:

SELECT DISTINCT ON (product_id)
       product_id,
       product_name,
       price,
       observed_at
FROM product_prices
ORDER BY product_id, observed_at DESC;
)";
}


// ============================================================================
// Section 13: Validation of the DISTINCT ON ordering rule
// ============================================================================

bool isValidDistinctOnOrder(
    const vector<string>& distinctOnColumns,
    const vector<string>& orderByColumns
) {
    if (orderByColumns.size() < distinctOnColumns.size()) {
        return false;
    }

    for (size_t i = 0; i < distinctOnColumns.size(); ++i) {
        if (distinctOnColumns[i] != orderByColumns[i]) {
            return false;
        }
    }

    return true;
}

void demoOrderingRule() {
    printTitle("11. PostgreSQL DISTINCT ON ordering rule");

    vector<string> validDistinctOn = {"customer_id"};
    vector<string> validOrderBy = {
        "customer_id",
        "order_date"
    };

    vector<string> invalidOrderBy = {
        "order_date",
        "customer_id"
    };

    cout << "Valid ordering: "
         << boolalpha
         << isValidDistinctOnOrder(validDistinctOn, validOrderBy)
         << '\n';

    cout << "Invalid ordering: "
         << boolalpha
         << isValidDistinctOnOrder(validDistinctOn, invalidOrderBy)
         << '\n';

    cout << R"(
PostgreSQL requires the DISTINCT ON expressions to match the leftmost
ORDER BY expressions.

Valid:

DISTINCT ON (customer_id)
ORDER BY customer_id, order_date DESC;

Invalid:

DISTINCT ON (customer_id)
ORDER BY order_date DESC, customer_id;
)";
}


// ============================================================================
// Section 14: Query intent
// ============================================================================

void demoConstructSelection() {
    printTitle("12. Choosing the correct construct");

    vector<pair<string, string>> decisions = {
        {"Unique projected rows", "SELECT DISTINCT"},
        {"One preferred row per group", "SELECT DISTINCT ON"},
        {"Rank every row within each group", "ROW_NUMBER()"},
        {"Counts or sums per group", "GROUP BY + aggregate"},
        {"Maximum value only", "MAX()"},
        {"Maximum plus complete source row", "DISTINCT ON or ROW_NUMBER()"},
        {"Every source row", "Plain SELECT"}
    };

    for (const auto& [requirement, construct] : decisions) {
        cout << left << setw(45)
             << requirement
             << " -> "
             << construct
             << '\n';
    }
}


// ============================================================================
// Section 15: Complexity analysis
// ============================================================================

void demoComplexity() {
    printTitle("13. Complexity and implementation trade-offs");

    cout << R"(
Conceptual DISTINCT using an ordered set:

    Insertion: O(log u)
    Total:      O(n log u)
    Memory:     O(u)

where:
    n = number of input rows
    u = number of unique values

The distinctOnOrdered algorithm assumes that rows are already ordered:

    Selection phase: O(n log u)

If ordering is required first:

    Sorting: O(n log n)
    Selection: O(n log u)

PostgreSQL can use different execution strategies, including sort-oriented
or hash-oriented duplicate elimination and index-supported plans.

Therefore this C++ complexity analysis describes this program's data
structures, not PostgreSQL's guaranteed internal implementation.
)";
}


// ============================================================================
// Section 16: Performance and indexing
// ============================================================================

void demoPerformance() {
    printTitle("14. PostgreSQL performance considerations");

    cout << R"(
For a PostgreSQL query such as:

SELECT DISTINCT ON (customer_id)
       customer_id,
       order_id,
       order_date,
       total_amount
FROM orders
ORDER BY customer_id,
         order_date DESC,
         order_id DESC;

a potentially useful index shape is:

CREATE INDEX ON orders
    (customer_id, order_date DESC, order_id DESC);

Whether that index is useful depends on:

    - table size
    - filtering predicates
    - selectivity
    - ordering requirements
    - selected columns
    - statistics
    - PostgreSQL version
    - available memory
    - competing workload
    - actual execution plan

Measure using:

EXPLAIN
EXPLAIN (ANALYZE, BUFFERS)

Do not infer performance solely from SQL syntax.
)";
}


// ============================================================================
// Section 17: Error handling
// ============================================================================

void validateOrder(const Order& order) {
    if (order.customerId <= 0) {
        throw invalid_argument("customerId must be positive");
    }

    if (order.orderId <= 0) {
        throw invalid_argument("orderId must be positive");
    }

    if (order.orderDate.empty()) {
        throw invalid_argument("orderDate cannot be empty");
    }

    if (order.totalAmount < 0.0) {
        throw invalid_argument("totalAmount cannot be negative");
    }
}

void validateOrders(const vector<Order>& orders) {
    for (const auto& order : orders) {
        validateOrder(order);
    }
}

void demoValidation() {
    printTitle("15. Input validation and failure handling");

    vector<Order> validOrders = {
        {1, 1001, "2026-09-10", 500.00},
        {2, 2001, "2026-09-12", 700.00}
    };

    try {
        validateOrders(validOrders);
        cout << "Valid order set accepted.\n";
    } catch (const exception& error) {
        cout << "Validation error: " << error.what() << '\n';
    }

    vector<Order> invalidOrders = {
        {-1, 1001, "2026-09-10", 500.00}
    };

    try {
        validateOrders(invalidOrders);
        cout << "Invalid order set accepted unexpectedly.\n";
    } catch (const exception& error) {
        cout << "Invalid input rejected: "
             << error.what()
             << '\n';
    }
}


// ============================================================================
// Section 18: Tests
// ============================================================================

void runTests() {
    printTitle("16. Automated correctness tests");

    {
        vector<string> values = {
            "Delhi",
            "Delhi",
            "Mumbai"
        };

        auto result = distinctStrings(values);

        assert(result.size() == 2);
    }

    {
        vector<Order> orders = {
            {1, 1001, "2026-09-10", 500.00},
            {1, 1002, "2026-09-15", 700.00},
            {2, 2001, "2026-09-11", 900.00}
        };

        auto result = distinctOnCustomer(orders);

        assert(result.size() == 2);
        assert(result[0].customerId == 1);
        assert(result[0].orderId == 1002);
        assert(result[1].customerId == 2);
    }

    {
        vector<Order> orders = {
            {1, 1001, "2026-09-15", 500.00},
            {1, 1002, "2026-09-15", 700.00}
        };

        auto result = distinctOnCustomer(orders);

        assert(result.size() == 1);
        assert(result[0].orderId == 1002);
    }

    {
        vector<string> empty;
        auto result = distinctStrings(empty);

        assert(result.empty());
    }

    {
        assert(
            isValidDistinctOnOrder(
                {"customer_id"},
                {"customer_id", "order_date"}
            )
        );

        assert(
            !isValidDistinctOnOrder(
                {"customer_id"},
                {"order_date", "customer_id"}
            )
        );
    }

    cout << "All tests passed.\n";
}


// ============================================================================
// Section 19: Security considerations
// ============================================================================

void demoSecurity() {
    printTitle("17. Security considerations");

    cout << R"(
DISTINCT and DISTINCT ON are not inherently security vulnerabilities.

Security problems usually arise around dynamic SQL construction.

Avoid:

    "SELECT DISTINCT city FROM customers WHERE country = '" + userInput + "'";

Use parameterized queries through the PostgreSQL client library.

Values should be bound as parameters rather than concatenated into SQL.

Identifiers such as column names cannot generally be treated as ordinary data
parameters. They need safe identifier handling or a strict allow-list.

The safest production design is to expose only the query structures that the
application actually requires.
)";
}


// ============================================================================
// Section 20: Real PostgreSQL query reference
// ============================================================================

void showSQLReference() {
    printTitle("18. PostgreSQL SQL reference used by the case study");

    cout << R"SQL(

-- Unique cities
SELECT DISTINCT city
FROM customers;

-- Unique combinations
SELECT DISTINCT city, country
FROM customers;

-- Latest order per customer
SELECT DISTINCT ON (customer_id)
       customer_id,
       order_id,
       order_date,
       total_amount
FROM orders
ORDER BY customer_id,
         order_date DESC,
         order_id DESC;

-- Latest price per product
SELECT DISTINCT ON (product_id)
       product_id,
       product_name,
       price,
       observed_at
FROM product_prices
ORDER BY product_id,
         observed_at DESC;

-- One row per composite group
SELECT DISTINCT ON (customer_id, product_id)
       customer_id,
       product_id,
       price,
       observed_at
FROM product_prices
ORDER BY customer_id,
         product_id,
         observed_at DESC;

-- Window-function alternative
SELECT *
FROM (
    SELECT o.*,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id
               ORDER BY order_date DESC, order_id DESC
           ) AS rn
    FROM orders AS o
) ranked
WHERE rn = 1;

-- Query plan investigation
EXPLAIN (ANALYZE, BUFFERS)
SELECT DISTINCT city
FROM customers;

)SQL";
}


// ============================================================================
// Section 21: Production checklist
// ============================================================================

void printProductionChecklist() {
    printTitle("19. Production checklist");

    vector<string> checklist = {
        "Determine whether duplicates are actually incorrect.",
        "Inspect JOIN cardinality before adding DISTINCT.",
        "Use DISTINCT when the complete projection must be unique.",
        "Use DISTINCT ON for PostgreSQL-specific one-row-per-group selection.",
        "Define the preferred row through ORDER BY.",
        "Keep DISTINCT ON columns at the left edge of ORDER BY.",
        "Add deterministic tie-breakers.",
        "Use ROW_NUMBER() for more complex ranking requirements.",
        "Use GROUP BY for aggregation.",
        "Use EXPLAIN and EXPLAIN ANALYZE for performance analysis.",
        "Evaluate indexes using real workload measurements.",
        "Never rely on result order without ORDER BY.",
        "Parameterize user-controlled values.",
        "Test NULL, empty, duplicate, and tied data.",
        "Verify that duplicate elimination does not remove meaningful facts."
    };

    for (const auto& item : checklist) {
        cout << "[ ] " << item << '\n';
    }
}


// ============================================================================
// Section 22: Main case study
// ============================================================================

int main() {
    printTitle("PostgreSQL DISTINCT and DISTINCT ON C++ Case Study");

    cout << R"(
The system models an order-history reporting problem.

The important logical distinction is:

    SELECT DISTINCT
        removes duplicate result rows.

    SELECT DISTINCT ON (group)
        keeps the first row for every group according to ORDER BY.

The second construct is PostgreSQL-specific.
)";

    demoBasicDistinct();
    demoCompositeDistinct();
    demoGroupByComparison();
    demoLatestOrder();
    demoTieBreaking();
    demoGenericDistinctOn();
    demoRowNumberAlternative();
    demoJoinMultiplicity();
    demoNullConcept();
    demoLatestPrice();
    demoOrderingRule();
    demoConstructSelection();
    demoComplexity();
    demoPerformance();
    demoValidation();
    runTests();
    demoSecurity();
    showSQLReference();
    printProductionChecklist();

    printTitle("Case study complete");

    cout << R"(
The implementation demonstrates how duplicate elimination and one-row-per-group
selection differ at the data-structure and algorithmic levels, while the SQL
reference shows the corresponding PostgreSQL constructs.
)";

    return 0;
}
