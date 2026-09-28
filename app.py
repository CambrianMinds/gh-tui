import subprocess
import json
import os
import webbrowser

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Button, DataTable, Label, Markdown, Input, Log
from textual import work

class GHTUIApp(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    #left-panel {
        width: 20%;
        height: 100%;
        border-right: solid $primary;
        padding: 1;
    }
    #center-panel {
        width: 60%;
        height: 100%;
        padding: 1;
    }
    #right-panel {
        width: 20%;
        height: 100%;
        border-left: solid $primary;
        padding: 1;
    }
    .field {
        margin-bottom: 1;
    }
    .nav-btn {
        width: 100%;
        margin-bottom: 1;
    }
    .action-btn {
        width: 100%;
        margin-bottom: 1;
    }
    DataTable {
        height: 1fr;
        border: solid $panel-light;
    }
    Markdown {
        height: 1fr;
        border: solid $panel-light;
        overflow-y: scroll;
        display: none;
    }
    Log {
        height: 10;
        border: solid $panel-light;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
        ("b", "back_to_list", "Back to List")
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal():
            # Left Panel: Navigation & Config
            with Vertical(id="left-panel"):
                yield Label("Target Repository", classes="field")
                self.repo_input = Input(placeholder="owner/repo (or blank for current)", classes="field")
                yield self.repo_input
                
                yield Label("Navigation", classes="field")
                yield Button("Dashboard", id="nav-dashboard", classes="nav-btn", variant="primary")
                yield Button("My Repositories", id="nav-my-repos", classes="nav-btn")
                yield Button("Issues", id="nav-issues", classes="nav-btn")
                yield Button("Pull Requests", id="nav-prs", classes="nav-btn")
                yield Button("Remotes / Config", id="nav-config", classes="nav-btn")
                
                yield Label("Status:")
                self.status_log = Log(id="status-log")
                yield self.status_log
                
                yield Button("Login (Interactive)", id="action-login", classes="nav-btn", variant="success")

            # Center Panel: Content (Table or Details)
            with Vertical(id="center-panel"):
                yield Label("Content View", id="content-title", classes="field")
                
                self.search_input = Input(id="search-filter", placeholder="Filter items...", classes="field")
                self.search_input.display = False
                yield self.search_input
                
                self.data_table = DataTable(cursor_type="row")
                yield self.data_table
                
                self.markdown_view = Markdown(id="markdown-view")
                yield self.markdown_view

            # Right Panel: Actions
            with VerticalScroll(id="right-panel"):
                yield Label("Actions", classes="field")
                
                self.btn_view_details = Button("View Details", id="action-details", classes="action-btn", disabled=True)
                yield self.btn_view_details
                
                self.btn_open_browser = Button("Open in Browser", id="action-browser", classes="action-btn", disabled=True)
                yield self.btn_open_browser
                
                self.btn_refresh = Button("Refresh", id="action-refresh", classes="action-btn", variant="success")
                yield self.btn_refresh
                self.btn_create_issue = Button("Create Issue", id="action-create-issue", classes="action-btn", variant="warning")
                yield self.btn_create_issue
                
                self.repo_controls = Vertical(
                    Button("Clone Repository", id="action-clone", classes="action-btn", variant="success"),
                    Button("Bulk Delete", id="action-bulk-delete", classes="action-btn", variant="error"),
                    Button("Make Private", id="action-bulk-private", classes="action-btn", variant="warning"),
                    Button("Make Public", id="action-bulk-public", classes="action-btn", variant="primary"),
                    id="repo-controls"
                )
                self.repo_controls.display = False
                yield self.repo_controls

                self.config_controls = Vertical(
                    Label("Remote Name (e.g. origin):"),
                    Input(id="input-remote-name", placeholder="origin", classes="field"),
                    Label("Remote URL or Repo:"),
                    Input(id="input-remote-url", placeholder="URL or owner/repo", classes="field"),
                    Button("Add Remote", id="action-add-remote", classes="action-btn", variant="success"),
                    Button("Remove Remote", id="action-remove-remote", classes="action-btn", variant="error"),
                    Button("Set Default (gh)", id="action-set-default", classes="action-btn", variant="primary"),
                    Button("Fetch Remotes", id="action-fetch-remotes", classes="action-btn"),
                    id="config-controls"
                )
                self.config_controls.display = False
                yield self.config_controls

        yield Footer()

    def on_mount(self) -> None:
        self.title = "GitHub CLI TUI"
        self.current_view = "dashboard"
        self.current_data = []
        self.selected_item = None
        self.selected_repos = set()
        
        self.check_auth()
        self.load_dashboard()

    def check_auth(self) -> None:
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
            self.status_log.write_line("gh CLI found.")
            
            auth_res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
            if auth_res.returncode == 0:
                self.status_log.write_line("Authenticated with GitHub.")
            else:
                self.status_log.write_line("Not logged in. Use the Login button.")
        except Exception:
            self.status_log.write_line("Error: gh CLI not found on PATH.")

    def get_repo_arg(self) -> list:
        repo = self.repo_input.value.strip()
        if repo:
            return ["--repo", repo]
        return []

    def log_msg(self, msg: str) -> None:
        self.app.call_from_thread(self.status_log.write_line, msg)

    @work(thread=True)
    def load_my_repos(self) -> None:
        self.app.call_from_thread(self.set_title, "Loading My Repositories...")
        self.log_msg("Fetching repositories...")
        self.selected_repos.clear()
        
        cmd = ["gh", "repo", "list", "--json", "name,visibility,updatedAt,url", "-L", "100"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            repos = json.loads(result.stdout)
            self.current_data = repos
            self.current_view = "my-repos"
            
            headers = ["Select", "Name", "Visibility", "Updated"]
            rows = [
                ("[ ]", r["name"], r["visibility"], r["updatedAt"][:10])
                for r in repos
            ]
            self.app.call_from_thread(self.show_table, "My Repositories (Select rows to mark)", headers, rows)
            self.log_msg(f"Loaded {len(repos)} repositories.")
        except Exception as e:
            self.log_msg(f"Error loading repos: {e}")

    @work(thread=True)
    def action_fetch_remotes(self) -> None:
        self.log_msg("Fetching remotes (git fetch --all)...")
        try:
            subprocess.run(["git", "fetch", "--all"], capture_output=True, text=True, check=True)
            self.log_msg("Successfully fetched remotes.")
        except subprocess.CalledProcessError as e:
            self.log_msg(f"Error fetching remotes: {e.stderr}")

    @work(thread=True)
    def bulk_action_repos(self, action: str, visibility: str = "") -> None:
        if not self.selected_repos:
            self.log_msg("Error: No repositories selected.")
            return
        
        repos = list(self.selected_repos)
        self.log_msg(f"Starting {action} for {len(repos)} repos...")
        
        for repo_name in repos:
            try:
                if action == "delete":
                    subprocess.run(["gh", "repo", "delete", repo_name, "--yes"], capture_output=True, text=True, check=True)
                    self.log_msg(f"Deleted {repo_name}.")
                elif action == "visibility":
                    subprocess.run(["gh", "repo", "edit", repo_name, f"--visibility={visibility}"], capture_output=True, text=True, check=True)
                    self.log_msg(f"Made {repo_name} {visibility}.")
            except subprocess.CalledProcessError as e:
                self.log_msg(f"Error processing {repo_name}: {e.stderr}")
        
        self.log_msg(f"Completed {action} operation.")
        self.load_my_repos()

    @work(thread=True)
    def action_clone_repo(self) -> None:
        if not self.selected_repos:
            self.log_msg("Error: No repositories selected.")
            return
        
        for repo_name in self.selected_repos:
            self.log_msg(f"Cloning {repo_name}...")
            try:
                subprocess.run(["gh", "repo", "clone", repo_name], capture_output=True, text=True, check=True)
                self.log_msg(f"Cloned {repo_name}.")
            except subprocess.CalledProcessError as e:
                self.log_msg(f"Error cloning {repo_name}: {e.stderr}")

    @work(thread=True)
    def load_dashboard(self) -> None:
        self.app.call_from_thread(self.set_title, "Loading Dashboard...")
        self.log_msg("Fetching repository overview...")
        
        cmd = ["gh", "repo", "view"] + self.get_repo_arg()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.app.call_from_thread(self.show_markdown, "Dashboard", result.stdout)
            self.log_msg("Dashboard loaded.")
            self.current_view = "dashboard"
        except subprocess.CalledProcessError as e:
            self.log_msg(f"Error loading repo: {e.stderr}")

    @work(thread=True)
    def load_issues(self) -> None:
        self.app.call_from_thread(self.set_title, "Loading Issues...")
        self.log_msg("Fetching open issues...")
        
        cmd = ["gh", "issue", "list", "--json", "number,title,author,state,createdAt,url"] + self.get_repo_arg()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            issues = json.loads(result.stdout)
            self.current_data = issues
            self.current_view = "issues"
            
            headers = ["#", "State", "Title", "Author", "Created"]
            rows = [
                (str(iss["number"]), iss["state"], iss["title"], iss["author"]["login"], iss["createdAt"][:10])
                for iss in issues
            ]
            self.app.call_from_thread(self.show_table, "Open Issues", headers, rows)
            self.log_msg(f"Loaded {len(issues)} issues.")
        except Exception as e:
            self.log_msg(f"Error loading issues: {e}")

    @work(thread=True)
    def load_prs(self) -> None:
        self.app.call_from_thread(self.set_title, "Loading Pull Requests...")
        self.log_msg("Fetching open PRs...")
        
        cmd = ["gh", "pr", "list", "--json", "number,title,author,state,createdAt,url"] + self.get_repo_arg()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            prs = json.loads(result.stdout)
            self.current_data = prs
            self.current_view = "prs"
            
            headers = ["#", "State", "Title", "Author", "Created"]
            rows = [
                (str(pr["number"]), pr["state"], pr["title"], pr["author"]["login"], pr["createdAt"][:10])
                for pr in prs
            ]
            self.app.call_from_thread(self.show_table, "Open Pull Requests", headers, rows)
            self.log_msg(f"Loaded {len(prs)} PRs.")
        except Exception as e:
            self.log_msg(f"Error loading PRs: {e}")

    @work(thread=True)
    def load_item_details(self, item_number: str, view_type: str) -> None:
        self.log_msg(f"Fetching details for #{item_number}...")
        cmd_base = "issue" if view_type == "issues" else "pr"
        cmd = ["gh", cmd_base, "view", item_number] + self.get_repo_arg()
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            title = f"{'Issue' if view_type == 'issues' else 'PR'} #{item_number} Details"
            self.app.call_from_thread(self.show_markdown, title, result.stdout)
            self.log_msg("Details loaded.")
        except subprocess.CalledProcessError as e:
            self.log_msg(f"Error fetching details: {e.stderr}")

    @work(thread=True)
    def load_config(self) -> None:
        self.app.call_from_thread(self.set_title, "Loading Configuration...")
        self.log_msg("Fetching git remotes...")
        
        try:
            git_result = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
            remotes = git_result.stdout if git_result.stdout else "No remotes found."
            
            gh_result = subprocess.run(["gh", "repo", "set-default", "--view"], capture_output=True, text=True)
            default_repo = gh_result.stdout if gh_result.stdout else "Not set."
            
            content = f"### Git Remotes\n```text\n{remotes}\n```\n\n### Default GitHub Repo (`gh`)\n```text\n{default_repo}\n```"
            
            self.app.call_from_thread(self.show_markdown, "Configuration & Remotes", content)
            self.current_view = "config"
            self.log_msg("Configuration loaded.")
        except Exception as e:
            self.log_msg(f"Error loading config: {e}")

    @work(thread=True)
    def action_remote_add(self, name: str, url: str) -> None:
        if not name or not url:
            self.log_msg("Error: Name and URL required to add remote.")
            return
        self.log_msg(f"Adding remote '{name}'...")
        try:
            subprocess.run(["git", "remote", "add", name, url], capture_output=True, text=True, check=True)
            self.log_msg(f"Added remote {name}.")
            self.load_config()
        except subprocess.CalledProcessError as e:
            self.log_msg(f"Error adding remote: {e.stderr}")

    @work(thread=True)
    def action_remote_remove(self, name: str) -> None:
        if not name:
            self.log_msg("Error: Remote name required to remove.")
            return
        self.log_msg(f"Removing remote '{name}'...")
        try:
            subprocess.run(["git", "remote", "remove", name], capture_output=True, text=True, check=True)
            self.log_msg(f"Removed remote {name}.")
            self.load_config()
        except subprocess.CalledProcessError as e:
            self.log_msg(f"Error removing remote: {e.stderr}")

    @work(thread=True)
    def action_remote_default(self, repo: str) -> None:
        if not repo:
            self.log_msg("Error: Repo required to set default.")
            return
        self.log_msg(f"Setting default repo to '{repo}'...")
        try:
            subprocess.run(["gh", "repo", "set-default", repo], capture_output=True, text=True, check=True)
            self.log_msg(f"Default repo set to {repo}.")
            self.load_config()
        except subprocess.CalledProcessError as e:
            self.log_msg(f"Error setting default: {e.stderr}")

    def show_table(self, title: str, headers: list, rows: list) -> None:
        self.query_one("#content-title", Label).update(title)
        self.current_rows = rows
        self.data_table.clear(columns=True)
        self.col_keys = self.data_table.add_columns(*headers)
        self.row_keys = []
        for row in rows:
            self.row_keys.append(self.data_table.add_row(*row))
            
        self.search_input.display = True
        self.markdown_view.display = False
        self.data_table.display = True
        
        self.btn_view_details.disabled = True
        self.btn_open_browser.disabled = True
        self.selected_item = None

    def show_markdown(self, title: str, content: str) -> None:
        self.query_one("#content-title", Label).update(title)
        self.markdown_view.update(content)
        
        self.search_input.display = False
        self.data_table.display = False
        self.markdown_view.display = True
        
        # Details button doesn't make sense here, browser button is kept if we selected an item
        self.btn_view_details.disabled = True

    def set_title(self, text: str) -> None:
        self.query_one("#content-title", Label).update(text)

    def action_login(self) -> None:
        with self.suspend():
            print("\n" * 40)
            print("--- GitHub CLI Authentication ---")
            subprocess.run(["gh", "auth", "login"])
            print("\nAuthentication process finished.")
            input("Press Enter to return to the TUI...")
        
        self.check_auth()
        if self.current_view == "dashboard":
            self.load_dashboard()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        
        if btn_id and btn_id.startswith("nav-"):
            is_config = (btn_id == "nav-config")
            is_repos = (btn_id == "nav-my-repos")
            if hasattr(self, 'config_controls'):
                self.config_controls.display = is_config
            if hasattr(self, 'repo_controls'):
                self.repo_controls.display = is_repos
                
            self.btn_view_details.display = not (is_config or is_repos)
            self.btn_open_browser.display = not (is_config or is_repos)
            self.btn_refresh.display = not (is_config or is_repos)
            self.btn_create_issue.display = not (is_config or is_repos)
        
        if btn_id == "nav-dashboard":
            self.load_dashboard()
        elif btn_id == "nav-my-repos":
            self.load_my_repos()
        elif btn_id == "nav-issues":
            self.load_issues()
        elif btn_id == "nav-prs":
            self.load_prs()
        elif btn_id == "nav-config":
            self.load_config()
        elif btn_id == "action-refresh":
            if self.current_view == "issues":
                self.load_issues()
            elif self.current_view == "prs":
                self.load_prs()
            elif self.current_view == "config":
                self.load_config()
            else:
                self.load_dashboard()
        elif btn_id == "action-details":
            if self.selected_item and self.current_view in ["issues", "prs"]:
                self.load_item_details(self.selected_item["number"], self.current_view)
        elif btn_id == "action-browser":
            if self.selected_item and "url" in self.selected_item:
                webbrowser.open(self.selected_item["url"])
                self.log_msg(f"Opened {self.selected_item['url']} in browser.")
        elif btn_id == "action-create-issue":
            self.log_msg("To create an issue, run 'gh issue create' in the terminal.")
        elif btn_id == "action-login":
            self.action_login()
        elif btn_id == "action-add-remote":
            name = self.query_one("#input-remote-name", Input).value.strip()
            url = self.query_one("#input-remote-url", Input).value.strip()
            self.action_remote_add(name, url)
        elif btn_id == "action-remove-remote":
            name = self.query_one("#input-remote-name", Input).value.strip()
            self.action_remote_remove(name)
        elif btn_id == "action-set-default":
            repo = self.query_one("#input-remote-url", Input).value.strip()
            self.action_remote_default(repo)
        elif btn_id == "action-fetch-remotes":
            self.action_fetch_remotes()
        elif btn_id == "action-clone":
            self.action_clone_repo()
        elif btn_id == "action-bulk-delete":
            self.bulk_action_repos("delete")
        elif btn_id == "action-bulk-private":
            self.bulk_action_repos("visibility", "private")
        elif btn_id == "action-bulk-public":
            self.bulk_action_repos("visibility", "public")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-filter":
            query = event.value.lower()
            self.data_table.clear()
            self.row_keys = []
            
            for item, row in zip(self.current_data, getattr(self, "current_rows", [])):
                # Join the row strings to check if any field matches the query
                row_str = " ".join(str(cell).lower() for cell in row)
                if query in row_str:
                    self.row_keys.append(self.data_table.add_row(*row))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_index = event.cursor_row
        if 0 <= row_index < len(self.current_data):
            self.selected_item = self.current_data[row_index]
            self.btn_view_details.disabled = False
            self.btn_open_browser.disabled = False
            
            if self.current_view == "my-repos":
                repo_name = self.selected_item["name"]
                if repo_name in self.selected_repos:
                    self.selected_repos.remove(repo_name)
                    mark = "[ ]"
                else:
                    self.selected_repos.add(repo_name)
                    mark = "[X]"
                self.data_table.update_cell(self.row_keys[row_index], self.col_keys[0], mark)
            
    def action_back_to_list(self) -> None:
        if self.current_view == "issues":
            self.search_input.display = True
            self.data_table.display = True
            self.markdown_view.display = False
            self.query_one("#content-title", Label).update("Open Issues")
        elif self.current_view == "prs":
            self.search_input.display = True
            self.data_table.display = True
            self.markdown_view.display = False
            self.query_one("#content-title", Label).update("Open Pull Requests")
            
    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

if __name__ == "__main__":
    app = GHTUIApp()
    app.run()
