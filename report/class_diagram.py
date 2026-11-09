from dataclasses import dataclass, field
from html import escape

LINE = 14
WIDTH = 1100


@dataclass
class Box:
    key: str
    name: str
    x: float
    y: float
    w: float
    stereotype: str = ""
    attrs: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    italic: bool = False
    fill: str = "#f6f6f4"

    @property
    def header_h(self) -> float:
        return 22 + (12 if self.stereotype else 0)

    @property
    def attrs_h(self) -> float:
        return 6 + LINE * len(self.attrs) if self.attrs else 6

    @property
    def methods_h(self) -> float:
        return 6 + LINE * len(self.methods) if self.methods else 6

    @property
    def h(self) -> float:
        return self.header_h + self.attrs_h + self.methods_h

    def anchor(self, side: str, frac: float = 0.5) -> tuple[float, float]:
        if side == "top":
            return self.x + self.w * frac, self.y
        if side == "bottom":
            return self.x + self.w * frac, self.y + self.h
        if side == "left":
            return self.x, self.y + self.h * frac
        return self.x + self.w, self.y + self.h * frac

    def svg(self) -> str:
        x, y, w = self.x, self.y, self.w
        parts = [
            f'<rect x="{x}" y="{y}" width="{w}" height="{self.h}" rx="3" fill="#fff" '
            f'stroke="#3d3d3a" stroke-width="1.1"/>',
            f'<rect x="{x}" y="{y}" width="{w}" height="{self.header_h}" rx="3" '
            f'fill="{self.fill}" stroke="#3d3d3a" stroke-width="1.1"/>',
        ]
        ty = y + 15
        if self.stereotype:
            parts.append(
                f'<text x="{x + w / 2}" y="{ty - 2}" class="st">«{escape(self.stereotype)}»</text>'
            )
            ty += 12
        style = ' font-style="italic"' if self.italic else ""
        parts.append(
            f'<text x="{x + w / 2}" y="{ty + 1}" class="nm"{style}>{escape(self.name)}</text>'
        )
        sy = y + self.header_h
        parts.append(
            f'<line x1="{x}" y1="{sy + self.attrs_h}" x2="{x + w}" '
            f'y2="{sy + self.attrs_h}" stroke="#3d3d3a" stroke-width="0.8"/>'
        )
        for i, text in enumerate(self.attrs):
            parts.append(
                f'<text x="{x + 6}" y="{sy + 14 + i * LINE}" class="mb">{escape(text)}</text>'
            )
        my = sy + self.attrs_h
        for i, text in enumerate(self.methods):
            parts.append(
                f'<text x="{x + 6}" y="{my + 14 + i * LINE}" class="mb">{escape(text)}</text>'
            )
        return "\n".join(parts)


ABSTRACT = "#e8f0fb"
VALUE = "#fdf3e3"
SERVICE = "#eaf6ef"

