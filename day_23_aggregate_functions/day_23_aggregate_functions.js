/*
 * Aggregate Functions: COUNT, SUM, AVG, MIN, MAX
 *
 * A self-contained JavaScript study file demonstrating the concepts behind
 * SQL aggregate functions through practical in-memory data processing.
 *
 * The examples progress from basic aggregation to grouping, NULL handling,
 * DISTINCT behavior, conditional aggregation, joins, window-style
 * calculations, validation, performance considerations, and a realistic
 * sales analytics case study.
 *
 * Runtime: modern Node.js
 *
 * No external npm packages are required.
 */


// -----------------------------------------------------------------------------
// 1. Output helpers
// -----------------------------------------------------------------------------

function printTitle(title) {
    console.log("\n" + "=".repeat(80));
    console.log(title);
    console.log("=".repeat(80));
}

function printObject(object) {
    console.table([object]);
}

function round(value, digits = 2) {
    const factor = 10 ** digits;
    return Math.round((value + Number.EPSILON) * factor) / factor;
}


// -----------------------------------------------------------------------------
// 2. Example data
// -----------------------------------------------------------------------------

printTitle("1. Creating the Example Dataset");

const customers = [
    { customerId: 1, name: "Aarav Sharma", city: "Lucknow", type: "Retail" },
    { customerId: 2, name: "Meera Singh", city: "Delhi", type: "Business" },
    { customerId: 3, name: "Rohan Verma", city: "Mumbai", type: "Retail" },
    { customerId: 4, name: "Ananya Gupta", city: "Lucknow", type: "Business" },
    { customerId: 5, name: "Kabir Khan", city: "Pune", type: "Retail" },
    { customerId: 6, name: "Isha Patel", city: "Ahmedabad", type: "Business" }
];

const products = [
    { productId: 1, name: "Laptop Pro", category: "Computers", price: 75000, stock: 12 },
    { productId: 2, name: "Wireless Mouse", category: "Accessories", price: 1500, stock: 80 },
    { productId: 3, name: "Mechanical Keyboard", category: "Accessories", price: 4500, stock: 35 },
    { productId: 4, name: "Monitor 27", category: "Displays", price: 22000, stock: 20 },
    { productId: 5, name: "USB-C Hub", category: "Accessories", price: 3500, stock: 50 },
    { productId: 6, name: "Office Chair", category: "Furniture", price: 18000, stock: 8 }
];

const sales = [
    { saleId: 1, customerId: 1, productId: 1, date: "2026-01-05", quantity: 1, unitPrice: 75000, discount: 5000, salesperson: "Neha" },
    { saleId: 2, customerId: 1, productId: 2, date: "2026-01-06", quantity: 2, unitPrice: 1500, discount: null, salesperson: "Neha" },
    { saleId: 3, customerId: 2, productId: 3, date: "2026-01-07", quantity: 3, unitPrice: 4500, discount: 1000, salesperson: "Rahul" },
    { saleId: 4, customerId: 2, productId: 4, date: "2026-01-08", quantity: 2, unitPrice: 22000, discount: 2000, salesperson: "Rahul" },
    { saleId: 5, customerId: 3, productId: 2, date: "2026-01-10", quantity: 1, unitPrice: 1500, discount: null, salesperson: "Priya" },
    { saleId: 6, customerId: 3, productId: 5, date: "2026-01-12", quantity: 4, unitPrice: 3500, discount: 500, salesperson: "Priya" },
    { saleId: 7, customerId: 4, productId: 1, date: "2026-02-01", quantity: 2, unitPrice: 75000, discount: 10000, salesperson: "Neha" },
    { saleId: 8, customerId: 4, productId: 6, date: "2026-02-03", quantity: 1, unitPrice: 18000, discount: null, salesperson: "Neha" },
    { saleId: 9, customerId: 5, productId: 3, date: "2026-02-05", quantity: 1, unitPrice: 4500, discount: null, salesperson: "Rahul" },
    { saleId: 10, customerId: 5, productId: 2, date: "2026-02-06", quantity: 5, unitPrice: 1500, discount: 250, salesperson: "Rahul" },
    { saleId: 11, customerId: 6, productId: 4, date: "2026-02-09", quantity: 3, unitPrice: 22000, discount: 3000, salesperson: "Priya" },
    { saleId: 12, customerId: 6, productId: 5, date: "2026-02-11", quantity: 2, unitPrice: 3500, discount: null, salesperson: "Priya" },
    { saleId: 13, customerId: 1, productId: 2, date: "2026-03-02", quantity: 3, unitPrice: 1500, discount: null, salesperson: "Neha" },
    { saleId: 14, customerId: 2, productId: 5, date: "2026-03-04", quantity: 2, unitPrice: 3500, discount: 500, salesperson: "Rahul" },
    { saleId: 15, customerId: 3, productId: 4, date: "2026-03-06", quantity: 1, unitPrice: 22000, discount: null, salesperson: "Priya" }
];

