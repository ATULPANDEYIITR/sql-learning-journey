-- ============================================================
-- VARIATIONAL QUANTUM CIRCUITS
-- Parameterized Quantum Computation
--
-- PostgreSQL 15+
--
-- Relational experiment-management and governance platform.
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS vqc;

SET search_path TO vqc, public;

-- ============================================================
-- 1. Enumerated domain types
-- ============================================================

CREATE TYPE experiment_status AS ENUM (
    'CREATED',
    'QUEUED',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'CANCELLED'
);

CREATE TYPE gate_type AS ENUM (
    'H',
    'RY',
    'RZ',
    'RX',
    'CNOT',
    'CZ',
    'MEASURE'
);

CREATE TYPE check_status AS ENUM (
    'PENDING',
    'PASSED',
    'FAILED',
    'SKIPPED'
);

CREATE TYPE optimizer_type AS ENUM (
    'GRADIENT_DESCENT',
    'ADAM',
    'COBYLA',
    'SPSA'
);

CREATE TYPE execution_backend AS ENUM (
    'STATE_VECTOR_SIMULATOR',
    'DENSITY_MATRIX_SIMULATOR',
    'QUANTUM_HARDWARE'
);

-- ============================================================
-- 2. Reusable timestamp management
-- ============================================================

CREATE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- ============================================================
-- 3. Organizations and users
-- ============================================================

