/*
 * Conditional Logic with SQL CASE, WHEN, THEN, ELSE, and Conditional Expressions
 *
 * This file complements the Python study by demonstrating:
 * - JavaScript conditional expressions
 * - SQL CASE-like rule evaluation in application code
 * - first-match rule precedence
 * - validation and error handling
 * - null handling
 * - functional rule definitions
 * - sorting with custom conditional priorities
 * - aggregation based on conditions
 * - performance-aware rule evaluation
 *
 * Runtime: Node.js 18+.
 * No external packages are required.
 */

"use strict";

function printTitle(title) {
    console.log(`\n${"=".repeat(78)}\n${title}\n${"=".repeat(78)}`);
}

function printTable(rows) {
    if (rows.length === 0) {
        console.log("(no rows)");
        return;
    }

    const columns = Object.keys(rows[0]);
    console.log(columns.join(" | "));
    console.log(columns.map(() => "---").join(" | "));

    for (const row of rows) {
        console.log(
            columns
                .map((column) => row[column] === null || row[column] === undefined
                    ? "NULL"
                    : String(row[column]))
                .join(" | ")
        );
    }
}

const customers = [
    { id: 1, name: "Asha", country: "India", loyaltyPoints: 120 },
    { id: 2, name: "Ravi", country: "India", loyaltyPoints: 40 },
    { id: 3, name: "Maya", country: "USA", loyaltyPoints: 800 },
    { id: 4, name: "Noah", country: "UK", loyaltyPoints: 15 },
    { id: 5, name: "Iris", country: "India", loyaltyPoints: 300 }
];

const orders = [
    { id: 101, customerId: 1, amount: 1250, paymentStatus: "PAID" },
    { id: 102, customerId: 1, amount: 450, paymentStatus: "PAID" },
    { id: 103, customerId: 2, amount: 90, paymentStatus: "PENDING" },
    { id: 104, customerId: 2, amount: 700, paymentStatus: "PAID" },
    { id: 105, customerId: 3, amount: 4200, paymentStatus: "PAID" },
    { id: 106, customerId: 3, amount: 1500, paymentStatus: "FAILED" },
    { id: 107, customerId: 4, amount: 50, paymentStatus: "PAID" },
    { id: 108, customerId: 5, amount: 2200, paymentStatus: "PAID" },
    { id: 109, customerId: 5, amount: 300, paymentStatus: null },
    { id: 110, customerId: 6, amount: 0, paymentStatus: "PAID" }
];

function simpleCaseLike(value) {
    /*
     * JavaScript does not have SQL's CASE syntax.
     * A switch statement provides a useful simple-CASE-like structure.
     */
    switch (value) {
        case "India":
            return "Domestic";
        case "USA":
            return "North America";
        case "UK":
            return "United Kingdom";
        default:
            return "Other";
    }
}

function searchedCaseLike(order) {
    /*
     * This mirrors SQL's searched CASE:
     *
     * CASE
     *     WHEN amount >= 3000 THEN 'Very large'
     *     WHEN amount >= 1000 THEN 'Large'
     *     WHEN amount >= 100 THEN 'Medium'
     *     ELSE 'Small'
     * END
     *
     * The if/else-if chain preserves first-match semantics.
     */
    if (order.amount >= 3000) {
        return "Very large";
    } else if (order.amount >= 1000) {
        return "Large";
    } else if (order.amount >= 100) {
        return "Medium";
    } else {
        return "Small";
    }
}

function loyaltyTier(points) {
    if (!Number.isFinite(points) || points < 0) {
        throw new RangeError("Loyalty points must be a non-negative finite number.");
    }

    if (points >= 500) {
        return "Platinum";
    } else if (points >= 200) {
        return "Gold";
    } else if (points >= 100) {
        return "Silver";
    }

    return "Standard";
}

function conditionalExpressionExample(amount) {
    /*
     * JavaScript's ternary operator is a conditional expression:
     *
     * condition ? valueIfTrue : valueIfFalse
     *
     * It is useful for short two-way decisions, but long chains are less readable.
     */
    return amount === 0 ? "Zero" : "Non-zero";
}

function safePaymentStatus(status) {
    /*
     * nullish coalescing handles null and undefined:
     * value ?? fallback
     *
     * It differs from || because valid falsy values such as 0 and ""
     * are not replaced by the fallback.
     */
    return status ?? "UNKNOWN";
}

function classifyOrders() {
    printTitle("1. Row classification");

    const result = orders.map((order) => ({
        orderId: order.id,
        amount: order.amount,
        size: searchedCaseLike(order),
        zeroState: conditionalExpressionExample(order.amount)
    }));

    printTable(result);
}

function classifyCustomers() {
    printTitle("2. Customer classification");

    const result = customers.map((customer) => ({
        customer: customer.name,
        country: customer.country,
        market: simpleCaseLike(customer.country),
        tier: loyaltyTier(customer.loyaltyPoints)
    }));

    printTable(result);
}

