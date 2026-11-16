#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std;

using Complex = complex<double>;
using StateVector = vector<Complex>;

constexpr double PI = 3.14159265358979323846;
constexpr double EPSILON = 1e-10;

// ============================================================
// 1. Domain model
// ============================================================

enum class CheckStatus {
    Pending,
    Passed,
    Failed
};

enum class ExperimentStatus {
    Created,
    Running,
    Completed,
    Failed
};

struct Configuration {
    int qubits = 2;
    int layers = 2;
    int epochs = 100;
    double learningRate = 0.08;
    double gradientClip = 5.0;
    uint64_t seed = 42;

    void validate() const {
        if (qubits < 1 || qubits > 12) {
            throw invalid_argument("Qubit count must be 1-12.");
        }

        if (layers < 1 || layers > 20) {
            throw invalid_argument("Layer count must be 1-20.");
        }

        if (epochs < 1 || learningRate <= 0 ||
            !isfinite(learningRate)) {
            throw invalid_argument("Invalid optimizer configuration.");
        }

        if (gradientClip <= 0) {
            throw invalid_argument("Gradient clipping must be positive.");
        }
    }

    size_t parameterCount() const {
        return static_cast<size_t>(qubits) * layers * 2;
    }
};

struct Sample {
    vector<double> features;
    double target;
};

struct Evaluation {
    double expectation = 0;
    double probabilityZero = 0;
    double probabilityOne = 0;
};

struct TrainingMetrics {
    double initialLoss = 0;
    double finalLoss = 0;
    double accuracy = 0;
    size_t completedEpochs = 0;
    size_t circuitEvaluations = 0;
};

// ============================================================
// 2. Quantum register
// ============================================================

class QuantumRegister {
private:
    int qubits;
    size_t dimension;
    StateVector state;

public:
    explicit QuantumRegister(int count)
        : qubits(count), dimension(1ULL << count) {

        if (count < 1 || count > 12) {
            throw invalid_argument("Unsupported qubit count.");
        }

        reset();
    }

    void reset() {
        state.assign(dimension, Complex(0, 0));
        state[0] = Complex(1, 0);
    }

    void applySingleQubit(
        int qubit,
        const array<array<Complex, 2>, 2>& matrix
    ) {
        if (qubit < 0 || qubit >= qubits) {
            throw out_of_range("Invalid qubit index.");
        }

        const size_t mask = 1ULL << qubit;

        for (size_t i = 0; i < dimension; ++i) {
            if (i & mask) continue;

            size_t j = i | mask;

            Complex a = state[i];
            Complex b = state[j];

            state[i] = matrix[0][0] * a + matrix[0][1] * b;
            state[j] = matrix[1][0] * a + matrix[1][1] * b;
        }
    }

    void ry(int qubit, double angle) {
        double c = cos(angle / 2);
        double s = sin(angle / 2);

        array<array<Complex, 2>, 2> matrix{{
            {c, -s},
            {s, c}
        }};

        applySingleQubit(qubit, matrix);
    }

    void rz(int qubit, double angle) {
        Complex upper = polar(1.0, -angle / 2);
        Complex lower = polar(1.0, angle / 2);

        array<array<Complex, 2>, 2> matrix{{
            {upper, Complex(0, 0)},
            {Complex(0, 0), lower}
        }};

        applySingleQubit(qubit, matrix);
    }

    void hadamard(int qubit) {
        const double scale = 1.0 / sqrt(2.0);

        array<array<Complex, 2>, 2> matrix{{
            {scale, scale},
            {scale, -scale}
        }};

        applySingleQubit(qubit, matrix);
    }

    void cnot(int control, int target) {
        if (control == target ||
            control < 0 || target < 0 ||
            control >= qubits || target >= qubits) {
            throw invalid_argument("Invalid CNOT configuration.");
        }

        const size_t controlMask = 1ULL << control;
        const size_t targetMask = 1ULL << target;

        for (size_t i = 0; i < dimension; ++i) {
            if ((i & controlMask) && !(i & targetMask)) {
                size_t j = i | targetMask;
                swap(state[i], state[j]);
            }
        }
    }

    double expectationZ(int qubit) const {
        if (qubit < 0 || qubit >= qubits) {
            throw out_of_range("Invalid observable qubit.");
        }

        const size_t mask = 1ULL << qubit;
        double result = 0;

        for (size_t i = 0; i < dimension; ++i) {
            double probability = norm(state[i]);

            result += (i & mask ? -1.0 : 1.0) * probability;
        }

        return result;
    }

    vector<double> probabilities() const {
        vector<double> result(dimension);

        for (size_t i = 0; i < dimension; ++i) {
            result[i] = norm(state[i]);
        }

        return result;
    }

    double normalizationError() const {
        auto values = probabilities();

        double total = accumulate(
            values.begin(), values.end(), 0.0
        );

        return abs(total - 1.0);
    }

    const StateVector& amplitudes() const {
        return state;
    }

    size_t size() const {
        return dimension;
    }
};

// ============================================================
// 3. Variational circuit
// ============================================================

