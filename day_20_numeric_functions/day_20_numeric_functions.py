"""
Numeric Functions: ROUND, CEIL, FLOOR, ABS, MOD, POWER, RANDOM

A comprehensive executable study of common numeric functions and their
behavior in practical programming.

The examples begin with basic arithmetic and progress through:
- rounding
- ceiling and flooring
- absolute values
- modulo/remainder
- powers and roots
- random number generation
- validation and error handling
- floating-point behavior
- financial-style rounding
- statistical simulations
- practical algorithms
- edge cases
- performance considerations

No external packages are required.
"""

from __future__ import annotations

import math
import random
import statistics
import time
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN, InvalidOperation
from typing import Iterable


# ---------------------------------------------------------------------------
# 1. BASIC CONCEPTS
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    """Print a readable section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


section("1. Numeric functions and their purpose")

numbers = [12.7, -12.7, 12.3, -12.3, 0.0]

for number in numbers:
    print(
        f"{number:>7}: "
        f"round={round(number):>4}, "
        f"ceil={math.ceil(number):>4}, "
        f"floor={math.floor(number):>4}, "
        f"abs={abs(number):>5}"
    )

print(
    """
ROUND  changes a number to a specified precision.
CEIL   returns the smallest integer greater than or equal to a number.
FLOOR  returns the largest integer less than or equal to a number.
ABS    returns the distance from zero.
MOD    returns the remainder after division.
POWER  raises a number to an exponent.
RANDOM produces values selected according to a random-number algorithm.
"""
)


# ---------------------------------------------------------------------------
# 2. ROUND
# ---------------------------------------------------------------------------

section("2. ROUND")

round_examples = [
    10.4,
    10.5,
    10.6,
    -10.4,
    -10.5,
    -10.6,
    123.456789,
]

for value in round_examples:
    print(f"round({value}) = {round(value)}")

print("\nRounding to a fixed number of decimal places:")

decimal_values = [12.345, 12.344, 12.3456, -12.345, 99.9999]

for value in decimal_values:
    print(
        f"{value:10} -> "
        f"0 decimals: {round(value):8} | "
        f"2 decimals: {round(value, 2):8} | "
        f"3 decimals: {round(value, 3):8}"
    )

print(
    """
Important Python behavior:
Python's round() uses rounding-to-even for halfway cases in many situations.

For example:
round(2.5) == 2
round(3.5) == 4

This reduces systematic bias when many halfway values are rounded, but it
may differ from the common school or financial expectation of "half up".
"""
)

for value in [2.5, 3.5, 4.5, 5.5, -2.5, -3.5]:
    print(f"round({value}) = {round(value)}")


# ---------------------------------------------------------------------------
# 3. FINANCIAL-STYLE ROUNDING
# ---------------------------------------------------------------------------

section("3. Decimal rounding and ROUND_HALF_UP")

financial_values = [
    Decimal("2.5"),
    Decimal("3.5"),
    Decimal("10.125"),
    Decimal("-2.5"),
]

for value in financial_values:
    half_up = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    half_even = value.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)

    print(
        f"{value:>8} -> "
        f"HALF_UP={half_up:>5}, "
        f"HALF_EVEN={half_even:>5}"
    )

print("\nTwo-decimal financial rounding:")

amounts = [
    Decimal("19.995"),
    Decimal("100.005"),
    Decimal("1234.567"),
    Decimal("-12.345"),
]

for amount in amounts:
    rounded = amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    print(f"{amount:>10} -> {rounded:>10}")


# ---------------------------------------------------------------------------
# 4. CEIL
# ---------------------------------------------------------------------------

section("4. CEIL")

ceil_values = [
    1.0,
    1.01,
    1.99,
    -1.01,
    -1.99,
    0.001,
    -0.001,
]

for value in ceil_values:
    print(f"ceil({value:>7}) = {math.ceil(value):>4}")

print(
    """
CEIL moves toward positive infinity.

This is particularly important for negative values:
ceil(-1.2) = -1
ceil(-1.8) = -1
"""


# ---------------------------------------------------------------------------
# 5. FLOOR
# ---------------------------------------------------------------------------

section("5. FLOOR")

for value in ceil_values:
    print(f"floor({value:>7}) = {math.floor(value):>4}")

print(
    """
FLOOR moves toward negative infinity.

