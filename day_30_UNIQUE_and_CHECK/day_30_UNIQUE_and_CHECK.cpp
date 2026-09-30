#include <algorithm>
#include <iomanip>
#include <iostream>
#include <optional>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

/*
 * UNIQUE and CHECK Constraints
 *
 * Case study:
 * A repository-independent order and inventory governance engine.
 *
 * The program models database-style constraints explicitly so the same
 * invariants can be evaluated before a write reaches persistent storage.
 *
 * UNIQUE rules:
 *   - SKU is globally unique.
 *   - Product name is unique inside a category.
 *   - An order may contain a product only once.
 *
 * CHECK rules:
 *   - price >= 0
 *   - stock >= 0
 *   - discount is in [0, 100]
 *   - quantity > 0
 *   - valid product and order states
 *
 * Business rules:
 *   - requested quantity cannot exceed available stock.
 *   - an order cannot be submitted without an item.
 *
 * Compile:
 *   g++ -std=c++17 -Wall -Wextra -pedantic unique_check_business_rules.cpp -o unique_check
 */

enum class ViolationType {
    Unique,
    Check,
    BusinessRule
};

std::string to_string(ViolationType type) {
    switch (type) {
        case ViolationType::Unique:
            return "UNIQUE";
        case ViolationType::Check:
            return "CHECK";
        case ViolationType::BusinessRule:
            return "BUSINESS_RULE";
    }

    return "UNKNOWN";
}

struct Violation {
    ViolationType type;
    std::string rule;
    std::string message;
};

struct Product {
    std::string id;
    std::string sku;
    std::string category;
    std::string name;
    double price{};
    int stock{};
    double discountPercent{};
    std::string status;
};

struct OrderItem {
    std::string productId;
    int quantity{};
    double unitPrice{};
};

enum class OrderStatus {
    Draft,
    Submitted,
    Cancelled
};

std::string to_string(OrderStatus status) {
    switch (status) {
        case OrderStatus::Draft:
            return "draft";
        case OrderStatus::Submitted:
            return "submitted";
        case OrderStatus::Cancelled:
            return "cancelled";
    }

    return "unknown";
}

class ConstraintEngine {
private:
    std::unordered_map<std::string, std::size_t> skuIndex;

    /*
     * A composite key models UNIQUE(category, name).
     * The separator makes the pair unambiguous for the controlled input
     * used by this case study.
     */
    std::unordered_set<std::string> categoryNameKeys;

    static std::string compositeKey(
        const std::string& category,
        const std::string& name
    ) {
        return category + '\x1F' + name;
    }

public:
    std::optional<Violation> validateUnique(
        const Product& product
    ) const {
        if (skuIndex.contains(product.sku)) {
            return Violation{
                ViolationType::Unique,
                "ux_product_sku",
                "SKU already exists: " + product.sku
            };
        }

        const auto key = compositeKey(product.category, product.name);

        if (categoryNameKeys.contains(key)) {
            return Violation{
                ViolationType::Unique,
                "ux_product_category_name",
                "Product name already exists inside category: " +
                    product.category + "/" + product.name
            };
        }

        return std::nullopt;
    }

    std::vector<Violation> validateChecks(
        const Product& product
    ) const {
        std::vector<Violation> violations;

        if (product.price < 0.0) {
            violations.push_back({
                ViolationType::Check,
                "ck_product_price",
                "price must be greater than or equal to zero"
            });
        }

        if (product.stock < 0) {
            violations.push_back({
                ViolationType::Check,
                "ck_product_stock",
                "stock must be greater than or equal to zero"
            });
        }

        if (product.discountPercent < 0.0 ||
            product.discountPercent > 100.0) {
            violations.push_back({
                ViolationType::Check,
                "ck_product_discount",
                "discount must be between 0 and 100"
            });
        }

        if (product.status != "active" &&
            product.status != "inactive") {
            violations.push_back({
                ViolationType::Check,
                "ck_product_status",
                "status must be active or inactive"
            });
        }

        if (product.sku.empty()) {
            violations.push_back({
                ViolationType::Check,
                "ck_product_sku_required",
                "SKU cannot be empty"
            });
        }

        if (product.category.empty()) {
            violations.push_back({
                ViolationType::Check,
                "ck_product_category_required",
                "category cannot be empty"
            });
        }

        if (product.name.empty()) {
            violations.push_back({
                ViolationType::Check,
                "ck_product_name_required",
                "product name cannot be empty"
            });
        }

        return violations;
    }

