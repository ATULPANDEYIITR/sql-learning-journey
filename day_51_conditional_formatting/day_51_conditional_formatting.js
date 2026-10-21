"use strict";

/*
 * Conditional aggregation is represented here through reusable reducers.
 * The implementation intentionally uses JavaScript's event-driven model:
 * KPI calculations are exposed through an asynchronous report service that
 * could be connected to a database or HTTP endpoint without changing the
 * aggregation rules.
 */

class Order {
    constructor({
        id,
        customerId,
        region,
        status,
        channel,
        amount,
        returned = false,
    }) {
        if (!Number.isInteger(id) || id <= 0) {
            throw new Error("Order id must be a positive integer.");
        }
        if (!Number.isInteger(customerId) || customerId <= 0) {
            throw new Error("Customer id must be a positive integer.");
        }
        if (!region || !region.trim()) {
            throw new Error("Region is required.");
        }
        if (!["completed", "cancelled", "pending"].includes(status)) {
            throw new Error(`Invalid order status: ${status}`);
        }
        if (!["web", "mobile", "store"].includes(channel)) {
            throw new Error(`Invalid sales channel: ${channel}`);
        }
        if (!Number.isFinite(amount) || amount < 0) {
            throw new Error("Amount must be a non-negative finite number.");
        }

        this.id = id;
        this.customerId = customerId;
        this.region = region;
        this.status = status;
        this.channel = channel;
        this.amount = Number(amount.toFixed(2));
        this.returned = Boolean(returned);
    }
}

class ConditionalAggregator {
    static sum(rows, predicate, valueSelector = row => row.amount) {
        return rows
            .filter(predicate)
            .reduce((total, row) => total + valueSelector(row), 0);
    }

    static count(rows, predicate) {
        return rows.reduce(
            (count, row) => count + (predicate(row) ? 1 : 0),
            0
        );
    }

    static average(rows, predicate, valueSelector = row => row.amount) {
        const matching = rows.filter(predicate);
        if (matching.length === 0) {
            return 0;
        }

        return (
            matching.reduce(
                (total, row) => total + valueSelector(row),
                0
            ) / matching.length
        );
    }

    static percentage(numerator, denominator) {
        return denominator === 0
            ? 0
            : Number(((numerator / denominator) * 100).toFixed(2));
    }
}

class KPIReportService {
    constructor(orders) {
        if (!Array.isArray(orders)) {
            throw new TypeError("Orders must be an array.");
        }
        this.orders = orders;
    }

    async generate() {
        // Promise.resolve models an asynchronous boundary such as a database query.
        await Promise.resolve();

        const completed = row => row.status === "completed";
        const cancelled = row => row.status === "cancelled";

        const completedCount = ConditionalAggregator.count(
            this.orders,
            completed
        );

        const cancelledCount = ConditionalAggregator.count(
            this.orders,
            cancelled
        );

        const report = {
            totalOrders: this.orders.length,

            completedOrders: completedCount,

            cancelledOrders: cancelledCount,

            pendingOrders: ConditionalAggregator.count(
                this.orders,
                row => row.status === "pending"
            ),

            completedRevenue: ConditionalAggregator.sum(
                this.orders,
                completed
            ),

            cancelledValue: ConditionalAggregator.sum(
                this.orders,
                cancelled
            ),

            webCompletedRevenue: ConditionalAggregator.sum(
                this.orders,
                row => row.status === "completed" && row.channel === "web"
            ),

            mobileCompletedRevenue: ConditionalAggregator.sum(
                this.orders,
                row =>
                    row.status === "completed" &&
                    row.channel === "mobile"
            ),

            returnedCompletedOrders: ConditionalAggregator.count(
                this.orders,
                row => row.status === "completed" && row.returned
            ),

            averageCompletedOrder: ConditionalAggregator.average(
                this.orders,
                completed
            ),

            completionRate: ConditionalAggregator.percentage(
                completedCount,
                this.orders.length
            ),

            cancellationRate: ConditionalAggregator.percentage(
                cancelledCount,
                this.orders.length
            ),
        };

        return Object.fromEntries(
            Object.entries(report).map(([key, value]) => [
                key,
                typeof value === "number" ? Number(value.toFixed(2)) : value,
            ])
        );
    }

