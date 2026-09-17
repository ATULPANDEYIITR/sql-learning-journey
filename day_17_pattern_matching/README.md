# Pattern Matching: LIKE, ILIKE, Wildcards, Regex Basics, and Pattern-Based Filtering

## Topic overview

Pattern matching is the process of determining whether text conforms to a specified pattern. It is used in database queries, search interfaces, validation systems, log processing, data cleaning, routing rules, file-name filtering, security controls, and application-level text processing.

This study focuses on two major pattern languages:

- SQL-style wildcard matching with `LIKE` and `ILIKE`
- Regular expressions, commonly abbreviated as regex

The three implementations use the same conceptual domain while emphasizing different technical aspects:

- Python provides a broad educational implementation, including a direct implementation of SQL-style matching, regular expressions, extraction, validation, dynamic programming, security considerations, and reusable abstractions.
- JavaScript demonstrates pattern matching in application and web-oriented environments, including `RegExp`, string APIs, functional filtering, reusable classes, and event-loop-friendly processing.
- C++ develops an industry-style searchable-record case study with structured data, validation, query processing, dynamic-programming wildcard matching, regular-expression matching, error handling, and performance measurement.

---

## Fundamental concept

A literal string comparison asks whether two values are exactly equal.

For example, an exact comparison between `Alice` and `Alice` succeeds, while a comparison between `Alice` and `alice` may fail when matching is case-sensitive.

Pattern matching introduces a language for describing a set of possible strings.

A pattern such as `A%` does not describe one specific string. It describes strings that begin with `A` and may contain any number of characters after it.

This distinction is important:

- Exact comparison identifies one exact value.
- Wildcard matching describes a constrained family of values.
- Regular expressions describe much more complex sets of strings.

---

## SQL `LIKE`

`LIKE` is a SQL predicate used for pattern-based string comparison.

The two fundamental SQL `LIKE` wildcards are:

| Wildcard | Meaning |
| --- | --- |
| `%` | Zero or more characters |
| `_` | Exactly one character |

For example:

`name LIKE 'A%'`

matches names beginning with `A`.

`name LIKE '%son'`

matches values ending with `son`.

`name LIKE '%data%'`

matches values containing `data`.

`code LIKE 'AB__'`

requires `AB` followed by exactly two characters.

The pattern normally describes the complete value. This means the placement of `%` determines whether the search is a prefix, suffix, substring, or more restrictive pattern.

---

## The `%` wildcard

The percent wildcard matches zero or more characters.

Examples:

| Value | Pattern | Result |
| --- | --- | --- |
| `cat` | `c%` | Match |
| `catalog` | `c%` | Match |
| `c` | `c%` | Match |
| `cat` | `%cat%` | Match |
| `cat` | `%` | Match |
| empty string | `%` | Match |

The ability of `%` to match zero characters is important. A pattern such as `A%` can therefore match `A` itself.

---

## The `_` wildcard

The underscore wildcard matches exactly one character.

Examples:

| Value | Pattern | Result |
| --- | --- | --- |
| `cat` | `c_t` | Match |
| `cot` | `c_t` | Match |
| `coat` | `c_t` | No match |
| `ct` | `c_t` | No match |
| `AB12` | `AB__` | Match |

The difference between `%` and `_` is fundamental:

- `%` can consume zero, one, or many characters.
- `_` consumes exactly one character.

---

## `ILIKE`

`ILIKE` is a case-insensitive pattern-matching operator associated particularly with PostgreSQL.

For example:

`name ILIKE 'atul%'`

can match:

- `Atul`
- `atul`
- `ATUL`
- `Atul Pandey`

The exact case-sensitivity behavior of SQL pattern matching depends on the database system, collation, locale, data type, and configuration.

`ILIKE` should therefore not be assumed to be a portable SQL feature with identical behavior across all database systems.

The Python, JavaScript, and C++ implementations explicitly provide an ILIKE-style operation by performing case-insensitive matching.

---

