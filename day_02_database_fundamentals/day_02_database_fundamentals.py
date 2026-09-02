# AI Problem Solving

## Intelligent Agents, Rational Agents, Environments, State, Actions, Goals and Utility

## 1. Artificial Intelligence and Problem Solving

Artificial Intelligence studies computational systems that can perceive information, reason about situations, make decisions, perform actions and, in many cases, learn from experience.

One of the most useful abstractions in AI is the **agent**.

An agent receives information from an environment through sensors or other input mechanisms, processes that information, chooses an action and affects the environment through actuators or other output mechanisms.

The basic interaction can be represented as:

```text
Environment
     |
     v
  Sensors
     |
     v
   Agent
     |
     v
 Actuators
     |
     v
Environment
```

The agent does not operate in isolation. Its behavior is meaningful only in relation to an environment and a task.

For AI problem solving, the important questions are:

* What does the agent perceive?
* What does the agent know?
* What states can exist?
* What actions are available?
* What happens after an action?
* What is the desired outcome?
* How should alternative outcomes be compared?
* What does it mean for the agent to behave rationally?

These questions lead directly to the concepts of intelligent agents, rationality, states, actions, goals, utility and search.

---

# 2. Intelligent Agents

An **agent** is an entity that perceives its environment and acts upon that environment.

A general agent cycle is:

```text
Perceive
   ↓
Interpret
   ↓
Decide
   ↓
Act
   ↓
Observe result
   ↓
Repeat
```

Examples include:

* a robot
* a self-driving vehicle
* a chess program
* a recommendation system
* a software automation system
* a navigation system
* a game-playing program

An agent may be physical or purely computational.

A physical robot can use cameras, microphones, lidar and other sensors. A software agent can receive information through APIs, databases, files, messages or user input.

---

# 3. Percepts

A **percept** is the information an agent receives from its environment at a particular point in time.

For a vehicle, a percept might contain:

```text
traffic light = red
speed = 20 km/h
pedestrian = detected
location = intersection
```

A percept sequence is the complete sequence of percepts received by an agent.

For example:

```text
t1: road clear
t2: pedestrian detected
t3: traffic light red
t4: obstacle detected
```

The agent's decision can depend on the current percept, the complete percept history, or an internal representation derived from that history.

---

# 4. Sensors

A **sensor** is a mechanism through which an agent obtains information from the environment.

Examples:

### Robot

```text
Camera
Lidar
Microphone
Touch sensor
Distance sensor
```

### Autonomous vehicle

```text
Camera
Radar
Lidar
GPS
Speed sensor
Inertial sensors
```

### Software agent

```text
API
Database
File system
User input
Network messages
Logs
```

The quality and availability of sensor information directly influence the agent's ability to make decisions.

---

# 5. Actuators

An **actuator** allows an agent to affect its environment.

Examples:

### Robot

```text
Motors
Robot arm
Gripper
Speaker
```

### Vehicle

```text
Steering
Brake
Accelerator
Indicators
```

### Software agent

```text
API request
Database update
Message
File modification
Command execution
```

Sensors provide information to the agent. Actuators allow the agent to produce effects in the environment.

---

# 6. Agent Function

The agent function provides an abstract mathematical description of the relationship between percept history and action.

It can be represented as:

```text
f(percept sequence) = action
```

For example:

```text
f([dirty]) = clean
f([obstacle]) = turn
f([danger]) = escape
```

The **agent function** is an abstract concept.

The **agent program** is the actual implementation of that function.

The **architecture** is the platform on which the program operates.

A useful distinction is therefore:

```text
Agent function
      ↓
Abstract behavior

Agent program
      ↓
Implementation

Architecture
      ↓
Computational platform
```

---

# 7. Rational Agents

A **rational agent** chooses the action that is expected to maximize its performance measure based on the information available to it.

Rationality does not mean that the agent always obtains the best actual result.

It means that the agent selects the action that is expected to produce the best result given its:

* percept sequence
* knowledge
* available actions
* environment
* performance measure
* computational limitations

Suppose an agent has two possible routes.