    void commitProduct(const Product& product) {
        skuIndex.emplace(product.sku, skuIndex.size());
        categoryNameKeys.insert(
            compositeKey(product.category, product.name)
        );
    }
};

class InventoryCatalog {
private:
    ConstraintEngine constraints;
    std::vector<Product> products;

public:
    const std::vector<Product>& allProducts() const {
        return products;
    }

    std::optional<Violation> insertProduct(const Product& product) {
        if (const auto uniqueViolation = constraints.validateUnique(product)) {
            return uniqueViolation;
        }

        const auto checkViolations = constraints.validateChecks(product);

        if (!checkViolations.empty()) {
            return checkViolations.front();
        }

        products.push_back(product);
        constraints.commitProduct(product);
        return std::nullopt;
    }

    Product* findProduct(const std::string& id) {
        auto iterator = std::find_if(
            products.begin(),
            products.end(),
            [&](Product& product) {
                return product.id == id;
            }
        );

        if (iterator == products.end()) {
            return nullptr;
        }

        return &(*iterator);
    }
};

class Order {
private:
    std::string id;
    std::string customerEmail;
    OrderStatus status = OrderStatus::Draft;
    std::vector<OrderItem> items;

public:
    Order(std::string orderId, std::string email)
        : id(std::move(orderId)),
          customerEmail(std::move(email)) {}

    const std::string& getId() const {
        return id;
    }

    OrderStatus getStatus() const {
        return status;
    }

    std::optional<Violation> addItem(
        Product& product,
        int quantity
    ) {
        /*
         * CHECK(quantity > 0)
         */
        if (quantity <= 0) {
            return Violation{
                ViolationType::Check,
                "ck_order_item_quantity",
                "quantity must be greater than zero"
            };
        }

        /*
         * Business rule:
         * Inventory availability depends on another entity. It is not
         * merely a property of the order-item row.
         */
        if (quantity > product.stock) {
            return Violation{
                ViolationType::BusinessRule,
                "inventory_sufficiency",
                "requested quantity exceeds available stock"
            };
        }

        /*
         * UNIQUE(order_id, product_id)
         */
        const bool duplicate = std::any_of(
            items.begin(),
            items.end(),
            [&](const OrderItem& item) {
                return item.productId == product.id;
            }
        );

        if (duplicate) {
            return Violation{
                ViolationType::Unique,
                "ux_order_product",
                "the same product cannot appear twice in one order"
            };
        }

        items.push_back({
            product.id,
            quantity,
            product.price
        });

        return std::nullopt;
    }

    std::optional<Violation> submit() {
        if (items.empty()) {
            return Violation{
                ViolationType::BusinessRule,
                "order_requires_item",
                "an order must contain at least one item"
            };
        }

        status = OrderStatus::Submitted;
        return std::nullopt;
    }

    double total() const {
        double result = 0.0;

        for (const auto& item : items) {
            result += item.quantity * item.unitPrice;
        }

        return result;
    }

    void print() const {
        std::cout << "Order " << id
                  << " | customer=" << customerEmail
                  << " | status=" << to_string(status)
                  << " | total=" << std::fixed
                  << std::setprecision(2)
                  << total() << '\n';

        for (const auto& item : items) {
            std::cout << "  product=" << item.productId
                      << " quantity=" << item.quantity
                      << " unit_price=" << item.unitPrice
                      << '\n';
        }
    }
};

void printViolation(const Violation& violation) {
    std::cout << '[' << to_string(violation.type) << "] "
              << violation.rule << ": "
              << violation.message << '\n';
}

bool insertAndReport(
    InventoryCatalog& catalog,
    const Product& product
) {
    const auto violation = catalog.insertProduct(product);

    if (violation) {
        printViolation(*violation);
        return false;
    }

    std::cout << "Accepted product: "
              << product.sku << " / "
              << product.name << '\n';

    return true;
}

