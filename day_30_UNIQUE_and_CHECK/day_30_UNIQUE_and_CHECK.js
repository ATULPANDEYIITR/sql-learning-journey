"use strict";

/*
 * UNIQUE and CHECK Constraints
 *
 * This file builds a JavaScript-specific business-rule engine for a product
 * catalog and order system. It models the distinction between:
 *
 *   UNIQUE  -> identity/collision rules
 *   CHECK   -> valid-value rules
 *   business rules -> relationships and policies that may require application
 *                     logic or transactional coordination
 *
 * No external packages are required.
 *
 * Run with:
 *   node unique-check-business-rules.js
 */

const assert = require("node:assert/strict");

class ConstraintViolation extends Error {
  constructor(type, message, details = {}) {
    super(message);
    this.name = "ConstraintViolation";
    this.type = type;
    this.details = details;
  }
}

class UniqueConstraint {
  constructor(name, fields) {
    this.name = name;
    this.fields = fields;
  }

  key(record) {
    return this.fields
      .map((field) => String(record[field]).trim().toLowerCase())
      .join("\u0000");
  }

  validate(records, candidate) {
    const candidateKey = this.key(candidate);

    const conflict = records.find(
      (record) => this.key(record) === candidateKey
    );

    if (conflict) {
      throw new ConstraintViolation(
        "UNIQUE",
        `Unique constraint "${this.name}" was violated.`,
        {
          fields: this.fields,
          conflictingRecordId: conflict.id,
        }
      );
    }
  }
}

class CheckConstraint {
  constructor(name, predicate, description) {
    this.name = name;
    this.predicate = predicate;
    this.description = description;
  }

  validate(record) {
    if (!this.predicate(record)) {
      throw new ConstraintViolation(
        "CHECK",
        `Check constraint "${this.name}" was violated: ${this.description}`,
        {
          constraint: this.name,
          description: this.description,
        }
      );
    }
  }
}

class ProductRepository {
  constructor() {
    this.products = [];

    /*
     * SKU identifies the product globally.
     */
    this.uniqueSku = new UniqueConstraint("ux_products_sku", ["sku"]);

    /*
     * Product names only need to be unique inside a category.
     * This models a composite UNIQUE(category, productName).
     */
    this.uniqueCategoryName = new UniqueConstraint(
      "ux_products_category_name",
      ["category", "productName"]
    );

    this.checks = [
      new CheckConstraint(
        "ck_products_price_non_negative",
        (product) => Number.isFinite(product.price) && product.price >= 0,
        "price must be a finite number greater than or equal to zero"
      ),
      new CheckConstraint(
        "ck_products_stock_non_negative",
        (product) =>
          Number.isInteger(product.stockQuantity) &&
          product.stockQuantity >= 0,
        "stockQuantity must be a non-negative integer"
      ),
      new CheckConstraint(
        "ck_products_discount_range",
        (product) =>
          Number.isFinite(product.discountPercent) &&
          product.discountPercent >= 0 &&
          product.discountPercent <= 100,
        "discountPercent must be between 0 and 100"
      ),
      new CheckConstraint(
        "ck_products_status",
        (product) => ["active", "inactive"].includes(product.status),
        "status must be active or inactive"
      ),
    ];
  }

  insert(product) {
    const normalized = {
      ...product,
      sku: product.sku.trim(),
      category: product.category.trim(),
      productName: product.productName.trim(),
    };

    if (!normalized.sku || !normalized.category || !normalized.productName) {
      throw new ConstraintViolation(
        "CHECK",
        "Required product fields cannot be empty."
      );
    }

    this.uniqueSku.validate(this.products, normalized);
    this.uniqueCategoryName.validate(this.products, normalized);

    for (const check of this.checks) {
      check.validate(normalized);
    }

    this.products.push(Object.freeze({ ...normalized }));
    return normalized;
  }

  findBySku(sku) {
    return this.products.find(
      (product) => product.sku.toLowerCase() === sku.trim().toLowerCase()
    );
  }
}

class ReviewableOrder {
  constructor(id, customerEmail) {
    this.id = id;
    this.customerEmail = customerEmail;
    this.items = [];
    this.status = "draft";
  }