```text
Route A:
Expected performance = 85

Route B:
Expected performance = 70
```

Choosing Route A can be rational even if Route B eventually turns out to be faster.

The agent does not normally know the future with certainty.

Therefore:

```text
Rational decision ≠ guaranteed successful outcome
```

Rationality concerns the quality of the decision given the information available when the decision was made.

---

# 8. Rationality Is Not Omniscience

**Omniscience** would mean knowing the actual outcome of every possible action before acting.

Real agents are not normally omniscient.

Consider a navigation agent that chooses a route because historical information indicates that it is usually faster.

An unexpected accident then creates a large traffic delay.

The poor outcome does not automatically mean that the original decision was irrational.

The agent made its decision using the information available at that time.

Rationality is therefore based on expected consequences rather than perfect knowledge of future events.

---

# 9. Performance Measures

A **performance measure** specifies how the success of an agent's behavior is evaluated.

For a delivery robot, possible performance measures include:

* safety
* delivery accuracy
* delivery time
* energy consumption
* cost
* customer satisfaction

Different performance measures produce different rational behaviors.

For example, consider two routes:

```text
Route A:
10 minutes
high risk

Route B:
20 minutes
very low risk
```

If the performance measure strongly prioritizes safety, Route B may be rational.

If the performance measure strongly prioritizes speed and accepts greater risk, the decision may differ.

Therefore rationality cannot be defined independently of the performance measure.

---

# 10. PEAS

**PEAS** is a framework for specifying an agent's task environment.

```text
P = Performance measure
E = Environment
A = Actuators
S = Sensors
```

For an autonomous taxi:

## Performance

* safety
* travel time
* passenger comfort
* energy efficiency
* legal compliance

## Environment

* roads
* vehicles
* pedestrians
* traffic signals
* weather

## Actuators

* steering
* brake
* accelerator
* indicators

## Sensors

* cameras
* radar
* lidar
* GPS
* speed sensors

PEAS provides a structured way of defining what an agent is supposed to achieve and what it can perceive and control.

---

# 11. Task Environment Properties

AI environments can be classified according to several dimensions.

## Fully Observable vs Partially Observable

### Fully observable

The agent can obtain all information relevant to decision making from its percepts.

Chess is commonly treated as fully observable because the board position is visible to both players.

### Partially observable

Some relevant information is hidden, unavailable or uncertain.

Examples include:

* poker
* medical diagnosis
* driving in fog
* navigation behind obstacles
* financial decision making

A partially observable environment may require an internal state or belief state.

---

# 12. Deterministic vs Stochastic

A **deterministic environment** has predictable transitions.

If the current state and action are known:

```text
next state = completely determined
```

Formally:

```text
RESULT(state, action) = next state
```

A **stochastic environment** contains uncertainty.

The same action may produce different outcomes.

For example:

```text
Action: Move forward

Success       = 0.90
Slip          = 0.07
Obstacle      = 0.03
```

The agent must reason using probabilities.

A stochastic transition can be represented as:

```text
P(next_state | current_state, action)
```

---

# 13. Episodic vs Sequential

An **episodic environment** consists of relatively independent decisions.

For example, an image classification system may classify one image at a time.

The classification of one image does not necessarily affect the next image.

A **sequential environment** is one where current actions influence future states.

Examples:

* chess
* driving
* navigation
* robotics
* financial planning

Sequential environments require consideration of future consequences.

---

# 14. Static vs Dynamic

A **static environment** does not change while the agent is making a decision.

A **dynamic environment** can change while the agent is thinking.

Chess is relatively static during a player's turn.

Driving is highly dynamic.

A dynamic environment may require:

* rapid perception
* continuous state updates
* prediction
* real-time decisions
* adaptation

An action plan that was correct several seconds ago may no longer be appropriate after the environment changes.

---

# 15. Discrete vs Continuous

A **discrete environment** contains distinct states or actions.

Chess is largely discrete.

A **continuous environment** contains variables that can take values over continuous ranges.

Examples:

```text
Speed = 62.31 km/h
Steering angle = 13.7 degrees
Temperature = 27.43°C
```

