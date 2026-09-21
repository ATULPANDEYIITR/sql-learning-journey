/*
 * Numeric Functions:
 * ROUND, CEIL, FLOOR, ABS, MOD, POWER, RANDOM
 *
 * This file provides a self-contained study of common numeric operations
 * using JavaScript. It progresses from simple examples to practical
 * algorithms, validation, floating-point behavior, random simulation,
 * performance measurement, and reusable functions.
 *
 * Run with:
 *   node numeric-functions.js
 */

// ---------------------------------------------------------------------------
// 1. BASIC NUMERIC FUNCTIONS
// ---------------------------------------------------------------------------

function section(title) {
    console.log("\n" + "=".repeat(78));
    console.log(title);
    console.log("=".repeat(78));
}

section("1. Numeric functions");

const basicValues = [12.7, -12.7, 12.3, -12.3, 0];

for (const value of basicValues) {
    console.log(
        `${value}: ` +
        `round=${Math.round(value)}, ` +
        `ceil=${Math.ceil(value)}, ` +
        `floor=${Math.floor(value)}, ` +
        `abs=${Math.abs(value)}`
    );
}

console.log(`
ROUND  changes a value toward an integer using JavaScript's Math.round rules.
CEIL   returns the smallest integer greater than or equal to a value.
FLOOR  returns the largest integer less than or equal to a value.
ABS    returns the magnitude of a value.
MOD    is normally represented by JavaScript's % remainder operator.
POWER  can be calculated using ** or Math.pow().
RANDOM produces a pseudo-random floating-point value from 0 inclusive to 1 exclusive.
`);


// ---------------------------------------------------------------------------
// 2. ROUND
// ---------------------------------------------------------------------------

section("2. ROUND");

for (const value of [10.4, 10.5, 10.6, -10.4, -10.5, -10.6]) {
    console.log(`Math.round(${value}) = ${Math.round(value)}`);
}

console.log("\nRounding to decimal places:");

function roundTo(value, decimalPlaces) {
    if (!Number.isFinite(value)) {
        throw new TypeError("Value must be finite.");
    }

    if (!Number.isInteger(decimalPlaces)) {
        throw new TypeError("Decimal places must be an integer.");
    }

    const factor = 10 ** decimalPlaces;
    return Math.round(value * factor) / factor;
}

for (const value of [12.345, 12.344, 99.9999, -12.345]) {
    console.log(
        `${value} -> ` +
        `2 decimals: ${roundTo(value, 2)}, ` +
        `3 decimals: ${roundTo(value, 3)}`
    );
}


// ---------------------------------------------------------------------------
// 3. CEIL
// ---------------------------------------------------------------------------

section("3. CEIL");

for (const value of [1, 1.01, 1.99, -1.01, -1.99, 0.001, -0.001]) {
    console.log(`Math.ceil(${value}) = ${Math.ceil(value)}`);
}

console.log(`
Math.ceil() moves toward positive infinity.
Therefore Math.ceil(-1.8) is -1, not -2.
`);


// ---------------------------------------------------------------------------
// 4. FLOOR
// ---------------------------------------------------------------------------

section("4. FLOOR");

for (const value of [1, 1.01, 1.99, -1.01, -1.99, 0.001, -0.001]) {
    console.log(`Math.floor(${value}) = ${Math.floor(value)}`);
}

console.log(`
Math.floor() moves toward negative infinity.
Therefore Math.floor(-1.8) is -2.
`);


// ---------------------------------------------------------------------------
// 5. ABS
// ---------------------------------------------------------------------------

section("5. ABS");

for (const value of [-100, -10.5, -1, 0, 1, 10.5, 100]) {
    console.log(`Math.abs(${value}) = ${Math.abs(value)}`);
}

function absoluteDifference(first, second) {
    return Math.abs(first - second);
}

console.log("\nAbsolute differences:");

for (const [first, second] of [
    [100, 97],
    [50, 61],
    [-10, 5],
    [-20, -31]
]) {
    console.log(
        `|${first} - ${second}| = ${absoluteDifference(first, second)}`
    );
}


