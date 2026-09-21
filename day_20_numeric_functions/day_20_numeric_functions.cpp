/*
 * Numeric Functions: ROUND, CEIL, FLOOR, ABS, MOD, POWER, RANDOM
 *
 * C++17 case study:
 * A warehouse inventory and shipment planning system.
 *
 * The program demonstrates how numeric functions can be combined in a
 * realistic system that:
 * - stores product quantities and measurements
 * - calculates shipping containers using ceiling logic
 * - handles prices and discounts
 * - uses absolute differences for inventory reconciliation
 * - uses modulo for cyclic scheduling and divisibility
 * - uses powers for growth and scoring calculations
 * - uses random numbers for simulation
 * - validates input
 * - reports errors
 * - measures basic performance
 *
 * Compile:
 *   g++ -std=c++17 -O2 numeric_functions.cpp -o numeric_functions
 *
 * Run:
 *   ./numeric_functions
 */

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;


// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

void section(const string& title) {
    cout << "\n" << string(78, '=') << "\n";
    cout << title << "\n";
    cout << string(78, '=') << "\n";
}

double requireFinite(double value, const string& name) {
    if (!std::isfinite(value)) {
        throw invalid_argument(name + " must be finite.");
    }

    return value;
}


// ---------------------------------------------------------------------------
// Numeric function demonstrations
// ---------------------------------------------------------------------------

void demonstrateRound() {
    section("1. ROUND");

    vector<double> values{
        12.4, 12.5, 12.6,
        -12.4, -12.5, -12.6,
        123.4567
    };

    for (double value : values) {
        cout << fixed << setprecision(4)
             << value
             << " -> round=" << std::round(value)
             << '\n';
    }

    cout << "\nC++ std::round rounds halfway cases away from zero.\n";
    cout << "std::round(2.5) = " << std::round(2.5) << '\n';
    cout << "std::round(-2.5) = " << std::round(-2.5) << '\n';
}

void demonstrateCeilAndFloor() {
    section("2. CEIL AND FLOOR");

    vector<double> values{
        1.01, 1.99,
        -1.01, -1.99
    };

    for (double value : values) {
        cout << fixed << setprecision(2)
             << value
             << " -> ceil=" << std::ceil(value)
             << ", floor=" << std::floor(value)
             << '\n';
    }

    cout << "\nCEIL moves toward positive infinity.\n";
    cout << "FLOOR moves toward negative infinity.\n";
}

void demonstrateAbs() {
    section("3. ABS");

    vector<double> values{
        -100.0, -10.5, -1.0, 0.0, 1.0, 10.5, 100.0
    };

    for (double value : values) {
        cout << "abs(" << value << ") = "
             << std::abs(value) << '\n';
    }
}

void demonstrateModulo() {
    section("4. MODULO");

    cout << "17 % 5 = " << (17 % 5) << '\n';
    cout << "100 % 7 = " << (100 % 7) << '\n';
    cout << "25 % 10 = " << (25 % 10) << '\n';

    cout << "\nEven and odd numbers:\n";

    for (int number = 0; number < 10; ++number) {
        cout << number << " -> "
             << (number % 2 == 0 ? "even" : "odd")
             << '\n';
    }

    cout << "\nNegative integer remainder:\n";

    for (int number : {-10, -7, -5, -2, -1, 0, 1, 2, 5, 7, 10}) {
        cout << number << " % 3 = " << (number % 3) << '\n';
    }
}

void demonstratePower() {
    section("5. POWER");

    cout << "2^3 = " << std::pow(2.0, 3.0) << '\n';
    cout << "5^2 = " << std::pow(5.0, 2.0) << '\n';
    cout << "10^3 = " << std::pow(10.0, 3.0) << '\n';
    cout << "9^0 = " << std::pow(9.0, 0.0) << '\n';
    cout << "2^-2 = " << std::pow(2.0, -2.0) << '\n';

    cout << "\nSquare root using power:\n";
    cout << "sqrt(81) = " << std::pow(81.0, 0.5) << '\n';

    cout << "\nPreferred square-root function:\n";
    cout << "sqrt(81) = " << std::sqrt(81.0) << '\n';
}