Therefore:
floor(1.8)  = 1
floor(-1.8) = -2

This is different from truncation toward zero.
"""
)

for value in [1.8, -1.8, 1.2, -1.2]:
    print(
        f"{value:>5}: "
        f"floor={math.floor(value):>3}, "
        f"int={int(value):>3}"
    )


# ---------------------------------------------------------------------------
# 6. ABS
# ---------------------------------------------------------------------------

section("6. ABS")

for value in [-100, -10.5, -1, 0, 1, 10.5, 100]:
    print(f"abs({value:>6}) = {abs(value):>6}")

print("\nAbsolute difference:")

measurements = [
    (100, 97),
    (50, 61),
    (-10, 5),
    (-20, -31),
]

for first, second in measurements:
    difference = abs(first - second)
    print(f"|{first} - {second}| = {difference}")


def within_tolerance(actual: float, expected: float, tolerance: float) -> bool:
    """Check whether two values differ by no more than tolerance."""
    if tolerance < 0:
        raise ValueError("Tolerance cannot be negative.")

    return abs(actual - expected) <= tolerance


print("\nTolerance checks:")

tests = [
    (10.01, 10.00, 0.02),
    (10.10, 10.00, 0.02),
    (-5.01, -5.00, 0.02),
]

for actual, expected, tolerance in tests:
    print(
        f"actual={actual}, expected={expected}, "
        f"tolerance={tolerance} -> "
        f"{within_tolerance(actual, expected, tolerance)}"
    )


# ---------------------------------------------------------------------------
# 7. MODULO
# ---------------------------------------------------------------------------

section("7. MODULO")

print("Basic remainder examples:")

for dividend, divisor in [
    (10, 3),
    (10, 2),
    (17, 5),
    (100, 7),
    (25, 10),
]:
    print(f"{dividend} % {divisor} = {dividend % divisor}")

print("\nModulo is useful for repeating cycles:")

for number in range(12):
    print(f"{number:2} % 4 = {number % 4}")

print("\nEven and odd classification:")

for number in range(10):
    category = "even" if number % 2 == 0 else "odd"
    print(f"{number} -> {category}")


def is_divisible(number: int, divisor: int) -> bool:
    """Return True when number divides evenly by divisor."""
    if divisor == 0:
        raise ValueError("A divisor of zero is invalid.")

    return number % divisor == 0


print("\nDivisibility:")

for number in [10, 12, 15, 21, 25]:
    print(f"{number} divisible by 5? {is_divisible(number, 5)}")

print("\nModulo and negative values:")

for value in [-10, -7, -5, -2, -1, 0, 1, 2, 5, 7, 10]:
    print(f"{value:>4} % 3 = {value % 3:>2}")

print(
    """
Python's modulo result follows the sign of the divisor.

