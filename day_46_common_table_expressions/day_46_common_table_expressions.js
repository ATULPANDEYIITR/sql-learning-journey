"use strict";

/*
 * Common Table Expressions are a SQL feature, but JavaScript can model
 * the same query-architecture idea using named transformation stages.
 *
 * The implementation intentionally uses JavaScript-specific capabilities:
 * immutable objects, Map, Set, array transformations, async execution,
 * validation, and an event-driven reporting pipeline.
 */

const customers = Object.freeze([
  Object.freeze({ id: 1, name: "Asha", region: "North" }),
  Object.freeze({ id: 2, name: "Ravi", region: "South" }),
  Object.freeze({ id: 3, name: "Meera", region: "West" }),
  Object.freeze({ id: 4, name: "Kabir", region: "East" })
]);

const orders = Object.freeze([
  Object.freeze({ id: 101, customerId: 1, date: "2026-01-05", status: "completed", amount: 1200 }),
  Object.freeze({ id: 102, customerId: 1, date: "2026-01-20", status: "completed", amount: 800 }),
  Object.freeze({ id: 103, customerId: 1, date: "2026-02-03", status: "cancelled", amount: 500 }),
  Object.freeze({ id: 104, customerId: 2, date: "2026-01-08", status: "completed", amount: 1500 }),
  Object.freeze({ id: 105, customerId: 2, date: "2026-02-12", status: "completed", amount: 2200 }),
  Object.freeze({ id: 106, customerId: 3, date: "2026-01-10", status: "completed", amount: 700 }),
  Object.freeze({ id: 107, customerId: 3, date: "2026-02-18", status: "completed", amount: 900 }),
  Object.freeze({ id: 108, customerId: 4, date: "2026-01-12", status: "completed", amount: 3000 })
]);

function validateOrders(source) {
  if (!Array.isArray(source)) {
    throw new TypeError("Orders must be an array.");
  }

  for (const order of source) {
    if (!Number.isInteger(order.id)) {
      throw new TypeError("Every order must have an integer id.");
    }

    if (!Number.isFinite(order.amount) || order.amount < 0) {
      throw new RangeError(`Invalid amount for order ${order.id}.`);
    }

    if (!["completed", "cancelled"].includes(order.status)) {
      throw new RangeError(`Invalid status for order ${order.id}.`);
    }
  }
}

function completedOrders(source) {
  return source.filter(order => order.status === "completed");
}

function customerTotals(source) {
  const totals = new Map();

  for (const order of source) {
    totals.set(
      order.customerId,
      (totals.get(order.customerId) ?? 0) + order.amount
    );
  }

  return totals;
}

function qualifiedCustomers(customerRows, totals, minimum) {
  if (!Number.isFinite(minimum) || minimum < 0) {
    throw new RangeError("Minimum sales must be a non-negative number.");
  }

  return customerRows
    .filter(customer => (totals.get(customer.id) ?? 0) >= minimum)
    .map(customer => ({
      customerId: customer.id,
      customer: customer.name,
      region: customer.region,
      completedSales: totals.get(customer.id) ?? 0
    }));
}

function monthlyRevenue(source) {
  const revenue = new Map();

  for (const order of source) {
    const month = order.date.slice(0, 7);
    revenue.set(month, (revenue.get(month) ?? 0) + order.amount);
  }

  return [...revenue.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, amount]) => ({ month, amount }));
}

/*
 * A SQL CTE is scoped to the statement. The event emitter below provides
 * a different JavaScript perspective: named stages emit intermediate
 * results without making each stage responsible for the entire report.
 */
class QueryPipeline {
  #listeners = new Map();

  on(stage, listener) {
    if (!this.#listeners.has(stage)) {
      this.#listeners.set(stage, []);
    }
    this.#listeners.get(stage).push(listener);
  }

  emit(stage, value) {
    for (const listener of this.#listeners.get(stage) ?? []) {
      listener(value);
    }
  }

  execute(source, minimum) {
    const filtered = completedOrders(source);
    this.emit("completed_orders", filtered);

    const totals = customerTotals(filtered);
    this.emit("customer_totals", totals);

    const qualified = qualifiedCustomers(customers, totals, minimum);
    this.emit("qualified_customers", qualified);

    return qualified;
  }
}

async function executeAsynchronousReport() {
  /*
   * JavaScript applications often receive data asynchronously. The CTE
   * itself remains a database-side construct, while this function models
   * how an application can consume a multi-stage database result.
   */
  await new Promise(resolve => setTimeout(resolve, 10));
  validateOrders(orders);

  const pipeline = new QueryPipeline();

  pipeline.on("completed_orders", rows => {
    console.log(`Completed-order stage: ${rows.length} rows`);
  });

  pipeline.on("customer_totals", totals => {
    console.log(`Aggregation stage: ${totals.size} customers`);
  });

  pipeline.on("qualified_customers", rows => {
    console.log(`Qualification stage: ${rows.length} customers`);
  });

  const report = pipeline.execute(orders, 2000);

  console.log("\nQualified customer report");
  console.table(report);

  console.log("\nMonthly revenue derived from the filtered relation");
  console.table(monthlyRevenue(completedOrders(orders)));
}

function recursiveHierarchy(employees, rootId) {
  const children = new Map();

  for (const employee of employees) {
    const managerId = employee.managerId;
    if (!children.has(managerId)) {
      children.set(managerId, []);
    }
    children.get(managerId).push(employee);
  }

  const result = [];
  const queue = [...(employees.filter(employee => employee.id === rootId))];

  while (queue.length > 0) {
    const current = queue.shift();
    result.push(current);

    for (const child of children.get(current.id) ?? []) {
      queue.push(child);
    }
  }

  return result;
}

async function main() {
  console.log("Common Table Expression Query Architecture");
  console.log("==========================================");

  await executeAsynchronousReport();

  const employees = [
    { id: 1, name: "Director", managerId: null },
    { id: 2, name: "Engineering Lead", managerId: 1 },
    { id: 3, name: "Data Lead", managerId: 1 },
    { id: 4, name: "Backend Engineer", managerId: 2 },
    { id: 5, name: "Data Engineer", managerId: 3 }
  ];

  console.log("\nRecursive-CTE-style hierarchy traversal");
  console.table(recursiveHierarchy(employees, 1));

  try {
    validateOrders([{ id: 900, customerId: 1, date: "2026-03-01", status: "unknown", amount: 10 }]);
  } catch (error) {
    console.log("\nValidation failure:", error.message);
  }

  console.log("\nThe database-side CTE remains preferable when the intermediate");
  console.log("relations are intended to be computed close to the data.");
}

main().catch(error => {
  console.error("Report execution failed:", error);
  process.exitCode = 1;
});