## Escaping wildcard characters

Sometimes `%` or `_` is actual data rather than a wildcard.

For example, suppose the stored value is:

`100%`

A search pattern must distinguish the literal percent sign from the `%` wildcard.

SQL supports an escape mechanism for this purpose. A conceptual example is:

`LIKE '100\%' ESCAPE '\'`

The escape character tells the pattern processor that the following wildcard character should be interpreted literally.

The implementations demonstrate this concept explicitly rather than treating every `%` and `_` as a wildcard in every situation.

---

## LIKE versus regular expressions

`LIKE` provides a small pattern language.

Regular expressions provide a much larger language.

A simplified comparison is:

| Capability | `LIKE` | Regex |
| --- | --- | --- |
| Exact characters | Yes | Yes |
| `%`-style repetition | Yes | Usually represented by `.*` |
| Single-character wildcard | `_` | `.` |
| Character classes | No | Yes |
| Quantifier ranges | No | Yes |
| Alternation | No | Yes |
| Capturing groups | No | Yes |
| Lookahead | No | Yes |
| Lookbehind | No | Yes |
| Extraction | Limited | Strong |
| Replacement | Limited | Strong |
| Complexity | Low | Higher |

For a simple database prefix search, `LIKE` can express the requirement directly.

A regex becomes useful when the pattern contains requirements such as:

- one of several alternatives
- a particular character class
- a numeric range structure
- optional sections
- repeated groups
- boundaries
- extraction of structured information

---

## Regular-expression fundamentals

A regular expression is a pattern language for describing text.

Common constructs include:

| Regex | Meaning |
| --- | --- |
| `.` | Any character in many regex modes |
| `\d` | Digit |
| `\w` | Word character |
| `\s` | Whitespace |
| `[abc]` | One character from `a`, `b`, or `c` |
| `[a-z]` | One character in the specified range |
| `[^0-9]` | One character not in the specified class |
| `*` | Zero or more |
| `+` | One or more |
| `?` | Zero or one |
| `{3}` | Exactly three |
| `{2,4}` | Two through four |
| `{2,}` | Two or more |
| `^` | Beginning anchor |
| `$` | End anchor |
| `\b` | Word boundary |
| `|` | Alternation |
| `(...)` | Capturing group |

The precise meaning of some constructs depends on the regex engine.

---

## Anchors

Anchors constrain where a match can occur.

`^Python`

requires the relevant match to begin at the start of the input.

`Python$`

requires the relevant match to finish at the end.

`^Python$`

requires the complete input to be exactly `Python` in engines where the expression is applied to the complete string as intended.

This distinction matters in validation.

A search expression that finds `Python` somewhere in a string is not equivalent to an expression that validates the complete string as `Python`.

---

## Search versus full validation

The Python implementation explicitly demonstrates the distinction between:

- `re.search()`
- `re.match()`
- `re.fullmatch()`

The JavaScript implementation demonstrates related behavior through `RegExp.test()`, `match()`, `search()`, and anchored expressions.

For validation, complete-input semantics are usually important.

For example, a six-digit postal code can be described by:

`^\d{6}$`

rather than merely searching for six digits somewhere in a larger value.

---

## Character classes

Character classes allow a regex to describe a set of permitted characters.

Examples include:

`[abc]`

which matches one of `a`, `b`, or `c`.

`[A-Z]`

which matches an uppercase ASCII letter.

`[0-9]`

which matches an ASCII digit.

`[^0-9]`

which matches a character outside the specified digit class.

Character classes are useful for validation, parsing, identifiers, codes, and structured text.

---

## Quantifiers

Quantifiers describe repetition.

`a*` means zero or more `a` characters.

`a+` means one or more.

`a?` means zero or one.

`a{3}` means exactly three.

`a{2,4}` means between two and four.

`a{2,}` means at least two.

Quantifiers are one of the main reasons regex can express patterns that cannot be expressed conveniently with SQL `LIKE`.

---