For positive divisors, the result is therefore normally in:
0 <= remainder < divisor
"""


# ---------------------------------------------------------------------------
# 8. MODULO FOR CLOCKS AND CYCLIC DATA
# ---------------------------------------------------------------------------

section("8. Modulo for cyclic systems")


def normalize_index(index: int, size: int) -> int:
    """Convert an arbitrary index into a valid cyclic index."""
    if size <= 0:
        raise ValueError("Size must be positive.")

    return index % size


items = ["A", "B", "C", "D", "E"]

for index in [-7, -1, 0, 1, 4, 5, 6, 11]:
    normalized = normalize_index(index, len(items))
    print(
        f"requested index={index:>3}, "
        f"normalized={normalized}, "
        f"value={items[normalized]}"
    )


def day_after(day_number: int, days_in_week: int = 7) -> int:
    """Return the next day using zero-based cyclic numbering."""
    return (day_number + 1) % days_in_week


print("\nCyclic day calculation:")

for day in range(7):
    print(f"day {day} -> next day {day_after(day)}")


# ---------------------------------------------------------------------------
# 9. POWER
# ---------------------------------------------------------------------------

section("9. POWER")

for base, exponent in [
    (2, 3),
    (5, 2),
    (10, 3),
    (9, 0),
    (2, -2),
]:
    print(f"{base}^{exponent} = {pow(base, exponent)}")

print("\nUsing math.pow():")
for base, exponent in [(2, 8), (3, 4), (10, 2)]:
    print(f"math.pow({base}, {exponent}) = {math.pow(base, exponent)}")

print("\nPython's exponentiation operator:")
for expression in ["2 ** 10", "9 ** 0.5", "27 ** (1 / 3)"]:
    print(f"{expression} = {eval(expression)}")


def safe_power(base: float, exponent: float) -> float:
    """Raise base to exponent while rejecting invalid non-finite input."""
    if not math.isfinite(base) or not math.isfinite(exponent):
        raise ValueError("Base and exponent must be finite.")

    try:
        result = base**exponent
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"Power operation failed: {exc}") from exc

    if isinstance(result, float) and not math.isfinite(result):
        raise OverflowError("Power result is not finite.")

    return result


print("\nSafe power examples:")

for base, exponent in [(2, 10), (4, 0.5), (10, -2)]:
    print(f"{base}^{exponent} = {safe_power(base, exponent)}")


# ---------------------------------------------------------------------------
# 10. POWER FOR PRACTICAL FORMULAS
# ---------------------------------------------------------------------------

section("10. Power in practical formulas")


def compound_value(
    principal: float,
    annual_rate: float,
    periods_per_year: int,
    years: float,
) -> float:
    """Calculate compound growth."""
    if principal < 0:
        raise ValueError("Principal cannot be negative.")
    if periods_per_year <= 0:
        raise ValueError("Periods per year must be positive.")
    if years < 0:
        raise ValueError("Years cannot be negative.")

    periodic_rate = annual_rate / periods_per_year
    number_of_periods = periods_per_year * years

    return principal * (1 + periodic_rate) ** number_of_periods


principal = 100000
rate = 0.08

for years in [1, 5, 10, 20]:
    value = compound_value(principal, rate, 12, years)
    print(f"{years:2} years -> {value:,.2f}")


# ---------------------------------------------------------------------------
# 11. RANDOM NUMBERS
# ---------------------------------------------------------------------------

section("11. RANDOM")

print("Random floating-point values in [0, 1):")

for _ in range(5):
    print(random.random())

print("\nRandom integers:")

for _ in range(5):
    print(random.randint(1, 100))

print("\nRandom values from a range:")

for _ in range(5):
    print(random.randrange(0, 50, 5))

print("\nRandom choice:")

colors = ["red", "green", "blue", "yellow"]

for _ in range(5):
    print(random.choice(colors))

print("\nRandom sample without replacement:")

population = list(range(1, 21))
print(random.sample(population, 5))

print("\nShuffling:")

cards = ["A", "K", "Q", "J", "10"]
random.shuffle(cards)
print(cards)


# ---------------------------------------------------------------------------
# 12. REPRODUCIBLE RANDOMNESS
# ---------------------------------------------------------------------------

section("12. Reproducible random sequences")

random.seed(42)
sequence_one = [random.randint(1, 100) for _ in range(10)]

random.seed(42)
sequence_two = [random.randint(1, 100) for _ in range(10)]

print("Sequence one:", sequence_one)
print("Sequence two:", sequence_two)
print("Identical:", sequence_one == sequence_two)

print(
    """
A seed is useful for testing and experiments because the same seed can
produce the same pseudo-random sequence.