class VariationalCircuit {
private:
    Configuration config;
    QuantumRegister quantumRegister;
    size_t evaluations = 0;

    void validateParameters(
        const vector<double>& parameters
    ) const {
        if (parameters.size() != config.parameterCount()) {
            throw invalid_argument("Incorrect parameter count.");
        }

        for (double value : parameters) {
            if (!isfinite(value)) {
                throw invalid_argument("Non-finite parameter.");
            }
        }
    }

    void validateFeatures(const vector<double>& features) const {
        if (features.size() != static_cast<size_t>(config.qubits)) {
            throw invalid_argument("Incorrect feature count.");
        }

        for (double feature : features) {
            if (!isfinite(feature)) {
                throw invalid_argument("Non-finite feature.");
            }
        }
    }

public:
    explicit VariationalCircuit(Configuration configuration)
        : config(configuration),
          quantumRegister(configuration.qubits) {

        config.validate();
    }

    double execute(
        const vector<double>& features,
        const vector<double>& parameters
    ) {
        validateFeatures(features);
        validateParameters(parameters);

        if (evaluations >= 1000000) {
            throw runtime_error("Circuit evaluation budget exceeded.");
        }

        ++evaluations;
        quantumRegister.reset();

        // Encode classical data into quantum rotation angles.
        for (int q = 0; q < config.qubits; ++q) {
            quantumRegister.ry(q, features[q]);
        }

        size_t position = 0;

        for (int layer = 0; layer < config.layers; ++layer) {

            for (int q = 0; q < config.qubits; ++q) {
                quantumRegister.ry(q, parameters[position++]);
                quantumRegister.rz(q, parameters[position++]);
            }

            // Linear entanglement topology.
            for (int q = 0; q < config.qubits - 1; ++q) {
                quantumRegister.cnot(q, q + 1);
            }
        }

        return quantumRegister.expectationZ(0);
    }

    vector<double> parameterShiftGradient(
        const vector<double>& features,
        const vector<double>& parameters
    ) {
        validateParameters(parameters);

        vector<double> gradient(parameters.size());
        constexpr double shift = PI / 2;

        for (size_t i = 0; i < parameters.size(); ++i) {
            auto plus = parameters;
            auto minus = parameters;

            plus[i] += shift;
            minus[i] -= shift;

            double upper = execute(features, plus);
            double lower = execute(features, minus);

            gradient[i] = (upper - lower) / 2;
        }

        return gradient;
    }

    Evaluation evaluate(
        const vector<double>& features,
        const vector<double>& parameters
    ) {
        double expectation = execute(features, parameters);

        return {
            expectation,
            (1.0 + expectation) / 2.0,
            (1.0 - expectation) / 2.0
        };
    }

    size_t evaluationCount() const {
        return evaluations;
    }

    double normalizationError() const {
        return quantumRegister.normalizationError();
    }
};

// ============================================================
// 4. Optimizer
// ============================================================

class GradientDescent {
private:
    double learningRate;
    double clipValue;

public:
    GradientDescent(double rate, double clipping)
        : learningRate(rate), clipValue(clipping) {

        if (rate <= 0 || clipping <= 0) {
            throw invalid_argument("Invalid optimizer settings.");
        }
    }

    void update(
        vector<double>& parameters,
        const vector<double>& gradient
    ) const {
        if (parameters.size() != gradient.size()) {
            throw invalid_argument("Gradient dimension mismatch.");
        }

        double squaredNorm = inner_product(
            gradient.begin(),
            gradient.end(),
            gradient.begin(),
            0.0
        );

        double norm = sqrt(squaredNorm);
        double scale = norm > clipValue ? clipValue / norm : 1.0;

        for (size_t i = 0; i < parameters.size(); ++i) {
            parameters[i] -= learningRate * gradient[i] * scale;
        }
    }
};

// ============================================================
// 5. Dataset
// ============================================================

vector<Sample> createDataset() {
    return {
        {{0.15, 0.25}, -1},
        {{0.30, 0.45}, -1},
        {{0.45, 0.20}, -1},
        {{2.30, 2.50}, 1},
        {{2.65, 2.25}, 1},
        {{2.80, 2.75}, 1},
        {{0.20, 2.50}, -1},
        {{2.60, 0.20}, 1}
    };
}

// ============================================================
// 6. Training service
// ============================================================

class TrainingService {
private:
    VariationalCircuit circuit;
    Configuration config;
    GradientDescent optimizer;
    ExperimentStatus status = ExperimentStatus::Created;

    double calculateLoss(
        const vector<Sample>& dataset,
        const vector<double>& parameters
    ) {
        double total = 0;

        for (const auto& sample : dataset) {
            double prediction = circuit.execute(
                sample.features, parameters
            );

            total += pow(prediction - sample.target, 2);
        }

        return total / dataset.size();
    }

public:
    explicit TrainingService(Configuration configuration)
        : circuit(configuration),
          config(configuration),
          optimizer(
              configuration.learningRate,
              configuration.gradientClip
          ) {}