## Greedy and lazy matching

Many regex quantifiers are greedy by default.

A greedy expression attempts to consume as much input as possible while still allowing the complete expression to succeed.

A lazy or non-greedy quantifier generally attempts to consume as little as possible.

The Python and JavaScript implementations demonstrate the difference using a simple tag-like string.

This distinction is especially important when processing structured text because an overly greedy expression can consume multiple logical records when only one was intended.

---

## Groups and extraction

Parentheses create groups.

Named groups make extracted fields easier to interpret.

The Python implementation parses a structured log line into:

- date
- time
- severity
- user
- request
- status

The JavaScript implementation demonstrates named groups using JavaScript's named capture syntax.

Regex is therefore not limited to returning `true` or `false`. It can also extract structured information from unstructured text.

---

## Lookahead and lookbehind

Lookaround allows a regex to require surrounding conditions without consuming the surrounding text as part of the main match.

Positive lookahead uses a structure such as:

`(?=...)`

Positive lookbehind uses a structure such as:

`(?<=...)`

The implementations demonstrate both concepts.

Lookaround can be useful for complex validation and extraction, but it increases pattern complexity and can reduce readability.

---

## Validation

Regex is frequently used for application-level validation.

The implementations demonstrate validation of:

- email-like strings
- six-digit numeric codes
- hexadecimal color values
- structured identifiers
- password-like requirements

Regex validation should be treated as application-specific rather than automatically equivalent to a formal standard.

For example, email syntax is substantially more complicated than a short educational regex. A production application must define what address forms it actually supports and should avoid assuming that a simple regex implements the complete email standard.

---

## Python implementation

The Python script develops the topic from basic string matching to advanced pattern processing.

### Basic matching

The script begins with:

- exact equality
- substring checks
- prefix checks
- suffix checks

These operations establish the difference between ordinary string operations and pattern languages.

### SQL LIKE translation

The function `sql_like_to_regex()` converts:

- `%` into `.*`
- `_` into `.`
- ordinary characters into escaped regex literals

Anchors are added so that the resulting regex represents complete-string LIKE semantics.

The implementation uses `re.escape()` for ordinary pattern characters. This prevents regex metacharacters from accidentally acquiring regex semantics when they should be literal characters in the LIKE language.

### Direct LIKE algorithm

The Python script also implements wildcard matching with dynamic programming.

The state:

`dp[i][j]`

represents whether the first `i` characters of the text match the first `j` characters of the pattern.

For `%`, two transitions are possible:

- `%` matches nothing
- `%` consumes one text character and remains active

The resulting complexity is:

- Time: `O(nm)`
- Space: `O(nm)`

where `n` is text length and `m` is pattern length.

This direct implementation is educational because it exposes the matching mechanism without relying on regex translation.

### Regular expressions

The Python implementation covers:

- compiled regex patterns
- `search`
- `match`
- `fullmatch`
- `findall`
- `finditer`
- capturing groups
- named groups
- replacement
- character classes
- quantifiers
- anchors
- lookaround
- greedy and non-greedy matching

### Reusable matcher

The `PatternMatcher` class provides reusable methods for:

- `like`
- `ilike`
- `regex`

It also caches translated LIKE regex objects.

Caching is useful when the same patterns are repeatedly applied because compilation work does not need to be repeated for every value.

---

## JavaScript implementation

JavaScript provides native regular-expression support through `RegExp` and regex literals.

The JavaScript implementation focuses on application-side processing.

### String operations

JavaScript provides methods such as:

- `includes()`
- `startsWith()`
- `endsWith()`
- equality with `===`

These are useful when no pattern language is required.

### LIKE implementation

JavaScript has no native SQL `LIKE` string method.

The implementation therefore translates SQL-style patterns into regular expressions.

The translation preserves the conceptual meaning:

- `%` becomes `.*`
- `_` becomes `.`
- other characters are escaped

An `s` flag is used so that the translated `.` can include line terminators when the implementation is treating the LIKE operation as a general character sequence.

