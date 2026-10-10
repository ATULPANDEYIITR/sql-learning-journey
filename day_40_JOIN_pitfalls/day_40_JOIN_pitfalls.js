/**
 * JOIN Pitfalls in JavaScript
 *
 * This Node.js program models a pull of relational data into application
 * memory and demonstrates how incorrect join assumptions produce duplicate
 * records, Cartesian products, NULL-like behavior, and misleading reports.
 *
 * The implementation uses JavaScript-specific structures and an event-driven
 * audit stream rather than translating the Python implementation line by line.
 */

"use strict";

const { EventEmitter } = require("node:events");

const customers = [
  { customerId: 1, name: "Asha", region: "North" },
  { customerId: 2, name: "Ravi", region: "South" },
  { customerId: 3, name: "Meera", region: null }
];

const orders = [
  { orderId: 1001, customerId: 1, amount: 250, status: "PAID" },
  { orderId: 1002, customerId: 1, amount: 125, status: "PAID" },
  { orderId: 1003, customerId: 2, amount: 500, status: "PENDING" },
  { orderId: 1004, customerId: null, amount: 90, status: "PENDING" }
];

const reviewEvents = new EventEmitter();

reviewEvents.on("joinAudit", (event) => {
  console.log(
    `[JOIN AUDIT] ${event.name}: ` +
    `left=${event.leftRows}, right=${event.rightRows}, result=${event.resultRows}`
  );
});

function hashJoin(left, right, leftKey, rightKey, options = {}) {
  const {
    nullsMatch = false,
    label = "hashJoin"
  } = options;

  const index = new Map();

  for (const row of right) {
    const key = rightKey(row);

    if (key === null || key === undefined) {
      if (!nullsMatch) {
        continue;
      }
    }

    if (!index.has(key)) {
      index.set(key, []);
    }

    index.get(key).push(row);
  }

  const result = [];

  for (const leftRow of left) {
    const key = leftKey(leftRow);

    if ((key === null || key === undefined) && !nullsMatch) {
      continue;
    }

    const matches = index.get(key) ?? [];

    for (const rightRow of matches) {
      result.push({
        ...leftRow,
        ...Object.fromEntries(
          Object.entries(rightRow).map(([column, value]) => [
            `right_${column}`,
            value
          ])
        )
      });
    }
  }

  reviewEvents.emit("joinAudit", {
    name: label,
    leftRows: left.length,
    rightRows: right.length,
    resultRows: result.length
  });

  return result;
}

function leftHashJoin(left, right, leftKey, rightKey) {
  const index = new Map();
  const rightColumns = new Set();

  for (const row of right) {
    const key = rightKey(row);

    if (!index.has(key)) {
      index.set(key, []);
    }

    index.get(key).push(row);

    for (const column of Object.keys(row)) {
      rightColumns.add(column);
    }
  }

  const result = [];

  for (const leftRow of left) {
    const key = leftKey(leftRow);
    const matches = index.get(key) ?? [];

    if (matches.length === 0) {
      const unmatched = { ...leftRow };

      for (const column of rightColumns) {
        unmatched[`right_${column}`] = null;
      }

      result.push(unmatched);
      continue;
    }

    for (const rightRow of matches) {
      result.push({
        ...leftRow,
        ...Object.fromEntries(
          Object.entries(rightRow).map(([column, value]) => [
            `right_${column}`,
            value
          ])
        )
      });
    }
  }

  reviewEvents.emit("joinAudit", {
    name: "leftHashJoin",
    leftRows: left.length,
    rightRows: right.length,
    resultRows: result.length
  });

  return result;
}

function crossJoin(left, right) {
  const result = [];

  for (const leftRow of left) {
    for (const rightRow of right) {
      result.push({
        ...leftRow,
        ...Object.fromEntries(
          Object.entries(rightRow).map(([column, value]) => [
            `right_${column}`,
            value
          ])
        )
      });
    }
  }

  reviewEvents.emit("joinAudit", {
    name: "crossJoin",
    leftRows: left.length,
    rightRows: right.length,
    resultRows: result.length
  });

  return result;
}

function printTable(title, rows) {
  console.log(`\n=== ${title} ===`);
  console.table(rows);
}

function demonstrateOneToMany() {
  const result = hashJoin(
    customers,
    orders,
    row => row.customerId,
    row => row.customerId,
    { label: "customer-to-order" }
  );

  printTable("Legitimate one-to-many relationship", result);

  console.log(
    "Customer 1 appears twice because two distinct orders belong to it. " +
    "The repeated customer data is a consequence of result grain."
  );
}

function demonstrateCartesianProduct() {
  const regions = [
    { regionId: 1, region: "North" },
    { regionId: 2, region: "South" },
    { regionId: 3, region: "West" }
  ];

  const salesChannels = [
    { channelId: "WEB", channel: "Web" },
    { channelId: "STORE", channel: "Store" }
  ];

  const result = crossJoin(regions, salesChannels);

  printTable("Accidental Cartesian product", result);

  const expected = regions.length * salesChannels.length;

  console.log(`Cartesian cardinality: ${expected}`);
}

