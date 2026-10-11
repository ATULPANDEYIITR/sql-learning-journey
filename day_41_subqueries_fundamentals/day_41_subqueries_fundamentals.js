"use strict";

/*
 * Subqueries Fundamentals in JavaScript
 *
 * This file builds a small in-memory relational query model using arrays,
 * Sets, higher-order functions, and explicit validation. It focuses on the
 * semantics of scalar, single-row, multi-row, correlated, EXISTS, and
 * table-style subqueries without requiring an external database package.
 *
 * The implementation deliberately uses JavaScript-specific patterns:
 * immutable data records, Set membership, Array transformations, closures,
 * asynchronous policy evaluation, and event-driven workflow processing.
 */

const departments = Object.freeze([
  Object.freeze({ id: 10, name: "Engineering" }),
  Object.freeze({ id: 20, name: "Finance" }),
  Object.freeze({ id: 30, name: "Operations" }),
  Object.freeze({ id: 40, name: "Security" }),
  Object.freeze({ id: 50, name: "Research" }),
]);

const employees = Object.freeze([
  Object.freeze({ id: 101, name: "Aarav", departmentId: 10, salary: 92000 }),
  Object.freeze({ id: 102, name: "Diya", departmentId: 10, salary: 108000 }),
  Object.freeze({ id: 103, name: "Kabir", departmentId: 10, salary: 125000 }),
  Object.freeze({ id: 104, name: "Meera", departmentId: 20, salary: 85000 }),
  Object.freeze({ id: 105, name: "Rohan", departmentId: 20, salary: 97000 }),
  Object.freeze({ id: 106, name: "Ishita", departmentId: 30, salary: 76000 }),
  Object.freeze({ id: 107, name: "Vihaan", departmentId: 30, salary: 89000 }),
  Object.freeze({ id: 108, name: "Anaya", departmentId: 40, salary: 118000 }),
  Object.freeze({ id: 109, name: "Arjun", departmentId: 40, salary: 131000 }),
  Object.freeze({ id: 110, name: "Sara", departmentId: 50, salary: 112000 }),
]);

const projects = Object.freeze([
  Object.freeze({ id: 201, name: "Payment Platform", departmentId: 10 }),
  Object.freeze({ id: 202, name: "Cloud Migration", departmentId: 10 }),
  Object.freeze({ id: 203, name: "Risk Analytics", departmentId: 20 }),
  Object.freeze({ id: 204, name: "Supply Optimization", departmentId: 30 }),
  Object.freeze({ id: 205, name: "Threat Detection", departmentId: 40 }),
  Object.freeze({ id: 206, name: "Quantum Research", departmentId: 50 }),
]);

const assignments = Object.freeze([
  Object.freeze({ employeeId: 101, projectId: 201, hours: 120 }),
  Object.freeze({ employeeId: 101, projectId: 202, hours: 80 }),
  Object.freeze({ employeeId: 102, projectId: 201, hours: 160 }),
  Object.freeze({ employeeId: 103, projectId: 201, hours: 180 }),
  Object.freeze({ employeeId: 103, projectId: 202, hours: 90 }),
  Object.freeze({ employeeId: 104, projectId: 203, hours: 150 }),
  Object.freeze({ employeeId: 105, projectId: 203, hours: 175 }),
  Object.freeze({ employeeId: 106, projectId: 204, hours: 120 }),
  Object.freeze({ employeeId: 107, projectId: 204, hours: 190 }),
  Object.freeze({ employeeId: 108, projectId: 205, hours: 170 }),
  Object.freeze({ employeeId: 109, projectId: 205, hours: 210 }),
  Object.freeze({ employeeId: 110, projectId: 206, hours: 200 }),
]);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function print(title, rows) {
  console.log(`\n--- ${title} ---`);
  if (rows.length === 0) {
    console.log("(no rows)");
    return;
  }

  for (const row of rows) {
    console.log(JSON.stringify(row));
  }
}

function scalarSubquery(query) {
  const result = query();

  if (result.length !== 1) {
    throw new Error(
      `Scalar subquery expected exactly one row but received ${result.length}.`
    );
  }

  return result[0];
}

function optionalScalarSubquery(query) {
  const result = query();

  if (result.length > 1) {
    throw new Error(
      `Scalar subquery expected zero or one row but received ${result.length}.`
    );
  }

  return result.length === 0 ? null : result[0];
}

function singleRowDepartmentByName(name) {
  return scalarSubquery(() =>
    departments
      .filter((department) => department.name === name)
      .map((department) => department.id)
  );
}