Real systems often contain both discrete and continuous components.

For example:

```text
Discrete action:
Brake

Continuous parameter:
Brake pressure = 0.73
```

---

# 16. Single-Agent vs Multi-Agent

In a **single-agent environment**, the agent is the main decision maker.

Examples:

* solving a maze
* solving a puzzle

In a **multi-agent environment**, other agents can influence the result.

Examples:

* chess
* football
* autonomous traffic
* competitive markets

Other agents may be:

* cooperative
* competitive
* partially cooperative
* unpredictable

The presence of other decision makers significantly changes the problem because the agent must account for their possible actions.

---

# 17. Known vs Unknown Environments

In a **known environment**, the agent knows the relevant rules governing the environment.

In an **unknown environment**, the agent may not know:

* available actions
* action consequences
* transition probabilities
* risks
* relevant state relationships

The agent may therefore need to learn the environment model through interaction.

---

# 18. State

A **state** describes the condition of an environment at a particular point in time.

For a grid world:

```text
(row=1, column=1)
```

may represent the agent's current state.

A richer state might contain:

```text
position
battery
package status
obstacles
time
known information
```

The appropriate state representation depends on the problem.

The important principle is that the state should contain information relevant to future decision making.

---

# 19. State Representation

Suppose a vehicle's complete state contains:

```text
location
speed
fuel
engine temperature
weather
traffic
road condition
time
```

A route-planning problem may only need:

```text
location
```

This is an example of **state abstraction**.

A detailed state:

```text
location = A
speed = 60
fuel = 70
temperature = 85
weather = clear
traffic = moderate
```

An abstract state:

```text
location = A
```

Abstraction reduces computational complexity.

But excessive abstraction can remove information required for correct decisions.

The challenge is to retain distinctions that matter while eliminating irrelevant detail.

---

# 20. Actions

An **action** is something the agent can perform.

For a grid-world agent:

```text
UP
DOWN
LEFT
RIGHT
```

An action changes the state.

For example:

```text
Current state:
(1,1)

Action:
RIGHT

New state:
(1,2)
```

The relationship between actions and resulting states is described by the transition model.

---

# 21. Transition Model

The **transition model** describes what happens when an action is applied to a state.

In a deterministic environment:

```text
RESULT(state, action) = next_state
```

For example:

```text
RESULT((1,1), RIGHT) = (1,2)
```

In a stochastic environment, a transition model describes a probability distribution:

```text
P(next_state | state, action)
```

For example:

```text
P(A | state, action) = 0.8
P(B | state, action) = 0.2
```

The transition model is central to planning because the agent must predict the consequences of actions.

---

# 22. Goals

A **goal** describes a desired condition.

Suppose:

```text
Initial state = (0,0)
Goal = (4,4)
```

The agent must find actions that transform the initial state into a state satisfying the goal.

A goal is not the same as an action.

```text
Goal:
Reach the airport.

Action:
Drive east.
```

Another example:

```text
Goal:
Deliver package.

Actions:
Move
Pick up
Drive
Drop off
```

The goal specifies the desired outcome.

The action specifies a way of changing the state.

---

# 23. Goal Test

A **goal test** determines whether a state satisfies the goal.

For example:

```python
def goal_test(city):
    return city == "Delhi"
```

The goal test returns:

```text
True
```

when the desired condition is satisfied.

A goal test does not necessarily prescribe one specific path.

For example, if the goal is:

```text
Reach Delhi
```

then any valid route that reaches Delhi may satisfy the goal.

---

# 24. Problem Formulation

A classical AI search problem can be represented using:

1. Initial state
2. Actions
3. Transition model
4. Goal test
5. Path cost

For a route-planning problem:

```text
Initial state:
Lucknow

Actions:
Travel to connected cities

Transition model:
Move from one city to another

Goal:
Delhi

Path cost:
Distance, time, fuel or another chosen cost
```

Problem formulation converts a real-world objective into a formal computational problem.

---

# 25. State-Space Search

A **state-space graph** represents possible states and transitions.

For example:

```text
        A
       / \
      B   C
      |   |
      D   E
       \ /
        G
```

Here:

```text
Nodes = states
Edges = transitions/actions
```

The agent searches through this space to find a path from an initial state to a goal state.

A path is a sequence of states or actions.

For example:

```text
A → B → D → G
```

---

# 26. Search Tree vs State-Space Graph

A search tree may contain multiple nodes representing the same underlying state because the state can be reached through different paths.

Suppose:

```text
        A
       / \
      B   C
       \ /
        D
```

D can be reached through:

```text
A → B → D
```

or:

```text
A → C → D
```

A search tree can represent these as separate tree nodes.

A state-space graph represents D as one state with multiple incoming transitions.

This distinction is important when implementing graph search.

---

# 27. Path Cost

**Path cost** is the cumulative cost of reaching a state.

If individual actions have costs:

```text
4
3
7
2
```

then:

```text
Total path cost = 4 + 3 + 7 + 2
                = 16
```

The cost can represent:

* distance
* time
* money
* energy
* risk
* computation

The definition of optimality depends on what cost means.

A shortest path is not necessarily the safest path.

A cheapest path is not necessarily the fastest path.

---

# 28. Breadth-First Search

**Breadth-first search**, or BFS, expands the shallowest nodes first.

It uses a FIFO queue:

```text
First In
   ↓
First Out
```

Conceptually:

```text
A
|
+-- B
+-- C
    |
    +-- D
```

BFS explores level by level.

For a branching factor `b` and shallowest solution depth `d`, common complexity descriptions are:

```text
Time:
O(b^d)

Space:
O(b^d)
```

When every action has the same cost, BFS finds a shallowest solution and therefore an optimal solution with respect to the number of actions.

---

# 29. Depth-First Search

**Depth-first search**, or DFS, explores one branch as deeply as possible before backtracking.

It can be implemented using a stack.

Typical complexity:

```text
Time:
O(b^m)

Space:
O(bm)
```

where:

```text
b = branching factor
m = maximum depth
```

DFS is not generally optimal.

It can also fail to find a solution in certain infinite-depth or cyclic search spaces without appropriate controls.

Its major advantage is that it can use much less memory than breadth-first search in many situations.

---

# 30. Uniform-Cost Search

**Uniform-cost search**, or UCS, expands the node with the smallest accumulated path cost.

It is useful when actions have different costs.

Suppose:

```text
A → B = 2
A → C = 5
B → G = 10
C → G = 2
```

Then:

```text
A → B → G
cost = 12

A → C → G
cost = 7
```

UCS prefers:

```text
A → C → G
```

because it has lower total cost.

UCS therefore focuses on:

```text
g(n)
```

where `g(n)` is the cost from the initial state to node `n`.

---

# 31. Heuristics

A **heuristic function** provides an estimate of the remaining cost to a goal.

It is normally represented as:

```text
h(n)
```

For a grid-world problem, Manhattan distance is a common heuristic:

```text
h(n) =
|row_current - row_goal|
+
|column_current - column_goal|
```

A heuristic incorporates problem-specific knowledge into search.

Without a heuristic, a search algorithm may have to explore a large number of possibilities.

With a useful heuristic, the search can focus on promising states.

---

# 32. Admissible Heuristic

A heuristic is **admissible** if it never overestimates the true cheapest remaining cost.

Therefore:

```text
h(n) <= h*(n)
```

where:

```text
h(n)  = estimated cost
h*(n) = actual optimal remaining cost
```

For example, if the true remaining cost is 10:

```text
h(n) = 7
```

is admissible.

But:

```text
h(n) = 13
```

is not admissible.

Admissibility is important for the optimality of A* search.

---

# 33. Consistent Heuristic

A heuristic is **consistent** when it satisfies the triangle inequality:

```text
h(n) <= c(n,a,n') + h(n')
```

where:

```text
c(n,a,n')
```

is the cost of moving from `n` to `n'`.

Consistency is a stronger useful property than simple admissibility and is particularly important in graph-search implementations of A*.

---

# 34. Greedy Best-First Search

Greedy best-first search evaluates a node using:

