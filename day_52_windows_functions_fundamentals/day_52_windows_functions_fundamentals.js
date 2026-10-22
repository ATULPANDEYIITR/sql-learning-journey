"use strict";

/*
 * Window-function concepts implemented as an event-driven Node.js report.
 * JavaScript does not have SQL's OVER() operator, so the implementation
 * explicitly models partitions, ordering, frames, and neighboring rows.
 */

const sales = [
  { id: 1, employee: "Asha", department: "Technology", date: "2026-01-05", amount: 12000 },
  { id: 2, employee: "Ravi", department: "Technology", date: "2026-01-12", amount: 18000 },
  { id: 3, employee: "Asha", department: "Technology", date: "2026-02-03", amount: 15000 },
  { id: 4, employee: "Ravi", department: "Technology", date: "2026-02-17", amount: 22000 },
  { id: 5, employee: "Neha", department: "Finance", date: "2026-01-08", amount: 9000 },
  { id: 6, employee: "Vikram", department: "Finance", date: "2026-01-22", amount: 14000 },
  { id: 7, employee: "Neha", department: "Finance", date: "2026-02-06", amount: 11000 },
  { id: 8, employee: "Vikram", department: "Finance", date: "2026-02-20", amount: 17000 },
  { id: 9, employee: "Meera", department: "Operations", date: "2026-01-10", amount: 7000 },
  { id: 10, employee: "Meera", department: "Operations", date: "2026-02-14", amount: 13000 }
];

function validateSales(rows) {
  if (!Array.isArray(rows)) {
    throw new TypeError("Sales must be an array.");
  }

  const ids = new Set();

  return rows.map((row) => {
    if (!Number.isInteger(row.id) || row.id <= 0) {
      throw new RangeError("Sale ID must be a positive integer.");
    }

    if (ids.has(row.id)) {
      throw new Error(`Duplicate sale ID: ${row.id}`);
    }
    ids.add(row.id);

    if (!row.employee?.trim() || !row.department?.trim()) {
      throw new Error(`Invalid employee or department for sale ${row.id}.`);
    }

    if (!Number.isFinite(row.amount) || row.amount < 0) {
      throw new RangeError(`Invalid amount for sale ${row.id}.`);
    }

    const parsedDate = new Date(`${row.date}T00:00:00Z`);
    if (Number.isNaN(parsedDate.getTime())) {
      throw new Error(`Invalid date for sale ${row.id}.`);
    }

    return { ...row, parsedDate };
  });
}

function partitionAndOrder(rows, key) {
  const partitions = new Map();

  for (const row of rows) {
    if (!partitions.has(row[key])) {
      partitions.set(row[key], []);
    }
    partitions.get(row[key]).push(row);
  }

  for (const partition of partitions.values()) {
    partition.sort(
      (a, b) =>
        a.parsedDate - b.parsedDate ||
        a.id - b.id
    );
  }

  return partitions;
}

function addRowNumber(rows) {
  const result = new Map();

  for (const partition of partitionAndOrder(rows, "department").values()) {
    partition.forEach((row, index) => {
      result.set(row.id, index + 1);
    });
  }

  return result;
}

function addRunningTotal(rows) {
  const result = new Map();

  for (const partition of partitionAndOrder(rows, "department").values()) {
    let total = 0;

    for (const row of partition) {
      total += row.amount;
      result.set(row.id, total);
    }
  }

  return result;
}

function addLagAndLead(rows) {
  const result = new Map();

  for (const partition of partitionAndOrder(rows, "department").values()) {
    partition.forEach((row, index) => {
      result.set(row.id, {
        lag: index === 0 ? null : partition[index - 1].amount,
        lead: index === partition.length - 1 ? null : partition[index + 1].amount
      });
    });
  }

  return result;
}

function addMovingAverage(rows, frameSize = 2) {
  if (!Number.isInteger(frameSize) || frameSize <= 0) {
    throw new RangeError("Frame size must be a positive integer.");
  }

  const result = new Map();

  for (const partition of partitionAndOrder(rows, "department").values()) {
    for (let index = 0; index < partition.length; index += 1) {
      const start = Math.max(0, index - frameSize + 1);
      const frame = partition.slice(start, index + 1);
      const average =
        frame.reduce((sum, row) => sum + row.amount, 0) / frame.length;

      result.set(partition[index].id, average);
    }
  }

  return result;
}

function addRank(rows) {
  const result = new Map();

  for (const partition of partitionAndOrder(rows, "department").values()) {
    const ranked = [...partition].sort(
      (a, b) => b.amount - a.amount || a.id - b.id
    );

    let previousAmount = null;
    let rank = 0;

    ranked.forEach((row, index) => {
      if (row.amount !== previousAmount) {
        rank = index + 1;
        previousAmount = row.amount;
      }
      result.set(row.id, rank);
    });
  }

  return result;
}

function buildReport(rows) {
  const rowNumbers = addRowNumber(rows);
  const runningTotals = addRunningTotal(rows);
  const neighbors = addLagAndLead(rows);
  const averages = addMovingAverage(rows);
  const ranks = addRank(rows);

  return [...rows]
    .sort((a, b) => a.parsedDate - b.parsedDate || a.id - b.id)
    .map((row) => ({
      ...row,
      rowNumber: rowNumbers.get(row.id),
      rank: ranks.get(row.id),
      runningTotal: runningTotals.get(row.id),
      movingAverage: averages.get(row.id),
      lag: neighbors.get(row.id).lag,
      lead: neighbors.get(row.id).lead
    }));
}

function printReport(report) {
  console.table(
    report.map((row) => ({
      ID: row.id,
      Department: row.department,
      Employee: row.employee,
      Amount: row.amount.toFixed(2),
      "ROW_NUMBER": row.rowNumber,
      RANK: row.rank,
      "Running Total": row.runningTotal.toFixed(2),
      "Moving Avg": row.movingAverage.toFixed(2),
      LAG: row.lag === null ? "-" : row.lag.toFixed(2),
      LEAD: row.lead === null ? "-" : row.lead.toFixed(2)
    }))
  );
}

function createEventStream(report) {
  return report.map((row) => ({
    type: "SALE_ANALYZED",
    saleId: row.id,
    department: row.department,
    rank: row.rank,
    runningTotal: row.runningTotal
  }));
}

async function main() {
  try {
    const validated = validateSales(sales);
    const report = buildReport(validated);

    printReport(report);

    const events = createEventStream(report);
    for (const event of events) {
      await Promise.resolve();
      console.log(
        `EVENT ${event.type}: sale=${event.saleId}, ` +
        `department=${event.department}, rank=${event.rank}, ` +
        `runningTotal=${event.runningTotal.toFixed(2)}`
      );
    }
  } catch (error) {
    console.error(`Window analysis failed: ${error.message}`);
    process.exitCode = 1;
  }
}

main();