A normal pseudo-random generator should not be treated as a cryptographic
security mechanism.
"""
)


# ---------------------------------------------------------------------------
# 13. RANDOM SIMULATION
# ---------------------------------------------------------------------------

section("13. Monte Carlo estimation of pi")

random.seed(12345)


def estimate_pi(number_of_points: int) -> float:
    """Estimate pi using random points inside a unit square."""
    if number_of_points <= 0:
        raise ValueError("Number of points must be positive.")

    inside_circle = 0

    for _ in range(number_of_points):
        x = random.random()
        y = random.random()

        if x * x + y * y <= 1:
            inside_circle += 1

    return 4 * inside_circle / number_of_points


for points in [100, 1_000, 10_000, 100_000]:
    estimate = estimate_pi(points)
    print(f"{points:>7} points -> estimated pi = {estimate:.8f}")


# ---------------------------------------------------------------------------
# 14. RANDOM DATA AND ROUNDING
# ---------------------------------------------------------------------------

section("14. Combining RANDOM, ROUND, ABS, MOD and POWER")

random.seed(7)

for _ in range(10):
    value = random.uniform(-10, 10)
    rounded = round(value, 2)
    magnitude = abs(value)
    remainder = int(magnitude * 100) % 10
    squared = value**2

    print(
        f"value={value:8.4f}, "
        f"round={rounded:7.2f}, "
        f"abs={magnitude:7.4f}, "
        f"mod={remainder}, "
        f"square={squared:9.4f}"
    )


# ---------------------------------------------------------------------------
# 15. EDGE CASES
# ---------------------------------------------------------------------------

section("15. Important edge cases")

print("Zero:")
print("abs(0) =", abs(0))
print("round(0) =", round(0))
print("0 % 5 =", 0 % 5)
print("0 ** 5 =", 0**5)

print("\nNegative zero in floating point:")
negative_zero = -0.0
print("negative_zero =", negative_zero)
print("abs(negative_zero) =", abs(negative_zero))
print("math.copysign(1, negative_zero) =", math.copysign(1, negative_zero))

print("\nVery small and very large values:")

small = 1e-12
large = 1e12

print("round(small, 5) =", round(small, 5))
print("ceil(small) =", math.ceil(small))
print("floor(small) =", math.floor(small))
print("round(large, -3) =", round(large, -3))

print("\nRounding to tens, hundreds and thousands:")

for value in [1234, 1567, 1899, -1234, -1567]:
    print(
        f"{value:>6} -> "
        f"tens={round(value, -1):>6}, "
        f"hundreds={round(value, -2):>6}, "
        f"thousands={round(value, -3):>6}"
    )


# ---------------------------------------------------------------------------
# 16. FLOATING-POINT PRECISION
# ---------------------------------------------------------------------------

section("16. Floating-point precision")

value = 0.1 + 0.2

print("0.1 + 0.2 =", value)
print("Exactly equal to 0.3?", value == 0.3)
print("Using isclose:", math.isclose(value, 0.3))

print("\nWhy abs() can be useful in numeric comparisons:")

actual = 0.1 + 0.2
expected = 0.3
difference = abs(actual - expected)

print("Difference:", difference)
print("Difference <= 1e-12:", difference <= 1e-12)

print(
    """
Floating-point numbers are binary approximations. Decimal fractions such
as 0.1 often cannot be represented exactly in binary floating point.