CREATE TABLE organizations (
    organization_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_name VARCHAR(160) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE researchers (
    researcher_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_id BIGINT NOT NULL
        REFERENCES organizations(organization_id),
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(40) NOT NULL CHECK (
        role IN (
            'RESEARCHER',
            'REVIEWER',
            'ADMINISTRATOR',
            'OPERATOR'
        )
    ),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 4. Quantum circuits
-- ============================================================

CREATE TABLE circuits (
    circuit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    organization_id BIGINT NOT NULL
        REFERENCES organizations(organization_id),

    owner_id BIGINT NOT NULL
        REFERENCES researchers(researcher_id),

    circuit_name VARCHAR(150) NOT NULL,

    description TEXT,

    qubit_count INTEGER NOT NULL CHECK (
        qubit_count BETWEEN 1 AND 30
    ),

    circuit_depth INTEGER NOT NULL CHECK (
        circuit_depth BETWEEN 1 AND 10000
    ),

    ansatz_type VARCHAR(60) NOT NULL CHECK (
        ansatz_type IN (
            'HARDWARE_EFFICIENT',
            'REAL_AMPLITUDES',
            'HEA',
            'PROBLEM_INSPIRED',
            'CUSTOM'
        )
    ),

    encoding_method VARCHAR(60) NOT NULL CHECK (
        encoding_method IN (
            'ANGLE_ENCODING',
            'AMPLITUDE_ENCODING',
            'BASIS_ENCODING',
            'IQP_ENCODING'
        )
    ),

    observable_definition JSONB NOT NULL DEFAULT
        '{"type":"PAULI_Z","qubit":0}'::jsonb,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (organization_id, circuit_name),

    CHECK (jsonb_typeof(observable_definition) = 'object')
);

CREATE TRIGGER circuits_updated_at
BEFORE UPDATE ON circuits
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 5. Circuit gate definitions
-- ============================================================

CREATE TABLE circuit_gates (
    gate_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    circuit_id BIGINT NOT NULL
        REFERENCES circuits(circuit_id) ON DELETE CASCADE,

    gate_sequence INTEGER NOT NULL CHECK (gate_sequence >= 0),

    gate_kind gate_type NOT NULL,

    target_qubit INTEGER NOT NULL CHECK (target_qubit >= 0),

    control_qubit INTEGER,

    parameter_index INTEGER,

    fixed_angle DOUBLE PRECISION,

    CHECK (
        control_qubit IS NULL OR control_qubit >= 0
    ),

    CHECK (
        parameter_index IS NULL OR parameter_index >= 0
    ),

    CHECK (
        fixed_angle IS NULL OR
        (
            fixed_angle > '-Infinity'::float8 AND
            fixed_angle < 'Infinity'::float8
        )
    ),

    CHECK (
        (gate_kind = 'CNOT' AND control_qubit IS NOT NULL
         AND parameter_index IS NULL)
        OR
        (gate_kind <> 'CNOT' AND control_qubit IS NULL)
    ),

    CHECK (
        gate_kind NOT IN ('RY', 'RX', 'RZ')
        OR num_nonnulls(parameter_index, fixed_angle) = 1
    ),

    CHECK (
        gate_kind NOT IN ('H', 'CNOT', 'CZ', 'MEASURE')
        OR (parameter_index IS NULL AND fixed_angle IS NULL)
    ),

    UNIQUE (circuit_id, gate_sequence)
);

-- ============================================================
-- 6. Trainable circuit parameters
-- ============================================================

CREATE TABLE circuit_parameters (
    parameter_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    circuit_id BIGINT NOT NULL
        REFERENCES circuits(circuit_id) ON DELETE CASCADE,

    parameter_index INTEGER NOT NULL CHECK (parameter_index >= 0),

    parameter_name VARCHAR(100) NOT NULL,

    initial_value DOUBLE PRECISION NOT NULL,

    trainable BOOLEAN NOT NULL DEFAULT TRUE,

    parameter_group VARCHAR(80),

    CHECK (
        initial_value > '-Infinity'::float8 AND
        initial_value < 'Infinity'::float8
    ),

    UNIQUE (circuit_id, parameter_index),
    UNIQUE (circuit_id, parameter_name)
);

-- ============================================================
-- 7. Dataset registry
-- ============================================================

CREATE TABLE datasets (
    dataset_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    organization_id BIGINT NOT NULL
        REFERENCES organizations(organization_id),

    dataset_name VARCHAR(150) NOT NULL,

    feature_count INTEGER NOT NULL CHECK (feature_count > 0),

    sample_count BIGINT NOT NULL CHECK (sample_count > 0),

    data_format VARCHAR(40) NOT NULL,

    data_location TEXT,

    data_checksum VARCHAR(128),

    preprocessing_definition JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (organization_id, dataset_name),

    CHECK (
        jsonb_typeof(preprocessing_definition) = 'object'
    )
);

-- ============================================================
-- 8. Optimization configurations
-- ============================================================

CREATE TABLE optimizer_configurations (
    optimizer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    optimizer_name VARCHAR(100) NOT NULL UNIQUE,

    algorithm optimizer_type NOT NULL,

    learning_rate DOUBLE PRECISION NOT NULL CHECK (
        learning_rate > 0 AND
        learning_rate < 'Infinity'::float8
    ),

    maximum_epochs INTEGER NOT NULL CHECK (
        maximum_epochs BETWEEN 1 AND 1000000
    ),

    convergence_tolerance DOUBLE PRECISION NOT NULL DEFAULT 0.000001
        CHECK (
            convergence_tolerance > 0 AND
            convergence_tolerance < 'Infinity'::float8
        ),

    batch_size INTEGER NOT NULL DEFAULT 8 CHECK (batch_size > 0),

    gradient_method VARCHAR(40) NOT NULL CHECK (
        gradient_method IN (
            'PARAMETER_SHIFT',
            'FINITE_DIFFERENCE',
            'SPSA',
            'BACKPROPAGATION'
        )
    ),

    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,

    CHECK (jsonb_typeof(configuration) = 'object')
);

-- ============================================================
-- 9. Governance policies
-- ============================================================

CREATE TABLE execution_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    organization_id BIGINT NOT NULL
        REFERENCES organizations(organization_id),

    policy_name VARCHAR(120) NOT NULL,

    maximum_qubits INTEGER NOT NULL CHECK (maximum_qubits > 0),

    maximum_depth INTEGER NOT NULL CHECK (maximum_depth > 0),

    maximum_evaluations BIGINT NOT NULL CHECK (
        maximum_evaluations > 0
    ),

    maximum_shots BIGINT NOT NULL CHECK (maximum_shots >= 0),

    allowed_backends execution_backend[] NOT NULL,

    require_validation BOOLEAN NOT NULL DEFAULT TRUE,

    allow_hardware_execution BOOLEAN NOT NULL DEFAULT FALSE,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (organization_id, policy_name),

    CHECK (cardinality(allowed_backends) > 0)
);

-- ============================================================
-- 10. Experiments
-- ============================================================

CREATE TABLE experiments (
    experiment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    organization_id BIGINT NOT NULL
        REFERENCES organizations(organization_id),

    circuit_id BIGINT NOT NULL
        REFERENCES circuits(circuit_id),

    dataset_id BIGINT NOT NULL
        REFERENCES datasets(dataset_id),

    optimizer_id BIGINT NOT NULL
        REFERENCES optimizer_configurations(optimizer_id),

    policy_id BIGINT NOT NULL
        REFERENCES execution_policies(policy_id),

    researcher_id BIGINT NOT NULL
        REFERENCES researchers(researcher_id),

    experiment_name VARCHAR(160) NOT NULL,

    status experiment_status NOT NULL DEFAULT 'CREATED',

    backend execution_backend NOT NULL,

    random_seed BIGINT NOT NULL DEFAULT 42,

    requested_shots BIGINT NOT NULL DEFAULT 0 CHECK (
        requested_shots >= 0
    ),

    initial_loss DOUBLE PRECISION,

    final_loss DOUBLE PRECISION,

    accuracy DOUBLE PRECISION CHECK (
        accuracy IS NULL OR accuracy BETWEEN 0 AND 1
    ),

    completed_epochs INTEGER NOT NULL DEFAULT 0 CHECK (
        completed_epochs >= 0
    ),

    circuit_evaluations BIGINT NOT NULL DEFAULT 0 CHECK (
        circuit_evaluations >= 0
    ),

    started_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    failure_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        initial_loss IS NULL OR
        (
            initial_loss >= 0 AND
            initial_loss < 'Infinity'::float8
        )
    ),

    CHECK (
        final_loss IS NULL OR
        (
            final_loss >= 0 AND
            final_loss < 'Infinity'::float8
        )
    ),

    CHECK (
        completed_at IS NULL OR started_at IS NOT NULL
    ),

    CHECK (
        status <> 'COMPLETED'
        OR (
            initial_loss IS NOT NULL
            AND final_loss IS NOT NULL
            AND completed_at IS NOT NULL
        )
    )
);

