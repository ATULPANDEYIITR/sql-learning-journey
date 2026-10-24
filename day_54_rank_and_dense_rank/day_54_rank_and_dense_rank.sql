DROP SCHEMA IF EXISTS leaderboard_demo CASCADE;
CREATE SCHEMA leaderboard_demo;

SET search_path TO leaderboard_demo;

CREATE TABLE players (
    player_id BIGSERIAL PRIMARY KEY,
    player_name TEXT NOT NULL,
    team_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT players_name_not_blank
        CHECK (btrim(player_name) <> ''),
    CONSTRAINT players_team_not_blank
        CHECK (btrim(team_name) <> '')
);

CREATE TABLE competitions (
    competition_id BIGSERIAL PRIMARY KEY,
    competition_name TEXT NOT NULL UNIQUE,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT competitions_name_not_blank
        CHECK (btrim(competition_name) <> ''),
    CONSTRAINT competitions_valid_period
        CHECK (ends_at > starts_at)
);

CREATE TABLE scores (
    score_id BIGSERIAL PRIMARY KEY,
    competition_id BIGINT NOT NULL
        REFERENCES competitions(competition_id)
        ON DELETE CASCADE,
    player_id BIGINT NOT NULL
        REFERENCES players(player_id)
        ON DELETE CASCADE,
    score NUMERIC(12, 2) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT scores_non_negative
        CHECK (score >= 0),
    CONSTRAINT scores_player_unique
        UNIQUE (competition_id, player_id)
);

CREATE INDEX idx_scores_competition_score
    ON scores (competition_id, score DESC, player_id);

CREATE INDEX idx_players_team
    ON players (team_name);

INSERT INTO competitions (
    competition_name,
    starts_at,
    ends_at
)
VALUES (
    'Autumn Coding League',
    '2026-10-01 00:00:00+05:30',
    '2026-10-31 23:59:59+05:30'
);

INSERT INTO players (player_name, team_name)
VALUES
    ('Aarav', 'Red'),
    ('Meera', 'Red'),
    ('Kabir', 'Red'),
    ('Diya', 'Blue'),
    ('Ishaan', 'Blue'),
    ('Anaya', 'Blue'),
    ('Vihaan', 'Blue');

INSERT INTO scores (
    competition_id,
    player_id,
    score
)
SELECT
    1,
    player_id,
    CASE player_name
        WHEN 'Aarav' THEN 980
        WHEN 'Meera' THEN 920
        WHEN 'Kabir' THEN 920
        WHEN 'Diya' THEN 850
        WHEN 'Ishaan' THEN 850
        WHEN 'Anaya' THEN 850
        WHEN 'Vihaan' THEN 700
    END
FROM players;

CREATE OR REPLACE VIEW competition_leaderboard AS
SELECT
    p.player_id,
    p.player_name,
    p.team_name,
    s.competition_id,
    s.score,

    /*
     * RANK preserves gaps caused by ties:
     * 980, 920, 920, 850 -> 1, 2, 2, 4.
     */
    RANK() OVER (
        PARTITION BY s.competition_id
        ORDER BY s.score DESC
    ) AS rank_position,

    /*
     * DENSE_RANK removes gaps:
     * 980, 920, 920, 850 -> 1, 2, 2, 3.
     */
    DENSE_RANK() OVER (
        PARTITION BY s.competition_id
        ORDER BY s.score DESC
    ) AS dense_rank_position,

    ROW_NUMBER() OVER (
        PARTITION BY s.competition_id
        ORDER BY s.score DESC, p.player_id
    ) AS display_position
FROM scores s
JOIN players p
    ON p.player_id = s.player_id;

CREATE OR REPLACE VIEW team_leaderboard AS
SELECT
    p.player_id,
    p.player_name,
    p.team_name,
    s.competition_id,
    s.score,
    RANK() OVER (
        PARTITION BY s.competition_id, p.team_name
        ORDER BY s.score DESC
    ) AS team_rank,
    DENSE_RANK() OVER (
        PARTITION BY s.competition_id, p.team_name
        ORDER BY s.score DESC
    ) AS team_dense_rank
FROM scores s
JOIN players p
    ON p.player_id = s.player_id;

-- Global ranking with both ranking semantics.
SELECT
    player_name,
    score,
    rank_position,
    dense_rank_position
