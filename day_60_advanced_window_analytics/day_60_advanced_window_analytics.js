"use strict";

const { EventEmitter } = require("node:events");

const MAX_EVENTS = 500_000;
const MAX_SPAN_DAYS = 3660;

class AnalyticsError extends Error {
    constructor(message) {
        super(message);
        this.name = "AnalyticsError";
    }
}

class WindowPolicy {
    constructor({
        windowDays = 7,
        revenueWeight = 0.60,
        growthWeight = 0.40,
        maximumSpanDays = MAX_SPAN_DAYS
    } = {}) {
        if (!Number.isInteger(windowDays) || windowDays < 1) {
            throw new AnalyticsError("Window length must be a positive integer.");
        }

        if (!Number.isFinite(revenueWeight) || revenueWeight < 0 ||
            !Number.isFinite(growthWeight) || growthWeight < 0) {
            throw new AnalyticsError("Ranking weights must be finite and non-negative.");
        }

        if (Math.abs(revenueWeight + growthWeight - 1) > 1e-10) {
            throw new AnalyticsError("Ranking weights must add up to 1.");
        }

        if (!Number.isInteger(maximumSpanDays) ||
            maximumSpanDays < 2 * windowDays ||
            maximumSpanDays > MAX_SPAN_DAYS) {
            throw new AnalyticsError("Invalid maximum date span.");
        }

        this.windowDays = windowDays;
        this.revenueWeight = revenueWeight;
        this.growthWeight = growthWeight;
        this.maximumSpanDays = maximumSpanDays;
        Object.freeze(this);
    }
}

function validateIdentifier(value, fieldName) {
    if (typeof value !== "string" ||
        !/^[A-Za-z0-9_-]{1,50}$/.test(value)) {
        throw new AnalyticsError(`Invalid ${fieldName}.`);
    }
}

function parseDate(value) {
    if (typeof value !== "string" ||
        !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        throw new AnalyticsError("Dates must use YYYY-MM-DD format.");
    }

    const timestamp = Date.parse(`${value}T00:00:00.000Z`);

    if (!Number.isFinite(timestamp) ||
        new Date(timestamp).toISOString().slice(0, 10) !== value) {
        throw new AnalyticsError(`Invalid calendar date: ${value}.`);
    }

    return Math.floor(timestamp / 86_400_000);
}

function formatDate(dayNumber) {
    return new Date(dayNumber * 86_400_000).toISOString().slice(0, 10);
}

function safeGrowth(current, previous) {
    if (previous === null || previous <= 0) {
        return null;
    }

    return (current - previous) / previous;
}

function competitionRanks(items, valueSelector) {
    const ordered = [...items].sort(
        (left, right) => valueSelector(right) - valueSelector(left)
    );

    const ranks = new Map();
    let previousValue = null;
    let currentRank = 0;

    ordered.forEach((item, index) => {
        const value = valueSelector(item);

        if (index === 0 || value !== previousValue) {
            currentRank = index + 1;
        }

        ranks.set(item.productId, currentRank);
        previousValue = value;
    });

    return ranks;
}

function normalizedRankScore(rank, populationSize) {
    if (populationSize <= 1) {
        return 1;
    }

    return (populationSize - rank) / (populationSize - 1);
}

class WindowAnalyticsEngine extends EventEmitter {
    constructor(policy = new WindowPolicy()) {
        super();
        this.policy = policy;
    }

