"use strict";

/*
 * LAG and LEAD analysis for Node.js.
 *
 * LAG looks backward within an ordered series.
 * LEAD looks forward within an ordered series.
 *
 * The implementation deliberately separates:
 * - ordered time-series validation
 * - neighboring-row analysis
 * - percentage calculations
 * - event-driven reporting
 * - policy evaluation
 */

const Trend = Object.freeze({
    UP: "UP",
    DOWN: "DOWN",
    FLAT: "FLAT",
    UNKNOWN: "UNKNOWN"
});

class Metric {
    constructor(timestamp, value) {
        if (!(timestamp instanceof Date) || Number.isNaN(timestamp.getTime())) {
            throw new TypeError("timestamp must be a valid Date");
        }

        if (!Number.isFinite(value)) {
            throw new TypeError("value must be a finite number");
        }

        this.timestamp = new Date(timestamp.getTime());
        this.value = value;
        Object.freeze(this);
    }
}

class TimeSeriesAnalyzer {
    constructor(metrics) {
        this.metrics = TimeSeriesAnalyzer.validate(metrics);
    }

    static validate(metrics) {
        if (!Array.isArray(metrics) || metrics.length === 0) {
            throw new TypeError("A non-empty metric array is required.");
        }

        const copy = [...metrics].sort(
            (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
        );

        const timestamps = new Set();

        for (const metric of copy) {
            if (!(metric instanceof Metric)) {
                throw new TypeError("Every item must be a Metric.");
            }

            const key = metric.timestamp.getTime();
            if (timestamps.has(key)) {
                throw new Error(`Duplicate timestamp detected: ${metric.timestamp.toISOString()}`);
            }

            timestamps.add(key);
        }

        return Object.freeze(copy);
    }

    static classify(current, reference) {
        if (reference === null || reference === undefined) {
            return Trend.UNKNOWN;
        }

        if (current > reference) return Trend.UP;
        if (current < reference) return Trend.DOWN;
        return Trend.FLAT;
    }

    static percentageChange(current, reference) {
        if (current === null || reference === null || reference === undefined || reference === 0) {
            return null;
        }

        return ((current - reference) / reference) * 100;
    }

    analyze() {
        return this.metrics.map((metric, index) => {
            const previous = index > 0 ? this.metrics[index - 1] : null;
            const next = index + 1 < this.metrics.length ? this.metrics[index + 1] : null;

            return {
                timestamp: metric.timestamp.toISOString(),
                value: metric.value,
                lag: previous ? previous.value : null,
                lead: next ? next.value : null,
                lagDifference: previous ? metric.value - previous.value : null,
                leadDifference: next ? next.value - metric.value : null,
                lagPercent: previous
                    ? TimeSeriesAnalyzer.percentageChange(metric.value, previous.value)
                    : null,
                leadPercent: next
                    ? TimeSeriesAnalyzer.percentageChange(next.value, metric.value)
                    : null,
                lagTrend: TimeSeriesAnalyzer.classify(metric.value, previous?.value),
                leadTrend: TimeSeriesAnalyzer.classify(next?.value, metric.value)
            };
        });
    }

    detectReversals() {
        const rows = this.analyze();

        return rows.filter((row, index) => {
            if (index === 0 || index === rows.length - 1) return false;

            const previous = rows[index - 1].value;
            const current = row.value;
            const next = rows[index + 1].value;

            return (
                (current > previous && next < current) ||
                (current < previous && next > current)
            );
        });
    }

    async streamEvents(handler) {
        if (typeof handler !== "function") {
            throw new TypeError("handler must be a function");
        }

        for (const row of this.analyze()) {
            await Promise.resolve(handler(row));
        }
    }
}

class MergePolicy {
    constructor({ requiredPositivePeriods = 2, maximumDropPercent = 10 }) {
        if (!Number.isInteger(requiredPositivePeriods) || requiredPositivePeriods < 1) {
            throw new RangeError("requiredPositivePeriods must be a positive integer");
        }

        if (!Number.isFinite(maximumDropPercent) || maximumDropPercent < 0) {
            throw new RangeError("maximumDropPercent must be non-negative");
        }

        this.requiredPositivePeriods = requiredPositivePeriods;
        this.maximumDropPercent = maximumDropPercent;
    }

    evaluate(rows) {
        const usable = rows.filter(row => row.lagPercent !== null);

        if (usable.length < this.requiredPositivePeriods) {
            return {
                eligible: false,
                reason: "Insufficient historical observations"
            };
        }

        const latest = usable[usable.length - 1];

        if (
            latest.lagPercent !== null &&
            latest.lagPercent < -this.maximumDropPercent
        ) {
            return {
                eligible: false,
                reason: "Latest period exceeds permitted decline"
            };
        }

        const recent = usable.slice(-this.requiredPositivePeriods);
        const positive = recent.every(row => row.lagDifference > 0);

        return {
            eligible: positive,
            reason: positive
                ? "Required recent periods increased"
                : "Required recent periods did not all increase"
        };
    }
}

async function main() {
    const metrics = [
        new Metric(new Date("2026-10-19T00:00:00Z"), 120),
        new Metric(new Date("2026-10-20T00:00:00Z"), 126),
        new Metric(new Date("2026-10-21T00:00:00Z"), 131),
        new Metric(new Date("2026-10-22T00:00:00Z"), 127),
        new Metric(new Date("2026-10-23T00:00:00Z"), 135),
        new Metric(new Date("2026-10-24T00:00:00Z"), 135),
        new Metric(new Date("2026-10-25T00:00:00Z"), 142)
    ];

    const analyzer = new TimeSeriesAnalyzer(metrics);
    const rows = analyzer.analyze();

    console.table(
        rows.map(row => ({
            timestamp: row.timestamp,
            value: row.value,
            lag: row.lag,
            lead: row.lead,
            lagDifference: row.lagDifference,
            leadDifference: row.leadDifference,
            lagPercent: row.lagPercent,
            leadPercent: row.leadPercent,
            lagTrend: row.lagTrend,
            leadTrend: row.leadTrend
        }))
    );

    console.log("Reversals:", analyzer.detectReversals());

    const policy = new MergePolicy({
        requiredPositivePeriods: 2,
        maximumDropPercent: 10
    });

    console.log("Policy decision:", policy.evaluate(rows));

    console.log("Event stream:");
    await analyzer.streamEvents(async row => {
        console.log(
            `${row.timestamp}: value=${row.value}, lag=${row.lag}, lead=${row.lead}`
        );
    });

    /*
     * Failure handling is demonstrated with invalid input.
     * No external dependency is needed, reducing supply-chain risk.
     */
    try {
        new TimeSeriesAnalyzer([
            new Metric(new Date("2026-01-01"), 10),
            new Metric(new Date("2026-01-01"), 20)
        ]);
    } catch (error) {
        console.log(`Validation failure captured: ${error.message}`);
    }
}

main().catch(error => {
    console.error(`Fatal error: ${error.message}`);
    process.exitCode = 1;
});