For scientific calculations, approximate comparison is often appropriate.
For exact decimal financial calculations, Decimal can be more suitable.
"""
)


# ---------------------------------------------------------------------------
# 17. SAFE NUMERIC VALIDATION
# ---------------------------------------------------------------------------

section("17. Numeric validation")


def require_finite_number(value: float, name: str = "value") -> float:
    """Validate that a value is a finite number."""
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric.")

    value = float(value)

    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")

    return value


for value in [10, 3.14, float("inf"), float("nan")]:
    try:
        validated = require_finite_number(value)
        print(f"{value!r} -> valid: {validated}")
    except (TypeError, ValueError) as error:
        print(f"{value!r} -> invalid: {error}")


# ---------------------------------------------------------------------------
# 18. A NUMERIC FUNCTION TOOLKIT
# ---------------------------------------------------------------------------

section("18. Reusable numeric toolkit")


class NumericToolkit:
    """Reusable collection of safe numeric operations."""

    @staticmethod
    def round_value(value: float, digits: int = 0) -> float:
        require_finite_number(value)
        return round(value, digits)

    @staticmethod
    def ceil_value(value: float) -> int:
        require_finite_number(value)
        return math.ceil(value)

    @staticmethod
    def floor_value(value: float) -> int:
        require_finite_number(value)
        return math.floor(value)

    @staticmethod
    def absolute_value(value: float) -> float:
        require_finite_number(value)
        return abs(value)

    @staticmethod
    def modulo(dividend: int, divisor: int) -> int:
        if divisor == 0:
            raise ZeroDivisionError("Modulo divisor cannot be zero.")
        return dividend % divisor

    @staticmethod
    def power(base: float, exponent: float) -> float:
        require_finite_number(base, "base")
        require_finite_number(exponent, "exponent")
        return safe_power(base, exponent)

    @staticmethod
    def random_integer(low: int, high: int) -> int:
        if low > high:
            raise ValueError("Low value cannot exceed high value.")
        return random.randint(low, high)


toolkit = NumericToolkit()

print(toolkit.round_value(12.3456, 2))
print(toolkit.ceil_value(12.01))
print(toolkit.floor_value(12.99))
print(toolkit.absolute_value(-50))
print(toolkit.modulo(17, 5))
print(toolkit.power(2, 8))
print(toolkit.random_integer(1, 10))


# ---------------------------------------------------------------------------
# 19. PRACTICAL DATA PROCESSING
# ---------------------------------------------------------------------------

section("19. Processing measurements")

measurements = [
    10.23,
    11.88,
    -2.44,
    19.91,
    15.005,
    20.999,
    8.125,
]

processed = []

for measurement in measurements:
    processed.append(
        {
            "original": measurement,
            "rounded": round(measurement, 2),
            "absolute": abs(measurement),
            "floor": math.floor(measurement),
            "ceil": math.ceil(measurement),
            "square": measurement**2,
        }
    )

for row in processed:
    print(row)


# ---------------------------------------------------------------------------
# 20. STATISTICAL APPLICATION
# ---------------------------------------------------------------------------

section("20. Random sample statistics")

random.seed(2026)

sample = [random.uniform(0, 100) for _ in range(1000)]

print("Count:", len(sample))
print("Mean:", round(statistics.mean(sample), 4))
print("Median:", round(statistics.median(sample), 4))
print("Minimum:", round(min(sample), 4))
print("Maximum:", round(max(sample), 4))
print("Standard deviation:", round(statistics.stdev(sample), 4))


# ---------------------------------------------------------------------------
# 21. PERFORMANCE COMPARISON
# ---------------------------------------------------------------------------

section("21. Simple performance measurement")

iterations = 200_000

start = time.perf_counter()
for number in range(iterations):
    result = abs(number - 100_000)
elapsed_abs = time.perf_counter() - start

start = time.perf_counter()
for number in range(iterations):
    result = math.floor(number / 3.7)
elapsed_floor = time.perf_counter() - start

start = time.perf_counter()
for number in range(iterations):
    result = number % 17
elapsed_modulo = time.perf_counter() - start

print(f"abs() loop:   {elapsed_abs:.6f} seconds")
print(f"floor() loop: {elapsed_floor:.6f} seconds")
print(f"modulo loop:  {elapsed_modulo:.6f} seconds")

print(
    """
Microbenchmarks depend on hardware, Python version, interpreter state and
the surrounding program. They should not be treated as universal timings.

In real applications, algorithmic complexity and unnecessary work often
matter more than tiny differences between numeric functions.
"""
)


# ---------------------------------------------------------------------------
# 22. ALGORITHM: ROUND-UP DIVISION
# ---------------------------------------------------------------------------

section("22. Practical algorithm using CEIL")

print(
    """
A common problem is determining how many complete containers are required
for a quantity of items when each container has a fixed capacity.

The mathematical operation is:
ceil(items / capacity)
"""
)


def containers_required(items: int, capacity: int) -> int:
    """Return the minimum number of containers needed."""
    if items < 0:
        raise ValueError("Items cannot be negative.")
    if capacity <= 0:
        raise ValueError("Capacity must be positive.")

    return math.ceil(items / capacity)


for items, capacity in [(0, 10), (1, 10), (10, 10), (11, 10), (101, 10)]:
    print(
        f"{items} items with capacity {capacity} "
        f"-> {containers_required(items, capacity)} containers"
    )


# ---------------------------------------------------------------------------
# 23. INTEGER-ONLY CEILING DIVISION
# ---------------------------------------------------------------------------

section("23. Integer ceiling division")

print(
    """
For positive integers, ceiling division can also be calculated without
floating-point arithmetic:

(items + capacity - 1) // capacity

This avoids converting very large integers to floating-point values.
"""
)


def integer_ceiling_division(items: int, capacity: int) -> int:
    """Ceiling division for non-negative integers."""
    if items < 0:
        raise ValueError("Items cannot be negative.")
    if capacity <= 0:
        raise ValueError("Capacity must be positive.")

    return (items + capacity - 1) // capacity


for items, capacity in [(0, 7), (1, 7), (7, 7), (8, 7), (15, 7)]:
    print(
        items,
        capacity,
        integer_ceiling_division(items, capacity),
    )


# ---------------------------------------------------------------------------
# 24. POWER AND ROOTS
# ---------------------------------------------------------------------------

section("24. Roots using powers")

for value in [4, 9, 16, 25, 64, 81]:
    square_root = value ** 0.5
    print(f"sqrt({value}) = {square_root}")

print("\nCube roots:")

for value in [1, 8, 27, 64, 125]:
    cube_root = value ** (1 / 3)
    print(f"cuberoot({value}) ≈ {cube_root:.8f}")

print(
    """
