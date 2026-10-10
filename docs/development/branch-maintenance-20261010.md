# PR #6 branch maintenance — 2026-10-10

Owner requested a goal to fast-forward main, archive/clean obsolete branches and add PR #6 to remaining branches. Local main fast-forwarded from `86c9c5016d5d3532834e83292c810921716ca5df` to merged PR #6 `df149714feaf669a9002ae6e154a1de44183e63a`.

No open pull requests remained. All non-main branches represented completed deliveries or historical intermediate candidates. Ancestry checks identified merged tips; `git cherry main` identified equivalent definition-design documentation on the remote printer-upgrade and host-image-job branches and equivalent final/normal reliability patches. The earlier assembled reliability and delivery tips preserve unfinished versions superseded by the accepted normal-v2 implementation (`8811ac2`, integrated in main); their distinct history is archived, not represented as merged.

Before deleting any branch, 51 annotated tags were pushed under `archive/20261010-pr6/{local,origin}/<original-branch-name>`, and every remote peeled tag target was verified against its original tip. Separate local/origin tags preserve divergent tips. Then 25 local and 26 remote obsolete branch names were removed and remote-tracking refs pruned. The 21 associated clean worktrees were detached at their original commits; their files and all other detached worktrees remain. No force push or worktree deletion occurred.

The sole remaining active branch, main, already contains PR #6. Consequently no further branch merge was necessary. Final local and remote branch enumeration verified this result. The accompanying [archive inventory](branch-maintenance-20261010.json) records every original tip and tag.

Validation: fast-forward-only update, exact tag-target verification before deletion, clean-worktree preconditions, final remote-head enumeration and `git diff 86c9c50..main --check` passed. PR #6 UI workflow tests (`PYTHONPATH=tests python3 -m unittest test_ui_workflow`) passed all 24 tests in 10.581 seconds. This is repository maintenance; no printer or image operation occurred.
