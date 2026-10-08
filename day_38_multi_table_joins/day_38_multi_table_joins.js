/**
 * Multi-Table JOINs using Node.js and SQLite-like relational workflow modeling.
 *
 * This file uses an in-memory relational dataset and a small query engine
 * written with JavaScript arrays. The implementation deliberately exposes
 * the mechanics of joining three or more relations, rather than requiring
 * an npm dependency.
 *
 * Run with:
 *     node multi-table-joins.js
 *
 * The data model is:
 *     regions -> customers -> orders -> orderItems -> products
 *
 * This mirrors a relational schema while allowing the file to remain
 * executable with the Node.js standard runtime.
 */

"use strict";

const regions = [
  { regionId: 1, regionName: "North" },
  { regionId: 2, regionName: "South" },
  { regionId: 3, regionName: "West" },
  { regionId: 4, regionName: "East" }
];

const customers = [
  { customerId: 101, customerName: "Aarav Systems", regionId: 1 },
  { customerId: 102, customerName: "Bharat Logistics", regionId: 2 },
  { customerId: 103, customerName: "Civic Research Lab", regionId: 3 },
  { customerId: 104, customerName: "Delta Manufacturing", regionId: 1 },
  { customerId: 105, customerName: "Eastern Retail Group", regionId: 4 }
];

const products = [
  { productId: 201, productName: "Edge Sensor", category: "IoT", unitPrice: 120 },
  { productId: 202, productName: "Gateway Pro", category: "Networking", unitPrice: 450 },
  { productId: 203, productName: "Analytics License", category: "Software", unitPrice: 800 },
  { productId: 204, productName: "Secure Router", category: "Networking", unitPrice: 600 },
  { productId: 205, productName: "Inspection Camera", category: "Vision", unitPrice: 950 }
];

const orders = [
  { orderId: 1001, customerId: 101, orderDate: "2026-09-01", status: "DELIVERED" },
  { orderId: 1002, customerId: 101, orderDate: "2026-09-14", status: "SHIPPED" },
  { orderId: 1003, customerId: 102, orderDate: "2026-09-18", status: "DELIVERED" },
  { orderId: 1004, customerId: 103, orderDate: "2026-09-20", status: "CANCELLED" },
  { orderId: 1005, customerId: 104, orderDate: "2026-09-22", status: "DELIVERED" },
  { orderId: 1006, customerId: 105, orderDate: "2026-09-24", status: "PLACED" }
];

const orderItems = [
  { orderId: 1001, productId: 201, quantity: 10, unitPrice: 120 },
  { orderId: 1001, productId: 202, quantity: 2, unitPrice: 450 },
  { orderId: 1002, productId: 203, quantity: 1, unitPrice: 800 },
  { orderId: 1002, productId: 201, quantity: 5, unitPrice: 120 },
  { orderId: 1003, productId: 204, quantity: 3, unitPrice: 600 },
  { orderId: 1003, productId: 201, quantity: 20, unitPrice: 120 },
  { orderId: 1004, productId: 205, quantity: 1, unitPrice: 950 },
  { orderId: 1005, productId: 205, quantity: 4, unitPrice: 950 },
  { orderId: 1005, productId: 203, quantity: 2, unitPrice: 800 },
  { orderId: 1006, productId: 202, quantity: 1, unitPrice: 450 }
];

function innerJoin(leftRows, rightRows, matches) {
  const output = [];

  for (const left of leftRows) {
    for (const right of rightRows) {
      if (matches(left, right)) {
        output.push({ ...left, ...right });
      }
    }
  }

  return output;
}

function leftJoin(leftRows, rightRows, matches, rightFactory = () => ({})) {
  const output = [];

  for (const left of leftRows) {
    const matchesForLeft = rightRows.filter((right) => matches(left, right));

    if (matchesForLeft.length === 0) {
      output.push({ ...left, ...rightFactory() });
      continue;
    }

    for (const right of matchesForLeft) {
      output.push({ ...left, ...right });
    }
  }

  return output;
}

function groupBy(rows, keySelector) {
  const groups = new Map();

  for (const row of rows) {
    const key = keySelector(row);

    if (!groups.has(key)) {
      groups.set(key, []);
    }

    groups.get(key).push(row);
  }

  return groups;
}

function printRows(title, rows, fields) {
  console.log(`\n=== ${title} ===`);

  if (rows.length === 0) {
    console.log("(no rows)");
    return;
  }

  console.table(
    rows.map((row) => {
      const result = {};
      for (const field of fields) {
        result[field] = row[field];
      }
      return result;
    })
  );
}

function buildFiveTableJoin() {
  const regionCustomers = innerJoin(
    regions,
    customers,
    (region, customer) => region.regionId === customer.regionId
  ).map(({ regionId, ...row }) => row);

  const customerOrders = innerJoin(
    regionCustomers,
    orders,
    (row, order) => row.customerId === order.customerId
  );

  const orderLines = innerJoin(
    customerOrders,
    orderItems,
    (row, item) => row.orderId === item.orderId
  );

  const completeRows = innerJoin(
    orderLines,
    products,
    (row, product) => row.productId === product.productId
  );

  return completeRows
    .filter((row) => row.status !== "CANCELLED")
    .map((row) => ({
      regionName: row.regionName,
      customerName: row.customerName,
      orderId: row.orderId,
      productName: row.productName,
      quantity: row.quantity,
      lineValue: row.quantity * row.unitPrice
    }));
}