FROM competition_leaderboard
WHERE competition_id = 1
ORDER BY rank_position, player_id;

-- Every player in the first two distinct score levels.
SELECT
    player_name,
    score,
    dense_rank_position
FROM competition_leaderboard
WHERE competition_id = 1
  AND dense_rank_position <= 2
ORDER BY score DESC, player_id;

-- The top three leaderboard positions by RANK.
-- A tie can cause more than three rows to be returned.
SELECT
    player_name,
    score,
    rank_position
FROM competition_leaderboard
WHERE competition_id = 1
  AND rank_position <= 3
ORDER BY rank_position, player_id;

-- Team-specific ranking demonstrates partitioning.
SELECT
    team_name,
    player_name,
    score,
    team_rank,
    team_dense_rank
FROM team_leaderboard
WHERE competition_id = 1
ORDER BY team_name, team_rank, player_id;

-- Count how many distinct score levels exist.
SELECT
    competition_id,
    COUNT(DISTINCT score) AS distinct_score_levels,
    COUNT(*) AS participating_players
FROM scores
WHERE competition_id = 1
GROUP BY competition_id;

-- Identify score levels containing ties.
SELECT
    score,
    COUNT(*) AS players_at_score,
    DENSE_RANK() OVER (
        ORDER BY score DESC
    ) AS score_level
FROM scores
WHERE competition_id = 1
GROUP BY score
HAVING COUNT(*) > 1
ORDER BY score DESC;

-- Find the number of players immediately below each player.
-- This exposes the gap behavior of RANK.
WITH ranked AS (
    SELECT
        player_id,
        player_name,
        score,
        RANK() OVER (
            ORDER BY score DESC
        ) AS rank_position,
        DENSE_RANK() OVER (
            ORDER BY score DESC
        ) AS dense_rank_position
    FROM scores
    WHERE competition_id = 1
)
SELECT
    player_name,
    score,
    rank_position,
    dense_rank_position,
    rank_position - dense_rank_position AS tie_gap
FROM ranked
ORDER BY rank_position, player_id;

-- A CTE can use ranking results as a business rule.
WITH ranked AS (
    SELECT
        p.player_name,
        p.team_name,
        s.score,
        RANK() OVER (
            ORDER BY s.score DESC
        ) AS rank_position,
        DENSE_RANK() OVER (
            ORDER BY s.score DESC
        ) AS dense_rank_position
    FROM scores s
    JOIN players p
        ON p.player_id = s.player_id
    WHERE s.competition_id = 1
)
SELECT
    player_name,
    team_name,
    score,
    rank_position,
    dense_rank_position,
    CASE
        WHEN dense_rank_position = 1 THEN 'CHAMPION'
        WHEN dense_rank_position <= 3 THEN 'PODIUM_LEVEL'
        ELSE 'STANDARD'
    END AS leaderboard_status
FROM ranked
ORDER BY rank_position, player_name;

-- Transactional example: replace a score safely.
BEGIN;

UPDATE scores
SET score = score + 25,
    recorded_at = CURRENT_TIMESTAMP
WHERE competition_id = 1
  AND player_id = (
      SELECT player_id
      FROM players
      WHERE player_name = 'Vihaan'
  );

-- Verify the changed ranking before committing.
SELECT
    player_name,
    score,
    RANK() OVER (ORDER BY score DESC) AS rank_position,
    DENSE_RANK() OVER (ORDER BY score DESC) AS dense_rank_position
FROM scores s
JOIN players p USING (player_id)
WHERE competition_id = 1
ORDER BY score DESC, player_id;

COMMIT;

-- The following intentionally fails because score cannot be negative.
-- It is kept disabled so the complete script remains executable.
-- UPDATE scores SET score = -1 WHERE score_id = 1;

-- Query-plan-friendly access path for a competition leaderboard.
EXPLAIN
SELECT
    p.player_name,
    s.score,
    RANK() OVER (ORDER BY s.score DESC) AS rank_position,
    DENSE_RANK() OVER (ORDER BY s.score DESC) AS dense_rank_position
FROM scores s
JOIN players p
    ON p.player_id = s.player_id
WHERE s.competition_id = 1
ORDER BY s.score DESC, p.player_id;
