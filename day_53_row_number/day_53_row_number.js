"use strict";

/*
 * Ranking rows, deduplication, and top-N analysis.
 * This implementation uses an event-driven pipeline so that each analytical
 * operation can be observed without coupling the calculations together.
 */

const sales = [
    { saleId: 1, customerId: 101, productId: "LAPTOP", category: "Electronics", amount: 1200 },
    { saleId: 2, customerId: 102, productId: "PHONE", category: "Electronics", amount: 800 },
    { saleId: 3, customerId: 101, productId: "LAPTOP", category: "Electronics", amount: 1250 },
    { saleId: 4, customerId: 103, productId: "CHAIR", category: "Furniture", amount: 300 },
    { saleId: 5, customerId: 104, productId: "PHONE", category: "Electronics", amount: 950 },
    { saleId: 6, customerId: 102, productId: "MONITOR", category: "Electronics", amount: 500 },
    { saleId: 7, customerId: 105, productId: "TABLE", category: "Furniture", amount: 700 },
    { saleId: 8, customerId: 103, productId: "CHAIR", category: "Furniture", amount: 320 },
    { saleId: 9, customerId: 106, productId: "PHONE", category: "Electronics", amount: 1100 },
    { saleId: 10, customerId: 107, productId: "DESK", category: "Furniture", amount: 900 },
    { saleId: 11, customerId: 108, productId: "PHONE", category: "Electronics", amount: 780 },
    { saleId: 12, customerId: 109, productId: "TABLE", category: "Furniture", amount: 650 }
];

class AnalysisPipeline {
    constructor(rows) {
        this.rows = rows.map(row => ({ ...row }));
        this.listeners = new Map();
    }

    on(eventName, handler) {
        if (!this.listeners.has(eventName)) {
            this.listeners.set(eventName, []);
        }
        this.listeners.get(eventName).push(handler);
        return this;
    }

    emit(eventName, payload) {
        for (const handler of this.listeners.get(eventName) ?? []) {
            handler(payload);
        }
    }

    validate() {
        const ids = new Set();

        for (const row of this.rows) {
            if (!Number.isInteger(row.saleId) || row.saleId <= 0) {
                throw new Error(`Invalid saleId: ${row.saleId}`);
            }

            if (ids.has(row.saleId)) {
                throw new Error(`Duplicate saleId: ${row.saleId}`);
            }

            ids.add(row.saleId);

            if (!Number.isInteger(row.customerId) || row.customerId <= 0) {
                throw new Error(`Invalid customerId: ${row.customerId}`);
            }

            if (!row.productId || !row.category) {
                throw new Error(`Missing product/category for sale ${row.saleId}`);
            }

            if (!Number.isFinite(row.amount) || row.amount < 0) {
                throw new Error(`Invalid amount for sale ${row.saleId}`);
            }
        }

        this.emit("validated", this.rows.length);
        return this;
    }

    rowNumberByCustomer() {
        const partitions = new Map();

        for (const row of this.rows) {
            if (!partitions.has(row.customerId)) {
                partitions.set(row.customerId, []);
            }
            partitions.get(row.customerId).push(row);
        }

        const result = [];

        for (const [customerId, group] of partitions) {
            group.sort((a, b) => b.amount - a.amount || a.saleId - b.saleId);

            group.forEach((row, index) => {
                result.push({
                    ...row,
                    rowNumber: index + 1
                });
            });
        }

        result.sort((a, b) =>
            a.customerId - b.customerId || a.rowNumber - b.rowNumber
        );

        this.emit("ranked", result);
        return result;
    }

    deduplicateByCustomerProduct() {
        const best = new Map();

        for (const row of this.rows) {
            const key = `${row.customerId}:${row.productId}`;
            const current = best.get(key);

            if (
                !current ||
                row.amount > current.amount ||
                (row.amount === current.amount && row.saleId > current.saleId)
            ) {
                best.set(key, row);
            }
        }

        const result = [...best.values()].sort((a, b) => a.saleId - b.saleId);
        this.emit("deduplicated", result);
        return result;
    }

    topNPerCategory(n) {
        if (!Number.isInteger(n) || n <= 0) {
            throw new Error("n must be a positive integer.");
        }

        const partitions = new Map();

        for (const row of this.rows) {
            if (!partitions.has(row.category)) {
                partitions.set(row.category, []);
            }
            partitions.get(row.category).push(row);
        }

        const result = [];

        for (const [category, group] of partitions) {
            group.sort((a, b) => b.amount - a.amount || a.saleId - b.saleId);

            group.slice(0, n).forEach((row, index) => {
                result.push({
                    ...row,
                    rowNumber: index + 1
                });
            });
        }

        result.sort((a, b) =>
            a.category.localeCompare(b.category) || a.rowNumber - b.rowNumber
        );

        return result;
    }

    globalTopN(n) {
        if (!Number.isInteger(n) || n <= 0) {
            throw new Error("n must be a positive integer.");
        }

        return [...this.rows]
            .sort((a, b) => b.amount - a.amount || a.saleId - b.saleId)
            .slice(0, n);
    }
}

function printRows(title, rows) {
    console.log(`\n${title}`);
    console.table(rows);
}

async function run() {
    const pipeline = new AnalysisPipeline(sales);

    pipeline
        .on("validated", count => console.log(`Validated ${count} rows.`))
        .on("ranked", rows => console.log(`Generated ${rows.length} ranked rows.`))
        .on("deduplicated", rows => console.log(`Reduced to ${rows.length} unique customer/product rows.`));

    pipeline.validate();

    printRows("ROW_NUMBER by customer", pipeline.rowNumberByCustomer());
    printRows(
        "Deduplicated customer/product records",
        pipeline.deduplicateByCustomerProduct()
    );
    printRows("Top 2 per category", pipeline.topNPerCategory(2));
    printRows("Global top 5", pipeline.globalTopN(5));

    /*
     * A database ROW_NUMBER assigns a distinct position to every row.
     * Therefore, ties do not receive the same row number.
     * The saleId tie-breaker makes the result deterministic.
     */
    const equalAmountRows = [
        { saleId: 20, amount: 900 },
        { saleId: 21, amount: 900 },
        { saleId: 22, amount: 800 }
    ];

    equalAmountRows.sort((a, b) => b.amount - a.amount || a.saleId - b.saleId);

    console.log("\nDeterministic tie handling");
    console.table(
        equalAmountRows.map((row, index) => ({
            ...row,
            rowNumber: index + 1
        }))
    );
}

run().catch(error => {
    console.error(`Analysis failed: ${error.message}`);
    process.exitCode = 1;
});
