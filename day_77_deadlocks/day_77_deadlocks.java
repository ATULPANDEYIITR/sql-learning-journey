import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.stream.IntStream;

/**
 * Enterprise Variational Quantum Circuit Experiment Platform.
 *
 * Java 17
 * No third-party dependencies.
 *
 * Features:
 * - Explicit quantum domain types
 * - Circuit specifications
 * - Parameterized quantum gates
 * - Parameter-shift optimization
 * - Experiment lifecycle management
 * - Execution policies and budgets
 * - Asynchronous job processing
 * - Immutable experiment records
 * - Persistent experiment reporting
 */
public class VQCEnterprise {

    // ========================================================
    // 1. Domain exceptions
    // ========================================================

    static class VQCException extends RuntimeException {
        VQCException(String message) {
            super(message);
        }
    }

    static class ValidationException extends VQCException {
        ValidationException(String message) {
            super(message);
        }
    }

    static class PolicyViolationException extends VQCException {
        PolicyViolationException(String message) {
            super(message);
        }
    }

    static class ExecutionException extends VQCException {
        ExecutionException(String message) {
            super(message);
        }
    }

    // ========================================================
    // 2. Enumerations
    // ========================================================

    enum ExperimentStatus {
        CREATED,
        QUEUED,
        RUNNING,
        COMPLETED,
        FAILED,
        CANCELLED
    }

    enum GateType {
        RY,
        RZ,
        CNOT
    }

    enum CheckType {
        PARAMETER_VALIDATION,
        STATE_NORMALIZATION,
        EXECUTION_BUDGET,
        NUMERICAL_STABILITY
    }

    enum CheckResult {
        PASSED,
        FAILED
    }

    // ========================================================
    // 3. Immutable domain records
    // ========================================================

    record CircuitSpecification(
        int qubits,
        int layers,
        int maximumEvaluations
    ) {
        CircuitSpecification {
            if (qubits < 1 || qubits > 12) {
                throw new ValidationException("Invalid qubit count.");
            }

            if (layers < 1 || layers > 20) {
                throw new ValidationException("Invalid circuit depth.");
            }

            if (maximumEvaluations < 1) {
                throw new ValidationException("Invalid evaluation budget.");
            }
        }

        int parameterCount() {
            return qubits * layers * 2;
        }

        int stateDimension() {
            return 1 << qubits;
        }
    }

    record TrainingSample(List<Double> features, double target) {
        TrainingSample {
            features = List.copyOf(features);

            if (features.isEmpty() ||
                features.stream().anyMatch(v -> !Double.isFinite(v))) {
                throw new ValidationException("Invalid input features.");
            }

            if (target != -1.0 && target != 1.0) {
                throw new ValidationException("Invalid classification target.");
            }
        }
    }

    record ReviewMetric(
        String metric,
        double value,
        Instant recordedAt
    ) {}

    record ExperimentRecord(
        String experimentId,
        String circuitName,
        ExperimentStatus status,
        double initialLoss,
        double finalLoss,
        double accuracy,
        int completedEpochs,
        long circuitEvaluations,
        Instant createdAt
    ) {}

    record PolicyDecision(
        boolean approved,
        List<String> violations
    ) {
        PolicyDecision {
            violations = List.copyOf(violations);
        }
    }

    // ========================================================
    // 4. Complex-number arithmetic
    // ========================================================

    record Complex(double real, double imaginary) {

        Complex add(Complex other) {
            return new Complex(
                real + other.real,
                imaginary + other.imaginary
            );
        }

        Complex multiply(Complex other) {
            return new Complex(
                real * other.real - imaginary * other.imaginary,
                real * other.imaginary + imaginary * other.real
            );
        }

        Complex scale(double value) {
            return new Complex(
                real * value,
                imaginary * value
            );
        }

        double magnitudeSquared() {
            return real * real + imaginary * imaginary;
        }

        static Complex polar(double angle) {
            return new Complex(
                Math.cos(angle),
                Math.sin(angle)
            );
        }
    }

    // ========================================================
    // 5. Quantum register service
    // ========================================================

    static final class QuantumRegister {

        private final int qubits;
        private final int dimension;
        private Complex[] amplitudes;

        QuantumRegister(int qubits) {
            if (qubits < 1 || qubits > 12) {
                throw new ValidationException("Unsupported register size.");
            }

            this.qubits = qubits;
            this.dimension = 1 << qubits;
            reset();
        }