BOXES = [
    Box(
        "service",
        "StudentService",
        10,
        10,
        300,
        "application service",
        fill=SERVICE,
        attrs=[
            "-_registry: StudentRegistry",
            "-_notifier: Notifier",
            "-_policy: GradingPolicy",
        ],
        methods=[
            "+register(student: S) → S",
            "+register_from_payload(p: StudentPayload)",
            "+edit / transfer / post_result",
            "+find_by_id / find_by_last_name / find_in_group",
            "+average_of(id) / best_student(group)",
        ],
    ),
    Box(
        "report",
        "ReportService",
        335,
        10,
        250,
        "application service",
        fill=SERVICE,
        attrs=["-_registry: StudentRegistry", "-_policy: GradingPolicy"],
        methods=[
            "+summaries() → list[StudentSummary]",
            "+ranking(group) → list[tuple[…]]",
            "+group_report() / scholarship_holders()",
            "+card(student) → str",
        ],
    ),
    Box(
        "notifier",
        "Notifier",
        760,
        10,
        330,
        "Protocol, runtime_checkable",
        italic=True,
        fill=ABSTRACT,
        methods=["+send(recipient, message) → None"],
    ),
    Box("console", "ConsoleNotifier", 700, 100, 175, methods=["+send(recipient, message)"]),
    Box(
        "memory",
        "MemoryNotifier",
        895,
        100,
        195,
        attrs=["+messages: list[tuple[str, str]]"],
        methods=["+send(recipient, message)"],
    ),
    Box(
        "registry",
        "StudentRegistry",
        10,
        225,
        300,
        "aggregate root",
        attrs=[
            "-_students: Repository[int, Student]",
            "-_groups: Repository[GroupCode, Group]",
        ],
        methods=[
            "+add_student(student: S) → S",
            "+get(id) / group(code) / groups()",
            "+find_by_last_name(name) → list[Student]",
            "+edit_student(…) / transfer(id, code)",
            "+best_student(policy, group) → Student | None",
        ],
    ),
    Box(
        "repo",
        "Repository[K, T]",
        335,
        225,
        250,
        "abstract, generic",
        italic=True,
        fill=ABSTRACT,
        methods=[
            "+add / get / remove «abstract»",
            "+__iter__ / __len__ «abstract»",
            "+find(predicate) → list[T]",
        ],
    ),
    Box(
        "memrepo",
        "InMemoryRepository[K, T]",
        335,
        333,
        250,
        attrs=["-_key: Callable[[T], K]", "-_items: dict[K, T]"],
        methods=["+__contains__ / __getitem__ / __repr__"],
    ),
    Box(
        "policy",
        "GradingPolicy",
        610,
        225,
        480,
        "abstract",
        italic=True,
        fill=ABSTRACT,
        attrs=["+name: ClassVar[str]"],
        methods=[
            "+average(results) → Grade | None «abstract»",
            "+create(name, …) «classmethod, фабрика»",
            "+available() → tuple[str, …]",
        ],
    ),
    Box("simple", "SimpleAverage", 610, 350, 130, methods=["+average(results)"]),
    Box("weighted", "CreditWeightedAverage", 750, 350, 180, methods=["+average(results)"]),
    Box(
        "best",
        "BestResultsAverage",
        940,
        350,
        150,
        attrs=["-_best: int"],
        methods=["+average(results)"],
    ),
    Box(
        "group",
        "Group",
        10,
        405,
        300,
        attrs=["-_code: GroupCode", "-_members: dict[int, Student]"],
        methods=[
            "+code / curator / members «property»",
            "+add(student) / remove(id)",
            "+average(policy) / best(policy)",
            "__len__ / __iter__ / __contains__",
        ],
    ),
    Box(
        "student",
        "Student",
        335,
        440,
        250,
        "dataclass, entity",
        attrs=[
            "id: int",
            "first_name, last_name, email: str",
            "group: GroupCode",
            "record: AcademicRecord",
        ],
        methods=[
            "+full_name «property»",
            "+edit(…) / average(policy)",
            "+has_scholarship(policy) → bool",
            "__eq__ / __hash__ / __str__",
        ],
    ),
    Box("budget", "BudgetStudent", 335, 625, 130, methods=["+has_scholarship()"]),
    Box("contract", "ContractStudent", 475, 625, 130, methods=["funding: 'contract'"]),
    Box(
        "record",
        "AcademicRecord",
        610,
        430,
        240,
        attrs=["-_results: dict[str, CourseResult]"],
        methods=[
            "+record(result) / results «property»",
            "+average(policy) → Grade | None",
            "__len__ / __iter__ / __getitem__",
            "__contains__ / __repr__",
        ],
    ),
    Box(
        "course",
        "CourseResult",
        870,
        430,
        220,
        "frozen dataclass",
        fill=VALUE,
        attrs=["subject: str", "grade: Grade", "credits: int"],
    ),
    Box(
        "grade",
        "Grade",
        870,
        550,
        220,
        "frozen value object",
        fill=VALUE,
        attrs=["value: Decimal"],
        methods=["+of(value) «classmethod»", "+level «property»", "__lt__ / __str__"],
    ),
    Box(
        "code",
        "GroupCode",
        610,
        560,
        240,
        "frozen value object",
        fill=VALUE,
        attrs=["value: str"],
        methods=["order=True, __str__"],
    ),
]