// ---------------------------------------------------------------------------
// Numeric algorithms
// ---------------------------------------------------------------------------

int containersRequired(int items, int capacity) {
    if (items < 0) {
        throw invalid_argument("Items cannot be negative.");
    }

    if (capacity <= 0) {
        throw invalid_argument("Capacity must be positive.");
    }

    // For non-negative integers:
    // ceil(items / capacity) can be computed without floating point.
    return (items + capacity - 1) / capacity;
}

int normalizeIndex(int index, int size) {
    if (size <= 0) {
        throw invalid_argument("Size must be positive.");
    }

    // C++ remainder can be negative. Adding size before the second %
    // produces a normalized value in [0, size).
    return ((index % size) + size) % size;
}

bool isDivisible(int number, int divisor) {
    if (divisor == 0) {
        throw invalid_argument("Divisor cannot be zero.");
    }

    return number % divisor == 0;
}


// ---------------------------------------------------------------------------
// Warehouse domain model
// ---------------------------------------------------------------------------

struct Product {
    int id;
    string name;
    int quantity;
    double unitPrice;
    int unitsPerContainer;
};

class Warehouse {
private:
    vector<Product> products;

public:
    void addProduct(const Product& product) {
        if (product.id <= 0) {
            throw invalid_argument("Product ID must be positive.");
        }

        if (product.quantity < 0) {
            throw invalid_argument("Quantity cannot be negative.");
        }

        if (!std::isfinite(product.unitPrice) || product.unitPrice < 0) {
            throw invalid_argument(
                "Unit price must be a non-negative finite number."
            );
        }

        if (product.unitsPerContainer <= 0) {
            throw invalid_argument(
                "Units per container must be positive."
            );
        }

        products.push_back(product);
    }

    const vector<Product>& getProducts() const {
        return products;
    }

    int totalUnits() const {
        int total = 0;

        for (const Product& product : products) {
            total += product.quantity;
        }

        return total;
    }

    double inventoryValue() const {
        double total = 0.0;

        for (const Product& product : products) {
            total +=
                static_cast<double>(product.quantity) *
                product.unitPrice;
        }

        return total;
    }

    int totalContainers() const {
        int total = 0;

        for (const Product& product : products) {
            total += containersRequired(
                product.quantity,
                product.unitsPerContainer
            );
        }

        return total;
    }

    void printReport() const {
        section("6. Warehouse inventory report");

        cout << left
             << setw(8) << "ID"
             << setw(20) << "Product"
             << setw(12) << "Quantity"
             << setw(14) << "Unit Price"
             << setw(14) << "Containers"
             << '\n';

        cout << string(68, '-') << '\n';

        for (const Product& product : products) {
            cout << left
                 << setw(8) << product.id
                 << setw(20) << product.name
                 << setw(12) << product.quantity
                 << setw(14) << fixed << setprecision(2)
                 << product.unitPrice
                 << setw(14)
                 << containersRequired(
                        product.quantity,
                        product.unitsPerContainer
                    )
                 << '\n';
        }

        cout << "\nTotal units: " << totalUnits() << '\n';

        cout << fixed << setprecision(2)
             << "Inventory value: $" << inventoryValue() << '\n';

        cout << "Containers required: " << totalContainers() << '\n';
    }
};


// ---------------------------------------------------------------------------
// Pricing calculations
// ---------------------------------------------------------------------------

double calculateDiscountedPrice(
    double price,
    double discountPercent
) {
    requireFinite(price, "Price");
    requireFinite(discountPercent, "Discount percentage");

    if (price < 0) {
        throw invalid_argument("Price cannot be negative.");
    }

    if (discountPercent < 0 || discountPercent > 100) {
        throw invalid_argument(
            "Discount percentage must be between 0 and 100."
        );
    }

    const double discount =
        price * discountPercent / 100.0;

    return price - discount;
}