        void reset() {
            amplitudes = new Complex[dimension];

            for (int i = 0; i < dimension; i++) {
                amplitudes[i] = new Complex(0, 0);
            }

            amplitudes[0] = new Complex(1, 0);
        }

        void applyGate(int qubit, Complex[][] matrix) {
            if (qubit < 0 || qubit >= qubits) {
                throw new ValidationException("Invalid qubit.");
            }

            int mask = 1 << qubit;

            for (int i = 0; i < dimension; i++) {
                if ((i & mask) != 0) {
                    continue;
                }

                int paired = i | mask;

                Complex a = amplitudes[i];
                Complex b = amplitudes[paired];

                amplitudes[i] = matrix[0][0].multiply(a)
                    .add(matrix[0][1].multiply(b));

                amplitudes[paired] = matrix[1][0].multiply(a)
                    .add(matrix[1][1].multiply(b));
            }
        }

        void ry(int qubit, double angle) {
            double c = Math.cos(angle / 2);
            double s = Math.sin(angle / 2);

            Complex[][] matrix = {
                {new Complex(c, 0), new Complex(-s, 0)},
                {new Complex(s, 0), new Complex(c, 0)}
            };

            applyGate(qubit, matrix);
        }

        void rz(int qubit, double angle) {
            Complex upper = Complex.polar(-angle / 2);
            Complex lower = Complex.polar(angle / 2);

            Complex[][] matrix = {
                {upper, new Complex(0, 0)},
                {new Complex(0, 0), lower}
            };

            applyGate(qubit, matrix);
        }

        void cnot(int control, int target) {
            if (control == target ||
                control < 0 || target < 0 ||
                control >= qubits || target >= qubits) {
                throw new ValidationException("Invalid CNOT operation.");
            }

            int controlMask = 1 << control;
            int targetMask = 1 << target;

            for (int i = 0; i < dimension; i++) {
                if ((i & controlMask) != 0 &&
                    (i & targetMask) == 0) {

                    int paired = i | targetMask;

                    Complex temporary = amplitudes[i];
                    amplitudes[i] = amplitudes[paired];
                    amplitudes[paired] = temporary;
                }
            }
        }

        double expectationZ(int qubit) {
            if (qubit < 0 || qubit >= qubits) {
                throw new ValidationException("Invalid observable.");
            }

            int mask = 1 << qubit;
            double result = 0;

            for (int i = 0; i < dimension; i++) {
                double probability = amplitudes[i].magnitudeSquared();

                result += (i & mask) == 0
                    ? probability
                    : -probability;
            }

            return result;
        }

        double[] probabilities() {
            double[] probabilities = new double[dimension];

            for (int i = 0; i < dimension; i++) {
                probabilities[i] = amplitudes[i].magnitudeSquared();
            }

            return probabilities;
        }

        double normalizationError() {
            return Math.abs(
                java.util.Arrays.stream(probabilities()).sum() - 1.0
            );
        }
    }

    // ========================================================
    // 6. Parameterized circuit service
    // ========================================================

    static final class CircuitExecutionService {

        private static final double SHIFT = Math.PI / 2;

        private final CircuitSpecification specification;
        private final QuantumRegister register;

        private long evaluationCount = 0;

        CircuitExecutionService(CircuitSpecification specification) {
            this.specification = specification;
            this.register = new QuantumRegister(specification.qubits());
        }

        private void validate(
            List<Double> features,
            double[] parameters
        ) {
            if (features.size() != specification.qubits()) {
                throw new ValidationException("Feature dimension mismatch.");
            }

            if (features.stream().anyMatch(v -> !Double.isFinite(v))) {
                throw new ValidationException("Non-finite feature.");
            }

            if (parameters.length != specification.parameterCount()) {
                throw new ValidationException("Parameter dimension mismatch.");
            }

            for (double parameter : parameters) {
                if (!Double.isFinite(parameter)) {
                    throw new ValidationException("Non-finite parameter.");
                }
            }
        }

        synchronized double execute(
            List<Double> features,
            double[] parameters
        ) {
            validate(features, parameters);

            if (++evaluationCount > specification.maximumEvaluations()) {
                throw new PolicyViolationException(
                    "Maximum circuit evaluations exceeded."
                );
            }

            register.reset();

            // Encode classical features.
            for (int qubit = 0; qubit < specification.qubits(); qubit++) {
                register.ry(qubit, features.get(qubit));
            }

            int position = 0;

            for (int layer = 0; layer < specification.layers(); layer++) {

                for (int qubit = 0;
                     qubit < specification.qubits();
                     qubit++) {

                    register.ry(qubit, parameters[position++]);
                    register.rz(qubit, parameters[position++]);
                }

                for (int qubit = 0;
                     qubit < specification.qubits() - 1;
                     qubit++) {

                    register.cnot(qubit, qubit + 1);
                }
            }

            return register.expectationZ(0);
        }

