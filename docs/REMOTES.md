# GitLab and GitHub

**Best setup for this project: GitLab stays the working copy; GitHub is a public push mirror of GitLab.** Do not invert that (do not make GitLab a mirror of GitHub) unless you move all merge requests to GitHub.

## Why this way

- Day-to-day work already lands on GitLab (including Cursor merges).
- GitHub is the copy you can make **public** so other people clone without a GitLab invite.
- One history, two hosts. After push mirroring is on, a merge on GitLab updates GitHub.

GitHub as the mirror of GitLab is the usual pattern when GitLab is where you merge. GitLab as a mirror of GitHub only helps if GitHub is where you actually work.

## One-time: push mirror

On GitLab: **Settings → Repository → Mirroring repositories**

1. URL: `https://github.com/quintus-lab/worklog.git`
2. Direction: **Push**
3. Username: your GitHub username
4. Password: a GitHub fine-grained PAT with **Contents: Read and write** on `quintus-lab/worklog`
5. Tick **Only protected branches**. `main` is protected, so only `main` goes to GitHub. Cursor topic branches stay on private GitLab.
6. Save, then **Update now**

If GitHub lags, the mirror may have failed. Check that page, or push `main` to both remotes once.

## Cursor (do not dump agent leftovers onto GitHub)

Cursor Cloud Agents / background jobs create `cursor/...` branches and a `.cursor/` folder. If GitLab mirrors every branch, those show up on public GitHub.

This repo is set so that does not happen:

- GitLab push mirror is **only protected branches** (`main`).
- `.cursor/` and `worklog-windows-*.zip` are gitignored.
- `.cursorrules` tells Cursor not to commit those files or push topic branches to GitHub.

When you use Cursor:

1. Open the **GitLab** copy, not the public GitHub copy. If Cloud Agents are attached to GitHub, they will push `cursor/...` straight to the public repo and skip the mirror filter.
2. Let it work on a topic branch. Review, merge into `main` on GitLab.
3. Delete the `cursor/...` branch after merge (GitLab: Merge request → Delete source branch).
4. Do not "sync all branches" or add a second remote to GitHub from the Cursor agent.

## Going public on GitHub

Before you click **Change repository visibility → Public**:

1. Confirm live notes are **not** in git. This repo gitignores `data/worklog.db`, `data/credentials.json`, `data/.session_secret`, Excel files, and `data/backups/`.
2. Fresh clones get an empty `data/` folder. `./setup.sh` (or `windows\setup.ps1`) creates the venv and loads **fictional** demo notes via `scripts/seed_demo.py`.
3. Demo logins are `admin` / `changeme` and `viewer` / `changeme`. Change them on any machine that is not a demo.
4. Keep GitLab private if you want a private place to try risky branches. The public GitHub copy should only receive `main` after you are happy with it.

Your real notes, if any, belong in a backup **outside** this repository (for example a folder under your home directory). Do not commit them so they can ride the mirror onto a public GitHub repo.
