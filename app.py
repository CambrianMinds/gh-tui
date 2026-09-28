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
        border-right: solid dodgerblue;
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
        border-left: solid dodgerblue;
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
        border: solid gray;
    }
    Markdown {
        height: 1fr;
        border: solid gray;
        overflow-y: scroll;
        display: none;
    }
    Log {
        height: 10;
        border: solid gray;
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
                yield Button("Issues", id="nav-issues", classes="nav-btn")
                yield Button("Pull Requests", id="nav-prs", classes="nav-btn")
                
                yield Label("Status:")
                self.status_log = Log(id="status-log")
                yield self.status_log

            # Center Panel: Content (Table or Details)
            with Vertical(id="center-panel"):
                yield Label("Content View", id="content-title", classes="field")
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
                
                yield Button("Refresh", id="action-refresh", classes="action-btn", variant="success")
                yield Button("Create Issue", id="action-create-issue", classes="action-btn", variant="warning")

        yield Footer()

    def on_mount(self) -> None:
        self.title = "GitHub CLI TUI"
        self.current_view = "dashboard"
        self.current_data = []
        self.selected_item = None
        
        # Check if gh CLI is installed
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
            self.status_log.write_line("gh CLI found.")
        except Exception:
            self.status_log.write_line("Error: gh CLI not found or not authenticated.")
            
        self.load_dashboard()

    def get_repo_arg(self) -> list:
        repo = self.repo_input.value.strip()
        if repo:
            return ["--repo", repo]
        return []

    def log_msg(self, msg: str) -> None:
        self.app.call_from_thread(self.status_log.write_line, msg)

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

    def show_table(self, title: str, headers: list, rows: list) -> None:
        self.query_one("#content-title", Label).update(title)
        self.data_table.clear(columns=True)
        self.data_table.add_columns(*headers)
        for row in rows:
            self.data_table.add_row(*row)
            
        self.markdown_view.display = False
        self.data_table.display = True
        
        self.btn_view_details.disabled = True
        self.btn_open_browser.disabled = True
        self.selected_item = None

    def show_markdown(self, title: str, content: str) -> None:
        self.query_one("#content-title", Label).update(title)
        self.markdown_view.update(content)
        
        self.data_table.display = False
        self.markdown_view.display = True
        
        # Details button doesn't make sense here, browser button is kept if we selected an item
        self.btn_view_details.disabled = True

    def set_title(self, text: str) -> None:
        self.query_one("#content-title", Label).update(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        
        if btn_id == "nav-dashboard":
            self.load_dashboard()
        elif btn_id == "nav-issues":
            self.load_issues()
        elif btn_id == "nav-prs":
            self.load_prs()
        elif btn_id == "action-refresh":
            if self.current_view == "issues":
                self.load_issues()
            elif self.current_view == "prs":
                self.load_prs()
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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_index = event.cursor_row
        if 0 <= row_index < len(self.current_data):
            self.selected_item = self.current_data[row_index]
            self.btn_view_details.disabled = False
            self.btn_open_browser.disabled = False
            
    def action_back_to_list(self) -> None:
        if self.current_view == "issues":
            self.data_table.display = True
            self.markdown_view.display = False
            self.query_one("#content-title", Label).update("Open Issues")
        elif self.current_view == "prs":
            self.data_table.display = True
            self.markdown_view.display = False
            self.query_one("#content-title", Label).update("Open Pull Requests")
            
    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

if __name__ == "__main__":
    app = GHTUIApp()
    app.run()