// ---------------------------------------------------------------------------
// 6. MODULO / REMAINDER
// ---------------------------------------------------------------------------

section("6. MODULO / REMAINDER");

for (const [dividend, divisor] of [
    [10, 3],
    [17, 5],
    [100, 7],
    [25, 10]
]) {
    console.log(`${dividend} % ${divisor} = ${dividend % divisor}`);
}

console.log("\nEven and odd classification:");

for (let number = 0; number < 10; number++) {
    console.log(
        `${number} -> ${number % 2 === 0 ? "even" : "odd"}`
    );
}

console.log("\nJavaScript's remainder behavior with negative values:");

for (const value of [-10, -7, -5, -2, -1, 0, 1, 2, 5, 7, 10]) {
    console.log(`${value} % 3 = ${value % 3}`);
}

function isDivisible(number, divisor) {
    if (!Number.isInteger(number) || !Number.isInteger(divisor)) {
        throw new TypeError("Both arguments must be integers.");
    }

    if (divisor === 0) {
        throw new RangeError("Divisor cannot be zero.");
    }

    return number % divisor === 0;
}

console.log("\nDivisibility:");

for (const number of [10, 12, 15, 21, 25]) {
    console.log(`${number} divisible by 5? ${isDivisible(number, 5)}`);
}


// ---------------------------------------------------------------------------
// 7. CYCLIC INDEXING
// ---------------------------------------------------------------------------

section("7. Modulo for cyclic data");

function normalizeIndex(index, size) {
    if (!Number.isInteger(index) || !Number.isInteger(size)) {
        throw new TypeError("Index and size must be integers.");
    }

    if (size <= 0) {
        throw new RangeError("Size must be positive.");
    }

    return ((index % size) + size) % size;
}

const items = ["A", "B", "C", "D", "E"];

for (const index of [-7, -1, 0, 1, 4, 5, 6, 11]) {
    const normalized = normalizeIndex(index, items.length);

    console.log(
        `index=${index}, normalized=${normalized}, value=${items[normalized]}`
    );
}


// ---------------------------------------------------------------------------
// 8. POWER
// ---------------------------------------------------------------------------

section("8. POWER");

for (const [base, exponent] of [
    [2, 3],
    [5, 2],
    [10, 3],
    [9, 0],
    [2, -2]
]) {
    console.log(
        `${base} ** ${exponent} = ${base ** exponent}`
    );
}

console.log("\nUsing Math.pow():");

for (const [base, exponent] of [[2, 8], [3, 4], [10, 2]]) {
    console.log(
        `Math.pow(${base}, ${exponent}) = ${Math.pow(base, exponent)}`
    );
}

console.log("\nRoots:");

for (const value of [4, 9, 16, 25, 64, 81]) {
    console.log(
        `sqrt(${value}) = ${Math.pow(value, 0.5)}`
    );
}


// ---------------------------------------------------------------------------
// 9. POWER IN PRACTICAL FORMULAS
// ---------------------------------------------------------------------------

section("9. Compound growth");

function compoundValue(principal, annualRate, periodsPerYear, years) {
    if (!Number.isFinite(principal) || principal < 0) {
        throw new RangeError("Principal must be a non-negative finite number.");
    }

    if (!Number.isFinite(annualRate)) {
        throw new TypeError("Annual rate must be finite.");
    }

    if (!Number.isInteger(periodsPerYear) || periodsPerYear <= 0) {
        throw new RangeError("Periods per year must be a positive integer.");
    }

    if (!Number.isFinite(years) || years < 0) {
        throw new RangeError("Years must be non-negative and finite.");
    }

    const periodicRate = annualRate / periodsPerYear;
    const numberOfPeriods = periodsPerYear * years;

    return principal * (1 + periodicRate) ** numberOfPeriods;
}

for (const years of [1, 5, 10, 20]) {
    console.log(
        `${years} years -> ` +
        `${compoundValue(100000, 0.08, 12, years).toFixed(2)}`
    );
}


// ---------------------------------------------------------------------------
// 10. RANDOM
// ---------------------------------------------------------------------------