console.log(`Customers: ${customers.length}`);
console.log(`Products: ${products.length}`);
console.log(`Sales lines: ${sales.length}`);


// -----------------------------------------------------------------------------
// 3. Core aggregate implementations
// -----------------------------------------------------------------------------

printTitle("2. Implementing COUNT, SUM, AVG, MIN and MAX");

function countRows(values) {
    return values.length;
}

function countNonNull(values) {
    return values.filter(value => value !== null && value !== undefined).length;
}

function sum(values) {
    return values
        .filter(value => value !== null && value !== undefined)
        .reduce((total, value) => total + value, 0);
}

function average(values) {
    const validValues = values.filter(
        value => value !== null && value !== undefined
    );

    if (validValues.length === 0) {
        return null;
    }

    return sum(validValues) / validValues.length;
}

function minimum(values) {
    const validValues = values.filter(
        value => value !== null && value !== undefined
    );

    return validValues.length === 0 ? null : Math.min(...validValues);
}

function maximum(values) {
    const validValues = values.filter(
        value => value !== null && value !== undefined
    );

    return validValues.length === 0 ? null : Math.max(...validValues);
}

const quantities = sales.map(sale => sale.quantity);

printObject({
    COUNT: countRows(quantities),
    SUM: sum(quantities),
    AVG: round(average(quantities)),
    MIN: minimum(quantities),
    MAX: maximum(quantities)
});


// -----------------------------------------------------------------------------
// 4. NULL semantics
// -----------------------------------------------------------------------------

printTitle("3. NULL Behavior");

const nullableValues = [10, 20, null, 30, null];

printObject({
    "COUNT(*) equivalent": countRows(nullableValues),
    "COUNT(value) equivalent": countNonNull(nullableValues),
    "SUM(value)": sum(nullableValues),
    "AVG(value)": average(nullableValues),
    "MIN(value)": minimum(nullableValues),
    "MAX(value)": maximum(nullableValues)
});

console.log(
    "\nNULL is not automatically equivalent to zero. " +
    "It represents a missing or unknown value."
);


// -----------------------------------------------------------------------------
// 5. DISTINCT
// -----------------------------------------------------------------------------

printTitle("4. DISTINCT Aggregation");

function uniqueValues(values) {
    return [...new Set(
        values.filter(value => value !== null && value !== undefined)
    )];
}

function countDistinct(values) {
    return uniqueValues(values).length;
}

function sumDistinct(values) {
    return sum(uniqueValues(values));
}

function averageDistinct(values) {
    return average(uniqueValues(values));
}

const customerIds = sales.map(sale => sale.customerId);
const unitPrices = sales.map(sale => sale.unitPrice);

printObject({
    totalSalesLines: sales.length,
    uniqueCustomers: countDistinct(customerIds),
    uniqueUnitPrices: countDistinct(unitPrices),
    sumOfDistinctPrices: sumDistinct(unitPrices),
    averageOfDistinctPrices: round(averageDistinct(unitPrices))
});


// -----------------------------------------------------------------------------
// 6. Basic complete aggregate report
// -----------------------------------------------------------------------------

printTitle("5. Complete Sales Aggregation");

const grossRevenueValues = sales.map(
    sale => sale.quantity * sale.unitPrice
);

const discounts = sales.map(sale => sale.discount);

const completeReport = {
    transactionLines: sales.length,
    uniqueCustomers: countDistinct(customerIds),
    uniqueProducts: countDistinct(sales.map(sale => sale.productId)),
    unitsSold: sum(quantities),
    averageUnitsPerLine: round(average(quantities)),
    minimumUnitsPerLine: minimum(quantities),
    maximumUnitsPerLine: maximum(quantities),
    grossRevenue: round(sum(grossRevenueValues)),
    totalDiscounts: round(sum(discounts)),
    netRevenue: round(sum(grossRevenueValues) - sum(discounts))
};

