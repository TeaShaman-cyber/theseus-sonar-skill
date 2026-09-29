modes = {"LITERAL", "SEMANTIC", "FUNCTIONAL", "RELATIONAL"};
modeStates = Tuples[{False, True}, 3];
budgets = Range[0, 3];

(* Each per-mode state is {hasStrong, hasDrift, hasConflict}.
   This is the exact information the Python policy uses after receipt
   multiplicity is collapsed by presence/set semantics. *)
states = Flatten[
  Table[
    {AssociationThread[modes -> state], budget},
    {state, Tuples[modeStates, Length[modes]]},
    {budget, budgets}
  ],
  1
];

decide[{observed_, budget_}] := Module[
  {values, hasConflict, hasDrift, strongModes, hasDiscriminatingStrong},
  values = Values[observed];
  hasConflict = AnyTrue[values, #[[3]] === True &];
  hasDrift = AnyTrue[values, #[[2]] === True &];

  If[hasConflict,
    Return[If[budget > 0, "PROBE", "UNKNOWN"]]
  ];

  If[hasDrift,
    Return[If[budget > 0, "PROBE", "UNKNOWN"]]
  ];

  strongModes = Keys @ Select[observed, #[[1]] === True &];
  hasDiscriminatingStrong =
    Length[Intersection[strongModes, {"FUNCTIONAL", "RELATIONAL"}]] > 0;

  If[Length[strongModes] >= 2 && hasDiscriminatingStrong,
    Return["READY"]
  ];

  If[budget > 0, "PROBE", "UNKNOWN"]
];

totalDecisionFunctionQ =
  AllTrue[states, MemberQ[{"READY", "PROBE", "UNKNOWN"}, decide[#]] &];

unsafeConflictReadyCount = Count[
  states,
  state_ /;
    AnyTrue[Values[state[[1]]], #[[3]] === True &] &&
    decide[state] === "READY"
];

unsafeDriftReadyCount = Count[
  states,
  state_ /;
    AnyTrue[Values[state[[1]]], #[[2]] === True &] &&
    decide[state] === "READY"
];

readyWithoutIndependentStrongCount = Count[
  states,
  state_ /; Module[{strongModes},
    If[decide[state] =!= "READY", Return[False]];
    strongModes = Keys @ Select[state[[1]], #[[1]] === True &];
    Length[strongModes] < 2
  ]
];

readyWithoutDiscriminatingStrongCount = Count[
  states,
  state_ /; Module[{strongModes},
    If[decide[state] =!= "READY", Return[False]];
    strongModes = Keys @ Select[state[[1]], #[[1]] === True &];
    Intersection[strongModes, {"FUNCTIONAL", "RELATIONAL"}] === {}
  ]
];

probeAtZeroBudgetCount = Count[
  states,
  state_ /; state[[2]] === 0 && decide[state] === "PROBE"
];

payload = <|
  "state_count" -> Length[states],
  "total_decision_function" -> totalDecisionFunctionQ,
  "unsafe_conflict_ready" -> unsafeConflictReadyCount,
  "unsafe_drift_ready" -> unsafeDriftReadyCount,
  "ready_without_independent_strong" -> readyWithoutIndependentStrongCount,
  "ready_without_discriminating_strong" -> readyWithoutDiscriminatingStrongCount,
  "probe_at_zero" -> probeAtZeroBudgetCount,
  "ready_reachable" -> AnyTrue[states, decide[#] === "READY" &],
  "probe_reachable" -> AnyTrue[states, decide[#] === "PROBE" &],
  "unknown_reachable" -> AnyTrue[states, decide[#] === "UNKNOWN" &]
|>;

payload = Append[
  payload,
  "pass" -> (
    payload["state_count"] === 16384 &&
    payload["total_decision_function"] === True &&
    payload["unsafe_conflict_ready"] === 0 &&
    payload["unsafe_drift_ready"] === 0 &&
    payload["ready_without_independent_strong"] === 0 &&
    payload["ready_without_discriminating_strong"] === 0 &&
    payload["probe_at_zero"] === 0 &&
    payload["ready_reachable"] === True &&
    payload["probe_reachable"] === True &&
    payload["unknown_reachable"] === True
  )
];

ExportString[payload, "RawJSON"]
