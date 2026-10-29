'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');

class RunningMetrics {
    #count = 0;
    #total = 0;
    #minimum = null;
    #maximum = null;

    add(value) {
        RunningMetrics.validateNumber(value);

        this.#count += 1;
        this.#total += value;
        this.#minimum = this.#minimum === null
            ? value
            : Math.min(this.#minimum, value);
        this.#maximum = this.#maximum === null
            ? value
            : Math.max(this.#maximum, value);

        return this.snapshot();
    }

    snapshot() {
        return Object.freeze({
            count: this.#count,
            runningTotal: this.#total,
            cumulativeAverage: this.#count === 0
                ? 0
                : this.#total / this.#count,
            runningMinimum: this.#minimum,
            runningMaximum: this.#maximum
        });
    }

    static validateNumber(value) {
        if (typeof value !== 'number' || !Number.isFinite(value)) {
            throw new TypeError('value must be a finite number');
        }
    }
}

class MetricsStream extends EventEmitter {
    constructor(name) {
        super();

        if (typeof name !== 'string' || name.trim() === '') {
            throw new TypeError('stream name must be non-empty');
        }

        this.name = name;
        this.metrics = new RunningMetrics();
        this.sequence = 0;
    }

    push(value, metadata = {}) {
        const snapshot = this.metrics.add(value);

        const event = Object.freeze({
            sequence: ++this.sequence,
            stream: this.name,
            value,
            ...snapshot,
            metadata: Object.freeze({ ...metadata })
        });

        this.emit('metric', event);
        return event;
    }

    async process(values, delayMs = 0) {
        if (!Number.isInteger(delayMs) || delayMs < 0) {
            throw new RangeError('delayMs must be a non-negative integer');
        }

        const results = [];

        for (const value of values) {
            if (delayMs > 0) {
                await new Promise(resolve => setTimeout(resolve, delayMs));
            }

            results.push(this.push(value));
        }

        return results;
    }
}

function runningTotals(values) {
    let total = 0;

    return values.map(value => {
        RunningMetrics.validateNumber(value);
        total += value;
        return total;
    });
}

function cumulativeAverages(values) {
    let total = 0;

    return values.map((value, index) => {
        RunningMetrics.validateNumber(value);
        total += value;
        return total / (index + 1);
    });
}

function evaluateThreshold(snapshot, threshold) {
    RunningMetrics.validateNumber(threshold);

    return Object.freeze({
        exceeded: snapshot.runningTotal > threshold,
        remaining: Math.max(0, threshold - snapshot.runningTotal)
    });
}

async function runDemo() {
    const stream = new MetricsStream('production-sales');

    stream.on('metric', event => {
        const threshold = evaluateThreshold(event, 5000);

        console.log(
            `${event.sequence}. ${event.value.toFixed(2)} | ` +
            `total=${event.runningTotal.toFixed(2)} | ` +
            `average=${event.cumulativeAverage.toFixed(2)} | ` +
            `thresholdExceeded=${threshold.exceeded}`
        );
    });

    const values = [1200, 850, 1475, 625, 1100];

    const events = await stream.process(values);

    assert.deepEqual(runningTotals([10, 20, 30]), [10, 30, 60]);
    assert.deepEqual(cumulativeAverages([10, 20, 30]), [10, 15, 20]);
    assert.equal(events.at(-1).runningTotal, 5250);
    assert.equal(events.at(-1).cumulativeAverage, 1050);

    try {
        stream.push(Number.NaN);
        assert.fail('NaN should be rejected');
    } catch (error) {
        assert.equal(error instanceof TypeError, true);
    }

    console.log('\nFinal snapshot:');
    console.log(stream.metrics.snapshot());

    console.log('\nComplexity: O(1) state and O(1) update time per observation.');
}

runDemo().catch(error => {
    console.error(`Processing failed: ${error.message}`);
    process.exitCode = 1;
});