void demonstrateProductConstraints(InventoryCatalog& catalog) {
    std::cout << "\nPRODUCT CONSTRAINTS\n";
    std::cout << "===================\n";

    insertAndReport(
        catalog,
        {
            "P-100",
            "LAP-001",
            "Laptop",
            "Engineering Pro",
            125000.0,
            10,
            5.0,
            "active"
        }
    );

    insertAndReport(
        catalog,
        {
            "P-101",
            "LAP-002",
            "Laptop",
            "Engineering Air",
            95000.0,
            8,
            0.0,
            "active"
        }
    );

    /*
     * Same name and category violates the composite UNIQUE rule.
     */
    insertAndReport(
        catalog,
        {
            "P-102",
            "LAP-003",
            "Laptop",
            "Engineering Pro",
            130000.0,
            5,
            0.0,
            "active"
        }
    );

    /*
     * Same name is legal in another category because the complete
     * uniqueness key is (category, name), not name alone.
     */
    insertAndReport(
        catalog,
        {
            "P-103",
            "Tablet",
            "Tablet",
            "Engineering Pro",
            70000.0,
            12,
            2.0,
            "active"
        }
    );

    /*
     * SKU collision is independent of category.
     */
    insertAndReport(
        catalog,
        {
            "P-104",
            "LAP-001",
            "Accessory",
            "Dock",
            12000.0,
            4,
            0.0,
            "active"
        }
    );

    /*
     * CHECK failure.
     */
    insertAndReport(
        catalog,
        {
            "P-105",
            "MON-001",
            "Monitor",
            "Studio Display",
            -100.0,
            3,
            0.0,
            "active"
        }
    );

    insertAndReport(
        catalog,
        {
            "P-106",
            "MON-002",
            "Monitor",
            "Studio Display 2",
            50000.0,
            -3,
            0.0,
            "active"
        }
    );

    insertAndReport(
        catalog,
        {
            "P-107",
            "MON-003",
            "Monitor",
            "Studio Display 3",
            50000.0,
            3,
            105.0,
            "active"
        }
    );

    insertAndReport(
        catalog,
        {
            "P-108",
            "MON-004",
            "Monitor",
            "Studio Display 4",
            50000.0,
            3,
            5.0,
            "archived"
        }
    );
}

void demonstrateOrderRules(InventoryCatalog& catalog) {
    std::cout << "\nORDER BUSINESS RULES\n";
    std::cout << "====================\n";

    Product* product = catalog.findProduct("P-100");

    if (product == nullptr) {
        std::cout << "Required product was not found.\n";
        return;
    }

    Order order("ORD-5001", "customer@example.com");

    if (const auto violation = order.addItem(*product, 2)) {
        printViolation(*violation);
    } else {
        std::cout << "Added two units to the order.\n";
    }

    /*
     * UNIQUE(order_id, product_id) is enforced before a second item is added.
     */
    if (const auto violation = order.addItem(*product, 1)) {
        printViolation(*violation);
    }

    /*
     * CHECK(quantity > 0)
     */
    if (const auto violation = order.addItem(*product, 0)) {
        printViolation(*violation);
    }

    /*
     * Business rule based on inventory state.
     */
    if (const auto violation = order.addItem(*product, 100)) {
        printViolation(*violation);
    }

    order.print();

    if (const auto violation = order.submit()) {
        printViolation(*violation);
    } else {
        std::cout << "Order submitted.\n";
    }
}

void demonstrateEmptyOrderRule() {
    std::cout << "\nEMPTY ORDER RULE\n";
    std::cout << "================\n";

    Order emptyOrder("ORD-EMPTY", "empty@example.com");

    if (const auto violation = emptyOrder.submit()) {
        printViolation(*violation);
    }
}

void explainProductionBoundary() {
    std::cout << "\nPRODUCTION BOUNDARY\n";
    std::cout << "===================\n";

    std::cout
        << "UNIQUE is appropriate for collision prevention where the database "
        << "can index the relevant column set.\n";

    std::cout
        << "CHECK is appropriate for row-local predicates such as price >= 0 "
        << "or discount between 0 and 100.\n";

    std::cout
        << "Cross-row rules such as inventory availability require coordinated "
        << "transactions or another concurrency-aware mechanism.\n";

    std::cout
        << "Application validation should provide clear feedback, but concurrent "
        << "writers can invalidate a pre-check before the final write. "
        << "The database must remain an enforcement boundary.\n";

    std::cout
        << "Error handling should distinguish duplicate identity conflicts, "
        << "invalid values, and higher-level business-policy violations.\n";
}

int main() {
    std::cout << "UNIQUE, CHECK, AND BUSINESS RULE CASE STUDY\n";
    std::cout << "==========================================\n";

    InventoryCatalog catalog;

    demonstrateProductConstraints(catalog);
    demonstrateOrderRules(catalog);
    demonstrateEmptyOrderRule();
    explainProductionBoundary();

    std::cout << "\nFINAL CATALOG\n";
    std::cout << "=============\n";

    for (const auto& product : catalog.allProducts()) {
        std::cout
            << product.id << " | "
            << product.sku << " | "
            << product.category << " | "
            << product.name << " | price="
            << product.price << " | stock="
            << product.stock << " | discount="
            << product.discountPercent << "%\n";
    }

    return 0;
}
