# GitHub CLI TUI (`gh-tui`)

A terminal user interface wrapper for the official GitHub CLI (`gh`). 
This tool makes exploring repositories, issues, and pull requests accessible to everyone without needing to memorize `gh` commands.

## Features
- **Dashboard:** Instantly view the repository's README and status.
- **Issues & PRs:** Browse open issues and pull requests in an interactive data table.
- **Details View:** Read issue/PR descriptions beautifully formatted in Markdown within the terminal.
- **Interactive Login:** Seamlessly launch the GitHub CLI authentication flow directly from the TUI.
- **My Repositories & Bulk Actions:** List all your GitHub repositories, select multiple rows, and perform bulk deletions or bulk visibility changes (make public/private).
- **Remotes & Configuration:** Manage git remotes (add/remove), instantly fetch all remotes (`git fetch --all`), and set the default `gh` repository via a dedicated configuration panel.
- **Browser Integration:** Instantly open the selected issue or PR in your default web browser with one click.
- **Search Capabilities:** A filter bar makes tracking down issues and PRs much easier.
- **Clone Actions:** Select a repository in the `My Repositories` view and easily clone it with a single button.
- **Cross-Repository Support:** Leave the repository input blank to view the current directory's git repo, or type any `owner/repo` (e.g., `cambrianminds/xai-tts`) to explore remotely!

## Prerequisites
1. **GitHub CLI (`gh`)**: You must have the [GitHub CLI installed](https://cli.github.com/) and authenticated (`gh auth login`).
2. **Python**: Python 3.10+ installed.

## Installation & Usage
1. Open your terminal in the `gh-tui` directory.
2. (Optional) Create a virtual environment: `python -m venv venv` and activate it.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python app.py
   ```

## Keybindings
- `q`: Quit the application
- `d`: Toggle Dark/Light mode
- `b`: Go back to the list view (if you are reading a specific issue/PR's details)
- `Tab`: Navigate between buttons and tables
- `Enter` or `Space`: Trigger the focused button or select a table row

## License
Distributed under the [MIT License](LICENSE).
