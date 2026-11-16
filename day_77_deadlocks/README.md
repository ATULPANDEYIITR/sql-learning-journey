# Variational Quantum Circuits: Parameterized Quantum Computation

## 1. Introduction

Variational Quantum Circuits (VQCs) are quantum circuits containing adjustable parameters that are optimized using a classical optimization algorithm.

They form an important computational approach in hybrid quantum-classical computing. A quantum processor evaluates a parameterized circuit, produces measurement outcomes, and supplies information to a classical optimizer. The optimizer updates the circuit parameters and repeats the process.

A VQC combines three principal mechanisms:

- Quantum state preparation and data encoding.
- Parameterized quantum operations and entanglement.
- Classical optimization using circuit measurements or expectation values.

The central computational relationship is:

\[
f(\mathbf{x},\boldsymbol{\theta})
=
\langle 0|
U^\dagger(\mathbf{x},\boldsymbol{\theta})
O
U(\mathbf{x},\boldsymbol{\theta})
|0\rangle
\]

Where:

- \(\mathbf{x}\) represents classical input data.
- \(\boldsymbol{\theta}\) represents trainable circuit parameters.
- \(U\) represents the complete quantum circuit.
- \(O\) represents an observable.
- \(f\) represents the measured expectation value.

The implementations use a two-qubit classification problem to demonstrate circuit construction, optimization, numerical evaluation, execution governance, and experiment management.

## 2. Quantum Computation Fundamentals

### 2.1 Qubits and quantum states

A classical bit has one of two values: zero or one.

A qubit is represented by a normalized complex state:

\[
|\psi\rangle = \alpha|0\rangle+\beta|1\rangle
\]

Where:

\[
|\alpha|^2+|\beta|^2=1
\]

The complex amplitudes determine the probabilities of measurement outcomes.

For a system containing \(n\) qubits, the state vector contains \(2^n\) complex amplitudes.

| Qubits | State-vector amplitudes |
|---:|---:|
| 1 | 2 |
| 2 | 4 |
| 4 | 16 |
| 8 | 256 |
| 10 | 1,024 |
| 20 | 1,048,576 |
| 30 | 1,073,741,824 |

This exponential growth is a central limitation of classical state-vector simulation.

### 2.2 Quantum gates

Quantum gates are operations that transform quantum states.

The implementations include the following operations.

**Pauli-Y rotation**

\[
R_y(\theta)=
\begin{bmatrix}
\cos(\theta/2)&-\sin(\theta/2)\\
\sin(\theta/2)&\cos(\theta/2)
\end{bmatrix}
\]

**Pauli-Z rotation**

\[
R_z(\theta)=
\begin{bmatrix}
e^{-i\theta/2}&0\\
0&e^{i\theta/2}
\end{bmatrix}
\]

**Hadamard gate**

\[
H=\frac{1}{\sqrt{2}}
\begin{bmatrix}
1&1\\
1&-1
\end{bmatrix}
\]

**Controlled-NOT gate**

CNOT is a two-qubit operation. It flips the target qubit when the control qubit is in state one.

Entangling gates introduce correlations between qubits that cannot generally be represented as independent single-qubit states.

### 2.3 State vectors and measurement

The state-vector representation stores the complex amplitude associated with each computational basis state.

For an observable \(O\), its expectation value is:

\[
\langle O\rangle
=
\langle\psi|O|\psi\rangle
\]

For a Pauli-Z measurement:

\[
\langle Z\rangle=P(0)-P(1)
\]

The output is bounded:

\[
-1\leq\langle Z\rangle\leq1
\]

The implementations use this expectation value as the output of the variational model.

On physical quantum hardware, measurements are repeated across multiple shots. The expectation value is estimated from measurement frequencies rather than obtained directly from a complete state vector.

## 3. Variational Quantum Circuit Architecture

### 3.1 Parameterized computation

A parameterized quantum circuit contains quantum operations whose rotation angles are adjustable.

A typical circuit has the following structure:

\[
U(\mathbf{x},\boldsymbol{\theta})
=
U_{\text{ansatz}}(\boldsymbol{\theta})
U_{\text{encoding}}(\mathbf{x})
\]

The data encoding stage maps classical input values into quantum states.

