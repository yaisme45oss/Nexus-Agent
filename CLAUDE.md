# Nexus-Agent

## Instagram skills (`/ig-*`)

`.claude/skills/ig-*` is the [instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill)
pack, vendored unchanged from upstream commit `d03c56b` (MIT, see
`.claude/skills/LICENSE.instagram-agent-skill`). To update, re-copy
`skills/ig-*` from upstream rather than editing these files in place.

**State lives in the repo, not in `~`.** Wherever a skill says
`~/.claude/instagram/` (voice.md, swipe.md, log.md, plan.md), use
`.claude/instagram/` at the root of this repo instead, and commit what the
skills write there. Cloud sessions start from a fresh container, so anything in
`~` is lost when the session ends.

**Voice first.** Every script, caption, comment, reply and DM must be written
from `.claude/instagram/voice.md`. While that file still has its
`STATUS: NOT FILLED IN YET` line, treat it as missing: ask the user for three of
their own reels or captions, write the profile from them, and delete the
status line before drafting anything in their voice.

Run the Python tools from the skill's own folder, for example
`python3 .claude/skills/ig-reel/hookscore.py hooks.txt`. They are standard
library only and make no network calls.