@dataclass
class Edge:
    source: str
    s_side: str
    target: str
    t_side: str
    kind: str
    s_frac: float = 0.5
    t_frac: float = 0.5
    label: str = ""
    via: list[tuple[float, float]] = field(default_factory=list)
    label_at: tuple[float, float] | None = None


EDGES = [
    Edge("budget", "top", "student", "bottom", "extends", s_frac=0.5, t_frac=0.25),
    Edge("contract", "top", "student", "bottom", "extends", s_frac=0.5, t_frac=0.75),
    Edge("simple", "top", "policy", "bottom", "extends", t_frac=0.2),
    Edge("weighted", "top", "policy", "bottom", "extends", t_frac=0.5),
    Edge("best", "top", "policy", "bottom", "extends", t_frac=0.8),
    Edge("memrepo", "top", "repo", "bottom", "extends"),
    Edge("console", "top", "notifier", "bottom", "realizes", t_frac=0.2),
    Edge("memory", "top", "notifier", "bottom", "realizes", t_frac=0.8),
    Edge("service", "bottom", "registry", "top", "inject", label="«inject»"),
    Edge(
        "service",
        "top",
        "notifier",
        "top",
        "inject",
        s_frac=0.95,
        via=[(295, -6), (0, -6)],
        label="«inject»",
        label_at=(560, -9),
    ),
    Edge(
        "report",
        "bottom",
        "registry",
        "top",
        "inject",
        s_frac=0.1,
        t_frac=0.93,
        via=[(360, 196), (0, 196)],
    ),
    Edge(
        "report",
        "right",
        "policy",
        "top",
        "inject",
        t_frac=(660 - 610) / 480,
        label="«inject»",
        label_at=(590, 68),
    ),
    Edge(
        "registry",
        "right",
        "repo",
        "left",
        "inject",
        s_frac=0.2,
        t_frac=0.2,
        label="×2",
        label_at=(314, 236),
    ),
    Edge("registry", "bottom", "group", "top", "aggregation", label="0..*"),
    Edge("group", "right", "student", "left", "aggregation", s_frac=0.45, t_frac=0.15),
    Edge("student", "right", "record", "left", "composition", s_frac=0.2, t_frac=0.3),
    Edge("record", "right", "course", "left", "composition", label="0..*", label_at=(851, 465)),
    Edge("course", "bottom", "grade", "top", "composition"),
    Edge("student", "right", "code", "left", "composition", s_frac=0.8, t_frac=0.5),
    Edge(
        "record",
        "top",
        "policy",
        "bottom",
        "uses",
        s_frac=(745 - 610) / 240,
        t_frac=(745 - 610) / 480,
        label="average(policy)",
        label_at=(750, 420),
    ),
]

MARKERS = """
<defs>
  <marker id="tri" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="12" markerHeight="12"
    markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L11,6 L0,12 z" fill="#fff"
    stroke="#3d3d3a" stroke-width="1"/></marker>
  <marker id="open" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9"
    markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L9,5 L0,10" fill="none"
    stroke="#3d3d3a" stroke-width="1.2"/></marker>
  <marker id="dfill" viewBox="0 0 16 10" refX="1" refY="5" markerWidth="16" markerHeight="10"
    markerUnits="userSpaceOnUse" orient="auto"><path d="M1,5 L8,0.5 L15,5 L8,9.5 z"
    fill="#3d3d3a"/></marker>
  <marker id="dhollow" viewBox="0 0 16 10" refX="1" refY="5" markerWidth="16" markerHeight="10"
    markerUnits="userSpaceOnUse" orient="auto"><path d="M1,5 L8,0.5 L15,5 L8,9.5 z" fill="#fff"
    stroke="#3d3d3a" stroke-width="1"/></marker>
</defs>"""