printObject(completeReport);


// -----------------------------------------------------------------------------
// 7. Grouping utility
// -----------------------------------------------------------------------------

printTitle("6. GROUP BY Simulation");

function groupBy(rows, keyFunction) {
    const groups = new Map();

    for (const row of rows) {
        const key = keyFunction(row);

        if (!groups.has(key)) {
            groups.set(key, []);
        }

        groups.get(key).push(row);
    }

    return groups;
}

const salesBySalesperson = groupBy(
    sales,
    sale => sale.salesperson
);

for (const [salesperson, rows] of salesBySalesperson) {
    console.log(
        salesperson,
        {
            count: rows.length,
            units: sum(rows.map(row => row.quantity)),
            revenue: round(
                sum(rows.map(row => row.quantity * row.unitPrice))
            )
        }
    );
}


// -----------------------------------------------------------------------------
// 8. Generic grouped aggregation
// -----------------------------------------------------------------------------

printTitle("7. Reusable Grouped Aggregation");

function aggregateRows(rows) {
    const quantities = rows.map(row => row.quantity);
    const revenues = rows.map(row => row.quantity * row.unitPrice);

    return {
        count: rows.length,
        units: sum(quantities),
        averageUnits: round(average(quantities)),
        minimumUnits: minimum(quantities),
        maximumUnits: maximum(quantities),
        revenue: round(sum(revenues))
    };
}

function aggregateBy(rows, keyFunction) {
    const groups = groupBy(rows, keyFunction);
    const result = [];

    for (const [key, groupRows] of groups) {
        result.push({
            group: key,
            ...aggregateRows(groupRows)
        });
    }

    return result;
}

console.table(
    aggregateBy(sales, sale => sale.salesperson)
);


// -----------------------------------------------------------------------------
// 9. Grouping by multiple dimensions
// -----------------------------------------------------------------------------

printTitle("8. GROUP BY Multiple Columns");

const salespersonCustomerReport = aggregateBy(
    sales,
    sale => `${sale.salesperson}|${sale.customerId}`
);

console.table(salespersonCustomerReport);


// -----------------------------------------------------------------------------
// 10. HAVING-style filtering
// -----------------------------------------------------------------------------

printTitle("9. HAVING-Style Filtering");

const highRevenueSalespeople = aggregateBy(
    sales,
    sale => sale.salesperson
).filter(group => group.revenue > 50000);

console.table(highRevenueSalespeople);

console.log(
    "\nThe filtering occurs after each group has been aggregated. " +
    "This corresponds conceptually to SQL HAVING."
);


// -----------------------------------------------------------------------------
// 11. WHERE-style filtering before aggregation
// -----------------------------------------------------------------------------

printTitle("10. WHERE-Style Filtering");

const salesFromFebruary = sales.filter(
    sale => sale.date >= "2026-02-01" && sale.date <= "2026-02-28"
);

console.table(
    aggregateBy(salesFromFebruary, sale => sale.salesperson)
);

console.log(
    "\nThe rows were filtered before grouping, corresponding conceptually " +
    "to SQL WHERE."
);


// -----------------------------------------------------------------------------
// 12. Conditional aggregation
// -----------------------------------------------------------------------------

printTitle("11. Conditional Aggregation");

const conditionalReport = {
    totalLines: sales.length,

    highQuantityLines: sales.filter(
        sale => sale.quantity >= 3
    ).length,

    highQuantityUnits: sum(
        sales
            .filter(sale => sale.quantity >= 3)
            .map(sale => sale.quantity)
    ),

    premiumRevenue: sum(
        sales
            .filter(sale => sale.unitPrice >= 20000)
            .map(sale => sale.quantity * sale.unitPrice)
    ),

    discountedLines: sales.filter(
        sale => sale.discount !== null
    ).length
};

printObject(conditionalReport);


// -----------------------------------------------------------------------------
// 13. Product lookup and JOIN-style processing
// -----------------------------------------------------------------------------

printTitle("12. JOIN-Style Product Aggregation");

const productMap = new Map(
    products.map(product => [product.productId, product])
);

