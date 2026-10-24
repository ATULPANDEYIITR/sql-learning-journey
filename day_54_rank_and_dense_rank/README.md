# RANK and DENSE_RANK

## Scope

This project examines two SQL window functions used to assign positions to ordered data:

- `RANK()` assigns the same rank to tied rows and leaves gaps after a tie.
- `DENSE_RANK()` assigns the same rank to tied rows without leaving gaps.

The distinction becomes important when building leaderboards, competition results, score classifications, grouped rankings, and reports where ties are meaningful.

The five implementations approach the same ranking problem from different engineering perspectives:

| Implementation | Primary perspective | Main mechanism |
|---|---|---|
| Python | Algorithmic leaderboard model | Sorting, state tracking, validation, partitioned ranking |
| JavaScript | Event-oriented application model | Maps, Sets, asynchronous processing, validation |
| C++17 | Ranking engine | STL sorting, domain structures, deterministic ordering |
| Java 17 | Enterprise domain model | Records, interfaces, services, validation, immutable results |
| PostgreSQL | Relational ranking workflow | Window functions, partitions, views, CTEs, indexes |

## Ranking Semantics

Assume the following scores:

| Player | Score |
|---|---:|
| Aarav | 980 |
| Meera | 920 |
| Kabir | 920 |
| Diya | 850 |
| Ishaan | 850 |
| Anaya | 850 |
| Vihaan | 700 |

The resulting rankings are:

| Player | Score | `RANK()` | `DENSE_RANK()` |
|---|---:|---:|---:|
| Aarav | 980 | 1 | 1 |
| Meera | 920 | 2 | 2 |
| Kabir | 920 | 2 | 2 |
| Diya | 850 | 4 | 3 |
| Ishaan | 850 | 4 | 3 |
| Anaya | 850 | 4 | 3 |
| Vihaan | 700 | 7 | 4 |

The important difference is the gap.

With `RANK()`, three players occupy rank 4, so the next player receives rank 7.

With `DENSE_RANK()`, the next distinct score receives rank 4 because only distinct score levels determine the rank number.

### Mathematical interpretation

For an ordering by descending score:

`RANK()` identifies the position of the first row in the current tie group.

`DENSE_RANK()` identifies the ordinal number of the current distinct score group.

Therefore, if there are `k` rows tied before a later score, `RANK()` advances by `k`, while `DENSE_RANK()` advances by exactly one.

## Why Ties Matter

A ranking function does not merely sort data. It defines how equal values affect the meaning of position.

Consider a competition with four distinct score levels:

`100, 90, 90, 80`

The rankings are:

| Score | `RANK()` | `DENSE_RANK()` |
|---:|---:|---:|
| 100 | 1 | 1 |
| 90 | 2 | 2 |
| 90 | 2 | 2 |
| 80 | 4 | 3 |

`RANK()` is appropriate when position represents the actual ordinal location of each row in the sorted population.

`DENSE_RANK()` is appropriate when position represents the ordinal level of a distinct value.

## Leaderboard Interpretation

A competition leaderboard may use either interpretation depending on the business rule.

### Competition position

If three competitors tie for second place, the next competitor is fourth:

`1, 2, 2, 4`

This is the conventional competition-ranking interpretation and corresponds to `RANK()`.

### Score level

If the application wants to identify the first, second, third, and fourth distinct performance levels:

`1, 2, 2, 3`

This corresponds to `DENSE_RANK()`.

The choice should be made from the meaning of the ranking rather than from the appearance of the output.

## SQL Window Functions

PostgreSQL provides both functions as window functions.

The basic form is:

`RANK() OVER (ORDER BY score DESC)`

and:

`DENSE_RANK() OVER (ORDER BY score DESC)`

The `ORDER BY` expression determines the ranking order.

For a high-score-first leaderboard, `DESC` is normally used.

For a low-value-first ranking, the ordering can be reversed with `ASC`.

The window function does not collapse rows. Every input row remains in the result.

This is different from `GROUP BY`, which produces one row per grouping combination.

## Ties and Secondary Ordering

A common leaderboard query may contain:

`ORDER BY score DESC, player_id`

The primary ranking value is still `score`.

The secondary `player_id` makes the displayed row order deterministic.

This distinction is important:

- `score` determines the ranking equivalence.
- `player_id` determines deterministic ordering among equal-score rows.

If the business rule says equal scores must have the same rank, a secondary ordering expression should not accidentally redefine the ranking groups.