CREATE INDEX idx_experiments_status
ON experiments(status, created_at DESC);

CREATE INDEX idx_experiments_circuit
ON experiments(circuit_id, created_at DESC);

CREATE INDEX idx_experiments_researcher
ON experiments(researcher_id, created_at DESC);

CREATE INDEX idx_experiments_organization
ON experiments(organization_id, status);

CREATE TRIGGER experiments_updated_at
BEFORE UPDATE ON experiments
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 11. Experiment parameter snapshots
-- ============================================================

CREATE TABLE experiment_parameters (
    experiment_id BIGINT NOT NULL
        REFERENCES experiments(experiment_id) ON DELETE CASCADE,

    parameter_index INTEGER NOT NULL CHECK (parameter_index >= 0),

    initial_value DOUBLE PRECISION NOT NULL,

    optimized_value DOUBLE PRECISION,

    gradient_value DOUBLE PRECISION,

    PRIMARY KEY (experiment_id, parameter_index),

    CHECK (
        initial_value > '-Infinity'::float8 AND
        initial_value < 'Infinity'::float8
    ),

    CHECK (
        optimized_value IS NULL OR
        (
            optimized_value > '-Infinity'::float8 AND
            optimized_value < 'Infinity'::float8
        )
    )
);

-- ============================================================
-- 12. Execution checks
-- ============================================================

CREATE TABLE experiment_checks (
    check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    experiment_id BIGINT NOT NULL
        REFERENCES experiments(experiment_id) ON DELETE CASCADE,

    check_name VARCHAR(120) NOT NULL,

    check_category VARCHAR(60) NOT NULL,

    result check_status NOT NULL DEFAULT 'PENDING',

    details JSONB NOT NULL DEFAULT '{}'::jsonb,

    checked_at TIMESTAMPTZ,

    UNIQUE (experiment_id, check_name),

    CHECK (jsonb_typeof(details) = 'object')
);

CREATE INDEX idx_experiment_checks_result
ON experiment_checks(experiment_id, result);

-- ============================================================
-- 13. Epoch metrics
-- ============================================================

CREATE TABLE training_metrics (
    metric_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    experiment_id BIGINT NOT NULL
        REFERENCES experiments(experiment_id) ON DELETE CASCADE,

    epoch_number INTEGER NOT NULL CHECK (epoch_number > 0),

    training_loss DOUBLE PRECISION NOT NULL CHECK (
        training_loss >= 0 AND
        training_loss < 'Infinity'::float8
    ),

    validation_loss DOUBLE PRECISION,

    gradient_norm DOUBLE PRECISION,

    learning_rate DOUBLE PRECISION NOT NULL CHECK (
        learning_rate > 0
    ),

    execution_duration_ms BIGINT CHECK (
        execution_duration_ms IS NULL OR
        execution_duration_ms >= 0
    ),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (experiment_id, epoch_number)
);

