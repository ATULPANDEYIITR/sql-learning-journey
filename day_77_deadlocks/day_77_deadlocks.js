"use strict";

/*
 * Variational Quantum Circuits
 * Event-driven parameterized quantum computation.
 *
 * Runtime: Node.js 18+
 * Dependencies: Node.js standard library only.
 */

const fs = require("node:fs/promises");
const { EventEmitter } = require("node:events");
const { performance } = require("node:perf_hooks");

// ============================================================
// 1. Domain errors and configuration
// ============================================================

class ValidationError extends Error {}
class CircuitError extends Error {}
class PolicyError extends Error {}

const ExperimentState = Object.freeze({
    CREATED: "CREATED",
    RUNNING: "RUNNING",
    COMPLETED: "COMPLETED",
    FAILED: "FAILED"
});

class CircuitConfiguration {
    constructor({
        qubits = 2,
        layers = 2,
        learningRate = 0.08,
        epochs = 80,
        seed = 42,
        maxEvaluations = 100000
    } = {}) {
        if (!Number.isInteger(qubits) || qubits < 1 || qubits > 12) {
            throw new ValidationError("Qubit count must be between 1 and 12.");
        }

        if (!Number.isInteger(layers) || layers < 1 || layers > 20) {
            throw new ValidationError("Invalid circuit depth.");
        }

        if (!Number.isFinite(learningRate) || learningRate <= 0) {
            throw new ValidationError("Invalid learning rate.");
        }

        if (!Number.isInteger(epochs) || epochs < 1) {
            throw new ValidationError("Invalid epoch count.");
        }

        if (!Number.isSafeInteger(maxEvaluations) || maxEvaluations < 1) {
            throw new ValidationError("Invalid evaluation budget.");
        }

        this.qubits = qubits;
        this.layers = layers;
        this.learningRate = learningRate;
        this.epochs = epochs;
        this.seed = seed;
        this.maxEvaluations = maxEvaluations;
        Object.freeze(this);
    }

    get parameterCount() {
        return this.qubits * this.layers * 2;
    }
}

// ============================================================
// 2. Deterministic random-number generator
// ============================================================

class RandomGenerator {
    constructor(seed) {
        this.state = seed >>> 0;
    }

    next() {
        this.state = (
            1664525 * this.state + 1013904223
        ) >>> 0;

        return this.state / 4294967296;
    }

    between(min, max) {
        return min + this.next() * (max - min);
    }
}

// ============================================================
// 3. Complex arithmetic
// ============================================================

class Complex {
    constructor(real = 0, imag = 0) {
        this.real = real;
        this.imag = imag;
    }

    add(other) {
        return new Complex(
            this.real + other.real,
            this.imag + other.imag
        );
    }

    multiply(other) {
        return new Complex(
            this.real * other.real - this.imag * other.imag,
            this.real * other.imag + this.imag * other.real
        );
    }

    scale(value) {
        return new Complex(
            this.real * value,
            this.imag * value
        );
    }

    magnitudeSquared() {
        return this.real ** 2 + this.imag ** 2;
    }
}

// ============================================================
// 4. Quantum state-vector engine
// ============================================================

class QuantumRegister {
    constructor(qubits) {
        if (!Number.isInteger(qubits) || qubits < 1 || qubits > 12) {
            throw new ValidationError("Unsupported register size.");
        }

        this.qubits = qubits;
        this.dimension = 2 ** qubits;
        this.reset();
    }

    reset() {
        this.state = Array.from(
            { length: this.dimension },
            () => new Complex()
        );

        this.state[0] = new Complex(1, 0);
    }

    applyGate(qubit, matrix) {
        if (!Number.isInteger(qubit) ||
            qubit < 0 || qubit >= this.qubits) {
            throw new CircuitError("Invalid qubit.");
        }

        const mask = 1 << qubit;

        for (let index = 0; index < this.dimension; index++) {
            if ((index & mask) !== 0) continue;

            const paired = index | mask;
            const a = this.state[index];
            const b = this.state[paired];

            this.state[index] = matrix[0][0].multiply(a)
                .add(matrix[0][1].multiply(b));

            this.state[paired] = matrix[1][0].multiply(a)
                .add(matrix[1][1].multiply(b));
        }
    }