        double[] parameterShiftGradient(
            List<Double> features,
            double[] parameters
        ) {
            double[] gradient = new double[parameters.length];

            for (int i = 0; i < parameters.length; i++) {
                double[] plus = parameters.clone();
                double[] minus = parameters.clone();

                plus[i] += SHIFT;
                minus[i] -= SHIFT;

                double upper = execute(features, plus);
                double lower = execute(features, minus);

                gradient[i] = (upper - lower) / 2;
            }

            return gradient;
        }

        long evaluationCount() {
            return evaluationCount;
        }

        double normalizationError() {
            return register.normalizationError();
        }
    }

    // ========================================================
    // 7. Governance policy
    // ========================================================

    static final class CircuitGovernancePolicy {

        private final int maximumQubits;
        private final int maximumDepth;
        private final long maximumEvaluations;

        CircuitGovernancePolicy(
            int maximumQubits,
            int maximumDepth,
            long maximumEvaluations
        ) {
            this.maximumQubits = maximumQubits;
            this.maximumDepth = maximumDepth;
            this.maximumEvaluations = maximumEvaluations;
        }

        PolicyDecision evaluate(
            CircuitSpecification specification
        ) {
            List<String> violations = new ArrayList<>();

            if (specification.qubits() > maximumQubits) {
                violations.add("Qubit policy exceeded.");
            }

            if (specification.layers() > maximumDepth) {
                violations.add("Circuit depth policy exceeded.");
            }

            if (specification.maximumEvaluations() >
                maximumEvaluations) {
                violations.add("Execution budget policy exceeded.");
            }

            return new PolicyDecision(
                violations.isEmpty(),
                violations
            );
        }

        void enforce(CircuitSpecification specification) {
            PolicyDecision decision = evaluate(specification);

            if (!decision.approved()) {
                throw new PolicyViolationException(
                    String.join("; ", decision.violations())
                );
            }
        }
    }

    // ========================================================
    // 8. Optimization service
    // ========================================================

    static final class OptimizationService {

        private final double learningRate;
        private final double gradientClip;

        OptimizationService(double learningRate, double gradientClip) {
            if (learningRate <= 0 || gradientClip <= 0) {
                throw new ValidationException("Invalid optimizer policy.");
            }

            this.learningRate = learningRate;
            this.gradientClip = gradientClip;
        }

        void update(double[] parameters, double[] gradient) {
            if (parameters.length != gradient.length) {
                throw new ValidationException("Gradient shape mismatch.");
            }

            double norm = Math.sqrt(
                IntStream.range(0, gradient.length)
                    .mapToDouble(i -> gradient[i] * gradient[i])
                    .sum()
            );

            double scale = norm > gradientClip
                ? gradientClip / norm
                : 1.0;

            for (int i = 0; i < parameters.length; i++) {
                parameters[i] -= learningRate * gradient[i] * scale;
            }
        }
    }

    // ========================================================
    // 9. Experiment lifecycle manager
    // ========================================================

    static final class ExperimentManager {

        private final String experimentId = UUID.randomUUID().toString();
        private final String circuitName;

        private ExperimentStatus status = ExperimentStatus.CREATED;

        ExperimentManager(String circuitName) {
            this.circuitName = Objects.requireNonNull(circuitName);
        }

        synchronized void transition(ExperimentStatus next) {
            Map<ExperimentStatus, List<ExperimentStatus>> transitions =
                Map.of(
                    ExperimentStatus.CREATED,
                    List.of(ExperimentStatus.QUEUED),
                    ExperimentStatus.QUEUED,
                    List.of(ExperimentStatus.RUNNING, ExperimentStatus.FAILED),
                    ExperimentStatus.RUNNING,
                    List.of(ExperimentStatus.COMPLETED, ExperimentStatus.FAILED),
                    ExperimentStatus.COMPLETED,
                    List.of(),
                    ExperimentStatus.FAILED,
                    List.of(),
                    ExperimentStatus.CANCELLED,
                    List.of()
                );

            if (!transitions.get(status).contains(next)) {
                throw new VQCException(
                    "Invalid experiment state transition."
                );
            }

            status = next;
        }