The ansatz applies trainable transformations to those states.

The measurement stage evaluates the resulting quantum state.

### 3.2 Data encoding

Data encoding transforms classical features into quantum gate parameters.

The implementations use angle encoding:

\[
|x\rangle=R_y(x)|0\rangle
\]

For two input features:

\[
|\psi_0\rangle
=
R_y(x_0)\otimes R_y(x_1)|00\rangle
\]

Angle encoding is straightforward to implement, although it does not eliminate the challenge of representing large classical datasets with limited qubits.

Different encoding methods have different resource requirements.

| Encoding | Mechanism | Main consideration |
|---|---|---|
| Angle encoding | Features become rotation angles | Multiple gates may be required |
| Amplitude encoding | Features become state amplitudes | State preparation can be expensive |
| Basis encoding | Binary values select computational basis states | Limited representation of continuous features |
| IQP encoding | Structured diagonal operations encode data | Depends on the chosen feature map |

### 3.3 Ansatz construction

An ansatz is the parameterized circuit architecture selected for a variational computation.

The implementations use a hardware-efficient rotation ansatz.

For each layer:

1. Apply an RY rotation to each qubit.
2. Apply an RZ rotation to each qubit.
3. Apply CNOT operations between neighboring qubits.
4. Repeat the structure for the specified number of layers.

For \(n\) qubits and \(L\) layers, the number of trainable parameters is:

\[
P=2nL
\]

For the two-qubit, two-layer configuration:

\[
P=2(2)(2)=8
\]

The circuit therefore contains eight trainable rotation parameters.

### 3.4 Entanglement topology

The examples use linear entanglement:

\[
q_0\rightarrow q_1\rightarrow q_2
\rightarrow\cdots\rightarrow q_{n-1}
\]

This topology is simple and makes circuit construction explicit.

Alternative arrangements include:

- Ring entanglement.
- All-to-all entanglement.
- Hardware-native connectivity.
- Problem-inspired entanglement.

The selected topology affects circuit depth, gate count, connectivity requirements, and optimization behavior.

## 4. Hybrid Quantum-Classical Optimization

### 4.1 Variational objective

The example applications formulate a binary classification task.

Each training sample contains:

\[
(\mathbf{x}_i,y_i)
\]

Where:

\[
y_i\in\{-1,+1\}
\]

The model predicts:

\[
\hat y_i=f(\mathbf{x}_i,\boldsymbol{\theta})
\]

The mean squared error objective is:

\[
L(\boldsymbol{\theta})
=
\frac{1}{N}
\sum_{i=1}^{N}
\left(
f(\mathbf{x}_i,\boldsymbol{\theta})-y_i
\right)^2
\]

The prediction is converted into a class using:

\[
\hat c_i=
\begin{cases}
+1 & f(\mathbf{x}_i,\boldsymbol{\theta})\geq0\\
-1 & f(\mathbf{x}_i,\boldsymbol{\theta})<0
\end{cases}
\]

This is a demonstration objective rather than a claim that every VQC should use mean squared error.

### 4.2 Parameter-shift rule

The parameter-shift rule calculates derivatives of suitable parameterized quantum expectation values.

For a gate parameter with the standard two-eigenvalue generator spectrum:

\[
\frac{\partial f}{\partial\theta_j}
=
\frac{1}{2}
\left[
f\left(\theta_j+\frac{\pi}{2}\right)
-
f\left(\theta_j-\frac{\pi}{2}\right)
\right]
\]

The implementations use this exact shift rule for individual RY and RZ parameters appearing once in the selected ansatz.

The derivative of the classification loss is obtained using the chain rule:

\[
\frac{\partial L}{\partial\theta_j}
=
\frac{2}{N}
\sum_{i=1}^{N}
(\hat y_i-y_i)
\frac{\partial\hat y_i}{\partial\theta_j}
\]

This produces a gradient vector that can be supplied to a classical optimizer.

The rule is not a universal two-evaluation formula for every arbitrary parameterized quantum circuit. More complex gate generators, repeated parameter occurrences, and parameter sharing may require generalized shift rules or additional evaluations.

### 4.3 Gradient descent

The classical optimizer updates the parameters according to:

\[
\theta_j^{(t+1)}
=
\theta_j^{(t)}
-
\eta
\frac{\partial L}{\partial\theta_j}
\]

