import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class RankingGovernance {

    public record Player(
            int id,
            String name,
            long score,
            String team
    ) {}

    public record RankedPlayer(
            Player player,
            long rank,
            long denseRank
    ) {}

    public enum RankingPolicy {
        STANDARD_RANK,
        DENSE_RANK
    }

    public static final class RankingValidationException
            extends RuntimeException {
        public RankingValidationException(String message) {
            super(message);
        }
    }

    public interface RankingService {
        List<RankedPlayer> rank(List<Player> players);
        List<RankedPlayer> rankByTeam(List<Player> players);
    }

    public static final class LeaderboardService
            implements RankingService {

        private static final Comparator<Player> ORDER =
                Comparator.comparingLong(Player::score)
                        .reversed()
                        .thenComparingInt(Player::id);

        private void validate(List<Player> players) {
            if (players == null) {
                throw new RankingValidationException(
                        "Players cannot be null"
                );
            }

            Set<Integer> ids = new HashSet<>();

            for (Player player : players) {
                if (player == null) {
                    throw new RankingValidationException(
                            "Player cannot be null"
                    );
                }

                if (player.id() <= 0) {
                    throw new RankingValidationException(
                            "Player ID must be positive"
                    );
                }

                if (player.name() == null ||
                        player.name().isBlank()) {
                    throw new RankingValidationException(
                            "Player name cannot be empty"
                    );
                }

                if (player.score() < 0) {
                    throw new RankingValidationException(
                            "Score cannot be negative"
                    );
                }

                if (player.team() == null ||
                        player.team().isBlank()) {
                    throw new RankingValidationException(
                            "Team cannot be empty"
                    );
                }

                if (!ids.add(player.id())) {
                    throw new RankingValidationException(
                            "Duplicate player ID: " + player.id()
                    );
                }
            }
        }

        @Override
        public List<RankedPlayer> rank(List<Player> players) {
            validate(players);

            List<Player> ordered = new ArrayList<>(players);
            ordered.sort(ORDER);

            List<RankedPlayer> result =
                    new ArrayList<>(ordered.size());

            long rank = 0;
            long denseRank = 0;
            long previousScore = Long.MIN_VALUE;

            for (int index = 0; index < ordered.size(); index++) {
                Player player = ordered.get(index);
                long position = index + 1L;

                if (index == 0 ||
                        player.score() != previousScore) {
                    rank = position;
                    denseRank++;
                }

                result.add(
                        new RankedPlayer(
                                player,
                                rank,
                                denseRank
                        )
                );

                previousScore = player.score();
            }

            return List.copyOf(result);
        }

        @Override
        public List<RankedPlayer> rankByTeam(
                List<Player> players) {

            validate(players);

            Map<String, List<Player>> grouped =
                    new HashMap<>();

            for (Player player : players) {
                grouped
                        .computeIfAbsent(
                                player.team(),
                                ignored -> new ArrayList<>()
                        )
                        .add(player);
            }

            List<RankedPlayer> result = new ArrayList<>();

            grouped.entrySet()
                    .stream()
                    .sorted(Map.Entry.comparingByKey())
                    .forEach(entry ->
                            result.addAll(rank(entry.getValue()))
                    );

            return List.copyOf(result);
        }
    }

    private static void print(
            List<RankedPlayer> rows) {

        System.out.printf(
                "%-16s %8s %8s %12s%n",
                "Player",
                "Score",
                "RANK",
                "DENSE_RANK"
        );

        System.out.println("-".repeat(50));

        for (RankedPlayer row : rows) {
            System.out.printf(
                    "%-16s %8d %8d %12d%n",
                    row.player().name(),
                    row.player().score(),
                    row.rank(),
                    row.denseRank()
            );
        }
    }

    private static void verify(
            List<RankedPlayer> rows) {

        long[] expectedRank =
                {1, 2, 2, 4, 4, 4, 7};

        long[] expectedDense =
                {1, 2, 2, 3, 3, 3, 4};

        if (rows.size() != expectedRank.length) {
            throw new IllegalStateException(
                    "Unexpected leaderboard size"
            );
        }

        for (int i = 0; i < rows.size(); i++) {
            if (rows.get(i).rank() != expectedRank[i] ||
                    rows.get(i).denseRank() != expectedDense[i]) {
                throw new IllegalStateException(
                        "Ranking verification failed"
                );
            }
        }
    }

    public static void main(String[] args) {
        List<Player> players = List.of(
                new Player(1, "Aarav", 980, "Red"),
                new Player(2, "Meera", 920, "Red"),
                new Player(3, "Kabir", 920, "Red"),
                new Player(4, "Diya", 850, "Blue"),
                new Player(5, "Ishaan", 850, "Blue"),
                new Player(6, "Anaya", 850, "Blue"),
                new Player(7, "Vihaan", 700, "Blue")
        );

        RankingService service =
                new LeaderboardService();

        List<RankedPlayer> global =
                service.rank(players);

        System.out.println("Global leaderboard");
        print(global);
        verify(global);

        System.out.println("\nRanking policy interpretation");
        System.out.println(
                "RANK assigns the next position after a tie."
        );
        System.out.println(
                "DENSE_RANK advances only when the score changes."
        );

        System.out.println("\nEnterprise team ranking");
        print(service.rankByTeam(players));

        System.out.println("\nValidation checks passed.");
    }
}