### ILIKE implementation

The JavaScript implementation provides ILIKE-style behavior using the regex `i` flag.

This demonstrates an important distinction between a database operator and a language-level implementation: the application is reproducing a database-style semantic rather than invoking an actual SQL operator.

### Functional filtering

JavaScript's `Array.prototype.filter()` makes pattern-based collection processing concise.

For example, records can be filtered by:

- name
- email
- city
- department

The result is a new array rather than a modification of the original collection.

### Event-driven processing

The asynchronous chunked filter demonstrates a client-side performance technique.

Large datasets can be divided into chunks, with control returned to the event loop between chunks.

This does not reduce the mathematical cost of matching. It can improve responsiveness in an application where a long synchronous operation would otherwise block the event loop.

---

## C++ case study

The C++ implementation models a searchable contact and incident-record system.

Each record contains:

- ID
- name
- email
- city
- department
- status
- priority

The system validates records before making them available to the search engine.

### Search engine architecture

The `SearchEngine` class provides:

- LIKE search
- ILIKE-style search
- regex search
- priority filtering
- combined pattern and priority filtering

The implementation separates domain data from matching logic.

This is important in production systems because the pattern engine should not be tightly coupled to one particular user interface.

### LIKE algorithm

The C++ `LikeMatcher` uses dynamic programming rather than converting LIKE patterns into regular expressions.

The implementation has the same core state relationship as the Python algorithm.

For a `%`:

`dp[i][j] = dp[i][j-1] || dp[i-1][j]`

The first term means that `%` matches zero characters.

The second means that `%` consumes one additional character.

For `_`, the current character is consumed exactly once.

For an ordinary character, the text character must equal the pattern character.

### Regular expressions

C++17 provides `std::regex`.

The `RegexMatcher` class exposes:

- search semantics through `regex_search`
- complete matching through `regex_match`

Invalid expressions are converted into application-level exceptions.

This demonstrates why validation and exception handling are important when patterns may come from outside the program.

---

## Data validation

The C++ case study validates:

- positive IDs
- non-empty names
- email-like values
- supported status values
- priority range

The system rejects invalid records before search processing.

This separation prevents pattern matching from becoming responsible for unrelated domain validation.

---

## Query validation

The C++ program also validates search requests.

The example limits pattern length to 256 characters.

A pattern-length limit is a practical security and resource-control measure when arbitrary patterns may originate from users.

An application may use different limits depending on its workload and requirements.

---

## Error handling

The C++ program explicitly handles:

- unknown search fields
- invalid regular expressions
- oversized patterns
- invalid domain records

Exceptions are caught at the application boundary.

This prevents a malformed pattern from silently producing incorrect results.

---

## Empty strings and NULL

An empty string and SQL `NULL` are different concepts.

An empty string is an actual string containing zero characters.

`NULL` represents an absent or unknown value in SQL's three-valued logic.

For example, SQL does not normally treat:

`NULL LIKE 'A%'`

as an ordinary false comparison. The result participates in SQL's `UNKNOWN` semantics.

Applications should explicitly consider:

- empty strings
- missing values
- `NULL`
- whitespace-only values

The Python and JavaScript demonstrations show how application languages represent missing values differently from SQL.

---

## Case sensitivity

Case sensitivity is not universally defined by the word `LIKE` alone.

Factors include:

- database engine
- collation
- locale
- data type
- operator
- database configuration

PostgreSQL provides `ILIKE` for case-insensitive pattern matching.

The C++ implementation performs simple lowercase normalization for its educational ILIKE behavior.

This is not a complete Unicode case-folding implementation. Production internationalized systems may require Unicode-aware normalization and locale-specific handling.

The same caution applies to simple ASCII-oriented regex validation.

---

## SQL dialect differences

Pattern-matching features differ among database systems.

PostgreSQL provides:

- `LIKE`
- `ILIKE`
- regular-expression operators such as `~` and `~*`