double roundCurrency(double amount) {
    requireFinite(amount, "Amount");

    // Multiplying by 100 and rounding demonstrates the numeric technique.
    // Real financial systems may require decimal arithmetic rather than
    // binary floating-point representation.
    return std::round(amount * 100.0) / 100.0;
}


// ---------------------------------------------------------------------------
// Compound growth
// ---------------------------------------------------------------------------

double compoundValue(
    double principal,
    double annualRate,
    int periodsPerYear,
    double years
) {
    requireFinite(principal, "Principal");
    requireFinite(annualRate, "Annual rate");
    requireFinite(years, "Years");

    if (principal < 0) {
        throw invalid_argument("Principal cannot be negative.");
    }

    if (periodsPerYear <= 0) {
        throw invalid_argument(
            "Periods per year must be positive."
        );
    }

    if (years < 0) {
        throw invalid_argument("Years cannot be negative.");
    }

    const double periodicRate =
        annualRate / periodsPerYear;

    const double numberOfPeriods =
        periodsPerYear * years;

    return principal *
           std::pow(1.0 + periodicRate, numberOfPeriods);
}


// ---------------------------------------------------------------------------
// Random number generation
// ---------------------------------------------------------------------------

class RandomGenerator {
private:
    std::mt19937 engine;

public:
    explicit RandomGenerator(unsigned int seed)
        : engine(seed) {
    }

    int integer(int minimum, int maximum) {
        if (minimum > maximum) {
            throw invalid_argument(
                "Minimum cannot exceed maximum."
            );
        }

        std::uniform_int_distribution<int> distribution(
            minimum,
            maximum
        );

        return distribution(engine);
    }

    double real(double minimum, double maximum) {
        if (minimum > maximum) {
            throw invalid_argument(
                "Minimum cannot exceed maximum."
            );
        }

        std::uniform_real_distribution<double> distribution(
            minimum,
            maximum
        );

        return distribution(engine);
    }
};


// ---------------------------------------------------------------------------
// Monte Carlo simulation
// ---------------------------------------------------------------------------

double estimatePi(
    RandomGenerator& randomGenerator,
    int numberOfPoints
) {
    if (numberOfPoints <= 0) {
        throw invalid_argument(
            "Number of points must be positive."
        );
    }

    int insideCircle = 0;

    for (int i = 0; i < numberOfPoints; ++i) {
        const double x =
            randomGenerator.real(0.0, 1.0);

        const double y =
            randomGenerator.real(0.0, 1.0);

        const double distanceSquared =
            std::pow(x, 2.0) +
            std::pow(y, 2.0);

        if (distanceSquared <= 1.0) {
            ++insideCircle;
        }
    }

    return 4.0 *
           static_cast<double>(insideCircle) /
           numberOfPoints;
}


// ---------------------------------------------------------------------------
// Inventory reconciliation
// ---------------------------------------------------------------------------

struct Reconciliation {
    int expected;
    int actual;
    int absoluteDifference;
    bool withinTolerance;
};

Reconciliation reconcileInventory(
    int expected,
    int actual,
    int tolerance
) {
    if (expected < 0 || actual < 0) {
        throw invalid_argument(
            "Inventory quantities cannot be negative."
        );
    }

    if (tolerance < 0) {
        throw invalid_argument(
            "Tolerance cannot be negative."
        );
    }

    const int difference =
        std::abs(expected - actual);

    return {
        expected,
        actual,
        difference,
        difference <= tolerance
    };
}


// ---------------------------------------------------------------------------
// Cyclic scheduling
// ---------------------------------------------------------------------------

