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
  g                 Open theme picker (filter concept list by subject area)
  t                 Toggle: show all concepts / top-level only (suppress demographic refinements)
  f                 Open full-screen concept browser
  p                 Preview data sample for highlighted variable (all states, 2023)
  e                 Export marked variables to data/acs_selection.txt
  Escape            Return focus to concept list / close preview
  q                 Quit
"""

import os
import re
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Input, Label, ListItem, ListView, Select, Static
from textual import work

load_dotenv()

CATALOG_PATH  = Path("data/acs_variables.parquet")
EXPORT_PATH   = Path("data/acs_selection.txt")
PREVIEW_YEAR  = 2023
ACS_URL       = f"https://api.census.gov/data/{PREVIEW_YEAR}/acs/acs1"

# Flat geographies: single wildcard fetch, no parent geo required
GEO_OPTIONS = [
    ("State", "state"),
    ("County  (65k+ pop, ACS 1-yr)", "county"),
    ("MSA / CBSA", "msa"),
]

GEO_PARAMS = {
    "state":  {"for": "state:*"},
    "county": {"for": "county:*", "in": "state:*"},
    "msa":    {"for": "metropolitan statistical area/micropolitan statistical area:*"},
}

GEO_ROW_LABEL = {
    "state":  "states",
    "county": "counties",
    "msa":    "MSAs/CBSAs",
}


_TRAILING_PAREN = re.compile(r'\s*\([^)]*\)\s*$')

def _is_refinement(concept: str, concept_set: set[str]) -> bool:
    """True if stripping the trailing (...) yields a concept that exists in the catalog."""
    m = _TRAILING_PAREN.search(concept)
    if not m:
        return False
    return concept[:m.start()].strip() in concept_set


# Ordered: first matching theme wins.
_THEME_RULES: list[tuple[str, list[str]]] = [
    ("Allocation",                   ["allocation of", "allocation --"]),
    ("Aggregate & Median",           ["aggregate ", "median "]),
    ("Technology",                   ["computer", "internet"]),
    ("Geographic Mobility",          ["geographical mobility", "residence 1 year ago", "migration"]),
    ("Disability",                   ["disability", "ambulatory difficulty", "cognitive difficulty",
                                      "hearing difficulty", "vision difficulty", "self-care difficulty",
                                      "independent living difficulty"]),
    ("Health Insurance",             ["health insurance", "insurance coverage"]),
    ("Commuting",                    ["travel time to work", "means of transportation to work",
                                      "time of departure to go to work", "vehicles (car, truck",
                                      "place of work"]),
    ("Education",                    ["educational attainment", "field of degree", "school enrollment",
                                      "enrolled in school", "grade enrolled"]),
    ("Language & Immigration",       ["language spoken at home", "ability to speak english",
                                      "place of birth", "year of entry", "period of entry",
                                      "ancestry", "year of naturalization"]),
    ("Veterans",                     ["veteran"]),
    ("Food Stamps / SNAP",           ["food stamp", "snap"]),
    ("Family & Living Arrangements", ["marital status", "marriage in the past", "married in the past",
                                      "divorced in the past", "grandparent", "fertility",
                                      "own children under 18", "living arrangements", "living alone",
                                      "unmarried-partner", "unmarried partner"]),
    ("Employment & Labor Force",     ["employment status", "class of worker", "industry",
                                      "occupation", "labor force", "work experience",
                                      "hours worked", "weeks worked", "self-employ"]),
    ("Poverty",                      ["poverty", "ratio of income to poverty", "income deficit"]),
    ("Housing Stock",                ["units in structure", "number of rooms", "number of bedrooms",
                                      "year structure built", "house heating fuel", "vacancy",
                                      "plumbing", "kitchen facilities", "telephone service"]),
    ("Housing Costs",                ["gross rent", "selected monthly owner costs", "contract rent",
                                      "price asked", "rent asked", "owner costs"]),
    ("Tenure & Mortgage",            ["tenure", "mortgage", "year householder moved",
                                      "meals included in rent"]),
    ("Household Structure",          ["household size", "household type", "group quarters",
                                      "nonfamily household", "family type", "householder",
                                      "presence of own children", "subfamilies"]),
    ("Income",                       ["income in the past 12 months", "earnings in the past 12 months",
                                      "wages and salary income", "social security income",
                                      "retirement income", "supplemental security income",
                                      "self-employment income", "public assistance income",
                                      "interest, dividends", "aggregate income", "aggregate earnings",
                                      "aggregate wage"]),
    ("Demographics & Population",    ["sex by age", "total population", "hispanic or latino",
                                      "citizenship status", "nativity of the population",
                                      "race alone", "sex and age"]),
]

ALL_THEMES = [name for name, _ in _THEME_RULES] + ["Other"]

def _assign_theme(concept: str) -> str:
    lower = concept.lower()
    for theme, keywords in _THEME_RULES:
        if any(kw in lower for kw in keywords):
            return theme
    return "Other"


def _clean_label(label: str) -> str:
    label = label.removeprefix("Estimate!!")
    return label.replace("!!", " › ")


# ──────────────────────────────────────────────────────────────────────────────
# Preview modal
# ──────────────────────────────────────────────────────────────────────────────

class PreviewModal(ModalScreen):
    """Data sample for one ACS variable at selectable geography (ACS 1-year, 2023)."""

    BINDINGS = [Binding("escape,q", "dismiss", "Close")]

    CSS = """
    PreviewModal {
        align: center middle;
    }

    #preview-dialog {
        width: 82;
        height: 40;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #preview-title {
        height: 2;
        color: $text;
    }

    #geo-select {
        height: 3;
        margin-bottom: 0;
    }

    #row-filter {
        margin-bottom: 1;
    }

    #preview-table {
        height: 1fr;
        border: solid $primary-darken-2;
    }

    #preview-status {
        height: 1;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def __init__(self, var_name: str, var_label: str, api_key: str) -> None:
        super().__init__()
        self.var_name  = var_name
        self.var_label = var_label
        self.api_key   = api_key
        self._all_rows: list[tuple[str, str]] = []  # (geography name, display value)

    def compose(self) -> ComposeResult:
        with Vertical(id="preview-dialog"):
            yield Label(
                f"[bold]{self.var_name}[/bold]   {_clean_label(self.var_label)}",
                id="preview-title",
            )
            yield Select(GEO_OPTIONS, value="state", id="geo-select")
            yield Input(placeholder="Filter by name…", id="row-filter")
            yield DataTable(id="preview-table", cursor_type="row")
            yield Static("", id="preview-status")

    def on_mount(self) -> None:
        table = self.query_one("#preview-table", DataTable)
        table.add_column("Geography",          key="geo",   width=44)
        table.add_column(f"Value ({PREVIEW_YEAR})", key="value", width=16)
        # Select fires Changed on mount with the initial value, triggering first fetch

    def on_select_changed(self, event: Select.Changed) -> None:
        geo = str(event.value)
        self._all_rows = []
        self.query_one("#row-filter", Input).value = ""
        self.query_one("#preview-table", DataTable).clear()
        self.query_one("#preview-status", Static).update(f"Fetching {PREVIEW_YEAR} data…")
        self._fetch(geo)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "row-filter":
            self._apply_filter()

    def _apply_filter(self) -> None:
        query = self.query_one("#row-filter", Input).value.strip().lower()
        matched = [(n, v) for n, v in self._all_rows if query in n.lower()]
        table = self.query_one("#preview-table", DataTable)
        table.clear()
        for name, val in matched:
            table.add_row(name, val)
        geo = str(self.query_one("#geo-select", Select).value)
        row_label = GEO_ROW_LABEL.get(geo, "rows")
        total = len(self._all_rows)
        if query:
            self.query_one("#preview-status", Static).update(
                f"{len(matched)} of {total} {row_label} match  |  Clear filter to see all"
            )
        else:
            self.query_one("#preview-status", Static).update(
                f"{total} {row_label}  |  Press Escape or q to close"
            )

    @work(thread=True, exclusive=True)
    def _fetch(self, geo: str) -> None:
        status = self.query_one("#preview-status", Static)
        try:
            params = {
                "get": f"NAME,{self.var_name}",
                "key": self.api_key,
                **GEO_PARAMS[geo],
            }
            resp = requests.get(ACS_URL, params=params, timeout=30)
            resp.raise_for_status()
            raw = resp.json()
        except requests.HTTPError as e:
            code = e.response.status_code if e.response else "?"
            self.app.call_from_thread(
                status.update,
                f"[red]HTTP {code} — variable may not exist at this geography in {PREVIEW_YEAR} ACS 1-year.[/red]",
            )
            return
        except Exception as e:
            self.app.call_from_thread(status.update, f"[red]Error: {e}[/red]")
            return

        header, *rows = raw
        val_idx  = header.index(self.var_name)
        name_idx = header.index("NAME")

        def sort_key(r):
            try:
                return (-float(r[val_idx]),)
            except (TypeError, ValueError):
                return (float("inf"),)

        rows.sort(key=sort_key)

        fetched: list[tuple[str, str]] = []
        for r in rows:
            raw_val = r[val_idx]
            try:
                display_val = f"{int(float(raw_val)):,}"
            except (TypeError, ValueError):
                display_val = str(raw_val) if raw_val is not None else "—"
            fetched.append((r[name_idx], display_val))

        self.app.call_from_thread(self._set_rows, fetched, geo)

    def _set_rows(self, rows: list[tuple[str, str]], geo: str) -> None:
        self._all_rows = rows
        self._apply_filter()