    validateEvents(events) {
        if (!Array.isArray(events) || events.length === 0) {
            throw new AnalyticsError("A non-empty event array is required.");
        }

        if (events.length > MAX_EVENTS) {
            throw new AnalyticsError(`Event limit exceeded: ${MAX_EVENTS}.`);
        }

        const seenIds = new Set();

        return events.map((event) => {
            if (!event || typeof event !== "object") {
                throw new AnalyticsError("Every event must be an object.");
            }

            validateIdentifier(event.eventId, "event identifier");
            validateIdentifier(event.storeId, "store identifier");
            validateIdentifier(event.productId, "product identifier");

            if (seenIds.has(event.eventId)) {
                throw new AnalyticsError(
                    `Duplicate event identifier: ${event.eventId}.`
                );
            }

            seenIds.add(event.eventId);

            const day = parseDate(event.saleDate);

            if (!Number.isSafeInteger(event.revenueCents) ||
                event.revenueCents < 0) {
                throw new AnalyticsError(
                    `Invalid revenue amount for ${event.eventId}.`
                );
            }

            if (!Number.isSafeInteger(event.units) || event.units <= 0) {
                throw new AnalyticsError(
                    `Invalid unit quantity for ${event.eventId}.`
                );
            }

            return {
                eventId: event.eventId,
                storeId: event.storeId,
                productId: event.productId,
                saleDate: event.saleDate,
                day,
                units: event.units,
                revenueCents: event.revenueCents
            };
        });
    }

    async calculate(events) {
        const validated = this.validateEvents(events);

        // Yield before processing so callers can integrate the engine into
        // an asynchronous Node.js workflow.
        await new Promise((resolve) => setImmediate(resolve));

        const daily = new Map();

        for (const event of validated) {
            const seriesKey = `${event.storeId}\u001f${event.productId}`;
            const dailyKey = `${seriesKey}\u001f${event.day}`;

            if (!daily.has(dailyKey)) {
                daily.set(dailyKey, {
                    storeId: event.storeId,
                    productId: event.productId,
                    day: event.day,
                    revenueCents: 0,
                    units: 0
                });
            }

            const aggregate = daily.get(dailyKey);
            aggregate.revenueCents += event.revenueCents;
            aggregate.units += event.units;

            if (!Number.isSafeInteger(aggregate.revenueCents)) {
                throw new AnalyticsError("Aggregated revenue exceeds safe integer range.");
            }
        }

        const series = new Map();

        for (const row of daily.values()) {
            const key = `${row.storeId}\u001f${row.productId}`;

            if (!series.has(key)) {
                series.set(key, {
                    storeId: row.storeId,
                    productId: row.productId,
                    observations: new Map()
                });
            }

            series.get(key).observations.set(row.day, row);
        }

        const workRows = [];
        const windowDays = this.policy.windowDays;

        for (const group of series.values()) {
            const dates = [...group.observations.keys()];
            const firstDay = Math.min(...dates);
            const lastDay = Math.max(...dates);
            const span = lastDay - firstDay + 1;

            if (span > this.policy.maximumSpanDays) {
                throw new AnalyticsError(
                    `Date span exceeded for ${group.storeId}/${group.productId}.`
                );
            }

            const dailyRevenue = [];
            const dailyUnits = [];
            const revenuePrefix = [0];
            const unitsPrefix = [0];

            for (let day = firstDay; day <= lastDay; day += 1) {
                const observation = group.observations.get(day);

                const revenue = observation ? observation.revenueCents : 0;
                const units = observation ? observation.units : 0;

                dailyRevenue.push(revenue);
                dailyUnits.push(units);

                revenuePrefix.push(revenuePrefix.at(-1) + revenue);
                unitsPrefix.push(unitsPrefix.at(-1) + units);
            }

            for (let index = 0; index < span; index += 1) {
                const currentStart = Math.max(0, index - windowDays + 1);
                const rollingRevenue =
                    revenuePrefix[index + 1] - revenuePrefix[currentStart];
                const rollingUnits =
                    unitsPrefix[index + 1] - unitsPrefix[currentStart];

                const observedDays = index - currentStart + 1;
                const movingAverageRevenue = rollingRevenue / observedDays;

                let previous7dRevenue = null;
                let growthRate = null;

                if (index >= (2 * windowDays - 1)) {
                    const previousStart = index - (2 * windowDays) + 1;
                    const previousEnd = index - windowDays + 1;

                    previous7dRevenue =
                        revenuePrefix[previousEnd] - revenuePrefix[previousStart];

                    growthRate = safeGrowth(rollingRevenue, previous7dRevenue);
                }

                const row = {
                    storeId: group.storeId,
                    productId: group.productId,
                    saleDate: formatDate(firstDay + index),
                    dailyRevenueCents: dailyRevenue[index],
                    dailyUnits: dailyUnits[index],
                    rollingRevenue7dCents: rollingRevenue,
                    rollingUnits7d: rollingUnits,
                    movingAverageRevenue7dCents: movingAverageRevenue,
                    previous7dRevenueCents: previous7dRevenue,
                    growthRate,
                    previousDayRevenueCents:
                        index > 0 ? dailyRevenue[index - 1] : null,
                    cumulativeRevenueCents: revenuePrefix[index + 1],
                    revenueRank: null,
                    growthRank: null,
                    compositeScore: null,
                    compositeRank: null
                };

                workRows.push(row);
            }
        }

        // Grouping by store and date creates the correct comparison population.
        const storeDayGroups = new Map();

        for (const row of workRows) {
            const key = `${row.storeId}\u001f${row.saleDate}`;

            if (!storeDayGroups.has(key)) {
                storeDayGroups.set(key, []);
            }

            storeDayGroups.get(key).push(row);
        }

        for (const candidates of storeDayGroups.values()) {
            const revenueRanks = competitionRanks(
                candidates,
                (row) => row.rollingRevenue7dCents
            );

            for (const row of candidates) {
                row.revenueRank = revenueRanks.get(row.productId);
            }

            const eligible = candidates.filter(
                (row) => row.growthRate !== null &&
                    row.previous7dRevenueCents !== null &&
                    row.previous7dRevenueCents > 0
            );

            if (eligible.length === 0) {
                continue;
            }

            const growthRanks = competitionRanks(
                eligible,
                (row) => row.growthRate
            );

            const populationSize = eligible.length;

            for (const row of eligible) {
                row.growthRank = growthRanks.get(row.productId);

                const revenueScore = normalizedRankScore(
                    row.revenueRank,
                    populationSize
                );
                const growthScore = normalizedRankScore(
                    row.growthRank,
                    populationSize
                );

                row.compositeScore =
                    this.policy.revenueWeight * revenueScore +
                    this.policy.growthWeight * growthScore;
            }

            const compositeRanks = competitionRanks(
                eligible,
                (row) => row.compositeScore
            );

            for (const row of eligible) {
                row.compositeRank = compositeRanks.get(row.productId);
            }
        }

        const result = workRows.sort((left, right) =>
            left.saleDate.localeCompare(right.saleDate) ||
            left.storeId.localeCompare(right.storeId) ||
            left.productId.localeCompare(right.productId)
        );

        this.emit("calculationCompleted", {
            eventCount: validated.length,
            rowCount: result.length,
            eligibleCount: result.filter(
                (row) => row.compositeScore !== null
            ).length
        });

        return result;
    }
}

