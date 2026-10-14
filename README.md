# KohaRoute

Waste & recycling pickup route planner for councils and community groups.

- **Backend:** Python + FastAPI (`backend/`)
- **Frontend:** React + react-leaflet (`frontend/`)

This README explains how to get the code, make a branch for each user story, and send your work to `main` with a Pull Request. Follow it in order the first time.

## Folder structure

```
koharoute/
├── README.md
├── .gitignore
├── backend/     ← Python code
└── frontend/    ← React code
```

Backend work goes in `backend/`, frontend work goes in `frontend/`. Nothing else at the top level without asking sy first.

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
   `https://github.com/osy0602/KohaRoute.git`

### 1.3 Clone

```bash
git clone https://github.com/osy0602/KohaRoute.git
```

This creates a new folder called `KohaRoute` with all the code inside. Move into it and open it in VS Code:

```bash
cd KohaRoute
code .
```

If a browser window opens asking you to sign in to GitHub, sign in and approve. That's normal the first time.

Check it worked:

```bash
git status
```

You should see `On branch main`.

---

## 2. One branch per user story

Every **user story gets its own branch**. You make it from the latest `main` when you start the story, open a PR when it's done, and the branch is deleted after it's merged. Then you start a new branch for your next story.

### 2.1 Branch names

```
us-<number>-<short-name>
```

Story number with two digits, then a few words from the story title, all lowercase, words joined with `-`. Examples:

| Story | Branch |
|---|---|
| US-04 Approve or reject bookings | `us-04-approve-bookings` |
| US-05 Manage vehicle records | `us-05-vehicle-records` |
| US-07 Build and optimise routes | `us-07-build-routes` |

A small fix that isn't a story: `fix-<short-name>`, e.g. `fix-login-error-message`.

### 2.2 Start a story (make the branch)

```bash
git switch main
git pull
git switch -c us-04-approve-bookings
git push -u origin us-04-approve-bookings
```

| Command | What it does |
|---|---|
| `git switch main` | Move onto `main` |
| `git pull` | Get everything that was merged into `main` so far |
| `git switch -c us-04-approve-bookings` | Create the new story branch from `main` and move onto it |
| `git push -u origin us-04-approve-bookings` | Put the branch on GitHub and link it, so later `git push` and `git pull` just work |

Always start a new branch **from an up-to-date `main`**, never from another story branch.

**VS Code alternative:** click the branch name in the **bottom-left corner** → pick **main** → click it again → **Create new branch...** → type the name.

### 2.3 Check which branch you're on

Look at the **bottom-left corner of VS Code**, or run:

```bash
git branch
```

The branch with `*` next to it is the one you're on. **Before you start coding, always check it says your story branch, not `main`.**

---

## 3. Story branch vs `main`

### Story branch (`us-<number>-<short-name>`)

- **The workspace for one user story.** The person who owns the story commits and pushes here.
- Work in progress is fine: half-finished code, experiments, many small commits.
- Nothing you do here affects anyone else.
- Only that story's work goes here. Starting another story? Make a new branch (2.2).
- Deleted after its PR is merged.

### `main`

- The **shared, official version** of the project. Everyone's finished work ends up here.
- Only code that is **finished, working and reviewed** goes into `main`:
  - the app starts without errors,
  - the feature works as described in the user story,
  - tests pass (for backend logic),
  - no secrets (`.env`), no generated folders (`node_modules/`, `.venv/`).
- **Nobody pushes to `main` directly.** Work gets into `main` only through a **Pull Request** with 1 approval (Section 4).

```
main                      ──●───────────────●──────────●──►  finished, reviewed work only
                             \  \           ↑ PR       ↑ PR
us-04-approve-bookings        ●──●──●──●────┘          │       one story
us-12-driver-route               ●──●──●──●──●──●──────┘       another story
```

### Daily routine on your story branch

```bash
# 1. Make sure you're on your story branch
git switch us-04-approve-bookings

# 2. Bring in everything that was merged into main since last time
git fetch origin
git merge origin/main

# 3. ...write code, save, test...

# 4. Save and upload
git add .
git commit -m "feat: approve and reject buttons on bookings list"
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

When the user story on that branch is **finished and working** (its acceptance criteria pass). One story = one branch = one PR.

### 4.3 How to open a PR, step by step

1. **Sync and push your branch** first:

   ```bash
   git switch us-04-approve-bookings
   git fetch origin
   git merge origin/main
   git push
   ```

2. Go to the repo on **github.com**.
3. You'll usually see a yellow bar: **"us-04-approve-bookings had recent pushes" → Compare & pull request**. Click it.
   No yellow bar? Click the **Pull requests** tab → **New pull request**.
4. Check the two boxes at the top:
   - **base: `main`** ← where the work goes
   - **compare: `us-04-approve-bookings`** ← your story branch
5. **Title:** story ID plus short description, e.g. `US-04: approve or reject bookings`
6. **Description:** fill in:

   ```markdown
   ## What
   Admin can approve or reject pending bookings; rejecting needs a reason.

   ## Story
   US-04

   ## How to test
   1. Run backend and frontend
   2. Log in as admin, open Bookings, approve one and reject one with a reason

   ## Screenshot
   (drag an image here for frontend changes)
   ```

7. On the right side, click **Reviewers** and pick a teammate.
8. Click **Create pull request**.

### 4.4 After you open it

- The reviewer reads the **Files changed** tab and either **Approves** or **Requests changes**.
- If changes are requested: fix them **on the same story branch**, then `git add .`, `git commit -m "..."`, `git push`. The PR updates automatically.
- Once it has **1 approval** and GitHub shows no conflicts, click **Merge pull request → Confirm merge**.
- Click **Delete branch** after merging. The story is done.
- Clean up on your computer and get the new `main`:

  ```bash
  git switch main
  git pull
  git branch -d us-04-approve-bookings
  ```

- Tell the team in the chat that it's merged, so everyone runs `git fetch origin` + `git merge origin/main` on their own story branch.

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

