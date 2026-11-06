# Hero avatar: production plan

**Goal:** an outstanding avatar that looks real while dancing. The look is set out in [AVATAR_BRIEF.md](AVATAR_BRIEF.md). Claude runs the project. The owner handles logins and payments.

## Tool choice: MetaHuman, not Character Creator

| | MetaHuman (Unreal Engine 5.7+) | Character Creator 4/5 |
|---|---|---|
| Runs on this Mac (M3 Pro, 36 GB) | yes; the Creator plugin is on macOS since 5.7 | no; Windows only, and it won't run in Parallels or VMware |
| Realism | best available: scan-based faces, strand grooms | good |
| Price | free under $1M/yr revenue | $299 plus assets |
| Use outside Unreal | allowed since June 2025 | allowed |
| Face for the web | joint-driven face; ARKit shapes must be baked out, which needs a plugin or our own script | ARKit and CC shapes export directly |

**Decision:** MetaHuman. The main extra work is baking the face out as shapes and converting the hair to cards.

## Pipeline

1. **Design in MetaHuman Creator.** Face, skin, curly hair and make-up, in Unreal Engine on this Mac.
2. **Export from Unreal.**
   - **Skeleton and meshes:** the body skeleton and meshes as FBX.
   - **Face:** baked into ARKit 52 shapes, plus extra shapes from the face rig: tongue out, up and sideways; one-eye wink; laugh.
   - **Hair:** the groom exported as hair cards.
3. **Build in Blender** with scripts in `scripts/blender/`.
   - **Skeleton:** map the MetaHuman bones to the Mixamo names our dances use.
   - **Physics bones:** add spring chains for curls, the ponytail, earrings, chains, fringe and the joggers.
   - **Weight:** cut the triangle count down to the budget.
   - **Output:** GLB with compressed textures.
4. **Outfits.**
   - **Joggers and crop top:** ready-made assets from Fab.
   - **Stage costume:** bought from Fab or CGTrader, or commissioned. Each is fitted to the body and gets spring chains.
5. **Page work in `index.html`:**
   - GLB loading;
   - expression performer;
   - hand poses;
   - new spring kinds;
   - skin, hair, eye and glitter materials;
   - outfit switching by scene.

## First milestone: a test run

Before any custom design, a stock MetaHuman preset goes through the whole pipeline into the page, dancing with springs and a few expressions. This proves the export, bone mapping, face shapes, file size and frame rate early. After that, the design work begins.

## What the owner provides

- **Browser access:**
  - **Claude in Chrome:** install the extension, then run `/chrome` in Claude Code and enable it. This lets Claude use your logged-in browser.
  - **Your part:** logins and payments; Claude asks before each one.
- **Epic Games account:** sign in to the Epic Games Launcher, which is needed to download Unreal Engine.
- **Screen access:** allow screen recording for the terminal or VS Code, so Claude can see the Unreal editor with `screencapture`.

## Status

| Step | State |
|---|---|
| Blender 4.5 LTS, Epic Games Launcher | installed (Homebrew) |
| Unreal Engine 5.7+ | needs Epic sign-in |
| Test run | not started |