const salesWithProducts = sales.map(sale => ({
    ...sale,
    product: productMap.get(sale.productId)
}));

const categoryReport = aggregateBy(
    salesWithProducts,
    sale => sale.product.category
);

console.table(categoryReport);


// -----------------------------------------------------------------------------
// 14. Customer LEFT JOIN-style report
// -----------------------------------------------------------------------------

printTitle("13. Customer Report Including Customers Without Sales");

const salesByCustomer = groupBy(
    sales,
    sale => sale.customerId
);

const customerReport = customers.map(customer => {
    const customerSales = salesByCustomer.get(customer.customerId) || [];

    return {
        customer: customer.name,
        city: customer.city,
        type: customer.type,
        purchaseLines: customerSales.length,
        unitsBought: sum(
            customerSales.map(sale => sale.quantity)
        ),
        grossSpend: round(
            sum(
                customerSales.map(
                    sale => sale.quantity * sale.unitPrice
                )
            )
        )
    };
});

console.table(customerReport);


// -----------------------------------------------------------------------------
// 15. Product performance including unsold products
// -----------------------------------------------------------------------------

printTitle("14. Product Performance");

const salesByProduct = groupBy(
    sales,
    sale => sale.productId
);

const productReport = products.map(product => {
    const productSales = salesByProduct.get(product.productId) || [];

    return {
        product: product.name,
        category: product.category,
        stock: product.stock,
        saleLines: productSales.length,
        unitsSold: sum(
            productSales.map(sale => sale.quantity)
        ),
        revenue: round(
            sum(
                productSales.map(
                    sale => sale.quantity * sale.unitPrice
                )
            )
        )
    };
});

console.table(productReport);


// -----------------------------------------------------------------------------
// 16. Date-based aggregation
// -----------------------------------------------------------------------------

printTitle("15. Monthly Aggregation");

function monthFromDate(dateString) {
    return dateString.slice(0, 7);
}

const monthlyReport = aggregateBy(
    sales,
    sale => monthFromDate(sale.date)
).sort(
    (a, b) => a.group.localeCompare(b.group)
);

console.table(monthlyReport);


// -----------------------------------------------------------------------------
// 17. MIN and MAX dates
// -----------------------------------------------------------------------------

printTitle("16. MIN and MAX with Dates");

const dates = sales.map(sale => sale.date);

printObject({
    firstSaleDate: minimum(
        dates.map(date => Date.parse(date))
    )
        ? new Date(
            minimum(dates.map(date => Date.parse(date)))
        ).toISOString().slice(0, 10)
        : null,

    lastSaleDate: maximum(
        dates.map(date => Date.parse(date))
    )
        ? new Date(
            maximum(dates.map(date => Date.parse(date)))
        ).toISOString().slice(0, 10)
        : null
});


// -----------------------------------------------------------------------------
// 18. Running aggregate
// -----------------------------------------------------------------------------

printTitle("17. Running Revenue");

const sortedSales = [...sales].sort(
    (a, b) => {
        const dateComparison = a.date.localeCompare(b.date);

        if (dateComparison !== 0) {
            return dateComparison;
        }

        return a.saleId - b.saleId;
    }
);

let cumulativeRevenue = 0;

const runningRevenue = sortedSales.map(sale => {
    const lineRevenue = sale.quantity * sale.unitPrice;
    cumulativeRevenue += lineRevenue;

    return {
        saleId: sale.saleId,
        date: sale.date,
        lineRevenue,
        cumulativeRevenue: round(cumulativeRevenue)
    };
});

console.table(runningRevenue);


// -----------------------------------------------------------------------------
// 19. Window-style partition aggregation
// -----------------------------------------------------------------------------

printTitle("18. Window-Style Salesperson Totals");

const salespersonTotals = new Map();

for (const sale of sales) {
    const revenue = sale.quantity * sale.unitPrice;

    salespersonTotals.set(
        sale.salesperson,
        (salespersonTotals.get(sale.salesperson) || 0) + revenue
    );
}

const windowStyleRows = sales.map(sale => ({
    saleId: sale.saleId,
    salesperson: sale.salesperson,
    lineRevenue: sale.quantity * sale.unitPrice,
    salespersonTotalRevenue: round(
        salespersonTotals.get(sale.salesperson)
    )
}));

