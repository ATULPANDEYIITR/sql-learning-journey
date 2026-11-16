#!/usr/bin/env python3
"""
Variational Quantum Circuits (VQCs)
Parameterized quantum computation using state-vector simulation,
angle encoding, trainable rotations, entanglement, parameter-shift
gradients, and variational optimization.

Dependencies: Python 3.10+
External dependencies: None
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Sequence


# ============================================================
# 1. Configuration and domain types
# ============================================================

class CircuitError(Exception):
    pass


class ValidationError(Exception):
    pass


class ExperimentStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CircuitConfig:
    qubits: int = 2
    layers: int = 2
    learning_rate: float = 0.08
    epochs: int = 100
    shots: int = 0
    seed: int = 42

    def __post_init__(self):
        if not 1 <= self.qubits <= 12:
            raise ValidationError("Qubits must be between 1 and 12.")
        if not 1 <= self.layers <= 20:
            raise ValidationError("Layers must be between 1 and 20.")
        if self.learning_rate <= 0:
            raise ValidationError("Learning rate must be positive.")
        if self.epochs <= 0:
            raise ValidationError("Epochs must be positive.")
        if self.shots < 0:
            raise ValidationError("Shots cannot be negative.")


@dataclass
class TrainingResult:
    initial_loss: float
    final_loss: float
    parameters: list[float]
    epochs_completed: int
    accuracy: float
    duration_seconds: float
    status: ExperimentStatus


# ============================================================
# 2. State-vector quantum simulator
# ============================================================

class StateVectorSimulator:
    """
    Pure state-vector simulator.

    Qubit 0 is the least significant bit.
    State-vector size is 2**n.
    """

    def __init__(self, qubits: int):
        if not 1 <= qubits <= 12:
            raise ValidationError("Unsupported qubit count.")

        self.qubits = qubits
        self.dimension = 1 << qubits
        self.state = [0j] * self.dimension
        self.reset()

    def reset(self):
        self.state = [0j] * self.dimension
        self.state[0] = 1 + 0j

    def apply_single_qubit(self, qubit: int, gate):
        if not 0 <= qubit < self.qubits:
            raise CircuitError("Invalid qubit index.")

        bit = 1 << qubit
        state = self.state

        for index in range(self.dimension):
            if index & bit:
                continue

            paired = index | bit
            a, b = state[index], state[paired]

            state[index] = gate[0][0] * a + gate[0][1] * b
            state[paired] = gate[1][0] * a + gate[1][1] * b

    def ry(self, qubit: int, theta: float):
        c = math.cos(theta / 2)
        s = math.sin(theta / 2)

        self.apply_single_qubit(
            qubit,
            ((c, -s), (s, c))
        )

    def rz(self, qubit: int, theta: float):
        self.apply_single_qubit(
            qubit,
            (
                (complex(math.cos(-theta / 2),
                         math.sin(-theta / 2)), 0j),
                (0j, complex(math.cos(theta / 2),
                             math.sin(theta / 2)))
            )
        )

    def hadamard(self, qubit: int):
        scale = 1 / math.sqrt(2)
        self.apply_single_qubit(
            qubit,
            ((scale, scale), (scale, -scale))
        )

    def cnot(self, control: int, target: int):
        if control == target:
            raise CircuitError("Control and target must differ.")

        if not (0 <= control < self.qubits
                and 0 <= target < self.qubits):
            raise CircuitError("Invalid CNOT qubit.")

        control_bit = 1 << control
        target_bit = 1 << target

        for index in range(self.dimension):
            if index & control_bit and not index & target_bit:
                paired = index | target_bit
                self.state[index], self.state[paired] = (
                    self.state[paired],
                    self.state[index]
                )

    def expectation_z(self, qubit: int) -> float:
        if not 0 <= qubit < self.qubits:
            raise CircuitError("Invalid observable qubit.")

        bit = 1 << qubit

        return sum(
            (1 if not index & bit else -1) * abs(amplitude) ** 2
            for index, amplitude in enumerate(self.state)
        )

    def probabilities(self) -> list[float]:
        return [abs(amplitude) ** 2 for amplitude in self.state]

    def measure(self, shots: int, rng: random.Random):
        if shots <= 0:
            raise ValidationError("Shots must be positive.")

        probabilities = self.probabilities()
        cumulative = []
        total = 0.0

        for probability in probabilities:
            total += probability
            cumulative.append(total)

        counts = [0] * self.dimension

        for _ in range(shots):
            value = rng.random()

            for index, boundary in enumerate(cumulative):
                if value <= boundary:
                    counts[index] += 1
                    break

        return counts


# ============================================================
# 3. Variational quantum circuit
# ============================================================

class VariationalCircuit:

    def __init__(self, config: CircuitConfig):
        self.config = config
        self.simulator = StateVectorSimulator(config.qubits)

        # Each qubit has two trainable rotation parameters per layer.
        self.parameter_count = config.qubits * config.layers * 2

    def validate_parameters(self, parameters):
        if len(parameters) != self.parameter_count:
            raise ValidationError(
                f"Expected {self.parameter_count} parameters."
            )

        if not all(math.isfinite(p) for p in parameters):
            raise ValidationError("Parameters must be finite.")

    def encode_features(self, features: Sequence[float]):
        if len(features) != self.config.qubits:
            raise ValidationError("Feature count must equal qubit count.")

        if not all(math.isfinite(x) for x in features):
            raise ValidationError("Features must be finite.")

        for qubit, feature in enumerate(features):
            self.simulator.ry(qubit, feature)

    def execute(
        self,
        features: Sequence[float],
        parameters: Sequence[float]
    ) -> float:

        self.validate_parameters(parameters)
        self.simulator.reset()
        self.encode_features(features)

        position = 0

        for _ in range(self.config.layers):

            for qubit in range(self.config.qubits):
                self.simulator.ry(qubit, parameters[position])
                position += 1

                self.simulator.rz(qubit, parameters[position])
                position += 1

            # Linear entanglement chain.
            for qubit in range(self.config.qubits - 1):
                self.simulator.cnot(qubit, qubit + 1)

        return self.simulator.expectation_z(0)

    def parameter_shift_gradient(
        self,
        features: Sequence[float],
        parameters: Sequence[float]
    ) -> list[float]:
        """
        Exact parameter-shift derivative for individual RY/RZ
        parameters, each appearing once in the ansatz.
        """

        self.validate_parameters(parameters)

        gradient = []
        shift = math.pi / 2

        for index in range(self.parameter_count):
            plus = list(parameters)
            minus = list(parameters)

            plus[index] += shift
            minus[index] -= shift

            forward = self.execute(features, plus)
            backward = self.execute(features, minus)

            gradient.append((forward - backward) / 2)

        return gradient


# ============================================================
# 4. Dataset and preprocessing
# ============================================================

@dataclass(frozen=True)
class Sample:
    features: tuple[float, ...]
    label: float


def create_dataset() -> list[Sample]:
    """
    Small binary classification dataset.

    Labels are represented by expectation-value targets:
    -1 and +1.
    """

    raw = [
        ((0.15, 0.25), -1.0),
        ((0.30, 0.45), -1.0),
        ((0.45, 0.20), -1.0),
        ((2.30, 2.50), 1.0),
        ((2.65, 2.25), 1.0),
        ((2.80, 2.75), 1.0),
        ((0.20, 2.50), -1.0),
        ((2.60, 0.20), 1.0),
    ]

    return [
        Sample(tuple(features), label)
        for features, label in raw
    ]


# ============================================================
# 5. Variational optimization
# ============================================================

class VariationalTrainer:

    def __init__(self, circuit: VariationalCircuit):
        self.circuit = circuit

    @staticmethod
    def loss(predictions, targets):
        return sum(
            (prediction - target) ** 2
            for prediction, target in zip(predictions, targets)
        ) / len(targets)

    def evaluate(self, dataset, parameters):
        predictions = [
            self.circuit.execute(sample.features, parameters)
            for sample in dataset
        ]

        targets = [sample.label for sample in dataset]

        return self.loss(predictions, targets)

    def train(self, dataset: Sequence[Sample]) -> TrainingResult:
        if not dataset:
            raise ValidationError("Training dataset cannot be empty.")

        rng = random.Random(self.circuit.config.seed)

        parameters = [
            rng.uniform(-0.5, 0.5)
            for _ in range(self.circuit.parameter_count)
        ]

        targets = [sample.label for sample in dataset]

        initial_loss = self.evaluate(dataset, parameters)
        current_loss = initial_loss

        start = time.perf_counter()
        completed = 0

        try:
            for epoch in range(self.circuit.config.epochs):

                predictions = [
                    self.circuit.execute(sample.features, parameters)
                    for sample in dataset
                ]

                gradients = [0.0] * len(parameters)

                for sample, prediction, target in zip(
                    dataset, predictions, targets
                ):
                    output_gradient = 2 * (
                        prediction - target
                    ) / len(dataset)

                    circuit_gradient = (
                        self.circuit.parameter_shift_gradient(
                            sample.features, parameters
                        )
                    )

                    for index, value in enumerate(circuit_gradient):
                        gradients[index] += output_gradient * value

                # Gradient clipping prevents unusually large updates.
                norm = math.sqrt(sum(g * g for g in gradients))

                if norm > 5.0:
                    gradients = [g * 5.0 / norm for g in gradients]

                learning_rate = self.circuit.config.learning_rate

                parameters = [
                    parameter - learning_rate * gradient
                    for parameter, gradient in zip(
                        parameters, gradients
                    )
                ]

                current_loss = self.evaluate(dataset, parameters)
                completed = epoch + 1

                if epoch % 20 == 0:
                    print(
                        f"Epoch {epoch + 1:03d} | "
                        f"Loss: {current_loss:.6f}"
                    )

                if not math.isfinite(current_loss):
                    raise ArithmeticError("Non-finite training loss.")

        except Exception:
            raise

        predictions = [
            self.circuit.execute(sample.features, parameters)
            for sample in dataset
        ]

        correct = sum(
            (prediction >= 0) == (sample.label >= 0)
            for prediction, sample in zip(predictions, dataset)
        )

        accuracy = correct / len(dataset)

        return TrainingResult(
            initial_loss=initial_loss,
            final_loss=current_loss,
            parameters=parameters,
            epochs_completed=completed,
            accuracy=accuracy,
            duration_seconds=time.perf_counter() - start,
            status=ExperimentStatus.COMPLETED
        )


# ============================================================
# 6. Experiment persistence
# ============================================================

class ExperimentStore:

    def __init__(self, path: str = "vqc_experiment.json"):
        self.path = Path(path)

    def save(self, result: TrainingResult):
        payload = asdict(result)
        payload["status"] = result.status.value

        temporary = self.path.with_suffix(".tmp")

        try:
            temporary.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8"
            )

            # Atomic replacement on the same filesystem.
            temporary.replace(self.path)

        except OSError as exc:
            raise RuntimeError(
                f"Experiment persistence failed: {exc}"
            ) from exc

    def load(self):
        if not self.path.exists():
            return None

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Cannot read experiment: {exc}"
            ) from exc


# ============================================================
# 7. Classical-versus-quantum diagnostics
# ============================================================

def circuit_diagnostics(circuit, parameters):
    circuit.validate_parameters(parameters)

    return {
        "qubits": circuit.config.qubits,
        "layers": circuit.config.layers,
        "parameter_count": circuit.parameter_count,
        "state_vector_dimension": 2 ** circuit.config.qubits,
        "state_vector_memory_bytes_estimate": (
            2 ** circuit.config.qubits * 16
        ),
        "trainable_parameter_values": parameters,
        "entanglement_operations_per_execution": (
            circuit.config.layers *
            max(0, circuit.config.qubits - 1)
        ),
    }


# ============================================================
# 8. Main execution and validation
# ============================================================

def main():
    config = CircuitConfig(
        qubits=2,
        layers=2,
        learning_rate=0.08,
        epochs=100,
        seed=42
    )

    print("=" * 65)
    print("VARIATIONAL QUANTUM CIRCUIT EXPERIMENT")
    print("=" * 65)

    circuit = VariationalCircuit(config)
    dataset = create_dataset()

    print("\nCircuit configuration:")
    print(config)

    print("\nDataset size:", len(dataset))
    print("Trainable parameters:", circuit.parameter_count)

    trainer = VariationalTrainer(circuit)

    print("\nTraining:")
    result = trainer.train(dataset)

    print("\nTraining results:")
    print(f"Initial loss: {result.initial_loss:.6f}")
    print(f"Final loss:   {result.final_loss:.6f}")
    print(f"Accuracy:     {result.accuracy:.2%}")
    print(f"Epochs:       {result.epochs_completed}")
    print(f"Duration:     {result.duration_seconds:.4f}s")

    print("\nCircuit diagnostics:")
    print(json.dumps(
        circuit_diagnostics(circuit, result.parameters),
        indent=2
    ))

    print("\nPredictions:")
    for sample in dataset:
        prediction = circuit.execute(
            sample.features, result.parameters
        )

        print(
            f"Features={sample.features} "
            f"Target={sample.label:+.0f} "
            f"Prediction={prediction:+.4f} "
            f"Class={1 if prediction >= 0 else -1:+d}"
        )

    store = ExperimentStore()
    store.save(result)

    print("\nExperiment saved to:", store.path)

    # Normalization and probability checks.
    circuit.execute(dataset[0].features, result.parameters)
    probabilities = circuit.simulator.probabilities()

    assert abs(sum(probabilities) - 1.0) < 1e-9
    assert all(p >= 0 for p in probabilities)

    # Basic gate invariant.
    simulator = StateVectorSimulator(2)
    simulator.hadamard(0)
    simulator.cnot(0, 1)

    assert abs(sum(simulator.probabilities()) - 1.0) < 1e-9

    print("\nValidation tests passed.")


if __name__ == "__main__":
    main()
