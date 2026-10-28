"use strict";

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}

class Sale {
    constructor(id, employee, date, amount) {
        if (!Number.isInteger(id) || id <= 0) {
            throw new ValidationError("Sale id must be a positive integer");
        }
        if (!employee.trim()) {
            throw new ValidationError("Employee cannot be empty");
        }
        if (!Number.isFinite(amount) || amount < 0) {
            throw new ValidationError("Amount must be a non-negative finite number");
        }

        this.id = id;
        this.employee = employee;
        this.date = new Date(date);
        this.amount = amount;

        if (Number.isNaN(this.date.getTime())) {
            throw new ValidationError(`Invalid date: ${date}`);
        }
    }
}

class WindowEngine {
    constructor(rows) {
        if (!Array.isArray(rows) || rows.length === 0) {
            throw new ValidationError("At least one row is required");
        }

        this.rows = [...rows];
        this.validateUniqueIds();
    }

    validateUniqueIds() {
        const ids = new Set();

        for (const row of this.rows) {
            if (ids.has(row.id)) {
                throw new ValidationError(`Duplicate id: ${row.id}`);
            }
            ids.add(row.id);
        }
    }

    rowsFrame(preceding, following = 0) {
        if (!Number.isInteger(preceding) || !Number.isInteger(following)) {
            throw new ValidationError("ROWS offsets must be integers");
        }

        return this.rows.map((_, index) => {
            const start = Math.max(0, index - preceding);
            const end = Math.min(this.rows.length - 1, index + following);

            let total = 0;
            for (let i = start; i <= end; i++) {
                total += this.rows[i].amount;
            }
            return total;
        });
    }

    runningRows() {
        return this.rows.map((_, index) => {
            let total = 0;
            for (let i = 0; i <= index; i++) {
                total += this.rows[i].amount;
            }
            return total;
        });
    }

    rangeFrame(orderSelector, preceding, following = 0) {
        if (!Number.isFinite(preceding) || preceding < 0) {
            throw new ValidationError("RANGE preceding must be non-negative");
        }

        const ordered = [...this.rows].sort(
            (a, b) => orderSelector(a) - orderSelector(b)
        );

        return ordered.map(current => {
            const value = orderSelector(current);
            const low = value - preceding;
            const high = value + following;

            return ordered
                .filter(row => {
                    const candidate = orderSelector(row);
                    return candidate >= low && candidate <= high;
                })
                .reduce((sum, row) => sum + row.amount, 0);
        });
    }

    groupsFrame(orderSelector, precedingGroups, followingGroups = 0) {
        if (
            !Number.isInteger(precedingGroups) ||
            precedingGroups < 0 ||
            !Number.isInteger(followingGroups) ||
            followingGroups < 0
        ) {
            throw new ValidationError("GROUPS boundaries must be non-negative integers");
        }

        const ordered = [...this.rows].sort(
            (a, b) => orderSelector(a) - orderSelector(b)
        );

        const peerValues = [...new Set(ordered.map(orderSelector))];

        return ordered.map(current => {
            const currentValue = orderSelector(current);
            const groupIndex = peerValues.indexOf(currentValue);
            const first = Math.max(0, groupIndex - precedingGroups);
            const last = Math.min(
                peerValues.length - 1,
                groupIndex + followingGroups
            );

            const allowed = new Set(peerValues.slice(first, last + 1));

            return ordered
                .filter(row => allowed.has(orderSelector(row)))
                .reduce((sum, row) => sum + row.amount, 0);
        });
    }
}

function printResult(title, rows, totals) {
    console.log(`\n${title}`);
    rows.forEach((row, index) => {
        console.log(
            `${row.id} | ${row.date.toISOString().slice(0, 10)} | ` +
            `${row.amount.toFixed(2)} | ${totals[index].toFixed(2)}`
        );
    });
}

async function main() {
    const rows = [
        new Sale(1, "Asha", "2026-10-01", 100),
        new Sale(2, "Asha", "2026-10-02", 200),
        new Sale(3, "Asha", "2026-10-02", 300),
        new Sale(4, "Asha", "2026-10-04", 400),
        new Sale(5, "Asha", "2026-10-07", 500)
    ];

    const engine = new WindowEngine(rows);

    printResult(
        "ROWS: 1 PRECEDING TO CURRENT ROW",
        rows,
        engine.rowsFrame(1)
    );

    printResult(
        "ROWS: UNBOUNDED PRECEDING TO CURRENT ROW",
        rows,
        engine.runningRows()
    );

    const rangeResult = engine.rangeFrame(
        row => row.amount,
        200
    );

    console.log("\nRANGE: amount - 200 THROUGH amount");
    rangeResult.forEach((total, index) => {
        console.log(`ordered row ${index + 1} -> ${total.toFixed(2)}`);
    });

    const groupsResult = engine.groupsFrame(
        row => row.date.getUTCDate(),
        1
    );

    console.log("\nGROUPS: 1 PRECEDING GROUP THROUGH CURRENT GROUP");
    groupsResult.forEach((total, index) => {
        console.log(`peer-group row ${index + 1} -> ${total.toFixed(2)}`);
    });

    // Window frames must be deterministic when physical row order matters.
    console.assert(
        JSON.stringify(engine.rowsFrame(1)) === JSON.stringify([100, 300, 500, 700, 900])
    );

    console.assert(
        JSON.stringify(engine.runningRows()) === JSON.stringify([100, 300, 600, 1000, 1500])
    );

    console.log("\nValidation checks passed.");
}

main().catch(error => {
    console.error(`[${error.name}] ${error.message}`);
    process.exitCode = 1;
});