# ──────────────────────────────────────────────────────────────────────────────
# Full-screen concept browser
# ──────────────────────────────────────────────────────────────────────────────

class ConceptScreen(ModalScreen[str | None]):
    """Full-screen concept list. Dismisses with selected concept name, or None."""

    BINDINGS = [Binding("escape", "dismiss_none", "Close")]

    CSS = """
    ConceptScreen {
        background: $surface;
        padding: 1 2;
    }

    #cs-title {
        height: 1;
        margin-bottom: 1;
        color: $text-muted;
    }

    #cs-filter {
        margin-bottom: 1;
    }

    #cs-list {
        height: 1fr;
        border: solid $primary-darken-2;
    }

    #cs-status {
        height: 1;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def __init__(self, concepts: list[str]) -> None:
        super().__init__()
        self.all_concepts = concepts

    def compose(self) -> ComposeResult:
        yield Label("Concept Browser  —  Enter to select, Escape to close", id="cs-title")
        yield Input(placeholder="Filter concepts…", id="cs-filter")
        yield ListView(id="cs-list")
        yield Static("", id="cs-status")

    def on_mount(self) -> None:
        self._populate(self.all_concepts)
        self.query_one("#cs-filter", Input).focus()
        self._update_status(len(self.all_concepts), len(self.all_concepts))

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip().lower()
        filtered = [c for c in self.all_concepts if query in c.lower()]
        self._populate(filtered)
        self._update_status(len(filtered), len(self.all_concepts))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#cs-list", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.name)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def _populate(self, concepts: list[str]) -> None:
        lv = self.query_one("#cs-list", ListView)
        lv.clear()
        for c in concepts:
            lv.append(ListItem(Label(c), name=c))

    def _update_status(self, shown: int, total: int) -> None:
        if shown == total:
            text = f"{total:,} concepts  —  type to filter"
        else:
            text = f"{shown:,} of {total:,} concepts match"
        self.query_one("#cs-status", Static).update(text)


# ──────────────────────────────────────────────────────────────────────────────
# Theme picker screen
# ──────────────────────────────────────────────────────────────────────────────

class ThemeScreen(ModalScreen[str | None]):
    """Full-screen theme picker. Dismisses with selected theme name, or None to clear."""

    BINDINGS = [Binding("escape", "dismiss_none", "Close")]

    CSS = """
    ThemeScreen {
        background: $surface;
        padding: 1 2;
    }

    #th-title {
        height: 1;
        margin-bottom: 1;
        color: $text-muted;
    }

    #th-list {
        height: 1fr;
        border: solid $primary-darken-2;
    }

    #th-status {
        height: 1;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def __init__(self, theme_counts: dict[str, int], active_theme: str | None) -> None:
        super().__init__()
        self.theme_counts  = theme_counts
        self.active_theme  = active_theme

    def compose(self) -> ComposeResult:
        yield Label("Theme Browser  —  Enter to select, Escape to close", id="th-title")
        yield ListView(id="th-list")
        yield Static("", id="th-status")

    def on_mount(self) -> None:
        lv = self.query_one("#th-list", ListView)
        # "(All themes)" always first
        lv.append(ListItem(Label("[italic]( All themes )[/italic]"), name="__all__"))
        for theme in ALL_THEMES:
            count = self.theme_counts.get(theme, 0)
            if count == 0:
                continue
            marker = "▶ " if theme == self.active_theme else "  "
            lv.append(ListItem(Label(f"{marker}{theme}  [{count}]"), name=theme))
        n = sum(self.theme_counts.values())
        self.query_one("#th-status", Static).update(
            f"{len(self.theme_counts)} themes  |  {n} concepts total"
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        name = event.item.name
        self.dismiss(None if name == "__all__" else name)

    def action_dismiss_none(self) -> None:
        self.dismiss(None if self.active_theme is None else self.active_theme)


# ──────────────────────────────────────────────────────────────────────────────
# Main browser
# ──────────────────────────────────────────────────────────────────────────────

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
        Binding("q",      "quit",                "Quit"),
        Binding("g",      "select_theme",        "Themes"),
        Binding("t",      "toggle_refinements",  "Top-level only"),
        Binding("f",      "fullscreen_concepts", "All concepts"),
        Binding("p",      "preview",             "Preview"),
        Binding("e",      "export",              "Export marked"),
        Binding("escape", "focus_concepts",      "Back to concepts"),
        Binding("tab",    "focus_variables",     "Variables", show=False),
    ]

    def __init__(self):
        super().__init__()
        if not CATALOG_PATH.exists():
            sys.exit(f"Catalog not found: {CATALOG_PATH}\nRun: uv run collect_acs_catalog.py")
        self.df = pd.read_parquet(CATALOG_PATH)
        self.all_concepts: list[str] = sorted(self.df["concept"].unique())
        _concept_set = set(self.all_concepts)
        self.top_level_concepts: list[str] = [
            c for c in self.all_concepts if not _is_refinement(c, _concept_set)
        ]
        # theme map over top-level concepts only
        self._theme_map: dict[str, list[str]] = {}
        for c in self.top_level_concepts:
            self._theme_map.setdefault(_assign_theme(c), []).append(c)
        self._theme_counts: dict[str, int] = {t: len(v) for t, v in self._theme_map.items()}
        self._top_level_only: bool = False
        self._active_theme: str | None = None
        self.marked: set[str] = set()
        self._current_concept: str | None = None
        self._current_var: str | None = None
        self._api_key: str = os.environ.get("CENSUS_API_KEY", "")

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

        self._populate_concepts(self._active_concepts())
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

    def _active_concepts(self) -> list[str]:
        if self._active_theme is not None:
            # Theme view always works on top-level concepts
            return self._theme_map.get(self._active_theme, [])
        return self.top_level_concepts if self._top_level_only else self.all_concepts

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip().lower()
        filtered = [c for c in self._active_concepts() if query in c.lower()]
        self._populate_concepts(filtered)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#concept-list", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._load_concept(event.item.name)

    def _load_concept(self, concept: str) -> None:
        if concept == self._current_concept:
            return
        self._current_concept = concept
        # Sync the sidebar highlight to match
        lv = self.query_one("#concept-list", ListView)
        for item in lv.query(ListItem):
            if item.name == concept:
                item.highlighted = True
                break
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
        marked_str = f"{n} variable{'s' if n != 1 else ''} marked"
        if self._active_theme:
            count = len(self._theme_map.get(self._active_theme, []))
            mode_str = f"theme: {self._active_theme} ({count:,})"
        elif self._top_level_only:
            mode_str = f"top-level only ({len(self.top_level_concepts):,})"
        else:
            mode_str = f"all concepts ({len(self.all_concepts):,})"
        self.sub_title = f"{marked_str}  |  {mode_str}"

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_preview(self) -> None:
        if not self._current_var:
            self.notify("Highlight a variable first.", severity="warning")
            return
        if not self._api_key:
            self.notify(
                "CENSUS_API_KEY not set — add it to .env or export it.",
                severity="error", timeout=5,
            )
            return
        rows = self.df[self.df["name"] == self._current_var]
        label = rows.iloc[0]["label"] if not rows.empty else ""
        self.push_screen(PreviewModal(self._current_var, label, self._api_key))

    def action_select_theme(self) -> None:
        def on_selected(theme: str | None) -> None:
            self._active_theme = theme
            query = self.query_one("#concept-filter", Input).value.strip().lower()
            filtered = [c for c in self._active_concepts() if query in c.lower()]
            self._populate_concepts(filtered)
            self._update_subtitle()
        self.push_screen(ThemeScreen(self._theme_counts, self._active_theme), on_selected)

    def action_toggle_refinements(self) -> None:
        self._top_level_only = not self._top_level_only
        query = self.query_one("#concept-filter", Input).value.strip().lower()
        filtered = [c for c in self._active_concepts() if query in c.lower()]
        self._populate_concepts(filtered)
        self._update_subtitle()

    def action_fullscreen_concepts(self) -> None:
        def on_selected(concept: str | None) -> None:
            if concept:
                self._load_concept(concept)
        self.push_screen(ConceptScreen(self._active_concepts()), on_selected)

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