CREATE INDEX idx_training_metrics_experiment_epoch
ON training_metrics(experiment_id, epoch_number);

-- ============================================================
-- 14. Execution events and audit history
-- ============================================================

CREATE TABLE experiment_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    experiment_id BIGINT NOT NULL
        REFERENCES experiments(experiment_id) ON DELETE CASCADE,

    event_type VARCHAR(80) NOT NULL,

    previous_status experiment_status,

    new_status experiment_status,

    event_message TEXT,

    event_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (jsonb_typeof(event_metadata) = 'object')
);

CREATE INDEX idx_experiment_events_timeline
ON experiment_events(experiment_id, created_at);

-- ============================================================
-- 15. State transition enforcement
-- ============================================================

CREATE FUNCTION validate_experiment_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status = OLD.status THEN
        RETURN NEW;
    END IF;

    IF NOT (
        (OLD.status = 'CREATED' AND
            NEW.status IN ('QUEUED', 'CANCELLED', 'FAILED'))
        OR
        (OLD.status = 'QUEUED' AND
            NEW.status IN ('RUNNING', 'CANCELLED', 'FAILED'))
        OR
        (OLD.status = 'RUNNING' AND
            NEW.status IN ('COMPLETED', 'FAILED', 'CANCELLED'))
    ) THEN
        RAISE EXCEPTION
            'Invalid experiment transition: % -> %',
            OLD.status, NEW.status;
    END IF;

    IF NEW.status = 'RUNNING' AND NEW.started_at IS NULL THEN
        NEW.started_at = CURRENT_TIMESTAMP;
    END IF;

    IF NEW.status IN ('COMPLETED', 'FAILED', 'CANCELLED') THEN
        NEW.completed_at = CURRENT_TIMESTAMP;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER experiments_state_transition
BEFORE UPDATE OF status ON experiments
FOR EACH ROW
EXECUTE FUNCTION validate_experiment_transition();

-- ============================================================
-- 16. Event audit trigger
-- ============================================================

CREATE FUNCTION record_experiment_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status <> OLD.status THEN
        INSERT INTO experiment_events (
            experiment_id,
            event_type,
            previous_status,
            new_status,
            event_message
        )
        VALUES (
            NEW.experiment_id,
            'STATE_TRANSITION',
            OLD.status,
            NEW.status,
            'Experiment lifecycle transition'
        );
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER experiment_transition_audit
AFTER UPDATE OF status ON experiments
FOR EACH ROW
EXECUTE FUNCTION record_experiment_transition();

-- ============================================================
-- 17. Eligibility determination
-- ============================================================

CREATE FUNCTION evaluate_experiment_eligibility(
    p_experiment_id BIGINT
)
RETURNS TABLE (
    eligible BOOLEAN,
    reasons TEXT[]
)
LANGUAGE plpgsql
AS $$
DECLARE
    e experiments%ROWTYPE;
    c circuits%ROWTYPE;
    d datasets%ROWTYPE;
    p execution_policies%ROWTYPE;
    o optimizer_configurations%ROWTYPE;
    r researchers%ROWTYPE;
    failures TEXT[] := ARRAY[]::TEXT[];
    failed_checks INTEGER;
