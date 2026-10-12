# KohaRoute

Waste & recycling pickup route planner for councils and community groups.

- **Backend:** Python (`backend/`)
- **Frontend:** React (`frontend/`)

This README explains how to get the code, set up your own branch, and send your work to `main` with a Pull Request. Follow it in order the first time.

## Folder structure

```
koharoute/
├── README.md
├── .gitignore
├── backend/     ← Python code
└── frontend/    ← React code
```

Backend work goes in `backend/`, frontend work goes in `frontend/`. Nothing else at the top level.

> You need **Git** installed and a **GitHub account**, and you must have **accepted the invitation** to this repo (check your email for "invited you to collaborate").
> Run every command below in a terminal. In VS Code: **Terminal → New Terminal**. Windows users can also use PowerShell; Mac users can use the Terminal app.

---

## 1. Get the code (git clone)

You only do this **once**.

### 1.1 Go to the folder where you want the project

Pick a normal folder, for example `Documents` or a `Projects` folder. **Don't** use a OneDrive, iCloud Drive, Google Drive or Dropbox folder; syncing apps break Git.

`cd` means "change directory" (move into a folder).

**Windows (PowerShell)**

```powershell
cd ~\Documents
mkdir Projects        # only if the folder doesn't exist yet
cd Projects
pwd                   # shows where you are now
```

**Mac (Terminal)**

```bash
cd ~/Documents
mkdir Projects        # only if the folder doesn't exist yet
cd Projects
pwd                   # shows where you are now
```

Tip: in VS Code you can also do **File → Open Folder**, pick the folder, then open **Terminal → New Terminal**. The terminal starts inside that folder.

### 1.2 Copy the repository URL

1. Open the repo page on GitHub.
2. Click the green **Code** button.
3. Make sure **HTTPS** is selected and click the copy icon. It looks like:
   `https://github.com/osy0602/KohaRoute`

### 1.3 Clone

```bash
git clone https://github.com/osy0602/KohaRoute
```

This creates a new folder called `koharoute` with all the code inside. Move into it and open it in VS Code:

```bash
cd koharoute
code .
```

If a browser window opens asking you to sign in to GitHub, sign in and approve. That's normal the first time.

Check it worked:

```bash
git status
```

You should see `On branch main`.

---

## 2. Switch to your own branch

Every team member has **one personal branch** for the whole project. You do all your work there.

**Your branch already exists.** I created one for each member on GitHub, so you don't create anything; you just switch to it.

### 2.1 Branch names

```
koharoute_chaw
koharoute_daniel
koharoute_keen
koharoute_seyoung
```

 You can also see all branches on the GitHub repo page: click the **main** dropdown button above the file list.

### 2.2 Switch to it (once, right after cloning)

```bash
git fetch origin
git switch koharoute_<yourname>
```

| Command | What it does |
|---|---|
| `git fetch origin` | Download the latest list of branches from GitHub |
| `git switch koharoute_<yourname>` | Move onto your branch. The first time, Git makes a local copy of it linked to the one on GitHub, so later `git push` and `git pull` just work |

You should see: `branch 'koharoute_seyoung' set up to track 'origin/koharoute_seyoung'`.

**VS Code alternative:** click the branch name in the **bottom-left corner** → pick **origin/koharoute_seyoung** from the list. VS Code switches you onto your branch.

> Got `invalid reference` or `did not match any file(s) known to git`? Check the spelling (all lowercase, `_` not `-`) and run `git fetch origin` again. Still nothing? Ask Seyoung to check the branch exists.

### 2.3 Check which branch you're on

Look at the **bottom-left corner of VS Code**, or run:

```bash
git branch
```

The branch with `*` next to it is the one you're on. **Before you start coding, always check it says your branch, not `main`.**

---

## 3. Your branch vs `main`

### Your branch (`koharoute_<yourname>`)

- **Your own workspace.** Only you commit and push here.
- Work in progress is fine: half-finished code, experiments, many small commits.
- Nothing you do here affects anyone else.
- You keep using the **same branch** for the whole project. Don't delete it.

### `main`

- The **shared, official version** of the project. Everyone's finished work ends up here.
- Only code that is **finished, working and reviewed** goes into `main`:
  - the app starts without errors,
  - the feature works as described in the user story,
  - tests pass (for backend logic),
  - no secrets (`.env`), no generated folders (`node_modules/`, `.venv/`).
- **Nobody pushes to `main` directly.** Work gets into `main` only through a **Pull Request** with 1 approval (Section 4).

```
main                ──●──────────────●───────────●──►  finished, reviewed work only
                       \            ↑ PR        ↑ PR
koharoute_seyoung       ●──●──●──●──┘           │       seyoung's daily work
koharoute_keen           ●──●──●──●──●──●───────┘       keen's daily work
```