string nextWarehouseShift(int shiftNumber) {
    static const vector<string> shifts{
        "Morning",
        "Afternoon",
        "Evening",
        "Night"
    };

    const int index =
        normalizeIndex(
            shiftNumber + 1,
            static_cast<int>(shifts.size())
        );

    return shifts[index];
}


// ---------------------------------------------------------------------------
// Performance measurement
// ---------------------------------------------------------------------------

void performanceTest() {
    section("7. Simple performance test");

    constexpr int iterations = 500000;

    volatile long long result = 0;

    auto start = chrono::steady_clock::now();

    for (int i = 0; i < iterations; ++i) {
        result += std::abs(i - 250000);
    }

    auto end = chrono::steady_clock::now();

    const auto absDuration =
        chrono::duration_cast<chrono::microseconds>(
            end - start
        ).count();

    start = chrono::steady_clock::now();

    for (int i = 0; i < iterations; ++i) {
        result += i % 17;
    }

    end = chrono::steady_clock::now();

    const auto moduloDuration =
        chrono::duration_cast<chrono::microseconds>(
            end - start
        ).count();

    cout << "ABS loop: "
         << absDuration
         << " microseconds\n";

    cout << "MOD loop: "
         << moduloDuration
         << " microseconds\n";

    // Prevent aggressive optimization from discarding the loops.
    cout << "Benchmark accumulator: "
         << result << '\n';
}


// ---------------------------------------------------------------------------
// Main case study
// ---------------------------------------------------------------------------