function demonstrateNullHandling() {
    printTitle("3. NULL-like values");

    const result = orders.map((order) => ({
        orderId: order.id,
        rawStatus: order.paymentStatus,
        safeStatus: safePaymentStatus(order.paymentStatus)
    }));

    printTable(result);

    console.log("\nImportant: JavaScript null is not identical to SQL NULL semantics.");
    console.log("Database drivers normally map SQL NULL to JavaScript null,");
    console.log("but SQL comparisons involving NULL use three-valued logic.");
}

function validateOrder(order) {
    if (!order || typeof order !== "object") {
        throw new TypeError("Order must be an object.");
    }

    if (!Number.isInteger(order.id) || order.id <= 0) {
        throw new RangeError("Order id must be a positive integer.");
    }

    if (!Number.isFinite(order.amount) || order.amount < 0) {
        throw new RangeError("Order amount must be a non-negative finite number.");
    }

    const allowedStatuses = new Set(["PAID", "PENDING", "FAILED", null]);

    if (!allowedStatuses.has(order.paymentStatus)) {
        throw new RangeError(`Unsupported payment status: ${order.paymentStatus}`);
    }
}

function paymentCategory(order) {
    validateOrder(order);

    if (order.paymentStatus === null) {
        return "Status missing";
    }

    if (order.paymentStatus === "PAID") {
        return "Completed";
    }

    if (order.paymentStatus === "PENDING") {
        return "Awaiting payment";
    }

    return "Failed";
}

function validateExamples() {
    printTitle("4. Validation and error handling");

    const validOrder = {
        id: 999,
        amount: 125,
        paymentStatus: "PAID"
    };

    console.log("Valid:", paymentCategory(validOrder));

    const invalidOrders = [
        { id: -1, amount: 100, paymentStatus: "PAID" },
        { id: 2, amount: -10, paymentStatus: "PAID" },
        { id: 3, amount: 100, paymentStatus: "UNKNOWN" }
    ];

    for (const invalidOrder of invalidOrders) {
        try {
            paymentCategory(invalidOrder);
        } catch (error) {
            console.log(`Rejected order: ${error.message}`);
        }
    }
}

function calculateDiscount(amount) {
    /*
     * This rule ordering intentionally mirrors a searched CASE.
     * Specific/high-value rules must occur before broad rules.
     */
    const rules = [
        {
            name: "Premium",
            matches: (value) => value >= 3000,
            rate: 0.15
        },
        {
            name: "Large",
            matches: (value) => value >= 1000,
            rate: 0.10
        },
        {
            name: "Standard",
            matches: (value) => value >= 500,
            rate: 0.05
        }
    ];

    for (const rule of rules) {
        if (rule.matches(amount)) {
            return {
                rule: rule.name,
                discount: Number((amount * rule.rate).toFixed(2))
            };
        }
    }

    return {
        rule: "None",
        discount: 0
    };
}

function ruleEngineDemo() {
    printTitle("5. Data-driven first-match rule engine");

    for (const amount of [50, 500, 750, 1000, 3000, 5000]) {
        const result = calculateDiscount(amount);
        console.log(
            `amount=${amount.toFixed(2)} rule=${result.rule} discount=${result.discount.toFixed(2)}`
        );
    }
}

function demonstrateWrongRuleOrdering() {
    printTitle("6. Overlapping conditions and rule precedence");

    function incorrectClassification(amount) {
        if (amount >= 100) {
            return "Large";
        } else if (amount >= 1000) {
            return "Very large";
        }

        return "Small";
    }

    function correctClassification(amount) {
        if (amount >= 1000) {
            return "Very large";
        } else if (amount >= 100) {
            return "Large";
        }

        return "Small";
    }

    for (const amount of [99.99, 100, 999.99, 1000, 3000]) {
        console.log(
            `amount=${amount}: incorrect=${incorrectClassification(amount)}, ` +
            `correct=${correctClassification(amount)}`
        );
    }
}

function customPaymentSort(a, b) {
    /*
     * SQL can use CASE in ORDER BY.
     * JavaScript's Array.sort can use an equivalent priority map.
     */
    const priority = {
        PENDING: 1,
        FAILED: 2,
        PAID: 3
    };

    const priorityA = priority[a.paymentStatus] ?? 4;
    const priorityB = priority[b.paymentStatus] ?? 4;

    if (priorityA !== priorityB) {
        return priorityA - priorityB;
    }

    return b.amount - a.amount;
}

function conditionalSorting() {
    printTitle("7. Conditional sorting");

    const result = [...orders]
        .sort(customPaymentSort)
        .map((order) => ({
            orderId: order.id,
            paymentStatus: safePaymentStatus(order.paymentStatus),
            amount: order.amount
        }));

    printTable(result);
}