BEGIN
    SELECT * INTO e
    FROM experiments
    WHERE experiment_id = p_experiment_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Experiment % does not exist.',
            p_experiment_id;
    END IF;

    SELECT * INTO c FROM circuits
    WHERE circuit_id = e.circuit_id;

    SELECT * INTO d FROM datasets
    WHERE dataset_id = e.dataset_id;

    SELECT * INTO p FROM execution_policies
    WHERE policy_id = e.policy_id;

    SELECT * INTO o FROM optimizer_configurations
    WHERE optimizer_id = e.optimizer_id;

    SELECT * INTO r FROM researchers
    WHERE researcher_id = e.researcher_id;

    IF NOT c.is_active THEN
        failures := array_append(failures, 'Circuit is inactive');
    END IF;

    IF NOT p.active THEN
        failures := array_append(failures, 'Execution policy is inactive');
    END IF;

    IF NOT r.active THEN
        failures := array_append(failures, 'Researcher is inactive');
    END IF;

    IF c.organization_id <> e.organization_id
       OR d.organization_id <> e.organization_id
       OR p.organization_id <> e.organization_id
       OR r.organization_id <> e.organization_id THEN

        failures := array_append(
            failures,
            'Organization ownership mismatch'
        );
    END IF;

    IF c.qubit_count > p.maximum_qubits THEN
        failures := array_append(
            failures,
            'Qubit limit exceeded'
        );
    END IF;

    IF c.circuit_depth > p.maximum_depth THEN
        failures := array_append(
            failures,
            'Circuit depth limit exceeded'
        );
    END IF;

    IF e.requested_shots > p.maximum_shots THEN
        failures := array_append(
            failures,
            'Shot budget exceeded'
        );
    END IF;

    IF NOT e.backend = ANY(p.allowed_backends) THEN
        failures := array_append(
            failures,
            'Backend not allowed by policy'
        );
    END IF;

    IF e.backend = 'QUANTUM_HARDWARE'
       AND NOT p.allow_hardware_execution THEN

        failures := array_append(
            failures,
            'Hardware execution prohibited'
        );
    END IF;

    IF d.feature_count <> c.qubit_count THEN
        failures := array_append(
            failures,
            'Dataset and circuit dimensions differ'
        );
    END IF;

    IF o.maximum_epochs < 1 THEN
        failures := array_append(
            failures,
            'Invalid optimization configuration'
        );
    END IF;

    IF p.require_validation THEN
        SELECT COUNT(*) INTO failed_checks
        FROM experiment_checks
        WHERE experiment_id = p_experiment_id
          AND result <> 'PASSED';

        IF failed_checks > 0 THEN
            failures := array_append(
                failures,
                'Required validation checks incomplete or failed'
            );
        END IF;
    END IF;

    RETURN QUERY
    SELECT cardinality(failures) = 0, failures;
END;
$$;

-- ============================================================
-- 18. Experiment creation and queueing procedure
-- ============================================================