int main() {
    try {
        demonstrateRound();
        demonstrateCeilAndFloor();
        demonstrateAbs();
        demonstrateModulo();
        demonstratePower();

        section("6. Building the warehouse system");

        Warehouse warehouse;

        warehouse.addProduct({
            101,
            "Industrial Sensors",
            157,
            42.75,
            20
        });

        warehouse.addProduct({
            102,
            "Network Modules",
            82,
            129.99,
            12
        });

        warehouse.addProduct({
            103,
            "Control Units",
            205,
            315.50,
            25
        });

        warehouse.addProduct({
            104,
            "Battery Packs",
            47,
            89.95,
            10
        });

        warehouse.printReport();

        section("7. Pricing using ROUND and ABS");

        const double originalPrice = 1299.995;
        const double discountPercent = 12.5;

        const double discountedPrice =
            calculateDiscountedPrice(
                originalPrice,
                discountPercent
            );

        cout << fixed << setprecision(6);

        cout << "Original price: $"
             << originalPrice << '\n';

        cout << "Discounted price before rounding: $"
             << discountedPrice << '\n';

        cout << "Currency-rounded price: $"
             << roundCurrency(discountedPrice)
             << '\n';

        const double expectedPrice = 1137.50;

        cout << "Absolute difference from expected value: $"
             << roundCurrency(
                    std::abs(
                        roundCurrency(discountedPrice) -
                        expectedPrice
                    )
                )
             << '\n';


        section("8. Inventory reconciliation");

        vector<Reconciliation> checks{
            reconcileInventory(100, 98, 3),
            reconcileInventory(250, 257, 5),
            reconcileInventory(500, 492, 5),
            reconcileInventory(75, 75, 0)
        };

        for (const auto& check : checks) {
            cout << "Expected=" << check.expected
                 << ", Actual=" << check.actual
                 << ", Difference=" << check.absoluteDifference
                 << ", Within tolerance="
                 << boolalpha
                 << check.withinTolerance
                 << '\n';
        }


        section("9. Divisibility and modulo");

        for (const auto& product : warehouse.getProducts()) {
            cout << product.name
                 << " quantity=" << product.quantity
                 << ", divisible by 5="
                 << boolalpha
                 << isDivisible(product.quantity, 5)
                 << '\n';
        }


        section("10. Cyclic warehouse shifts");

        for (int shift = -2; shift < 8; ++shift) {
            cout << "Current shift index "
                 << shift
                 << " -> next shift: "
                 << nextWarehouseShift(shift)
                 << '\n';
        }


        section("11. Compound growth using POWER");

        for (double years : {1.0, 5.0, 10.0, 20.0}) {
            const double value =
                compoundValue(
                    100000.0,
                    0.08,
                    12,
                    years
                );

            cout << fixed << setprecision(2)
                 << years
                 << " years -> $"
                 << value
                 << '\n';
        }


        section("12. Random simulation");

        RandomGenerator randomGenerator(2026);

        cout << "Random integers:\n";

        for (int i = 0; i < 5; ++i) {
            cout << randomGenerator.integer(1, 100)
                 << '\n';
        }

        cout << "\nRandom measurements:\n";

        for (int i = 0; i < 5; ++i) {
            const double measurement =
                randomGenerator.real(-10.0, 10.0);

            cout << fixed << setprecision(4)
                 << "value=" << measurement
                 << ", abs=" << std::abs(measurement)
                 << ", square=" << std::pow(measurement, 2.0)
                 << '\n';
        }


        section("13. Monte Carlo pi estimation");

        for (int points : {100, 1000, 10000, 100000}) {
            const double estimate =
                estimatePi(
                    randomGenerator,
                    points
                );

            cout << points
                 << " points -> pi ≈ "
                 << fixed
                 << setprecision(8)
                 << estimate
                 << '\n';
        }


        section("14. Edge cases");

        cout << "ceil(-1.8) = "
             << std::ceil(-1.8)
             << '\n';

        cout << "floor(-1.8) = "
             << std::floor(-1.8)
             << '\n';

        cout << "abs(-42) = "
             << std::abs(-42)
             << '\n';

        cout << "17 % 5 = "
             << (17 % 5)
             << '\n';

        cout << "2^10 = "
             << std::pow(2.0, 10.0)
             << '\n';


        section("15. Error handling");

        try {
            containersRequired(10, 0);
        } catch (const exception& error) {
            cout << "Container error: "
                 << error.what()
                 << '\n';
        }

        try {
            calculateDiscountedPrice(100.0, 150.0);
        } catch (const exception& error) {
            cout << "Pricing error: "
                 << error.what()
                 << '\n';
        }

        try {
            isDivisible(10, 0);
        } catch (const exception& error) {
            cout << "Modulo error: "
                 << error.what()
                 << '\n';
        }


        performanceTest();


        section("16. Assertions and invariants");

        if (containersRequired(101, 10) != 11) {
            throw runtime_error(
                "Container calculation invariant failed."
            );
        }

        if (normalizeIndex(-1, 5) != 4) {
            throw runtime_error(
                "Index normalization invariant failed."
            );
        }

        if (std::abs(-50) != 50) {
            throw runtime_error(
                "Absolute-value invariant failed."
            );
        }

        if (17 % 5 != 2) {
            throw runtime_error(
                "Modulo invariant failed."
            );
        }

        cout << "All validation checks passed.\n";


        section("17. Important implementation rules");

        cout << "1. ROUND changes precision; its exact tie behavior depends "
                "on the rounding function.\n";

        cout << "2. CEIL moves toward positive infinity.\n";
        cout << "3. FLOOR moves toward negative infinity.\n";
        cout << "4. ABS produces magnitude.\n";
        cout << "5. MODULO provides a remainder for integer operands.\n";
        cout << "6. POWER performs exponentiation.\n";
        cout << "7. Random generators should be selected according to the "
                "application's security requirements.\n";
        cout << "8. Floating-point values should not automatically be "
                "assumed to represent decimal values exactly.\n";
        cout << "9. Validate zero divisors and invalid ranges.\n";
        cout << "10. Integer arithmetic can avoid unnecessary floating-point "
                "rounding in some algorithms.\n";

        cout << "\nCase study completed successfully.\n";

    } catch (const exception& error) {
        cerr << "\nFatal error: "
             << error.what()
             << '\n';

        return 1;
    }

    return 0;
}