function createSampleEvents() {
    const events = [];
    let eventNumber = 1;

    const stores = ["LKO-01", "LKO-02"];
    const products = ["P-A", "P-B", "P-C"];
    const startDay = parseDate("2026-10-01");

    for (let storeIndex = 0; storeIndex < stores.length; storeIndex += 1) {
        for (let productIndex = 0; productIndex < products.length; productIndex += 1) {
            for (let dayNumber = 0; dayNumber < 21; dayNumber += 1) {
                const day = startDay + dayNumber;

                if (
                    stores[storeIndex] === "LKO-02" &&
                    products[productIndex] === "P-C" &&
                    dayNumber === 5
                ) {
                    continue;
                }

                const revenueCents =
                    10000 +
                    productIndex * 1700 +
                    storeIndex * 800 +
                    dayNumber * (productIndex * 220 + storeIndex * 90);

                events.push({
                    eventId: `EVT-${String(eventNumber++).padStart(5, "0")}`,
                    storeId: stores[storeIndex],
                    productId: products[productIndex],
                    saleDate: formatDate(day),
                    units: 5 + productIndex + ((dayNumber + storeIndex) % 4),
                    revenueCents
                });

                if (dayNumber % 5 === 0 && productIndex === 0) {
                    events.push({
                        eventId: `EVT-${String(eventNumber++).padStart(5, "0")}`,
                        storeId: stores[storeIndex],
                        productId: products[productIndex],
                        saleDate: formatDate(day),
                        units: 2,
                        revenueCents: 2500 + dayNumber * 10
                    });
                }
            }
        }
    }

    return events;
}

