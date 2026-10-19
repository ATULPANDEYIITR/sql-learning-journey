from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Callable
from collections import Counter
import csv
import io
import json


def heading(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def show(label: str, values: Iterable[str]) -> None:
    print(f"{label}: {sorted(values)}")


def union(left: set[str], right: set[str]) -> set[str]:
    """Return distinct members present in either input set."""
    return left | right


def union_all(left: Iterable[str], right: Iterable[str]) -> list[str]:
    """
    UNION ALL preserves duplicates and therefore cannot be represented
    faithfully by an ordinary Python set.
    """
    return list(left) + list(right)


def intersection(left: set[str], right: set[str]) -> set[str]:
    """Return members present in both sets."""
    return left & right


def difference(left: set[str], right: set[str]) -> set[str]:
    """Return members in left that are absent from right."""
    return left - right


def symmetric_difference(left: set[str], right: set[str]) -> set[str]:
    """Useful for diagnostics, although it is not one of the SQL operators."""
    return left ^ right


def normalize_email(value: str) -> str:
    normalized = value.strip().casefold()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise ValueError(f"Invalid email address: {value!r}")
    return normalized


def distinct_preserving_order(values: Iterable[str]) -> list[str]:
    """Model SQL DISTINCT behavior while retaining first-seen order."""
    return list(dict.fromkeys(values))


@dataclass(frozen=True)
class Customer:
    customer_id: int
    email: str
    segment: str


@dataclass(frozen=True)
class CampaignRecipient:
    campaign: str
    email: str


@dataclass(frozen=True)
class SegmentResult:
    name: str
    emails: frozenset[str]


def demonstrate_basic_set_operations() -> None:
    heading("Basic set operations")

    engineering = {"alice@example.com", "bob@example.com", "carol@example.com"}
    security = {"carol@example.com", "david@example.com", "erin@example.com"}

    show("Engineering UNION Security", engineering | security)
    show("Engineering INTERSECT Security", engineering & security)
    show("Engineering EXCEPT Security", engineering - security)
    show("Security EXCEPT Engineering", security - engineering)
    show("Symmetric difference", engineering ^ security)

    print("\nSet semantics automatically remove duplicates.")
    duplicate_source = ["alice@example.com", "alice@example.com", "bob@example.com"]
    print("Source rows:", duplicate_source)
    print("Distinct set:", sorted(set(duplicate_source)))


def demonstrate_union_all() -> None:
    heading("UNION versus UNION ALL")

    newsletter_a = [
        "alice@example.com",
        "alice@example.com",
        "bob@example.com",
    ]
    newsletter_b = [
        "bob@example.com",
        "carol@example.com",
    ]

    union_result = distinct_preserving_order(newsletter_a + newsletter_b)
    union_all_result = newsletter_a + newsletter_b

    print("First source:", newsletter_a)
    print("Second source:", newsletter_b)
    print("UNION:", union_result)
    print("UNION ALL:", union_all_result)

    counts = Counter(union_all_result)
    print("UNION ALL multiplicities:", dict(sorted(counts.items())))


def demonstrate_relational_compatibility() -> None:
    heading("Relational compatibility")

    active_users = [
        {"email": "alice@example.com", "source": "web"},
        {"email": "bob@example.com", "source": "web"},
    ]

    mobile_users = [
        {"email": "bob@example.com", "source": "mobile"},
        {"email": "carol@example.com", "source": "mobile"},
    ]

    # SQL set operators combine compatible projections. Selecting only email
    # makes the two sources structurally comparable even though their source
    # metadata differs.
    web_emails = {row["email"] for row in active_users}
    mobile_emails = {row["email"] for row in mobile_users}

    show("Web OR mobile", web_emails | mobile_emails)
    show("Web AND mobile", web_emails & mobile_emails)
    show("Web but not mobile", web_emails - mobile_emails)


def demonstrate_customer_campaign_case() -> None:
    heading("Customer campaign audience analysis")

    customers = [
        Customer(101, " Alice@Example.com ", "enterprise"),
        Customer(102, "bob@example.com", "startup"),
        Customer(103, "carol@example.com", "enterprise"),
        Customer(104, "david@example.com", "startup"),
        Customer(105, "erin@example.com", "enterprise"),
        Customer(106, "frank@example.com", "public-sector"),
    ]

    purchases = [
        "alice@example.com",
        "carol@example.com",
        "carol@example.com",
        "frank@example.com",
    ]

    webinar_registrants = [
        "alice@example.com",
        "bob@example.com",
        "erin@example.com",
    ]

    customer_emails = {normalize_email(c.email) for c in customers}
    purchase_emails = {normalize_email(email) for email in purchases}
    webinar_emails = {normalize_email(email) for email in webinar_registrants}

    eligible = customer_emails & webinar_emails
    purchased = customer_emails & purchase_emails
    webinar_without_purchase = webinar_emails - purchase_emails
    purchase_without_webinar = purchase_emails - webinar_emails

    show("Customers", customer_emails)
    show("Webinar registrants", webinar_emails)
    show("Customers who attended webinar", eligible)
    show("Customers who purchased", purchased)
    show("Webinar registrants without purchase", webinar_without_purchase)
    show("Purchasers absent from webinar", purchase_without_webinar)

    enterprise = {
        normalize_email(c.email)
        for c in customers
        if c.segment == "enterprise"
    }

    target_enterprise_followup = eligible & enterprise
    show("Enterprise webinar follow-up", target_enterprise_followup)


def demonstrate_record_level_set_operations() -> None:
    heading("Set operations on composite business records")

    left = {
        ("PROD-100", "analytics"),
        ("PROD-101", "security"),
        ("PROD-102", "cloud"),
    }

    right = {
        ("PROD-101", "security"),
        ("PROD-103", "database"),
    }

    print("Exact row UNION:", sorted(left | right))
    print("Exact row INTERSECT:", sorted(left & right))
    print("Exact row EXCEPT:", sorted(left - right))

    # SQL compares complete projected rows. Changing one attribute means the
    # row is different even when the product identifier matches.
    changed_projection = {
        ("PROD-101", "platform"),
        ("PROD-103", "database"),
    }

    print("Changed projection INTERSECT:", sorted(right & changed_projection))


def demonstrate_sql_like_null_behavior() -> None:
    heading("NULL-related caution")

    print(
        "SQL NULL is not an ordinary value. SQL set operators apply SQL's "
        "duplicate-elimination and row-comparison rules, while Python's "
        "None behaves like a normal hashable object."
    )

    python_left = {None, "alice@example.com"}
    python_right = {None, "bob@example.com"}

    print("Python intersection containing None:", python_left & python_right)
    print(
        "When translating logic to SQL, verify NULL behavior with the target "
        "database rather than assuming Python set semantics are identical."
    )


def demonstrate_set_operations_with_csv() -> None:
    heading("CSV data processing")

    csv_a = """email,source
alice@example.com,crm
bob@example.com,crm
carol@example.com,crm
"""

    csv_b = """email,source
bob@example.com,event
david@example.com,event
"""

    def read_emails(text: str) -> set[str]:
        rows = csv.DictReader(io.StringIO(text))
        result: set[str] = set()

        for row in rows:
            email = normalize_email(row["email"])
            result.add(email)

        return result

    crm = read_emails(csv_a)
    event = read_emails(csv_b)

    show("CRM UNION event", crm | event)
    show("CRM INTERSECT event", crm & event)
    show("CRM EXCEPT event", crm - event)


def demonstrate_advanced_pipeline() -> None:
    heading("Advanced audience reconciliation")

    sources = {
        "crm": SegmentResult(
            "crm",
            frozenset(
                {
                    "alice@example.com",
                    "bob@example.com",
                    "carol@example.com",
                    "david@example.com",
                }
            ),
        ),
        "product_usage": SegmentResult(
            "product_usage",
            frozenset(
                {
                    "bob@example.com",
                    "carol@example.com",
                    "erin@example.com",
                }
            ),
        ),
        "support": SegmentResult(
            "support",
            frozenset(
                {
                    "carol@example.com",
                    "david@example.com",
                    "frank@example.com",
                }
            ),
        ),
    }

    all_known = set().union(*(segment.emails for segment in sources.values()))
    active_in_all = set.intersection(*(set(segment.emails) for segment in sources.values()))
    crm_only = set(sources["crm"].emails) - (
        set(sources["product_usage"].emails)
        | set(sources["support"].emails)
    )

    show("All known customers", all_known)
    show("Present in every source", active_in_all)
    show("CRM-only customers", crm_only)

    source_counts = {
        email: sum(email in segment.emails for segment in sources.values())
        for email in all_known
    }

    print("Source coverage:")
    for email in sorted(source_counts):
        print(f"  {email}: {source_counts[email]} source(s)")

    high_confidence = {
        email for email, count in source_counts.items() if count >= 2
    }

    show("High-confidence multi-source audience", high_confidence)


def demonstrate_validation_and_failures() -> None:
    heading("Validation and failure handling")

    raw_values = [
        "alice@example.com",
        " alice@example.com ",
        "BOB@example.com",
        "",
        "invalid-address",
    ]

    valid: set[str] = set()
    invalid: list[str] = []

    for value in raw_values:
        try:
            valid.add(normalize_email(value))
        except ValueError:
            invalid.append(value)

    show("Validated distinct emails", valid)
    print("Rejected values:", invalid)

    print(
        "\nA common mistake is using UNION semantics when duplicate frequency "
        "matters. Use a list or Counter when multiplicity is part of the "
        "business meaning."
    )


def demonstrate_performance() -> None:
    heading("Performance characteristics")

    left = set(f"user{i}@example.com" for i in range(20_000))
    right = set(f"user{i}@example.com" for i in range(10_000, 30_000))

    print("Left size:", len(left))
    print("Right size:", len(right))
    print("UNION size:", len(left | right))
    print("INTERSECT size:", len(left & right))
    print("EXCEPT size:", len(left - right))

    print(
        "Hash-based Python sets provide expected O(n + m) work for these "
        "binary operations, with memory proportional to the participating "
        "distinct elements."
    )


def demonstrate_audit_report() -> None:
    heading("Audit report")

    crm = {"alice", "bob", "carol", "david"}
    billing = {"bob", "carol", "erin"}
    support = {"carol", "david", "frank"}

    report = {
        "all_accounts": sorted(crm | billing | support),
        "crm_and_billing": sorted(crm & billing),
        "crm_not_billing": sorted(crm - billing),
        "billing_not_crm": sorted(billing - crm),
        "present_everywhere": sorted(crm & billing & support),
        "source_exclusive_accounts": sorted(
            (crm ^ billing) | (billing ^ support) | (crm ^ support)
        ),
    }

    print(json.dumps(report, indent=2))


def main() -> None:
    demonstrate_basic_set_operations()
    demonstrate_union_all()
    demonstrate_relational_compatibility()
    demonstrate_customer_campaign_case()
    demonstrate_record_level_set_operations()
    demonstrate_sql_like_null_behavior()
    demonstrate_set_operations_with_csv()
    demonstrate_advanced_pipeline()
    demonstrate_validation_and_failures()
    demonstrate_performance()
    demonstrate_audit_report()


if __name__ == "__main__":
    main()
