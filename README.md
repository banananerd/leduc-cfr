# Leduc Hold'em CFR Solver

A from-scratch **vector-form Counterfactual Regret Minimization (CFR)** solver for Leduc Hold'em, written in plain Python with no dependencies.

It uses the same architecture as modern no-limit postflop solvers such as [postflop-solver](https://github.com/b-inary/postflop-solver) (the engine behind wasm-postflop) and shark: the game tree branches only on **public** information (actions and the board card). Private hands are carried as a vector at every node, not as separate branches. This project is a stepping stone toward a no-limit hold'em subgame solver.

## Leduc Hold'em

- A 6-card deck: J♠ J♥ Q♠ Q♥ K♠ K♥. Each player antes 1 and is dealt one private card.
- Two betting rounds with one public board card dealt between them.
- Fixed bet/raise size: 2 in round 1 and 4 in round 2, with at most 2 bets per round.
- Showdown: pairing the board wins, otherwise the higher card wins.

## How it works

**1. Build the public game tree once** (`build`)

A throwaway `State` (who acts, previous action, bet count, contributions) is passed down recursively. Each call returns one of three node types:

| Node | Stores |
|---|---|
| `actionNode` | acting player, legal actions, children, and per-hand `regrets` / `strategy_sum` |
| `chanceNode` | one child per possible board card |
| `terminalNode` | fold or showdown, contributions, board |

The tree has 186 action nodes, 5 chance nodes and 274 terminal nodes.

**2. Run CFR over the tree** (`cfr`), alternating the traversing player every iteration. Each call carries two reach vectors (one entry per hand):

- **Traverser's node:** regret matching gives the current strategy. Each action is evaluated, regrets are updated with `actionEV − nodeEV`, and the reach-weighted strategy is added to `strategy_sum`.
- **Opponent's node:** their current strategy narrows `oppReach` per hand on the way down. Child values are summed.
- **Chance node:** the dealt card is removed from both reach vectors (card removal), and the opponent's reach is scaled by ¼.
- **Terminal:** counterfactual value for every (my hand, opponent hand) pair, weighted by the opponent's reach.

**3. Measure exploitability** (`exploitability`): a best-response pass against the opponent's average strategy (`strategy_sum`, normalized), done once for each player.

## Results

The known game value of Leduc for the first player is **−0.0856** chips per hand.

| Iterations | Game value (avg strategy) | Exploitability (chips/hand) |
|---:|---:|---:|
| 10 | −0.4448 | 1.7772 |
| 100 | −0.1140 | 0.1914 |
| 1,000 | −0.0872 | 0.0236 |
| 5,000 | −0.0860 | 0.0059 |

Exploitability here is `BR(p0) + BR(p1)`, the total that two best-responders gain over the average strategies. It approaches 0 as the strategy approaches a Nash equilibrium.

Sample learned strategy, first player's opening action:

| Card | Bet | Check |
|---|---:|---:|
| J | 8% | 92% |
| Q | 74% | 26% |
| K | 76% | 24% |

## Run

```bash
python3 solver.py
```

Runs 1,000 iterations (about 10 seconds) and prints each player's best-response value and the total exploitability. It needs Python 3.9 or newer.

## Next steps

- Discounted CFR (DCFR) for faster convergence
- A river-only no-limit hold'em subgame: 1,326 combos, range inputs, and a sorted O(n log n) showdown evaluation
- A port to C++ and eventually WebAssembly