section("10. RANDOM");

console.log("Random values in [0, 1):");

for (let i = 0; i < 5; i++) {
    console.log(Math.random());
}

console.log("\nRandom integer from 1 through 100:");

function randomInteger(min, max) {
    if (!Number.isInteger(min) || !Number.isInteger(max)) {
        throw new TypeError("Bounds must be integers.");
    }

    if (min > max) {
        throw new RangeError("Minimum cannot exceed maximum.");
    }

    return Math.floor(Math.random() * (max - min + 1)) + min;
}

for (let i = 0; i < 5; i++) {
    console.log(randomInteger(1, 100));
}

console.log("\nRandom choice:");

function randomChoice(array) {
    if (!Array.isArray(array) || array.length === 0) {
        throw new RangeError("Array must contain at least one element.");
    }

    return array[Math.floor(Math.random() * array.length)];
}

const colors = ["red", "green", "blue", "yellow"];

for (let i = 0; i < 5; i++) {
    console.log(randomChoice(colors));
}


// ---------------------------------------------------------------------------
// 11. RANDOM SIMULATION
// ---------------------------------------------------------------------------

section("11. Monte Carlo estimation of pi");

function estimatePi(numberOfPoints) {
    if (!Number.isInteger(numberOfPoints) || numberOfPoints <= 0) {
        throw new RangeError("Number of points must be positive.");
    }

    let insideCircle = 0;

    for (let i = 0; i < numberOfPoints; i++) {
        const x = Math.random();
        const y = Math.random();

        if (x * x + y * y <= 1) {
            insideCircle++;
        }
    }

    return 4 * insideCircle / numberOfPoints;
}

for (const points of [100, 1000, 10000, 100000]) {
    console.log(
        `${points} points -> ${estimatePi(points).toFixed(8)}`
    );
}


// ---------------------------------------------------------------------------
// 12. FLOATING-POINT PRECISION
// ---------------------------------------------------------------------------

section("12. Floating-point precision");

const floatingPointResult = 0.1 + 0.2;

console.log("0.1 + 0.2 =", floatingPointResult);
console.log("Exactly equal to 0.3?", floatingPointResult === 0.3);

function approximatelyEqual(first, second, tolerance = Number.EPSILON * 10) {
    if (!Number.isFinite(first) || !Number.isFinite(second)) {
        return first === second;
    }

    return Math.abs(first - second) <= tolerance;
}

console.log(
    "Approximately equal:",
    approximatelyEqual(floatingPointResult, 0.3)
);

console.log(`
JavaScript Number uses IEEE 754 double-precision floating point for ordinary
numeric values. Decimal fractions may therefore contain small representation
errors.

For display, toFixed() can be useful, but it returns a string.
`);

console.log("123.456789.toFixed(2) =", (123.456789).toFixed(2));
console.log("Type:", typeof (123.456789).toFixed(2));


// ---------------------------------------------------------------------------
// 13. PRACTICAL CEILING DIVISION
// ---------------------------------------------------------------------------

section("13. Ceiling division");

function containersRequired(items, capacity) {
    if (!Number.isInteger(items) || items < 0) {
        throw new RangeError("Items must be a non-negative integer.");
    }

    if (!Number.isInteger(capacity) || capacity <= 0) {
        throw new RangeError("Capacity must be a positive integer.");
    }

    return Math.ceil(items / capacity);
}

for (const [itemsCount, capacity] of [
    [0, 10],
    [1, 10],
    [10, 10],
    [11, 10],
    [101, 10]
]) {
    console.log(
        `${itemsCount} items, capacity ${capacity} -> ` +
        `${containersRequired(itemsCount, capacity)} containers`
    );
}


// ---------------------------------------------------------------------------
// 14. INTEGER-ONLY CEILING DIVISION
// ---------------------------------------------------------------------------

section("14. Integer ceiling division without floating point");