```text
f(n) = h(n)
```

It focuses on estimated distance to the goal.

The advantage is that it can quickly move toward apparently promising states.

The disadvantage is that it ignores the cost already incurred.

A node can appear very close to the goal while having been reached through an extremely expensive path.

Greedy best-first search is therefore not generally optimal.

---

# 35. A* Search

A* combines path cost and heuristic estimate.

Its evaluation function is:

```text
f(n) = g(n) + h(n)
```

where:

```text
g(n) = cost from initial state to n
h(n) = estimated cost from n to goal
f(n) = estimated total solution cost through n
```

A* therefore balances:

```text
Cost already spent
```

with:

```text
Estimated remaining cost
```

A useful interpretation is:

```text
f(n)
=
past cost
+
estimated future cost
```

When the heuristic satisfies the appropriate conditions, A* can provide an optimal solution.

---

# 36. Goal-Based Agents

A **goal-based agent** explicitly considers goals when choosing actions.

For example:

```text
Current state:
(1,1)

Goal:
(3,3)
```

The agent selects actions that move it toward a goal state.

A goal-based agent is more flexible than a purely reflex-based system because it considers desired future states rather than reacting only to the current percept.

---

# 37. Simple Reflex Agents

A **simple reflex agent** selects actions based on the current percept.

A rule might be:

```text
IF dirty
THEN clean
```

Another:

```text
IF obstacle
THEN turn
```

Its basic structure is:

```text
Current percept
      ↓
Condition
      ↓
Action
```

It does not necessarily maintain an explicit model of the world.

Simple reflex agents are appropriate for situations where the current percept contains enough information to make a decision.

---

# 38. Model-Based Agents

A **model-based agent** maintains an internal representation of the environment.

This becomes useful when the environment is partially observable.

For example, a robot may remember:

```text
Previous location
Known obstacles
Previous actions
Battery level
Previously observed objects
```

The agent can combine new percepts with its internal state.

Conceptually:

```text
Current percept
       +
Previous internal state
       ↓
Updated internal state
       ↓
Decision
```

This allows the agent to reason about aspects of the environment that are not directly visible at the current moment.

---

# 39. Utility-Based Agents

A **utility-based agent** evaluates the desirability of possible outcomes.

A goal-based system asks:

```text
Does this state satisfy the goal?
```

A utility-based system asks:

```text
How desirable is this state compared with other possible states?
```

Suppose three routes all reach the destination:

```text
Route A = 20 minutes
Route B = 35 minutes
Route C = 50 minutes
```

A goal-based agent can classify all three as successful.

A utility-based agent can rank them:

```text
A > B > C
```

Utility becomes especially useful when multiple successful outcomes have different qualities.

---

# 40. Utility

A **utility function** represents preferences numerically.

A utility function may combine:

* safety
* time
* cost
* comfort
* energy
* reliability

For example:

```text
U =
0.5 × safety
+
0.2 × comfort
+
0.2 × speed
-
0.1 × cost
```

The exact formulation depends on the problem.

Higher utility normally represents a more preferred outcome.

Utility values should not automatically be interpreted as literal physical quantities.

If:

```text
U(A) = 100
U(B) = 50
```

the important point is that A is preferred to B under the model. It does not necessarily mean A is physically twice as good.

---

# 41. Goal vs Utility

Goals and utilities solve different problems.

A goal provides a desired condition.

```text
Reach Delhi.
```

Utility provides a preference over possible outcomes.

```text
Route A:
20 minutes
high safety
high utility

Route B:
40 minutes
medium safety
medium utility
```

Goal-based reasoning is useful when success can be clearly defined.

Utility-based reasoning becomes more important when:

* multiple outcomes satisfy the goal
* objectives conflict
* outcomes differ in quality
* uncertainty exists
* trade-offs are required

---

# 42. Multi-Objective Decision Making

Real-world intelligent agents often have multiple objectives.

For an autonomous vehicle:

```text
Safety
Speed
Comfort
Energy
Cost
Legality
```

These objectives may conflict.

A simple weighted utility model can be:

```text
U =
w1 × safety
+
w2 × speed
+
w3 × comfort
-
w4 × cost
```

The weights determine how strongly each objective influences the decision.

Changing the weights can change the rational action.

---

# 43. Decision Making Under Uncertainty

When an action can have several possible outcomes, the agent can use probability and utility together.

The expected utility of an action is:

```text
EU(action)
=
Σ P(outcome | action) × U(outcome)
```

Suppose:

```text
Action A

80% probability → utility 100
20% probability → utility 20
```

Then:

```text
EU(A)
=
0.8 × 100
+
0.2 × 20

=
80 + 4

=
84
```

Another action may have:

```text
EU(B) = 90
```

A rational utility-maximizing agent would prefer B under this model.

The decision rule can be written as:

```text
a* = argmax EU(a)
```

where `a*` is the selected action.

---

# 44. Belief State

In a partially observable environment, the agent may not know the exact current state.

It can instead maintain a **belief state**.

For example:

```text
State A → 0.60
State B → 0.30
State C → 0.10
```

The agent does not know exactly which state is true.

Instead, it maintains probabilities representing its current beliefs.

This is useful in:

* diagnosis
* robotics
* navigation
* games with hidden information
* uncertain environments

---

# 45. Internal State

An internal state stores information that is not necessarily present in the current percept.

Suppose a robot currently sees:

```text
Door
```

Its internal state may contain:

```text
The door was previously open.
The robot is carrying a package.
The destination is Room 4.
The battery is low.
```

This information can affect its decision.

Internal state is particularly important when current observations do not provide a complete description of the environment.

---

# 46. Rationality and Bounded Rationality

A theoretically perfect agent could attempt to compute the optimal action with unlimited resources.

Real systems have limitations:

* limited time
* limited memory
* limited processing power
* incomplete information
* imperfect models

This produces **bounded rationality**.

An agent may therefore select the best action it can compute within its resource limitations.

Chess provides a clear example.

A chess engine cannot normally evaluate every possible future game sequence.

Instead, it uses:

* search
* heuristics
* evaluation functions
* pruning
* learned knowledge
* time limits

The resulting behavior can still be highly rational.

---

# 47. Autonomy

An agent is autonomous to the extent that its behavior is determined by its own experience rather than being completely controlled by its designer.

A completely fixed rule system has limited autonomy.

A learning agent can modify its behavior using experience.

Autonomy does not mean that the agent receives no external information.

An autonomous agent can still use:

* sensors
* instructions
* models
* policies
* external information

The important distinction is how much of its behavior is generated from accumulated experience and internal decision processes.

---

# 48. Learning Agents

A **learning agent** improves its behavior through experience.

A classical learning-agent architecture can contain:

### Performance element

Chooses actions.

### Learning element

Modifies the performance element.

### Critic

Evaluates behavior.

### Problem generator

Encourages exploration and useful experiences.

The basic interaction is:

```text
Environment
     ↓
Experience
     ↓
Critic
     ↓
Learning element
     ↓
Performance element
     ↓
Action
     ↓
Environment
```

Learning allows an agent to adapt rather than relying entirely on predefined behavior.

---

# 49. Exploration and Exploitation

A learning agent faces a fundamental trade-off.

### Exploration

Try actions to gain information.

### Exploitation

Use actions that are already believed to be good.

If the agent only exploits:

```text
It may never discover better actions.
```

If the agent explores excessively:

```text
It may sacrifice performance unnecessarily.
```

This trade-off is important in:

* reinforcement learning
* recommendation systems
* online optimization
* adaptive systems
* autonomous decision making

A common mechanism is epsilon-greedy selection.

With probability `ε`, the agent explores.

Otherwise, it chooses the currently highest-valued action.

---

# 50. Policy

A **policy** specifies what action should be taken in a particular state or observation.

It can be represented as:

```text
π(s) = action
```

For example:

```text
π(A) = RIGHT
π(B) = DOWN
π(C) = LEFT
```

An individual action is one decision.

A policy is a rule that determines decisions across states.

The distinction is important in sequential decision making and reinforcement learning.