### Daily routine on your branch

```bash
# 1. Make sure you're on your branch
git switch koharoute_<your_name>

# 2. Bring in everything that was merged into main since last time
git fetch origin
git merge origin/main

# 3. ...write code, save, test...

# 4. Save and upload
git add .
git commit -m "feat: show driver stops as cards"
git push
```

Do step 2 **every time you start working**, and again after any teammate's PR is merged. It keeps your branch close to `main`, so conflicts stay small.

---

## 4. Pull Requests (PR)

### 4.1 What is a PR?

A **Pull Request** is a request on GitHub that says: *"My branch has finished work. Please review it and add it to `main`."*

A PR shows:

- **which changes** you made (every added or removed line),
- **a description** of what you did and how to test it,
- **comments** from the reviewer,
- an **Approve** button for the reviewer and a **Merge** button.

On our team, every PR needs **1 approval** from a teammate before it can be merged into `main`.

### 4.2 When to open a PR

When one piece of work is **finished and working**, for example one user story (like "R2 driver stop cards") or one bug fix. Keep PRs small; a small PR is quick to review.

> While your PR is open, **anything else you push to your branch is added to that same PR.** So wait until it's merged before pushing your next feature, or ask your reviewer to be quick.

### 4.3 How to open a PR, step by step

1. **Sync and push your branch** first:

   ```bash
   git switch koharoute_seyoung
   git fetch origin
   git merge origin/main
   git push
   ```

2. Go to the repo on **github.com**.
3. You'll usually see a yellow bar: **"koharoute_seyoung had recent pushes" → Compare & pull request**. Click it.
   No yellow bar? Click the **Pull requests** tab → **New pull request**.
4. Check the two boxes at the top:
   - **base: `main`** ← where the work goes
   - **compare: `koharoute_seyoung`** ← your branch
5. **Title:** short description plus the story ID, e.g. `feat: driver stop cards (R2)`
6. **Description:** fill in:

   ```markdown
   ## What
   Driver page shows today's stops as cards, next stop highlighted.

   ## Story
   R2

   ## How to test
   1. Run backend and frontend
   2. Log in as a driver, open /driver, check the stops are in order

   ## Screenshot
   (drag an image here for frontend changes)
   ```

7. On the right side, click **Reviewers** and pick a teammate.
8. Click **Create pull request**.

### 4.4 After you open it

- The reviewer reads the **Files changed** tab and either **Approves** or **Requests changes**.
- If changes are requested: fix them **on your branch**, then `git add .`, `git commit -m "..."`, `git push`. The PR updates automatically.
- Once it has **1 approval** and GitHub shows no conflicts, click **Merge pull request → Confirm merge**.
- **Don't click "Delete branch".** You keep using your branch.
- Tell the team in the chat that it's merged, so everyone runs `git fetch origin` + `git merge origin/main` on their branch.

### 4.5 Reviewing a teammate's PR

1. Open their PR → **Files changed**.
2. Click **+** next to a line to leave a comment.
3. Click **Review changes** (top right) → **Approve**, **Request changes** (say what and why), or **Comment**.

---

## 5. File naming rules

General rules for every file and folder:

- **English letters only.** No Korean, no spaces, no special characters except `_`, `-` and `.`
- Short and descriptive: the name says what's inside (`assign.py`, not `test2_final.py`).
- One file, one job.

| What | Style | Examples |
|---|---|---|
| Python files (`backend/`) | `snake_case.py` (lowercase, words joined with `_`) | `assign.py`, `routing.py`, `seed.py`, `models.py` |
| Python tests | `test_<what>.py` in `backend/tests/` | `test_assign.py`, `test_routing.py` |
| React component files | `PascalCase.jsx` (each word capitalised, no separator) | `MapView.jsx`, `StopCard.jsx`, `DriverRoute.jsx` |
| Other JavaScript files (helpers, API calls) | `camelCase.js` | `apiClient.js`, `formatDistance.js` |
| CSS for a component | same name as the component | `StopCard.css` |
| Folders | lowercase | `routers/`, `services/`, `components/`, `pages/` |
| Docs, notes | `kebab-case.md` (lowercase, words joined with `-`) | `baseline-definition.md`, `demo-script.md` |
| Images | `kebab-case.png` | `route-map-screenshot.png` |

Names inside the code follow the same idea: Python variables and functions in `snake_case` (`total_distance_km`), React components in `PascalCase` (`StopCard`), JavaScript variables and functions in `camelCase` (`totalDistanceKm`).

Never commit these (the `.gitignore` already blocks them): `.env`, `node_modules/`, `.venv/`, `__pycache__/`, `*.db`.

---