  addItem(product, quantity) {
    /*
     * A JavaScript Set gives us a fast in-memory representation of the
     * composite uniqueness rule (orderId, productId).
     */
    if (!Number.isInteger(quantity) || quantity <= 0) {
      throw new ConstraintViolation(
        "CHECK",
        "Order quantity must be a positive integer."
      );
    }

    if (this.items.some((item) => item.productId === product.id)) {
      throw new ConstraintViolation(
        "UNIQUE",
        "The same product cannot appear twice in one order.",
        {
          fields: ["orderId", "productId"],
        }
      );
    }

    if (quantity > product.stockQuantity) {
      throw new ConstraintViolation(
        "BUSINESS_RULE",
        "Requested quantity exceeds available stock.",
        {
          requested: quantity,
          available: product.stockQuantity,
        }
      );
    }

    this.items.push({
      productId: product.id,
      quantity,
      unitPrice: product.price,
    });
  }

  total() {
    return this.items.reduce(
      (sum, item) => sum + item.quantity * item.unitPrice,
      0
    );
  }

  submit() {
    if (this.items.length === 0) {
      throw new ConstraintViolation(
        "BUSINESS_RULE",
        "An order must contain at least one item before submission."
      );
    }

    this.status = "submitted";
  }
}

class RepositoryPolicy {
  constructor() {
    this.rules = [
      {
        name: "email-identity",
        type: "UNIQUE",
        description: "Customer email addresses must be unique.",
      },
      {
        name: "price-validity",
        type: "CHECK",
        description: "Product prices cannot be negative.",
      },
      {
        name: "stock-validity",
        type: "CHECK",
        description: "Stock quantities cannot be negative.",
      },
      {
        name: "discount-validity",
        type: "CHECK",
        description: "Discount percentage must remain in the inclusive 0-100 range.",
      },
    ];
  }

  evaluateProduct(product, existingProducts) {
    const violations = [];

    const duplicateSku = existingProducts.some(
      (existing) =>
        existing.sku.trim().toLowerCase() === product.sku.trim().toLowerCase()
    );

    if (duplicateSku) {
      violations.push({
        type: "UNIQUE",
        rule: "email-independent product identity",
        message: "SKU already exists.",
      });
    }

    if (!Number.isFinite(product.price) || product.price < 0) {
      violations.push({
        type: "CHECK",
        rule: "price >= 0",
        message: "Price is invalid.",
      });
    }

    if (!Number.isInteger(product.stockQuantity) || product.stockQuantity < 0) {
      violations.push({
        type: "CHECK",
        rule: "stockQuantity >= 0",
        message: "Stock quantity is invalid.",
      });
    }

    if (
      !Number.isFinite(product.discountPercent) ||
      product.discountPercent < 0 ||
      product.discountPercent > 100
    ) {
      violations.push({
        type: "CHECK",
        rule: "0 <= discountPercent <= 100",
        message: "Discount percentage is invalid.",
      });
    }

    return violations;
  }
}

async function eventDrivenLifecycle() {
  console.log("\nEVENT-DRIVEN BUSINESS RULE FLOW");
  console.log("================================");

  /*
   * EventEmitter is intentionally used here instead of a database trigger.
   * It demonstrates how an application can react to validated domain events.
   */
  const { EventEmitter } = require("node:events");
  const events = new EventEmitter();

  events.on("product:accepted", (product) => {
    console.log(`Accepted product ${product.sku}: ${product.productName}`);
  });

  events.on("constraint:violation", (error) => {
    console.log(
      `Rejected ${error.type}: ${error.message}`
    );
  });

  const repository = new ProductRepository();

  const product = {
    id: "P-100",
    sku: "LAP-100",
    category: "Laptop",
    productName: "Engineering Pro",
    price: 125000,
    stockQuantity: 12,
    discountPercent: 5,
    status: "active",
  };

  try {
    repository.insert(product);
    events.emit("product:accepted", product);
  } catch (error) {
    events.emit("constraint:violation", error);
  }

  try {
    repository.insert({
      ...product,
      id: "P-101",
      sku: "LAP-100",
    });
  } catch (error) {
    events.emit("constraint:violation", error);
  }

  try {
    repository.insert({
      ...product,
      id: "P-102",
      sku: "LAP-102",
      price: -10,
    });
  } catch (error) {
    events.emit("constraint:violation", error);
  }

  /*
   * Promise resolution is included to show where an asynchronous database
   * call would normally occur. The rule itself remains deterministic.
   */
  await Promise.resolve();
}