Other database systems use different names or provide regex functionality through functions.

Examples include database-specific constructs such as `REGEXP`, `REGEXP_LIKE`, or other regular-expression functions.

The exact syntax, regex engine, case behavior, escaping rules, and indexing capabilities should therefore be evaluated for the target DBMS rather than assumed to be portable.

---

## Pattern-based filtering

Pattern filtering can be represented conceptually as:

`filter(rows, predicate)`

The predicate evaluates a field against a pattern.

Examples include:

`name LIKE 'A%'`

`email LIKE '%@company.com'`

`city ILIKE '%del%'`

`name` matching a regex such as `^[A-Z][a-z]+$`

Pattern-based filtering is common in:

- contact search
- product search
- administrative dashboards
- log investigation
- customer support systems
- record management
- validation pipelines
- data-quality workflows

---

## Prefix, suffix, and substring searches

These three forms have different performance implications.

### Prefix search

`name LIKE 'Ali%'`

The beginning of the string is fixed.

Depending on the database and index configuration, this type of query may be able to use an index efficiently.

### Suffix search

`name LIKE '%son'`

The beginning of the value is unknown.

An ordinary B-tree index may not provide the same benefit as it can for a fixed prefix.

### Substring search

`name LIKE '%ali%'`

The search term can occur anywhere.

This often requires examining many candidate values unless the database has an appropriate specialized index or search mechanism.

---

## Performance considerations

Pattern matching has both algorithmic and database-level performance characteristics.

For the direct dynamic-programming LIKE matcher:

- Time complexity: `O(nm)`
- Space complexity: `O(nm)`

where `n` is text length and `m` is pattern length.

The space requirement can be reduced with a rolling dynamic-programming array when only the previous row is required.

Regular-expression performance depends heavily on the regex engine and pattern structure.

Repeated regex compilation can add unnecessary overhead. The Python and JavaScript implementations therefore demonstrate reusable compiled patterns.

For database workloads, performance depends on:

- number of rows
- column cardinality
- pattern structure
- indexes
- collation
- query planner
- statistics
- database engine
- specialized search indexes

A simple pattern over a small table and the same pattern over hundreds of millions of rows are fundamentally different performance problems.

---

## Regex backtracking and resource consumption

Some regex engines use backtracking algorithms.

Certain combinations of nested or overlapping quantifiers can cause extremely expensive matching behavior.

A classic risk pattern contains nested repetition where many alternative match paths are possible.

This class of problem is commonly discussed as regular-expression denial of service, or ReDoS.

Applications accepting arbitrary regex patterns should consider:

- pattern length limits
- execution limits
- timeouts where supported
- restricted pattern languages
- safer regex engines
- rejecting unnecessarily complex expressions

A controlled application-defined pattern language can sometimes be safer than allowing arbitrary user-defined regex.

---

## Security considerations

Pattern matching intersects with security in several ways.

### SQL injection

Pattern values should not be concatenated directly into SQL statements.

Unsafe conceptual construction:

`SELECT * FROM users WHERE name LIKE 'USER_INPUT';`

A production application should use parameterized queries through its database driver.

The database should receive the SQL statement separately from the pattern value.

### LIKE wildcard abuse

Even when SQL injection is prevented, a user can intentionally or accidentally submit broad patterns such as:

`%`

or:

`%term%`

Such patterns can produce large result sets and expensive scans.

Applications can impose:

- maximum result sizes
- maximum pattern lengths
- search time limits
- rate limits
- controlled search syntax

### Regex abuse

Arbitrary regex input may create CPU-intensive operations.

Regex patterns should be treated as executable pattern logic rather than harmless text.

---

## Common mistakes

### Using equality for wildcard searches

`name = 'A%'`

does not mean the same thing as:

`name LIKE 'A%'`

The equality operator treats `%` as ordinary data.

### Confusing `%` and `_`

`%` represents zero or more characters.

`_` represents one character.

### Mixing LIKE and regex syntax

