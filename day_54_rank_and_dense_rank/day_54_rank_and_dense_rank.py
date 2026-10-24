from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class Player:
    player_id: int
    name: str
    score: Decimal


def validate_players(players: Iterable[Player]) -> list[Player]:
    result = list(players)
    seen_ids: set[int] = set()

    for player in result:
        if player.player_id <= 0:
            raise ValueError(f"Invalid player id: {player.player_id}")
        if not player.name.strip():
            raise ValueError(f"Player {player.player_id} has an empty name")
        if player.score < 0:
            raise ValueError(f"Negative score for player {player.player_id}")
        if player.player_id in seen_ids:
            raise ValueError(f"Duplicate player id: {player.player_id}")
        seen_ids.add(player.player_id)

    return result


def rank_competition(players: Iterable[Player]) -> list[dict]:
    """
    Produce RANK and DENSE_RANK values.

    RANK:
        1, 2, 2, 4
        Equal scores share a position and consume positions.

    DENSE_RANK:
        1, 2, 2, 3
        Equal scores share a position without gaps.
    """
    ordered = sorted(
        validate_players(players),
        key=lambda p: (-p.score, p.player_id)
    )

    output: list[dict] = []
    previous_score: Decimal | None = None
    rank = 0
    dense_rank = 0

    for position, player in enumerate(ordered, start=1):
        if previous_score is None or player.score != previous_score:
            rank = position
            dense_rank += 1

        output.append(
            {
                "player_id": player.player_id,
                "name": player.name,
                "score": player.score,
                "rank": rank,
                "dense_rank": dense_rank,
            }
        )
        previous_score = player.score

    return output


def rank_with_partition(players: Iterable[dict]) -> list[dict]:
    """
    Demonstrate ranking inside independent groups.

    Each row has:
        player_id, name, team, score

    The rank resets for every team, equivalent to:
        RANK() OVER (PARTITION BY team ORDER BY score DESC)
    """
    rows = list(players)

    for row in rows:
        required = {"player_id", "name", "team", "score"}
        if not required.issubset(row):
            raise ValueError("Every player row must contain all required fields")
        if not row["team"].strip():
            raise ValueError("Team cannot be empty")

    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["team"], []).append(row)

    result: list[dict] = []

    for team, members in groups.items():
        members.sort(key=lambda x: (-x["score"], x["player_id"]))
        previous_score = None
        rank = 0
        dense_rank = 0

        for position, member in enumerate(members, start=1):
            if previous_score is None or member["score"] != previous_score:
                rank = position
                dense_rank += 1

            result.append(
                {
                    **member,
                    "rank": rank,
                    "dense_rank": dense_rank,
                }
            )
            previous_score = member["score"]

    return sorted(result, key=lambda x: (x["team"], x["rank"], x["player_id"]))


def top_n_distinct_score_levels(
    ranked: list[dict], levels: int
) -> list[dict]:
    """Return every player belonging to the first N dense-rank levels."""
    if levels <= 0:
        raise ValueError("levels must be positive")

    return [
        row for row in ranked
        if row["dense_rank"] <= levels
    ]


def print_leaderboard(rows: list[dict]) -> None:
    print(f"{'Player':<16}{'Score':>8}{'RANK':>8}{'DENSE':>8}")
    print("-" * 40)
    for row in rows:
        print(
            f"{row['name']:<16}"
            f"{row['score']:>8}"
            f"{row['rank']:>8}"
            f"{row['dense_rank']:>8}"
        )


def main() -> None:
    players = [
        Player(1, "Aarav", Decimal("980")),
        Player(2, "Meera", Decimal("920")),
        Player(3, "Kabir", Decimal("920")),
        Player(4, "Diya", Decimal("850")),
        Player(5, "Ishaan", Decimal("850")),
        Player(6, "Anaya", Decimal("850")),
        Player(7, "Vihaan", Decimal("700")),
    ]

    ranked = rank_competition(players)

    print("Global leaderboard")
    print_leaderboard(ranked)

    print("\nTop two distinct score levels")
    for row in top_n_distinct_score_levels(ranked, 2):
        print(
            row["name"],
            row["score"],
            "rank=", row["rank"],
            "dense_rank=", row["dense_rank"],
        )

    team_players = [
        {"player_id": 1, "name": "Aarav", "team": "Red", "score": 980},
        {"player_id": 2, "name": "Meera", "team": "Red", "score": 920},
        {"player_id": 3, "name": "Kabir", "team": "Red", "score": 920},
        {"player_id": 4, "name": "Diya", "team": "Blue", "score": 950},
        {"player_id": 5, "name": "Ishaan", "team": "Blue", "score": 950},
        {"player_id": 6, "name": "Anaya", "team": "Blue", "score": 700},
    ]

    print("\nPartitioned leaderboard")
    partitioned = rank_with_partition(team_players)

    for row in partitioned:
        print(
            row["team"],
            row["name"],
            row["score"],
            "rank=", row["rank"],
            "dense_rank=", row["dense_rank"],
        )

    # Demonstrate an important tie property.
    assert [r["rank"] for r in ranked] == [1, 2, 2, 4, 4, 4, 7]
    assert [r["dense_rank"] for r in ranked] == [1, 2, 2, 3, 3, 3, 4]

    # No player can have a rank greater than the number of players.
    assert all(1 <= r["rank"] <= len(players) for r in ranked)

    print("\nValidation checks passed.")


if __name__ == "__main__":
    main()