def route(edge: Edge, boxes: dict[str, Box]) -> list[tuple[float, float]]:
    start = boxes[edge.source].anchor(edge.s_side, edge.s_frac)
    end = boxes[edge.target].anchor(edge.t_side, edge.t_frac)
    if edge.via:
        points = [start]
        for vx, vy in edge.via:
            points.append((vx or end[0], vy or end[1]))
        return [*points, end]
    vertical = {"top", "bottom"}
    if edge.s_side in vertical and edge.t_side in vertical:
        mid = (start[1] + end[1]) / 2
        return [start, (start[0], mid), (end[0], mid), end]
    if edge.s_side not in vertical and edge.t_side not in vertical:
        mid = (start[0] + end[0]) / 2
        return [start, (mid, start[1]), (mid, end[1]), end]
    if edge.s_side in vertical:
        return [start, (start[0], end[1]), end]
    return [start, (end[0], start[1]), end]


def edge_svg(edge: Edge, boxes: dict[str, Box]) -> str:
    points = route(edge, boxes)
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    dashed = edge.kind in {"realizes", "uses", "inject"}
    attrs = {
        "extends": 'marker-end="url(#tri)"',
        "realizes": 'marker-end="url(#tri)"',
        "uses": 'marker-end="url(#open)"',
        "inject": 'marker-end="url(#open)"',
        "composition": 'marker-start="url(#dfill)" marker-end="url(#open)"',
        "aggregation": 'marker-start="url(#dhollow)" marker-end="url(#open)"',
    }[edge.kind]
    dash = ' stroke-dasharray="5 3"' if dashed else ""
    svg = f'<path d="{d}" fill="none" stroke="#3d3d3a" stroke-width="1.1"{dash} {attrs}/>'
    if edge.label:
        if edge.label_at is not None:
            lx, ly = edge.label_at
            anchor = "start"
        else:
            (x1, y1), (x2, y2) = points[-2], points[-1]
            lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
            lx, ly = (lx, ly - 4) if y1 == y2 else (lx + 5, ly)
            anchor = "middle" if y1 == y2 else "start"
        svg += (
            f'<text x="{lx}" y="{ly}" class="lb" text-anchor="{anchor}">{escape(edge.label)}</text>'
        )
    return svg


def render() -> str:
    boxes = {box.key: box for box in BOXES}
    height = max(box.y + box.h for box in BOXES) + 10
    style = (
        "<style>.nm{font:bold 12.5px 'Segoe UI',Arial,sans-serif;text-anchor:middle;fill:#111}"
        ".st{font:italic 10px 'Segoe UI',Arial,sans-serif;text-anchor:middle;fill:#444}"
        ".mb{font:10.5px Consolas,'Courier New',monospace;fill:#222}"
        ".lb{font:italic 10px 'Segoe UI',Arial,sans-serif;fill:#333}</style>"
    )
    body = [box.svg() for box in BOXES] + [edge_svg(edge, boxes) for edge in EDGES]
    top = 20
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height + top:.0f}" '
        f'role="img" aria-label="UML class diagram">{style}{MARKERS}'
        f'<g transform="translate(0,{top})">{"".join(body)}</g></svg>'
    )


if __name__ == "__main__":
    import sys
    from pathlib import Path

    Path(sys.argv[1]).write_text(
        f"<!doctype html><meta charset='utf-8'><body style='margin:0;background:#fff'>"
        f"<div style='width:{WIDTH}px'>{render()}</div>",
        encoding="utf-8",
    )
    for box in BOXES:
        print(
            f"{box.key:10} x={box.x:5} y={box.y:5} w={box.w:5} h={box.h:5} bottom={box.y + box.h}"
        )