For numerical code, math.sqrt() is often clearer for square roots and can
provide appropriate domain checking for negative inputs.
"""
)


# ---------------------------------------------------------------------------
# 25. COMBINING FUNCTIONS IN A PRACTICAL SCORING MODEL
# ---------------------------------------------------------------------------

section("25. Practical scoring model")

scores = [72.4, 81.9, 64.2, 95.7, 88.3]

for score in scores:
    normalized = score / 100
    squared = normalized**2
    distance_from_target = abs(score - 80)
    bucket = math.floor(score / 10)

    print(
        f"score={score:5.1f}, "
        f"normalized={normalized:.3f}, "
        f"squared={squared:.3f}, "
        f"distance_from_80={distance_from_target:.1f}, "
        f"bucket={bucket}"
    )


# ---------------------------------------------------------------------------
# 26. ERROR HANDLING FOR MODULO AND POWER
# ---------------------------------------------------------------------------

section("26. Error handling")

try:
    print(10 % 0)
except ZeroDivisionError as error:
    print("Modulo error:", error)

try:
    print(safe_power(-2, 0.5))
except (ValueError, OverflowError) as error:
    print("Power error:", error)

try:
    print(containers_required(10, 0))
except ValueError as error:
    print("Container calculation error:", error)

try:
    Decimal("not-a-number")
except InvalidOperation as error:
    print("Decimal conversion error:", error)


# ---------------------------------------------------------------------------
# 27. NUMERIC FUNCTION COMPARISON TABLE
# ---------------------------------------------------------------------------

section("27. Function comparison")

comparison = [
    ("ROUND", "Changes precision", "round(12.345, 2)", "12.35"),
    ("CEIL", "Moves to +infinity", "ceil(12.1)", "13"),
    ("FLOOR", "Moves to -infinity", "floor(12.9)", "12"),
    ("ABS", "Distance from zero", "abs(-12)", "12"),
    ("MOD", "Remainder", "17 % 5", "2"),
    ("POWER", "Exponentiation", "2 ** 5", "32"),
    ("RANDOM", "Pseudo-random value", "random()", "variable"),
]

print(f"{'Function':<10} {'Purpose':<25} {'Example':<24} {'Result'}")
print("-" * 78)

for function_name, purpose, example, result in comparison:
    print(f"{function_name:<10} {purpose:<25} {example:<24} {result}")


# ---------------------------------------------------------------------------
# 28. MINI TEST SUITE
# ---------------------------------------------------------------------------

section("28. Built-in assertions")

assert round(12.345, 2) == 12.35
assert math.ceil(12.01) == 13
assert math.floor(12.99) == 12
assert abs(-50) == 50
assert 17 % 5 == 2
assert 2**8 == 256
assert normalize_index(12, 5) == 2
assert containers_required(101, 10) == 11
assert integer_ceiling_division(101, 10) == 11
assert math.isclose(0.1 + 0.2, 0.3)

print("All assertions passed.")


# ---------------------------------------------------------------------------
# 29. KEY RULES DISPLAY
# ---------------------------------------------------------------------------

section("29. Important rules to remember")

rules = [
    "ROUND changes numerical precision but its tie behavior depends on the language and function.",
    "CEIL moves toward positive infinity, not simply away from zero.",
    "FLOOR moves toward negative infinity, not simply toward zero.",
    "ABS converts a signed quantity into its magnitude.",
    "MOD gives the remainder and is useful for divisibility and cycles.",
    "POWER represents exponentiation and is useful for growth, geometry and formulas.",
    "RANDOM usually produces pseudo-random values, not cryptographically secure secrets.",
    "Floating-point values can contain small representation errors.",
    "Use Decimal when exact decimal arithmetic is required by the application.",
    "Validate divisors, capacities, ranges and other numeric inputs before calculation.",
    "For very large integer calculations, avoid unnecessary floating-point conversion.",
]

for number, rule in enumerate(rules, start=1):
    print(f"{number:02}. {rule}")


print("\nNumeric functions study completed successfully.")