function conditionalAggregation() {
    printTitle("8. Conditional aggregation");

    const paidOrders = orders.filter((order) => order.paymentStatus === "PAID");
    const pendingOrders = orders.filter((order) => order.paymentStatus === "PENDING");
    const failedOrders = orders.filter((order) => order.paymentStatus === "FAILED");

    const paidAmount = paidOrders.reduce((sum, order) => sum + order.amount, 0);

    const totalOrders = orders.length;
    const paidPercentage = totalOrders === 0
        ? 0
        : Number(((paidOrders.length / totalOrders) * 100).toFixed(2));

    console.log(`Total orders: ${totalOrders}`);
    console.log(`Paid orders: ${paidOrders.length}`);
    console.log(`Pending orders: ${pendingOrders.length}`);
    console.log(`Failed orders: ${failedOrders.length}`);
    console.log(`Paid amount: ${paidAmount.toFixed(2)}`);
    console.log(`Paid percentage: ${paidPercentage}%`);
}

function buildCustomerMetrics() {
    printTitle("9. Integrated customer report");

    const rows = customers.map((customer) => {
        const customerOrders = orders.filter(
            (order) => order.customerId === customer.id
        );

        const totalSpend = customerOrders.reduce(
            (sum, order) => sum + order.amount,
            0
        );

        const paidSpend = customerOrders
            .filter((order) => order.paymentStatus === "PAID")
            .reduce((sum, order) => sum + order.amount, 0);

        let segment;

        if (totalSpend >= 5000 && customer.loyaltyPoints >= 500) {
            segment = "Strategic customer";
        } else if (totalSpend >= 2000 || customer.loyaltyPoints >= 300) {
            segment = "High-value customer";
        } else if (totalSpend >= 500 || customer.loyaltyPoints >= 100) {
            segment = "Growing customer";
        } else {
            segment = "Standard customer";
        }

        let paymentProfile;

        if (customerOrders.length === 0) {
            paymentProfile = "No orders";
        } else if (paidSpend === totalSpend) {
            paymentProfile = "All orders paid";
        } else if (paidSpend > 0) {
            paymentProfile = "Mixed payment state";
        } else {
            paymentProfile = "No paid orders";
        }

        return {
            customer: customer.name,
            totalSpend,
            orderCount: customerOrders.length,
            paidSpend,
            segment,
            paymentProfile
        };
    });

    printTable(
        rows.map((row) => ({
            ...row,
            totalSpend: row.totalSpend.toFixed(2),
            paidSpend: row.paidSpend.toFixed(2)
        }))
    );
}

function boundaryTests() {
    printTitle("10. Boundary-value tests");

    const testValues = [
        99.99,
        100,
        100.01,
        999.99,
        1000,
        1000.01,
        2999.99,
        3000
    ];

    for (const amount of testValues) {
        console.log(
            `${amount.toFixed(2)} -> ${searchedCaseLike({
                amount
            })}`
        );
    }
}

function benchmarkRuleEvaluation() {
    printTitle("11. Simple performance comparison");

    /*
     * For a small fixed number of rules, an if/else-if chain avoids creating
     * extra objects and callbacks. A data-driven rule array is more flexible
     * but may carry some per-evaluation overhead.
     */
    const testAmounts = Array.from({ length: 100000 }, (_, index) => index % 5000);

    const startIf = process.hrtime.bigint();

    let ifAccumulator = 0;

    for (const amount of testAmounts) {
        if (amount >= 3000) {
            ifAccumulator += 4;
        } else if (amount >= 1000) {
            ifAccumulator += 3;
        } else if (amount >= 100) {
            ifAccumulator += 2;
        } else {
            ifAccumulator += 1;
        }
    }

    const endIf = process.hrtime.bigint();

    const startRules = process.hrtime.bigint();

    let ruleAccumulator = 0;

    const rules = [
        { matches: (value) => value >= 3000, result: 4 },
        { matches: (value) => value >= 1000, result: 3 },
        { matches: (value) => value >= 100, result: 2 }
    ];

    for (const amount of testAmounts) {
        let result = 1;

        for (const rule of rules) {
            if (rule.matches(amount)) {
                result = rule.result;
                break;
            }
        }

        ruleAccumulator += result;
    }

    const endRules = process.hrtime.bigint();

    const ifMilliseconds = Number(endIf - startIf) / 1e6;
    const rulesMilliseconds = Number(endRules - startRules) / 1e6;

    console.log(`if/else accumulator: ${ifAccumulator}`);
    console.log(`rule-array accumulator: ${ruleAccumulator}`);
    console.log(`if/else elapsed: ${ifMilliseconds.toFixed(3)} ms`);
    console.log(`rule-array elapsed: ${rulesMilliseconds.toFixed(3)} ms`);
    console.log("Benchmark values vary by runtime, hardware, and optimization state.");
}

function runStudy() {
    classifyOrders();
    classifyCustomers();
    demonstrateNullHandling();
    validateExamples();
    ruleEngineDemo();
    demonstrateWrongRuleOrdering();
    conditionalSorting();
    conditionalAggregation();
    buildCustomerMetrics();
    boundaryTests();
    benchmarkRuleEvaluation();

    printTitle("12. Important distinctions");
    console.log("SQL CASE is an expression that returns a SQL value.");
    console.log("JavaScript if/else is control flow; the ternary operator is an expression.");
    console.log("JavaScript switch is useful for simple value-to-value branching.");
    console.log("SQL NULL uses three-valued logic, so database NULL handling must be explicit.");
}

runStudy();