    async regionalReport() {
        await Promise.resolve();

        const regions = [...new Set(this.orders.map(order => order.region))]
            .sort();

        return regions.map(region => {
            const rows = this.orders.filter(
                order => order.region === region
            );

            const completed = ConditionalAggregator.count(
                rows,
                order => order.status === "completed"
            );

            return {
                region,
                orders: rows.length,
                completed,
                cancelled: ConditionalAggregator.count(
                    rows,
                    order => order.status === "cancelled"
                ),
                revenue: Number(
                    ConditionalAggregator.sum(
                        rows,
                        order => order.status === "completed"
                    ).toFixed(2)
                ),
                webRevenue: Number(
                    ConditionalAggregator.sum(
                        rows,
                        order =>
                            order.status === "completed" &&
                            order.channel === "web"
                    ).toFixed(2)
                ),
                returnedCompleted: ConditionalAggregator.count(
                    rows,
                    order =>
                        order.status === "completed" &&
                        order.returned
                ),
                completionRate: ConditionalAggregator.percentage(
                    completed,
                    rows.length
                ),
            };
        });
    }
}

function buildOrders() {
    return [
        new Order({
            id: 1,
            customerId: 101,
            region: "North",
            status: "completed",
            channel: "web",
            amount: 1250,
        }),
        new Order({
            id: 2,
            customerId: 102,
            region: "North",
            status: "cancelled",
            channel: "mobile",
            amount: 800,
        }),
        new Order({
            id: 3,
            customerId: 103,
            region: "South",
            status: "completed",
            channel: "mobile",
            amount: 2100,
        }),
        new Order({
            id: 4,
            customerId: 104,
            region: "South",
            status: "completed",
            channel: "web",
            amount: 1750,
            returned: true,
        }),
        new Order({
            id: 5,
            customerId: 105,
            region: "East",
            status: "pending",
            channel: "web",
            amount: 900,
        }),
        new Order({
            id: 6,
            customerId: 106,
            region: "East",
            status: "completed",
            channel: "store",
            amount: 3200,
        }),
        new Order({
            id: 7,
            customerId: 107,
            region: "West",
            status: "cancelled",
            channel: "web",
            amount: 600,
        }),
        new Order({
            id: 8,
            customerId: 108,
            region: "West",
            status: "completed",
            channel: "mobile",
            amount: 1450,
        }),
        new Order({
            id: 9,
            customerId: 109,
            region: "North",
            status: "completed",
            channel: "web",
            amount: 2800,
        }),
        new Order({
            id: 10,
            customerId: 110,
            region: "South",
            status: "pending",
            channel: "mobile",
            amount: 1100,
        }),
    ];
}

async function main() {
    const service = new KPIReportService(buildOrders());

    const report = await service.generate();

    console.log("Overall KPI Report");
    console.table(report);

    const regional = await service.regionalReport();

    console.log("Regional Conditional Metrics");
    console.table(regional);

    // A predicate that matches nothing must safely return zero.
    const noMatchingRevenue = ConditionalAggregator.sum(
        service.orders,
        order => order.amount > 1000000
    );

    if (noMatchingRevenue !== 0) {
        throw new Error("Unexpected result for an empty conditional set.");
    }

    // Conditional counts must partition the mutually exclusive statuses.
    const statusTotal =
        report.completedOrders +
        report.cancelledOrders +
        report.pendingOrders;

    if (statusTotal !== report.totalOrders) {
        throw new Error("Status aggregation failed validation.");
    }

    console.log("Aggregation validation: passed");
}

main().catch(error => {
    console.error(`Report generation failed: ${error.message}`);
    process.exitCode = 1;
});