function demonstrateWrongJoinKey() {
  const accounts = [
    { accountId: 101, customerId: 1, region: "North" },
    { accountId: 102, customerId: 2, region: "North" },
    { accountId: 103, customerId: 3, region: "South" }
  ];

  const invoices = [
    { invoiceId: 5001, customerId: 1, region: "North" },
    { invoiceId: 5002, customerId: 2, region: "North" },
    { invoiceId: 5003, customerId: 3, region: "South" }
  ];

  const correct = hashJoin(
    accounts,
    invoices,
    row => row.customerId,
    row => row.customerId,
    { label: "customer-id join" }
  );

  const incorrect = hashJoin(
    accounts,
    invoices,
    row => row.region,
    row => row.region,
    { label: "region-only join" }
  );

  printTable("Correct key", correct);
  printTable("Incorrect non-unique key", incorrect);
}

function demonstrateNullSemantics() {
  const left = [
    { id: 1, reference: null },
    { id: 2, reference: "A" }
  ];

  const right = [
    { code: 10, reference: null },
    { code: 11, reference: "A" }
  ];

  const sqlLike = hashJoin(
    left,
    right,
    row => row.reference,
    row => row.reference,
    { label: "SQL-like NULL join", nullsMatch: false }
  );

  const applicationSpecific = hashJoin(
    left,
    right,
    row => row.reference,
    row => row.reference,
    { label: "application NULL-as-value join", nullsMatch: true }
  );

  printTable("SQL-like equality semantics", sqlLike);
  printTable("Explicit NULL-as-equal application rule", applicationSpecific);

  console.log(
    "JavaScript Map can treat null as a normal key, but SQL equality " +
    "does not match NULL to NULL. Application code must not silently assume " +
    "that in-memory behavior is identical to database semantics."
  );
}

function demonstrateLeftJoinFilterProblem() {
  const result = leftHashJoin(
    customers,
    orders,
    row => row.customerId,
    row => row.customerId
  );

  const paidAfterJoin = result.filter(
    row => row.right_status === "PAID"
  );

  printTable("LEFT JOIN result", result);
  printTable(
    "Filtering the nullable right side after the join",
    paidAfterJoin
  );

  console.log(
    "Customers without matching orders disappear when a post-join filter " +
    "requires a right-side value. In SQL, moving the predicate into the " +
    "JOIN condition can preserve unmatched left rows."
  );
}

function demonstratePreAggregation() {
  const totals = new Map();

  for (const order of orders) {
    if (order.customerId === null) {
      continue;
    }

    const current = totals.get(order.customerId) ?? 0;
    totals.set(order.customerId, current + order.amount);
  }

  const customerSummary = customers.map(customer => ({
    customerId: customer.customerId,
    name: customer.name,
    totalOrderValue: totals.get(customer.customerId) ?? 0
  }));

  printTable("Customer-grain result after pre-aggregation", customerSummary);
}

function demonstrateCardinalityAssertion() {
  const customerProfiles = [
    { customerId: 1, risk: "LOW" },
    { customerId: 2, risk: "MEDIUM" },
    { customerId: 3, risk: "HIGH" }
  ];

  const joined = hashJoin(
    customers,
    customerProfiles,
    row => row.customerId,
    row => row.customerId,
    { label: "one-to-one profile join" }
  );

  if (joined.length !== customers.length) {
    throw new Error(
      "Expected one profile per customer, but join cardinality changed."
    );
  }

  const ids = joined.map(row => row.customerId);
  const uniqueIds = new Set(ids);

  if (uniqueIds.size !== ids.length) {
    throw new Error("Duplicate customer IDs detected after expected 1:1 join.");
  }

  printTable("Cardinality-validated join", joined);
}

function demonstrateManyToManyExplosion() {
  const ordersForCustomer = [
    { orderId: 1, customerId: 1 },
    { orderId: 2, customerId: 1 }
  ];

  const promotionsForCustomer = [
    { promotionId: "P1", customerId: 1 },
    { promotionId: "P2", customerId: 1 },
    { promotionId: "P3", customerId: 1 }
  ];

  const result = hashJoin(
    ordersForCustomer,
    promotionsForCustomer,
    row => row.customerId,
    row => row.customerId,
    { label: "order-promotion many-to-many join" }
  );

  printTable("Many-to-many multiplication", result);

  console.log(
    `2 orders × 3 promotions = ${result.length} result rows. ` +
    "DISTINCT would not define the missing business relationship."
  );
}

function demonstrateAsyncJoinAudit() {
  return new Promise(resolve => {
    setImmediate(() => {
      const result = hashJoin(
        customers,
        orders,
        row => row.customerId,
        row => row.customerId,
        { label: "asynchronous audit join" }
      );

      console.log(
        `Asynchronous processing completed with ${result.length} rows.`
      );

      resolve();
    });
  });
}

async function main() {
  console.log("JOIN PITFALLS LAB");
  console.log("=================");

  demonstrateOneToMany();
  demonstrateCartesianProduct();
  demonstrateWrongJoinKey();
  demonstrateNullSemantics();
  demonstrateLeftJoinFilterProblem();
  demonstratePreAggregation();
  demonstrateCardinalityAssertion();
  demonstrateManyToManyExplosion();

  await demonstrateAsyncJoinAudit();

  console.log("\nProduction diagnostic rule:");
  console.log(
    "Record the expected grain and cardinality before executing a join. " +
    "Measure the result, inspect key uniqueness, and investigate unexpected " +
    "multiplication before applying DISTINCT."
  );
}

main().catch(error => {
  console.error("JOIN analysis failed:", error.message);
  process.exitCode = 1;
});