---

# 51. Search vs Decision Making

Classical search asks:

```text
Which sequence of actions leads to a goal?
```

Decision theory asks:

```text
Which action or strategy is most desirable given uncertainty
and preferences?
```

These ideas can be combined.

A navigation system may search for possible routes while considering:

```text
distance
traffic
time
fuel
safety
uncertainty
```

The problem is therefore not simply:

```text
Find any path.
```

It becomes:

```text
Find or select a path that provides the best expected result
according to the agent's objectives.
```

---

# 52. Path and Plan

A **path** is a sequence of states through a state space.

A **plan** is generally a sequence of actions intended to accomplish a goal.

For example:

```text
Initial:
Home

Goal:
Airport

Plan:

1. walk to station
2. board train
3. travel
4. exit train
5. take taxi
6. reach airport
```

In a deterministic environment with a known model, the result of a plan may be predictable.

In a stochastic environment, the same plan may lead to different possible outcomes.

---

# 53. Cumulative Utility

In sequential environments, an agent may care about utility accumulated across multiple steps.

A simple cumulative model is:

```text
U_total = R1 + R2 + R3 + ... + Rn
```

A discounted model is:

```text
U_total =
R1
+ γR2
+ γ²R3
+ ...
```

where:

```text
0 ≤ γ ≤ 1
```

The parameter `γ` is a discount factor.

When:

```text
γ = 1
```

future rewards are not discounted.

When `γ` is smaller, future rewards have less influence compared with immediate rewards.

This becomes important when actions have long-term consequences.

---

# 54. Conflicting Goals

An agent may have goals that conflict.

For example:

```text
Goal 1:
Minimize travel time.

Goal 2:
Maximize safety.
```

A very fast route may be less safe.

A very safe route may take considerably longer.

A utility function can encode this trade-off:

```text
U =
0.4 × speed
+
0.6 × safety
```

The weights indicate the relative importance of the objectives.

This is one reason utility-based agents are more expressive than simple goal-based agents.

---

# 55. Information as a Decision

An intelligent agent may decide to gather information before taking an action.

Suppose a robot is uncertain about which route is safer.

It can:

```text
Act immediately
```

or:

```text
Inspect the environment first
```

Inspection has a cost:

* time
* energy
* computation
* risk

But it can also have information value.

The relevant question becomes:

```text
Is the expected value of additional information greater than
the cost of obtaining it?
```

This turns information gathering itself into a decision problem.

---

# 56. Complete Agent Decision Pipeline

A generalized intelligent-agent decision process can be represented as:

```text
1. Perception
      ↓
2. State estimation
      ↓
3. Goal identification
      ↓
4. Action generation
      ↓
5. Prediction
      ↓
6. Evaluation
      ↓
7. Decision
      ↓
8. Execution
      ↓
9. Feedback
      ↓
10. State/model update
      ↓
Repeat
```

Each stage addresses a different aspect of intelligent behavior.

### Perception

What information is available?

### State estimation

What does the agent believe the current state is?

### Goal identification

What condition should be achieved?

### Action generation

What can the agent do?

### Prediction

What might happen after each action?

### Evaluation

How desirable or costly are the possible outcomes?

### Decision

Which action is rational according to the chosen criterion?

### Execution

Perform the selected action.

### Feedback

Observe what actually happened.

### Update

Revise internal knowledge or state.

---

# 57. Delivery Robot Example

Consider a delivery robot.

## State

The state may include:

```text
position
battery
package status
time
known obstacles
```

## Actions

```text
move
recharge
pick up
drop off
wait
```

## Goal

```text
Deliver the package.
```

## Utility

The robot may prefer:

```text
safe delivery
short delivery time
low energy consumption
low cost
```

## Environment

The environment may contain:

```text
roads
people
obstacles
other robots
weather
```

## Decision process

```text
Perceive environment
        ↓
Estimate current state
        ↓
Identify goal
        ↓
Generate possible actions
        ↓
Predict consequences
        ↓
Calculate costs/utilities
        ↓
Choose rational action
        ↓
Execute
        ↓
Observe result
        ↓
Update state
```