function integerCeilingDivision(items, capacity) {
    if (!Number.isSafeInteger(items) || items < 0) {
        throw new RangeError("Items must be a non-negative safe integer.");
    }

    if (!Number.isSafeInteger(capacity) || capacity <= 0) {
        throw new RangeError("Capacity must be a positive safe integer.");
    }

    return Math.floor((items + capacity - 1) / capacity);
}

for (const [itemsCount, capacity] of [
    [0, 7],
    [1, 7],
    [7, 7],
    [8, 7],
    [15, 7]
]) {
    console.log(
        `${itemsCount} / ${capacity} -> ` +
        `${integerCeilingDivision(itemsCount, capacity)}`
    );
}


// ---------------------------------------------------------------------------
// 15. RANDOM DATA PROCESSING
// ---------------------------------------------------------------------------

section("15. Combining numeric functions");

for (let i = 0; i < 10; i++) {
    const value = Math.random() * 20 - 10;
    const rounded = roundTo(value, 2);
    const magnitude = Math.abs(value);
    const remainder = Math.floor(magnitude * 100) % 10;
    const squared = value ** 2;

    console.log(
        `value=${value.toFixed(4)}, ` +
        `round=${rounded.toFixed(2)}, ` +
        `abs=${magnitude.toFixed(4)}, ` +
        `mod=${remainder}, ` +
        `square=${squared.toFixed(4)}`
    );
}


// ---------------------------------------------------------------------------
// 16. NUMERIC TOOLKIT
// ---------------------------------------------------------------------------

section("16. Reusable numeric toolkit");

class NumericToolkit {
    static round(value, digits = 0) {
        return roundTo(value, digits);
    }

    static ceil(value) {
        if (!Number.isFinite(value)) {
            throw new TypeError("Value must be finite.");
        }

        return Math.ceil(value);
    }

    static floor(value) {
        if (!Number.isFinite(value)) {
            throw new TypeError("Value must be finite.");
        }

        return Math.floor(value);
    }

    static abs(value) {
        if (!Number.isFinite(value)) {
            throw new TypeError("Value must be finite.");
        }

        return Math.abs(value);
    }

    static mod(dividend, divisor) {
        if (divisor === 0) {
            throw new RangeError("Divisor cannot be zero.");
        }

        return dividend % divisor;
    }

    static power(base, exponent) {
        if (!Number.isFinite(base) || !Number.isFinite(exponent)) {
            throw new TypeError("Base and exponent must be finite.");
        }

        return base ** exponent;
    }

    static randomInteger(min, max) {
        return randomInteger(min, max);
    }
}

console.log(NumericToolkit.round(12.3456, 2));
console.log(NumericToolkit.ceil(12.01));
console.log(NumericToolkit.floor(12.99));
console.log(NumericToolkit.abs(-50));
console.log(NumericToolkit.mod(17, 5));
console.log(NumericToolkit.power(2, 8));
console.log(NumericToolkit.randomInteger(1, 10));


// ---------------------------------------------------------------------------
// 17. ERROR HANDLING
// ---------------------------------------------------------------------------

section("17. Error handling");

try {
    NumericToolkit.mod(10, 0);
} catch (error) {
    console.log("Modulo error:", error.message);
}

try {
    containersRequired(10, 0);
} catch (error) {
    console.log("Container error:", error.message);
}

try {
    randomInteger(10, 1);
} catch (error) {
    console.log("Random range error:", error.message);
}


// ---------------------------------------------------------------------------
// 18. SPECIAL VALUES
// ---------------------------------------------------------------------------

section("18. Special numeric values");

const specialValues = [
    NaN,
    Infinity,
    -Infinity,
    0,
    -0
];

for (const value of specialValues) {
    console.log({
        value,
        isNaN: Number.isNaN(value),
        isFinite: Number.isFinite(value),
        absolute: Math.abs(value),
        rounded: Math.round(value),
        floor: Math.floor(value),
        ceil: Math.ceil(value)
    });
}

console.log("\nJavaScript peculiarities:");

console.log("NaN === NaN:", NaN === NaN);
console.log("Number.isNaN(NaN):", Number.isNaN(NaN));
console.log("Object.is(-0, 0):", Object.is(-0, 0));
console.log("Object.is(-0, -0):", Object.is(-0, -0));