        synchronized ExperimentStatus status() {
            return status;
        }

        String experimentId() {
            return experimentId;
        }

        String circuitName() {
            return circuitName;
        }
    }

    // ========================================================
    // 10. Training service
    // ========================================================

    static final class TrainingService {

        private final CircuitExecutionService circuit;
        private final CircuitSpecification specification;
        private final OptimizationService optimizer;
        private final ExperimentManager manager;

        TrainingService(
            CircuitSpecification specification,
            double learningRate,
            double gradientClip
        ) {
            this.specification = specification;
            this.circuit = new CircuitExecutionService(specification);
            this.optimizer = new OptimizationService(
                learningRate, gradientClip
            );
            this.manager = new ExperimentManager("VQC-BINARY-CLASSIFIER");
        }

        private double loss(
            List<TrainingSample> dataset,
            double[] parameters
        ) {
            return dataset.stream()
                .mapToDouble(sample -> {
                    double prediction = circuit.execute(
                        sample.features(), parameters
                    );

                    return Math.pow(
                        prediction - sample.target(), 2
                    );
                })
                .average()
                .orElseThrow();
        }

        ExperimentRecord train(
            List<TrainingSample> dataset,
            int epochs,
            long seed
        ) {
            if (dataset.isEmpty()) {
                throw new ValidationException("Dataset is empty.");
            }

            for (TrainingSample sample : dataset) {
                if (sample.features().size() != specification.qubits()) {
                    throw new ValidationException(
                        "Training sample dimension mismatch."
                    );
                }
            }

            manager.transition(ExperimentStatus.QUEUED);
            manager.transition(ExperimentStatus.RUNNING);

            Instant createdAt = Instant.now();

            try {
                java.util.Random random = new java.util.Random(seed);

                double[] parameters = new double[
                    specification.parameterCount()
                ];

                for (int i = 0; i < parameters.length; i++) {
                    parameters[i] = random.nextDouble() - 0.5;
                }

                double initialLoss = loss(dataset, parameters);
                int completedEpochs = 0;

                for (int epoch = 0; epoch < epochs; epoch++) {
                    double[] gradient = new double[parameters.length];

                    for (TrainingSample sample : dataset) {
                        double prediction = circuit.execute(
                            sample.features(), parameters
                        );

                        double[] localGradient =
                            circuit.parameterShiftGradient(
                                sample.features(), parameters
                            );

                        double scale = 2.0 *
                            (prediction - sample.target()) / dataset.size();

                        for (int i = 0; i < gradient.length; i++) {
                            gradient[i] += scale * localGradient[i];
                        }
                    }

                    optimizer.update(parameters, gradient);

                    double currentLoss = loss(dataset, parameters);

                    if (!Double.isFinite(currentLoss)) {
                        throw new ExecutionException(
                            "Non-finite training loss."
                        );
                    }

                    completedEpochs = epoch + 1;

                    if (epoch % 20 == 0) {
                        System.out.printf(
                            "Epoch %03d | Loss %.6f%n",
                            epoch + 1,
                            currentLoss
                        );
                    }
                }

                double finalLoss = loss(dataset, parameters);

                long correct = dataset.stream()
                    .filter(sample -> {
                        double prediction = circuit.execute(
                            sample.features(), parameters
                        );

                        return (prediction >= 0) ==
                               (sample.target() >= 0);
                    })
                    .count();

                double accuracy = (double) correct / dataset.size();

                if (circuit.normalizationError() > 1e-8) {
                    throw new ExecutionException(
                        "Quantum state normalization failed."
                    );
                }

                manager.transition(ExperimentStatus.COMPLETED);

                return new ExperimentRecord(
                    manager.experimentId(),
                    manager.circuitName(),
                    manager.status(),
                    initialLoss,
                    finalLoss,
                    accuracy,
                    completedEpochs,
                    circuit.evaluationCount(),
                    createdAt
                );

            } catch (RuntimeException exception) {
                manager.transition(ExperimentStatus.FAILED);
                throw exception;
            }
        }
    }

    // ========================================================
    // 11. Asynchronous experiment execution
    // ========================================================

    static final class ExperimentJobService implements AutoCloseable {

        private final ExecutorService executor =
            Executors.newFixedThreadPool(2);

        CompletableFuture<ExperimentRecord> submit(
            TrainingService service,
            List<TrainingSample> dataset,
            int epochs,
            long seed
        ) {
            List<TrainingSample> immutableDataset =
                List.copyOf(dataset);

            return CompletableFuture.supplyAsync(
                () -> service.train(immutableDataset, epochs, seed),
                executor
            );
        }