    ry(qubit, angle) {
        const c = Math.cos(angle / 2);
        const s = Math.sin(angle / 2);

        this.applyGate(qubit, [
            [new Complex(c), new Complex(-s)],
            [new Complex(s), new Complex(c)]
        ]);
    }

    rz(qubit, angle) {
        const c = Math.cos(angle / 2);
        const s = Math.sin(angle / 2);

        this.applyGate(qubit, [
            [new Complex(c, -s), new Complex()],
            [new Complex(), new Complex(c, s)]
        ]);
    }

    cnot(control, target) {
        if (control === target ||
            control < 0 || target < 0 ||
            control >= this.qubits ||
            target >= this.qubits) {
            throw new CircuitError("Invalid CNOT operation.");
        }

        const controlMask = 1 << control;
        const targetMask = 1 << target;

        for (let index = 0; index < this.dimension; index++) {
            if ((index & controlMask) &&
                !(index & targetMask)) {
                const paired = index | targetMask;

                [this.state[index], this.state[paired]] =
                    [this.state[paired], this.state[index]];
            }
        }
    }

    expectationZ(qubit) {
        const mask = 1 << qubit;
        let expectation = 0;

        for (let index = 0; index < this.dimension; index++) {
            const probability = this.state[index].magnitudeSquared();

            expectation += (index & mask ? -1 : 1) * probability;
        }

        return expectation;
    }

    probabilities() {
        return this.state.map(
            amplitude => amplitude.magnitudeSquared()
        );
    }
}

// ============================================================
// 5. Parameterized circuit
// ============================================================

class VariationalCircuit {
    constructor(configuration) {
        this.configuration = configuration;
        this.register = new QuantumRegister(configuration.qubits);
        this.evaluationCount = 0;
    }

    validate(features, parameters) {
        if (!Array.isArray(features) ||
            features.length !== this.configuration.qubits) {
            throw new ValidationError("Incorrect feature dimensions.");
        }

        if (!features.every(Number.isFinite)) {
            throw new ValidationError("Features must be finite.");
        }

        if (!Array.isArray(parameters) ||
            parameters.length !== this.configuration.parameterCount) {
            throw new ValidationError("Incorrect parameter dimensions.");
        }

        if (!parameters.every(Number.isFinite)) {
            throw new ValidationError("Parameters must be finite.");
        }
    }

    execute(features, parameters) {
        this.validate(features, parameters);

        if (++this.evaluationCount >
            this.configuration.maxEvaluations) {
            throw new PolicyError("Circuit evaluation budget exceeded.");
        }

        this.register.reset();

        // Data encoding.
        features.forEach((feature, qubit) => {
            this.register.ry(qubit, feature);
        });

        let position = 0;

        for (let layer = 0;
             layer < this.configuration.layers;
             layer++) {

            for (let qubit = 0;
                 qubit < this.configuration.qubits;
                 qubit++) {

                this.register.ry(
                    qubit,
                    parameters[position++]
                );

                this.register.rz(
                    qubit,
                    parameters[position++]
                );
            }

            // Entangling operation.
            for (let qubit = 0;
                 qubit < this.configuration.qubits - 1;
                 qubit++) {

                this.register.cnot(qubit, qubit + 1);
            }
        }

        return this.register.expectationZ(0);
    }

    parameterShiftGradient(features, parameters) {
        const shift = Math.PI / 2;
        const gradient = [];

        for (let index = 0; index < parameters.length; index++) {
            const plus = [...parameters];
            const minus = [...parameters];

            plus[index] += shift;
            minus[index] -= shift;

            const upper = this.execute(features, plus);
            const lower = this.execute(features, minus);

            gradient.push((upper - lower) / 2);
        }

        return gradient;
    }
}

// ============================================================
// 6. Event-driven experiment manager
// ============================================================

