'use strict';

/*
 * Ranking a leaderboard with RANK and DENSE_RANK semantics.
 *
 * RANK:
 *   scores 100, 90, 90, 80 -> 1, 2, 2, 4
 *
 * DENSE_RANK:
 *   scores 100, 90, 90, 80 -> 1, 2, 2, 3
 */

class ValidationError extends Error {}

function validatePlayers(players) {
    if (!Array.isArray(players)) {
        throw new ValidationError('players must be an array');
    }

    const ids = new Set();

    for (const player of players) {
        if (!Number.isInteger(player.id) || player.id <= 0) {
            throw new ValidationError(`Invalid player id: ${player.id}`);
        }

        if (typeof player.name !== 'string' || player.name.trim() === '') {
            throw new ValidationError(`Invalid player name for ${player.id}`);
        }

        if (!Number.isFinite(player.score) || player.score < 0) {
            throw new ValidationError(`Invalid score for ${player.id}`);
        }

        if (ids.has(player.id)) {
            throw new ValidationError(`Duplicate player id: ${player.id}`);
        }

        ids.add(player.id);
    }
}

function rankLeaderboard(players) {
    validatePlayers(players);

    const ordered = [...players].sort(
        (a, b) => b.score - a.score || a.id - b.id
    );

    let previousScore = null;
    let rank = 0;
    let denseRank = 0;

    return ordered.map((player, index) => {
        const position = index + 1;

        if (previousScore === null || player.score !== previousScore) {
            rank = position;
            denseRank += 1;
        }

        previousScore = player.score;

        return {
            ...player,
            rank,
            denseRank
        };
    });
}

function rankByGroup(players, groupField) {
    if (!Array.isArray(players)) {
        throw new ValidationError('players must be an array');
    }

    const groups = new Map();

    for (const player of players) {
        if (typeof player[groupField] !== 'string' ||
            player[groupField].trim() === '') {
            throw new ValidationError(`Invalid ${groupField}`);
        }

        if (!groups.has(player[groupField])) {
            groups.set(player[groupField], []);
        }

        groups.get(player[groupField]).push(player);
    }

    const result = [];

    for (const [group, members] of groups) {
        const ranked = rankLeaderboard(members);

        for (const row of ranked) {
            result.push({
                ...row,
                group
            });
        }
    }

    return result.sort(
        (a, b) =>
            a.group.localeCompare(b.group) ||
            a.rank - b.rank ||
            a.id - b.id
    );
}

function getTopDenseLevels(ranked, levels) {
    if (!Number.isInteger(levels) || levels <= 0) {
        throw new ValidationError('levels must be a positive integer');
    }

    return ranked.filter(row => row.denseRank <= levels);
}

function printLeaderboard(rows) {
    console.log(
        `${'Player'.padEnd(16)}${'Score'.padStart(8)}${'RANK'.padStart(8)}${'DENSE'.padStart(8)}`
    );
    console.log('-'.repeat(40));

    for (const row of rows) {
        console.log(
            `${row.name.padEnd(16)}` +
            `${String(row.score).padStart(8)}` +
            `${String(row.rank).padStart(8)}` +
            `${String(row.denseRank).padStart(8)}`
        );
    }
}

async function processLeaderboard(players) {
    // Promise-based processing models a service that could later
    // combine database, cache, or API operations.
    return Promise.resolve(rankLeaderboard(players));
}

async function main() {
    const players = [
        { id: 1, name: 'Aarav', score: 980 },
        { id: 2, name: 'Meera', score: 920 },
        { id: 3, name: 'Kabir', score: 920 },
        { id: 4, name: 'Diya', score: 850 },
        { id: 5, name: 'Ishaan', score: 850 },
        { id: 6, name: 'Anaya', score: 850 },
        { id: 7, name: 'Vihaan', score: 700 }
    ];

    const ranked = await processLeaderboard(players);

    console.log('Global leaderboard');
    printLeaderboard(ranked);

    console.log('\nTop two dense-rank levels');
    console.table(getTopDenseLevels(ranked, 2));

    const teams = [
        { id: 1, name: 'Aarav', team: 'Red', score: 980 },
        { id: 2, name: 'Meera', team: 'Red', score: 920 },
        { id: 3, name: 'Kabir', team: 'Red', score: 920 },
        { id: 4, name: 'Diya', team: 'Blue', score: 950 },
        { id: 5, name: 'Ishaan', team: 'Blue', score: 950 },
        { id: 6, name: 'Anaya', team: 'Blue', score: 700 }
    ];

    console.log('\nPartitioned leaderboard');
    console.table(rankByGroup(teams, 'team'));

    const expectedRank = [1, 2, 2, 4, 4, 4, 7];
    const expectedDenseRank = [1, 2, 2, 3, 3, 3, 4];

    console.assert(
        JSON.stringify(ranked.map(r => r.rank)) === JSON.stringify(expectedRank),
        'RANK calculation failed'
    );

    console.assert(
        JSON.stringify(ranked.map(r => r.denseRank)) ===
        JSON.stringify(expectedDenseRank),
        'DENSE_RANK calculation failed'
    );

    console.log('\nValidation checks passed.');
}

main().catch(error => {
    console.error(`Leaderboard processing failed: ${error.message}`);
    process.exitCode = 1;
});
