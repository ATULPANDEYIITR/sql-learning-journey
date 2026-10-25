"use strict";

/*
 * NTILE implementation for ordered records.
 *
 * The implementation follows SQL NTILE semantics:
 * - rows are ordered first;
 * - rows are distributed across N buckets;
 * - bucket sizes differ by at most one;
 * - earlier buckets receive the extra rows.
 */

class InvalidBucketCountError extends Error {
    constructor(message) {
        super(message);
        this.name = "InvalidBucketCountError";
    }
}

class Record {
    constructor(id, customer, score) {
        if (!Number.isInteger(id) || id <= 0) {
            throw new TypeError("id must be a positive integer");
        }

        if (typeof customer !== "string" || customer.trim() === "") {
            throw new TypeError("customer must be a non-empty string");
        }

        if (!Number.isFinite(score)) {
            throw new TypeError("score must be finite");
        }

        this.id = id;
        this.customer = customer;
        this.score = score;
    }
}

function validateBucketCount(bucketCount) {
    if (!Number.isInteger(bucketCount) || bucketCount <= 0) {
        throw new InvalidBucketCountError(
            "bucketCount must be a positive integer"
        );
    }
}

function ntile(records, bucketCount) {
    validateBucketCount(bucketCount);

    if (!Array.isArray(records)) {
        throw new TypeError("records must be an array");
    }

    const ordered = [...records].sort(
        (a, b) => b.score - a.score || a.id - b.id
    );

    const total = ordered.length;
    if (total === 0) {
        return [];
    }

    const baseSize = Math.floor(total / bucketCount);
    const remainder = total % bucketCount;

    const result = [];
    let position = 0;

    for (let bucket = 1; bucket <= bucketCount; bucket++) {
        const size = baseSize + (bucket <= remainder ? 1 : 0);

        for (let offset = 0; offset < size && position < total; offset++) {
            result.push({
                record: ordered[position],
                bucket,
                bucketCount
            });
            position++;
        }
    }

    return result;
}

function groupByBucket(bucketedRecords) {
    const groups = new Map();

    for (const item of bucketedRecords) {
        if (!groups.has(item.bucket)) {
            groups.set(item.bucket, []);
        }
        groups.get(item.bucket).push(item.record);
    }

    return groups;
}

function summarize(bucketedRecords) {
    const groups = groupByBucket(bucketedRecords);
    const result = [];

    for (const [bucket, records] of groups.entries()) {
        const scores = records.map(record => record.score);
        const total = scores.reduce((sum, value) => sum + value, 0);

        result.push({
            bucket,
            count: scores.length,
            minimum: Math.min(...scores),
            maximum: Math.max(...scores),
            average: total / scores.length
        });
    }

    return result;
}

function evaluateSegmentation(records, bucketCount = 10) {
    if (bucketCount !== 10) {
        throw new RangeError("Segmentation requires ten buckets");
    }

    const labels = new Map([
        [1, "Top 10%"],
        [2, "High"],
        [3, "High"],
        [4, "Upper-Middle"],
        [5, "Upper-Middle"],
        [6, "Lower-Middle"],
        [7, "Lower-Middle"],
        [8, "Low"],
        [9, "Low"],
        [10, "Bottom 10%"]
    ]);

    return new Map(
        ntile(records, 10).map(item => [
            item.record.id,
            labels.get(item.bucket)
        ])
    );
}

function assertNtileProperties(records, bucketCount) {
    const bucketed = ntile(records, bucketCount);

    if (bucketed.length !== records.length) {
        throw new Error("NTILE lost or duplicated records");
    }

    const groups = groupByBucket(bucketed);
    const sizes = [];

    for (let bucket = 1; bucket <= bucketCount; bucket++) {
        sizes.push((groups.get(bucket) || []).length);
    }

    if (records.length > 0) {
        const minimum = Math.min(...sizes);
        const maximum = Math.max(...sizes);

        if (maximum - minimum > 1) {
            throw new Error("NTILE bucket sizes differ by more than one");
        }
    }

    for (let i = 1; i < bucketed.length; i++) {
        if (bucketed[i - 1].record.score < bucketed[i].record.score) {
            throw new Error("Records are not ordered correctly");
        }
    }
}

async function processBuckets(records, bucketCount) {
    /*
     * A Promise-based API makes this function suitable for a larger
     * event-driven workflow without introducing third-party packages.
     */
    return Promise.resolve(ntile(records, bucketCount));
}

async function main() {
    const records = [
        new Record(101, "Asha", 96),
        new Record(102, "Bharat", 82),
        new Record(103, "Chirag", 91),
        new Record(104, "Divya", 74),
        new Record(105, "Esha", 88),
        new Record(106, "Farhan", 67),
        new Record(107, "Gita", 91),
        new Record(108, "Harsh", 59),
        new Record(109, "Isha", 84),
        new Record(110, "Jay", 72),
        new Record(111, "Kiran", 95),
        new Record(112, "Lalit", 63)
    ];

    const quartiles = await processBuckets(records, 4);

    console.log("QUARTILES");
    for (const item of quartiles) {
        console.log(
            `${item.record.customer.padEnd(8)} ` +
            `score=${item.record.score.toFixed(1).padStart(5)} ` +
            `quartile=${item.bucket}`
        );
    }

    console.log("\nQUARTILE STATISTICS");
    console.table(summarize(quartiles));

    const deciles = await processBuckets(records, 10);

    console.log("\nDECILES");
    for (const item of deciles) {
        console.log(
            `${item.record.customer.padEnd(8)} ` +
            `score=${item.record.score.toFixed(1).padStart(5)} ` +
            `decile=${item.bucket}`
        );
    }

    console.log("\nSEGMENTS");
    for (const [id, segment] of evaluateSegmentation(records)) {
        console.log(`${id}: ${segment}`);
    }

    assertNtileProperties(records, 4);
    assertNtileProperties(records, 10);
    assertNtileProperties([], 5);

    try {
        ntile(records, 0);
    } catch (error) {
        if (!(error instanceof InvalidBucketCountError)) {
            throw error;
        }
        console.log("\nInvalid bucket count rejected.");
    }

    console.log("NTILE validation passed.");
}

main().catch(error => {
    console.error("Processing failed:", error.message);
    process.exitCode = 1;
});