function demonstrateNullableUniqueness() {
  console.log("\nNULL AND UNIQUE SEMANTICS");
  console.log("=========================");

  /*
   * JavaScript Map treats undefined as one key, so it is not a faithful
   * model of SQL's NULL semantics. A database UNIQUE constraint may allow
   * multiple NULL values depending on the database engine.
   *
   * This explicit representation prevents accidental conflation.
   */
  const rows = [
    { id: 1, externalReference: null },
    { id: 2, externalReference: null },
    { id: 3, externalReference: "REF-001" },
  ];

  const nonNullReferences = new Set();

  for (const row of rows) {
    if (row.externalReference !== null) {
      if (nonNullReferences.has(row.externalReference)) {
        throw new ConstraintViolation(
          "UNIQUE",
          "Duplicate non-null external reference."
        );
      }

      nonNullReferences.add(row.externalReference);
    }
  }

  console.log(
    "Two NULL references are retained because the demonstration treats NULL as unknown."
  );
}

function demonstrateAtomicValidation() {
  console.log("\nATOMIC VALIDATION");
  console.log("==================");

  const repository = new ProductRepository();

  const candidateProducts = [
    {
      id: "P-1",
      sku: "CAM-001",
      category: "Camera",
      productName: "Mirrorless",
      price: 75000,
      stockQuantity: 4,
      discountPercent: 8,
      status: "active",
    },
    {
      id: "P-2",
      sku: "CAM-002",
      category: "Camera",
      productName: "Mirrorless",
      price: 90000,
      stockQuantity: 2,
      discountPercent: 5,
      status: "active",
    },
    {
      id: "P-3",
      sku: "CAM-001",
      category: "Lens",
      productName: "Wide Angle",
      price: 45000,
      stockQuantity: 3,
      discountPercent: 0,
      status: "active",
    },
  ];

  for (const candidate of candidateProducts) {
    try {
      repository.insert(candidate);
      console.log(`Committed ${candidate.sku}`);
    } catch (error) {
      console.log(`Rejected ${candidate.sku}: ${error.message}`);
    }
  }

  assert.equal(repository.products.length, 2);
}

async function main() {
  console.log("UNIQUE, CHECK, AND BUSINESS RULE ENGINE");
  console.log("=======================================");

  await eventDrivenLifecycle();
  demonstrateNullableUniqueness();
  demonstrateAtomicValidation();

  console.log("\nORDER BUSINESS RULES");
  console.log("====================");

  const repository = new ProductRepository();

  const phone = repository.insert({
    id: "P-500",
    sku: "PHN-500",
    category: "Phone",
    productName: "Secure Pro",
    price: 80000,
    stockQuantity: 5,
    discountPercent: 10,
    status: "active",
  });

  const order = new ReviewableOrder("ORD-9001", "buyer@example.com");

  order.addItem(phone, 2);

  console.log(`Current order total: ${order.total()}`);

  try {
    order.addItem(phone, 1);
  } catch (error) {
    console.log(`Duplicate order item rejected: ${error.message}`);
  }

  order.submit();
  console.log(`Order state: ${order.status}`);

  console.log("\nPOLICY EVALUATION");
  console.log("=================");

  const policy = new RepositoryPolicy();

  const invalidProduct = {
    sku: "BAD-001",
    price: -100,
    stockQuantity: -4,
    discountPercent: 150,
  };

  console.table(policy.evaluateProduct(invalidProduct, []));

  console.log("\nDESIGN DISTINCTION");
  console.log("==================");
  console.log(
    "UNIQUE answers whether a value or value combination may collide."
  );
  console.log(
    "CHECK answers whether a row's values satisfy an allowed condition."
  );
  console.log(
    "Business rules may span rows, state transitions, inventory, or external systems."
  );
  console.log(
    "Application validation improves feedback, but persistent database constraints remain important for concurrent writes."
  );
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exitCode = 1;
});
