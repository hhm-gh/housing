"""
ACS Variable Browser — Phase 1.5
Keyboard-driven TUI for browsing the ACS 1-year variable catalog.

Usage:
  uv run browse_acs_catalog.py

Keys:
  Tab / Shift+Tab   Switch focus between concept list and variable table
  Type              Filter concept list (when concept pane is focused)
  Enter             Confirm concept filter, move to variable table
  Space             Mark / unmark highlighted variable
  e                 Export marked variables to data/acs_selection.txt
  Escape            Return focus to concept list
  q                 Quit
"""

import sys
from pathlib import Path

import pandas as pd
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Label, ListItem, ListView, Static

CATALOG_PATH = Path("data/acs_variables.parquet")
EXPORT_PATH  = Path("data/acs_selection.txt")


def _clean_label(label: str) -> str:
    label = label.removeprefix("Estimate!!")
    return label.replace("!!", " › ")


class ACSBrowser(App):
    TITLE = "ACS Variable Browser"

    CSS = """
    Screen { layers: base; }

    #left-pane {
        width: 40;
        border-right: solid $primary-darken-2;
    }

    #concept-filter {
        dock: top;
        margin: 0;
    }

    #concept-list {
        height: 1fr;
    }

    #right-pane {
        width: 1fr;
    }

    #variable-table {
        height: 1fr;
    }

    #detail {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-top: solid $primary-darken-2;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("q",      "quit",           "Quit"),
        Binding("e",      "export",         "Export marked"),
        Binding("escape", "focus_concepts", "Back to concepts"),
        Binding("tab",    "focus_variables","Variables", show=False),
    ]

    def __init__(self):
        super().__init__()
        if not CATALOG_PATH.exists():
            sys.exit(f"Catalog not found: {CATALOG_PATH}\nRun: uv run collect_acs_catalog.py")
        self.df = pd.read_parquet(CATALOG_PATH)
        self.all_concepts: list[str] = sorted(self.df["concept"].unique())
        self.marked: set[str] = set()
        self._current_concept: str | None = None
        self._current_var: str | None = None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="left-pane"):
                yield Input(placeholder="Filter concepts…", id="concept-filter")
                yield ListView(id="concept-list")
            with Vertical(id="right-pane"):
                yield DataTable(id="variable-table", cursor_type="row")
        yield Static("Select a concept to browse variables.", id="detail")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#variable-table", DataTable)
        table.add_column("Variable", key="var", width=16)
        table.add_column("Label",    key="lbl")

        self._populate_concepts(self.all_concepts)
        self.query_one("#concept-list", ListView).focus()
        self._update_subtitle()

    # ------------------------------------------------------------------
    # Concept pane
    # ------------------------------------------------------------------

    def _populate_concepts(self, concepts: list[str]) -> None:
        lv = self.query_one("#concept-list", ListView)
        lv.clear()
        for c in concepts:
            lv.append(ListItem(Label(c), name=c))

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip().lower()
        filtered = [c for c in self.all_concepts if query in c.lower()]
        self._populate_concepts(filtered)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#concept-list", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        concept = event.item.name
        if concept == self._current_concept:
            return
        self._current_concept = concept
        self._populate_variables(concept)
        self.query_one("#variable-table", DataTable).focus()

    # ------------------------------------------------------------------
    # Variable pane
    # ------------------------------------------------------------------

    def _populate_variables(self, concept: str) -> None:
        table = self.query_one("#variable-table", DataTable)
        table.clear()
        subset = self.df[self.df["concept"] == concept].sort_values("name")
        for _, row in subset.iterrows():
            mark = "★ " if row["name"] in self.marked else "  "
            table.add_row(
                mark + row["name"],
                _clean_label(row["label"]),
                key=row["name"],
            )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None:
            return
        name = str(event.row_key.value)
        self._current_var = name
        self._update_detail(name)

    def on_key(self, event) -> None:
        focused = self.focused
        table = self.query_one("#variable-table", DataTable)
        if event.key == "space" and focused is table and self._current_var:
            self._toggle_marked(self._current_var)
            event.stop()

    def _toggle_marked(self, name: str) -> None:
        table = self.query_one("#variable-table", DataTable)
        if name in self.marked:
            self.marked.discard(name)
            prefix = "  "
        else:
            self.marked.add(name)
            prefix = "★ "
        table.update_cell(name, "var", prefix + name, update_width=False)
        self._update_detail(name)
        self._update_subtitle()

    # ------------------------------------------------------------------
    # Detail strip
    # ------------------------------------------------------------------

    def _update_detail(self, name: str) -> None:
        rows = self.df[self.df["name"] == name]
        if rows.empty:
            return
        row = rows.iloc[0]
        mark_str = "  ★ marked" if name in self.marked else ""
        text = (
            f" [bold]{name}[/bold]  |  group: {row['group']}  |  "
            f"type: {row['predicate_type']}  |  concept: {row['concept']}{mark_str}\n"
            f" {_clean_label(row['label'])}"
        )
        self.query_one("#detail", Static).update(text)

    def _update_subtitle(self) -> None:
        n = len(self.marked)
        self.sub_title = f"{n} variable{'s' if n != 1 else ''} marked"

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_export(self) -> None:
        if not self.marked:
            self.notify("No variables marked — use Space to mark.", severity="warning")
            return
        EXPORT_PATH.write_text("\n".join(sorted(self.marked)) + "\n")
        self.notify(f"Exported {len(self.marked)} variables → {EXPORT_PATH}", timeout=4)

    def action_focus_concepts(self) -> None:
        self.query_one("#concept-list", ListView).focus()

    def action_focus_variables(self) -> None:
        self.query_one("#variable-table", DataTable).focus()


if __name__ == "__main__":
    ACSBrowser().run()