function demonstrateManyToManyBridge() {
  const productOrderRows = innerJoin(
    products,
    orderItems,
    (product, item) => product.productId === item.productId
  );

  const completedLines = innerJoin(
    productOrderRows,
    orders,
    (row, order) =>
      row.orderId === order.orderId && order.status !== "CANCELLED"
  );

  const groups = groupBy(completedLines, (row) => row.productId);

  const result = [];

  for (const rows of groups.values()) {
    const first = rows[0];
    const orderIds = new Set(rows.map((row) => row.orderId));
    const unitsSold = rows.reduce((sum, row) => sum + row.quantity, 0);
    const revenue = rows.reduce(
      (sum, row) => sum + row.quantity * row.unitPrice,
      0
    );

    result.push({
      productName: first.productName,
      distinctOrders: orderIds.size,
      unitsSold,
      revenue: Number(revenue.toFixed(2))
    });
  }

  return result.sort((a, b) => b.revenue - a.revenue);
}

function demonstrateLeftJoin() {
  const rows = leftJoin(
    customers,
    orders,
    (customer, order) => customer.customerId === order.customerId,
    () => ({ orderId: null, status: null })
  );

  const groups = groupBy(rows, (row) => row.customerId);

  return [...groups.values()].map((customerRows) => ({
    customerName: customerRows[0].customerName,
    orderCount: customerRows.filter((row) => row.orderId !== null).length
  }));
}

function demonstrateJoinOrder() {
  const customerFirst = innerJoin(
    innerJoin(customers, orders, (c, o) => c.customerId === o.customerId),
    orderItems,
    (row, item) => row.orderId === item.orderId
  );

  const productFirst = innerJoin(
    innerJoin(orderItems, products, (item, product) => item.productId === product.productId),
    orders,
    (row, order) => row.orderId === order.orderId
  );

  const normalizeCustomerFirst = customerFirst
    .map((row) => `${row.customerId}:${row.orderId}:${row.productId}`)
    .sort();

  const normalizeProductFirst = productFirst
    .map((row) => `${row.customerId}:${row.orderId}:${row.productId}`)
    .sort();

  return normalizeCustomerFirst.join("|") === normalizeProductFirst.join("|");
}

function validateRelationshipIntegrity() {
  const customerIds = new Set(customers.map((customer) => customer.customerId));
  const productIds = new Set(products.map((product) => product.productId));
  const orderIds = new Set(orders.map((order) => order.orderId));

  const invalidOrders = orders.filter(
    (order) => !customerIds.has(order.customerId)
  );

  const invalidItems = orderItems.filter(
    (item) => !orderIds.has(item.orderId) || !productIds.has(item.productId)
  );

  return {
    invalidOrders,
    invalidItems,
    valid: invalidOrders.length === 0 && invalidItems.length === 0
  };
}

async function asynchronousRepositoryQuery(customerId) {
  /*
   * Promise-based functions model the asynchronous behavior common in
   * JavaScript database drivers. Each stage represents a dependent query
   * operation, even though this example uses local arrays.
   */
  return Promise.resolve(
    customers.filter((customer) => customer.customerId === customerId)
  ).then((matchingCustomers) => {
    if (matchingCustomers.length === 0) {
      throw new Error(`Customer ${customerId} does not exist`);
    }

    return Promise.resolve(
      orders.filter((order) => order.customerId === customerId)
    );
  }).then((customerOrders) => {
    const orderIds = new Set(customerOrders.map((order) => order.orderId));

    return {
      customerOrders,
      customerItems: orderItems.filter((item) => orderIds.has(item.orderId))
    };
  });
}

async function main() {
  const completeRows = buildFiveTableJoin();

  printRows(
    "Five-table join",
    completeRows,
    [
      "regionName",
      "customerName",
      "orderId",
      "productName",
      "quantity",
      "lineValue"
    ]
  );

  printRows(
    "LEFT JOIN semantics",
    demonstrateLeftJoin(),
    ["customerName", "orderCount"]
  );

  printRows(
    "Many-to-many bridge aggregation",
    demonstrateManyToManyBridge(),
    ["productName", "distinctOrders", "unitsSold", "revenue"]
  );

  console.log("\n=== Join-order reasoning ===");
  console.log(`Equivalent inner-join result: ${demonstrateJoinOrder()}`);

  console.log("\n=== Relationship validation ===");
  console.log(validateRelationshipIntegrity());

  console.log("\n=== Asynchronous dependent query ===");
  try {
    const result = await asynchronousRepositoryQuery(101);
    console.log({
      orderCount: result.customerOrders.length,
      lineCount: result.customerItems.length
    });
  } catch (error) {
    console.error(error.message);
  }

  console.log("\n=== Failure condition ===");
  try {
    await asynchronousRepositoryQuery(999);
  } catch (error) {
    console.error(`Expected validation failure: ${error.message}`);
  }
}

main().catch((error) => {
  console.error("Unhandled application failure:", error);
  process.exitCode = 1;
});