console.table(windowStyleRows);


// -----------------------------------------------------------------------------
// 20. Ranking aggregated groups
// -----------------------------------------------------------------------------

printTitle("19. Ranking Salespeople After Aggregation");

const rankedSalespeople = aggregateBy(
    sales,
    sale => sale.salesperson
)
    .sort((a, b) => b.revenue - a.revenue)
    .map((row, index) => ({
        ...row,
        rank: index + 1
    }));

console.table(rankedSalespeople);


// -----------------------------------------------------------------------------
// 21. Important distinction: average of rows vs average of groups
// -----------------------------------------------------------------------------

printTitle("20. Average of Rows vs Average of Group Totals");

const averageLineRevenue = average(
    sales.map(sale => sale.quantity * sale.unitPrice)
);

const salespersonGroups = aggregateBy(
    sales,
    sale => sale.salesperson
);

const averageSalespersonRevenue = average(
    salespersonGroups.map(group => group.revenue)
);

printObject({
    averageTransactionLineRevenue: round(averageLineRevenue),
    averageSalespersonRevenue: round(averageSalespersonRevenue)
});

console.log(
    "\nThese metrics answer different questions and should not be treated " +
    "as interchangeable."
);


// -----------------------------------------------------------------------------
// 22. Financial precision
// -----------------------------------------------------------------------------

printTitle("21. Monetary Precision Considerations");

const floatingPointExample = 0.1 + 0.2;

console.log("JavaScript 0.1 + 0.2 =", floatingPointExample);
console.log(
    "For exact financial systems, consider integer minor units " +
    "(for example paise) or a decimal arithmetic strategy."
);

function rupeesToPaise(rupees) {
    if (!Number.isFinite(rupees) || rupees < 0) {
        throw new Error("Amount must be a finite non-negative number.");
    }

    return Math.round(rupees * 100);
}

function paiseToRupees(paise) {
    if (!Number.isInteger(paise) || paise < 0) {
        throw new Error("Paise must be a non-negative integer.");
    }

    return paise / 100;
}

const monetaryValues = [10.10, 20.20, 30.30];

const totalPaise = sum(
    monetaryValues.map(rupeesToPaise)
);

console.log("Total paise:", totalPaise);
console.log("Total rupees:", paiseToRupees(totalPaise));


// -----------------------------------------------------------------------------
// 23. Validation
// -----------------------------------------------------------------------------

printTitle("22. Validation Before Aggregation");

function validateSale(sale) {
    if (!Number.isInteger(sale.quantity) || sale.quantity <= 0) {
        throw new Error(
            `Sale ${sale.saleId}: quantity must be a positive integer.`
        );
    }

    if (!Number.isFinite(sale.unitPrice) || sale.unitPrice < 0) {
        throw new Error(
            `Sale ${sale.saleId}: unit price must be non-negative.`
        );
    }

    if (
        sale.discount !== null &&
        (!Number.isFinite(sale.discount) || sale.discount < 0)
    ) {
        throw new Error(
            `Sale ${sale.saleId}: discount must be null or non-negative.`
        );
    }

    return true;
}

for (const sale of sales) {
    validateSale(sale);
}

console.log("All sales passed validation.");


// -----------------------------------------------------------------------------
// 24. Empty-set behavior
// -----------------------------------------------------------------------------

printTitle("23. Empty Dataset Behavior");

const empty = [];

printObject({
    count: countRows(empty),
    sum: sum(empty),
    average: average(empty),
    minimum: minimum(empty),
    maximum: maximum(empty)
});

console.log(
    "\nThe application must explicitly define what an empty aggregate " +
    "means. JavaScript's helper functions return null for undefined " +
    "average, minimum, and maximum."
);


// -----------------------------------------------------------------------------
// 25. Query-like analytics service
// -----------------------------------------------------------------------------

printTitle("24. Reusable Sales Analytics Service");

class SalesAnalytics {
    constructor(salesRows) {
        this.sales = [...salesRows];

        for (const sale of this.sales) {
            validateSale(sale);
        }
    }

    totalUnits() {
        return sum(this.sales.map(sale => sale.quantity));
    }

    grossRevenue() {
        return sum(
            this.sales.map(
                sale => sale.quantity * sale.unitPrice
            )
        );
    }