function multiRowDepartmentIds(names) {
  return departments
    .filter((department) => names.includes(department.name))
    .map((department) => department.id);
}

function average(values) {
  assert(values.length > 0, "Cannot calculate an average of an empty set.");
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function companyAverageSalary() {
  return scalarSubquery(() => [
    average(employees.map((employee) => employee.salary)),
  ]);
}

function employeesAboveCompanyAverage() {
  const threshold = companyAverageSalary();

  return employees
    .filter((employee) => employee.salary > threshold)
    .map((employee) => ({
      name: employee.name,
      salary: employee.salary,
      companyAverage: threshold,
    }));
}

function employeesInSelectedDepartments() {
  const selectedIds = new Set(
    multiRowDepartmentIds(["Engineering", "Security", "Research"])
  );

  return employees
    .filter((employee) => selectedIds.has(employee.departmentId))
    .map((employee) => employee.name);
}

function existsSubquery(employeeId, predicate) {
  return assignments.some(
    (assignment) =>
      assignment.employeeId === employeeId && predicate(assignment)
  );
}

function employeesWithHeavyProjectAssignment() {
  return employees
    .filter((employee) =>
      existsSubquery(employee.id, (assignment) => assignment.hours >= 180)
    )
    .map((employee) => employee.name);
}

function departmentEmployees(departmentId) {
  return employees.filter(
    (employee) => employee.departmentId === departmentId
  );
}

function correlatedDepartmentAverage(employee) {
  const rowsForDepartment = departmentEmployees(employee.departmentId);
  return average(rowsForDepartment.map((item) => item.salary));
}

function employeesAboveOwnDepartmentAverage() {
  return employees
    .filter(
      (employee) =>
        employee.salary > correlatedDepartmentAverage(employee)
    )
    .map((employee) => ({
      name: employee.name,
      salary: employee.salary,
      departmentAverage: correlatedDepartmentAverage(employee),
    }));
}

function tableSubquery() {
  /*
   * The inner map creates a derived table of department metrics.
   * The outer filter consumes that derived result just as a SQL query can
   * consume a subquery in its FROM clause.
   */
  const derivedDepartmentMetrics = departments.map((department) => {
    const members = departmentEmployees(department.id);

    return {
      departmentId: department.id,
      departmentName: department.name,
      employeeCount: members.length,
      averageSalary:
        members.length === 0
          ? null
          : average(members.map((employee) => employee.salary)),
    };
  });

  return derivedDepartmentMetrics
    .filter((row) => row.employeeCount >= 2)
    .sort((a, b) => b.averageSalary - a.averageSalary);
}

function notExistsDepartmentProjects() {
  return departments
    .filter(
      (department) =>
        !projects.some((project) => project.departmentId === department.id)
    )
    .map((department) => department.name);
}

function nestedSubquery() {
  const engineeringId = singleRowDepartmentByName("Engineering");

  const engineeringAverage = scalarSubquery(() => [
    average(
      employees
        .filter((employee) => employee.departmentId === engineeringId)
        .map((employee) => employee.salary)
    ),
  ]);

  return employees
    .filter((employee) => employee.salary > engineeringAverage)
    .map((employee) => ({
      name: employee.name,
      salary: employee.salary,
      comparisonValue: engineeringAverage,
    }));
}

function subqueryWithAllSemantics() {
  /*
   * JavaScript has no SQL ALL operator. The equivalent condition
   *
   *     value > ALL (set)
   *
   * is represented by every(). For a non-empty Finance salary set,
   * every finance salary must be lower than the employee salary.
   */
  const financeId = singleRowDepartmentByName("Finance");

  const financeSalaries = employees
    .filter((employee) => employee.departmentId === financeId)
    .map((employee) => employee.salary);

  return employees
    .filter((employee) =>
      financeSalaries.every((financeSalary) => employee.salary > financeSalary)
    )
    .map((employee) => employee.name);
}

function subqueryWithAnySemantics() {
  /*
   * SQL's value = ANY(subquery) is naturally represented by some().
   */
  const engineeringId = singleRowDepartmentByName("Engineering");

  const engineeringSalaries = employees
    .filter((employee) => employee.departmentId === engineeringId)
    .map((employee) => employee.salary);

  return employees
    .filter((employee) =>
      engineeringSalaries.some(
        (engineeringSalary) => employee.salary === engineeringSalary
      )
    )
    .map((employee) => employee.name);
}

function demonstrateNullLikeBehavior() {
  /*
   * JavaScript's undefined/null behavior is not identical to SQL NULL.
   * This explicit helper demonstrates why SQL semantics should not be
   * approximated casually in application code.
   */
  const values = [1, 2, null];
  const candidate = 5;

  const directMembership = values.includes(candidate);
  const explicitUnknown = values.some((value) => value === null);

  return {
    candidate,
    values,
    directMembership,
    containsNull: explicitUnknown,
    note:
      "SQL NOT IN with a nullable subquery can become UNKNOWN; application code must model that rule explicitly.",
  };
}

function validateScalarContract() {
  try {
    scalarSubquery(() =>
      departments
        .filter((department) => department.name === "Engineering")
        .map((department) => department.id)
    );

    return "Engineering resolves to one department ID.";
  } catch (error) {
    return error.message;
  }
}

class QueryEventBus {
  #handlers = new Map();

  on(eventName, handler) {
    if (!this.#handlers.has(eventName)) {
      this.#handlers.set(eventName, []);
    }

    this.#handlers.get(eventName).push(handler);
  }

  emit(eventName, payload) {
    const handlers = this.#handlers.get(eventName) ?? [];
    return Promise.all(handlers.map((handler) => handler(payload)));
  }
}

async function asynchronousSubqueryPipeline() {
  /*
   * Real applications often obtain outer and inner datasets asynchronously.
   * Promise.all allows independent lookups to execute concurrently before
   * the outer filtering step consumes the subquery-like result.
   */
  const [securityId, researchId] = await Promise.all([
    Promise.resolve(singleRowDepartmentByName("Security")),
    Promise.resolve(singleRowDepartmentByName("Research")),
  ]);

  const selectedIds = new Set([securityId, researchId]);

  return employees.filter((employee) => selectedIds.has(employee.departmentId));
}

async function eventDrivenSubqueryWorkflow() {
  const bus = new QueryEventBus();

  bus.on("department-analysis-requested", async ({ departmentName }) => {
    const departmentId = optionalScalarSubquery(() =>
      departments
        .filter((department) => department.name === departmentName)
        .map((department) => department.id)
    );

    if (departmentId === null) {
      throw new Error(`Unknown department: ${departmentName}`);
    }

    const members = employees.filter(
      (employee) => employee.departmentId === departmentId
    );

    console.log(
      `Event analysis for ${departmentName}: ${members.length} employee(s)`
    );
  });

  await bus.emit("department-analysis-requested", {
    departmentName: "Security",
  });
}

function compareSubqueryStyles() {
  const selectedDepartmentIds = new Set(
    multiRowDepartmentIds(["Security", "Research"])
  );

  const subqueryStyle = employees
    .filter((employee) => selectedDepartmentIds.has(employee.departmentId))
    .map((employee) => employee.name)
    .sort();

  const joinStyle = employees
    .flatMap((employee) => {
      const department = departments.find(
        (candidate) => candidate.id === employee.departmentId
      );

      return department &&
        ["Security", "Research"].includes(department.name)
        ? [employee.name]
        : [];
    })
    .sort();

  return {
    subqueryStyle,
    joinStyle,
    equivalent:
      JSON.stringify(subqueryStyle) === JSON.stringify(joinStyle),
  };
}

function run() {
  console.log("SUBQUERIES FUNDAMENTALS");
  console.log("Scalar, single-row, multi-row, correlated, and table subqueries");

  print(
    "Employees above the company average",
    employeesAboveCompanyAverage()
  );

  print(
    "Employees in Engineering, Security, or Research",
    employeesInSelectedDepartments()
  );

  print(
    "Employees with at least 180 hours on one project",
    employeesWithHeavyProjectAssignment()
  );

  print(
    "Employees above their own department average",
    employeesAboveOwnDepartmentAverage()
  );

  print("Derived department table", tableSubquery());

  print("Departments with no projects", notExistsDepartmentProjects());

  print(
    "Employees above Engineering's average",
    nestedSubquery()
  );

  print(
    "Employees earning more than every Finance employee",
    subqueryWithAllSemantics()
  );

  print(
    "Employees whose salary matches any Engineering salary",
    subqueryWithAnySemantics()
  );

  print("Nested NULL-semantics demonstration", [
    demonstrateNullLikeBehavior(),
  ]);

  console.log("\nScalar contract:");
  console.log(validateScalarContract());

  console.log("\nAsynchronous subquery-like pipeline:");
  asynchronousSubqueryPipeline()
    .then((result) => {
      print("Employees selected by asynchronous inner result", result);

      return eventDrivenSubqueryWorkflow();
    })
    .then(() => {
      console.log("\nSubquery versus join:");
      console.log(compareSubqueryStyles());
    })
    .catch((error) => {
      console.error(`Workflow failed: ${error.message}`);
      process.exitCode = 1;
    });
}

run();