    TrainingMetrics train(const vector<Sample>& dataset) {
        if (status != ExperimentStatus::Created) {
            throw logic_error("Experiment already started.");
        }

        if (dataset.empty()) {
            throw invalid_argument("Dataset cannot be empty.");
        }

        for (const auto& sample : dataset) {
            if (sample.features.size() !=
                static_cast<size_t>(config.qubits)) {
                throw invalid_argument("Invalid feature dimension.");
            }

            if (sample.target != -1 && sample.target != 1) {
                throw invalid_argument("Target must be -1 or +1.");
            }
        }

        status = ExperimentStatus::Running;

        try {
            mt19937_64 generator(config.seed);
            uniform_real_distribution<double> distribution(-0.5, 0.5);

            vector<double> parameters(config.parameterCount());

            generate(
                parameters.begin(),
                parameters.end(),
                [&]() { return distribution(generator); }
            );

            TrainingMetrics metrics;
            metrics.initialLoss = calculateLoss(dataset, parameters);

            for (int epoch = 0; epoch < config.epochs; ++epoch) {
                vector<double> gradient(parameters.size(), 0.0);

                for (const auto& sample : dataset) {
                    double prediction = circuit.execute(
                        sample.features, parameters
                    );

                    vector<double> localGradient =
                        circuit.parameterShiftGradient(
                            sample.features, parameters
                        );

                    double scale = 2.0 *
                        (prediction - sample.target) / dataset.size();

                    for (size_t i = 0; i < gradient.size(); ++i) {
                        gradient[i] += scale * localGradient[i];
                    }
                }

                optimizer.update(parameters, gradient);

                double loss = calculateLoss(dataset, parameters);

                if (!isfinite(loss)) {
                    throw runtime_error("Training produced invalid loss.");
                }

                metrics.completedEpochs = epoch + 1;

                if (epoch % 20 == 0) {
                    cout << "Epoch " << epoch + 1
                         << " | Loss: " << fixed
                         << setprecision(6) << loss << '\n';
                }
            }

            metrics.finalLoss = calculateLoss(dataset, parameters);

            int correct = 0;

            for (const auto& sample : dataset) {
                double prediction = circuit.execute(
                    sample.features, parameters
                );

                if ((prediction >= 0) ==
                    (sample.target >= 0)) {
                    ++correct;
                }
            }

            metrics.accuracy =
                static_cast<double>(correct) / dataset.size();

            metrics.circuitEvaluations = circuit.evaluationCount();

            status = ExperimentStatus::Completed;

            cout << "\nOptimized parameters:\n";

            for (double value : parameters) {
                cout << fixed << setprecision(5) << value << ' ';
            }

            cout << '\n';

            return metrics;

        } catch (...) {
            status = ExperimentStatus::Failed;
            throw;
        }
    }

    ExperimentStatus getStatus() const {
        return status;
    }
};

// ============================================================
// 7. Diagnostics and application
// ============================================================

void printComplexity(const Configuration& config) {
    const size_t dimension = 1ULL << config.qubits;

    cout << "\nComputational characteristics:\n";
    cout << "Qubits: " << config.qubits << '\n';
    cout << "Circuit depth: " << config.layers << '\n';
    cout << "Parameters: " << config.parameterCount() << '\n';
    cout << "State-vector dimension: " << dimension << '\n';
    cout << "Approximate state memory: "
         << dimension * sizeof(Complex) << " bytes\n";

    cout << "Single-qubit operation complexity: O(2^n)\n";
    cout << "State-vector storage complexity: O(2^n)\n";
}

int main() {
    try {
        Configuration config;
        config.qubits = 2;
        config.layers = 2;
        config.epochs = 100;
        config.learningRate = 0.08;

        config.validate();

        cout << "VARIATIONAL QUANTUM CIRCUIT ENGINE\n";
        cout << "=================================\n";

        printComplexity(config);

        auto dataset = createDataset();

        TrainingService service(config);

        cout << "\nStarting training...\n";

        TrainingMetrics metrics = service.train(dataset);

        cout << "\nExperiment results:\n";
        cout << "Initial loss: " << metrics.initialLoss << '\n';
        cout << "Final loss:   " << metrics.finalLoss << '\n';
        cout << "Accuracy:     " << metrics.accuracy * 100 << "%\n";
        cout << "Epochs:       " << metrics.completedEpochs << '\n';
        cout << "Evaluations:  " << metrics.circuitEvaluations << '\n';

        cout << "Experiment state: "
             << (service.getStatus() == ExperimentStatus::Completed
                 ? "COMPLETED" : "NOT COMPLETED") << '\n';

        // Validate normalization independently.
        QuantumRegister registerTest(2);
        registerTest.hadamard(0);
        registerTest.cnot(0, 1);

        if (registerTest.normalizationError() > EPSILON) {
            throw runtime_error("Quantum state normalization failed.");
        }

        cout << "\nBell-state probabilities:\n";

        for (double probability : registerTest.probabilities()) {
            cout << fixed << setprecision(4)
                 << probability << ' ';
        }

        cout << "\n\nAll validation checks passed.\n";

    } catch (const exception& error) {
        cerr << "Execution error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