function verifyResults(rows) {
    if (rows.length !== 126) {
        throw new AnalyticsError(`Unexpected result count: ${rows.length}.`);
    }

    const missingDate = rows.find(
        (row) =>
            row.storeId === "LKO-02" &&
            row.productId === "P-C" &&
            row.saleDate === "2026-10-06"
    );

    if (!missingDate ||
        missingDate.dailyRevenueCents !== 0 ||
        missingDate.dailyUnits !== 0) {
        throw new AnalyticsError("Missing-date handling validation failed.");
    }

    const firstEligibleDate = rows.find(
        (row) =>
            row.storeId === "LKO-01" &&
            row.productId === "P-A" &&
            row.saleDate === "2026-10-14"
    );

    if (!firstEligibleDate ||
        firstEligibleDate.growthRate === null ||
        firstEligibleDate.compositeRank === null) {
        throw new AnalyticsError("First eligible window validation failed.");
    }

    if (safeGrowth(120, 0) !== null || safeGrowth(120, null) !== null) {
        throw new AnalyticsError("Zero-denominator handling validation failed.");
    }
}

function printLatestReport(rows) {
    const latestDate = rows.reduce(
        (latest, row) => row.saleDate > latest ? row.saleDate : latest,
        rows[0].saleDate
    );

    console.log(`Advanced Window Analytics | Reporting date: ${latestDate}`);
    console.log(
        "Store      Product   Daily revenue   Rolling 7d   Growth %   Score   Rank"
    );

    const reportRows = rows
        .filter((row) => row.saleDate === latestDate)
        .sort((left, right) =>
            left.storeId.localeCompare(right.storeId) ||
            (left.compositeRank ?? Number.MAX_SAFE_INTEGER) -
                (right.compositeRank ?? Number.MAX_SAFE_INTEGER)
        );

    for (const row of reportRows) {
        const growth = row.growthRate === null
            ? "N/A"
            : (row.growthRate * 100).toFixed(2);

        const score = row.compositeScore === null
            ? "N/A"
            : row.compositeScore.toFixed(4);

        const rank = row.compositeRank ?? "N/A";

        console.log(
            `${row.storeId.padEnd(10)} ${row.productId.padEnd(8)} ` +
            `${(row.dailyRevenueCents / 100).toFixed(2).padStart(12)} ` +
            `${(row.rollingRevenue7dCents / 100).toFixed(2).padStart(12)} ` +
            `${growth.padStart(9)} ${score.padStart(8)} ${String(rank).padStart(6)}`
        );
    }
}

async function main() {
    try {
        const engine = new WindowAnalyticsEngine(
            new WindowPolicy({
                windowDays: 7,
                revenueWeight: 0.60,
                growthWeight: 0.40
            })
        );

        engine.on("calculationCompleted", (statistics) => {
            console.log(
                `\nProcessed ${statistics.eventCount} transactions into ` +
                `${statistics.rowCount} daily rows.`
            );
            console.log(`Ranking-eligible rows: ${statistics.eligibleCount}`);
        });

        const events = createSampleEvents();
        const rows = await engine.calculate(events);

        verifyResults(rows);
        printLatestReport(rows);
    } catch (error) {
        if (error instanceof AnalyticsError) {
            console.error(`Analytics failure: ${error.message}`);
        } else {
            console.error("Unexpected execution failure:", error);
        }

        process.exitCode = 1;
    }
}

if (require.main === module) {
    main();
}

module.exports = {
    AnalyticsError,
    WindowPolicy,
    WindowAnalyticsEngine,
    safeGrowth,
    competitionRanks
};