Where \(\eta\) is the learning rate.

The implementations also include gradient clipping:

\[
g_{\text{clipped}}
=
g\cdot
\min\left(1,\frac{c}{\|g\|_2}\right)
\]

This limits the magnitude of individual optimization updates.

Other optimizers that can be used in variational quantum computation include:

- Adam.
- COBYLA.
- SPSA.
- Natural gradient methods.

SPSA is particularly relevant when gradient evaluations are expensive because it estimates gradient information using stochastic perturbations.

## 5. Python Implementation

The Python implementation provides a self-contained quantum simulation and training workflow.

### 5.1 StateVectorSimulator

The simulator implements:

- Quantum register initialization.
- State-vector normalization.
- RY and RZ rotations.
- Hadamard transformations.
- CNOT entanglement.
- Pauli-Z expectation values.
- Measurement sampling.

The state-vector simulator uses Python complex numbers and standard-library mathematical operations.

### 5.2 VariationalCircuit

The circuit class separates feature encoding from trainable transformations.

Its principal methods are:

| Method | Responsibility |
|---|---|
| `encode_features()` | Maps input features into quantum rotations |
| `execute()` | Executes the complete parameterized circuit |
| `parameter_shift_gradient()` | Computes trainable parameter derivatives |
| `validate_parameters()` | Checks parameter dimensions and numerical validity |

### 5.3 VariationalTrainer

The training service performs:

1. Parameter initialization.
2. Initial loss evaluation.
3. Quantum circuit execution.
4. Parameter-shift gradient calculation.
5. Gradient clipping.
6. Classical parameter updates.
7. Loss monitoring.
8. Classification accuracy calculation.

The optimizer operates on the classical parameter vector. It does not directly modify the quantum state.

### 5.4 Experiment persistence

The `ExperimentStore` class stores experiment results in JSON.

It writes to a temporary file before replacing the destination file, reducing the possibility of leaving a partially written experiment record.

The saved record contains the optimization results, parameter values, execution duration, and experiment status.

## 6. JavaScript Implementation

The JavaScript implementation uses an event-driven experiment-management design.

### 6.1 Complex arithmetic

The `Complex` class implements complex addition, multiplication, scaling, and squared magnitude.

This makes the quantum-state calculations independent of external mathematical libraries.

### 6.2 QuantumRegister

The quantum register maintains a state vector and applies gate transformations.

The implementation uses array indexing and bit masks to identify basis states affected by quantum operations.

### 6.3 Event-driven experiment management

The `ExperimentManager` extends Node.js `EventEmitter`.

It emits events for:

- State transitions.
- Completed optimization epochs.
- Successful experiments.
- Failed experiments.

This separates numerical computation from monitoring and application-level reporting.

### 6.4 Asynchronous execution

The training service periodically yields to the Node.js event loop using `setImmediate`.

This allows other event-loop work to execute between training intervals.

It does not make the state-vector calculations parallel. CPU-intensive quantum simulation can still block the event loop between yields. Production workloads requiring substantial computation should use worker threads or separate execution processes.

### 6.5 Execution policies

`ExecutionPolicy` evaluates:

- Maximum qubit count.
- Maximum circuit depth.
- Maximum evaluation budget.

A circuit exceeding these limits is rejected before training begins.

### 6.6 Experiment repository

The repository writes experiment records to a JSON archive.

The implementation separates experiment computation from persistence and uses atomic file replacement for archive updates.

For multi-process production systems, a transactional database is more appropriate than concurrent read-modify-write operations on one JSON file.

## 7. C++17 Implementation

The C++ implementation emphasizes explicit memory representation, numerical computation, and modular engineering.

### 7.1 Quantum register

The `QuantumRegister` class uses:

- `std::vector<std::complex<double>>` for amplitudes.
- Bit masks for qubit indexing.
- Matrix operations for single-qubit gates.
- State-vector swaps for CNOT transformations.

The state dimension is:

\[
D=2^n
\]

Each complex amplitude normally occupies 16 bytes when represented using two double-precision values.

Approximate state-vector memory is:

\[
M=16\times2^n\text{ bytes}
\]

This excludes container overhead and temporary allocations.

