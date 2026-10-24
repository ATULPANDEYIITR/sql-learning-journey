#include <algorithm>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

struct Player {
    int id;
    std::string name;
    long long score;
    std::string team;
};

struct RankedPlayer {
    Player player;
    std::size_t rank;
    std::size_t denseRank;
};

class RankingEngine {
public:
    static void validate(const std::vector<Player>& players) {
        std::unordered_map<int, bool> ids;

        for (const auto& player : players) {
            if (player.id <= 0) {
                throw std::invalid_argument("Player ID must be positive");
            }

            if (player.name.empty()) {
                throw std::invalid_argument("Player name cannot be empty");
            }

            if (player.score < 0) {
                throw std::invalid_argument("Score cannot be negative");
            }

            if (ids.contains(player.id)) {
                throw std::invalid_argument("Duplicate player ID");
            }

            ids[player.id] = true;
        }
    }

    /*
     * Ranking requires a total ordering for deterministic output.
     * The primary ordering is score descending. Player ID is only a
     * deterministic display tie-breaker and does not change the rank.
     */
    static std::vector<RankedPlayer>
    rank(const std::vector<Player>& players) {
        validate(players);

        std::vector<Player> ordered = players;

        std::sort(
            ordered.begin(),
            ordered.end(),
            [](const Player& a, const Player& b) {
                if (a.score != b.score) {
                    return a.score > b.score;
                }
                return a.id < b.id;
            }
        );

        std::vector<RankedPlayer> result;
        result.reserve(ordered.size());

        long long previousScore = -1;
        std::size_t currentRank = 0;
        std::size_t currentDenseRank = 0;

        for (std::size_t i = 0; i < ordered.size(); ++i) {
            const auto& player = ordered[i];
            const std::size_t position = i + 1;

            if (i == 0 || player.score != previousScore) {
                currentRank = position;
                ++currentDenseRank;
            }

            result.push_back(
                RankedPlayer{
                    player,
                    currentRank,
                    currentDenseRank
                }
            );

            previousScore = player.score;
        }

        return result;
    }

    static std::vector<RankedPlayer>
    rankByTeam(const std::vector<Player>& players) {
        validate(players);

        std::unordered_map<std::string, std::vector<Player>> groups;

        for (const auto& player : players) {
            if (player.team.empty()) {
                throw std::invalid_argument("Team cannot be empty");
            }
            groups[player.team].push_back(player);
        }

        std::vector<RankedPlayer> result;

        for (auto& [team, members] : groups) {
            auto ranked = rank(members);
            result.insert(
                result.end(),
                ranked.begin(),
                ranked.end()
            );
        }

        std::sort(
            result.begin(),
            result.end(),
            [](const RankedPlayer& a, const RankedPlayer& b) {
                if (a.player.team != b.player.team) {
                    return a.player.team < b.player.team;
                }
                if (a.rank != b.rank) {
                    return a.rank < b.rank;
                }
                return a.player.id < b.player.id;
            }
        );

        return result;
    }
};

void printLeaderboard(const std::vector<RankedPlayer>& rows) {
    std::cout << std::left
              << std::setw(16) << "Player"
              << std::right
              << std::setw(10) << "Score"
              << std::setw(10) << "RANK"
              << std::setw(12) << "DENSE_RANK"
              << '\n';

    std::cout << std::string(48, '-') << '\n';

    for (const auto& row : rows) {
        std::cout << std::left
                  << std::setw(16) << row.player.name
                  << std::right
                  << std::setw(10) << row.player.score
                  << std::setw(10) << row.rank
                  << std::setw(12) << row.denseRank
                  << '\n';
    }
}

void verifyRanking(const std::vector<RankedPlayer>& rows) {
    const std::vector<std::size_t> expectedRank{
        1, 2, 2, 4, 4, 4, 7
    };

    const std::vector<std::size_t> expectedDense{
        1, 2, 2, 3, 3, 3, 4
    };

    if (rows.size() != expectedRank.size()) {
        throw std::runtime_error("Unexpected leaderboard size");
    }

    for (std::size_t i = 0; i < rows.size(); ++i) {
        if (rows[i].rank != expectedRank[i] ||
            rows[i].denseRank != expectedDense[i]) {
            throw std::runtime_error("Ranking verification failed");
        }
    }
}

int main() {
    try {
        const std::vector<Player> players{
            {1, "Aarav", 980, "Red"},
            {2, "Meera", 920, "Red"},
            {3, "Kabir", 920, "Red"},
            {4, "Diya", 850, "Blue"},
            {5, "Ishaan", 850, "Blue"},
            {6, "Anaya", 850, "Blue"},
            {7, "Vihaan", 700, "Blue"}
        };

        const auto global = RankingEngine::rank(players);

        std::cout << "Global leaderboard\n";
        printLeaderboard(global);

        verifyRanking(global);

        std::cout << "\nTeam leaderboards\n";
        const auto teams = RankingEngine::rankByTeam(players);
        printLeaderboard(teams);

        std::cout << "\nRanking verification passed.\n";
        std::cout
            << "Complexity: O(n log n) time and O(n) auxiliary storage.\n";

    } catch (const std::exception& error) {
        std::cerr << "Ranking engine error: "
                  << error.what() << '\n';
        return 1;
    }

    return 0;
}
