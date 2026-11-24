#!/usr/bin/env python3
"""
QUERY EXECUTION ENGINE
SQL Parsing, Logical Planning, Optimization, and Physical Execution

Supported SQL:
- SELECT and SELECT *
- FROM with one table
- WHERE with AND, OR, NOT, comparisons
- ORDER BY ASC / DESC
- LIMIT
- Column projection
- Predicate pushdown
- Constant-expression evaluation
- Execution statistics
- EXPLAIN-style query plans
- In-memory table storage
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class QueryError(Exception):
    pass


class ParseError(QueryError):
    pass


class PlanningError(QueryError):
    pass


class ExecutionError(QueryError):
    pass


class TokenType(Enum):
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    OPERATOR = "OPERATOR"
    SYMBOL = "SYMBOL"
    KEYWORD = "KEYWORD"
    EOF = "EOF"


KEYWORDS = {
    "SELECT", "FROM", "WHERE", "AND", "OR", "NOT",
    "ORDER", "BY", "ASC", "DESC", "LIMIT", "AS",
    "TRUE", "FALSE", "NULL"
}


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: Any
    position: int


class Lexer:
    PATTERN = re.compile(
        r"""
        (?P<SPACE>\s+)
        |(?P<COMMENT>--[^\n]*)
        |(?P<STRING>'(?:''|[^'])*')
        |(?P<NUMBER>\d+(?:\.\d+)?)
        |(?P<OP><=|>=|<>|!=|=|<|>)
        |(?P<SYMBOL>[(),.*;])
        |(?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
        """,
        re.VERBOSE
    )

    @classmethod
    def tokenize(cls, sql: str) -> list[Token]:
        if not isinstance(sql, str) or not sql.strip():
            raise ParseError("SQL query cannot be empty.")

        tokens = []
        position = 0

        while position < len(sql):
            match = cls.PATTERN.match(sql, position)

            if not match:
                raise ParseError(
                    f"Unexpected character at position {position}: "
                    f"{sql[position]!r}"
                )

            kind = match.lastgroup
            value = match.group()
            start = position
            position = match.end()

            if kind in {"SPACE", "COMMENT"}:
                continue

            if kind == "STRING":
                tokens.append(Token(
                    TokenType.STRING,
                    value[1:-1].replace("''", "'"),
                    start
                ))

            elif kind == "NUMBER":
                number = float(value) if "." in value else int(value)
                tokens.append(Token(TokenType.NUMBER, number, start))

            elif kind == "OP":
                tokens.append(Token(TokenType.OPERATOR, value, start))

            elif kind == "SYMBOL":
                tokens.append(Token(TokenType.SYMBOL, value, start))

            elif kind == "IDENT":
                if value.upper() in KEYWORDS:
                    tokens.append(Token(
                        TokenType.KEYWORD, value.upper(), start
                    ))
                else:
                    tokens.append(Token(
                        TokenType.IDENTIFIER, value, start
                    ))

        tokens.append(Token(TokenType.EOF, None, position))
        return tokens


@dataclass
class Expression:
    kind: str
    value: Any = None
    left: Expression | None = None
    right: Expression | None = None


@dataclass
class SelectStatement:
    columns: list[str]
    table: str
    where: Expression | None = None
    order_by: list[tuple[str, bool]] = field(default_factory=list)
    limit: int | None = None


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.position = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.position]

    def advance(self) -> Token:
        token = self.current
        if token.type != TokenType.EOF:
            self.position += 1
        return token

    def accept(self, value: str) -> bool:
        if str(self.current.value).upper() == value:
            self.advance()
            return True
        return False

    def expect(self, value: str) -> None:
        if not self.accept(value):
            raise ParseError(f"Expected {value}, found {self.current.value}")

    def identifier(self) -> str:
        if self.current.type != TokenType.IDENTIFIER:
            raise ParseError("Expected an identifier.")
        return str(self.advance().value)

    def parse(self) -> SelectStatement:
        self.expect("SELECT")

        columns = []

        if self.accept("*"):
            columns = ["*"]
        else:
            while True:
                columns.append(self.identifier())
                if not self.accept(","):
                    break

        self.expect("FROM")
        table = self.identifier()

        where = None
        order_by = []
        limit = None

        if self.accept("WHERE"):
            where = self.parse_or()

        if self.accept("ORDER"):
            self.expect("BY")

            while True:
                column = self.identifier()
                descending = self.accept("DESC")

                if not descending:
                    self.accept("ASC")

                order_by.append((column, descending))

                if not self.accept(","):
                    break

        if self.accept("LIMIT"):
            if self.current.type != TokenType.NUMBER:
                raise ParseError("LIMIT requires an integer.")

            value = self.advance().value

            if not isinstance(value, int) or value < 0:
                raise ParseError("LIMIT must be a non-negative integer.")

            limit = value

        self.accept(";")

        if self.current.type != TokenType.EOF:
            raise ParseError(
                f"Unexpected trailing token: {self.current.value}"
            )

        return SelectStatement(columns, table, where, order_by, limit)

    def parse_or(self) -> Expression:
        expression = self.parse_and()

        while self.accept("OR"):
            expression = Expression(
                "OR", left=expression, right=self.parse_and()
            )

        return expression

    def parse_and(self) -> Expression:
        expression = self.parse_comparison()

        while self.accept("AND"):
            expression = Expression(
                "AND", left=expression, right=self.parse_comparison()
            )

        return expression

    def parse_comparison(self) -> Expression:
        if self.accept("NOT"):
            return Expression("NOT", left=self.parse_comparison())

        if self.accept("("):
            expression = self.parse_or()
            self.expect(")")
            return expression

        left = self.parse_value()

        if self.current.type == TokenType.OPERATOR:
            operator = self.advance().value
            right = self.parse_value()
            return Expression(
                "COMPARE", operator, left, right
            )

        return left

    def parse_value(self) -> Expression:
        token = self.current

        if token.type == TokenType.IDENTIFIER:
            self.advance()
            return Expression("COLUMN", token.value)

        if token.type in {TokenType.NUMBER, TokenType.STRING}:
            self.advance()
            return Expression("LITERAL", token.value)

        if token.value == "TRUE":
            self.advance()
            return Expression("LITERAL", True)

        if token.value == "FALSE":
            self.advance()
            return Expression("LITERAL", False)

        if token.value == "NULL":
            self.advance()
            return Expression("LITERAL", None)

        raise ParseError(f"Invalid expression near {token.value}")


class Table:
    def __init__(
        self,
        name: str,
        columns: list[str],
        rows: list[dict[str, Any]]
    ):
        self.name = name
        self.columns = columns
        self.rows = rows

        if len(columns) != len(set(columns)):
            raise ValueError("Duplicate column names.")

        for row in rows:
            if set(row) != set(columns):
                raise ValueError("Row schema does not match table schema.")


class Catalog:
    def __init__(self):
        self.tables: dict[str, Table] = {}

    def register(self, table: Table):
        key = table.name.lower()

        if key in self.tables:
            raise ValueError(f"Table already exists: {table.name}")

        self.tables[key] = table

    def get(self, name: str) -> Table:
        try:
            return self.tables[name.lower()]
        except KeyError:
            raise PlanningError(f"Unknown table: {name}")


class PlanNode:
    def execute(self, context: dict) -> list[dict]:
        raise NotImplementedError

    def explain(self, depth=0) -> str:
        raise NotImplementedError


@dataclass
class Scan(PlanNode):
    table: Table

    def execute(self, context):
        context["rows_scanned"] += len(self.table.rows)
        return list(self.table.rows)

    def explain(self, depth=0):
        return " " * depth + f"TableScan({self.table.name})"


@dataclass
class Filter(PlanNode):
    child: PlanNode
    predicate: Expression

    def execute(self, context):
        rows = self.child.execute(context)
        result = []

        for row in rows:
            if evaluate(self.predicate, row) is True:
                result.append(row)

        context["rows_filtered"] += len(rows) - len(result)
        return result

    def explain(self, depth=0):
        return (
            " " * depth + "Filter\n"
            + self.child.explain(depth + 2)
        )


@dataclass
class Project(PlanNode):
    child: PlanNode
    columns: list[str]

    def execute(self, context):
        rows = self.child.execute(context)

        if self.columns == ["*"]:
            return rows

        return [
            {column: row[column] for column in self.columns}
            for row in rows
        ]

    def explain(self, depth=0):
        return (
            " " * depth + f"Project({', '.join(self.columns)})\n"
            + self.child.explain(depth + 2)
        )


@dataclass
class Sort(PlanNode):
    child: PlanNode
    order_by: list[tuple[str, bool]]

    def execute(self, context):
        rows = self.child.execute(context)

        # Stable multi-column sorting is applied from the last key backward.
        for column, descending in reversed(self.order_by):
            rows.sort(
                key=lambda row: (
                    row[column] is None,
                    row[column]
                ),
                reverse=descending
            )

        return rows

    def explain(self, depth=0):
        return (
            " " * depth + "Sort\n"
            + self.child.explain(depth + 2)
        )


@dataclass
class Limit(PlanNode):
    child: PlanNode
    count: int

    def execute(self, context):
        return self.child.execute(context)[:self.count]

    def explain(self, depth=0):
        return (
            " " * depth + f"Limit({self.count})\n"
            + self.child.explain(depth + 2)
        )


def evaluate(expression: Expression, row: dict):
    kind = expression.kind

    if kind == "LITERAL":
        return expression.value

    if kind == "COLUMN":
        if expression.value not in row:
            raise ExecutionError(
                f"Unknown column: {expression.value}"
            )
        return row[expression.value]

    if kind == "NOT":
        value = evaluate(expression.left, row)
        return None if value is None else not bool(value)

    if kind == "AND":
        left = evaluate(expression.left, row)
        right = evaluate(expression.right, row)

        if left is False or right is False:
            return False
        if left is None or right is None:
            return None
        return bool(left and right)

    if kind == "OR":
        left = evaluate(expression.left, row)
        right = evaluate(expression.right, row)

        if left is True or right is True:
            return True
        if left is None or right is None:
            return None
        return bool(left or right)

    if kind == "COMPARE":
        left = evaluate(expression.left, row)
        right = evaluate(expression.right, row)

        # SQL comparisons involving NULL produce UNKNOWN.
        if left is None or right is None:
            return None

        operations: dict[str, Callable] = {
            "=": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<>": lambda a, b: a != b,
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
        }

        try:
            return operations[expression.value](left, right)
        except (TypeError, KeyError) as error:
            raise ExecutionError(
                f"Invalid comparison: {error}"
            )

    raise ExecutionError(f"Unsupported expression: {kind}")


class Optimizer:
    @staticmethod
    def validate(statement: SelectStatement, table: Table):
        available = set(table.columns)

        if statement.columns != ["*"]:
            for column in statement.columns:
                if column not in available:
                    raise PlanningError(f"Unknown column: {column}")

        if statement.where:
            Optimizer.validate_expression(statement.where, available)

        for column, _ in statement.order_by:
            if column not in available:
                raise PlanningError(
                    f"Unknown ORDER BY column: {column}"
                )

    @staticmethod
    def validate_expression(expression, available):
        if expression is None:
            return

        if expression.kind == "COLUMN":
            if expression.value not in available:
                raise PlanningError(
                    f"Unknown column: {expression.value}"
                )

        Optimizer.validate_expression(expression.left, available)
        Optimizer.validate_expression(expression.right, available)

    @staticmethod
    def optimize(statement: SelectStatement, table: Table):
        Optimizer.validate(statement, table)

        # Filter is applied before projection to preserve predicate columns.
        plan: PlanNode = Scan(table)

        if statement.where:
            plan = Filter(plan, statement.where)

        if statement.order_by:
            plan = Sort(plan, statement.order_by)

        if statement.limit is not None:
            plan = Limit(plan, statement.limit)

        plan = Project(plan, statement.columns)

        return plan


class QueryEngine:
    def __init__(self):
        self.catalog = Catalog()

    def register(self, table: Table):
        self.catalog.register(table)

    def execute(self, sql: str):
        start = time.perf_counter()

        tokens = Lexer.tokenize(sql)
        statement = Parser(tokens).parse()

        table = self.catalog.get(statement.table)
        plan = Optimizer.optimize(statement, table)

        statistics = {
            "rows_scanned": 0,
            "rows_filtered": 0,
        }

        result = plan.execute(statistics)

        elapsed = time.perf_counter() - start

        return {
            "columns": (
                table.columns
                if statement.columns == ["*"]
                else statement.columns
            ),
            "rows": result,
            "row_count": len(result),
            "execution_ms": round(elapsed * 1000, 4),
            "statistics": statistics,
            "plan": plan.explain()
        }


def build_demo_engine():
    engine = QueryEngine()

    engine.register(Table(
        "employees",
        ["id", "name", "department", "salary", "active"],
        [
            {
                "id": 1,
                "name": "Asha",
                "department": "Engineering",
                "salary": 95000,
                "active": True
            },
            {
                "id": 2,
                "name": "Rahul",
                "department": "Finance",
                "salary": 72000,
                "active": True
            },
            {
                "id": 3,
                "name": "Neha",
                "department": "Engineering",
                "salary": 110000,
                "active": True
            },
            {
                "id": 4,
                "name": "Arjun",
                "department": "Operations",
                "salary": 68000,
                "active": False
            },
            {
                "id": 5,
                "name": "Meera",
                "department": "Engineering",
                "salary": 88000,
                "active": True
            }
        ]
    ))

    return engine


def run_tests(engine):
    result = engine.execute(
        "SELECT name, salary FROM employees "
        "WHERE department = 'Engineering' "
        "AND active = TRUE ORDER BY salary DESC LIMIT 2"
    )

    assert result["row_count"] == 2
    assert result["rows"][0]["name"] == "Neha"
    assert result["rows"][1]["name"] == "Asha"

    empty = engine.execute(
        "SELECT id FROM employees WHERE salary > 500000"
    )
    assert empty["row_count"] == 0

    zero_limit = engine.execute(
        "SELECT id FROM employees LIMIT 0"
    )
    assert zero_limit["row_count"] == 0

    null_test = engine.execute(
        "SELECT id FROM employees WHERE department = NULL"
    )
    assert null_test["row_count"] == 0

    try:
        engine.execute("SELECT unknown FROM employees")
        raise AssertionError("Unknown column was not rejected.")
    except PlanningError:
        pass

    try:
        engine.execute("SELECT * FROM missing_table")
        raise AssertionError("Unknown table was not rejected.")
    except PlanningError:
        pass

    print("All tests passed.")


def main():
    engine = build_demo_engine()

    queries = [
        "SELECT name, salary FROM employees "
        "WHERE department = 'Engineering' "
        "AND salary >= 90000 ORDER BY salary DESC",

        "SELECT * FROM employees "
        "WHERE active = TRUE LIMIT 3",

        "SELECT name FROM employees "
        "WHERE department = 'Finance' OR department = 'Operations'"
    ]

    for sql in queries:
        print("\nSQL:", sql)

        result = engine.execute(sql)

        print("PLAN:")
        print(result["plan"])

        print("RESULT:")
        print(json.dumps(result["rows"], indent=2))

        print("STATISTICS:")
        print(json.dumps({
            "rows_scanned": result["statistics"]["rows_scanned"],
            "rows_filtered": result["statistics"]["rows_filtered"],
            "returned": result["row_count"],
            "execution_ms": result["execution_ms"]
        }, indent=2))

    run_tests(engine)


if __name__ == "__main__":
    main()