### 7.2 VariationalCircuit

The circuit class encapsulates:

- Feature validation.
- Parameter validation.
- Circuit execution.
- Observable evaluation.
- Parameter-shift gradient calculation.

The evaluation counter provides a mechanism for limiting computational work.

### 7.3 GradientDescent

The optimizer is implemented as a separate component.

This allows the circuit simulation and classical optimization algorithm to be maintained independently.

The separation is important because the same circuit can be optimized with different classical algorithms.

### 7.4 TrainingService

The training service controls the experiment lifecycle and evaluates the training dataset.

It handles:

- Initial parameter generation.
- Loss calculation.
- Gradient accumulation.
- Parameter updates.
- Numerical failure detection.
- Final classification accuracy.

The use of STL containers and algorithms supports modularity without external dependencies.

## 8. Java 17 Enterprise Implementation

The Java implementation introduces a service-oriented architecture suitable for an experiment-management platform.

### 8.1 Domain model

The implementation uses explicit domain types:

| Type | Responsibility |
|---|---|
| `CircuitSpecification` | Circuit dimensions and execution budget |
| `TrainingSample` | Immutable input and target |
| `ExperimentRecord` | Experiment results |
| `PolicyDecision` | Governance evaluation |
| `ExperimentStatus` | Experiment lifecycle |
| `GateType` | Quantum operation classification |

Java records provide immutable data structures for experiment metadata.

### 8.2 Circuit execution service

`CircuitExecutionService` performs the quantum simulation and parameter-shift calculations.

The service validates the dimensions of input data and trainable parameters before circuit execution.

Synchronized execution protects the shared quantum register from concurrent access.

### 8.3 Governance policy

`CircuitGovernancePolicy` checks whether a proposed experiment satisfies institutional execution limits.

It considers:

- Maximum qubit count.
- Maximum circuit depth.
- Maximum number of circuit evaluations.

Policy evaluation is separate from quantum circuit execution.

This separation is useful in enterprise research platforms where resource allocation and computational execution have different responsibilities.

### 8.4 Experiment lifecycle

The lifecycle manager supports:

\[
CREATED
\rightarrow QUEUED
\rightarrow RUNNING
\rightarrow COMPLETED
\]

It also supports failed execution.

Invalid transitions are rejected.

The state model makes experiment tracking explicit rather than relying on loosely structured status strings.

### 8.5 Asynchronous experiment jobs

`ExperimentJobService` uses a fixed thread pool and `CompletableFuture`.

This provides asynchronous job submission without requiring an external messaging framework.

The experiment dataset is copied before submission to avoid changes to the submitted training data while the job is executing.

### 8.6 Persistence

`ExperimentRepository` stores experiment records in JSON files.

It creates a temporary file before moving the record to its destination.

The enterprise implementation demonstrates service separation, immutable records, asynchronous execution, and resource governance. A production multi-user platform would normally replace local file persistence with a transactional database and add durable job recovery.

## 9. PostgreSQL Experiment Management

The PostgreSQL implementation models the relational infrastructure required to manage VQC experiments.

It separates quantum circuit definitions, experimental configurations, computational policies, and execution results.

### 9.1 Relational architecture

The principal relationships are:

| Entity | Relationship |
|---|---|
| Organizations | Own researchers, circuits, datasets, and policies |
| Researchers | Create and operate experiments |
| Circuits | Contain gate and parameter definitions |
| Circuit gates | Represent ordered quantum operations |
| Circuit parameters | Store trainable rotation values |
| Datasets | Represent classical training data |
| Optimizer configurations | Store optimization settings |
| Execution policies | Define permitted computational resources |
| Experiments | Connect circuits, datasets, optimizers, and researchers |
| Experiment parameters | Preserve parameter snapshots |
| Experiment checks | Record validation results |
| Training metrics | Record epoch-level performance |
| Experiment events | Preserve lifecycle history |

### 9.2 Circuit representation

The `circuits` table stores the circuit architecture.

The `circuit_gates` table stores ordered gate operations.

The `circuit_parameters` table stores adjustable rotation values.

The distinction is important:

- A circuit definition describes the operations.
- A gate record identifies an individual operation.
- A parameter record represents an adjustable numerical value.
- An experiment parameter snapshot records the values associated with a particular experiment.