This example connects the central concepts into one agent model.

---

# 58. Central Relationships

The concepts are closely connected.

## State

Describes the current relevant condition.

## Action

Changes the state.

## Transition model

Describes how actions change states.

## Goal

Defines a desired state or condition.

## Search

Finds sequences of actions that can reach a goal.

## Path cost

Measures the cumulative cost of a sequence of actions.

## Heuristic

Estimates the remaining cost to guide search.

## Utility

Measures preference among possible outcomes.

## Rationality

Selects the action expected to provide the best performance according to available information.

## Environment

Determines what the agent can perceive and how its actions affect the world.

## Agent architecture

Determines how perception, state, goals, utility, learning and action selection are implemented.

---

# 59. Core Mathematical Vocabulary

Several mathematical expressions capture the basic ideas.

### Agent function

```text
f(percept sequence) = action
```

### Deterministic transition

```text
RESULT(state, action) = next_state
```

### Stochastic transition

```text
P(next_state | state, action)
```

### Heuristic

```text
h(n)
```

### Path cost

```text
g(n)
```

### A* evaluation

```text
f(n) = g(n) + h(n)
```

### Expected utility

```text
EU(a)
=
Σ P(outcome | a) U(outcome)
```

### Rational decision

```text
a* = argmax EU(a)
```

### Policy

```text
π(s) = action
```

### Discounted cumulative reward

```text
G =
R1
+ γR2
+ γ²R3
+ ...
```

---

# 60. Conceptual Comparison

| Concept             | Central Question                                       |
| ------------------- | ------------------------------------------------------ |
| Agent               | Who is making decisions?                               |
| Environment         | Where does the agent operate?                          |
| Percept             | What information does the agent receive?               |
| Sensor              | How does the agent receive information?                |
| Actuator            | How does the agent affect the environment?             |
| State               | What condition is the world currently in?              |
| Action              | What can the agent do?                                 |
| Transition model    | What happens after an action?                          |
| Goal                | What condition is desired?                             |
| Goal test           | Has the desired condition been achieved?               |
| Path                | What sequence of states was followed?                  |
| Path cost           | What did the sequence cost?                            |
| Search              | How can possible solutions be explored?                |
| Heuristic           | Which possibilities appear promising?                  |
| Utility             | How desirable is an outcome?                           |
| Rationality         | Which action is expected to perform best?              |
| Policy              | What action should be taken in each state?             |
| Belief state        | What does the agent believe the hidden state might be? |
| Learning            | How can the agent improve from experience?             |
| Performance measure | How is behavior evaluated?                             |

---

# 61. The Complete AI Problem-Solving Model

The complete conceptual model can be expressed as:

```text
                         ENVIRONMENT
                              |
                              v
                           PERCEPT
                              |
                              v
                            AGENT
                              |
                +-------------+-------------+
                |                           |
                v                           v
          CURRENT STATE                    GOAL
                |                           |
                +-------------+-------------+
                              |
                              v
                           ACTIONS
                              |
                              v
                       TRANSITION MODEL
                              |
                              v
                      POSSIBLE OUTCOMES
                              |
                              v
                       COST / UTILITY
                              |
                              v
                    RATIONAL DECISION
                              |
                              v
                            ACTION
                              |
                              v
                         ENVIRONMENT
                              |
                              v
                       NEW PERCEPT
                              |
                              v
                           REPEAT
```

The central idea is that an intelligent agent does not simply execute arbitrary actions. It operates within an environment, receives percepts, maintains or estimates a state, considers available actions, predicts their consequences, evaluates those consequences against goals or utilities, selects an action according to a rational decision criterion, and then observes the resulting environment.

State provides the representation of the current situation.

Actions provide mechanisms for changing that situation.

Goals define desired conditions.

Search provides methods for discovering action sequences that reach those conditions.

Costs provide a way to compare the resources required by alternative solutions.

Utility provides a richer representation of preference when successful outcomes differ in quality or when objectives conflict.

Rationality connects all of these elements by defining how an agent should select actions given its information, objectives, available actions and limitations.