For example, `RANK() OVER (ORDER BY score DESC, player_id)` treats each unique combination of score and player ID as an ordering value. That can eliminate the intended ties.

The correct design for score-based ties is normally:

`RANK() OVER (ORDER BY score DESC)`

while using `player_id` only in the outer query's display ordering.

## Partitioned Ranking

Ranking does not have to be global.

A leaderboard can be reset for every team, department, category, tournament, or geographic region.

The SQL form is:

`RANK() OVER (PARTITION BY team_name ORDER BY score DESC)`

and:

`DENSE_RANK() OVER (PARTITION BY team_name ORDER BY score DESC)`

The partition establishes independent ranking groups.

For example:

| Team | Player | Score | Team Rank |
|---|---|---:|---:|
| Blue | Diya | 950 | 1 |
| Blue | Ishaan | 950 | 1 |
| Blue | Anaya | 700 | 3 |
| Red | Aarav | 980 | 1 |
| Red | Meera | 920 | 2 |
| Red | Kabir | 920 | 2 |

The rank restarts when the partition changes.

## Python Implementation

The Python implementation models players with a `dataclass`.

Each player contains:

- numeric identifier
- name
- score

Validation prevents:

- non-positive identifiers
- empty names
- negative scores
- duplicate identifiers

The ranking algorithm sorts players by descending score and uses player ID only as a deterministic tie-breaker for display order.

Two state variables are maintained:

- `rank`
- `dense_rank`

When the score changes, the algorithm updates both values.

The standard rank uses the current one-based sorted position. This creates gaps after ties.

The dense rank increases by one for every new score level.

The Python implementation also models partitioned ranking by grouping players with a dictionary. Each group is independently ranked, which corresponds conceptually to SQL's `PARTITION BY`.

The script includes assertions that verify:

`RANK()` equivalent output: `1, 2, 2, 4, 4, 4, 7`

`DENSE_RANK()` equivalent output: `1, 2, 2, 3, 3, 3, 4`

This provides a direct correctness check for the core ranking semantics.

## JavaScript Implementation

The JavaScript implementation uses objects to represent player records.

`Set` is used to detect duplicate player identifiers efficiently.

`Map` is used to create independent groups for partitioned ranking.

The implementation separates responsibilities into functions:

- input validation
- global ranking
- grouped ranking
- top dense-rank selection
- output formatting

The asynchronous `processLeaderboard` function uses a Promise-based interface. The ranking itself is CPU-local, but the service shape allows the same interface to be integrated into an application where the data could originate from asynchronous database or network operations.

The implementation deliberately keeps ranking state separate from display formatting.

This prevents formatting requirements from changing the ranking algorithm.

## C++17 Implementation

The C++ implementation models ranking as an explicit `RankingEngine`.

`Player` represents input data.

`RankedPlayer` contains the original player and computed ranking values.

The engine uses:

- `std::vector` for ordered player storage
- `std::sort` for score ordering
- `std::unordered_map` for duplicate detection and team grouping
- exceptions for invalid domain data

The comparison function orders scores descending and then uses player ID to make equal-score display order deterministic.

The rank calculation itself compares only scores.

This distinction prevents the deterministic tie-breaker from changing the semantics of the ranking.

The program also provides a team-ranking operation that independently ranks each group.

Complexity is dominated by sorting:

- Time: `O(n log n)`
- Auxiliary storage: `O(n)`

For large datasets, database-side ranking can be preferable because the database can combine filtering, indexing, partitioning, and ranking closer to the stored data.

## Java 17 Implementation

The Java implementation uses an enterprise-oriented service model.

`Player` and `RankedPlayer` are Java records, providing compact immutable domain representations.

`RankingService` defines the service contract.

`LeaderboardService` implements ranking and validation.

The service explicitly models:

- domain validation
- ordering policy
- ranking state
- partitioning
- immutable result collections

The implementation uses Java collections and comparators rather than exposing the ranking algorithm through a procedural `main` method.

The resulting structure is suitable for a larger application where a service could be called by an API, scheduled process, reporting system, or persistence layer.

The validation layer rejects:

- null players
- invalid identifiers
- empty names
- negative scores
- empty teams
- duplicate identifiers

The service returns immutable lists through `List.copyOf`, preventing callers from modifying the computed ranking accidentally.

## PostgreSQL Implementation

The PostgreSQL implementation represents the domain relationally.

The main entities are:

`players`

Stores player identity and team membership.

`competitions`

Stores competition boundaries and names.

`scores`

Associates one player with one competition and stores the player's score.

