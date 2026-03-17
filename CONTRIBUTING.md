# Contributing to Transcriber CLI

Thank you for your interest in contributing to Transcriber CLI! This document explains how the team tracks work and how anyone can participate.

---

## 📋 Project Board (Backlog & Issues)

All planned work, in-progress tasks, and completed items are tracked on the **GitHub Project board**:

👉 **[View the Project Board](https://github.com/users/mpivarski/projects)**

The board is organized into the following columns:

| Column | Purpose |
|--------|---------|
| **Backlog** | Ideas and tasks that are not yet scheduled |
| **To Do** | Work that has been prioritized for the current cycle |
| **In Progress** | Work actively being developed |
| **Done** | Completed work |

Anyone with a GitHub account can view the project board. Repository contributors can move cards and update statuses.

---

## 🐛 Reporting Issues & Submitting Backlog Items

We use **GitHub Issues** as the single source of truth for all bugs, feature requests, and tasks. Everyone is welcome to open an issue.

### How to open an issue

1. Go to the [Issues tab](https://github.com/mpivarski/Transcriber-CLI-V3/issues).
2. Click **New issue**.
3. Choose the appropriate template:
   - **Bug Report** – something is broken or behaving unexpectedly.
   - **Feature Request / Backlog Item** – you have an idea for an improvement.
   - **Task / Backlog Item** – a development task that needs to be tracked.
4. Fill in the template and click **Submit new issue**.

Your issue will automatically appear on the project board backlog and will be triaged by a maintainer.

---

## 🔀 Submitting a Pull Request

1. **Fork** the repository and create a new branch from `main`:
   ```bash
   git checkout -b feature/my-descriptive-branch-name
   ```
2. Make your changes, following the style of the existing code.
3. Test your changes locally before opening a PR.
4. Open a **Pull Request** against the `main` branch and fill in the description, linking to any related issue (e.g., `Closes #42`).
5. A maintainer will review your PR and may request changes.

---

## 🛠️ Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/mpivarski/Transcriber-CLI-V3.git
cd Transcriber-CLI-V3

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure AWS credentials (required for Bedrock access)
aws configure
```

See the [README](./README.md) for full usage instructions.

---

## 📜 Code of Conduct

Please be respectful and constructive in all interactions. We follow the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct.

---

*Created for the Field Museum Transcriber CLI project.*