A pattern such as:

`[A-Z]+`

has regex meaning but is not an ordinary SQL `LIKE` pattern.

A `LIKE` expression should use its own wildcard language.

### Forgetting case sensitivity

A query that works for `Alice` may not work for `alice`.

Case behavior must be intentional.

### Forgetting escaping

Literal `%` and `_` may need to be escaped when they are actual data.

### Using search semantics for validation

Searching for a valid fragment is not the same as validating the complete input.

Anchors or complete-match APIs are important when the entire value must satisfy the pattern.

### Compiling regex repeatedly

If the same regex is applied to thousands or millions of values, repeated compilation can be wasteful.

Compiled or reusable expressions are preferable where the language and workload support them.

### Ignoring Unicode

ASCII-oriented expressions do not automatically provide correct internationalized behavior.

Unicode introduces considerations involving:

- case folding
- normalization
- grapheme clusters
- locale-sensitive behavior
- character categories

---

## Important distinction: database pattern matching versus application matching

A database query such as:

`WHERE name LIKE 'A%'`

operates inside a database execution environment.

A Python expression such as:

`sql_like(name, "A%")`

operates in application memory.

The semantics can be made similar, but their performance characteristics are different.

A database can use:

- indexes
- query planners
- statistics
- storage-level optimizations
- specialized search structures

An application-level filter normally examines the records that have already been loaded into the application.

Therefore, moving a database filter into application code can create unnecessary data transfer and memory consumption.

---

## When LIKE is appropriate

LIKE is useful when the requirement is simple.

Examples:

- starts with a prefix
- ends with a suffix
- contains a substring
- follows a fixed character layout

Typical patterns include:

`A%`

`%example.com`

`%database%`

`AB__`

Its simple syntax is often easier to understand and maintain than an equivalent regex.

---

## When regex is appropriate

Regex is useful when requirements exceed LIKE's wildcard model.

Examples include:

- multiple alternatives
- character classes
- structured extraction
- optional components
- numeric formatting
- validation rules
- repeated groups
- word boundaries
- lookaround

Regex should not automatically replace LIKE. Greater expressive power also means greater complexity.

---

## Pattern languages and abstraction

A useful engineering approach is to treat a pattern language as a formal interface.

The application should know:

1. Which pattern language is accepted.
2. Which operators are supported.
3. Whether matching is case-sensitive.
4. Whether patterns apply to complete values or substrings.
5. How wildcard characters are escaped.
6. What length and complexity limits exist.
7. What happens for malformed patterns.
8. How missing values are handled.
9. What performance characteristics are expected.

This prevents users and developers from accidentally mixing SQL syntax, regex syntax, and ordinary string operations.

---

## Practical architecture

A production search system can be separated into several layers:

### Input layer

Receives the user's search expression.

### Validation layer

Checks:

- length
- allowed syntax
- field name
- supported operators
- resource limits

### Pattern layer

Converts or compiles the expression into the selected matching representation.

### Data-access layer

Uses parameterized database operations.

### Optimization layer

Chooses indexes or specialized search structures where appropriate.

### Result layer

Applies pagination, limits, sorting, and authorization.

This separation keeps search semantics distinct from database access and application presentation.

---

## Implementation comparison

| Aspect | Python | JavaScript | C++ |
| --- | --- | --- | --- |
| LIKE implementation | Translation and DP | Translation and DP | Direct DP |
| Regex | `re` | `RegExp` | `std::regex` |
| Filtering | Iterables and comprehensions | Array filtering | Explicit loops and classes |
| Validation | Functions and compiled regex | RegExp | `std::regex` |
| Abstraction | `PatternMatcher` | `PatternMatcher` | `SearchEngine` |
| Error handling | Exceptions | Exceptions and rejected promises | Exceptions |
| Async demonstration | Not required | Event-loop chunking | Not central |
| Performance example | Timing | `performance.now()` | `chrono` |
| Case-insensitive mode | `re.IGNORECASE` | `i` flag | lowercase normalization |
| Main emphasis | Language and algorithms | Application-side behavior | Systems-style design |

