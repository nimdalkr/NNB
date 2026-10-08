# NNB — NewNimdalBot

Locutus-based successor to Nimdal. Fork: https://github.com/nimdalkr/NNB

The upstream reference is `bmnielsen/Locutus@4e96da0b7e31831ee97aaef153b2bef977a235e1`.
The pinned upstream baseline, original DLL and `Locutus.json` are preserved. The working tree now contains explicit, optional editor hooks; it must not be described as unmodified Locutus. The original README and licenses remain in place.
The local strategy editor, replay evidence retrieval and nine current-pool terrain caches are ready. This is **not yet a verified Remastered game integration or an improved playing policy**.

## Open the editor

```powershell
.\scripts\build-editor.ps1
.\scripts\start-editor.ps1
```

Open [NNB strategy workshop](http://127.0.0.1:8830/). It runs locally using Python's standard library and browser JavaScript, matching the existing local C++/replay workflow without a cloud service or login. Copy the read-only baseline to edit opening order, per-matchup selection, 18 operating settings and nine kinds of conditional adjustment. Korean pickers support common units, buildings, counts and locations; native command strings remain available for advanced editing.

The editor writes profiles and creates **new artifact folders** with a DLL, configuration and verified map caches. It never launches a game. Turning the profile off stages the preserved pure DLL and original configuration. [Editor behavior, scope and validation](reports/EDITOR.md) documents the actual runtime connection and what is not implemented.

[Native judgments and scouting inference](reports/JUDGMENTS.md) now expose the existing operating defaults, eight active recognition branches and prepared response templates. Opening names and steps have Korean explanations and structured editing. Recognition thresholds are opt-in editor settings with the pinned defaults preserved; 156,000 synthetic recognition/update comparisons match the original. Sensor collection and gameplay are outside this comparison.

[Cross-system review](reports/EDITOR-SAFETY.md) shows affected production, economy, scouting, combat and placement; blocks known prerequisite/parser/priority conflicts; previews coupled prerequisite repairs; and preserves previous saved revisions. Both the UI and staging API enforce the static checks. Generated candidates retain the exact profile and review report and remain explicitly unverified for gameplay. The native parser's own-race setting semantics and integer/double serialization are preserved.

## Build and verify

Requires Windows, Visual Studio 2022 C++ Build Tools, SDK 10.0.26100.0, CMake, Python 3.11+.

```powershell
$stage = .\scripts\build-baseline.ps1
cmake -S tools/native-check -B build/native-check -A Win32
cmake --build build/native-check --config Release
.\build\native-check\Release\nnb-native-smoke.exe (Join-Path $stage NNB.dll)
python -m unittest discover -s tools -p test_*.py -v
```

The baseline script archives the pinned upstream commit into a new, isolated build folder before compiling. It never compiles the edited working tree as a baseline. The DLL is written to `artifacts/baseline-<timestamp>/NNB.dll`; the first successful baseline initializes `artifacts/upstream/`, and subsequent builds preserve it. Build artifacts are not distributed.
The smoke check tests loading, exports, factory creation and destruction. It deliberately does not call `onStart` or run a game. Retargeting the old solution to v143 requires no strategy-source edits. Compiler warnings remain, including a reference-to-temporary warning in upstream `SquadData.cpp`; a successful build is not gameplay validation.

## Import the existing expert collection

```powershell
python tools/corpus.py import --source-root <existing-StardustRemastered-directory>
python tools/corpus.py find --map-hash 12917b98ef6ee4f4755d036b5f6f631b368519a6 --matchup pvz --opening NineGateExpand --frame 4000 --workers 18 --bases 2
python tools/map_preflight.py --runtime artifacts/baseline-<timestamp>
```

All 1,645 collected replays are accepted as the user's **2500+ collection**. No rating revalidation, opponent-rating inference or MMR filter is applied. Technical issues remain visible in the inventory and do not erase games. Replay hashes establish identity; state-cache errors indicate whether extracted observations can support a change.

Inputs are read-only. Indexes, replay paths, state data and machine paths stay under ignored `data/`. Neither raw replays nor map assets are published. Reimport after changing source files.

Case retrieval requires the exact observed map hash, matchup and opening classification. Optional start coordinates require the same spawn. Situation matching compares the requested worker, army-resource, base, resource and observed enemy pressure values using explicit scales. It is a retrieval aid, not a policy, rating, intent detector or victory probability. The output provides the player's observed situation and following build observations, with replay identity for manual verification of movement and micro. Opponent hidden states are not used as player knowledge.

The original replay-level analysis/holdout split is preserved for both PvP perspectives. Holdout games are never returned for policy design. Default cases require the existing independent first-eight-minute comparison; `--provisional` explicitly permits other technically clean state extracts. No match returns an empty list, not a substituted map or build. Opening counts have 48-frame sampling resolution and do not prove exact command order or intention. Movement through mineral gaps must be checked at unit/command resolution before becoming a micro rule.

## Current maps and integration status

The locally collected pool contains Aiolos 1.0b, Attitude SE 2.1, Backrooms 1.1, Colorless Fate 1.1, KnockOut 1.4, Octagon SE 2.0, Odyssey:RE 2.0, Radeon 1.2 and Fighting Spirit 1.4. Each CHK is checked against its existing census SHA256; exact observed game hashes remain in the local map manifest. This matches the community [2026 Season 2 map listing](https://liquipedia.net/starcraft/Ladder/Maps); native ladder assets locally corroborate seven maps, and match evidence corroborates Aiolos, Radeon and Odyssey. The listing is not an official Blizzard announcement and should be refreshed when a new season is observed.

Locutus's bundled BWTA removes online map analysis. `BWTA::analyze()` requires `bwapi-data/BWTA2/<mapHash>.bwta`, version 6; without it `onStart` stops. **All nine exact-map caches have now been generated with the full BWTA 2.2 analyzer and checked using the original Locutus cache loader.** Source map identity, exact starting depot anchors and start-to-start ground connectivity passed. The editor stages these caches after checking their recorded hashes. The earlier missing-cache blocker in the initial baseline report is resolved; that historical report remains unchanged.

[Terrain results and reproduction](reports/MAPS.md) contain the map table, pinned dependencies, exact CHK start-anchor correction and remaining geometry limits. Current local ladder/replay versions are used; a newer tournament map revision is not silently substituted.

Before gameplay: test native `onStart`/`onFrame`, placement, unit-size pathing and command transport offline. Locutus also couples strategy, scouting, placement and combat; replacing the foundation does not remove those dependencies. The prior Remastered bridge is not assumed compatible just because the DLL factory loads.

## Improvement acceptance

Keep the upstream baseline reproducible. For each candidate, cite matching map/build/situation replay frames, distinguish observed action from inferred purpose, change one behavior, and check construction/production/scouting/combat together. Compare against baseline on the same map and spawn before separate holdout evaluation. Only measured improvement is promoted. No online ladder restart is authorized by this setup; the user's stopped trial and current replay viewing remain untouched.

Current user targets remain PvZ gateway-first, PvP 10/12 and PvT 23 Nexus. They are future policy constraints; the untouched Locutus baseline has **not** been silently configured to use them. APM throttling is not transplanted into NNB. Final rating and matchup skill still require real game evidence.