    discounts() {
        return sum(
            this.sales.map(
                sale => sale.discount ?? 0
            )
        );
    }

    netRevenue() {
        return this.grossRevenue() - this.discounts();
    }

    uniqueCustomers() {
        return countDistinct(
            this.sales.map(sale => sale.customerId)
        );
    }

    uniqueProducts() {
        return countDistinct(
            this.sales.map(sale => sale.productId)
        );
    }

    report() {
        const quantities = this.sales.map(
            sale => sale.quantity
        );

        return {
            transactionLines: this.sales.length,
            uniqueCustomers: this.uniqueCustomers(),
            uniqueProducts: this.uniqueProducts(),
            unitsSold: this.totalUnits(),
            averageUnits: round(average(quantities)),
            minimumUnits: minimum(quantities),
            maximumUnits: maximum(quantities),
            grossRevenue: round(this.grossRevenue()),
            discounts: round(this.discounts()),
            netRevenue: round(this.netRevenue())
        };
    }
}

const analytics = new SalesAnalytics(sales);

printObject(analytics.report());


// -----------------------------------------------------------------------------
// 26. Date-filtered reporting
// -----------------------------------------------------------------------------

printTitle("25. Date-Range Report");

function dateRangeReport(rows, startDate, endDate) {
    if (startDate > endDate) {
        throw new Error("Start date cannot be after end date.");
    }

    const filtered = rows.filter(
        row => row.date >= startDate && row.date <= endDate
    );

    const service = new SalesAnalytics(filtered);

    return {
        startDate,
        endDate,
        ...service.report()
    };
}

printObject(
    dateRangeReport(
        sales,
        "2026-01-01",
        "2026-02-28"
    )
);


// -----------------------------------------------------------------------------
// 27. Performance considerations
// -----------------------------------------------------------------------------

printTitle("26. Performance Considerations");

console.log(`
Repeatedly scanning a large array for every metric can create unnecessary
work.

A single-pass aggregation can calculate multiple metrics together.

This is conceptually similar to an efficient SQL query that lets the
database engine perform multiple aggregates during one execution.

The following implementation performs one scan.
`);

function onePassAggregate(rows) {
    let count = 0;
    let totalQuantity = 0;
    let totalRevenue = 0;
    let minimumQuantity = null;
    let maximumQuantity = null;

    for (const row of rows) {
        const quantity = row.quantity;
        const revenue = row.quantity * row.unitPrice;

        count += 1;
        totalQuantity += quantity;
        totalRevenue += revenue;

        if (minimumQuantity === null || quantity < minimumQuantity) {
            minimumQuantity = quantity;
        }

        if (maximumQuantity === null || quantity > maximumQuantity) {
            maximumQuantity = quantity;
        }
    }

    return {
        count,
        totalQuantity,
        averageQuantity: count === 0 ? null : totalQuantity / count,
        minimumQuantity,
        maximumQuantity,
        totalRevenue
    };
}

printObject(onePassAggregate(sales));


// -----------------------------------------------------------------------------
// 28. Complexity
// -----------------------------------------------------------------------------

printTitle("27. Complexity of the One-Pass Aggregate");

console.log(`
For n input rows:

Time complexity: O(n)
Additional aggregation space: O(1)

This is efficient because each input row is processed once and only a
constant number of running variables are maintained.

Grouping changes the space requirement because groups must be stored.
A grouped aggregation is commonly O(n) additional space in an in-memory
implementation, depending on the number of distinct groups.
`);


// -----------------------------------------------------------------------------
// 29. Duplicate join problem
// -----------------------------------------------------------------------------

printTitle("28. Join Cardinality and Duplicate Aggregates");

const customerTags = [
    { customerId: 1, tag: "VIP" },
    { customerId: 1, tag: "Technology" },
    { customerId: 2, tag: "Enterprise" }
];

const joinedRows = [];

for (const sale of sales) {
    const matchingTags = customerTags.filter(
        tag => tag.customerId === sale.customerId
    );

    if (matchingTags.length === 0) {
        joinedRows.push({ sale, tag: null });
    } else {
        for (const tag of matchingTags) {
            joinedRows.push({ sale, tag });
        }
    }
}

const originalCustomerOneRevenue = sum(
    sales
        .filter(sale => sale.customerId === 1)
        .map(sale => sale.quantity * sale.unitPrice)
);