CREATE PROCEDURE queue_experiment(
    p_experiment_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_eligible BOOLEAN;
    v_reasons TEXT[];
BEGIN
    SELECT eligible, reasons
    INTO v_eligible, v_reasons
    FROM evaluate_experiment_eligibility(p_experiment_id);

    IF NOT v_eligible THEN
        RAISE EXCEPTION
            'Experiment rejected: %',
            array_to_string(v_reasons, '; ');
    END IF;

    UPDATE experiments
    SET status = 'QUEUED'
    WHERE experiment_id = p_experiment_id
      AND status = 'CREATED';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Experiment is not in CREATED state.';
    END IF;

    INSERT INTO experiment_events (
        experiment_id,
        event_type,
        event_message
    )
    VALUES (
        p_experiment_id,
        'QUEUE_ACCEPTED',
        'Experiment passed eligibility checks'
    );
END;
$$;

-- ============================================================
-- 19. Reporting views
-- ============================================================

CREATE VIEW experiment_summary AS
SELECT
    e.experiment_id,
    e.experiment_name,
    o.organization_name,
    r.username AS researcher,
    c.circuit_name,
    c.qubit_count,
    c.circuit_depth,
    d.dataset_name,
    op.algorithm,
    e.backend,
    e.status,
    e.initial_loss,
    e.final_loss,
    e.accuracy,
    e.completed_epochs,
    e.circuit_evaluations,
    e.created_at,
    e.completed_at
FROM experiments e
JOIN organizations o
    ON o.organization_id = e.organization_id
JOIN researchers r
    ON r.researcher_id = e.researcher_id
JOIN circuits c
    ON c.circuit_id = e.circuit_id
JOIN datasets d
    ON d.dataset_id = e.dataset_id
JOIN optimizer_configurations op
    ON op.optimizer_id = e.optimizer_id;

CREATE VIEW experiment_validation_summary AS
SELECT
    e.experiment_id,
    e.experiment_name,
    COUNT(ch.check_id) AS total_checks,
    COUNT(ch.check_id) FILTER (
        WHERE ch.result = 'PASSED'
    ) AS passed_checks,
    COUNT(ch.check_id) FILTER (
        WHERE ch.result = 'FAILED'
    ) AS failed_checks,
    COUNT(ch.check_id) FILTER (
        WHERE ch.result = 'PENDING'
    ) AS pending_checks
FROM experiments e
LEFT JOIN experiment_checks ch
    ON ch.experiment_id = e.experiment_id
GROUP BY e.experiment_id, e.experiment_name;

-- ============================================================
-- 20. Sample organizational records
-- ============================================================

INSERT INTO organizations (organization_name)
VALUES
    ('Quantum Research Laboratory'),
    ('Applied Computing Institute');

INSERT INTO researchers (
    organization_id, username, email, role
)
VALUES
    (1, 'researcher_01', 'researcher01@example.org', 'RESEARCHER'),
    (1, 'reviewer_01', 'reviewer01@example.org', 'REVIEWER'),
    (1, 'operator_01', 'operator01@example.org', 'OPERATOR'),
    (2, 'researcher_02', 'researcher02@example.org', 'RESEARCHER');

INSERT INTO circuits (
    organization_id,
    owner_id,
    circuit_name,
    description,
    qubit_count,
    circuit_depth,
    ansatz_type,
    encoding_method
)
VALUES
    (
        1, 1,
        'Binary Classification VQC',
        'Two-qubit hardware-efficient variational classifier',
        2, 2,
        'HARDWARE_EFFICIENT',
        'ANGLE_ENCODING'
    ),
    (
        1, 1,
        'Deeper Experimental Ansatz',
        'Four-layer parameterized quantum circuit',
        2, 4,
        'PROBLEM_INSPIRED',
        'ANGLE_ENCODING'
    );

INSERT INTO circuit_parameters (
    circuit_id,
    parameter_index,
    parameter_name,
    initial_value,
    parameter_group
)
VALUES
    (1, 0, 'theta_0', 0.10, 'layer_0'),
    (1, 1, 'phi_0', 0.20, 'layer_0'),
    (1, 2, 'theta_1', 0.30, 'layer_0'),
    (1, 3, 'phi_1', 0.40, 'layer_0'),
    (1, 4, 'theta_2', 0.50, 'layer_1'),
    (1, 5, 'phi_2', 0.60, 'layer_1'),
    (1, 6, 'theta_3', 0.70, 'layer_1'),
    (1, 7, 'phi_3', 0.80, 'layer_1');

INSERT INTO circuit_gates (
    circuit_id,
    gate_sequence,
    gate_kind,
    target_qubit,
    control_qubit,
    parameter_index
)
VALUES
    (1, 0, 'RY', 0, NULL, 0),
    (1, 1, 'RZ', 0, NULL, 1),
    (1, 2, 'RY', 1, NULL, 2),
    (1, 3, 'RZ', 1, NULL, 3),
    (1, 4, 'CNOT', 1, 0, NULL),
    (1, 5, 'RY', 0, NULL, 4),
    (1, 6, 'RZ', 0, NULL, 5),
    (1, 7, 'RY', 1, NULL, 6),
    (1, 8, 'RZ', 1, NULL, 7),
    (1, 9, 'CNOT', 1, 0, NULL);

INSERT INTO datasets (
    organization_id,
    dataset_name,
    feature_count,
    sample_count,
    data_format,
    data_location,
    data_checksum
)
VALUES
    (
        1,
        'Binary Classification Dataset',
        2,
        8,
        'NUMERIC_CSV',
        'controlled://datasets/vqc-binary',
        'sha256:sample-dataset-checksum'
    );

INSERT INTO optimizer_configurations (
    optimizer_name,
    algorithm,
    learning_rate,
    maximum_epochs,
    convergence_tolerance,
    batch_size,
    gradient_method
)
VALUES
    (
        'Parameter Shift Gradient Descent',
        'GRADIENT_DESCENT',
        0.08,
        100,
        0.000001,
        8,
        'PARAMETER_SHIFT'
    ),
    (
        'SPSA Experimental Optimizer',
        'SPSA',
        0.02,
        200,
        0.00001,
        8,
        'SPSA'
    );

INSERT INTO execution_policies (
    organization_id,
    policy_name,
    maximum_qubits,
    maximum_depth,
    maximum_evaluations,
    maximum_shots,
    allowed_backends,
    require_validation,
    allow_hardware_execution
)
VALUES
    (
        1,
        'Standard Simulation Policy',
        8,
        10,
        100000,
        100000,
        ARRAY['STATE_VECTOR_SIMULATOR'::execution_backend],
        TRUE,
        FALSE
    ),
    (
        1,
        'Hardware Research Policy',
        20,
        100,
        1000000,
        1000000,
        ARRAY[
            'STATE_VECTOR_SIMULATOR'::execution_backend,
            'QUANTUM_HARDWARE'::execution_backend
        ],
        TRUE,
        TRUE
    ),
    (
        2,
        'Restricted Simulation Policy',
        4,
        5,
        10000,
        10000,
        ARRAY['STATE_VECTOR_SIMULATOR'::execution_backend],
        TRUE,
        FALSE
    );

-- ============================================================
-- 21. Valid experiment and failure-case records
-- ============================================================

INSERT INTO experiments (
    organization_id,
    circuit_id,
    dataset_id,
    optimizer_id,
    policy_id,
    researcher_id,
    experiment_name,
    backend,
    requested_shots
)
VALUES
    (
        1, 1, 1, 1, 1, 1,
        'Binary Classification Training',
        'STATE_VECTOR_SIMULATOR',
        0
    ),
    (
        1, 1, 1, 1, 1, 1,
        'Validation Failure Demonstration',
        'STATE_VECTOR_SIMULATOR',
        0
    ),
    (
        1, 1, 1, 1, 2, 1,
        'Hardware Backend Eligibility Example',
        'QUANTUM_HARDWARE',
        1000
    ),
    (
        1, 1, 1, 1, 1, 1,
        'Completed Experiment Example',
        'STATE_VECTOR_SIMULATOR',
        0
    );

-- ============================================================
-- 22. Validation records
-- ============================================================

INSERT INTO experiment_checks (
    experiment_id,
    check_name,
    check_category,
    result,
    details,
    checked_at
)
VALUES
    (
        1,
        'Parameter Shape Validation',
        'PARAMETERS',
        'PASSED',
        '{"expected":8,"actual":8}'::jsonb,
        CURRENT_TIMESTAMP
    ),
    (
        1,
        'State Normalization',
        'NUMERICAL',
        'PASSED',
        '{"normalization_error":0.000000001}'::jsonb,
        CURRENT_TIMESTAMP
    ),
    (
        1,
        'Evaluation Budget',
        'GOVERNANCE',
        'PASSED',
        '{"evaluations":5000,"maximum":100000}'::jsonb,
        CURRENT_TIMESTAMP
    ),
    (
        2,
        'Parameter Shape Validation',
        'PARAMETERS',
        'FAILED',
        '{"expected":8,"actual":6}'::jsonb,
        CURRENT_TIMESTAMP
    ),
    (
        3,
        'Hardware Approval',
        'GOVERNANCE',
        'PASSED',
        '{"hardware_approved":true}'::jsonb,
        CURRENT_TIMESTAMP
    ),
    (
        4,
        'State Normalization',
        'NUMERICAL',
        'PASSED',
        '{"normalization_error":0.000000001}'::jsonb,
        CURRENT_TIMESTAMP
    );

-- ============================================================
-- 23. Transactional workflow processing
-- ============================================================

-- Experiment 1 passes all eligibility checks and is queued.
CALL queue_experiment(1);

-- Experiment 2 remains CREATED because its parameter check failed.
-- Experiment 3 remains CREATED because its required validation
-- checks are incomplete.
-- Experiment 4 will demonstrate completed state reporting.

-- ============================================================
-- 24. Insert completed experiment metrics
-- ============================================================

INSERT INTO training_metrics (
    experiment_id,
    epoch_number,
    training_loss,
    validation_loss,
    gradient_norm,
    learning_rate,
    execution_duration_ms
)
VALUES
    (4, 1, 0.720000, 0.740000, 0.840000, 0.08, 120),
    (4, 2, 0.610000, 0.630000, 0.710000, 0.08, 115),
    (4, 3, 0.480000, 0.510000, 0.530000, 0.08, 118),
    (4, 4, 0.350000, 0.390000, 0.410000, 0.08, 122),
    (4, 5, 0.240000, 0.280000, 0.290000, 0.08, 117);

UPDATE experiments
SET
    status = 'QUEUED'
WHERE experiment_id = 4;

UPDATE experiments
SET
    status = 'RUNNING'
WHERE experiment_id = 4;

UPDATE experiments
SET
    status = 'COMPLETED',
    initial_loss = 0.720000,
    final_loss = 0.240000,
    accuracy = 0.875,
    completed_epochs = 5,
    circuit_evaluations = 5000
WHERE experiment_id = 4;

-- ============================================================
-- 25. Retrieval query
-- ============================================================

SELECT
    experiment_id,
    experiment_name,
    status,
    backend,
    final_loss,
    accuracy
FROM experiment_summary
ORDER BY created_at DESC;

-- ============================================================
-- 26. Eligibility query
-- ============================================================

SELECT
    e.experiment_id,
    e.experiment_name,
    eligibility.eligible,
    eligibility.reasons
FROM experiments e
CROSS JOIN LATERAL
    evaluate_experiment_eligibility(e.experiment_id)
    AS eligibility
ORDER BY e.experiment_id;

-- ============================================================
-- 27. Validation reporting
-- ============================================================

SELECT
    experiment_id,
    experiment_name,
    total_checks,
    passed_checks,
    failed_checks,
    pending_checks
FROM experiment_validation_summary
ORDER BY experiment_id;

-- ============================================================
-- 28. Aggregation and convergence analysis
-- ============================================================

WITH ordered_metrics AS (
    SELECT
        experiment_id,
        epoch_number,
        training_loss,
        LAG(training_loss) OVER (
            PARTITION BY experiment_id
            ORDER BY epoch_number
        ) AS previous_loss
    FROM training_metrics
),
convergence AS (
    SELECT
        experiment_id,
        COUNT(*) AS epochs,
        AVG(training_loss) AS average_loss,
        MIN(training_loss) AS minimum_loss,
        MAX(training_loss) AS maximum_loss,
        COUNT(*) FILTER (
            WHERE previous_loss IS NOT NULL
              AND training_loss < previous_loss
        ) AS improving_epochs
    FROM ordered_metrics
    GROUP BY experiment_id
)
SELECT *
FROM convergence
ORDER BY experiment_id;

-- ============================================================
-- 29. Optimizer performance reporting
-- ============================================================

SELECT
    op.algorithm,
    COUNT(e.experiment_id) AS experiment_count,
    AVG(e.final_loss) AS average_final_loss,
    AVG(e.accuracy) AS average_accuracy,
    AVG(e.circuit_evaluations) AS average_evaluations
FROM experiments e
JOIN optimizer_configurations op
    ON op.optimizer_id = e.optimizer_id
WHERE e.status = 'COMPLETED'
GROUP BY op.algorithm
ORDER BY average_final_loss;

-- ============================================================
-- 30. Workflow queue retrieval
-- ============================================================

SELECT
    experiment_id,
    experiment_name,
    created_at,
    backend
FROM experiments
WHERE status = 'QUEUED'
ORDER BY created_at
FOR UPDATE SKIP LOCKED;

-- ============================================================
-- 31. Audit history
-- ============================================================

SELECT
    event_id,
    experiment_id,
    event_type,
    previous_status,
    new_status,
    event_message,
    created_at
FROM experiment_events
ORDER BY created_at, event_id;

-- ============================================================
-- 32. Parameter retrieval
-- ============================================================

SELECT
    c.circuit_name,
    p.parameter_index,
    p.parameter_name,
    p.initial_value,
    p.trainable
FROM circuit_parameters p
JOIN circuits c
    ON c.circuit_id = p.circuit_id
ORDER BY c.circuit_id, p.parameter_index;

-- ============================================================
-- 33. Performance and governance report
-- ============================================================

SELECT
    c.circuit_name,
    c.qubit_count,
    c.circuit_depth,
    COUNT(DISTINCT e.experiment_id) AS experiments,
    AVG(e.circuit_evaluations) AS mean_evaluations,
    AVG(e.final_loss) AS mean_final_loss
FROM circuits c
LEFT JOIN experiments e
    ON e.circuit_id = c.circuit_id
GROUP BY
    c.circuit_id,
    c.circuit_name,
    c.qubit_count,
    c.circuit_depth
ORDER BY c.qubit_count, c.circuit_depth;

COMMIT;

-- ============================================================
-- Operational notes:
--
-- 1. State-vector memory grows exponentially with qubit count.
-- 2. Parameter-shift evaluations can dominate optimization cost.
-- 3. Hardware execution requires shot and backend governance.
-- 4. Experiment status triggers prevent invalid transitions.
-- 5. Eligibility is recalculated from current policy and checks.
-- 6. Organization ownership is validated before queueing.
-- 7. SKIP LOCKED supports concurrent queue consumers.
-- 8. Production deployments should restrict direct table updates,
--    grant access through controlled roles and procedures, and
--    retain immutable audit records.
--
-- This database records and governs experiments. It does not
-- itself execute quantum circuits.
-- ============================================================