class ExperimentManager extends EventEmitter {
    constructor(configuration) {
        super();

        this.configuration = configuration;
        this.circuit = new VariationalCircuit(configuration);
        this.state = ExperimentState.CREATED;
        this.history = [];
        this.running = false;
    }

    transition(next) {
        const allowed = {
            CREATED: ["RUNNING"],
            RUNNING: ["COMPLETED", "FAILED"],
            COMPLETED: [],
            FAILED: []
        };

        if (!allowed[this.state].includes(next)) {
            throw new CircuitError(
                `Invalid transition: ${this.state} -> ${next}`
            );
        }

        const previous = this.state;
        this.state = next;

        this.emit("stateChanged", { previous, next });
    }

    async train(dataset) {
        if (this.running) {
            throw new PolicyError("Experiment is already running.");
        }

        if (this.state !== ExperimentState.CREATED) {
            throw new PolicyError("Experiment cannot be restarted.");
        }

        if (!Array.isArray(dataset) || dataset.length === 0) {
            throw new ValidationError("Dataset cannot be empty.");
        }

        for (const sample of dataset) {
            if (!Array.isArray(sample.features) ||
                sample.features.length !== this.configuration.qubits ||
                !sample.features.every(Number.isFinite) ||
                ![-1, 1].includes(sample.label)) {
                throw new ValidationError("Invalid training sample.");
            }
        }

        this.running = true;
        this.transition(ExperimentState.RUNNING);

        const start = performance.now();
        const random = new RandomGenerator(this.configuration.seed);

        let parameters = Array.from(
            { length: this.configuration.parameterCount },
            () => random.between(-0.5, 0.5)
        );

        const mse = async currentParameters => {
            let total = 0;

            for (const sample of dataset) {
                const prediction = this.circuit.execute(
                    sample.features,
                    currentParameters
                );

                total += (prediction - sample.label) ** 2;
            }

            return total / dataset.length;
        };

        try {
            const initialLoss = await mse(parameters);

            for (let epoch = 0;
                 epoch < this.configuration.epochs;
                 epoch++) {

                const gradient = Array(parameters.length).fill(0);

                for (const sample of dataset) {
                    const prediction = this.circuit.execute(
                        sample.features,
                        parameters
                    );

                    const derivative = this.circuit.parameterShiftGradient(
                        sample.features,
                        parameters
                    );

                    const scale = (
                        2 * (prediction - sample.label) / dataset.length
                    );

                    derivative.forEach((value, index) => {
                        gradient[index] += scale * value;
                    });
                }

                // Bound gradient norm.
                const norm = Math.sqrt(
                    gradient.reduce(
                        (sum, value) => sum + value * value, 0
                    )
                );

                const scale = norm > 5 ? 5 / norm : 1;

                parameters = parameters.map(
                    (parameter, index) =>
                        parameter -
                        this.configuration.learningRate *
                        gradient[index] * scale
                );

                const loss = await mse(parameters);

                const event = {
                    epoch: epoch + 1,
                    loss,
                    evaluationCount: this.circuit.evaluationCount
                };

                this.history.push(event);
                this.emit("epochCompleted", event);

                if (!Number.isFinite(loss)) {
                    throw new CircuitError("Training diverged.");
                }

                // Yield periodically to the Node.js event loop.
                if (epoch % 5 === 0) {
                    await new Promise(resolve => setImmediate(resolve));
                }
            }

            const predictions = dataset.map(sample =>
                this.circuit.execute(sample.features, parameters)
            );

            const accuracy = predictions.reduce(
                (correct, prediction, index) =>
                    correct +
                    (Number(prediction >= 0) ===
                     Number(dataset[index].label >= 0) ? 1 : 0),
                0
            ) / dataset.length;

            const result = {
                initialLoss,
                finalLoss: this.history.at(-1).loss,
                parameters,
                accuracy,
                durationMilliseconds: performance.now() - start,
                evaluations: this.circuit.evaluationCount,
                state: ExperimentState.COMPLETED
            };

            this.transition(ExperimentState.COMPLETED);
            this.emit("experimentCompleted", result);

            return result;

        } catch (error) {
            this.transition(ExperimentState.FAILED);
            this.emit("experimentFailed", error);
            throw error;

        } finally {
            this.running = false;
        }
    }
}