---

## Why the three implementations differ

Python is particularly useful for exposing algorithms and language-level abstractions concisely. The Python script therefore contains several independent implementations of wildcard matching and a broad exploration of regex APIs.

JavaScript is useful for demonstrating pattern processing in application environments where strings, arrays, regular expressions, and event-loop behavior are central. The JavaScript implementation therefore emphasizes `RegExp`, functional filtering, and chunked asynchronous processing.

C++ provides stronger control over implementation structure and makes algorithmic and systems-level concerns explicit. The C++ program therefore models a searchable record system with classes, validation, exceptions, data structures, complexity analysis, and performance measurement.

---

## Real-world applications

Pattern matching is used in:

### Database search

Users often search for names, emails, product codes, addresses, or descriptions using prefix and substring patterns.

### Data validation

Regex can validate structured identifiers, codes, dates, and other application-defined formats.

### Log analysis

Structured log lines can be searched and parsed using regex groups.

### Data cleaning

Pattern matching can identify malformed records, inconsistent formats, or unexpected characters.

### Security operations

Pattern matching can identify suspicious strings, log events, indicators, and structured artifacts.

### File filtering

Wildcard patterns are widely used for file names and paths.

### Search interfaces

Applications can provide simple wildcard syntax or more advanced regex-based filtering.

---

## Limitations

Pattern matching is not equivalent to semantic search.

A substring search does not understand:

- synonyms
- meaning
- grammar
- context
- intent
- spelling similarity

For example, a substring search for `car` does not inherently understand that `automobile` has a related meaning.

LIKE is also not a replacement for full-text search when the application requires linguistic processing, ranking, tokenization, stemming, or relevance scoring.

---

## Full-text search versus pattern matching

Pattern matching asks whether a value satisfies a defined character-level pattern.

Full-text search usually operates at a higher level.

Pattern matching is suitable when exact character relationships matter.

Full-text search is more appropriate when the system needs concepts such as:

- tokenization
- relevance ranking
- linguistic normalization
- stemming
- phrase searching
- document-oriented indexing

The appropriate technology depends on the actual search requirement.

---

## Testing strategy

Pattern-matching implementations should test at least:

- empty text
- empty pattern
- exact matches
- complete mismatches
- prefix patterns
- suffix patterns
- substring patterns
- `%`
- `_`
- multiple wildcards
- consecutive `%` characters
- escaped wildcard characters
- case differences
- malformed regex
- very long inputs
- Unicode data where supported
- missing values
- boundary conditions

The Python, JavaScript, and C++ implementations include explicit edge cases and assertions or failure handling.

---

## Design principles demonstrated by the implementations

### Keep pattern languages separate

SQL `LIKE` and regex are different languages.

### Define complete-match semantics

Know whether a pattern should match the complete value or merely find a substring.

### Validate external input

Patterns can be invalid or computationally expensive.

### Keep database access parameterized

Pattern values should be passed as data, not concatenated into SQL.

### Measure performance

Pattern matching can behave differently at scale.

### Use the simplest expressive language

If `%` and `_` are sufficient, a complicated regex may provide unnecessary complexity.

### Consider indexing

The database execution strategy matters as much as the matching expression.

### Handle missing values explicitly

Empty strings and `NULL` are different concepts.

### Treat case sensitivity as a deliberate requirement

Do not assume that all systems use the same rules.

---

## Files represented by this study

The Python implementation is a standalone educational program containing the broadest treatment of the topic.

The JavaScript implementation is a standalone executable file focused on JavaScript regular expressions, application-side filtering, reusable matching, and event-loop behavior.

The C++ implementation is a complete C++17 case study representing a searchable record-management system with validation, query processing, dynamic programming, regular expressions, exception handling, and performance measurement.

All three implementations use complete executable logic rather than pseudocode or unfinished placeholders.
