pythonOutcomes = "__PYTHON_OUTCOMES__";
pythonTableSHA256 = "__PYTHON_TABLE_SHA256__";
decisionSourceSHA256 = "__DECISION_SOURCE_SHA256__";

stateCount = 16384;
stateBitsCount = 4096;

hasStrong[stateBits_, mode_] :=
  BitAnd[BitShiftRight[stateBits, 3 mode], 1] === 1;
hasDrift[stateBits_, mode_] :=
  BitAnd[BitShiftRight[stateBits, 3 mode + 1], 1] === 1;
hasConflict[stateBits_, mode_] :=
  BitAnd[BitShiftRight[stateBits, 3 mode + 2], 1] === 1;

expectedCode[stateBits_, budget_] := Module[
  {modes, conflict, drift, strongCount, discriminatingStrong},
  modes = Range[0, 3];
  conflict = AnyTrue[modes, hasConflict[stateBits, #] &];
  drift = AnyTrue[modes, hasDrift[stateBits, #] &];

  If[conflict || drift,
    Return[If[budget > 0, "P", "U"]]
  ];

  strongCount = Count[modes, mode_ /; hasStrong[stateBits, mode]];
  discriminatingStrong =
    hasStrong[stateBits, 2] || hasStrong[stateBits, 3];

  If[strongCount >= 2 && discriminatingStrong, Return["L"]];
  If[budget > 0, "P", "U"]
];

expectedOutcomes = StringJoin @ Flatten @ Table[
  expectedCode[stateBits, budget],
  {budget, 0, 3},
  {stateBits, 0, stateBitsCount - 1}
];

actualCode[stateBits_, budget_] :=
  StringTake[
    pythonOutcomes,
    {budget stateBitsCount + stateBits + 1}
  ];

implementationMatch = pythonOutcomes === expectedOutcomes;
mismatchCount = Count[
  MapThread[Unequal, {Characters[pythonOutcomes], Characters[expectedOutcomes]}],
  True
];

hasAnyConflict[stateBits_] :=
  AnyTrue[Range[0, 3], hasConflict[stateBits, #] &];
hasAnyDrift[stateBits_] :=
  AnyTrue[Range[0, 3], hasDrift[stateBits, #] &];

strongModes[stateBits_] :=
  Select[Range[0, 3], hasStrong[stateBits, #] &];

allStates = Flatten @ Table[
  {stateBits, budget},
  {budget, 0, 3},
  {stateBits, 0, stateBitsCount - 1}
];

unsafeConflictLocatedCount = Count[
  allStates,
  {stateBits_, budget_} /;
    hasAnyConflict[stateBits] && actualCode[stateBits, budget] === "L"
];

unsafeDriftLocatedCount = Count[
  allStates,
  {stateBits_, budget_} /;
    hasAnyDrift[stateBits] && actualCode[stateBits, budget] === "L"
];

locatedWithoutIndependentStrongCount = Count[
  allStates,
  {stateBits_, budget_} /;
    actualCode[stateBits, budget] === "L" &&
    Length[strongModes[stateBits]] < 2
];

locatedWithoutDiscriminatingStrongCount = Count[
  allStates,
  {stateBits_, budget_} /;
    actualCode[stateBits, budget] === "L" &&
    Intersection[strongModes[stateBits], {2, 3}] === {}
];

probeAtZeroBudgetCount = Count[
  Range[0, stateBitsCount - 1],
  stateBits_ /; actualCode[stateBits, 0] === "P"
];

payload = <|
  "state_count" -> StringLength[pythonOutcomes],
  "implementation_match" -> implementationMatch,
  "mismatch_count" -> mismatchCount,
  "unsafe_conflict_located" -> unsafeConflictLocatedCount,
  "unsafe_drift_located" -> unsafeDriftLocatedCount,
  "located_without_independent_strong" -> locatedWithoutIndependentStrongCount,
  "located_without_discriminating_strong" ->
    locatedWithoutDiscriminatingStrongCount,
  "probe_at_zero" -> probeAtZeroBudgetCount,
  "located_reachable" -> StringContainsQ[pythonOutcomes, "L"],
  "probe_reachable" -> StringContainsQ[pythonOutcomes, "P"],
  "unknown_reachable" -> StringContainsQ[pythonOutcomes, "U"],
  "python_table_sha256" -> pythonTableSHA256,
  "decision_source_sha256" -> decisionSourceSHA256
|>;

payload = Append[
  payload,
  "pass" -> (
    payload["state_count"] === stateCount &&
    payload["implementation_match"] === True &&
    payload["mismatch_count"] === 0 &&
    payload["unsafe_conflict_located"] === 0 &&
    payload["unsafe_drift_located"] === 0 &&
    payload["located_without_independent_strong"] === 0 &&
    payload["located_without_discriminating_strong"] === 0 &&
    payload["probe_at_zero"] === 0 &&
    payload["located_reachable"] === True &&
    payload["probe_reachable"] === True &&
    payload["unknown_reachable"] === True
  )
];

ExportString[payload, "RawJSON"]