The relational design avoids mixing circuit definitions with individual training results.

### 9.3 Optimization configuration

The `optimizer_configurations` table records:

- Optimization algorithm.
- Learning rate.
- Maximum epochs.
- Convergence tolerance.
- Batch size.
- Gradient calculation method.

This makes optimization configurations independently reusable.

### 9.4 Execution governance

Execution policies specify computational constraints.

A policy can restrict:

- Maximum qubit count.
- Maximum circuit depth.
- Evaluation budget.
- Measurement shot budget.
- Permitted execution backends.
- Physical quantum hardware execution.

The `evaluate_experiment_eligibility()` function evaluates these conditions before an experiment enters the execution queue.

### 9.5 Experiment lifecycle

The database uses an enumerated experiment status.

The state transition trigger prevents invalid lifecycle changes.

The supported workflow is:

CREATED → QUEUED → RUNNING → COMPLETED

Alternative terminal states include FAILED and CANCELLED.

The transition audit trigger records state changes in `experiment_events`.

This creates an execution history that can be used for operational reporting and debugging.

### 9.6 Validation and reporting

The database provides several reporting mechanisms:

- `experiment_summary` presents experiment metadata and results.
- `experiment_validation_summary` aggregates validation outcomes.
- Convergence analysis evaluates changes in training loss.
- Optimizer reporting compares completed experiments.
- Parameter retrieval presents trainable parameter definitions.
- Execution reporting aggregates circuit evaluation counts.

The queue retrieval query uses `FOR UPDATE SKIP LOCKED`, a PostgreSQL mechanism useful for concurrent job consumers.

### 9.7 Transaction management

The complete database setup runs inside a transaction.

This ensures that schema creation and sample-data insertion can be rolled back if a statement fails before commit.

The queueing procedure also evaluates experiment eligibility before changing its state.

The database records experiment metadata and governance decisions. Actual quantum circuit execution remains the responsibility of an external simulation or quantum hardware service.

## 10. Parameterized Quantum Circuit Workflow

The complete computational workflow is:

Classical dataset  
↓  
Feature preprocessing  
↓  
Quantum data encoding  
↓  
Parameterized ansatz  
↓  
Entanglement operations  
↓  
Observable measurement  
↓  
Expectation-value calculation  
↓  
Loss calculation  
↓  
Parameter-shift gradient estimation  
↓  
Classical optimization  
↓  
Updated parameter vector  
↓  
Repeated circuit evaluation  
↓  
Experiment validation and reporting

The circuit architecture remains fixed during ordinary variational optimization, while its trainable parameters change.

Changing the ansatz architecture, feature map, number of qubits, or entanglement topology constitutes a separate circuit-design decision.

## 11. Important Technical Distinctions

### 11.1 Variational circuits versus conventional quantum circuits

A conventional quantum circuit may use fixed gate parameters to execute a predetermined transformation.

A variational circuit contains adjustable parameters that are optimized against an objective function.

The difference is not simply the presence of rotation gates. The optimization loop is a defining part of variational computation.

### 11.2 Quantum computation versus classical optimization

The quantum component evaluates the parameterized transformation and observables.

The classical component calculates loss, estimates gradients, and updates the parameter vector.

These operations have different computational responsibilities.

### 11.3 Exact simulation versus physical quantum hardware

The state-vector implementations calculate quantum amplitudes directly.

They do not simulate hardware noise, decoherence, gate infidelity, or measurement uncertainty.

Physical quantum processors provide measurement samples and are subject to hardware limitations.

A state-vector expectation value is therefore not equivalent to a noisy hardware measurement.

### 11.4 Circuit depth versus qubit count

Qubit count determines the dimension of the state vector.

Circuit depth describes the sequence of operations.

Increasing either can create computational challenges, but they represent different resource requirements.

### 11.5 Trainable parameters versus measured observables

Trainable parameters determine the circuit transformation.

Observables define the quantities measured from the resulting state.

Optimizing parameters changes the circuit behavior. Changing the observable changes the objective being evaluated.

## 12. Performance and Numerical Considerations

### 12.1 State-vector complexity

A state-vector simulator requires:

\[
O(2^n)
\]

memory.

A single-qubit operation generally requires:

\[
O(2^n)
\]

arithmetic operations.

The exponential scaling makes direct classical state-vector simulation impractical for sufficiently large systems.

### 12.2 Parameter-shift cost

For \(P\) trainable parameters, one parameter-shift gradient evaluation requires approximately:

\[
2P
\]

circuit executions per training sample.

For \(N\) samples, a full-batch gradient calculation therefore requires approximately:

\[
2PN
\]

shifted executions, excluding the additional forward evaluations used for loss calculation.

The cost increases with parameter count, dataset size, and optimization epochs.

### 12.3 Measurement shots

On quantum hardware, each expectation value is estimated using repeated measurements.

Finite-shot measurements introduce statistical uncertainty.

Increasing the shot count generally improves estimation precision but increases execution cost.

### 12.4 Barren plateaus

Barren plateaus are regions of parameter space where gradients become very small.

They can make optimization difficult, especially in certain deep or highly expressive ansatz architectures.

Potential contributing factors include:

- Circuit depth.
- Ansatz structure.
- Entanglement patterns.
- Initialization strategy.
- Observable selection.

The example uses a shallow circuit and bounded gradient updates. These design choices do not guarantee the absence of barren plateaus.

### 12.5 Numerical stability

The implementations validate:

- Parameter dimensions.
- Input dimensions.
- Finite numerical values.
- State-vector normalization.
- Optimization loss.
- Evaluation budgets.

Gradient clipping reduces the magnitude of optimization updates but does not guarantee convergence.

## 13. Security and Operational Considerations

A production variational quantum computing platform should address several operational risks.

**Experiment authorization**

Only authorized researchers and operators should submit or execute experiments.

**Resource governance**

Circuit depth, qubit count, evaluation budgets, and hardware access should be controlled through execution policies.

**Dataset protection**

Training datasets may contain confidential or proprietary information. Access controls, encryption, retention policies, and audit logging are important.

**Parameter integrity**

Experiment parameter snapshots should be associated with their circuit definitions and experiment identifiers.

**Reproducibility**

Record random seeds, circuit specifications, optimization settings, dataset versions, backend details, and software versions.

**Hardware governance**

Physical quantum hardware execution should require separate authorization and resource allocation.

**Failure recovery**

Experiment states and audit events should be retained so that failed jobs can be investigated.

The supplied programs demonstrate basic governance and persistence mechanisms. They are educational implementations, not complete multi-user production security systems.

## 14. Limitations of the Implementations

| Area | Limitation |
|---|---|
| State-vector simulation | Exponential memory requirements |
| Quantum noise | No hardware noise model |
| Measurement | Exact expectation values in the main training loop |
| Optimization | Basic gradient descent |
| Ansatz | Fixed rotation and linear CNOT structure |
| Dataset | Small illustrative classification dataset |
| Persistence | Local JSON in Python, JavaScript, and Java |
| Database | Stores metadata rather than executing circuits |
| Parallelism | Limited CPU parallelism |
| Hardware integration | No physical quantum backend connection |

The C++ and JavaScript implementations also use the same fundamental state-vector principles but organize the engineering responsibilities differently.

The Python implementation emphasizes mathematical experimentation, the JavaScript implementation emphasizes event-driven processing, the C++ implementation emphasizes computational efficiency and memory representation, and the Java implementation emphasizes enterprise services and lifecycle governance.

## 15. Execution and File Structure

| File | Implementation | Runtime |
|---|---|---|
| Python script | State-vector simulation and optimization | Python 3.10+ |
| JavaScript file | Event-driven VQC experiment manager | Node.js 18+ |
| C++ program | Modular quantum simulation engine | C++17 |
| Java program | Enterprise experiment-management platform | Java 17 |
| PostgreSQL script | Relational experiment and governance database | PostgreSQL 15+ |
| README.md | Technical documentation | Markdown |

The Python, JavaScript, C++, and Java implementations use standard language capabilities without third-party dependencies.

The SQL script creates the `vqc` schema, relational tables, constraints, functions, procedures, triggers, indexes, reporting views, and sample experiment records.

The five implementations provide complementary perspectives on the same computational domain: parameterized quantum computation, classical optimization, quantum-state evaluation, and controlled experiment execution.