        @Override
        public void close() {
            executor.shutdown();

            try {
                if (!executor.awaitTermination(30, TimeUnit.SECONDS)) {
                    executor.shutdownNow();
                }
            } catch (InterruptedException exception) {
                executor.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }
    }

    // ========================================================
    // 12. Experiment persistence
    // ========================================================

    static final class ExperimentRepository {

        private final Path directory;

        ExperimentRepository(Path directory) {
            this.directory = directory;
        }

        void save(ExperimentRecord record) {
            try {
                Files.createDirectories(directory);

                String content = """
                    {
                      "experimentId": "%s",
                      "circuitName": "%s",
                      "status": "%s",
                      "initialLoss": %.10f,
                      "finalLoss": %.10f,
                      "accuracy": %.6f,
                      "completedEpochs": %d,
                      "circuitEvaluations": %d,
                      "createdAt": "%s"
                    }
                    """.formatted(
                        record.experimentId(),
                        record.circuitName(),
                        record.status(),
                        record.initialLoss(),
                        record.finalLoss(),
                        record.accuracy(),
                        record.completedEpochs(),
                        record.circuitEvaluations(),
                        record.createdAt()
                    );

                Path destination = directory.resolve(
                    record.experimentId() + ".json"
                );

                Path temporary = Files.createTempFile(
                    directory, "vqc-", ".tmp"
                );

                Files.writeString(
                    temporary,
                    content,
                    StandardCharsets.UTF_8
                );

                try {
                    Files.move(
                        temporary,
                        destination,
                        StandardCopyOption.ATOMIC_MOVE
                    );
                } catch (IOException exception) {
                    Files.move(
                        temporary,
                        destination,
                        StandardCopyOption.REPLACE_EXISTING
                    );
                }

            } catch (IOException exception) {
                throw new ExecutionException(
                    "Experiment persistence failed: " +
                    exception.getMessage()
                );
            }
        }
    }

    // ========================================================
    // 13. Application entry point
    // ========================================================

    public static void main(String[] args) {

        try {
            CircuitSpecification specification =
                new CircuitSpecification(2, 2, 100000);

            CircuitGovernancePolicy policy =
                new CircuitGovernancePolicy(8, 10, 100000);

            policy.enforce(specification);

            List<TrainingSample> dataset = List.of(
                new TrainingSample(List.of(0.15, 0.25), -1),
                new TrainingSample(List.of(0.30, 0.45), -1),
                new TrainingSample(List.of(0.45, 0.20), -1),
                new TrainingSample(List.of(2.30, 2.50), 1),
                new TrainingSample(List.of(2.65, 2.25), 1),
                new TrainingSample(List.of(2.80, 2.75), 1),
                new TrainingSample(List.of(0.20, 2.50), -1),
                new TrainingSample(List.of(2.60, 0.20), 1)
            );

            TrainingService service = new TrainingService(
                specification,
                0.08,
                5.0
            );

            System.out.println("ENTERPRISE VQC EXPERIMENT");
            System.out.println("=========================");

            ExperimentRecord result;

            try (ExperimentJobService jobs =
                     new ExperimentJobService()) {

                result = jobs.submit(
                    service,
                    dataset,
                    100,
                    42
                ).join();
            }

            System.out.println("\nExperiment report:");
            System.out.println("ID: " + result.experimentId());
            System.out.println("Status: " + result.status());

            System.out.printf(
                "Initial loss: %.6f%n",
                result.initialLoss()
            );

            System.out.printf(
                "Final loss: %.6f%n",
                result.finalLoss()
            );

            System.out.printf(
                "Accuracy: %.2f%%%n",
                result.accuracy() * 100
            );

            System.out.println(
                "Completed epochs: " + result.completedEpochs()
            );

            System.out.println(
                "Circuit evaluations: " + result.circuitEvaluations()
            );

            ExperimentRepository repository =
                new ExperimentRepository(Path.of("vqc-enterprise-data"));

            repository.save(result);

            System.out.println("\nExperiment persisted.");

            System.out.println(
                "State-vector dimension: " +
                specification.stateDimension()
            );

            System.out.println(
                "Trainable parameters: " +
                specification.parameterCount()
            );

            System.out.println("Validation completed.");

        } catch (Exception exception) {
            System.err.println(
                "Experiment execution failed: " +
                exception.getMessage()
            );

            System.exitCode = 1;
        }
    }
}
