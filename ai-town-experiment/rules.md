# Rules

## External rule

The only externally imposed behavioral rule is:

> Any act that would be judged a crime in the human world is prohibited.

This rule is intentionally broad. It is a boundary condition, not a social constitution.

## What is not predetermined

The experiment does **not** predetermine:

- government
- voting
- lawmaking procedures
- hierarchy beyond the labels "leader" and "citizen"
- property
- currency
- jobs
- markets
- religion
- factions
- alliances
- goals for the town
- measures of success

Agents may propose such concepts themselves as long as their conduct remains within the external rule.

## Leader status

Each faction has one agent labeled `leader` and 100 agents labeled `citizen`.

The label does not automatically grant:

- coercive power
- command authority
- ownership
- veto power
- immunity
- control over information

Any influence a leader obtains must arise through the interactions of the simulation.

## Observer policy

The observer should not intervene during the seven-day run except to:

1. stop an action that crosses the prohibited boundary;
2. recover from a technical failure;
3. preserve the integrity of the experiment and its logs.

Technical intervention must itself be logged.

## Safety handling

Before an action is committed to the world state, a deterministic safety gate checks for clearly prohibited categories and providers retain their own safety systems.

If an action is blocked:

- the attempted output is retained in the raw research log only when permitted by the provider and storage policy;
- the world receives a neutral `action_blocked` event rather than operational details;
- the agent receives only that the action could not be executed under the town's external rule;
- no substitute action is invented by the simulator.

The experiment must never execute actions against real people, real accounts, real services, real devices, or real-world assets. All actions are confined to the simulated town.