// ============================================================
// 7. Evaluation policy
// ============================================================

class ExecutionPolicy {
    constructor({
        maximumQubits = 8,
        maximumLayers = 10,
        maximumEvaluations = 100000
    } = {}) {
        this.maximumQubits = maximumQubits;
        this.maximumLayers = maximumLayers;
        this.maximumEvaluations = maximumEvaluations;
    }

    evaluate(configuration) {
        const violations = [];

        if (configuration.qubits > this.maximumQubits) {
            violations.push("Qubit limit exceeded.");
        }

        if (configuration.layers > this.maximumLayers) {
            violations.push("Depth limit exceeded.");
        }

        if (configuration.maxEvaluations > this.maximumEvaluations) {
            violations.push("Evaluation budget exceeded.");
        }

        return {
            eligible: violations.length === 0,
            violations
        };
    }
}

// ============================================================
// 8. Persistent experiment records
// ============================================================

class ExperimentRepository {
    constructor(filePath = "vqc_experiments.json") {
        this.filePath = filePath;
    }

    async append(result) {
        let records = [];

        try {
            const contents = await fs.readFile(
                this.filePath,
                "utf8"
            );

            records = JSON.parse(contents);

            if (!Array.isArray(records)) {
                throw new ValidationError("Invalid experiment archive.");
            }

        } catch (error) {
            if (error.code !== "ENOENT") throw error;
        }

        records.push({
            id: `${Date.now()}-${records.length + 1}`,
            createdAt: new Date().toISOString(),
            ...result
        });

        const temporary = `${this.filePath}.tmp`;

        await fs.writeFile(
            temporary,
            JSON.stringify(records, null, 2),
            { encoding: "utf8", mode: 0o600 }
        );

        await fs.rename(temporary, this.filePath);
    }
}

// ============================================================
// 9. Dataset and application workflow
// ============================================================

const dataset = [
    { features: [0.15, 0.25], label: -1 },
    { features: [0.30, 0.45], label: -1 },
    { features: [0.45, 0.20], label: -1 },
    { features: [2.30, 2.50], label: 1 },
    { features: [2.65, 2.25], label: 1 },
    { features: [2.80, 2.75], label: 1 },
    { features: [0.20, 2.50], label: -1 },
    { features: [2.60, 0.20], label: 1 }
];

async function main() {
    const configuration = new CircuitConfiguration({
        qubits: 2,
        layers: 2,
        learningRate: 0.08,
        epochs: 80,
        maxEvaluations: 100000
    });

    const policy = new ExecutionPolicy();
    const decision = policy.evaluate(configuration);

    if (!decision.eligible) {
        throw new PolicyError(decision.violations.join(" "));
    }

    const experiment = new ExperimentManager(configuration);

    experiment.on("stateChanged", event => {
        console.log(
            `State: ${event.previous} -> ${event.next}`
        );
    });

    experiment.on("epochCompleted", event => {
        if (event.epoch % 20 === 1) {
            console.log(
                `Epoch ${event.epoch}: loss=${event.loss.toFixed(6)}`
            );
        }
    });

    experiment.on("experimentFailed", error => {
        console.error("Experiment failed:", error.message);
    });

    const result = await experiment.train(dataset);

    console.log("\nTraining result:");
    console.log(JSON.stringify(result, null, 2));

    const repository = new ExperimentRepository();
    await repository.append(result);

    console.log("\nExperiment archived.");

    // Validate probability normalization.
    const circuit = new VariationalCircuit(configuration);

    circuit.execute(dataset[0].features, result.parameters);

    const probabilitySum = circuit.register
        .probabilities()
        .reduce((sum, value) => sum + value, 0);

    if (Math.abs(probabilitySum - 1) > 1e-9) {
        throw new CircuitError("State normalization failed.");
    }

    console.log("State normalization verified.");
}

main().catch(error => {
    console.error(error.name + ":", error.message);
    process.exitCode = 1;
});