The unique constraint on `(competition_id, player_id)` prevents duplicate score records for the same player within a competition.

The score check constraint prevents negative scores.

## Database Ranking

The main view, `competition_leaderboard`, calculates:

- `RANK()`
- `DENSE_RANK()`
- `ROW_NUMBER()`

`ROW_NUMBER()` is included as a useful contrast.

For equal scores:

- `RANK()` produces equal ranks with gaps.
- `DENSE_RANK()` produces equal ranks without gaps.
- `ROW_NUMBER()` assigns every row a unique sequence.

For example:

| Score | RANK | DENSE_RANK | ROW_NUMBER |
|---:|---:|---:|---:|
| 100 | 1 | 1 | 1 |
| 90 | 2 | 2 | 2 |
| 90 | 2 | 2 | 3 |
| 80 | 4 | 3 | 4 |

`ROW_NUMBER()` should therefore not be substituted for either ranking function when ties must share a position.

## Top-N Ranking Problems

A major source of leaderboard bugs is ambiguity around "top N."

Suppose the ranks are:

`1, 2, 2, 4`

A query filtering on `rank <= 2` returns three players.

That is correct if the requirement means:

"Return everyone whose competition rank is within the top two positions."

It is different from:

"Return exactly two rows."

For exactly N rows, `ROW_NUMBER()` is usually the appropriate mechanism.

For the first N distinct score levels, `DENSE_RANK()` provides a direct expression of the requirement.

This distinction is important in contests, award systems, dashboards, and reporting systems.

## Tie Gap Analysis

The PostgreSQL script calculates:

`rank_position - dense_rank_position`

This value indicates the accumulated effect of previous ties.

For the example data:

| Score | RANK | DENSE_RANK | Gap |
|---:|---:|---:|---:|
| 980 | 1 | 1 | 0 |
| 920 | 2 | 2 | 0 |
| 850 | 4 | 3 | 1 |
| 700 | 7 | 4 | 3 |

The gap grows when earlier ranking levels contain multiple rows.

This provides a useful diagnostic when analyzing why competition ranks differ from distinct-score positions.

## Views and CTEs

The PostgreSQL implementation creates views so ranking logic can be reused by reporting queries.

A view can expose ranking calculations without requiring every consuming query to repeat the complete window-function definition.

CTEs are used for more specialized reporting.

For example, the script uses a CTE to classify players into:

- `CHAMPION`
- `PODIUM_LEVEL`
- `STANDARD`

The classification is performed after ranking has been calculated.

This keeps ranking logic separate from business classification logic.

## Constraints and Data Integrity

The database enforces several rules directly.

| Rule | Database mechanism |
|---|---|
| Every player has an identifier | Primary key |
| Every score belongs to a player | Foreign key |
| Every score belongs to a competition | Foreign key |
| Player cannot have duplicate competition score | Unique constraint |
| Score cannot be negative | Check constraint |
| Player name cannot be blank | Check constraint |
| Team name cannot be blank | Check constraint |
| Competition end must follow start | Check constraint |

Database-level enforcement is important because application-level validation alone cannot guarantee consistency when multiple applications or users can modify the same database.

## Indexing

The main score index is:

`(competition_id, score DESC, player_id)`

It supports common leaderboard access patterns where a competition is selected and scores are read in descending order.

The team index supports queries that group or filter players by team.

Indexes have a storage and write-maintenance cost. They should therefore correspond to actual query patterns rather than being added indiscriminately.

Window functions may still require sorting or additional execution work depending on the query plan and available indexes.

The included `EXPLAIN` statement provides a practical way to inspect the PostgreSQL execution strategy.

## Transactional Update

The PostgreSQL script demonstrates a transactional score update.

The transaction:

1. Changes a player's score.
2. Recalculates the leaderboard inside the transaction.
3. Commits the change.

If a validation or database error occurs before the commit, the transaction can be rolled back.

This matters when ranking is derived from mutable competition data. A partially updated set of scores should not become visible as an unintended permanent state.

## Deterministic Display Order

Ranking and display order are related but different concerns.

Two players with the same score must receive the same `RANK()` and `DENSE_RANK()` value.

The application may still need deterministic output order.

A stable secondary key such as `player_id` can be used for display:

`ORDER BY score DESC, player_id`

The secondary key should not be included in the ranking expression if equal scores are supposed to remain tied.

## Edge Cases

### No players

An empty input produces an empty ranking rather than an artificial rank.

### One player

The only player receives:

`RANK = 1`

and:

`DENSE_RANK = 1`

### All players tied

For five players with the same score:

`RANK = 1, 1, 1, 1, 1`

`DENSE_RANK = 1, 1, 1, 1, 1`

### No ties

When every score is unique, `RANK()` and `DENSE_RANK()` produce identical values.

### Negative scores

The provided domain treats scores as non-negative. Both application and database validation reject negative values.

### Duplicate players

The application implementations reject duplicate identifiers. PostgreSQL uses a uniqueness constraint on competition and player.

### Partitioned ranking

Each partition has an independent rank sequence.

A player ranked first in one team does not affect the rank of a player in another team.

## Common Ranking Errors

### Using `ROW_NUMBER()` for tied rankings

`ROW_NUMBER()` assigns a unique position to every row.

It is not equivalent to `RANK()`.

### Using `DENSE_RANK()` when competition positions are required

If three players tie for second place, `DENSE_RANK()` makes the next player third.

A conventional competition leaderboard normally expects fourth place.

### Including a tie-breaker in the ranking expression

Using:

`RANK() OVER (ORDER BY score DESC, player_id)`

can destroy score-based ties because the complete ordering expression becomes unique.

### Confusing top N rows with top N ranks

`LIMIT 10` means ten rows.

`RANK() <= 10` means all players whose rank is at most ten.

These can produce different result sizes.

### Confusing distinct score levels with positions

The number of distinct scores corresponds more closely to `DENSE_RANK()` than `RANK()`.

## Performance Considerations

For an in-memory implementation, ranking normally requires sorting:

`O(n log n)`

After sorting, assigning ranks is linear:

`O(n)`

Therefore the complete operation remains dominated by sorting.

The database version delegates ordering and ranking to PostgreSQL's execution engine.

For very large datasets, useful considerations include:

- filtering the competition before ranking
- indexing common filtering columns
- avoiding unnecessary columns in intermediate results
- using partitions when the business requirement genuinely calls for independent ranking
- inspecting execution plans
- avoiding repeated ranking calculations when a reusable view or materialized result is appropriate
- separating exact top-N-row requirements from top-N-rank requirements

## Security Considerations

Ranking itself is not a security mechanism.

Applications should still validate externally supplied identifiers, competition IDs, team names, and scores.

Database permissions should restrict who can modify scores.

If ranking data is exposed through an API, authorization should determine whether a user can access:

- global rankings
- private rankings
- team rankings
- historical competition data

Input validation prevents malformed data, while authorization prevents users from changing or reading data they are not permitted to access.

The sample implementations avoid dynamic SQL and do not construct executable SQL statements from user-provided strings.

## Relationship Between the Concepts

The central relationship can be represented as:

`Scores`
`  ↓`
`Ordered values`
`  ↓`
`Tie groups`
`  ├── RANK()`
`  │     ↓`
`  │   gaps after ties`
`  │`
`  └── DENSE_RANK()`
`        ↓`
`      no gaps`

The ranking function does not determine whether two rows should be tied by itself. The expressions in its `ORDER BY` clause define the values used to establish ranking equivalence.

This makes the selection of ranking expressions a core design decision.

## Practical Decision Table

| Requirement | Appropriate mechanism |
|---|---|
| Give tied competitors the same competition position | `RANK()` |
| Give tied score levels consecutive positions | `DENSE_RANK()` |
| Give every row a unique sequence | `ROW_NUMBER()` |
| Rank independently within teams | `PARTITION BY team` |
| Return everyone within the top three ranks | Filter on `RANK() <= 3` |
| Return first three distinct score levels | Filter on `DENSE_RANK() <= 3` |
| Return exactly three rows | `ROW_NUMBER()` or an explicit row limit |
| Preserve deterministic order among ties | Add a secondary ordering expression outside the rank definition |

## Repository File Responsibilities

The five source files deliberately emphasize different engineering concerns.

| File | Responsibility |
|---|---|
| Python | Builds a reusable ranking model and validates algorithmic behavior |
| JavaScript | Models ranking as a service-oriented, asynchronous application operation |
| C++17 | Implements a strongly structured ranking engine with explicit error handling |
| Java 17 | Models ranking as an enterprise service with immutable domain records |
| PostgreSQL | Performs ranking directly against relational competition data |

All implementations preserve the central distinction:

`RANK()` creates gaps after ties.

`DENSE_RANK()` does not create gaps after ties.

The surrounding architecture differs so that the ranking problem can be understood as an algorithm, application service, native engine, enterprise domain service, and relational database operation.