const joinedCustomerOneRevenue = sum(
    joinedRows
        .filter(row => row.sale.customerId === 1)
        .map(row => row.sale.quantity * row.sale.unitPrice)
);

printObject({
    originalCustomerOneRevenue,
    joinedCustomerOneRevenue
});

console.log(
    "\nA one-to-many join can multiply rows before aggregation. " +
    "Aggregation must be designed around the intended grain."
);


// -----------------------------------------------------------------------------
// 30. Defensive aggregate API
// -----------------------------------------------------------------------------

printTitle("29. Defensive Aggregate API");

function safeAverage(values) {
    const numericValues = values.filter(
        value => typeof value === "number" && Number.isFinite(value)
    );

    return numericValues.length === 0
        ? null
        : sum(numericValues) / numericValues.length;
}

function safeSum(values) {
    const numericValues = values.filter(
        value => typeof value === "number" && Number.isFinite(value)
    );

    return sum(numericValues);
}

const mixedValues = [10, null, 20, undefined, 30, NaN, "40"];

printObject({
    safeSum: safeSum(mixedValues),
    safeAverage: safeAverage(mixedValues),
    countOriginal: mixedValues.length,
    countNumeric: mixedValues.filter(
        value => typeof value === "number" && Number.isFinite(value)
    ).length
});


// -----------------------------------------------------------------------------
// 31. Assertions
// -----------------------------------------------------------------------------

printTitle("30. Verification Tests");

console.assert(
    countRows([1, 2, 3]) === 3,
    "COUNT test failed"
);

console.assert(
    countNonNull([1, null, 2]) === 2,
    "COUNT(non-null) test failed"
);

console.assert(
    sum([1, 2, 3]) === 6,
    "SUM test failed"
);

console.assert(
    average([10, 20, 30]) === 20,
    "AVG test failed"
);

console.assert(
    minimum([7, 2, 9]) === 2,
    "MIN test failed"
);

console.assert(
    maximum([7, 2, 9]) === 9,
    "MAX test failed"
);

console.assert(
    average([]) === null,
    "Empty AVG test failed"
);

console.assert(
    countDistinct([1, 1, 2, 3]) === 3,
    "COUNT DISTINCT test failed"
);

console.log("All aggregate tests passed.");


// -----------------------------------------------------------------------------
// 32. Final integrated report
// -----------------------------------------------------------------------------

printTitle("31. Integrated Executive Dashboard");

const finalAnalytics = new SalesAnalytics(sales);

const finalReport = {
    transactionLines: sales.length,
    activeCustomers: finalAnalytics.uniqueCustomers(),
    productsSold: finalAnalytics.uniqueProducts(),
    unitsSold: finalAnalytics.totalUnits(),
    averageUnitsPerLine: round(
        average(sales.map(sale => sale.quantity))
    ),
    minimumUnitsPerLine: minimum(
        sales.map(sale => sale.quantity)
    ),
    maximumUnitsPerLine: maximum(
        sales.map(sale => sale.quantity)
    ),
    grossRevenue: round(finalAnalytics.grossRevenue()),
    totalDiscounts: round(finalAnalytics.discounts()),
    netRevenue: round(finalAnalytics.netRevenue())
};

printObject(finalReport);


// -----------------------------------------------------------------------------
// 33. Conceptual checklist
// -----------------------------------------------------------------------------

printTitle("32. Aggregate Function Checklist");

const checklist = [
    ["COUNT(*) counts rows", true],
    ["COUNT(column) ignores NULL", true],
    ["COUNT(DISTINCT column) counts unique values", true],
    ["SUM adds values", true],
    ["AVG calculates the mean", true],
    ["MIN returns the smallest value", true],
    ["MAX returns the largest value", true],
    ["GROUP BY creates independent groups", true],
    ["WHERE filters rows before grouping", true],
    ["HAVING filters groups after aggregation", true],
    ["NULL and zero have different meanings", true],
    ["DISTINCT changes the aggregate input", true],
    ["Join cardinality can change aggregate results", true],
    ["Window-style aggregation preserves row-level detail", true],
    ["Large datasets require performance planning", true]
];

for (const [concept, verified] of checklist) {
    console.log(`[${verified ? "PASS" : "FAIL"}] ${concept}`);
}

console.log("\nAggregate study completed.");