// ---------------------------------------------------------------------------
// 19. BIGINT DISTINCTION
// ---------------------------------------------------------------------------

section("19. Number versus BigInt");

const largeInteger = 9007199254740991;
console.log("Largest commonly safe integer:", Number.MAX_SAFE_INTEGER);
console.log("Is safe:", Number.isSafeInteger(largeInteger));

const bigInteger = 9007199254740991n + 10n;

console.log("BigInt value:", bigInteger);
console.log("BigInt modulo:", bigInteger % 7n);
console.log("BigInt power:", 2n ** 10n);

console.log(`
BigInt is useful for integers larger than the safe integer range of Number.
It cannot be freely mixed with Number in arithmetic expressions.
`);


// ---------------------------------------------------------------------------
// 20. PERFORMANCE MEASUREMENT
// ---------------------------------------------------------------------------

section("20. Simple performance measurement");

const iterations = 200000;

let start = performance.now();

let result = 0;

for (let i = 0; i < iterations; i++) {
    result += Math.abs(i - 100000);
}

const absTime = performance.now() - start;

start = performance.now();

result = 0;

for (let i = 0; i < iterations; i++) {
    result += Math.floor(i / 3.7);
}

const floorTime = performance.now() - start;

start = performance.now();

result = 0;

for (let i = 0; i < iterations; i++) {
    result += i % 17;
}

const moduloTime = performance.now() - start;

console.log(`abs:    ${absTime.toFixed(4)} ms`);
console.log(`floor:  ${floorTime.toFixed(4)} ms`);
console.log(`modulo: ${moduloTime.toFixed(4)} ms`);

console.log(`
These measurements are environment-dependent. JavaScript engines may use
JIT compilation and optimize code differently. Application architecture
and algorithmic complexity usually matter more than tiny microbenchmark
differences.
`);


// ---------------------------------------------------------------------------
// 21. NUMERIC DATA PROCESSING
// ---------------------------------------------------------------------------

section("21. Measurement processing");

const measurements = [
    10.23,
    11.88,
    -2.44,
    19.91,
    15.005,
    20.999,
    8.125
];

for (const measurement of measurements) {
    console.log({
        original: measurement,
        rounded: roundTo(measurement, 2),
        absolute: Math.abs(measurement),
        floor: Math.floor(measurement),
        ceil: Math.ceil(measurement),
        square: measurement ** 2
    });
}


// ---------------------------------------------------------------------------
// 22. MINI TEST SUITE
// ---------------------------------------------------------------------------

section("22. Assertions");

console.assert(roundTo(12.345, 2) === 12.35);
console.assert(Math.ceil(12.01) === 13);
console.assert(Math.floor(12.99) === 12);
console.assert(Math.abs(-50) === 50);
console.assert(17 % 5 === 2);
console.assert(2 ** 8 === 256);
console.assert(normalizeIndex(12, 5) === 2);
console.assert(containersRequired(101, 10) === 11);
console.assert(integerCeilingDivision(101, 10) === 11);

console.log("Assertions completed.");


// ---------------------------------------------------------------------------
// 23. FUNCTION COMPARISON
// ---------------------------------------------------------------------------

section("23. Function comparison");

const comparison = [
    ["ROUND", "Precision adjustment", "Math.round(12.5)", "13"],
    ["CEIL", "Toward +infinity", "Math.ceil(12.1)", "13"],
    ["FLOOR", "Toward -infinity", "Math.floor(12.9)", "12"],
    ["ABS", "Magnitude", "Math.abs(-12)", "12"],
    ["MOD", "Remainder", "17 % 5", "2"],
    ["POWER", "Exponentiation", "2 ** 5", "32"],
    ["RANDOM", "Pseudo-random value", "Math.random()", "variable"]
];

console.table(
    comparison.map(([functionName, purpose, example, result]) => ({
        function: functionName,
        purpose,
        example,
        result
    }))
);

console.log("\nNumeric functions study completed successfully.");
